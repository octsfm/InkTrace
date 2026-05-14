from __future__ import annotations

from fastapi import APIRouter, Request

from domain.entities.ai.models import ContextPackBuildRequest
from presentation.api import dependencies
from presentation.api.routers.v2.ai.schemas import BuildContextPackRequest as BuildReq
from presentation.api.routers.v2.ai.response_utils import error_response, success_response, trace_id_from_request

router = APIRouter(prefix="/api/v2/ai/context-packs", tags=["v2-ai-context-pack"])


def _reject_invalid_caller_type(request: Request, *, caller_type: str) -> JSONResponse | None:
    if caller_type and caller_type != "user_action":
        return error_response(request, error_code="caller_type_not_allowed", status_code=403)
    return None


def _serialize_context_pack(snapshot) -> dict[str, object]:
    return {
        "context_pack_id": snapshot.context_pack_id,
        "work_id": snapshot.work_id,
        "chapter_id": snapshot.chapter_id,
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
        "created_at": snapshot.created_at,
    }


@router.post("")
def build_context_pack(payload: BuildReq, request: Request):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
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
            trace_id=trace_id_from_request(request),
            allow_degraded=payload.allow_degraded,
            allow_stale_vector=payload.allow_stale_vector,
        )
        snapshot = service.build_and_save(req)
        return success_response(
            request,
            data={
                "context_pack_id": snapshot.context_pack_id,
                "status": snapshot.status.value,
                "warnings": snapshot.warnings,
                "caller_type": payload.caller_type,
                "idempotency_key": payload.idempotency_key,
            },
        )
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=400)
    except Exception as exc:
        return error_response(request, error_code=exc.__class__.__name__, status_code=500, safe_message="internal_error")


@router.get("/works/{work_id}/latest")
def get_latest_context_pack(work_id: str, request: Request, chapter_id: str = ""):
    service = dependencies.get_context_pack_service()
    snapshot = service.get_latest(work_id, chapter_id=chapter_id)
    if snapshot is None:
        return error_response(request, error_code="context_pack_not_found", status_code=404)
    return success_response(request, data=_serialize_context_pack(snapshot))


@router.get("/works/{work_id}/readiness")
def get_context_pack_readiness(work_id: str, request: Request, chapter_id: str = ""):
    service = dependencies.get_context_pack_service()
    try:
        readiness = service.evaluate_readiness(work_id, chapter_id=chapter_id)
        return success_response(request, data=readiness)
    except Exception as exc:
        return error_response(request, error_code=exc.__class__.__name__, status_code=500, safe_message="internal_error")


@router.get("/{context_pack_id}")
def get_context_pack(context_pack_id: str, request: Request):
    service = dependencies.get_context_pack_service()
    try:
        snapshot = service.get(context_pack_id)
        return success_response(request, data=_serialize_context_pack(snapshot))
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
