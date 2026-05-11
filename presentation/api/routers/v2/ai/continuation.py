from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from presentation.api import dependencies
from presentation.api.routers.v2.ai.schemas import StartContinuationRequest

router = APIRouter(tags=["v2-ai-continuation"])


def _trace_id(request: Request) -> str:
    header_value = request.headers.get("X-Trace-Id", "").strip()
    return header_value or f"trace_{uuid.uuid4().hex[:12]}"


def _success(request: Request, *, data: dict[str, object]) -> dict[str, object]:
    return {
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": _trace_id(request),
        "status": "ok",
        "data": data,
    }


def _error(request: Request, *, error_code: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": getattr(request.state, "request_id", ""),
            "trace_id": _trace_id(request),
            "status": "error",
            "error": {
                "error_code": error_code,
                "safe_message": error_code,
                "retryable": False,
            },
        },
    )


def _serialize_candidate_summary(draft) -> dict[str, object]:
    return {
        "candidate_draft_id": draft.candidate_draft_id,
        "work_id": draft.work_id,
        "chapter_id": draft.chapter_id,
        "source_context_pack_id": draft.source_context_pack_id,
        "source_job_id": draft.source_job_id,
        "status": draft.status.value,
        "content_preview": draft.content_preview,
        "word_count": draft.word_count,
        "char_count": draft.char_count,
        "validation_status": draft.validation_status.value,
        "validation_errors": draft.validation_errors,
        "writer_model_role": draft.writer_model_role,
        "provider_name": draft.provider_name,
        "model_name": draft.model_name,
        "created_by": draft.created_by,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
        "metadata": draft.metadata,
    }


def _serialize_candidate_detail(draft) -> dict[str, object]:
    payload = _serialize_candidate_summary(draft)
    payload["content"] = draft.content
    return payload


@router.post("/api/v2/ai/continuations")
def start_continuation(payload: StartContinuationRequest, request: Request):
    workflow = dependencies.get_continuation_workflow()
    try:
        result = workflow.start_continuation(
            payload.work_id,
            payload.chapter_id,
            user_instruction=payload.user_instruction,
            created_by="user_action",
        )
        return _success(
            request,
            data={
                "workflow_id": result.workflow_id,
                "job_id": result.job_id,
                "writing_task_id": result.writing_task_id,
                "candidate_draft_id": result.candidate_draft_id,
                "status": result.status,
                "warnings": result.warnings,
                "error_code": result.error_code,
            },
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code in {"work_not_found", "chapter_not_found"} else 400
        return _error(request, error_code=error_code, status_code=status_code)


@router.get("/api/v2/ai/candidate-drafts")
def list_candidate_drafts(work_id: str, request: Request, chapter_id: str = ""):
    workflow = dependencies.get_continuation_workflow()
    try:
        drafts = workflow.list_candidate_drafts(work_id, chapter_id=chapter_id or None)
    except ValueError as exc:
        return _error(request, error_code=str(exc), status_code=400)
    return _success(request, data={"items": [_serialize_candidate_summary(item) for item in drafts]})


@router.get("/api/v2/ai/candidate-drafts/{candidate_draft_id}")
def get_candidate_draft(candidate_draft_id: str, request: Request):
    workflow = dependencies.get_continuation_workflow()
    try:
        draft = workflow.get_candidate_draft(candidate_draft_id)
    except ValueError as exc:
        return _error(request, error_code=str(exc), status_code=404)
    return _success(request, data=_serialize_candidate_detail(draft))
