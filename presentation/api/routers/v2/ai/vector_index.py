from __future__ import annotations

import threading

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import V2AIBaseModel

router = APIRouter(prefix="/api/v2/ai/vector-index", tags=["v2-ai-vector-index"])


class ReindexRequest(V2AIBaseModel):
    work_id: str
    index_scope: str
    target_chapter_ids: list[str] | None = None
    idempotency_key: str = Field(default="", max_length=256)
    force_rebuild: bool = False
    reason: str = Field(default="", max_length=500)
    caller_type: str = "user_action"


def _reject_invalid_caller_type(request: Request, *, caller_type: str) -> JSONResponse | None:
    if caller_type and caller_type != "user_action":
        return error_response(request, error_code="P2_VECTOR_CALLER_FORBIDDEN", status_code=403)
    return None


def _parse_job_targets(job) -> list[str]:
    raw_value = str(job.payload.get("target_chapter_ids_csv", "") or "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _polling_hint() -> dict[str, object]:
    return {
        "next_poll_after_ms": 3000,
        "max_poll_interval_ms": 10000,
        "timeout_hint_ms": 300000,
        "still_running_message": "索引重建中，请耐心等待。",
    }


def _build_response_data(request: Request, job, *, reused_existing_job: bool) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "operation": "reindex",
        "work_id": job.work_id,
        "index_scope": str(job.payload.get("index_scope", "") or ""),
        "target_chapter_ids": _parse_job_targets(job),
        "status": job.status.value,
        "created_at": job.created_at,
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": request.headers.get("X-Trace-Id", "").strip(),
        "polling_hint": _polling_hint(),
        "reused_existing_job": reused_existing_job,
    }


def _validate_request(payload: ReindexRequest) -> str | None:
    if payload.index_scope not in {"full_work", "chapter"}:
        return "P2_VECTOR_INVALID_INDEX_SCOPE"
    target_chapter_ids = list(payload.target_chapter_ids or [])
    if payload.index_scope == "chapter" and not target_chapter_ids:
        return "P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED"
    if payload.index_scope == "full_work" and target_chapter_ids:
        return "P2_VECTOR_TARGET_CHAPTER_IDS_NOT_ALLOWED"
    if len(target_chapter_ids) > 50:
        return "P2_VECTOR_TOO_MANY_CHAPTERS"
    return None


def _validate_work_and_chapters(payload: ReindexRequest) -> str | None:
    work_service = dependencies.get_work_service()
    chapter_service = dependencies.get_chapter_service()
    try:
        work_service.get_work(payload.work_id)
    except ValueError:
        return "P2_VECTOR_WORK_NOT_FOUND"
    seen: set[str] = set()
    for chapter_id in payload.target_chapter_ids or []:
        normalized = str(chapter_id or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        chapter = chapter_service.chapter_repo.find_by_id(normalized)
        if chapter is None:
            return "P2_VECTOR_CHAPTER_NOT_FOUND"
        if chapter.work_id.value != payload.work_id:
            return "P2_VECTOR_CHAPTER_NOT_IN_WORK"
    return None


def _validate_runtime_dependencies() -> str | None:
    try:
        provider = dependencies.get_embedding_provider()
        provider.get_embedding_model_info()
    except Exception:
        return "P2_VECTOR_EMBEDDING_UNAVAILABLE"
    try:
        dependencies.get_vector_store()
    except Exception:
        return "P2_VECTOR_STORE_UNAVAILABLE"
    return None


def _run_reindex_async(job_id: str) -> None:
    service = dependencies.get_vector_reindex_service()
    try:
        service.run_reindex(job_id)
    except Exception:
        # Job failure is persisted in service layer; background runner should not crash the request thread.
        return


@router.post("/reindex")
def start_reindex(payload: ReindexRequest, request: Request):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied

    validation_error = _validate_request(payload)
    if validation_error is not None:
        return error_response(request, error_code=validation_error, status_code=400)

    relation_error = _validate_work_and_chapters(payload)
    if relation_error is not None:
        status_code = 404 if relation_error in {"P2_VECTOR_WORK_NOT_FOUND", "P2_VECTOR_CHAPTER_NOT_FOUND"} else 400
        return error_response(request, error_code=relation_error, status_code=status_code)

    runtime_error = _validate_runtime_dependencies()
    if runtime_error is not None:
        return error_response(request, error_code=runtime_error, status_code=503, retryable=True)

    service = dependencies.get_vector_reindex_service()
    try:
        job = service.start_reindex(
            work_id=payload.work_id,
            index_scope=payload.index_scope,
            target_chapter_ids=payload.target_chapter_ids,
            created_by=payload.caller_type,
            idempotency_key=payload.idempotency_key,
            force_rebuild=payload.force_rebuild,
            reason=payload.reason,
            auto_run=False,
        )
    except ValueError as exc:
        error_code = str(exc)
        if error_code == "P2_VECTOR_INDEXING_IN_PROGRESS":
            return error_response(request, error_code=error_code, status_code=409, retryable=True)
        if error_code == "P2_VECTOR_IDEMPOTENCY_CONFLICT":
            return error_response(request, error_code=error_code, status_code=409)
        if error_code == "target_chapter_ids_required":
            return error_response(request, error_code="P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED", status_code=400)
        if error_code == "invalid_index_scope":
            return error_response(request, error_code="P2_VECTOR_INVALID_INDEX_SCOPE", status_code=400)
        if error_code == "work_not_found":
            return error_response(request, error_code="P2_VECTOR_WORK_NOT_FOUND", status_code=404)
        return error_response(request, error_code="P2_VECTOR_REINDEX_FAILED", status_code=500, retryable=True)

    reused_existing_job = bool(dict(job.metadata or {}).get("reused_existing_job", False))
    if not reused_existing_job:
        threading.Thread(target=_run_reindex_async, args=(job.job_id,), daemon=True).start()
    payload_body = success_response(
        request,
        data=_build_response_data(request, job, reused_existing_job=reused_existing_job),
        extra={},
    )
    return JSONResponse(status_code=200 if reused_existing_job else 202, content=payload_body)
