from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response

router = APIRouter(tags=["v2-ai-plot-arcs"])


@router.get("/api/v2/ai/plot-arcs")
def list_plot_arcs(work_id: str, request: Request):
    items = dependencies.get_plot_arc_query_service().list_plot_arcs(work_id)
    return success_response(request, data={"items": items})


@router.get("/api/v2/ai/plot-arcs/status")
def get_plot_arc_status(request: Request, work_id: str, chapter_id: str = ""):
    payload = dependencies.get_plot_arc_query_service().get_plot_arc_status(work_id=work_id, chapter_id=chapter_id)
    return success_response(request, data=payload)


@router.get("/api/v2/ai/plot-arcs/{arc_id}")
def get_plot_arc(arc_id: str, request: Request, work_id: str):
    try:
        payload = dependencies.get_plot_arc_query_service().get_plot_arc(work_id=work_id, arc_id=arc_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=payload)
