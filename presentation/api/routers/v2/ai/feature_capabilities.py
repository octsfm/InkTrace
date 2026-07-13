from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response


router = APIRouter(prefix="/api/v2/ai/feature-capabilities", tags=["v2-ai-feature-capabilities"])


class FeaturePreferenceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    caller_type: str = "user_action"
    user_action: bool = False
    idempotency_key: str = ""


@router.get("")
def list_feature_capabilities(request: Request):
    return success_response(request, data=dependencies.get_feature_capability_service().list_capabilities())


@router.put("/{feature_key}")
def update_feature_preference(feature_key: str, payload: FeaturePreferenceUpdateRequest, request: Request):
    if payload.caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    if not payload.user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not payload.idempotency_key.strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    try:
        data = dependencies.get_feature_capability_service().update_preference(
            feature_key=feature_key,
            enabled=payload.enabled,
            idempotency_key=payload.idempotency_key,
        )
    except Exception as exc:
        error_code = getattr(exc, "error_code", str(exc) or "invalid_input")
        status_code = 503 if error_code == "P2_FEATURE_DISABLED" else 409 if error_code == "idempotency_conflict" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(request, data=data)
