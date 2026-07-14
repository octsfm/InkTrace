from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

from application.services.ai.agent_profile_registry import build_default_agent_profile_registry
from application.services.ai.output_validation_service import OutputValidationService
from application.services.ai.writer_service import WriterService
from domain.entities.ai.models import (
    AISuggestion,
    AISuggestionAction,
    AISuggestionActionType,
    AISuggestionPriority,
    AISuggestionSeverity,
    AISuggestionSource,
    AISuggestionStatus,
    AISuggestionTarget,
    AISuggestionType,
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftVersion,
    CandidateDraftVersionStatus,
    CandidateDraftValidationStatus,
    ChapterPlan,
    DirectionPlanStatus,
    ContextPackBuildRequest,
    DirectionProposal,
    WritingTask,
    WritingTaskStatus,
)


@dataclass(slots=True)
class ToolExecutionContext:
    caller_type: str
    work_id: str = ""
    chapter_id: str = ""
    request_id: str = ""
    trace_id: str = ""
    agent_session_id: str = ""
    agent_step_id: str = ""
    agent_type: str = ""
    session_status: str = ""
    step_status: str = ""
    resource_scope_refs: list[str] = field(default_factory=list)
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
    tool_audit_log_ref: str = ""

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
        ai_suggestion_repository=None,
        chapter_plan_repository=None,
        direction_plan_repository=None,
        story_memory_repository=None,
        story_state_repository=None,
        ai_review_service=None,
        candidate_rewrite_service=None,
        writer,
        job_service=None,
        planning_generation_service=None,
        agent_profile_registry=None,
        trace_service=None,
    ) -> None:
        self._context_pack_service = context_pack_service
        self._candidate_draft_repository = candidate_draft_repository
        self._planning_generation_service = planning_generation_service
        self._ai_suggestion_repository = ai_suggestion_repository
        self._chapter_plan_repository = chapter_plan_repository
        self._direction_plan_repository = direction_plan_repository
        self._story_memory_repository = story_memory_repository
        self._story_state_repository = story_state_repository
        self._ai_review_service = ai_review_service
        self._candidate_rewrite_service = candidate_rewrite_service
        self._writer_service = WriterService(writer)
        self._job_service = job_service
        self._trace_service = trace_service
        self._output_validation_service = OutputValidationService()
        self._permission_policy = ToolPermissionPolicy()
        self._agent_profile_registry = agent_profile_registry or build_default_agent_profile_registry()
        self._registry = ToolRegistry()
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self.audit_logs: list[dict[str, Any]] = []
        self._register_builtin_tools()

    def register_tool(self, definition: ToolDefinition, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self._registry.register(definition)
        self._handlers[definition.tool_name] = handler

    def call(self, tool_name: str, *, context: ToolExecutionContext, payload: dict[str, Any]) -> ToolResultEnvelope:
        if not self._is_valid_context(context):
            envelope = self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_context_invalid",
                safe_message="tool_context_invalid",
                retryable=False,
                user_visible=True,
                source_service="tool_execution_context",
            )
            self._record_audit(tool_name, context, envelope)
            return envelope
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
        if not self._is_valid_definition_context(definition, context):
            envelope = self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_context_invalid",
                safe_message="tool_context_invalid",
                retryable=False,
                user_visible=True,
                source_service="tool_execution_context",
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
        if context.caller_type == "agent":
            envelope = self._validate_agent_tool_permission(tool_name=tool_name, context=context)
            if envelope is not None:
                self._record_audit(tool_name, context, envelope)
                return envelope

        try:
            result = self._execute_handler(tool_name, payload=payload, context=context)
        except Exception as exc:  # noqa: BLE001
            error_code = str(exc) or "tool_execution_failed"
            envelope = self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code=error_code,
                safe_message=error_code,
                retryable=self._is_retryable_error(error_code),
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

    def _execute_handler(
        self,
        tool_name: str,
        *,
        payload: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        if tool_name == "create_direction_proposal":
            return self._create_direction_proposal(payload, context=context)
        if tool_name == "create_chapter_plan":
            return self._create_chapter_plan(payload, context=context)
        if tool_name == "get_story_memory_snapshot":
            return self._get_story_memory_snapshot(payload, context=context)
        if tool_name == "get_story_state_baseline":
            return self._get_story_state_baseline(payload, context=context)
        if tool_name == "run_writer_step":
            return self._run_writer_step(payload, context=context)
        if tool_name == "create_review_report":
            return self._create_review_report(payload, context=context)
        if tool_name == "create_candidate_version":
            return self._create_candidate_version(payload, context=context)
        return self._handlers[tool_name](payload)

    def _validate_agent_tool_permission(
        self,
        *,
        tool_name: str,
        context: ToolExecutionContext,
    ) -> ToolResultEnvelope | None:
        try:
            profile = self._agent_profile_registry.require_profile(context.agent_type)
            permission = self._agent_profile_registry.get_permission(context.agent_type, tool_name)
        except ValueError:
            return self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_permission_denied",
                safe_message="tool_permission_denied",
                retryable=False,
                user_visible=True,
                source_service="agent_profile_registry",
            )
        if tool_name in profile.denied_tool_names or permission.requires_user_action:
            return self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_permission_denied",
                safe_message="tool_permission_denied",
                retryable=False,
                user_visible=True,
                source_service="agent_profile_registry",
            )
        if tool_name in profile.allowed_tool_names:
            return None
        if permission.permission.value == "deny" and tool_name in {
            "accept_candidate_draft",
            "reject_candidate_draft",
            "apply_candidate_to_draft",
            "formal_chapter_write",
        }:
            return self._error_envelope(
                tool_name=tool_name,
                context=context,
                error_code="tool_permission_denied",
                safe_message="tool_permission_denied",
                retryable=False,
                user_visible=True,
                source_service="agent_profile_registry",
            )
        return None

    def _is_retryable_error(self, error_code: str) -> bool:
        normalized = str(error_code or "").strip().lower()
        return normalized in {"temporary_unavailable", "provider_timeout", "tool_execution_failed", "rate_limited"}

    def _is_valid_context(self, context: ToolExecutionContext) -> bool:
        if context.caller_type != "agent":
            return True
        if not context.agent_session_id or not context.agent_step_id or not context.agent_type:
            return False
        if not context.resource_scope_refs:
            return False
        if context.session_status not in {"running", "waiting_for_user", "paused"}:
            return False
        if context.step_status not in {"running", "waiting_observation", "waiting_user"}:
            return False
        return True

    def _is_valid_definition_context(self, definition: ToolDefinition, context: ToolExecutionContext) -> bool:
        if context.caller_type != "agent":
            return True
        return context.side_effect_level == definition.side_effect_level

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
            "result_ref": f"context_pack:{snapshot.context_pack_id}",
            "result_status": snapshot.status.value,
            "blocked_reason": snapshot.blocked_reason,
            "warnings": list(snapshot.warnings),
        }

    def _generate_candidate_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        writer_output = self._writer_service.generate_candidate_text(
            context_pack=payload["context_pack"],
            writing_task=payload["writing_task"],
        )
        return {"writer_output": writer_output}

    def _run_writer_step(
        self,
        payload: dict[str, Any],
        *,
        context: ToolExecutionContext | None = None,
    ) -> dict[str, Any]:
        if "context_pack" in payload and "writing_task" in payload:
            return self._generate_candidate_text(payload)
        if context is None or context.caller_type != "agent":
            raise ValueError("writer_input_invalid")
        work_id = self._resolve_scoped_work_id(payload, context=context)
        chapter_id = str(payload.get("chapter_id", "") or context.chapter_id).strip()
        if not chapter_id or (context.chapter_id and chapter_id != context.chapter_id):
            raise ValueError("tool_resource_scope_mismatch")
        context_pack = self._context_pack_service.get_latest(work_id, chapter_id)
        expected_context_pack_id = str(payload.get("context_pack_id", "")).strip()
        if context_pack is None or (expected_context_pack_id and context_pack.context_pack_id != expected_context_pack_id):
            raise ValueError("context_pack_not_found")
        if context_pack.status.value == "blocked":
            raise ValueError(context_pack.blocked_reason or "context_pack_blocked")
        if self._direction_plan_repository is None:
            raise ValueError("direction_plan_repository_not_available")
        writing_task_id = str(payload.get("writing_task_id", "")).strip()
        if not writing_task_id:
            raise ValueError("writing_task_required")
        writing_task = self._direction_plan_repository.get_writing_task(writing_task_id)
        if writing_task.work_id != work_id or writing_task.chapter_id != chapter_id:
            raise ValueError("tool_resource_scope_mismatch")
        if writing_task.status not in {WritingTaskStatus.READY, WritingTaskStatus.PENDING}:
            raise ValueError("writing_task_not_ready")

        writer_output = self._writer_service.generate_candidate_text(
            context_pack=context_pack,
            writing_task=writing_task,
        )
        validated = self._validate_writer_output({"content": str(writer_output.get("content", ""))})
        candidate_draft_id = str(payload.get("candidate_draft_id", "")).strip() or f"cd_{uuid.uuid4().hex[:12]}"
        saved = self._save_candidate_draft(
            {
                "candidate_draft_id": candidate_draft_id,
                "candidate_version_id": f"{candidate_draft_id}_v1",
                "work_id": work_id,
                "chapter_id": chapter_id,
                "agent_session_id": context.agent_session_id,
                "writing_task_id": writing_task.writing_task_id,
                "direction_plan_snapshot_id": str(writing_task.metadata.get("direction_plan_snapshot_id", "")),
                "source_context_pack_id": context_pack.context_pack_id,
                "source_job_id": str(payload.get("source_job_id", "") or context.agent_session_id),
                "content": validated["validated_content"],
                "writer_model_role": str(writer_output.get("model_role", "writer")),
                "provider_name": str(writer_output.get("provider_name", "")),
                "model_name": str(writer_output.get("model_name", "")),
                "created_by": "writer_agent",
                "request_id": context.request_id,
                "trace_id": context.trace_id,
                "metadata": {
                    "context_pack_status": context_pack.status.value,
                    "context_warning_refs": list(context_pack.warnings),
                    "formal_write_forbidden": True,
                },
            }
        )["candidate_draft"]
        return {
            "result_ref": f"candidate_draft:{saved.candidate_draft_id}",
            "candidate_draft_id": saved.candidate_draft_id,
            "candidate_version_id": saved.selected_version_id,
            "warnings": list(context_pack.warnings),
        }

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
        candidate_version_id = str(payload.get("candidate_version_id", "")).strip() or f"{payload['candidate_draft_id']}_v1"
        created_at = self._now()
        draft = CandidateDraft(
            candidate_draft_id=str(payload["candidate_draft_id"]),
            work_id=str(payload["work_id"]),
            chapter_id=str(payload["chapter_id"]),
            agent_session_id=str(payload.get("agent_session_id", "")),
            writing_task_id=str(payload.get("writing_task_id", "")),
            direction_plan_snapshot_id=str(payload.get("direction_plan_snapshot_id", "")),
            source_context_pack_id=str(payload["source_context_pack_id"]),
            source_job_id=str(payload["source_job_id"]),
            status=CandidateDraftStatus.PENDING_REVIEW,
            selected_version_id=candidate_version_id,
            latest_version_no=1,
            content=content,
            content_preview=content[:120],
            word_count=max(1, len(re.findall(r"\S+", content))),
            char_count=len(content),
            validation_status=CandidateDraftValidationStatus.PASSED,
            writer_model_role=str(payload.get("writer_model_role", "writer")),
            provider_name=str(payload.get("provider_name", "")),
            model_name=str(payload.get("model_name", "")),
            created_by=str(payload.get("created_by", "workflow")),
            created_at=created_at,
            updated_at=created_at,
            request_id=str(payload.get("request_id", "")),
            trace_id=str(payload.get("trace_id", "")),
            metadata=dict(payload.get("metadata", {})),
        )
        saved = self._candidate_draft_repository.save(draft)
        self._candidate_draft_repository.save_version(
            CandidateDraftVersion(
                candidate_version_id=candidate_version_id,
                candidate_draft_id=saved.candidate_draft_id,
                work_id=saved.work_id,
                chapter_id=saved.chapter_id,
                agent_session_id=saved.agent_session_id,
                version_no=1,
                status=CandidateDraftVersionStatus.GENERATED,
                content=content,
                content_summary=content[:120],
                word_count=saved.word_count,
                writing_task_id=saved.writing_task_id,
                direction_plan_snapshot_id=saved.direction_plan_snapshot_id,
                source_context_pack_id=saved.source_context_pack_id,
                created_by=str(payload.get("created_by", "workflow")),
                created_at=created_at,
                updated_at=created_at,
                request_id=saved.request_id,
                trace_id=saved.trace_id,
            )
        )
        return {"candidate_draft": saved}

    def _get_candidate_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        draft = self._candidate_draft_repository.get(str(payload["candidate_draft_id"]))
        return {"candidate_draft": draft}

    def _get_story_memory_snapshot(
        self,
        payload: dict[str, Any],
        *,
        context: ToolExecutionContext | None = None,
    ) -> dict[str, Any]:
        work_id = self._resolve_scoped_work_id(payload, context=context)
        if self._story_memory_repository is None:
            raise ValueError("story_memory_repository_not_available")
        snapshot = self._story_memory_repository.get_latest_snapshot_by_work(work_id)
        if snapshot is None:
            raise ValueError("story_memory_not_found")
        warnings = ["story_memory_stale"] if str(snapshot.stale_status) == "stale" else []
        return {
            "result_ref": f"memory_context:{snapshot.snapshot_id}",
            "story_memory_ref": f"story_memory:{snapshot.snapshot_id}",
            "snapshot_id": snapshot.snapshot_id,
            "stale_status": str(snapshot.stale_status),
            "warnings": warnings,
        }

    def _get_story_state_baseline(
        self,
        payload: dict[str, Any],
        *,
        context: ToolExecutionContext | None = None,
    ) -> dict[str, Any]:
        work_id = self._resolve_scoped_work_id(payload, context=context)
        if self._story_state_repository is None:
            raise ValueError("story_state_repository_not_available")
        story_state = self._story_state_repository.get_latest_analysis_baseline_by_work(work_id)
        if story_state is None:
            raise ValueError("story_state_not_found")
        warnings = ["story_state_stale"] if str(story_state.stale_status) == "stale" else []
        return {
            "result_ref": f"story_state:{story_state.story_state_id}",
            "story_state_id": story_state.story_state_id,
            "stale_status": str(story_state.stale_status),
            "warnings": warnings,
        }

    def _resolve_scoped_work_id(
        self,
        payload: dict[str, Any],
        *,
        context: ToolExecutionContext | None,
    ) -> str:
        payload_work_id = str(payload.get("work_id", "")).strip()
        context_work_id = str(context.work_id if context is not None else "").strip()
        if payload_work_id and context_work_id and payload_work_id != context_work_id:
            raise ValueError("tool_resource_scope_mismatch")
        work_id = context_work_id or payload_work_id
        if not work_id:
            raise ValueError("work_id_required")
        return work_id

    def _create_memory_update_suggestion(self, payload: dict[str, Any]) -> dict[str, Any]:
        suggestion_id = str(payload.get("suggestion_id", "")) or f"memsug_{uuid.uuid4().hex[:8]}"
        return {"result_ref": f"memory_update_suggestion:{suggestion_id}"}

    def _create_direction_proposal(
        self,
        payload: dict[str, Any],
        *,
        context: ToolExecutionContext | None = None,
    ) -> dict[str, Any]:
        if self._planning_generation_service is not None and not list(payload.get("options", []) or []):
            if context is None:
                raise ValueError("tool_context_invalid")
            payload = self._planning_generation_service.build_direction_proposal_payload(
                work_id=str(payload.get("work_id", "") or context.work_id),
                chapter_id=str(payload.get("chapter_id", "") or context.chapter_id),
                user_instruction=str(payload.get("user_instruction", "")),
                request_id=context.request_id,
                trace_id=context.trace_id,
                agent_session_id=context.agent_session_id,
            )
        proposal_id = str(payload.get("direction_proposal_id", "") or payload.get("proposal_id", "")) or f"dir_{uuid.uuid4().hex[:8]}"
        if self._direction_plan_repository is not None:
            self._supersede_existing_direction_proposals(
                work_id=str(payload.get("work_id", "")),
                chapter_id=str(payload.get("chapter_id", "")),
                exclude_proposal_id=proposal_id,
                stale_reason="direction_regenerated",
            )
            proposal_payload = dict(payload)
            proposal_payload["direction_proposal_id"] = proposal_id
            normalized_options: list[dict[str, Any]] = []
            for item in list(proposal_payload.get("options", [])):
                current = dict(item)
                current.setdefault("direction_proposal_id", proposal_id)
                normalized_options.append(current)
            if normalized_options:
                proposal_payload["options"] = normalized_options
            proposal = DirectionProposal.model_validate(proposal_payload)
            self._direction_plan_repository.save_direction_proposal(proposal)
        return {"result_ref": f"direction:{proposal_id}"}

    def _create_chapter_plan(
        self,
        payload: dict[str, Any],
        *,
        context: ToolExecutionContext | None = None,
    ) -> dict[str, Any]:
        if self._planning_generation_service is not None and not list(payload.get("plan_items", []) or []):
            if context is None:
                raise ValueError("tool_context_invalid")
            payload = self._planning_generation_service.build_chapter_plan_payload(
                work_id=str(payload.get("work_id", "") or context.work_id),
                chapter_id=str(payload.get("chapter_id", "") or context.chapter_id),
                direction_proposal_id=str(payload.get("direction_proposal_id", "")),
                request_id=context.request_id,
                trace_id=context.trace_id,
                agent_session_id=context.agent_session_id,
            )
        plan_id = str(payload.get("chapter_plan_id", "") or payload.get("plan_id", "")) or f"plan_{uuid.uuid4().hex[:8]}"
        if self._chapter_plan_repository is not None:
            self._supersede_existing_chapter_plans(
                work_id=str(payload.get("work_id", "")),
                chapter_id=str(payload.get("chapter_id", "")),
                exclude_plan_id=plan_id,
                stale_reason="chapter_plan_regenerated",
            )
            plan_payload = dict(payload)
            plan_payload["chapter_plan_id"] = plan_id
            normalized_items: list[dict[str, Any]] = []
            for item in list(plan_payload.get("plan_items", [])):
                current = dict(item)
                current.setdefault("chapter_plan_id", plan_id)
                normalized_items.append(current)
            if normalized_items:
                plan_payload["plan_items"] = normalized_items
            plan = ChapterPlan.model_validate(plan_payload)
            self._chapter_plan_repository.save(plan)
        return {"result_ref": f"chapter_plan:{plan_id}"}

    def _create_writing_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = str(payload.get("writing_task_id", "")) or f"wt_{uuid.uuid4().hex[:8]}"
        if self._direction_plan_repository is not None:
            task_payload = dict(payload)
            task_payload["writing_task_id"] = task_id
            task = WritingTask.model_validate(task_payload)
            self._direction_plan_repository.save_writing_task(task)
        return {"result_ref": f"writing_task:{task_id}"}

    def _supersede_existing_direction_proposals(
        self,
        *,
        work_id: str,
        chapter_id: str,
        exclude_proposal_id: str,
        stale_reason: str,
    ) -> None:
        if self._direction_plan_repository is None or not work_id:
            return
        superseded_direction_ids: list[str] = []
        now = self._now()
        for proposal in self._direction_plan_repository.list_direction_proposals(work_id, chapter_id=chapter_id):
            if proposal.direction_proposal_id == exclude_proposal_id:
                continue
            if proposal.status == DirectionPlanStatus.SUPERSEDED and proposal.stale_reason == stale_reason:
                superseded_direction_ids.append(proposal.direction_proposal_id)
                continue
            updated = proposal.model_copy(
                update={
                    "status": DirectionPlanStatus.SUPERSEDED,
                    "stale_status": "stale",
                    "stale_reason": stale_reason,
                    "updated_at": now,
                }
            )
            self._direction_plan_repository.save_direction_proposal(updated)
            superseded_direction_ids.append(proposal.direction_proposal_id)
        if superseded_direction_ids:
            self._supersede_related_chapter_plans(
                work_id=work_id,
                chapter_id=chapter_id,
                direction_ids=superseded_direction_ids,
                stale_reason=stale_reason,
            )
            self._stale_related_writing_tasks(
                work_id=work_id,
                chapter_id=chapter_id,
                direction_ids=superseded_direction_ids,
                stale_reason=stale_reason,
            )

    def _supersede_existing_chapter_plans(
        self,
        *,
        work_id: str,
        chapter_id: str,
        exclude_plan_id: str,
        stale_reason: str,
    ) -> None:
        if self._chapter_plan_repository is None or not work_id:
            return
        superseded_plan_ids: list[str] = []
        now = self._now()
        for plan in self._chapter_plan_repository.list_by_work(work_id, chapter_id=chapter_id):
            if plan.chapter_plan_id == exclude_plan_id:
                continue
            if plan.status == DirectionPlanStatus.SUPERSEDED and plan.stale_reason == stale_reason:
                superseded_plan_ids.append(plan.chapter_plan_id)
                continue
            updated = plan.model_copy(
                update={
                    "status": DirectionPlanStatus.SUPERSEDED,
                    "stale_status": "stale",
                    "stale_reason": stale_reason,
                    "updated_at": now,
                }
            )
            self._chapter_plan_repository.save(updated)
            superseded_plan_ids.append(plan.chapter_plan_id)
        if superseded_plan_ids:
            self._stale_related_writing_tasks(
                work_id=work_id,
                chapter_id=chapter_id,
                chapter_plan_ids=superseded_plan_ids,
                stale_reason=stale_reason,
            )

    def _supersede_related_chapter_plans(
        self,
        *,
        work_id: str,
        chapter_id: str,
        direction_ids: list[str],
        stale_reason: str,
    ) -> None:
        if self._chapter_plan_repository is None or not direction_ids:
            return
        now = self._now()
        for plan in self._chapter_plan_repository.list_by_work(work_id, chapter_id=chapter_id):
            if plan.direction_proposal_id not in direction_ids:
                continue
            updated = plan.model_copy(
                update={
                    "status": DirectionPlanStatus.SUPERSEDED,
                    "stale_status": "stale",
                    "stale_reason": stale_reason,
                    "updated_at": now,
                }
            )
            self._chapter_plan_repository.save(updated)

    def _stale_related_writing_tasks(
        self,
        *,
        work_id: str,
        chapter_id: str,
        stale_reason: str,
        direction_ids: list[str] | None = None,
        chapter_plan_ids: list[str] | None = None,
    ) -> None:
        if self._direction_plan_repository is None:
            return
        direction_ids = direction_ids or []
        chapter_plan_ids = chapter_plan_ids or []
        if not direction_ids and not chapter_plan_ids:
            return
        now = self._now()
        for task in self._direction_plan_repository.list_writing_tasks(work_id, chapter_id=chapter_id):
            if task.direction_proposal_id not in direction_ids and task.chapter_plan_id not in chapter_plan_ids:
                continue
            updated = task.model_copy(
                update={
                    "status": WritingTaskStatus.STALE,
                    "stale_status": "stale",
                    "stale_reason": stale_reason,
                    "updated_at": now,
                }
            )
            self._direction_plan_repository.save_writing_task(updated)

    def _create_review_report(
        self,
        payload: dict[str, Any],
        *,
        context: ToolExecutionContext | None = None,
    ) -> dict[str, Any]:
        candidate_draft_id = str(payload.get("candidate_draft_id", "")).strip()
        if self._ai_review_service is not None and candidate_draft_id:
            if context is None or context.caller_type != "agent" or context.agent_type != "reviewer":
                raise ValueError("tool_context_invalid")
            review = self._ai_review_service.review_candidate_draft(
                candidate_draft_id,
                created_by="reviewer_agent",
                user_instruction=str(payload.get("user_instruction", "")),
                allow_degraded=bool(payload.get("allow_degraded", True)),
                idempotency_key=str(payload.get("idempotency_key", "") or context.agent_step_id),
            )
            if review.status.value in {"failed", "blocked"}:
                raise ValueError("review_generation_failed")
            return {
                "result_ref": f"review_report:{review.review_id}",
                "result_status": review.status.value,
                "rewrite_recommended": bool(review.issues) or review.risk_level.value == "high",
                "warnings": list(review.warnings),
            }
        review_id = str(payload.get("review_id", "")) or f"review_{uuid.uuid4().hex[:8]}"
        return {"result_ref": f"review_report:{review_id}"}

    def _create_review_issue(self, payload: dict[str, Any]) -> dict[str, Any]:
        issue_id = str(payload.get("issue_id", "")) or f"issue_{uuid.uuid4().hex[:8]}"
        return {"result_ref": f"review_issue:{issue_id}"}

    def _create_ai_suggestion(self, payload: dict[str, Any]) -> dict[str, Any]:
        suggestion_id = str(payload.get("suggestion_id", "")) or f"ais_{uuid.uuid4().hex[:8]}"
        if self._ai_suggestion_repository is not None:
            now = self._now()
            suggestion_type = AISuggestionType(str(payload.get("suggestion_type", AISuggestionType.REWRITE_SUGGESTION.value)))
            suggestion_payload = {
                "suggestion_id": suggestion_id,
                "work_id": str(payload.get("work_id", "")),
                "chapter_id": str(payload.get("chapter_id", "")),
                "agent_session_id": str(payload.get("agent_session_id", "")),
                "source": payload.get("source")
                or {
                    "source_type": str(payload.get("source_type", "review_issue")),
                    "source_ref_id": str(
                        payload.get("source_ref_id", "")
                        or payload.get("review_issue_id", "")
                        or payload.get("review_id", "")
                    ),
                    "source_agent_type": str(payload.get("source_agent_type", "")),
                    "source_agent_session_id": str(payload.get("source_agent_session_id", "")),
                    "source_version_id": str(payload.get("source_version_id", "")),
                },
                "target": payload.get("target")
                or {
                    "target_type": str(payload.get("target_type", "candidate_draft_version")),
                    "target_ref_id": str(payload.get("target_ref_id", "")),
                    "target_scope": str(payload.get("target_scope", "chapter")),
                    "target_snapshot_ref": str(payload.get("target_snapshot_ref", "")),
                },
                "suggestion_type": suggestion_type,
                "severity": AISuggestionSeverity(str(payload.get("severity", AISuggestionSeverity.MEDIUM.value))),
                "priority": AISuggestionPriority(str(payload.get("priority", AISuggestionPriority.MEDIUM.value))),
                "title": str(payload.get("title", "") or "AI 建议"),
                "summary": str(payload.get("summary", "")),
                "rationale": str(payload.get("rationale", "")),
                "proposed_action": str(payload.get("proposed_action", "")),
                "status": AISuggestionStatus(str(payload.get("status", AISuggestionStatus.GENERATED.value))),
                "decision": str(payload.get("decision", "")),
                "decided_by": str(payload.get("decided_by", "")),
                "warning_codes": list(payload.get("warning_codes", []) or []),
                "created_by": str(payload.get("created_by", "reviewer_agent")),
                "created_at": str(payload.get("created_at", "")) or now,
                "updated_at": str(payload.get("updated_at", "")) or now,
                "request_id": str(payload.get("request_id", "")),
                "trace_id": str(payload.get("trace_id", "")),
                "expires_at": str(payload.get("expires_at", "")),
                "action": payload.get("action")
                or {
                    "action_type": self._default_ai_suggestion_action_type(suggestion_type).value,
                    "requires_user_action": True,
                    "action_status": "pending",
                },
                "batch_id": str(payload.get("batch_id", "")),
                "metadata": dict(payload.get("metadata", {})),
            }
            suggestion = AISuggestion.model_validate(suggestion_payload)
            self._ai_suggestion_repository.save(suggestion)
        return {"result_ref": f"ai_suggestion:{suggestion_id}"}

    @staticmethod
    def _default_ai_suggestion_action_type(suggestion_type: AISuggestionType) -> AISuggestionActionType:
        if suggestion_type == AISuggestionType.RISK_WARNING:
            return AISuggestionActionType.DISMISS_ONLY
        if suggestion_type == AISuggestionType.MEMORY_UPDATE_SUGGESTION_REF:
            return AISuggestionActionType.CREATE_MEMORY_UPDATE_REF
        if suggestion_type == AISuggestionType.CONFLICT_RESOLUTION_SUGGESTION:
            return AISuggestionActionType.OPEN_CONFLICT_RESOLUTION
        if suggestion_type == AISuggestionType.DIRECTION_PLAN_SUGGESTION:
            return AISuggestionActionType.ADJUST_DIRECTION_OR_PLAN
        return AISuggestionActionType.CONVERT_TO_REWRITE_INSTRUCTION

    def _create_candidate_version(
        self,
        payload: dict[str, Any],
        *,
        context: ToolExecutionContext | None = None,
    ) -> dict[str, Any]:
        candidate_draft_id = str(payload.get("candidate_draft_id", "")).strip()
        source_version_id = str(payload.get("source_version_id", "")).strip()
        if self._candidate_rewrite_service is not None and candidate_draft_id and source_version_id:
            if context is None or context.caller_type != "agent" or context.agent_type != "rewriter":
                raise ValueError("tool_context_invalid")
            result = self._candidate_rewrite_service.request_rewrite(
                candidate_draft_id=candidate_draft_id,
                source_version_id=source_version_id,
                trigger_type=str(payload.get("trigger_type", "review_based")),
                review_report_id=str(payload.get("review_report_id", "")),
                user_instruction=str(payload.get("user_instruction", "")),
                user_action=False,
                idempotency_key=str(payload.get("idempotency_key", "") or context.agent_step_id),
                caller_type="rewriter_agent",
                agent_session_id=context.agent_session_id,
            )
            target_version = result["target_version"]
            return {
                "result_ref": f"candidate_version:{target_version.candidate_version_id}",
                "candidate_version_id": target_version.candidate_version_id,
                "result_status": target_version.status.value,
            }
        version_id = str(payload.get("candidate_version_id", "")) or f"ver_{uuid.uuid4().hex[:8]}"
        if self._candidate_draft_repository is not None and str(payload.get("candidate_draft_id", "")).strip():
            version = CandidateDraftVersion(
                candidate_version_id=version_id,
                candidate_draft_id=str(payload["candidate_draft_id"]),
                work_id=str(payload.get("work_id", "")),
                chapter_id=str(payload.get("chapter_id", "")),
                agent_session_id=str(payload.get("agent_session_id", "")),
                source_candidate_draft_id=str(payload.get("source_candidate_draft_id", "")),
                source_version_id=str(payload.get("source_version_id", "")),
                parent_version_id=str(payload.get("parent_version_id", "")),
                version_no=int(payload.get("version_no", 1) or 1),
                status=CandidateDraftVersionStatus(str(payload.get("status", "generated"))),
                content_ref=str(payload.get("content_ref", "")),
                text_ref=str(payload.get("text_ref", "")),
                content=str(payload.get("content", "")),
                content_summary=str(payload.get("content_summary", "") or str(payload.get("content", ""))[:120]),
                word_count=int(payload.get("word_count", 0) or 0),
                writing_task_id=str(payload.get("writing_task_id", "")),
                direction_plan_snapshot_id=str(payload.get("direction_plan_snapshot_id", "")),
                source_context_pack_id=str(payload.get("source_context_pack_id", "")),
                review_report_id=str(payload.get("review_report_id", "")),
                warning_codes=list(payload.get("warning_codes", []) or []),
                stale_status=str(payload.get("stale_status", "fresh") or "fresh"),
                created_by=str(payload.get("created_by", "rewriter_agent")),
                created_at=str(payload.get("created_at", "")) or self._now(),
                updated_at=str(payload.get("updated_at", "")) or self._now(),
                request_id=str(payload.get("request_id", "")),
                trace_id=str(payload.get("trace_id", "")),
            )
            self._candidate_draft_repository.save_version(version)
            draft = self._candidate_draft_repository.get(version.candidate_draft_id)
            updated_draft = draft.model_copy(
                update={
                    "latest_version_no": max(int(draft.latest_version_no or 0), version.version_no),
                    "revision_round": max(int(draft.revision_round or 0), max(0, version.version_no - 1)),
                    "updated_at": self._now(),
                }
            )
            self._candidate_draft_repository.save(updated_draft)
        return {"result_ref": f"candidate_version:{version_id}"}

    def _request_conflict_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        target_ref = str(payload.get("target_ref", "")) or f"work:{payload.get('work_id', '')}"
        return {"result_ref": f"conflict_status:{target_ref}", "status": "clear"}

    def _create_agent_observation(self, payload: dict[str, Any]) -> dict[str, Any]:
        observation_id = str(payload.get("observation_id", "")) or f"obs_{uuid.uuid4().hex[:8]}"
        return {"result_ref": f"agent_observation:{observation_id}"}

    def _create_agent_trace_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_event_id = str(payload.get("trace_event_id", "")) or f"trace_evt_{uuid.uuid4().hex[:8]}"
        return {"result_ref": f"agent_trace_event:{trace_event_id}"}

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
                tool_name="get_story_memory_snapshot",
                allowed_callers={"agent"},
                side_effect_level="read_only",
                source_service="story_memory_service",
            ),
            self._get_story_memory_snapshot,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="get_story_state_baseline",
                allowed_callers={"agent"},
                side_effect_level="read_only",
                source_service="story_state_service",
            ),
            self._get_story_state_baseline,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="build_context_pack",
                allowed_callers={"workflow", "ai", "quick_trial", "user_action", "agent"},
                side_effect_level="plan_write",
                source_service="context_pack_service",
            ),
            self._build_context_pack,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_memory_update_suggestion",
                allowed_callers={"agent"},
                side_effect_level="safe_write_suggestion",
                source_service="story_memory_service",
            ),
            self._create_memory_update_suggestion,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_direction_proposal",
                allowed_callers={"agent"},
                side_effect_level="plan_write",
                source_service="planner_service",
            ),
            self._create_direction_proposal,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_chapter_plan",
                allowed_callers={"agent"},
                side_effect_level="plan_write",
                source_service="planner_service",
            ),
            self._create_chapter_plan,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_writing_task",
                allowed_callers={"agent"},
                side_effect_level="plan_write",
                source_service="planner_service",
            ),
            self._create_writing_task,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="run_writer_step",
                allowed_callers={"workflow", "ai", "agent"},
                side_effect_level="safe_write_candidate",
                source_service="writer_service",
            ),
            self._generate_candidate_text,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="validate_writer_output",
                allowed_callers={"workflow", "ai", "agent"},
                side_effect_level="read_only",
                source_service="output_validation_service",
            ),
            self._validate_writer_output,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_review_report",
                allowed_callers={"agent"},
                side_effect_level="safe_write_review",
                source_service="review_service",
            ),
            self._create_review_report,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_review_issue",
                allowed_callers={"agent"},
                side_effect_level="safe_write_review",
                source_service="review_service",
            ),
            self._create_review_issue,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_ai_suggestion",
                allowed_callers={"agent"},
                side_effect_level="safe_write_suggestion",
                source_service="review_service",
            ),
            self._create_ai_suggestion,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_candidate_version",
                allowed_callers={"agent"},
                side_effect_level="safe_write_candidate",
                source_service="candidate_draft_repository",
            ),
            self._create_candidate_version,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="request_conflict_check",
                allowed_callers={"agent"},
                side_effect_level="read_only",
                source_service="conflict_guard",
            ),
            self._request_conflict_check,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_agent_observation",
                allowed_callers={"agent"},
                side_effect_level="trace_only",
                source_service="agent_runtime",
            ),
            self._create_agent_observation,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="create_agent_trace_event",
                allowed_callers={"agent"},
                side_effect_level="trace_only",
                source_service="agent_runtime",
            ),
            self._create_agent_trace_event,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="save_candidate_draft",
                allowed_callers={"workflow", "ai", "agent"},
                side_effect_level="safe_write_candidate",
                source_service="candidate_draft_repository",
            ),
            self._save_candidate_draft,
        )
        self.register_tool(
            ToolDefinition(
                tool_name="get_candidate_draft",
                allowed_callers={"workflow", "ai", "user_action", "agent"},
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
        audit_log_ref = f"toolaudit_{uuid.uuid4().hex[:12]}"
        audit_entry = {
            "audit_log_ref": audit_log_ref,
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
        self.audit_logs.append(audit_entry)
        envelope.tool_audit_log_ref = audit_log_ref
        if self._trace_service is not None and context.trace_id and context.agent_step_id:
            permission_result = "deny" if envelope.error_code == "tool_permission_denied" else "allow"
            call_status = "failed"
            if permission_result == "deny":
                call_status = "failed"
            elif envelope.ok:
                call_status = "succeeded"
            self._trace_service.record_tool_call(
                trace_id=context.trace_id,
                step_id=context.agent_step_id,
                tool_name=tool_name,
                caller_type=context.caller_type,
                side_effect_level=context.side_effect_level or "trace_only",
                permission_result=permission_result,
                call_status=call_status,
                request_id=context.request_id,
                safe_input_digest={"payload_keys": sorted(str(key) for key in envelope.payload.keys())} if envelope.payload else {},
                safe_output_digest={"warnings": list(envelope.warnings), "error_code": envelope.error_code},
                error_code=envelope.error_code,
                tool_audit_log_ref=audit_log_ref,
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
