from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from presentation.api import dependencies
from presentation.api.routers.v2.ai.schemas import AISettingsUpdateRequest, ProviderConnectionTestRequest

router = APIRouter(prefix="/api/v2/ai/settings", tags=["v2-ai-settings"])


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


def _error(request: Request, *, error_code: str, status_code: int = 400, retryable: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": getattr(request.state, "request_id", ""),
            "trace_id": _trace_id(request),
            "status": "error",
            "error": {
                "error_code": error_code,
                "safe_message": error_code,
                "retryable": retryable,
            },
        },
    )


@router.get("")
def get_ai_settings(request: Request):
    service = dependencies.get_ai_settings_service()
    return _success(request, data=service.get_public_settings())


@router.put("")
def update_ai_settings(payload: AISettingsUpdateRequest, request: Request):
    service = dependencies.get_ai_settings_service()
    try:
        data = service.update_settings(
            provider_configs=[item.model_dump(mode="json") for item in payload.provider_configs],
            model_role_mappings={key: value.model_dump(mode="json") for key, value in payload.model_role_mappings.items()},
        )
    except Exception as exc:
        error_code = getattr(exc, "error_code", str(exc) or "invalid_input")
        return _error(request, error_code=error_code)
    return _success(request, data=data)


@router.post("/providers/{provider_name}/test")
def test_provider_connection(provider_name: str, payload: ProviderConnectionTestRequest, request: Request):
    service = dependencies.get_ai_settings_service()
    try:
        data = service.test_provider_connection(provider_name=provider_name, model_name=payload.model_name)
    except Exception as exc:
        error_code = getattr(exc, "error_code", str(exc) or "provider_unknown_error")
        status_code = 404 if error_code == "provider_not_found" else 400
        return _error(request, error_code=error_code, status_code=status_code)
    return _success(request, data=data)
