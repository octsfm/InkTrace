from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import ConflictDecisionRequest

router = APIRouter(tags=["v2-ai-conflicts"])


def _serialize_conflict(item) -> dict[str, object]:  # noqa: ANN001
    return item.model_dump(mode="json")


def _conflict_error_status(error_code: str) -> int:
    if error_code in {"conflict_record_not_found"}:
        return 404
    if error_code in {"action_not_allowed", "caller_type_not_allowed"}:
        return 403
    if error_code in {"blocking_conflict_unresolved", "cannot_override_blocking"}:
        return 409
    if error_code in {"idempotency_key_required"}:
        return 400
    return 400


def _reject_invalid_decision_request(request: Request, payload: ConflictDecisionRequest):
    if payload.caller_type != "user_action":
        return error_response(request, error_code="caller_type_not_allowed", status_code=403)
    if not payload.user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(payload.idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


@router.get("/api/v2/ai/conflicts")
def list_conflicts(
    request: Request,
    work_id: str = "",
    chapter_id: str = "",
    candidate_draft_id: str = "",
    candidate_version_id: str = "",
):
    service = dependencies.get_conflict_guard_service()
    items = service.list_records(
        work_id=work_id,
        chapter_id=chapter_id,
        candidate_draft_id=candidate_draft_id,
        candidate_version_id=candidate_version_id,
    )
    return success_response(request, data={"items": [_serialize_conflict(item) for item in items]})


@router.get("/api/v2/ai/conflicts/{record_id}")
def get_conflict(record_id: str, request: Request):
    service = dependencies.get_conflict_guard_service()
    try:
        item = service.get_record(record_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_conflict(item))


@router.post("/api/v2/ai/conflicts/{record_id}/decide")
def decide_conflict(record_id: str, payload: ConflictDecisionRequest, request: Request):
    denied = _reject_invalid_decision_request(request, payload)
    if denied is not None:
        return denied
    service = dependencies.get_conflict_guard_service()
    try:
        item = service.decide_record(
            record_id,
            decision=payload.decision,
            user_id=payload.user_id,
            user_action=payload.user_action,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
            note=payload.decision_note,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_conflict_error_status(error_code))
    return success_response(request, data=_serialize_conflict(item))
