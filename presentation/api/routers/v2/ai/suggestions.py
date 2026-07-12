from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.middleware.p2_feature_flag import (
    is_outline_assist_enabled,
    outline_assist_feature_disabled_response,
)
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import SuggestionDecisionRequest

router = APIRouter(tags=["v2-ai-suggestions"])

_AUDIT_FAILURE_SAFE_MESSAGE = "安全记录暂时失败，本次操作没有生效，请稍后重试。"


def _serialize_suggestion(item) -> dict[str, object]:  # noqa: ANN001
    return item.model_dump(mode="json")


def _decision_error_status(error_code: str) -> int:
    if error_code in {"ai_suggestion_not_found"}:
        return 404
    if error_code in {"action_not_allowed", "caller_type_forbidden"}:
        return 403
    if error_code in {"idempotency_key_required"}:
        return 400
    if error_code in {"P2_IDEMPOTENCY_CONFLICT", "P2_WRITING_TASK_PREREQUISITE_MISSING", "P2_OUTLINE_TARGET_CONFLICT"}:
        return 409
    if error_code == "P2_OUTLINE_AUDIT_WRITE_FAILED":
        return 503
    return 400


def _decision_error_response(request: Request, error_code: str):
    audit_failed = error_code == "P2_OUTLINE_AUDIT_WRITE_FAILED"
    return error_response(
        request,
        error_code=error_code,
        status_code=_decision_error_status(error_code),
        retryable=audit_failed,
        safe_message=_AUDIT_FAILURE_SAFE_MESSAGE if audit_failed else None,
    )


def _is_outline_assist_suggestion(service, suggestion_id: str) -> bool:  # noqa: ANN001
    classifier = getattr(service, "is_outline_assist_suggestion", None)
    if not callable(classifier):
        return False
    try:
        return classifier(suggestion_id)
    except ValueError as exc:
        if str(exc) == "ai_suggestion_not_found":
            return False
        raise


def _reject_invalid_decision_request(
    request: Request,
    payload: SuggestionDecisionRequest,
    *,
    is_outline_assist: bool = False,
):
    if payload.caller_type != "user_action":
        error_code = "P2_CALLER_FORBIDDEN" if is_outline_assist else "caller_type_forbidden"
        return error_response(request, error_code=error_code, status_code=403)
    if not payload.user_action:
        error_code = "P2_USER_ACTION_REQUIRED" if is_outline_assist else "action_not_allowed"
        return error_response(request, error_code=error_code, status_code=403)
    if not str(payload.idempotency_key or "").strip():
        error_code = "P2_IDEMPOTENCY_KEY_REQUIRED" if is_outline_assist else "idempotency_key_required"
        return error_response(request, error_code=error_code, status_code=400)
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
    service = dependencies.get_ai_suggestion_service()
    is_outline = _is_outline_assist_suggestion(service, suggestion_id)
    if is_outline and not is_outline_assist_enabled():
        return outline_assist_feature_disabled_response(request)
    denied = _reject_invalid_decision_request(request, payload, is_outline_assist=is_outline)
    if denied is not None:
        return denied
    try:
        item = service.accept_suggestion(suggestion_id, user_id=payload.user_id, user_action=payload.user_action)
    except ValueError as exc:
        error_code = str(exc)
        return _decision_error_response(request, error_code)
    return success_response(request, data=_serialize_suggestion(item))


@router.post("/api/v2/ai/suggestions/{suggestion_id}/dismiss")
def dismiss_ai_suggestion(suggestion_id: str, payload: SuggestionDecisionRequest, request: Request):
    service = dependencies.get_ai_suggestion_service()
    is_outline = _is_outline_assist_suggestion(service, suggestion_id)
    if is_outline and not is_outline_assist_enabled():
        return outline_assist_feature_disabled_response(request)
    denied = _reject_invalid_decision_request(request, payload, is_outline_assist=is_outline)
    if denied is not None:
        return denied
    try:
        item = service.dismiss_suggestion(
            suggestion_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
            note=payload.decision_note,
        )
    except ValueError as exc:
        error_code = str(exc)
        return _decision_error_response(request, error_code)
    return success_response(request, data=_serialize_suggestion(item))


@router.post("/api/v2/ai/suggestions/{suggestion_id}/convert")
def convert_ai_suggestion(suggestion_id: str, payload: SuggestionDecisionRequest, request: Request):
    service = dependencies.get_ai_suggestion_service()
    is_outline = _is_outline_assist_suggestion(service, suggestion_id)
    if is_outline and not is_outline_assist_enabled():
        return outline_assist_feature_disabled_response(request)
    denied = _reject_invalid_decision_request(request, payload, is_outline_assist=is_outline)
    if denied is not None:
        return denied
    try:
        item = service.convert_suggestion(
            suggestion_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
            idempotency_key=payload.idempotency_key,
            decision_note=payload.decision_note,
        )
    except ValueError as exc:
        error_code = str(exc)
        return _decision_error_response(request, error_code)
    return success_response(request, data=_serialize_suggestion(item))
