from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import AISettingsUpdateRequest, ProviderConnectionTestRequest

router = APIRouter(prefix="/api/v2/ai/settings", tags=["v2-ai-settings"])


@router.get("")
def get_ai_settings(request: Request):
    service = dependencies.get_ai_settings_service()
    return success_response(request, data=service.get_public_settings())


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
        return error_response(request, error_code=error_code, safe_message="invalid_input")
    return success_response(request, data=data)


@router.post("/providers/{provider_name}/test")
def test_provider_connection(provider_name: str, payload: ProviderConnectionTestRequest, request: Request):
    service = dependencies.get_ai_settings_service()
    try:
        data = service.test_provider_connection(provider_name=provider_name, model_name=payload.model_name)
    except Exception as exc:
        error_code = getattr(exc, "error_code", str(exc) or "provider_unknown_error")
        status_code = 404 if error_code == "provider_not_found" else 400
        return error_response(request, error_code=error_code, status_code=status_code, safe_message=error_code)
    return success_response(request, data=data)
