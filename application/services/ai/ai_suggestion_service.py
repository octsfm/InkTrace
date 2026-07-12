from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from threading import RLock

from domain.entities.ai.models import (
    AISuggestion,
    AISuggestionAction,
    AISuggestionActionType,
    AISuggestionBatch,
    AISuggestionDecision,
    AISuggestionDecisionType,
    AISuggestionPriority,
    AISuggestionSeverity,
    AISuggestionSource,
    AISuggestionStatus,
    AISuggestionTarget,
    AISuggestionType,
    DirectionPlanStatus,
    WritingTask,
    WritingTaskStatus,
)
from domain.repositories.ai.ai_review_repository import AIReviewRepository
from domain.repositories.ai.ai_suggestion_repository import AISuggestionRepository
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from application.services.ai.candidate_rewrite_service import CandidateRewriteService
from domain.value_objects.outline_snapshot import outline_content_hash
from domain.entities.ai.suggestion_payloads import WritingTaskSuggestionPayload


_P2_WRITING_TASK_CONVERT_LOCK = RLock()


def _normalize_decision_note(value: str) -> str:
    return str(value or "").strip()


def _user_decision_request_hash(*, resource_id: str, user_id: str, decision_note: str) -> str:
    canonical = json.dumps(
        {
            "resource_id": str(resource_id),
            "user_id": str(user_id),
            "decision_note": _normalize_decision_note(decision_note),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AISuggestionService:
    def __init__(
        self,
        *,
        ai_suggestion_repository: AISuggestionRepository,
        ai_review_repository: AIReviewRepository,
        candidate_draft_repository: CandidateDraftRepository,
        candidate_rewrite_service: CandidateRewriteService,
        trace_service=None,
        direction_plan_repository=None,
        chapter_plan_repository=None,
        writing_asset_service=None,
    ) -> None:
        self._ai_suggestion_repository = ai_suggestion_repository
        self._ai_review_repository = ai_review_repository
        self._candidate_draft_repository = candidate_draft_repository
        self._candidate_rewrite_service = candidate_rewrite_service
        self._trace_service = trace_service
        self._direction_plan_repository = direction_plan_repository
        self._chapter_plan_repository = chapter_plan_repository
        self._writing_asset_service = writing_asset_service

    def generate_from_review(self, review_id: str) -> AISuggestionBatch:
        review = self._ai_review_repository.get(review_id)
        draft = self._candidate_draft_repository.get(review.candidate_draft_id)
        source_version_id = draft.selected_version_id or self._candidate_draft_repository.list_versions(draft.candidate_draft_id)[-1].candidate_version_id
        now = self._now()
        suggestion_ids: list[str] = []

        for issue in list(review.issues or []):
            suggestion = AISuggestion(
                suggestion_id=f"ais_{uuid.uuid4().hex[:10]}",
                work_id=review.work_id,
                chapter_id=review.chapter_id,
                agent_session_id=draft.agent_session_id,
                source=AISuggestionSource(
                    source_type="review_issue",
                    source_ref_id=getattr(issue, "issue_id", ""),
                    source_agent_type="reviewer",
                    source_agent_session_id=draft.agent_session_id,
                    source_version_id=source_version_id,
                ),
                target=AISuggestionTarget(
                    target_type="candidate_draft_version",
                    target_ref_id=source_version_id,
                    target_scope="version",
                    target_snapshot_ref=draft.direction_plan_snapshot_id,
                ),
                suggestion_type=self._map_issue_to_suggestion_type(str(getattr(issue, "category", "") or "")),
                severity=self._map_severity(str(getattr(issue, "severity", "medium") or "medium")),
                priority=AISuggestionPriority.HIGH,
                title=str(getattr(issue, "message", "") or "AI 建议"),
                summary=str(getattr(issue, "suggestion", "") or str(getattr(issue, "message", "") or "")),
                rationale=review.summary,
                proposed_action="转化为 RewriteInstruction",
                status=AISuggestionStatus.GENERATED,
                created_by="reviewer_agent",
                created_at=now,
                updated_at=now,
                request_id=review.review_id,
                trace_id=draft.trace_id,
                action=AISuggestionAction(
                    action_type=AISuggestionActionType.CONVERT_TO_REWRITE_INSTRUCTION,
                    requires_user_action=True,
                    action_status="pending",
                ),
                batch_id="",
                metadata={"review_id": review.review_id},
            )
            self._ai_suggestion_repository.save(suggestion)
            suggestion_ids.append(suggestion.suggestion_id)

        if str(review.risk_level.value) in {"medium", "high"}:
            risk = AISuggestion(
                suggestion_id=f"ais_{uuid.uuid4().hex[:10]}",
                work_id=review.work_id,
                chapter_id=review.chapter_id,
                agent_session_id=draft.agent_session_id,
                source=AISuggestionSource(
                    source_type="review_report",
                    source_ref_id=review.review_id,
                    source_agent_type="reviewer",
                    source_agent_session_id=draft.agent_session_id,
                    source_version_id=source_version_id,
                ),
                target=AISuggestionTarget(
                    target_type="candidate_draft_version",
                    target_ref_id=source_version_id,
                    target_scope="version",
                    target_snapshot_ref=draft.direction_plan_snapshot_id,
                ),
                suggestion_type=AISuggestionType.RISK_WARNING,
                severity=AISuggestionSeverity.HIGH,
                priority=AISuggestionPriority.HIGH,
                title="高风险提示",
                summary=review.summary or "当前版本存在高风险问题。",
                rationale="risk_warning 只允许 acknowledge 或 dismiss，不允许自动执行。",
                proposed_action="人工确认后继续处理",
                status=AISuggestionStatus.GENERATED,
                created_by="reviewer_agent",
                created_at=now,
                updated_at=now,
                request_id=review.review_id,
                trace_id=draft.trace_id,
                action=AISuggestionAction(
                    action_type=AISuggestionActionType.DISMISS_ONLY,
                    requires_user_action=True,
                    action_status="pending",
                ),
                batch_id="",
                metadata={"review_id": review.review_id},
            )
            self._ai_suggestion_repository.save(risk)
            suggestion_ids.append(risk.suggestion_id)

        batch = AISuggestionBatch(
            batch_id=f"aisb_{uuid.uuid4().hex[:10]}",
            work_id=review.work_id,
            chapter_id=review.chapter_id,
            agent_session_id=draft.agent_session_id,
            source_report_id=review.review_id,
            suggestion_ids=suggestion_ids,
            generated_count=len(suggestion_ids),
            stale_count=0,
            created_at=now,
        )
        self._ai_suggestion_repository.save_batch(batch)
        for suggestion_id in suggestion_ids:
            suggestion = self._ai_suggestion_repository.get(suggestion_id)
            self._ai_suggestion_repository.save(suggestion.model_copy(update={"batch_id": batch.batch_id}))
        return batch

    def list_suggestions(self, *, work_id: str, chapter_id: str = "", target_ref_id: str = "") -> list[AISuggestion]:
        items = self._ai_suggestion_repository.list_suggestions(work_id=work_id, chapter_id=chapter_id, target_ref_id=target_ref_id)
        shown: list[AISuggestion] = []
        for item in items:
            if item.status == AISuggestionStatus.GENERATED:
                item = self._ai_suggestion_repository.save(item.model_copy(update={"status": AISuggestionStatus.SHOWN, "updated_at": self._now()}))
            shown.append(item)
        return shown

    def get_suggestion(self, suggestion_id: str) -> AISuggestion:
        item = self._ai_suggestion_repository.get(suggestion_id)
        if item.status == AISuggestionStatus.GENERATED:
            item = self._ai_suggestion_repository.save(item.model_copy(update={"status": AISuggestionStatus.SHOWN, "updated_at": self._now()}))
        return item

    def is_outline_assist_suggestion(self, suggestion_id: str) -> bool:
        try:
            item = self._ai_suggestion_repository.get(suggestion_id)
        except ValueError:
            return False
        return item.source.source_type == "outline_assist"

    def accept_suggestion(self, suggestion_id: str, *, user_id: str, user_action: bool) -> AISuggestion:
        self._require_user_action(user_action)
        item = self._ai_suggestion_repository.get(suggestion_id)
        if item.suggestion_type in {
            AISuggestionType.OUTLINE_POLISH,
            AISuggestionType.OUTLINE_EXPAND,
            AISuggestionType.CHAPTER_OUTLINE_DETAIL,
            AISuggestionType.WRITING_TASK_SUGGESTION,
        } and item.status not in {AISuggestionStatus.GENERATED, AISuggestionStatus.SHOWN}:
            raise ValueError("action_not_allowed")
        return self._save_decision(item, decision=AISuggestionDecisionType.ACCEPTED, status=AISuggestionStatus.ACCEPTED, user_id=user_id)

    def dismiss_suggestion(self, suggestion_id: str, *, user_id: str, user_action: bool, note: str = "") -> AISuggestion:
        self._require_user_action(user_action)
        item = self._ai_suggestion_repository.get(suggestion_id)
        if item.suggestion_type in {
            AISuggestionType.OUTLINE_POLISH,
            AISuggestionType.OUTLINE_EXPAND,
            AISuggestionType.CHAPTER_OUTLINE_DETAIL,
            AISuggestionType.WRITING_TASK_SUGGESTION,
        } and item.status not in {
            AISuggestionStatus.GENERATED,
            AISuggestionStatus.SHOWN,
            AISuggestionStatus.ACCEPTED,
        }:
            raise ValueError("action_not_allowed")
        return self._save_decision(
            item,
            decision=AISuggestionDecisionType.DISMISSED,
            status=AISuggestionStatus.DISMISSED,
            user_id=user_id,
            note=note,
        )

    def convert_suggestion(
        self,
        suggestion_id: str,
        *,
        user_id: str,
        user_action: bool,
        idempotency_key: str,
        decision_note: str = "",
    ) -> AISuggestion:
        self._require_user_action(user_action)
        if not str(idempotency_key or "").strip():
            raise ValueError("idempotency_key_required")
        item = self._ai_suggestion_repository.get(suggestion_id)
        if item.suggestion_type == AISuggestionType.WRITING_TASK_SUGGESTION:
            with _P2_WRITING_TASK_CONVERT_LOCK:
                return self._convert_writing_task_suggestion(
                    self._ai_suggestion_repository.get(suggestion_id),
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                    decision_note=decision_note,
                )
        if item.suggestion_type == AISuggestionType.RISK_WARNING:
            raise ValueError("suggestion_convert_forbidden")
        if item.action.action_type == AISuggestionActionType.CONVERT_TO_REWRITE_INSTRUCTION:
            rewrite = self._candidate_rewrite_service.request_rewrite(
                candidate_draft_id=item.metadata.get("candidate_draft_id", "") or self._candidate_draft_id_from_target(item.target.target_ref_id),
                source_version_id=item.target.target_ref_id,
                trigger_type="review_based",
                review_report_id=item.metadata.get("review_id", ""),
                user_instruction=item.summary,
                user_id=user_id,
                user_action=True,
                idempotency_key=idempotency_key,
            )
            action = item.action.model_copy(
                update={
                    "action_payload_ref": f"rewrite_request:{rewrite['rewrite_request_id']}",
                    "action_status": "completed",
                }
            )
        elif item.suggestion_type == AISuggestionType.MEMORY_UPDATE_SUGGESTION_REF:
            action = item.action.model_copy(
                update={"action_payload_ref": f"memory_review_gate:{item.target.target_ref_id}", "action_status": "completed"}
            )
        elif item.suggestion_type == AISuggestionType.CONFLICT_RESOLUTION_SUGGESTION:
            action = item.action.model_copy(
                update={"action_payload_ref": f"conflict_guard:{item.target.target_ref_id}", "action_status": "completed"}
            )
        else:
            action = item.action.model_copy(
                update={"action_payload_ref": f"suggestion_action:{item.target.target_ref_id}", "action_status": "completed"}
            )
        updated = self._save_decision(
            item.model_copy(update={"action": action}),
            decision=AISuggestionDecisionType.CONVERTED,
            status=AISuggestionStatus.CONVERTED,
            user_id=user_id,
        )
        return updated

    def _convert_writing_task_suggestion(
        self,
        item: AISuggestion,
        *,
        user_id: str,
        idempotency_key: str,
        decision_note: str,
    ) -> AISuggestion:
        key_hash = self._hash_idempotency_key(idempotency_key.strip())
        normalized_note = _normalize_decision_note(decision_note)
        request_hash = _user_decision_request_hash(
            resource_id=item.suggestion_id,
            user_id=user_id,
            decision_note=normalized_note,
        )
        self._require_convert_request_matches_key_scope(
            item,
            key_hash=key_hash,
            request_hash=request_hash,
        )
        metadata = dict(item.metadata or {})
        if item.status == AISuggestionStatus.CONVERTED:
            if (
                metadata.get("writing_task_convert_key_hash") == key_hash
                and metadata.get("writing_task_convert_request_hash") == request_hash
                and item.action.action_payload_ref
            ):
                return item
            raise ValueError("P2_IDEMPOTENCY_CONFLICT")
        if item.status not in {
            AISuggestionStatus.GENERATED,
            AISuggestionStatus.SHOWN,
            AISuggestionStatus.ACCEPTED,
        }:
            raise ValueError("suggestion_convert_forbidden")
        if self._direction_plan_repository is None or self._chapter_plan_repository is None:
            raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING")
        try:
            payload = WritingTaskSuggestionPayload.model_validate(item.payload).model_dump()
        except ValueError as exc:
            raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING") from exc
        chapter_plan_id = str(payload.get("chapter_plan_id") or "")
        try:
            plan = self._chapter_plan_repository.get(chapter_plan_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING") from exc
        if (
            plan.work_id != item.work_id
            or plan.chapter_id != item.chapter_id
            or plan.status not in {DirectionPlanStatus.CONFIRMED, DirectionPlanStatus.EDITED}
            or plan.stale_status != "fresh"
        ):
            raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING")
        current_plan = next(
            (
                candidate
                for candidate in self._chapter_plan_repository.list_by_work(item.work_id, chapter_id=item.chapter_id)
                if candidate.status in {DirectionPlanStatus.CONFIRMED, DirectionPlanStatus.EDITED}
                and candidate.stale_status == "fresh"
            ),
            None,
        )
        if current_plan is None or current_plan.chapter_plan_id != plan.chapter_plan_id:
            raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING")
        if self._writing_asset_service is None:
            raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING")
        try:
            current_outline = self._writing_asset_service.get_chapter_outline(item.chapter_id)
        except ValueError as exc:
            raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING") from exc
        if (
            int(current_outline.version) != int(payload.get("target_revision") or 0)
            or outline_content_hash(current_outline.content_text, current_outline.content_tree_json)
            != str(payload.get("target_content_hash") or "")
        ):
            raise ValueError("P2_OUTLINE_TARGET_CONFLICT")

        now = self._now()
        stable_task_id = f"wt_p2_{hashlib.sha256(item.suggestion_id.encode('utf-8')).hexdigest()[:16]}"
        existing_task = None
        try:
            existing_task = self._direction_plan_repository.get_writing_task(stable_task_id)
        except ValueError:
            existing_task = None
        if existing_task is not None:
            if (
                existing_task.metadata.get("conversion_key_hash") != key_hash
                or existing_task.metadata.get("conversion_request_hash") != request_hash
            ):
                raise ValueError("P2_IDEMPOTENCY_CONFLICT")
            task = existing_task
        else:
            task = WritingTask(
                writing_task_id=stable_task_id,
                work_id=item.work_id,
                chapter_id=item.chapter_id,
                target_chapter_id=item.chapter_id,
                direction_proposal_id=plan.direction_proposal_id,
                selected_option_id=plan.selected_option_id,
                chapter_plan_id=plan.chapter_plan_id,
                plan_item_id=plan.plan_items[0].item_id if plan.plan_items else "",
                agent_session_id=plan.agent_session_id,
                source_context_pack_id=plan.source_context_pack_id,
                source_arc_refs=[ref.arc_id for ref in plan.source_arc_refs],
                source_memory_refs=list(plan.source_memory_refs),
                status=WritingTaskStatus.PENDING,
                writing_goal=str(payload.get("writing_goal") or ""),
                must_include=[str(value) for value in list(payload.get("must_include") or [])],
                must_not_include=[str(value) for value in list(payload.get("must_not_include") or [])],
                tone_guidance=str(payload.get("tone_guidance") or ""),
                target_word_count=max(0, int(payload.get("target_word_count") or 0)),
                required_beats=[str(value) for value in list(payload.get("required_beats") or [])],
                direction_summary=str(payload.get("context_summary") or ""),
                plan_summary=plan.plan_summary,
                stale_status="fresh",
                generated_by="planner_agent",
                created_by="user_action",
                created_at=now,
                updated_at=now,
                request_id=item.request_id,
                trace_id=item.trace_id,
                metadata={
                    "source": "p2_outline_assist",
                    "suggestion_id": item.suggestion_id,
                    "chapter_plan_version": plan.version,
                    "target_revision": payload.get("target_revision"),
                    "target_content_hash": str(payload.get("target_content_hash") or ""),
                    "task_title": str(payload.get("task_title") or ""),
                    "conversion_key_hash": key_hash,
                    "conversion_request_hash": request_hash,
                },
            )
        self._record_outline_user_decision_before_write(
            trace_id=item.trace_id,
            work_id=item.work_id,
            chapter_id=item.chapter_id,
            operation_ref=item.suggestion_id,
            session_id=item.suggestion_id,
            step_id="writing_task_convert",
            summary="writing_task_convert",
            payload_digest={
                "suggestion_id": item.suggestion_id,
                "writing_task_id": task.writing_task_id,
                "decision_type": "convert_to_writing_task",
                "user_id": user_id,
            },
        )
        if existing_task is None:
            self._direction_plan_repository.save_writing_task(task)
        action = item.action.model_copy(
            update={
                "action_type": AISuggestionActionType.CREATE_WRITING_TASK,
                "action_payload_ref": f"writing_task:{task.writing_task_id}",
                "action_status": "completed",
            }
        )
        metadata["writing_task_convert_key_hash"] = key_hash
        metadata["writing_task_convert_request_hash"] = request_hash
        metadata["writing_task_id"] = task.writing_task_id
        return self._save_decision(
            item.model_copy(update={"action": action, "metadata": metadata}),
            decision=AISuggestionDecisionType.CONVERTED,
            status=AISuggestionStatus.CONVERTED,
            user_id=user_id,
            note=normalized_note,
        )

    def _require_convert_request_matches_key_scope(
        self,
        item: AISuggestion,
        *,
        key_hash: str,
        request_hash: str,
    ) -> None:
        for candidate in self._ai_suggestion_repository.list_suggestions(work_id=item.work_id):
            metadata = candidate.metadata or {}
            if (
                metadata.get("writing_task_convert_key_hash") == key_hash
                and metadata.get("writing_task_convert_request_hash") != request_hash
            ):
                raise ValueError("P2_IDEMPOTENCY_CONFLICT")
        if self._direction_plan_repository is None:
            return
        for task in self._direction_plan_repository.list_writing_tasks(item.work_id):
            metadata = task.metadata or {}
            if (
                metadata.get("conversion_key_hash") == key_hash
                and metadata.get("conversion_request_hash") != request_hash
            ):
                raise ValueError("P2_IDEMPOTENCY_CONFLICT")

    @staticmethod
    def _map_issue_to_suggestion_type(category: str) -> AISuggestionType:
        mapping = {
            "style": AISuggestionType.STYLE_SUGGESTION,
            "plot": AISuggestionType.PLOT_SUGGESTION,
            "character": AISuggestionType.CHARACTER_SUGGESTION,
            "foreshadow": AISuggestionType.FORESHADOW_SUGGESTION,
            "continuity": AISuggestionType.REWRITE_SUGGESTION,
        }
        return mapping.get(category, AISuggestionType.REWRITE_SUGGESTION)

    @staticmethod
    def _map_severity(value: str) -> AISuggestionSeverity:
        mapping = {
            "low": AISuggestionSeverity.LOW,
            "medium": AISuggestionSeverity.MEDIUM,
            "high": AISuggestionSeverity.HIGH,
        }
        return mapping.get(value, AISuggestionSeverity.MEDIUM)

    def _save_decision(
        self,
        item: AISuggestion,
        *,
        decision: AISuggestionDecisionType,
        status: AISuggestionStatus,
        user_id: str,
        note: str = "",
    ) -> AISuggestion:
        now = self._now()
        updated = item.model_copy(
            update={
                "decision": decision,
                "status": status,
                "decided_by": user_id,
                "updated_at": now,
                "decision_log": AISuggestionDecision(
                    suggestion_id=item.suggestion_id,
                    decision=decision,
                    decided_by=user_id,
                    decision_note=note,
                    decided_at=now,
                ),
            }
        )
        saved = self._ai_suggestion_repository.save(updated)
        self._record_trace_decision(saved, decision=decision)
        return saved

    def _candidate_draft_id_from_target(self, target_ref_id: str) -> str:
        version = self._candidate_draft_repository.get_version(target_ref_id)
        return version.candidate_draft_id

    @staticmethod
    def _require_user_action(user_action: bool) -> None:
        if not user_action:
            raise ValueError("action_not_allowed")

    def _record_trace_decision(self, item: AISuggestion, *, decision: AISuggestionDecisionType) -> None:
        if self._trace_service is None or not str(item.trace_id or "").strip():
            return
        event_type = {
            AISuggestionDecisionType.ACCEPTED: "suggestion_accepted",
            AISuggestionDecisionType.DISMISSED: "suggestion_dismissed",
        }.get(decision)
        if not event_type:
            return
        self._trace_service.record_audit_event(
            trace_id=item.trace_id,
            session_id=item.agent_session_id,
            step_id="",
            event_type=event_type,
            summary=item.suggestion_id,
            payload_digest={
                "suggestion_id": item.suggestion_id,
                "suggestion_type": item.suggestion_type.value,
                "target_ref_id": item.target.target_ref_id,
            },
            high_risk_user_action=decision == AISuggestionDecisionType.CONVERTED,
        )

    def _record_outline_user_decision_before_write(
        self,
        *,
        trace_id: str,
        work_id: str,
        chapter_id: str,
        operation_ref: str,
        session_id: str,
        step_id: str,
        summary: str,
        payload_digest: dict[str, str],
    ) -> None:
        if self._trace_service is None or not str(trace_id or "").strip():
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")
        try:
            trace = self._trace_service.ensure_operation_trace(
                trace_id=trace_id,
                work_id=work_id,
                chapter_id=chapter_id,
                operation_ref=operation_ref,
                workflow_type="outline_assist",
            )
            event = self._trace_service.record_audit_event(
                trace_id=trace_id,
                session_id=session_id,
                step_id=step_id,
                event_type="user_decision_recorded",
                summary=summary,
                payload_digest=payload_digest,
                high_risk_user_action=True,
            )
            if trace is None or event is None:
                raise ValueError("audit_record_not_persisted")
        except Exception as exc:
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED") from exc

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _hash_idempotency_key(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
