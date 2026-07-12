from __future__ import annotations

import hashlib
import json
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.output_validation_service import OutputValidationService
from application.services.v1.content_tree_schema import validate_content_tree_json
from domain.entities.ai.models import (
    AIJobStepStatus,
    AIJobStatus,
    AgentTraceStatus,
    AISuggestion,
    AISuggestionAction,
    AISuggestionActionType,
    AISuggestionPriority,
    AISuggestionSeverity,
    AISuggestionSource,
    AISuggestionStatus,
    AISuggestionTarget,
    AISuggestionType,
    DirectionPlanStatus,
    LLMCallStatus,
    LLMRequest,
    LLMUsage,
)
from domain.entities.ai.suggestion_payloads import SuggestionLaunchResult
from domain.repositories.ai.ai_suggestion_repository import AISuggestionRepository
from domain.value_objects.outline_snapshot import outline_content_hash, preserves_outline_node_contract


_CONTRACTS: dict[AISuggestionType, tuple[str, str]] = {
    AISuggestionType.OUTLINE_POLISH: ("outline_polish_v1", "outline_polish_schema"),
    AISuggestionType.OUTLINE_EXPAND: ("outline_expand_v1", "outline_expand_schema"),
    AISuggestionType.CHAPTER_OUTLINE_DETAIL: ("chapter_outline_detail_v1", "chapter_outline_detail_schema"),
    AISuggestionType.WRITING_TASK_SUGGESTION: ("writing_task_suggest_v1", "writing_task_suggestion_schema"),
}

_AUDIT_WRITE_FAILED = "P2_OUTLINE_AUDIT_WRITE_FAILED"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _request_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256(encoded)


class OutlinePlannerService:
    """Controlled Planner boundary for P2-07 model calls and structured validation."""

    def __init__(
        self,
        *,
        model_router,
        output_validator: OutputValidationService,
        prompt_registry,
        llm_call_logger,
    ) -> None:
        self._model_router = model_router
        self._output_validator = output_validator
        self._prompt_registry = prompt_registry
        self._llm_call_logger = llm_call_logger

    def generate(
        self,
        *,
        suggestion_type: AISuggestionType,
        source_text: str,
        target_content_tree_json,
        options: dict[str, object],
        work_id: str,
        trace_id: str,
        session_id: str,
        step_id: str,
    ) -> dict[str, object]:
        if self._llm_call_logger is None or not all(
            str(value or "").strip() for value in (work_id, trace_id, session_id, step_id)
        ):
            raise ValueError(_AUDIT_WRITE_FAILED)
        prompt_key, schema_key = _CONTRACTS[suggestion_type]
        prompt_input = {
            "source_text": str(source_text or ""),
            "target_content_tree_json": target_content_tree_json,
            **options,
        }
        system_prompt = self._render_prompt(prompt_key, prompt_input)
        last_error = "output_schema_invalid"
        for attempt_no in range(1, 4):
            request_id = f"req_oa_{uuid.uuid4().hex[:12]}"
            started_at = datetime.now(UTC)
            try:
                selection = self._model_router.resolve_model("planner")
            except Exception as exc:
                error_code = self._safe_provider_error_code(exc)
                self._record_llm_call(
                    prompt_key=prompt_key,
                    schema_key=schema_key,
                    work_id=work_id,
                    provider_name="",
                    model_name="",
                    request_id=request_id,
                    trace_id=trace_id,
                    session_id=session_id,
                    step_id=step_id,
                    attempt_no=attempt_no,
                    started_at=started_at,
                    status=LLMCallStatus.FAILED,
                    error_code=error_code,
                )
                raise ValueError(error_code) from exc
            request = LLMRequest(
                model_role="planner",
                prompt_key=prompt_key,
                prompt_version="v1",
                output_schema_key=schema_key,
                request_id=request_id,
                trace_id=trace_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(prompt_input, ensure_ascii=False)},
                ],
            )
            try:
                response = self._model_router.generate(request)
            except Exception as exc:
                error_code = self._safe_provider_error_code(exc)
                self._record_llm_call(
                    prompt_key=prompt_key,
                    schema_key=schema_key,
                    work_id=work_id,
                    provider_name=str(selection.provider_name or ""),
                    model_name=str(selection.model_name or ""),
                    request_id=request_id,
                    trace_id=trace_id,
                    session_id=session_id,
                    step_id=step_id,
                    attempt_no=attempt_no,
                    started_at=started_at,
                    status=LLMCallStatus.FAILED,
                    error_code=error_code,
                )
                raise ValueError(error_code) from exc

            error_code = ""
            parsed: dict[str, object] = {}
            try:
                validated = self._output_validator.validate(schema_key, response.content)
                if not validated.success:
                    error_code = validated.error_code or "output_schema_invalid"
                else:
                    parsed = dict(validated.parsed_output or {})
                    if "proposed_content_tree_json" in parsed:
                        parsed["proposed_content_tree_json"] = validate_content_tree_json(
                            parsed.get("proposed_content_tree_json")
                        )
                        if not preserves_outline_node_contract(
                            target_content_tree_json,
                            parsed["proposed_content_tree_json"],
                        ):
                            error_code = "output_schema_invalid"
            except Exception:
                error_code = "output_schema_invalid"

            self._record_llm_call(
                prompt_key=prompt_key,
                schema_key=schema_key,
                work_id=work_id,
                provider_name=str(getattr(response, "provider_name", "") or selection.provider_name or ""),
                model_name=str(getattr(response, "model_name", "") or selection.model_name or ""),
                request_id=request_id,
                trace_id=trace_id,
                session_id=session_id,
                step_id=step_id,
                attempt_no=attempt_no,
                started_at=started_at,
                status=LLMCallStatus.FAILED if error_code else LLMCallStatus.SUCCEEDED,
                usage=getattr(response, "token_usage", None),
                error_code=error_code,
                content_hash=_sha256(getattr(response, "content", "")),
            )
            if error_code:
                last_error = error_code
                continue
            return parsed
        raise ValueError(last_error)

    def _render_prompt(self, prompt_key: str, prompt_input: dict[str, object]) -> str:
        if self._prompt_registry is None:
            raise ValueError("prompt_template_missing")
        return self._prompt_registry.render(
            prompt_key=prompt_key,
            version="v1",
            variables={"input_json": json.dumps(prompt_input, ensure_ascii=False)},
        )

    def _record_llm_call(
        self,
        *,
        prompt_key: str,
        schema_key: str,
        work_id: str,
        provider_name: str,
        model_name: str,
        request_id: str,
        trace_id: str,
        session_id: str,
        step_id: str,
        attempt_no: int,
        started_at: datetime,
        status: LLMCallStatus,
        usage=None,
        error_code: str = "",
        content_hash: str = "",
    ) -> None:
        try:
            self._llm_call_logger.record(
                prompt_key=prompt_key,
                prompt_version="v1",
                work_id=work_id,
                model_role="planner",
                provider_name=str(provider_name or "").strip() or "unresolved",
                model_name=str(model_name or "").strip() or "unresolved",
                request_id=request_id,
                trace_id=trace_id,
                status=status,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                usage=usage if usage is not None else LLMUsage(),
                error_code=error_code,
                error_message=error_code,
                attempt_no=attempt_no,
                output_schema_key=schema_key,
                session_id=session_id,
                step_id=step_id,
                content_hash=content_hash,
            )
        except Exception as exc:
            raise ValueError(_AUDIT_WRITE_FAILED) from exc

    @staticmethod
    def _safe_provider_error_code(exc: Exception) -> str:
        candidate = str(getattr(exc, "error_code", "") or "").strip()
        if candidate and len(candidate) <= 100 and all(
            character.isalnum() or character in {"_", "-", ".", ":"} for character in candidate
        ):
            return candidate
        return "provider_call_failed"


class OutlineAssistService:
    def __init__(
        self,
        *,
        planner_service,
        ai_suggestion_repository: AISuggestionRepository,
        ai_job_service: AIJobService,
        writing_asset_service,
        chapter_plan_repository=None,
        trace_service=None,
        background_submitter: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._planner_service = planner_service
        self._suggestions = ai_suggestion_repository
        self._jobs = ai_job_service
        self._assets = writing_asset_service
        self._chapter_plans = chapter_plan_repository
        self._trace_service = trace_service
        self._background_submitter = background_submitter or self._submit_thread

    def start_polish(
        self,
        *,
        work_id: str,
        target_kind: str,
        target_id: str | None,
        target_revision: int | None,
        selected_text: str | None,
        caller_type: str,
        idempotency_key: str,
    ) -> SuggestionLaunchResult:
        return self._start(
            suggestion_type=AISuggestionType.OUTLINE_POLISH,
            work_id=work_id,
            target_kind=target_kind,
            target_id=target_id,
            target_revision=target_revision,
            selected_text=selected_text,
            caller_type=caller_type,
            idempotency_key=idempotency_key,
            options={},
        )

    def start_expand(
        self,
        *,
        work_id: str,
        target_kind: str,
        target_id: str | None,
        target_revision: int | None,
        selected_text: str | None,
        expand_focus: str | None,
        caller_type: str,
        idempotency_key: str,
    ) -> SuggestionLaunchResult:
        return self._start(
            suggestion_type=AISuggestionType.OUTLINE_EXPAND,
            work_id=work_id,
            target_kind=target_kind,
            target_id=target_id,
            target_revision=target_revision,
            selected_text=selected_text,
            caller_type=caller_type,
            idempotency_key=idempotency_key,
            options={"expand_focus": expand_focus},
        )

    def start_chapter_outline(
        self,
        *,
        work_id: str,
        target_kind: str,
        target_id: str,
        target_revision: int,
        chapter_goal: str | None,
        caller_type: str,
        idempotency_key: str,
    ) -> SuggestionLaunchResult:
        if target_kind != "chapter_outline":
            raise ValueError("P2_OUTLINE_TARGET_REQUIRED")
        return self._start(
            suggestion_type=AISuggestionType.CHAPTER_OUTLINE_DETAIL,
            work_id=work_id,
            target_kind=target_kind,
            target_id=target_id,
            target_revision=target_revision,
            selected_text=None,
            caller_type=caller_type,
            idempotency_key=idempotency_key,
            options={"chapter_goal": str(chapter_goal or "")},
        )

    def start_writing_task_suggestion(
        self,
        *,
        work_id: str,
        chapter_id: str,
        target_revision: int,
        caller_type: str,
        idempotency_key: str,
    ) -> SuggestionLaunchResult:
        plan = self._current_confirmed_plan(work_id, chapter_id)
        prompt_options: dict[str, object] = {
            "chapter_id": chapter_id,
            "chapter_plan_id": plan.chapter_plan_id if plan else "",
        }
        if plan is not None:
            prompt_options.update(
                {
                    "confirmed_plan_summary": str(plan.plan_summary or "")[:2000],
                    "confirmed_plan_items": [
                        {
                            "chapter_goal": str(item.chapter_goal or "")[:500],
                            "conflict_progression": str(item.conflict_progression or "")[:500],
                            "forbidden_items": [str(value)[:200] for value in item.forbidden_items[:20]],
                            "required_beats": [str(value)[:200] for value in item.required_beats[:20]],
                        }
                        for item in plan.plan_items[:10]
                    ],
                    "direction_ref": plan.direction_proposal_id,
                    "selected_option_ref": plan.selected_option_id,
                }
            )
        return self._start(
            suggestion_type=AISuggestionType.WRITING_TASK_SUGGESTION,
            work_id=work_id,
            target_kind="chapter_outline",
            target_id=chapter_id,
            target_revision=target_revision,
            selected_text=None,
            caller_type=caller_type,
            idempotency_key=idempotency_key,
            options=prompt_options,
        )

    def _start(
        self,
        *,
        suggestion_type: AISuggestionType,
        work_id: str,
        target_kind: str,
        target_id: str | None,
        target_revision: int | None,
        selected_text: str | None,
        caller_type: str,
        idempotency_key: str,
        options: dict[str, object],
    ) -> SuggestionLaunchResult:
        self._require_launch_gate(caller_type, idempotency_key)
        base_text, base_tree, actual_revision = self._load_target(
            work_id=work_id,
            target_kind=target_kind,
            target_id=target_id,
            target_revision=target_revision,
            selected_text=selected_text,
        )
        normalized_request = {
            "suggestion_type": suggestion_type.value,
            "work_id": work_id,
            "target_kind": target_kind,
            "target_id": target_id,
            "target_revision": target_revision,
            "selected_text_hash": _sha256(selected_text or ""),
            "options": options,
        }
        fingerprint = _request_hash(normalized_request)
        key_hash = _sha256(idempotency_key.strip())
        prior = self._find_idempotent(work_id, key_hash, fingerprint)
        if prior is not None:
            return SuggestionLaunchResult(
                suggestion_id=prior.suggestion_id,
                job_id=str(prior.metadata.get("job_id") or ""),
            )

        now = _now()
        suggestion_id = f"ais_oa_{uuid.uuid4().hex[:12]}"
        trace_id = f"trace_oa_{uuid.uuid4().hex[:12]}"
        target_hash = outline_content_hash(base_text, base_tree) if target_kind != "selection" else ""
        if suggestion_type == AISuggestionType.WRITING_TASK_SUGGESTION:
            common_payload: dict[str, Any] = {
                "chapter_id": str(options.get("chapter_id") or ""),
                "target_revision": actual_revision,
                "target_content_hash": target_hash,
                "chapter_plan_id": str(options.get("chapter_plan_id") or ""),
                "task_title": "",
                "writing_goal": "",
                "must_include": [],
                "must_not_include": [],
                "target_word_count": 0,
                "tone_guidance": "",
                "required_beats": [],
                "context_summary": "",
            }
        else:
            common_payload = {
                "target_kind": target_kind,
                "target_id": target_id,
                "target_revision": actual_revision,
                "target_content_hash": target_hash,
                "target_content_text": base_text,
                "target_content_tree_json": base_tree,
                "proposed_content_text": "",
                "proposed_content_tree_json": base_tree,
                "diff_summary": [],
                **options,
            }
        suggestion = AISuggestion(
            suggestion_id=suggestion_id,
            work_id=work_id,
            chapter_id=str(target_id or "") if target_kind == "chapter_outline" else "",
            source=AISuggestionSource(
                source_type="outline_assist",
                source_ref_id=suggestion_id,
                source_agent_type="planner",
                source_version_id=str(actual_revision or ""),
            ),
            target=AISuggestionTarget(
                target_type=target_kind,
                target_ref_id=str(target_id or ""),
                target_scope="selection" if target_kind == "selection" else "formal_asset",
                target_snapshot_ref=str(actual_revision or ""),
            ),
            suggestion_type=suggestion_type,
            severity=AISuggestionSeverity.MEDIUM,
            priority=AISuggestionPriority.MEDIUM,
            title=self._title_for(suggestion_type),
            summary="",
            proposed_action="由作者查看后决定是否采用",
            status=AISuggestionStatus.PENDING,
            created_by="planner_agent",
            created_at=now,
            updated_at=now,
            trace_id=trace_id,
            action=AISuggestionAction(
                action_type=(
                    AISuggestionActionType.CREATE_WRITING_TASK
                    if suggestion_type == AISuggestionType.WRITING_TASK_SUGGESTION
                    else AISuggestionActionType.APPLY_OUTLINE
                ),
                requires_user_action=True,
                action_status="pending",
            ),
            payload=common_payload,
            metadata={
                "idempotency_key_hash": key_hash,
                "request_hash": fingerprint,
                "target_content_hash": target_hash,
            },
        )
        self._suggestions.save(suggestion)
        job = self._jobs.create_job(
            job_type="outline_assist",
            work_id=work_id,
            chapter_id=suggestion.chapter_id or None,
            created_by="user_action",
            idempotency_key=key_hash,
            payload={"suggestion_id": suggestion_id, "target_revision": actual_revision, "target_kind": target_kind},
            steps=[{"step_type": "generate_outline_suggestion", "step_name": "Generate outline suggestion"}],
        )
        launched_suggestion = self._suggestions.save(
            suggestion.model_copy(update={"metadata": {**suggestion.metadata, "job_id": job.job_id}})
        )
        step_id = self._jobs.get_job_steps(job.job_id)[0].step_id
        try:
            self._record_generation_trace(
                launched_suggestion,
                step_id=step_id,
                event_type="step_started",
                status=None,
            )
        except Exception:
            self._mark_generation_failed(
                job_id=job.job_id,
                step_id=step_id,
                suggestion=launched_suggestion,
                error_code=_AUDIT_WRITE_FAILED,
            )
            return SuggestionLaunchResult(suggestion_id=suggestion_id, job_id=job.job_id)
        model_source = selected_text if str(selected_text or "").strip() else base_text
        self._background_submitter(
            lambda: self._run_generation(
                job_id=job.job_id,
                step_id=step_id,
                suggestion_id=suggestion_id,
                source_text=str(model_source or ""),
                base_tree=base_tree,
                options={**options, "formal_target_content_text": base_text},
            )
        )
        return SuggestionLaunchResult(suggestion_id=suggestion_id, job_id=job.job_id)

    def _run_generation(
        self,
        *,
        job_id: str,
        step_id: str,
        suggestion_id: str,
        source_text: str,
        base_tree,
        options: dict[str, object],
    ) -> None:
        try:
            job = self._jobs.get_job(job_id)
            if job.status == AIJobStatus.CANCELLED:
                self._close_cancelled_step(job_id, step_id)
                return
            if job.status in {AIJobStatus.QUEUED, AIJobStatus.PAUSED}:
                self._jobs.start_job(job_id)
            self._jobs.mark_step_running(job_id, step_id)
            if self._jobs.get_job(job_id).status == AIJobStatus.CANCELLED:
                self._close_cancelled_step(job_id, step_id)
                return
            suggestion = self._suggestions.get(suggestion_id)
            generated = self._planner_service.generate(
                suggestion_type=suggestion.suggestion_type,
                source_text=source_text,
                target_content_tree_json=base_tree,
                options=options,
                work_id=suggestion.work_id,
                trace_id=suggestion.trace_id,
                session_id=suggestion.suggestion_id,
                step_id=step_id,
            )
            if self._jobs.get_job(job_id).status == AIJobStatus.CANCELLED:
                self._close_cancelled_step(job_id, step_id)
                return
            payload = dict(suggestion.payload)
            payload.update(generated)
            if suggestion.suggestion_type == AISuggestionType.WRITING_TASK_SUGGESTION:
                payload.update(
                    {
                        "chapter_id": suggestion.chapter_id,
                        "target_revision": suggestion.payload.get("target_revision"),
                        "target_content_hash": suggestion.payload.get("target_content_hash", ""),
                        "chapter_plan_id": suggestion.payload.get("chapter_plan_id", ""),
                    }
                )
            updated = suggestion.model_copy(
                update={
                    "payload": payload,
                    "summary": self._summary_for_payload(suggestion.suggestion_type, payload),
                    "status": AISuggestionStatus.GENERATED,
                    "updated_at": _now(),
                }
            )
            with self._jobs.terminal_transition():
                if self._jobs.get_job(job_id).status == AIJobStatus.CANCELLED:
                    self._close_cancelled_step(job_id, step_id)
                    return
                self._record_generation_trace(
                    updated,
                    step_id=step_id,
                    event_type="step_succeeded",
                    status=AgentTraceStatus.COMPLETED,
                    result_ref=f"ai_suggestion:{suggestion_id}",
                )
                if self._jobs.get_job(job_id).status == AIJobStatus.CANCELLED:
                    self._close_cancelled_step(job_id, step_id)
                    return
                self._suggestions.save(updated)
                self._jobs.mark_step_completed(job_id, step_id, summary=f"suggestion:{suggestion_id}")
                self._jobs.mark_job_completed(
                    job_id,
                    result_summary={"suggestion_id": suggestion_id, "status": AISuggestionStatus.GENERATED.value},
                    result_ref=f"ai_suggestion:{suggestion_id}",
                )
        except Exception as exc:
            try:
                if self._jobs.get_job(job_id).status == AIJobStatus.CANCELLED:
                    self._close_cancelled_step(job_id, step_id)
                    return
            except Exception:
                pass
            error_code = self._generation_error_code(exc)
            try:
                suggestion = self._suggestions.get(suggestion_id)
                try:
                    self._record_generation_trace(
                        suggestion,
                        step_id=step_id,
                        event_type="step_failed",
                        status=AgentTraceStatus.FAILED,
                        error_code=error_code,
                    )
                except Exception:
                    error_code = _AUDIT_WRITE_FAILED
                self._mark_generation_failed(
                    job_id=job_id,
                    step_id=step_id,
                    suggestion=suggestion,
                    error_code=error_code,
                )
            except Exception:
                return

    def _mark_generation_failed(
        self,
        *,
        job_id: str,
        step_id: str,
        suggestion: AISuggestion,
        error_code: str,
    ) -> None:
        with self._jobs.terminal_transition():
            if self._jobs.get_job(job_id).status == AIJobStatus.CANCELLED:
                self._close_cancelled_step(job_id, step_id)
                return
            metadata = {**suggestion.metadata, "generation_error_code": error_code}
            self._suggestions.save(
                suggestion.model_copy(
                    update={
                        "status": AISuggestionStatus.FAILED,
                        "metadata": metadata,
                        "updated_at": _now(),
                    }
                )
            )
            self._jobs.mark_step_failed(job_id, step_id, error_code=error_code, error_message=error_code)
            self._jobs.mark_job_failed(job_id, error_code=error_code, error_message=error_code)

    def _close_cancelled_step(self, job_id: str, step_id: str) -> None:
        try:
            step = next(item for item in self._jobs.get_job_steps(job_id) if item.step_id == step_id)
        except (StopIteration, ValueError):
            return
        if step.status in {
            AIJobStepStatus.PENDING,
            AIJobStepStatus.RUNNING,
            AIJobStepStatus.PAUSED,
        }:
            self._jobs.mark_step_skipped(job_id, step_id, reason="job_cancelled")

    @staticmethod
    def _generation_error_code(exc: Exception) -> str:
        error_code = str(exc or "").strip()
        if error_code == _AUDIT_WRITE_FAILED:
            return error_code
        if error_code == "prompt_template_missing":
            return error_code
        if error_code.startswith(("P2_", "output_", "provider_")):
            return error_code
        return "output_schema_invalid"

    def _record_generation_trace(
        self,
        suggestion: AISuggestion,
        *,
        step_id: str,
        event_type: str,
        status: AgentTraceStatus | None,
        result_ref: str = "",
        error_code: str = "",
    ) -> None:
        try:
            self._write_generation_trace(
                suggestion,
                step_id=step_id,
                event_type=event_type,
                status=status,
                result_ref=result_ref,
                error_code=error_code,
            )
        except Exception as exc:
            raise ValueError(_AUDIT_WRITE_FAILED) from exc

    def _write_generation_trace(
        self,
        suggestion: AISuggestion,
        *,
        step_id: str,
        event_type: str,
        status: AgentTraceStatus | None,
        result_ref: str = "",
        error_code: str = "",
    ) -> None:
        if self._trace_service is None:
            raise ValueError(_AUDIT_WRITE_FAILED)
        trace = self._trace_service.ensure_operation_trace(
            trace_id=suggestion.trace_id,
            work_id=suggestion.work_id,
            chapter_id=suggestion.chapter_id,
            operation_ref=suggestion.suggestion_id,
            workflow_type="outline_assist",
        )
        if trace is None:
            raise ValueError(_AUDIT_WRITE_FAILED)
        event = self._trace_service.record_audit_event(
            trace_id=suggestion.trace_id,
            session_id=suggestion.suggestion_id,
            step_id=step_id,
            event_type=event_type,
            summary=suggestion.suggestion_id,
            payload_digest={
                "suggestion_id": suggestion.suggestion_id,
                "suggestion_type": suggestion.suggestion_type.value,
                "target_kind": suggestion.target.target_type,
                "target_id": suggestion.target.target_ref_id,
                "target_revision": suggestion.payload.get("target_revision"),
                "target_content_hash": suggestion.metadata.get("target_content_hash", ""),
                "result_ref": result_ref,
                "error_code": error_code,
            },
            high_risk_user_action=True,
        )
        if event is None:
            raise ValueError(_AUDIT_WRITE_FAILED)
        if status is not None:
            finished = self._trace_service.finish_operation_trace(
                suggestion.trace_id,
                status=status,
                result_ref=result_ref,
                error_code=error_code,
            )
            if finished is None:
                raise ValueError(_AUDIT_WRITE_FAILED)

    def _load_target(
        self,
        *,
        work_id: str,
        target_kind: str,
        target_id: str | None,
        target_revision: int | None,
        selected_text: str | None,
    ) -> tuple[str, object, int | None]:
        if target_kind == "selection":
            if target_id is not None or target_revision is not None or not str(selected_text or "").strip():
                raise ValueError("P2_OUTLINE_TARGET_REQUIRED")
            return str(selected_text), [], None
        if target_id is None or target_revision is None:
            raise ValueError("P2_OUTLINE_TARGET_REQUIRED")
        try:
            if target_kind == "work_outline":
                if target_id != work_id:
                    raise ValueError("P2_OUTLINE_TARGET_NOT_FOUND")
                if not self._assets.is_outline_persisted(target_kind=target_kind, target_id=target_id):
                    raise ValueError("P2_OUTLINE_TARGET_NOT_FOUND")
                outline = self._assets.get_work_outline(target_id)
            elif target_kind == "chapter_outline":
                if not self._assets.chapter_belongs_to_work(chapter_id=target_id, work_id=work_id):
                    raise ValueError("P2_OUTLINE_TARGET_NOT_FOUND")
                if not self._assets.is_outline_persisted(target_kind=target_kind, target_id=target_id):
                    raise ValueError("P2_OUTLINE_TARGET_NOT_FOUND")
                outline = self._assets.get_chapter_outline(target_id)
            else:
                raise ValueError("P2_OUTLINE_TARGET_REQUIRED")
        except ValueError as exc:
            if str(exc).startswith("P2_"):
                raise
            raise ValueError("P2_OUTLINE_TARGET_NOT_FOUND") from exc
        if int(outline.version) != int(target_revision):
            raise ValueError("P2_OUTLINE_TARGET_CONFLICT")
        return str(outline.content_text or ""), outline.content_tree_json, int(outline.version)

    def _current_confirmed_plan(self, work_id: str, chapter_id: str):
        if self._chapter_plans is None:
            return None
        for plan in self._chapter_plans.list_by_work(work_id, chapter_id=chapter_id):
            if plan.status in {DirectionPlanStatus.CONFIRMED, DirectionPlanStatus.EDITED} and plan.stale_status == "fresh":
                return plan
        return None

    def _find_idempotent(self, work_id: str, key_hash: str, fingerprint: str) -> AISuggestion | None:
        for item in self._suggestions.list_suggestions(work_id=work_id):
            if item.metadata.get("idempotency_key_hash") != key_hash:
                continue
            if item.metadata.get("request_hash") != fingerprint:
                raise ValueError("P2_IDEMPOTENCY_CONFLICT")
            return item
        return None

    @staticmethod
    def _require_launch_gate(caller_type: str, idempotency_key: str) -> None:
        if caller_type != "user_action":
            raise ValueError("P2_CALLER_FORBIDDEN")
        if not str(idempotency_key or "").strip():
            raise ValueError("P2_IDEMPOTENCY_KEY_REQUIRED")

    @staticmethod
    def _submit_thread(callback: Callable[[], None]) -> None:
        threading.Thread(target=callback, daemon=True).start()

    @staticmethod
    def _title_for(suggestion_type: AISuggestionType) -> str:
        return {
            AISuggestionType.OUTLINE_POLISH: "把这段写顺",
            AISuggestionType.OUTLINE_EXPAND: "把这段补完整",
            AISuggestionType.CHAPTER_OUTLINE_DETAIL: "本章细纲建议",
            AISuggestionType.WRITING_TASK_SUGGESTION: "本章写作要点",
        }[suggestion_type]

    @staticmethod
    def _summary_for_payload(suggestion_type: AISuggestionType, payload: dict[str, object]) -> str:
        if suggestion_type == AISuggestionType.WRITING_TASK_SUGGESTION:
            return str(payload.get("task_title") or payload.get("writing_goal") or "写作要点已整理")[:200]
        return "；".join(str(item) for item in list(payload.get("diff_summary") or [])[:3])[:200]
