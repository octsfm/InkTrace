from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from domain.entities.ai.models import QuickTrialRequest
from presentation.api import dependencies
from presentation.api.routers.v2.ai.schemas import QuickTrialRunRequest

router = APIRouter(tags=["v2-ai-quick-trial"])


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


@router.post("/api/v2/ai/quick-trials")
def run_quick_trial(payload: QuickTrialRunRequest, request: Request):
    service = dependencies.get_quick_trial_service()
    try:
        result = service.run_quick_trial(
            QuickTrialRequest(
                model_role=payload.model_role,
                provider_name=payload.provider_name,
                model_name=payload.model_name,
                input_text=payload.input_text,
                system_prompt=payload.system_prompt,
                output_schema_key=payload.output_schema_key,
                max_output_chars=payload.max_output_chars,
                created_by=payload.created_by,
                metadata=payload.metadata,
            )
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code == "provider_not_found" else 400
        return _error(request, error_code=error_code, status_code=status_code)
    return _success(
        request,
        data={
            "trial_id": result.trial_id,
            "status": result.status,
            "output_text": result.output_text,
            "output_preview": result.output_preview,
            "validation_status": result.validation_status,
            "validation_errors": result.validation_errors,
            "provider_name": result.provider_name,
            "model_name": result.model_name,
            "model_role": result.model_role,
            "request_id": result.request_id,
            "created_at": result.created_at,
            "metadata": result.metadata,
        },
    )
