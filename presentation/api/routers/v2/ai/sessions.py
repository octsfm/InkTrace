from __future__ import annotations

from fastapi import APIRouter, Request

from domain.entities.ai.models import AgentWorkflowType
from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response, trace_id_from_request
from presentation.api.routers.v2.ai.schemas import SessionActionRequest, StartAgentSessionRequest

router = APIRouter(tags=["v2-ai-sessions"])


def _ensure_gate_request(request: Request, *, caller_type: str, user_action: bool, idempotency_key: str):
    if caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    if not user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


def _serialize_session(item) -> dict[str, object]:  # noqa: ANN001
    return item.model_dump(mode="json")


def _session_status_code(error_code: str) -> int:
    if error_code in {"session_not_found"}:
        return 404
    if error_code in {"session_not_pausable", "session_not_resumable", "session_not_cancellable", "waiting_user_decision_required"}:
        return 409
    if error_code in {"action_not_allowed", "caller_type_forbidden"}:
        return 403
    return 400


@router.post("/api/v2/ai/sessions")
def start_agent_session(payload: StartAgentSessionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_agent_runtime_service()
    try:
        session = service.create_session(
            work_id=payload.work_id,
            chapter_id=payload.chapter_id or None,
            agent_workflow_type=AgentWorkflowType(str(payload.workflow_type or "continuation")),
            user_instruction=payload.user_instruction,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=trace_id_from_request(request),
            caller_type=payload.caller_type,
            allow_degraded=payload.allow_degraded,
        )
        started = service.start_session(session.session_id)
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_session_status_code(error_code))
    return success_response(request, data=_serialize_session(started))


@router.get("/api/v2/ai/sessions")
def list_agent_sessions(request: Request, work_id: str = "", status: str = ""):
    items = dependencies.get_agent_runtime_service().list_sessions(work_id=work_id, status=status)
    return success_response(request, data={"items": [_serialize_session(item) for item in items]})


@router.get("/api/v2/ai/sessions/{session_id}")
def get_agent_session(session_id: str, request: Request):
    try:
        item = dependencies.get_agent_runtime_service().get_session(session_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_session(item))


@router.post("/api/v2/ai/sessions/{session_id}/pause")
def pause_agent_session(session_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    try:
        item = dependencies.get_agent_runtime_service().pause_session(session_id, reason=payload.reason or "pause_requested")
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_session_status_code(error_code))
    return success_response(request, data=_serialize_session(item))


@router.post("/api/v2/ai/sessions/{session_id}/resume")
def resume_agent_session(session_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    try:
        item = dependencies.get_agent_runtime_service().resume_session(session_id)
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_session_status_code(error_code))
    return success_response(request, data=_serialize_session(item))


@router.post("/api/v2/ai/sessions/{session_id}/cancel")
def cancel_agent_session(session_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    try:
        item = dependencies.get_agent_runtime_service().cancel_session(session_id, reason=payload.reason or "user_cancelled")
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_session_status_code(error_code))
    return success_response(request, data=_serialize_session(item))
