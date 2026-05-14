from __future__ import annotations

from fastapi import APIRouter, Request

from domain.entities.ai.models import QuickTrialRequest
from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import QuickTrialRunRequest

router = APIRouter(tags=["v2-ai-quick-trial"])


def _reject_invalid_caller_type(request: Request, *, caller_type: str) -> object | None:
    if caller_type and caller_type != "user_action":
        return error_response(request, error_code="caller_type_not_allowed", status_code=403)
    return None


@router.post("/api/v2/ai/quick-trials")
def run_quick_trial(payload: QuickTrialRunRequest, request: Request):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
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
                created_by=payload.caller_type or payload.created_by,
                metadata={
                    **payload.metadata,
                    "caller_type": payload.caller_type,
                    "idempotency_key": payload.idempotency_key,
                },
            )
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code == "provider_not_found" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(
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
            "caller_type": payload.caller_type,
            "idempotency_key": payload.idempotency_key,
        },
    )
