from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import (
    ApplyOutlineSuggestionRequest,
    ChapterOutlineAssistRequest,
    OutlineExpandRequest,
    OutlinePolishRequest,
    WritingTaskAssistRequest,
)


router = APIRouter(tags=["v2-ai-outline-assist"])

_AUDIT_FAILURE_SAFE_MESSAGE = "安全记录暂时失败，本次操作没有生效，请稍后重试。"

_STATUS = {
    "P2_CALLER_FORBIDDEN": 403,
    "P2_USER_ACTION_REQUIRED": 403,
    "P2_IDEMPOTENCY_KEY_REQUIRED": 400,
    "P2_IDEMPOTENCY_CONFLICT": 409,
    "P2_OUTLINE_TARGET_REQUIRED": 400,
    "P2_OUTLINE_TARGET_NOT_FOUND": 404,
    "P2_OUTLINE_TARGET_CONFLICT": 409,
    "P2_OUTLINE_SUGGESTION_NOT_FOUND": 404,
    "P2_OUTLINE_SUGGESTION_NOT_ACCEPTED": 409,
    "P2_OUTLINE_SUGGESTION_TYPE_UNSUPPORTED": 400,
    "P2_OUTLINE_APPLY_CONFIRMATION_REQUIRED": 400,
    "P2_OUTLINE_CONFLICT_REVIEW_REQUIRED": 409,
    "P2_OUTLINE_CONFLICT_CHECK_FAILED": 503,
    "P2_OUTLINE_AUDIT_WRITE_FAILED": 503,
    "P2_WRITING_TASK_PREREQUISITE_MISSING": 409,
}


def _error(request: Request, exc: ValueError):
    code = str(exc)
    audit_failed = code == "P2_OUTLINE_AUDIT_WRITE_FAILED"
    return error_response(
        request,
        error_code=code,
        status_code=_STATUS.get(code, 400),
        retryable=code in {"P2_OUTLINE_CONFLICT_CHECK_FAILED", "P2_OUTLINE_AUDIT_WRITE_FAILED"},
        safe_message=_AUDIT_FAILURE_SAFE_MESSAGE if audit_failed else None,
        data={"record_refs": list(getattr(exc, "record_refs", []))} if getattr(exc, "record_refs", None) else None,
    )


def _launch_data(result) -> dict[str, object]:  # noqa: ANN001
    return result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)


@router.post("/api/v2/ai/outline-assist/polish", status_code=202)
def polish_outline(payload: OutlinePolishRequest, request: Request):
    try:
        result = dependencies.get_outline_assist_service().start_polish(
            work_id=payload.work_id,
            target_kind=payload.target_kind,
            target_id=payload.target_id,
            target_revision=payload.target_revision,
            selected_text=payload.selected_text,
            caller_type=payload.caller_type,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        return _error(request, exc)
    return success_response(request, data=_launch_data(result))


@router.post("/api/v2/ai/outline-assist/expand", status_code=202)
def expand_outline(payload: OutlineExpandRequest, request: Request):
    try:
        result = dependencies.get_outline_assist_service().start_expand(
            work_id=payload.work_id,
            target_kind=payload.target_kind,
            target_id=payload.target_id,
            target_revision=payload.target_revision,
            selected_text=payload.selected_text,
            expand_focus=payload.expand_focus,
            caller_type=payload.caller_type,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        return _error(request, exc)
    return success_response(request, data=_launch_data(result))


@router.post("/api/v2/ai/outline-assist/chapter-outline", status_code=202)
def chapter_outline(payload: ChapterOutlineAssistRequest, request: Request):
    try:
        result = dependencies.get_outline_assist_service().start_chapter_outline(
            work_id=payload.work_id,
            target_kind=payload.target_kind,
            target_id=payload.target_id,
            target_revision=payload.target_revision,
            chapter_goal=payload.chapter_goal,
            caller_type=payload.caller_type,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        return _error(request, exc)
    return success_response(request, data=_launch_data(result))


@router.post("/api/v2/ai/outline-assist/writing-task", status_code=202)
def writing_task(payload: WritingTaskAssistRequest, request: Request):
    try:
        result = dependencies.get_outline_assist_service().start_writing_task_suggestion(
            work_id=payload.work_id,
            chapter_id=payload.chapter_id,
            target_revision=payload.target_revision,
            caller_type=payload.caller_type,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        return _error(request, exc)
    return success_response(request, data=_launch_data(result))


@router.post("/api/v2/ai/outline-assist/suggestions/{suggestion_id}/apply")
def apply_outline_suggestion(suggestion_id: str, payload: ApplyOutlineSuggestionRequest, request: Request):
    try:
        result = dependencies.get_outline_application_service().apply_suggestion(
            suggestion_id=suggestion_id,
            caller_type=payload.caller_type,
            user_action=payload.user_action,
            user_id=payload.user_id,
            idempotency_key=payload.idempotency_key,
            confirm_apply=payload.confirm_apply,
            target_revision=payload.target_revision,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
        )
    except ValueError as exc:
        return _error(request, exc)
    return success_response(request, data=result.to_dict())
