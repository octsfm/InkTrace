from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response

router = APIRouter(tags=["v2-ai-traces"])


def _serialize_trace(trace) -> dict[str, object]:  # noqa: ANN001
    return trace.model_dump(mode="json")


@router.get("/api/v2/ai/traces")
def list_agent_traces(request: Request, work_id: str = "", chapter_id: str = "", session_id: str = "", status: str = ""):
    service = dependencies.get_agent_trace_service()
    items = service.list_traces(work_id=work_id, chapter_id=chapter_id, session_id=session_id, status=status)
    return success_response(request, data={"items": [_serialize_trace(item) for item in items]})


@router.get("/api/v2/ai/traces/{trace_id}")
def get_agent_trace(trace_id: str, request: Request):
    service = dependencies.get_agent_trace_service()
    try:
        trace = service.get_trace(trace_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_trace(trace))


@router.get("/api/v2/ai/traces/{trace_id}/steps")
def list_agent_trace_steps(trace_id: str, request: Request):
    service = dependencies.get_agent_trace_service()
    try:
        service.get_trace(trace_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(
        request,
        data={"items": [item.model_dump(mode="json") for item in service.list_step_traces(trace_id)]},
    )


@router.get("/api/v2/ai/traces/{trace_id}/detail-view")
def get_agent_trace_detail_view(trace_id: str, request: Request, detail: bool = False, developer_mode: bool = False):
    service = dependencies.get_agent_trace_service()
    try:
        if not detail:
            raise ValueError("invalid_request")
        payload = service.get_detail_view(trace_id, developer_mode=developer_mode)
    except ValueError as exc:
        error_code = str(exc)
        status_code = 403 if error_code == "permission_denied" else (404 if error_code == "trace_not_found" else 400)
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(
        request,
        data={
            "trace": payload["trace"].model_dump(mode="json"),
            "events": [item.model_dump(mode="json") for item in payload["events"]],
            "steps": [item.model_dump(mode="json") for item in payload["steps"]],
            "tool_calls": [item.model_dump(mode="json") for item in payload["tool_calls"]],
            "observations": [item.model_dump(mode="json") for item in payload["observations"]],
            "llm_calls": [item.model_dump(mode="json") for item in payload["llm_calls"]],
            "user_decisions": [item.model_dump(mode="json") for item in payload["user_decisions"]],
            "metrics": [item.model_dump(mode="json") for item in payload["metrics"]],
            "alerts": [item.model_dump(mode="json") for item in payload["alerts"]],
        },
    )
