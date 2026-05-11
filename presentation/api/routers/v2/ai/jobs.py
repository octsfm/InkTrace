from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from presentation.api import dependencies
from presentation.api.routers.v2.ai.schemas import CancelAIJobRequest

router = APIRouter(prefix="/api/v2/ai/jobs", tags=["v2-ai-jobs"])


def _trace_id(request: Request) -> str:
    header_value = request.headers.get("X-Trace-Id", "").strip()
    return header_value or f"trace_{uuid.uuid4().hex[:12]}"


def _success(request: Request, *, data: dict[str, object]) -> dict[str, object]:
    return {
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": _trace_id(request),
        "status": "ok",
        "data": data,
        "polling_hint": {
            "next_poll_after_ms": 2000,
            "max_poll_interval_ms": 5000,
            "still_running_message": "job_still_running",
        },
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


def _serialize_job(job) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "work_id": job.work_id,
        "chapter_id": job.chapter_id,
        "job_type": job.job_type,
        "status": job.status.value,
        "progress": job.progress.model_dump(mode="json"),
        "error_code": job.error_code,
        "error_message": job.error_message,
        "result_ref": job.result_ref,
        "result_summary": job.result_summary,
        "status_reason": job.status_reason,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "cancelled_at": job.cancelled_at,
    }


def _serialize_step(step) -> dict[str, object]:
    return {
        "step_id": step.step_id,
        "step_type": step.step_type,
        "step_name": step.step_name,
        "status": step.status.value,
        "progress": step.progress,
        "attempt_no": step.attempt_count,
        "max_attempts": step.max_attempts,
        "error_code": step.error_code,
        "error_message": step.error_message,
        "can_retry": step.can_retry,
        "can_skip": step.can_skip,
        "updated_at": step.finished_at or step.started_at or "",
    }


@router.get("")
def list_ai_jobs(request: Request, work_id: str | None = None, status: str | None = None):
    service = dependencies.get_ai_job_service()
    items = [_serialize_job(job) for job in service.list_jobs(work_id=work_id, status=status)]
    return _success(request, data={"items": items})


@router.get("/{job_id}")
def get_ai_job(job_id: str, request: Request):
    service = dependencies.get_ai_job_service()
    try:
        return _success(request, data=_serialize_job(service.get_job(job_id)))
    except ValueError as exc:
        return _error(request, error_code=str(exc), status_code=404)


@router.get("/{job_id}/steps")
def get_ai_job_steps(job_id: str, request: Request):
    service = dependencies.get_ai_job_service()
    try:
        steps = [_serialize_step(step) for step in service.get_job_steps(job_id)]
        return _success(request, data={"job_id": job_id, "steps": steps})
    except ValueError as exc:
        return _error(request, error_code=str(exc), status_code=404)


@router.post("/{job_id}/cancel")
def cancel_ai_job(job_id: str, payload: CancelAIJobRequest, request: Request):
    service = dependencies.get_ai_job_service()
    try:
        job = service.cancel_job(job_id, reason=payload.reason)
        return _success(request, data=_serialize_job(job))
    except ValueError as exc:
        return _error(request, error_code=str(exc), status_code=404)
