from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import AISettingsUpdateRequest, ProviderConnectionTestRequest

router = APIRouter(prefix="/api/v2/ai/settings", tags=["v2-ai-settings"])


def _ensure_gate_request(request: Request, *, caller_type: str, user_action: bool, idempotency_key: str):
    if caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    if not user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


@router.get("")
def get_ai_settings(request: Request):
    service = dependencies.get_ai_settings_service()
    return success_response(request, data=service.get_public_settings())


@router.put("")
def update_ai_settings(payload: AISettingsUpdateRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_ai_settings_service()
    try:
        data = service.update_settings(
            provider_configs=[item.model_dump(mode="json") for item in payload.provider_configs],
            model_role_mappings={key: value.model_dump(mode="json") for key, value in payload.model_role_mappings.items()},
        )
    except Exception as exc:
        error_code = getattr(exc, "error_code", str(exc) or "invalid_input")
        return error_response(request, error_code=error_code, safe_message=error_code)
    return success_response(request, data=data)


@router.post("/providers/{provider_name}/test")
def test_provider_connection(provider_name: str, payload: ProviderConnectionTestRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_ai_settings_service()
    try:
        data = service.test_provider_connection(provider_name=provider_name, model_name=payload.model_name)
    except Exception as exc:
        error_code = getattr(exc, "error_code", str(exc) or "provider_unknown_error")
        status_code = 404 if error_code in {"provider_not_found", "provider_config_missing"} else 400
        return error_response(request, error_code=error_code, status_code=status_code, safe_message=error_code)
    return success_response(request, data=data)
