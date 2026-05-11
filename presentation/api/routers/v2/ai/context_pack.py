from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from domain.entities.ai.models import ContextPackBuildRequest
from presentation.api import dependencies
from presentation.api.routers.v2.ai.schemas import BuildContextPackRequest as BuildReq

router = APIRouter(prefix="/api/v2/ai/context-packs", tags=["v2-ai-context-pack"])


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


def _serialize_context_pack(snapshot) -> dict[str, object]:
    return {
        "context_pack_id": snapshot.context_pack_id,
        "work_id": snapshot.work_id,
        "chapter_id": snapshot.chapter_id,
        "source_initialization_id": snapshot.source_initialization_id,
        "source_story_memory_snapshot_id": snapshot.source_story_memory_snapshot_id,
        "source_story_state_id": snapshot.source_story_state_id,
        "status": snapshot.status.value,
        "blocked_reason": snapshot.blocked_reason,
        "degraded_reason": snapshot.degraded_reason,
        "warnings": snapshot.warnings,
        "vector_recall_status": snapshot.vector_recall_status,
        "context_items": [
            {
                "item_id": item.item_id,
                "source_type": item.source_type,
                "priority": item.priority,
                "content_text": item.content_text[:200] if item.included else "",
                "token_estimate": item.token_estimate,
                "required": item.required,
                "included": item.included,
                "trim_reason": item.trim_reason,
                "stale_status": item.stale_status,
                "warning": item.warning,
            }
            for item in snapshot.context_items
        ],
        "token_budget": snapshot.token_budget,
        "estimated_token_count": snapshot.estimated_token_count,
        "trimmed_items_count": len(snapshot.trimmed_items),
        "stale": snapshot.stale,
        "stale_reason": snapshot.stale_reason,
        "source_chapter_versions": snapshot.source_chapter_versions,
        "summary": snapshot.summary,
        "created_at": snapshot.created_at,
    }


@router.post("")
def build_context_pack(payload: BuildReq, request: Request):
    service = dependencies.get_context_pack_service()
    try:
        req = ContextPackBuildRequest(
            work_id=payload.work_id,
            chapter_id=payload.chapter_id,
            continuation_mode=payload.continuation_mode,
            user_instruction=payload.user_instruction,
            max_context_tokens=payload.max_context_tokens,
            model_role=payload.model_role,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=_trace_id(request),
            allow_degraded=payload.allow_degraded,
            is_quick_trial=payload.is_quick_trial,
        )
        snapshot = service.build_and_save(req)
        return _success(request, data=_serialize_context_pack(snapshot))
    except ValueError as exc:
        return _error(request, error_code=str(exc), status_code=400)
    except Exception as exc:
        return _error(request, error_code=str(exc), status_code=500)


@router.get("/works/{work_id}/latest")
def get_latest_context_pack(work_id: str, request: Request, chapter_id: str = ""):
    service = dependencies.get_context_pack_service()
    snapshot = service.get_latest(work_id, chapter_id=chapter_id)
    if snapshot is None:
        return _error(request, error_code="context_pack_not_found", status_code=404)
    return _success(request, data=_serialize_context_pack(snapshot))


@router.get("/works/{work_id}/readiness")
def get_context_pack_readiness(work_id: str, request: Request, chapter_id: str = ""):
    service = dependencies.get_context_pack_service()
    try:
        readiness = service.evaluate_readiness(work_id, chapter_id=chapter_id)
        return _success(request, data=readiness)
    except Exception as exc:
        return _error(request, error_code=str(exc), status_code=500)


@router.get("/{context_pack_id}")
def get_context_pack(context_pack_id: str, request: Request):
    service = dependencies.get_context_pack_service()
    try:
        snapshot = service.get(context_pack_id)
        return _success(request, data=_serialize_context_pack(snapshot))
    except ValueError as exc:
        return _error(request, error_code=str(exc), status_code=404)
