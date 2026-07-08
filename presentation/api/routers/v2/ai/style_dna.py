from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from domain.entities.ai.models import StyleProfileStatus
from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import V2AIBaseModel, V2AIOperationRequest

router = APIRouter(prefix="/api/v2/ai/style-dna", tags=["v2-ai-style-dna"])


class ExtractStyleDNARequest(V2AIBaseModel):
    work_id: str
    source_text: str
    source_type: str
    source_ref: str = ""
    caller_type: str = "user_action"
    idempotency_key: str = Field(default="", max_length=256)


def _reject_invalid_caller_type(request: Request, *, caller_type: str) -> JSONResponse | None:
    if caller_type and caller_type != "user_action":
        return error_response(request, error_code="P2_CALLER_FORBIDDEN", status_code=403)
    return None


def _polling_hint() -> dict[str, object]:
    return {
        "next_poll_after_ms": 3000,
        "max_poll_interval_ms": 10000,
        "timeout_hint_ms": 60000,
        "still_running_message": "风格画像提取中，请稍候查看结果。",
    }


def _serialize_profile(profile) -> dict[str, object]:
    return {
        "profile_id": profile.profile_id,
        "work_id": profile.work_id,
        "source_type": profile.source_type.value,
        "source_ref": profile.source_ref,
        "source_text_hash": profile.source_text_hash,
        "source_text_length": profile.source_text_length,
        "confidence": profile.confidence,
        "low_confidence_reason": profile.low_confidence_reason,
        "avg_sentence_length": profile.avg_sentence_length,
        "sentence_length_variance": profile.sentence_length_variance,
        "short_sentence_ratio": profile.short_sentence_ratio,
        "long_sentence_ratio": profile.long_sentence_ratio,
        "compound_sentence_ratio": profile.compound_sentence_ratio,
        "avg_paragraph_length": profile.avg_paragraph_length,
        "paragraph_length_variance": profile.paragraph_length_variance,
        "dialogue_ratio": profile.dialogue_ratio,
        "psychological_ratio": profile.psychological_ratio,
        "action_ratio": profile.action_ratio,
        "description_ratio": profile.description_ratio,
        "narrative_perspective": profile.narrative_perspective,
        "tense_preference": profile.tense_preference,
        "style_summary": profile.style_summary,
        "style_tags": list(profile.style_tags),
        "version": profile.version,
        "status": profile.status.value,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "confirmed_at": profile.confirmed_at,
    }


def _run_extract_async(
    job_id: str,
    *,
    job_service,
    style_service,
    work_id: str,
    source_text: str,
    source_type: str,
    source_ref: str,
) -> None:
    try:
        job_service.start_job(job_id)
        step = job_service.get_job_steps(job_id)[0]
        job_service.mark_step_running(job_id, step.step_id)
        result = asyncio.run(
            style_service.extract(
                work_id=work_id,
                source_text=source_text,
                source_type=source_type,
                source_ref=source_ref,
            )
        )
        warning_count = max(len(result.warnings), 1 if result.confidence < 0.5 else 0)
        job_service.mark_step_completed(
            job_id,
            step.step_id,
            summary=f"profile:{result.profile.profile_id}",
            warning_count=warning_count,
            status_reason="P2_STYLE_LOW_CONFIDENCE" if result.confidence < 0.5 else "",
        )
        result_summary = {
            "profile_id": result.profile.profile_id,
            "profile_status": result.profile.status.value,
            "confidence": result.confidence,
            "warnings": list(result.warnings),
        }
        if result.confidence < 0.5:
            result_summary["warning_code"] = "P2_STYLE_LOW_CONFIDENCE"
        job_service.mark_job_completed(
            job_id,
            result_summary=result_summary,
            result_ref=f"style_profile:{result.profile.profile_id}",
        )
    except Exception as exc:
        try:
            steps = job_service.get_job_steps(job_id)
            if steps:
                job_service.mark_step_failed(
                    job_id,
                    steps[0].step_id,
                    error_code="style_dna_extract_failed",
                    error_message=str(exc),
                )
        except Exception:
            pass
        try:
            job_service.mark_job_failed(
                job_id,
                error_code="style_dna_extract_failed",
                error_message=str(exc),
            )
        except Exception:
            pass


@router.post("/extract")
def extract_style_dna(payload: ExtractStyleDNARequest, request: Request, background_tasks: BackgroundTasks):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
    if not str(payload.source_text or "").strip():
        return error_response(request, error_code="style_dna_source_text_empty", status_code=400)

    job_service = dependencies.get_ai_job_service()
    style_service = dependencies.get_style_dna_service()
    job = job_service.create_job(
        job_type="style_dna_extraction",
        work_id=payload.work_id,
        created_by=payload.caller_type or "user_action",
        idempotency_key=payload.idempotency_key,
        payload={
            "work_id": payload.work_id,
            "source_type": payload.source_type,
            "source_ref": payload.source_ref,
        },
        steps=[
            {
                "step_type": "extract_style_dna",
                "step_name": "Extract Style DNA",
            }
        ],
    )
    background_tasks.add_task(
        _run_extract_async,
        job.job_id,
        job_service=job_service,
        style_service=style_service,
        work_id=payload.work_id,
        source_text=payload.source_text,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
    )
    return JSONResponse(
        status_code=202,
        content=success_response(
            request,
            data={
                "job_id": job.job_id,
                "job_type": job.job_type,
                "operation": "extract",
                "work_id": payload.work_id,
                "status": job.status.value,
                "polling_hint": _polling_hint(),
            },
        ),
    )


@router.get("/profiles/{profile_id}")
def get_style_profile(profile_id: str, request: Request):
    service = dependencies.get_style_dna_service()
    try:
        profile = service.get_profile(profile_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"profile": _serialize_profile(profile)})


@router.get("/{work_id}/active")
def get_active_style_profile(work_id: str, request: Request):
    service = dependencies.get_style_dna_service()
    profile = service.get_active(work_id)
    return success_response(request, data={"profile": _serialize_profile(profile) if profile is not None else None})


@router.get("/{work_id}/history")
def get_style_profile_history(work_id: str, request: Request):
    service = dependencies.get_style_dna_service()
    profiles = service.get_history(work_id)
    return success_response(request, data={"profiles": [_serialize_profile(item) for item in profiles]})


@router.post("/profiles/{profile_id}/confirm")
def confirm_style_profile(profile_id: str, payload: V2AIOperationRequest, request: Request):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
    service = dependencies.get_style_dna_service()
    try:
        profile = service.confirm(profile_id)
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code == "style_profile_not_found" else 409 if error_code == "profile_not_confirmable" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(request, data={"profile": _serialize_profile(profile)})


@router.post("/profiles/{profile_id}/disable")
def disable_style_profile(profile_id: str, payload: V2AIOperationRequest, request: Request):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
    service = dependencies.get_style_dna_service()
    try:
        profile = service.disable(profile_id)
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code == "style_profile_not_found" else 409 if error_code == "profile_not_disableable" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(request, data={"profile": _serialize_profile(profile)})


@router.delete("/profiles/{profile_id}")
def delete_style_profile(profile_id: str, payload: V2AIOperationRequest, request: Request):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
    service = dependencies.get_style_dna_service()
    try:
        profile = service.get_profile(profile_id)
        service.delete(profile_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    deleted_status = (
        "deleted" if profile.status in {StyleProfileStatus.PENDING_CONFIRM, StyleProfileStatus.DRAFT} else "archived"
    )
    return success_response(request, data={"deleted": True, "status": deleted_status})
