from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.output_validation_service import OutputValidationService
from domain.entities.ai.models import AIJobStatus
from domain.entities.ai.models import (
    LLMRequest,
    SelectionRewriteCandidate,
    SelectionRewriteMode,
    SelectionRewriteStatus,
)
from domain.repositories.ai.selection_rewrite_repository import SelectionRewriteRepository
from domain.services.ai.provider import AIInfraError


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_utc(value: str) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolve_mode_contract(mode: SelectionRewriteMode) -> dict[str, str]:
    contract_map = {
        SelectionRewriteMode.EXPAND: {
            "model_role": "writer",
            "prompt_key": "selection_expand_v1",
        },
        SelectionRewriteMode.REWRITE: {
            "model_role": "writer",
            "prompt_key": "selection_rewrite_v1",
        },
        SelectionRewriteMode.ABBREVIATE: {
            "model_role": "writer",
            "prompt_key": "selection_abbreviate_v1",
        },
        SelectionRewriteMode.POLISH: {
            "model_role": "rewriter",
            "prompt_key": "selection_polish_v1",
        },
        SelectionRewriteMode.DIALOGUE_OPT: {
            "model_role": "rewriter",
            "prompt_key": "selection_dialogue_opt_v1",
        },
        SelectionRewriteMode.DE_AI: {
            "model_role": "rewriter",
            "prompt_key": "selection_de_ai_v1",
        },
    }
    return contract_map[mode]


def _matches_mode_constraint(mode: SelectionRewriteMode, source_text: str, rewritten_text: str) -> bool:
    source_length = max(1, len(str(source_text or "").strip()))
    rewritten_length = len(str(rewritten_text or "").strip())
    ratio = rewritten_length / source_length
    if mode == SelectionRewriteMode.EXPAND:
        return 1.5 <= ratio <= 3.0
    if mode == SelectionRewriteMode.ABBREVIATE:
        return 0.3 <= ratio <= 0.8
    return True


def _snapshot_context_before(value: str) -> str:
    return str(value or "")[-100:]


def _snapshot_context_after(value: str) -> str:
    return str(value or "")[:100]


class SelectionRewriteService:
    def __init__(
        self,
        *,
        rewrite_repository: SelectionRewriteRepository,
        job_service: AIJobService | None = None,
        model_router=None,
        prompt_registry=None,
    ) -> None:
        self._rewrite_repository = rewrite_repository
        self._job_service = job_service
        self._model_router = model_router
        self._prompt_registry = prompt_registry
        self._output_validation_service = OutputValidationService()
        self._history_expire_after = timedelta(hours=24)

    async def rewrite(
        self,
        *,
        work_id: str,
        chapter_id: str,
        chapter_revision: int,
        draft_revision: int,
        draft_text_hash: str,
        draft_length: int,
        source_text: str,
        source_hash: str,
        start_pos: int,
        end_pos: int,
        context_before: str = "",
        context_after: str = "",
        mode: SelectionRewriteMode,
        caller_type: str = "user_action",
    ) -> SelectionRewriteCandidate:
        if caller_type and caller_type != "user_action":
            raise ValueError("caller_type_forbidden")
        normalized_source = str(source_text or "")
        if start_pos < 0 or end_pos <= start_pos or end_pos > int(draft_length or 0):
            raise ValueError("invalid_selection_range")
        if len(normalized_source) < 2:
            raise ValueError("selection_too_short")
        if len(normalized_source) > 3000:
            raise ValueError("selection_too_long")
        if not str(draft_text_hash or "").strip():
            raise ValueError("draft_snapshot_invalid")
        if sha256(normalized_source.encode("utf-8")).hexdigest() != str(source_hash or ""):
            raise ValueError("source_hash_mismatch")

        mode_contract = _resolve_mode_contract(mode)
        now = _utc_now()
        candidate = SelectionRewriteCandidate(
            rewrite_id=f"srw_{uuid4().hex[:12]}",
            chapter_id=str(chapter_id or ""),
            work_id=str(work_id or ""),
            rewrite_mode=mode,
            source_text=normalized_source,
            source_hash=str(source_hash or ""),
            source_start_pos=int(start_pos or 0),
            source_end_pos=int(end_pos or 0),
            rewritten_text="",
            applied_text="",
            word_count_before=len(normalized_source),
            word_count_after=0,
            diff_summary="",
            status=SelectionRewriteStatus.GENERATING,
            model_role=mode_contract["model_role"],
            chapter_revision=int(chapter_revision or 0),
            draft_revision=int(draft_revision or 0),
            draft_text_hash=str(draft_text_hash or ""),
            draft_length=int(draft_length or 0),
            edited_before_apply=False,
            context_before=_snapshot_context_before(context_before),
            context_after=_snapshot_context_after(context_after),
            created_at=now,
            applied_at="",
        )
        saved = self._rewrite_repository.save(candidate)
        self._submit_generation(
            saved,
            prompt_context_before=str(context_before or ""),
            prompt_context_after=str(context_after or ""),
        )
        return saved

    async def get_candidate(self, rewrite_id: str) -> SelectionRewriteCandidate:
        candidate = self._rewrite_repository.get(str(rewrite_id or ""))
        if candidate is None:
            raise ValueError("selection_rewrite_not_found")
        return self._expire_candidate_if_needed(candidate)

    async def list_candidates_by_chapter(self, chapter_id: str) -> list[SelectionRewriteCandidate]:
        items = self._rewrite_repository.list_by_chapter(str(chapter_id or ""))
        return [self._expire_candidate_if_needed(item) for item in items]

    async def clear_chapter_history(self, chapter_id: str) -> dict[str, object]:
        cleared = self._rewrite_repository.delete_by_chapter(str(chapter_id or ""))
        return {
            "chapter_id": str(chapter_id or ""),
            "cleared_count": cleared,
        }

    async def apply(
        self,
        rewrite_id: str,
        *,
        final_text: str | None = None,
        chapter_revision: int,
        draft_revision: int,
        draft_text_hash: str,
        draft_length: int,
        range_text: str,
        caller_type: str = "user_action",
    ) -> dict[str, object]:
        if caller_type and caller_type != "user_action":
            raise ValueError("caller_type_forbidden")
        candidate = await self.get_candidate(rewrite_id)
        if candidate.status != SelectionRewriteStatus.PENDING:
            raise ValueError("status_not_pending")
        if int(chapter_revision or 0) != candidate.chapter_revision:
            raise ValueError("selection_conflict")
        if int(draft_revision or 0) != candidate.draft_revision:
            raise ValueError("selection_conflict")
        if str(draft_text_hash or "") != candidate.draft_text_hash:
            raise ValueError("selection_conflict")
        if int(draft_length or 0) < candidate.source_end_pos:
            raise ValueError("selection_conflict")
        if str(range_text or "") != candidate.source_text:
            raise ValueError("selection_text_mismatch")
        replacement = str(final_text) if final_text is not None and str(final_text) != "" else candidate.rewritten_text
        updated = candidate.model_copy(
            update={
                "applied_text": replacement,
                "edited_before_apply": bool(final_text),
                "status": SelectionRewriteStatus.APPLIED,
                "applied_at": _utc_now(),
            }
        )
        self._rewrite_repository.save(updated)
        return {
            "rewrite_id": updated.rewrite_id,
            "status": updated.status.value,
            "patch": {
                "range": [updated.source_start_pos, updated.source_end_pos],
                "replacement": replacement,
            },
            "applied_text": replacement,
        }

    async def reject(self, rewrite_id: str) -> SelectionRewriteCandidate:
        candidate = await self.get_candidate(rewrite_id)
        updated = candidate.model_copy(update={"status": SelectionRewriteStatus.REJECTED})
        return self._rewrite_repository.save(updated)

    def _generate_candidate(
        self,
        candidate: SelectionRewriteCandidate,
        *,
        prompt_context_before: str = "",
        prompt_context_after: str = "",
    ) -> SelectionRewriteCandidate:
        if self._model_router is None:
            return candidate
        mode_contract = _resolve_mode_contract(candidate.rewrite_mode)
        try:
            response = self._model_router.generate(
                LLMRequest(
                    model_role=mode_contract["model_role"],
                    prompt_key=mode_contract["prompt_key"],
                    prompt_version="v1",
                    output_schema_key="selection_rewrite_schema",
                    request_id=candidate.request_id or f"req_{uuid4().hex[:12]}",
                    trace_id=candidate.trace_id or f"trace_{uuid4().hex[:12]}",
                    messages=self._build_messages(
                        candidate,
                        prompt_context_before=prompt_context_before,
                        prompt_context_after=prompt_context_after,
                    ),
                )
            )
            validation = self._output_validation_service.validate("selection_rewrite_schema", response.content)
            if not validation.success:
                failed = candidate.model_copy(
                    update={
                        "status": SelectionRewriteStatus.FAILED,
                        "error_code": validation.error_code,
                        "error_message": validation.message,
                    }
                )
                return self._rewrite_repository.save(failed)
            parsed_output = validation.parsed_output or {}
            rewritten_text = str(parsed_output.get("rewritten_text") or "").strip()
            if not _matches_mode_constraint(candidate.rewrite_mode, candidate.source_text, rewritten_text):
                failed = candidate.model_copy(
                    update={
                        "status": SelectionRewriteStatus.FAILED,
                        "error_code": "output_schema_invalid",
                        "error_message": "selection_rewrite_mode_constraint_invalid",
                    }
                )
                return self._rewrite_repository.save(failed)
            completed = candidate.model_copy(
                update={
                    "status": SelectionRewriteStatus.PENDING,
                    "rewritten_text": rewritten_text,
                    "word_count_after": len(rewritten_text),
                    "diff_summary": str(parsed_output.get("diff_summary") or ""),
                }
            )
            return self._rewrite_repository.save(completed)
        except (AIInfraError, ValueError) as exc:
            failed = candidate.model_copy(
                update={
                    "status": SelectionRewriteStatus.FAILED,
                    "error_code": getattr(exc, "error_code", str(exc)),
                    "error_message": str(exc),
                }
            )
            return self._rewrite_repository.save(failed)

    @staticmethod
    def _build_fallback_system_prompt(candidate: SelectionRewriteCandidate) -> str:
        return f"请执行选区改写，模式={candidate.rewrite_mode.value}，仅输出包含 rewritten_text、diff_summary、risk_notes 的 JSON。"

    def _build_messages(
        self,
        candidate: SelectionRewriteCandidate,
        *,
        prompt_context_before: str = "",
        prompt_context_after: str = "",
    ) -> list[dict[str, str]]:
        system_prompt = self._build_fallback_system_prompt(candidate)
        mode_contract = _resolve_mode_contract(candidate.rewrite_mode)
        resolved_context_before = str(prompt_context_before or candidate.context_before or "")
        resolved_context_after = str(prompt_context_after or candidate.context_after or "")
        if self._prompt_registry is not None:
            try:
                system_prompt = self._prompt_registry.render(
                    prompt_key=mode_contract["prompt_key"],
                    version="v1",
                    variables={
                        "source_text": candidate.source_text,
                        "context_before": resolved_context_before,
                        "context_after": resolved_context_after,
                    },
                )
            except ValueError:
                system_prompt = self._build_fallback_system_prompt(candidate)
        return [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": candidate.source_text,
            },
        ]

    def _submit_generation(
        self,
        candidate: SelectionRewriteCandidate,
        *,
        prompt_context_before: str = "",
        prompt_context_after: str = "",
    ) -> None:
        if self._job_service is None:
            self._generate_candidate(
                candidate,
                prompt_context_before=prompt_context_before,
                prompt_context_after=prompt_context_after,
            )
            return
        job = self._job_service.create_job(
            job_type="selection_rewrite",
            work_id=candidate.work_id,
            chapter_id=candidate.chapter_id,
            created_by="user_action",
            payload={"rewrite_id": candidate.rewrite_id},
            steps=[{"step_type": "generate_selection_rewrite", "step_name": "Generate Selection Rewrite"}],
        )
        self._rewrite_repository.save(
            candidate.model_copy(
                update={
                    "request_id": job.job_id,
                }
            )
        )
        thread = threading.Thread(
            target=self._run_generation_job,
            args=(job.job_id, candidate.rewrite_id, prompt_context_before, prompt_context_after),
            daemon=True,
        )
        thread.start()

    def _expire_candidate_if_needed(self, candidate: SelectionRewriteCandidate) -> SelectionRewriteCandidate:
        if candidate.status != SelectionRewriteStatus.PENDING:
            return candidate
        created_at = _parse_utc(candidate.created_at)
        if created_at is None:
            return candidate
        if datetime.now(UTC) - created_at <= self._history_expire_after:
            return candidate
        expired = candidate.model_copy(
            update={
                "status": SelectionRewriteStatus.EXPIRED,
                "error_code": candidate.error_code or "selection_rewrite_expired",
                "error_message": candidate.error_message or "selection_rewrite_expired",
            }
        )
        return self._rewrite_repository.save(expired)

    def _run_generation_job(
        self,
        job_id: str,
        rewrite_id: str,
        prompt_context_before: str = "",
        prompt_context_after: str = "",
    ) -> None:
        if self._job_service is None:
            return
        try:
            job = self._job_service.get_job(job_id)
            if job.status in {AIJobStatus.QUEUED, AIJobStatus.PAUSED}:
                self._job_service.start_job(job_id)
            step = self._job_service.get_job_steps(job_id)[0]
            self._job_service.mark_step_running(job_id, step.step_id)
            candidate = self._rewrite_repository.get(str(rewrite_id or ""))
            if candidate is None:
                raise ValueError("selection_rewrite_not_found")
            generated = self._generate_candidate(
                candidate,
                prompt_context_before=prompt_context_before,
                prompt_context_after=prompt_context_after,
            )
            if generated.status == SelectionRewriteStatus.FAILED:
                self._job_service.mark_step_failed(
                    job_id,
                    step.step_id,
                    error_code=generated.error_code or "selection_rewrite_generation_failed",
                    error_message=generated.error_message or generated.error_code or "selection_rewrite_generation_failed",
                )
                self._job_service.mark_job_failed(
                    job_id,
                    error_code=generated.error_code or "selection_rewrite_generation_failed",
                    error_message=generated.error_message or generated.error_code or "selection_rewrite_generation_failed",
                )
                return
            self._job_service.mark_step_completed(job_id, step.step_id, summary=f"rewrite:{generated.rewrite_id}")
            self._job_service.mark_job_completed(
                job_id,
                result_summary={"rewrite_id": generated.rewrite_id, "status": generated.status.value},
                result_ref=generated.rewrite_id,
            )
        except Exception as exc:
            self._job_service.mark_job_failed(
                job_id,
                error_code="selection_rewrite_generation_failed",
                error_message=str(exc),
            )
