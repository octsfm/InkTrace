from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

from application.services.ai.output_validation_service import OutputValidationService
from application.services.ai.writer_service import WriterService
from domain.entities.ai.models import (
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
    ContextPackBuildRequest,
)


@dataclass(slots=True)
class ToolExecutionContext:
    caller_type: str
    work_id: str = ""
    chapter_id: str = ""
    request_id: str = ""
    trace_id: str = ""
    side_effect_level: str = ""
    idempotency_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolError:
    error_code: str
    safe_message: str
    retryable: bool
    user_visible: bool
    debug_ref: str
    source_tool: str
    source_service: str
    occurred_at: str


@dataclass(slots=True)
class ToolResultEnvelope:
    ok: bool
    tool_name: str
    payload: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: ToolError | None = None
    request_id: str = ""
    trace_id: str = ""

    @property
    def error_code(self) -> str:
        return self.error.error_code if self.error else ""

    @property
    def safe_message(self) -> str:
        return self.error.safe_message if self.error else ""


@dataclass(slots=True)
class ToolDefinition:
    tool_name: str
    allowed_callers: set[str]
    side_effect_level: str
    enabled: bool = True
    source_service: str = "core_tool_facade"


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._definitions[definition.tool_name] = definition

    def get(self, tool_name: str) -> ToolDefinition | None:
        return self._definitions.get(tool_name)

    def all(self) -> dict[str, ToolDefinition]:
        return dict(self._definitions)


class ToolPermissionPolicy:
    _USER_ACTION_ONLY = {"accept_candidate_draft", "reject_candidate_draft", "apply_candidate_to_draft"}
    _FORMAL_WRITE_FORBIDDEN = {"formal_chapter_write"}

    def is_allowed(self, *, definition: ToolDefinition, caller_type: str) -> bool:
        if definition.tool_name in self._FORMAL_WRITE_FORBIDDEN:
            return False
        return caller_type in definition.allowed_callers

    def is_reserved_denied(self, *, tool_name: str, caller_type: str) -> bool:
        if tool_name in self._FORMAL_WRITE_FORBIDDEN:
            return True
        if tool_name in self._USER_ACTION_ONLY and caller_type != "user_action":
            return True
        return False


class CoreToolFacade:
    def __init__(
        self,
        *,
        context_pack_service,
        candidate_draft_repository,
        writer,
        job_service=None,
    ) -> None:
        self._context_pack_service = context_pack_service
        self._candidate_draft_repository = candidate_draft_repository
        self._writer_service = WriterService(writer)
        self._job_service = job_service
        self._output_validation_service = OutputValidationService()
        self._permission_policy = ToolPermissionPolicy()
        self._registry = ToolRegistry()
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self.audit_logs: list[dict[str, Any]] = []
        self._register_builtin_tools()

    def register_tool(self, definition: ToolDefinition, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self._registry.register(definition)
        self._handlers[definition.tool_name] = handler

    def call(self, tool_name: str, *, context: ToolExecutionContext, payload: dict[str, Any]) -> ToolResultEnvelope:
        if self._permission_policy.is_reserved_denied(tool_name=tool_name, caller_type=context.caller_type):
            envelope = self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_permission_denied",
                safe_message="tool_permission_denied",
                retryable=False,
                user_visible=True,
                source_service="tool_permission_policy",
            )
            self._record_audit(tool_name, context, envelope)
            return envelope
        definition = self._registry.get(tool_name)
        if definition is None:
            envelope = self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_not_registered",
                safe_message="tool_not_registered",
                retryable=False,
                user_visible=True,
                source_service="tool_registry",
            )
            self._record_audit(tool_name, context, envelope)
            return envelope
        if not definition.enabled:
            envelope = self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_disabled",
                safe_message="tool_disabled",
                retryable=False,
                user_visible=True,
                source_service=definition.source_service,
            )
            self._record_audit(tool_name, context, envelope)
            return envelope
        if not self._permission_policy.is_allowed(definition=definition, caller_type=context.caller_type):
            envelope = self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_permission_denied",
                safe_message="tool_permission_denied",
                retryable=False,
                user_visible=True,
                source_service=definition.source_service,
            )
            self._record_audit(tool_name, context, envelope)
            return envelope

        try:
            result = self._handlers[tool_name](payload)
        except Exception as exc:  # noqa: BLE001
            error_code = str(exc) or "tool_execution_failed"
            envelope = self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code=error_code,
                safe_message=error_code,
                retryable=False,
                user_visible=True,
                source_service=definition.source_service,
            )
            self._record_audit(tool_name, context, envelope)
            return envelope

        envelope = ToolResultEnvelope(
            ok=True,
            tool_name=tool_name,
            payload=result,
            warnings=list(result.get("warnings", [])) if isinstance(result, dict) else [],
            request_id=context.request_id,
            trace_id=context.trace_id,
        )
        self._record_audit(tool_name, context, envelope)
        return envelope

    def _build_context_pack(self, payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = self._context_pack_service.build_and_save(
            ContextPackBuildRequest(
                work_id=str(payload.get("work_id", "")),
                chapter_id=str(payload.get("chapter_id", "")),
                user_instruction=str(payload.get("user_instruction", "")),
                continuation_mode=str(payload.get("continuation_mode", "continue_chapter")),
                model_role=str(payload.get("model_role", "writer")),
            )
        )
        return {
            "context_pack": snapshot,
            "warnings": list(snapshot.warnings),
        }

    def _generate_candidate_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        writer_output = self._writer_service.generate_candidate_text(
            context_pack=payload["context_pack"],
            writing_task=payload["writing_task"],
        )
        return {"writer_output": writer_output}

    def _validate_writer_output(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_output = str(payload.get("content", ""))
        validation = self._output_validation_service.validate("plain_text", raw_output)
        if not validation.success:
            raise ValueError("writer_output_invalid")
        text = str(validation.parsed_output or "").strip()
        lowered = text.lower()
        if len(text) < 20 or len(text) > 5000:
            raise ValueError("writer_output_invalid")
        if lowered in {"todo", "tbd", "placeholder"}:
            raise ValueError("writer_output_invalid")
        if "traceback" in lowered or "exception" in lowered:
            raise ValueError("writer_output_invalid")
        return {"validated_content": text}

    def _save_candidate_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        content = str(payload.get("content", "")).strip()
        draft = CandidateDraft(
            candidate_draft_id=str(payload["candidate_draft_id"]),
            work_id=str(payload["work_id"]),
            chapter_id=str(payload["chapter_id"]),
            source_context_pack_id=str(payload["source_context_pack_id"]),
            source_job_id=str(payload["source_job_id"]),
            status=CandidateDraftStatus.PENDING_REVIEW,
            content=content,
            content_preview=content[:120],
            word_count=max(1, len(re.findall(r"\S+", content))),
            char_count=len(content),
            validation_status=CandidateDraftValidationStatus.PASSED,
            writer_model_role=str(payload.get("writer_model_role", "writer")),
            provider_name=str(payload.get("provider_name", "")),
            model_name=str(payload.get("model_name", "")),
            created_by=str(payload.get("created_by", "workflow")),
            created_at=self._now(),
            updated_at=self._now(),
            metadata=dict(payload.get("metadata", {})),
        )
        saved = self._candidate_draft_repository.save(draft)
        return {"candidate_draft": saved}

    def _get_candidate_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        draft = self._candidate_draft_repository.get(str(payload["candidate_draft_id"]))
        return {"candidate_draft": draft}

    def _update_job_step_progress(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._job_service is None:
            raise ValueError("job_service_not_available")
        status = str(payload.get("status", ""))
        job_id = str(payload["job_id"])
        step_id = str(payload["step_id"])
        if status == "running":
            step = self._job_service.mark_step_running(job_id, step_id)
        elif status == "skipped":
            step = self._job_service.mark_step_skipped(job_id, step_id, reason=str(payload.get("reason", "")))
        else:
            raise ValueError("job_step_status_not_supported")
        return {"job_step": step}

    def _mark_job_step_failed(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._job_service is None:
            raise ValueError("job_service_not_available")
        step = self._job_service.mark_step_failed(
            str(payload["job_id"]),
            str(payload["step_id"]),
            error_code=str(payload.get("error_code", "tool_execution_failed")),
            error_message=str(payload.get("error_message", "")),
        )
        return {"job_step": step}

    def _mark_job_step_completed(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._job_service is None:
            raise ValueError("job_service_not_available")
        step = self._job_service.mark_step_completed(
            str(payload["job_id"]),
            str(payload["step_id"]),
            summary=str(payload.get("summary", "")),
        )
        return {"job_step": step}

    def _mark_job_failed(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._job_service is None:
            raise ValueError("job_service_not_available")
        job = self._job_service.mark_job_failed(
            str(payload["job_id"]),
            error_code=str(payload.get("error_code", "tool_execution_failed")),
            error_message=str(payload.get("error_message", "")),
        )
        return {"job": job}

    def _mark_job_completed(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._job_service is None:
            raise ValueError("job_service_not_available")
        job = self._job_service.mark_job_completed(
            str(payload["job_id"]),
            result_summary=dict(payload.get("result_summary", {})),
            result_ref=str(payload.get("result_ref", "")),
        )
        return {"job": job}

    def _get_job_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._job_service is None:
            raise ValueError("job_service_not_available")
        job = self._job_service.get_job(str(payload["job_id"]))
        return {"job": job, "steps": self._job_service.get_job_steps(job.job_id)}

    def _register_builtin_tools(self) -> None:
        self.register_tool(
            ToolDefinition(
                tool_name="build_context_pack",
                allowed_callers={"workflow", "ai", "quick_trial", "user_action"},
                side_effect_level="plan_write",
                source_service="context_pack_service",
            ),
            self._build_context_pack,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="run_writer_step",
                allowed_callers={"workflow", "ai"},
                side_effect_level="safe_write_candidate",
                source_service="writer_service",
            ),
            self._generate_candidate_text,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="validate_writer_output",
                allowed_callers={"workflow", "ai"},
                side_effect_level="read_only",
                source_service="output_validation_service",
            ),
            self._validate_writer_output,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="save_candidate_draft",
                allowed_callers={"workflow", "ai"},
                side_effect_level="safe_write_candidate",
                source_service="candidate_draft_repository",
            ),
            self._save_candidate_draft,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="get_candidate_draft",
                allowed_callers={"workflow", "ai", "user_action"},
                side_effect_level="read_only",
                source_service="candidate_draft_repository",
            ),
            self._get_candidate_draft,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="update_job_step_progress",
                allowed_callers={"workflow", "ai"},
                side_effect_level="trace_only",
                source_service="ai_job_service",
            ),
            self._update_job_step_progress,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="mark_job_step_failed",
                allowed_callers={"workflow", "ai"},
                side_effect_level="trace_only",
                source_service="ai_job_service",
            ),
            self._mark_job_step_failed,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="mark_job_step_completed",
                allowed_callers={"workflow", "ai"},
                side_effect_level="trace_only",
                source_service="ai_job_service",
            ),
            self._mark_job_step_completed,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="mark_job_failed",
                allowed_callers={"workflow", "ai"},
                side_effect_level="trace_only",
                source_service="ai_job_service",
            ),
            self._mark_job_failed,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="mark_job_completed",
                allowed_callers={"workflow", "ai"},
                side_effect_level="trace_only",
                source_service="ai_job_service",
            ),
            self._mark_job_completed,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="get_job_status",
                allowed_callers={"workflow", "ai", "user_action"},
                side_effect_level="read_only",
                source_service="ai_job_service",
            ),
            self._get_job_status,
        )

    def _error_envelope(
        self,
        *,
        tool_name: str,
        context: ToolExecutionContext,
        error_code: str,
        safe_message: str,
        retryable: bool,
        user_visible: bool,
        source_service: str,
    ) -> ToolResultEnvelope:
        return ToolResultEnvelope(
            ok=False,
            tool_name=tool_name,
            error=ToolError(
                error_code=error_code,
                safe_message=safe_message,
                retryable=retryable,
                user_visible=user_visible,
                debug_ref=f"toolerr_{uuid.uuid4().hex[:12]}",
                source_tool=tool_name,
                source_service=source_service,
                occurred_at=self._now(),
            ),
            request_id=context.request_id,
            trace_id=context.trace_id,
        )

    def _record_audit(self, tool_name: str, context: ToolExecutionContext, envelope: ToolResultEnvelope) -> None:
        self.audit_logs.append(
            {
                "tool_name": tool_name,
                "caller_type": context.caller_type,
                "side_effect_level": context.side_effect_level,
                "request_id": context.request_id,
                "trace_id": context.trace_id,
                "ok": envelope.ok,
                "error_code": envelope.error_code,
                "warnings": list(envelope.warnings),
                "logged_at": self._now(),
            }
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
