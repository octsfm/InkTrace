from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from domain.entities.ai.models import CandidateDraft, CandidateDraftStatus, CandidateDraftValidationStatus, LLMRequest
from domain.entities.ai.opening_models import (
    OpeningBatchStatus,
    OpeningBrief,
    OpeningChapterResult,
    OpeningDirection,
    OpeningDirectionBatch,
    OpeningDirectionStatus,
    OpeningDraftBatch,
    OpeningReferenceSession,
    OpeningReferenceSummary,
    OpeningOriginalityReport,
    OpeningRiskLevel,
)


class OpeningAgentService:
    def __init__(
        self,
        *,
        repository,
        temporary_text_store,
        direction_generator,
        draft_generator,
        candidate_draft_repository=None,
        originality_checker=None,
    ) -> None:
        self._repository = repository
        self._temporary_text_store = temporary_text_store
        self._direction_generator = direction_generator
        self._draft_generator = draft_generator
        self._candidate_draft_repository = candidate_draft_repository
        self._originality_checker = originality_checker

    def prepare_brief(
        self,
        *,
        work_id: str,
        story_premise: str,
        protagonist_desire: str,
        third_chapter_expectation: str,
        idempotency_key: str,
        source_outline_version: str = "",
        source_asset_versions: dict[str, str] | None = None,
    ) -> OpeningBrief:
        existing = self._repository.find_by_idempotency("brief", idempotency_key)
        if existing is not None:
            return existing
        if not all(str(value or "").strip() for value in (work_id, story_premise, protagonist_desire, third_chapter_expectation)):
            raise ValueError("P2_OPENING_BRIEF_NOT_READY")
        now = self._now()
        value = OpeningBrief(
            brief_id=self._id("ob"), work_id=work_id,
            story_premise=story_premise.strip(), protagonist_desire=protagonist_desire.strip(),
            third_chapter_expectation=third_chapter_expectation.strip(),
            source_outline_version=source_outline_version,
            source_asset_versions=source_asset_versions or {}, idempotency_key=idempotency_key,
            created_at=now, updated_at=now,
        )
        return self._repository.save_brief(value)

    def import_references(
        self,
        *,
        brief_id: str,
        references: list[dict[str, object]],
        rights_confirmed: bool,
        rights_text_version: str,
        idempotency_key: str,
    ) -> OpeningReferenceSession:
        existing = self._repository.find_by_idempotency("reference_session", idempotency_key)
        if existing is not None:
            return existing
        brief = self._require_brief(brief_id)
        if not rights_confirmed:
            raise ValueError("P2_COPYRIGHT_NOT_CONFIRMED")
        if not 1 <= len(references) <= 3:
            raise ValueError("P2_OPENING_REFERENCE_LIMIT_EXCEEDED")
        texts: list[str] = []
        normalized: list[tuple[str, list[str]]] = []
        for item in references:
            title = str(item.get("title", "") or "").strip()
            chapters = [str(value or "") for value in list(item.get("chapters_text", []) or [])]
            if not title or not 1 <= len(chapters) <= 3 or sum(len(value) for value in chapters) > 30000:
                raise ValueError("P2_OPENING_REFERENCE_LIMIT_EXCEEDED")
            texts.extend(chapters)
            normalized.append((title, chapters))
        session_id = self._id("ors")
        self._temporary_text_store.put(session_id, texts)
        try:
            summaries = []
            for title, chapters in normalized:
                joined = "\n".join(chapters)
                summaries.append(OpeningReferenceSummary(
                    reference_id=self._id("oref"), title=title, chapter_count=len(chapters),
                    word_count=len(joined), source_text_hash=hashlib.sha256(joined.encode("utf-8")).hexdigest(),
                    analysis_summary=self._summarize_reference(chapters),
                ))
            now_dt = datetime.now(UTC)
            value = OpeningReferenceSession(
                reference_session_id=session_id, brief_id=brief_id, work_id=brief.work_id,
                reference_summaries=summaries, copyright_confirmed_at=now_dt.isoformat(),
                rights_text_version=rights_text_version, status="analyzed",
                expires_at=(now_dt + timedelta(minutes=30)).isoformat(), idempotency_key=idempotency_key,
                created_at=now_dt.isoformat(), updated_at=now_dt.isoformat(),
            )
            return self._repository.save_reference_session(value)
        finally:
            self._temporary_text_store.delete(session_id)

    def generate_directions(self, *, brief_id: str, idempotency_key: str) -> OpeningDirectionBatch:
        existing = self._repository.find_by_idempotency("direction_batch", idempotency_key)
        if existing is not None:
            return existing
        brief = self._require_brief(brief_id)
        references = self._repository.list_reference_sessions(brief_id)
        raw_items = self._direction_generator.generate(
            brief=brief,
            reference_summaries=[summary for session in references for summary in session.reference_summaries],
        )
        if len(raw_items) != 3:
            raise ValueError("P2_OPENING_DIRECTION_GENERATION_INVALID")
        now = self._now()
        batch_id = self._id("odb")
        directions = [OpeningDirection(
            direction_id=self._id("od"), batch_id=batch_id, brief_id=brief_id, work_id=brief.work_id,
            name=str(item["name"]), summary=str(item["summary"]),
            chapter_goals=list(item.get("chapter_goals", [])), advantages=list(item.get("advantages", [])),
            risks=list(item.get("risks", [])), created_at=now, updated_at=now,
        ) for item in raw_items]
        return self._repository.save_direction_batch(OpeningDirectionBatch(
            batch_id=batch_id, brief_id=brief_id, work_id=brief.work_id, directions=directions,
            idempotency_key=idempotency_key, created_at=now, updated_at=now,
        ))

    def confirm_direction(self, *, direction_id: str, caller_type: str, user_action: bool, user_id: str, idempotency_key: str) -> OpeningDirection:
        if caller_type != "user_action" or not user_action or not user_id or not idempotency_key:
            raise ValueError("P2_CALLER_FORBIDDEN")
        direction = self._repository.get_direction(direction_id)
        if direction is None:
            raise ValueError("P2_OPENING_DIRECTION_NOT_FOUND")
        batch = self._repository.get_direction_batch(direction.batch_id)
        if batch is None:
            raise ValueError("P2_OPENING_DIRECTION_NOT_FOUND")
        if batch.confirmed_direction_id and batch.confirmed_direction_id != direction_id:
            raise ValueError("P2_OPENING_DIRECTION_STALE")
        now = self._now()
        updated_directions = []
        confirmed = None
        for item in batch.directions:
            if item.direction_id == direction_id:
                item = item.model_copy(update={"status": OpeningDirectionStatus.CONFIRMED, "confirmed_by": user_id, "confirmed_at": now, "updated_at": now})
                confirmed = item
            else:
                item = item.model_copy(update={"status": OpeningDirectionStatus.SUPERSEDED, "updated_at": now})
            updated_directions.append(item)
        self._repository.save_direction_batch(batch.model_copy(update={"directions": updated_directions, "confirmed_direction_id": direction_id, "updated_at": now}))
        return confirmed

    def revise_direction(
        self,
        *,
        direction_id: str,
        name: str,
        summary: str,
        chapter_goals: list[str],
        advantages: list[str],
        risks: list[str],
        idempotency_key: str,
    ) -> OpeningDirection:
        revised_id = self._revision_id(idempotency_key)
        existing = self._repository.get_direction(revised_id)
        if existing is not None:
            return existing
        original = self._repository.get_direction(direction_id)
        if original is None:
            raise ValueError("P2_OPENING_DIRECTION_NOT_FOUND")
        batch = self._repository.get_direction_batch(original.batch_id)
        if batch is None:
            raise ValueError("P2_OPENING_DIRECTION_NOT_FOUND")
        normalized_goals = [str(value or "").strip() for value in chapter_goals]
        if (
            batch.confirmed_direction_id
            or not idempotency_key
            or not str(name or "").strip()
            or not str(summary or "").strip()
            or len(normalized_goals) != 3
            or not all(normalized_goals)
        ):
            raise ValueError("P2_OPENING_DIRECTION_STALE" if batch.confirmed_direction_id else "P2_OPENING_DIRECTION_GENERATION_INVALID")
        now = self._now()
        revised = OpeningDirection(
            direction_id=revised_id, batch_id=batch.batch_id, brief_id=original.brief_id,
            work_id=original.work_id, name=name.strip(), summary=summary.strip(),
            chapter_goals=normalized_goals,
            advantages=[str(value).strip() for value in advantages if str(value).strip()],
            risks=[str(value).strip() for value in risks if str(value).strip()],
            revision_no=original.revision_no + 1, parent_direction_id=original.direction_id,
            created_at=now, updated_at=now,
        )
        directions = [
            item.model_copy(update={"status": OpeningDirectionStatus.SUPERSEDED, "updated_at": now})
            if item.direction_id == original.direction_id else item
            for item in batch.directions
        ]
        directions.append(revised)
        self._repository.save_direction_batch(batch.model_copy(update={"directions": directions, "updated_at": now}))
        return revised

    def generate_drafts(self, *, direction_id: str, idempotency_key: str) -> OpeningDraftBatch:
        existing = self._repository.find_by_idempotency("draft_batch", idempotency_key)
        if existing is not None:
            return existing
        direction = self._repository.get_direction(direction_id)
        if direction is None or direction.status != OpeningDirectionStatus.CONFIRMED:
            raise ValueError("P2_OPENING_DIRECTION_NOT_CONFIRMED")
        brief = self._require_brief(direction.brief_id)
        reference_sessions = self._repository.list_reference_sessions(brief.brief_id)
        reference_summaries = [summary for session in reference_sessions for summary in session.reference_summaries]
        if self._originality_checker is not None and reference_summaries:
            strategy_risk = self._originality_checker.check_strategy(brief=brief, direction=direction, reference_summaries=reference_summaries)
            strategy_report = self._save_originality_report(
                brief=brief, direction=direction, check_stage="strategy", raw=strategy_risk
            )
            if strategy_report.risk_level == OpeningRiskLevel.HIGH:
                raise ValueError("P2_OPENING_STRATEGY_SIMILARITY_BLOCKED")
        now = self._now()
        batch_id = self._id("odraft")
        results: list[OpeningChapterResult] = []
        result_refs: list[str] = []
        previous: list[str] = []
        for chapter_no in (1, 2, 3):
            try:
                content = self._draft_generator.generate(brief=brief, direction=direction, chapter_no=chapter_no, previous_drafts=previous)
                candidate_id = self._id("cd")
                self._save_candidate(candidate_id=candidate_id, batch_id=batch_id, brief=brief, direction=direction, chapter_no=chapter_no, content=content)
                report_id = ""
                if self._originality_checker is not None and reference_summaries:
                    draft_risk = self._originality_checker.check_draft(
                        brief=brief, direction=direction, chapter_no=chapter_no, content=content,
                        reference_summaries=reference_summaries,
                    )
                    report = self._save_originality_report(
                        brief=brief, direction=direction, check_stage="draft", raw=draft_risk,
                        draft_batch_id=batch_id, candidate_draft_id=candidate_id,
                    )
                    report_id = report.report_id
                    if report.risk_level == OpeningRiskLevel.HIGH and self._candidate_draft_repository is not None:
                        draft = self._candidate_draft_repository.get(candidate_id)
                        metadata = dict(draft.metadata)
                        metadata.update({"opening_originality_status": "blocked", "opening_originality_report_id": report_id})
                        self._candidate_draft_repository.save(draft.model_copy(update={"metadata": metadata, "warning_codes": [*draft.warning_codes, "P2_OPENING_DRAFT_ORIGINALITY_REVIEW_REQUIRED"]}))
                previous.append(content)
                result_refs.append(f"candidate_draft:{candidate_id}")
                results.append(OpeningChapterResult(chapter_no=chapter_no, status="waiting_review", candidate_draft_id=candidate_id, originality_report_id=report_id))
            except Exception as exc:
                results.append(OpeningChapterResult(chapter_no=chapter_no, status="failed", error_code=str(exc) or "writer_failed"))
                break
        if len(results) == 3 and all(item.status == "waiting_review" for item in results):
            status = OpeningBatchStatus.WAITING_DRAFT_REVIEW
        elif result_refs:
            status = OpeningBatchStatus.PARTIAL_SUCCESS
        else:
            status = OpeningBatchStatus.FAILED
        value = OpeningDraftBatch(
            draft_batch_id=batch_id, work_id=brief.work_id, brief_id=brief.brief_id,
            direction_id=direction_id, status=status, chapter_results=results, result_refs=result_refs,
            idempotency_key=idempotency_key, created_at=now, updated_at=self._now(),
        )
        return self._repository.save_draft_batch(value)

    def get_direction_batch(self, batch_id: str):
        value = self._repository.get_direction_batch(batch_id)
        if value is None:
            raise ValueError("P2_OPENING_DIRECTION_BATCH_NOT_FOUND")
        return value

    def get_draft_batch(self, batch_id: str):
        value = self._repository.get_draft_batch(batch_id)
        if value is None:
            raise ValueError("P2_OPENING_DRAFT_BATCH_NOT_FOUND")
        return value

    def stop_draft_batch(self, *, batch_id: str, caller_type: str, user_action: bool, user_id: str, idempotency_key: str):
        if caller_type != "user_action" or not user_action or not user_id or not idempotency_key:
            raise ValueError("P2_CALLER_FORBIDDEN")
        value = self.get_draft_batch(batch_id)
        if value.status not in {OpeningBatchStatus.GENERATING, OpeningBatchStatus.PARTIAL_SUCCESS}:
            raise ValueError("P2_OPENING_DRAFT_BATCH_NOT_RUNNING")
        updated = value.model_copy(update={"status": OpeningBatchStatus.STOPPED, "updated_at": self._now()})
        return self._repository.save_draft_batch(updated)

    def get_latest(self, work_id: str):
        return self._repository.get_latest(work_id)

    def _save_candidate(self, *, candidate_id: str, batch_id: str, brief: OpeningBrief, direction: OpeningDirection, chapter_no: int, content: str) -> None:
        if self._candidate_draft_repository is None:
            return
        now = self._now()
        self._candidate_draft_repository.save(CandidateDraft(
            candidate_draft_id=candidate_id, work_id=brief.work_id, chapter_id=f"opening-chapter-{chapter_no}",
            source_context_pack_id="", source_job_id="", status=CandidateDraftStatus.PENDING_REVIEW,
            content=content, content_preview=content[:200], word_count=len(content.split()), char_count=len(content),
            validation_status=CandidateDraftValidationStatus.PASSED, created_by="opening_agent",
            created_at=now, updated_at=now, metadata={"opening_phase": True, "opening_chapter_no": chapter_no,
            "opening_draft_batch_id": batch_id, "opening_brief_id": brief.brief_id, "opening_direction_id": direction.direction_id},
        ))

    def _require_brief(self, brief_id: str) -> OpeningBrief:
        value = self._repository.get_brief(brief_id)
        if value is None:
            raise ValueError("P2_OPENING_BRIEF_NOT_FOUND")
        return value

    def _save_originality_report(self, *, brief, direction, check_stage, raw, draft_batch_id="", candidate_draft_id=""):
        risk_level = OpeningRiskLevel(str(raw.get("risk_level", "low")))
        value = OpeningOriginalityReport(
            report_id=self._id("oor"), work_id=brief.work_id, brief_id=brief.brief_id,
            direction_id=direction.direction_id, draft_batch_id=draft_batch_id,
            candidate_draft_id=candidate_draft_id, check_stage=check_stage, risk_level=risk_level,
            evidence_summary=str(raw.get("evidence_summary", "")),
            revision_suggestions=list(raw.get("revision_suggestions", [])), created_at=self._now(),
        )
        return self._repository.save_originality_report(value)

    @staticmethod
    def _summarize_reference(chapters: list[str]) -> str:
        total = sum(len(value) for value in chapters)
        return f"已分析前{len(chapters)}章，共{total}字；仅保留结构化开篇特点。"

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _revision_id(idempotency_key: str) -> str:
        digest = hashlib.sha256(str(idempotency_key or "").encode("utf-8")).hexdigest()[:16]
        return f"odr_{digest}"

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()


class ModelRouterOpeningDirectionGenerator:
    def __init__(self, model_router) -> None:
        self._model_router = model_router

    def generate(self, *, brief, reference_summaries):
        reference_note = "；".join(item.analysis_summary for item in reference_summaries) or "无参考作品，请基于通用原创开篇规则"
        request = LLMRequest(
            model_role="planning", prompt_key="opening_directions", prompt_version="v2.0",
            output_schema_key="opening_directions_v2", request_id=f"req_{uuid.uuid4().hex[:12]}",
            trace_id=f"trace_{uuid.uuid4().hex[:12]}", messages=[
                {"role": "system", "content": "你是小说开篇策划助手。只输出 JSON 数组，必须恰好三个方向；每项包含 name、summary、chapter_goals(3项)、advantages、risks。不得模仿参考原文。"},
                {"role": "user", "content": f"故事：{brief.story_premise}\n主角目标：{brief.protagonist_desire}\n第三章期待：{brief.third_chapter_expectation}\n参考摘要：{reference_note}"},
            ],
        )
        response = self._model_router.generate(request)
        try:
            value = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise ValueError("P2_OPENING_DIRECTION_GENERATION_INVALID") from exc
        if not isinstance(value, list):
            raise ValueError("P2_OPENING_DIRECTION_GENERATION_INVALID")
        return value


class ModelRouterOpeningDraftGenerator:
    def __init__(self, model_router) -> None:
        self._model_router = model_router

    def generate(self, *, brief, direction, chapter_no, previous_drafts):
        previous_summary = "\n".join(text[-500:] for text in previous_drafts)
        request = LLMRequest(
            model_role="writer", prompt_key="opening_draft", prompt_version="v2.0",
            output_schema_key="plain_text", request_id=f"req_{uuid.uuid4().hex[:12]}",
            trace_id=f"trace_{uuid.uuid4().hex[:12]}", messages=[
                {"role": "system", "content": "你是原创小说作者助手。根据用户故事和已确认方向生成候选章节，不复刻任何现有作品，不解释，只输出正文。"},
                {"role": "user", "content": f"故事：{brief.story_premise}\n主角目标：{brief.protagonist_desire}\n开篇方向：{direction.summary}\n本章：第{chapter_no}章\n本章目标：{direction.chapter_goals[chapter_no - 1] if len(direction.chapter_goals) >= chapter_no else ''}\n前章末尾：{previous_summary}"},
            ],
        )
        content = str(self._model_router.generate(request).content or "").strip()
        if not content:
            raise ValueError("writer_output_invalid")
        return content


class ModelRouterOpeningOriginalityChecker:
    def __init__(self, model_router) -> None:
        self._model_router = model_router

    def check_strategy(self, *, brief, direction, reference_summaries):
        return self._check(
            stage="strategy",
            content=f"故事：{brief.story_premise}\n方向：{direction.summary}\n前三章：{' / '.join(direction.chapter_goals)}\n参考结构摘要：{' / '.join(item.analysis_summary for item in reference_summaries)}",
        )

    def check_draft(self, *, brief, direction, chapter_no, content, reference_summaries):
        return self._check(stage="draft", content=f"方向：{direction.summary}\n第{chapter_no}章候选稿：{content}\n参考结构摘要：{' / '.join(item.analysis_summary for item in reference_summaries)}")

    def _check(self, *, stage: str, content: str):
        request = LLMRequest(
            model_role="reviewer", prompt_key="opening_originality", prompt_version="v2.0",
            output_schema_key="opening_originality_v2", request_id=f"req_{uuid.uuid4().hex[:12]}",
            trace_id=f"trace_{uuid.uuid4().hex[:12]}", messages=[
                {"role": "system", "content": "检查原创性风险，只输出 JSON 对象：risk_level(low/medium/high)、evidence_summary、revision_suggestions。没有参考原文时不得凭空判定高风险。"},
                {"role": "user", "content": f"检查阶段：{stage}\n{content}"},
            ],
        )
        try:
            value = json.loads(self._model_router.generate(request).content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("P2_OPENING_ORIGINALITY_CHECK_INVALID") from exc
        if not isinstance(value, dict) or value.get("risk_level") not in {"low", "medium", "high"}:
            raise ValueError("P2_OPENING_ORIGINALITY_CHECK_INVALID")
        return value
