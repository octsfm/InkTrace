from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import SuggestionDecisionRequest

router = APIRouter(tags=["v2-ai-suggestions"])


def _serialize_suggestion(item) -> dict[str, object]:  # noqa: ANN001
    return item.model_dump(mode="json")


def _decision_error_status(error_code: str) -> int:
    if error_code in {"ai_suggestion_not_found"}:
        return 404
    if error_code in {"action_not_allowed", "caller_type_forbidden"}:
        return 403
    if error_code in {"idempotency_key_required"}:
        return 400
    return 400


def _reject_invalid_decision_request(request: Request, payload: SuggestionDecisionRequest):
    if payload.caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    if not payload.user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(payload.idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


@router.get("/api/v2/ai/suggestions")
def list_ai_suggestions(request: Request, work_id: str, chapter_id: str = "", target_ref_id: str = ""):
    service = dependencies.get_ai_suggestion_service()
    items = service.list_suggestions(work_id=work_id, chapter_id=chapter_id, target_ref_id=target_ref_id)
    return success_response(request, data={"items": [_serialize_suggestion(item) for item in items]})


@router.get("/api/v2/ai/suggestions/{suggestion_id}")
def get_ai_suggestion(suggestion_id: str, request: Request):
    service = dependencies.get_ai_suggestion_service()
    try:
        item = service.get_suggestion(suggestion_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_suggestion(item))


@router.post("/api/v2/ai/suggestions/{suggestion_id}/accept")
def accept_ai_suggestion(suggestion_id: str, payload: SuggestionDecisionRequest, request: Request):
    denied = _reject_invalid_decision_request(request, payload)
    if denied is not None:
        return denied
    service = dependencies.get_ai_suggestion_service()
    try:
        item = service.accept_suggestion(suggestion_id, user_id=payload.user_id, user_action=payload.user_action)
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_decision_error_status(error_code))
    return success_response(request, data=_serialize_suggestion(item))


@router.post("/api/v2/ai/suggestions/{suggestion_id}/dismiss")
def dismiss_ai_suggestion(suggestion_id: str, payload: SuggestionDecisionRequest, request: Request):
    denied = _reject_invalid_decision_request(request, payload)
    if denied is not None:
        return denied
    service = dependencies.get_ai_suggestion_service()
    try:
        item = service.dismiss_suggestion(
            suggestion_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
            note=payload.decision_note,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_decision_error_status(error_code))
    return success_response(request, data=_serialize_suggestion(item))


@router.post("/api/v2/ai/suggestions/{suggestion_id}/convert")
def convert_ai_suggestion(suggestion_id: str, payload: SuggestionDecisionRequest, request: Request):
    denied = _reject_invalid_decision_request(request, payload)
    if denied is not None:
        return denied
    service = dependencies.get_ai_suggestion_service()
    try:
        item = service.convert_suggestion(
            suggestion_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_decision_error_status(error_code))
    return success_response(request, data=_serialize_suggestion(item))
