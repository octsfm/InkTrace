from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel,ConfigDict
from presentation.api.routers.v2.ai.response_utils import error_response

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import success_response


router = APIRouter(prefix="/api/v2/ai/analysis-dashboard", tags=["v2-ai-analysis-dashboard"])


class RefreshRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    work_id: str
    caller_type: str="user_action"
    user_action: bool=False
    user_id: str=""
    idempotency_key: str=""


def _wrapped(data: dict[str, object]) -> dict[str, object]:
    return {
        "source": "realtime",
        "computed_at": datetime.now(UTC).isoformat(),
        "stale": False,
        "data": data,
    }


@router.get("/overview")
async def overview(work_id: str, request: Request):
    service=dependencies.get_analysis_dashboard_query_service(); data = await service.get_metric_response(work_id,"overview") if hasattr(service,"get_metric_response") else _wrapped(await service.get_writing_stats(work_id))
    return success_response(request, data=data)


@router.get("/rhythm")
async def rhythm(work_id: str, request: Request):
    service=dependencies.get_analysis_dashboard_query_service(); data = await service.get_metric_response(work_id,"rhythm") if hasattr(service,"get_metric_response") else _wrapped(await service.get_rhythm_analysis(work_id))
    return success_response(request, data=data)


@router.get("/dialogue")
async def dialogue(work_id: str, request: Request):
    service=dependencies.get_analysis_dashboard_query_service(); data = await service.get_metric_response(work_id,"dialogue") if hasattr(service,"get_metric_response") else _wrapped(await service.get_dialogue_analysis(work_id))
    return success_response(request, data=data)


@router.get("/word-frequency")
async def word_frequency(request: Request, work_id: str, top_n: int = Query(default=50, ge=10, le=200)):
    service=dependencies.get_analysis_dashboard_query_service(); data = await service.get_metric_response(work_id,"word_frequency",top_n=top_n) if hasattr(service,"get_metric_response") else _wrapped(await service.get_word_frequency(work_id,top_n=top_n))
    return success_response(request, data=data)


@router.get("/style")
async def style(work_id: str, request: Request):
    service=dependencies.get_analysis_dashboard_query_service(); data = await service.get_metric_response(work_id,"style") if hasattr(service,"get_metric_response") else _wrapped(await service.get_style_consistency(work_id))
    return success_response(request, data=data)


@router.get("/ai-usage")
async def ai_usage(work_id: str, request: Request):
    service=dependencies.get_analysis_dashboard_query_service(); data = await service.get_metric_response(work_id,"ai_usage") if hasattr(service,"get_metric_response") else _wrapped(await service.get_ai_usage_analysis(work_id))
    return success_response(request, data=data)


@router.get("/status")
def analysis_status(work_id: str,request: Request): return success_response(request,data=dependencies.get_analysis_dashboard_query_service().status(work_id))


@router.get("/recompute/status")
def recompute_status(work_id: str,request: Request):
    service=dependencies.get_analysis_dashboard_query_service()
    return success_response(request,data=service.recompute_status(work_id) if hasattr(service,"recompute_status") else {"status":"idle","progress":0.0})


@router.post("/refresh")
async def refresh_analysis(payload: RefreshRequest,request: Request):
    if payload.caller_type!="user_action" or not payload.user_action or not payload.user_id.strip(): return error_response(request,error_code="P2_CALLER_FORBIDDEN",status_code=403)
    if not payload.idempotency_key.strip(): return error_response(request,error_code="P2_IDEMPOTENCY_REQUIRED",status_code=400)
    try: data=await dependencies.get_analysis_dashboard_query_service().refresh(payload.work_id)
    except Exception: return error_response(request,error_code="P2_ANALYSIS_REFRESH_FAILED",status_code=503)
    return success_response(request,data=data)


@router.post("/recompute",status_code=202)
async def recompute_analysis(payload: RefreshRequest,request: Request):
    if payload.caller_type!="user_action" or not payload.user_action or not payload.user_id.strip(): return error_response(request,error_code="P2_CALLER_FORBIDDEN",status_code=403)
    if not payload.idempotency_key.strip(): return error_response(request,error_code="P2_IDEMPOTENCY_REQUIRED",status_code=400)
    service=dependencies.get_analysis_dashboard_query_service()
    if hasattr(service,"is_large") and not service.is_large(payload.work_id): return error_response(request,error_code="P2_ANALYSIS_REALTIME_ONLY",status_code=400)
    data=service.start_recompute(payload.work_id) if hasattr(service,"start_recompute") else {"accepted":True,"work_id":payload.work_id,"estimated_seconds":6}
    return success_response(request,data=data)
