from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import (
    ApplyMemoryGateRequest,
    MemorySuggestionDecisionRequest,
    MemorySuggestionEditApproveRequest,
    RollbackMemoryRevisionRequest,
)

router = APIRouter(tags=["v2-ai-memory"])


def _reject_invalid_memory_request(request: Request, *, caller_type: str, user_action: bool, idempotency_key: str):
    if caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    if not user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


def _memory_error_status_code(error_code: str) -> int:
    if error_code in {"memory_revision_apply_blocked", "memory_rollback_not_allowed", "idempotency_key_conflict"}:
        return 409
    return 400


def _serialize_suggestion(item) -> dict[str, object]:  # noqa: ANN001
    return item.model_dump(mode="json")


def _serialize_gate(service, gate) -> dict[str, object]:  # noqa: ANN001
    return {
        **gate.model_dump(mode="json"),
        "suggestions": [_serialize_suggestion(item) for item in service.list_gate_suggestions(gate.gate_id)],
        "revision_ids": [item["revision_id"] for item in service.list_revisions(work_id=gate.work_id, chapter_id=gate.chapter_id) if item["source_suggestion_id"] in gate.suggestion_ids],
    }


@router.get("/api/v2/ai/memory-gates")
def list_memory_gates(request: Request, work_id: str, chapter_id: str = ""):
    service = dependencies.get_memory_review_gate_service()
    items = service.list_gates(work_id=work_id, chapter_id=chapter_id)
    return success_response(request, data={"items": [_serialize_gate(service, item) for item in items]})


@router.get("/api/v2/ai/memory-gates/{gate_id}")
def get_memory_gate(gate_id: str, request: Request):
    service = dependencies.get_memory_review_gate_service()
    try:
        gate = service.get_gate(gate_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_gate(service, gate))


@router.post("/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/approve")
def approve_memory_suggestion(gate_id: str, suggestion_id: str, payload: MemorySuggestionDecisionRequest, request: Request):
    denied = _reject_invalid_memory_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_memory_review_gate_service()
    try:
        gate = service.approve_suggestion(
            gate_id,
            suggestion_id,
            idempotency_key=payload.idempotency_key,
            user_id=payload.user_id,
            user_action=payload.user_action,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
        )
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=_memory_error_status_code(str(exc)))
    return success_response(request, data=_serialize_gate(service, gate))


@router.post("/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/edit-approve")
def edit_approve_memory_suggestion(gate_id: str, suggestion_id: str, payload: MemorySuggestionEditApproveRequest, request: Request):
    denied = _reject_invalid_memory_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_memory_review_gate_service()
    try:
        gate = service.edit_and_approve_suggestion(
            gate_id,
            suggestion_id,
            idempotency_key=payload.idempotency_key,
            user_id=payload.user_id,
            user_action=payload.user_action,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
            proposed_value_summary=payload.proposed_value_summary,
            decision_note=payload.decision_note,
        )
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=_memory_error_status_code(str(exc)))
    return success_response(request, data=_serialize_gate(service, gate))


@router.post("/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/reject")
def reject_memory_suggestion(gate_id: str, suggestion_id: str, payload: MemorySuggestionDecisionRequest, request: Request):
    denied = _reject_invalid_memory_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_memory_review_gate_service()
    try:
        gate = service.reject_suggestion(
            gate_id,
            suggestion_id,
            idempotency_key=payload.idempotency_key,
            user_id=payload.user_id,
            user_action=payload.user_action,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
            decision_note=payload.decision_note,
        )
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=_memory_error_status_code(str(exc)))
    return success_response(request, data=_serialize_gate(service, gate))


@router.post("/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/defer")
def defer_memory_suggestion(gate_id: str, suggestion_id: str, payload: MemorySuggestionDecisionRequest, request: Request):
    denied = _reject_invalid_memory_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_memory_review_gate_service()
    try:
        gate = service.defer_suggestion(
            gate_id,
            suggestion_id,
            idempotency_key=payload.idempotency_key,
            user_id=payload.user_id,
            user_action=payload.user_action,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
            decision_note=payload.decision_note,
        )
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=_memory_error_status_code(str(exc)))
    return success_response(request, data=_serialize_gate(service, gate))


@router.post("/api/v2/ai/memory-gates/{gate_id}/apply")
def apply_memory_gate(gate_id: str, payload: ApplyMemoryGateRequest, request: Request):
    denied = _reject_invalid_memory_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_memory_review_gate_service()
    try:
        result = service.apply_gate(
            gate_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
            idempotency_key=payload.idempotency_key,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = _memory_error_status_code(error_code)
        return error_response(request, error_code=error_code, status_code=status_code)
    gate = result["gate"]
    return success_response(
        request,
        data={
            "gate": _serialize_gate(service, gate),
            "apply_results": result["apply_results"],
            "revision_ids": result["revision_ids"],
        },
    )


@router.get("/api/v2/ai/memory-revisions")
def list_memory_revisions(request: Request, work_id: str, chapter_id: str = ""):
    service = dependencies.get_memory_review_gate_service()
    return success_response(request, data={"items": service.list_revisions(work_id=work_id, chapter_id=chapter_id)})


@router.get("/api/v2/ai/memory-revisions/{revision_id}")
def get_memory_revision(revision_id: str, request: Request):
    service = dependencies.get_memory_review_gate_service()
    try:
        payload = service.get_revision(revision_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=payload)


@router.post("/api/v2/ai/memory-revisions/{revision_id}/rollback")
def rollback_memory_revision(revision_id: str, payload: RollbackMemoryRevisionRequest, request: Request):
    denied = _reject_invalid_memory_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_memory_review_gate_service()
    try:
        result = service.rollback_revision(
            revision_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
            idempotency_key=payload.idempotency_key,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = _memory_error_status_code(error_code)
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(request, data=result)
