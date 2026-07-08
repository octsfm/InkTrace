from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import (
    AcceptCandidateDraftRequest,
    ApplyCandidateDraftRequest,
    RejectCandidateDraftRequest,
    RewriteCandidateDraftRequest,
    SelectCandidateDraftVersionRequest,
    StartContinuationRequest,
)

router = APIRouter(tags=["v2-ai-continuation"])


def _serialize_candidate_summary(draft) -> dict[str, object]:
    return {
        "candidate_draft_id": draft.candidate_draft_id,
        "work_id": draft.work_id,
        "chapter_id": draft.chapter_id,
        "agent_session_id": draft.agent_session_id,
        "writing_task_id": draft.writing_task_id,
        "direction_plan_snapshot_id": draft.direction_plan_snapshot_id,
        "source_context_pack_id": draft.source_context_pack_id,
        "source_job_id": draft.source_job_id,
        "status": draft.status.value,
        "selected_version_id": draft.selected_version_id,
        "accepted_version_id": draft.accepted_version_id,
        "applied_version_id": draft.applied_version_id,
        "latest_version_no": draft.latest_version_no,
        "revision_round": draft.revision_round,
        "max_revision_rounds": draft.max_revision_rounds,
        "warning_codes": draft.warning_codes,
        "stale_status": draft.stale_status,
        "content_preview": draft.content_preview,
        "word_count": draft.word_count,
        "char_count": draft.char_count,
        "validation_status": draft.validation_status.value,
        "validation_errors": draft.validation_errors,
        "writer_model_role": draft.writer_model_role,
        "provider_name": draft.provider_name,
        "model_name": draft.model_name,
        "created_by": draft.created_by,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
        "request_id": draft.request_id,
        "trace_id": draft.trace_id,
        "metadata": draft.metadata,
    }


def _serialize_candidate_detail(draft) -> dict[str, object]:
    payload = _serialize_candidate_summary(draft)
    payload["content"] = draft.content
    return payload


def _serialize_candidate_version(version) -> dict[str, object]:
    return {
        "candidate_version_id": version.candidate_version_id,
        "candidate_draft_id": version.candidate_draft_id,
        "work_id": version.work_id,
        "chapter_id": version.chapter_id,
        "agent_session_id": version.agent_session_id,
        "source_candidate_draft_id": version.source_candidate_draft_id,
        "source_version_id": version.source_version_id,
        "parent_version_id": version.parent_version_id,
        "version_no": version.version_no,
        "status": version.status.value,
        "content_ref": version.content_ref,
        "text_ref": version.text_ref,
        "content": version.content,
        "content_summary": version.content_summary,
        "word_count": version.word_count,
        "writing_task_id": version.writing_task_id,
        "direction_plan_snapshot_id": version.direction_plan_snapshot_id,
        "source_context_pack_id": version.source_context_pack_id,
        "review_report_id": version.review_report_id,
        "warning_codes": version.warning_codes,
        "stale_status": version.stale_status,
        "created_by": version.created_by,
        "created_at": version.created_at,
        "updated_at": version.updated_at,
        "request_id": version.request_id,
        "trace_id": version.trace_id,
    }


def _candidate_error_status(error_code: str) -> int:
    if error_code in {"candidate_draft_not_found", "chapter_not_found", "work_not_found"}:
        return 404
    if error_code in {"candidate_version_not_found", "rewrite_request_not_found", "revision_round_not_found"}:
        return 404
    if error_code in {"user_confirmation_required"}:
        return 403
    if error_code in {"chapter_version_conflict", "blocking_conflict_unresolved"}:
        return 409
    if error_code in {"max_revision_rounds_exceeded"}:
        return 409
    return 400


def _reject_invalid_caller_type(request: Request, *, caller_type: str) -> JSONResponse | None:
    if caller_type and caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    return None


def _ensure_user_request(request: Request, *, caller_type: str, user_action: bool, idempotency_key: str) -> JSONResponse | None:
    denied = _reject_invalid_caller_type(request, caller_type=caller_type)
    if denied is not None:
        return denied
    if not user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


def _ensure_gate_request(request: Request, *, caller_type: str, user_action: bool, idempotency_key: str) -> JSONResponse | None:
    return _ensure_user_request(
        request,
        caller_type=caller_type,
        user_action=user_action,
        idempotency_key=idempotency_key,
    )


@router.post("/api/v2/ai/continuations")
def start_continuation(payload: StartContinuationRequest, request: Request):
    denied = _ensure_user_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    workflow = dependencies.get_continuation_workflow()
    try:
        result = workflow.start_continuation(
            payload.work_id,
            payload.chapter_id,
            user_instruction=payload.user_instruction,
            created_by=payload.caller_type or "user_action",
        )
        return success_response(
            request,
            data={
                "workflow_id": result.workflow_id,
                "job_id": result.job_id,
                "writing_task_id": result.writing_task_id,
                "candidate_draft_id": result.candidate_draft_id,
                "status": result.status,
                "warnings": result.warnings,
                "error_code": result.error_code,
                "caller_type": payload.caller_type,
                "idempotency_key": payload.idempotency_key,
            },
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code in {"work_not_found", "chapter_not_found"} else 400
        return error_response(request, error_code=error_code, status_code=status_code)


@router.get("/api/v2/ai/candidate-drafts")
def list_candidate_drafts(work_id: str, request: Request, chapter_id: str = ""):
    workflow = dependencies.get_continuation_workflow()
    try:
        drafts = workflow.list_candidate_drafts(work_id, chapter_id=chapter_id or None)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=400)
    return success_response(request, data={"items": [_serialize_candidate_summary(item) for item in drafts]})


@router.get("/api/v2/ai/candidate-drafts/{candidate_draft_id}")
def get_candidate_draft(candidate_draft_id: str, request: Request):
    workflow = dependencies.get_continuation_workflow()
    try:
        draft = workflow.get_candidate_draft(candidate_draft_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_candidate_detail(draft))


@router.get("/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions")
def list_candidate_draft_versions(candidate_draft_id: str, request: Request):
    service = dependencies.get_candidate_review_service()
    try:
        versions = service.list_candidate_versions(candidate_draft_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"items": [_serialize_candidate_version(item) for item in versions]})


@router.get("/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions/diff")
def get_candidate_draft_version_diff(candidate_draft_id: str, request: Request, from_version_id: str, to_version_id: str):
    service = dependencies.get_candidate_rewrite_service()
    try:
        payload = service.diff_versions(
            candidate_draft_id=candidate_draft_id,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_candidate_error_status(error_code))
    return success_response(request, data=payload)


@router.get("/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions/{candidate_version_id}")
def get_candidate_draft_version(candidate_draft_id: str, candidate_version_id: str, request: Request):
    service = dependencies.get_candidate_review_service()
    try:
        version = service.get_candidate_version(candidate_draft_id, candidate_version_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_candidate_version(version))


@router.post("/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions/{candidate_version_id}/select")
def select_candidate_draft_version(
    candidate_draft_id: str,
    candidate_version_id: str,
    payload: SelectCandidateDraftVersionRequest,
    request: Request,
):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_candidate_review_service()
    try:
        draft = service.select_candidate_version(
            candidate_draft_id,
            candidate_version_id=candidate_version_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_candidate_error_status(error_code))
    return success_response(request, data=_serialize_candidate_detail(draft))


@router.post("/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions/{candidate_version_id}/reject")
def reject_candidate_draft_version(
    candidate_draft_id: str,
    candidate_version_id: str,
    payload: RejectCandidateDraftRequest,
    request: Request,
):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_candidate_rewrite_service()
    try:
        draft = service.reject_candidate_version(
            candidate_draft_id=candidate_draft_id,
            candidate_version_id=candidate_version_id,
            user_id=payload.user_id,
            reason=payload.reason,
            user_action=payload.user_action,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_candidate_error_status(error_code))
    return success_response(request, data=_serialize_candidate_detail(draft))


@router.post("/api/v2/ai/candidate-drafts/{candidate_draft_id}/versions/{candidate_version_id}/accept")
def accept_candidate_draft_version(
    candidate_draft_id: str,
    candidate_version_id: str,
    payload: AcceptCandidateDraftRequest,
    request: Request,
):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_candidate_review_service()
    try:
        draft = service.accept_candidate(
            candidate_draft_id,
            candidate_version_id=candidate_version_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_candidate_error_status(error_code))
    return success_response(request, data=_serialize_candidate_detail(draft))


@router.post("/api/v2/ai/candidate-drafts/{candidate_draft_id}/accept")
def accept_candidate_draft(candidate_draft_id: str, payload: AcceptCandidateDraftRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_candidate_review_service()
    try:
        draft = service.accept_candidate(
            candidate_draft_id,
            candidate_version_id=payload.candidate_version_id,
            user_id=payload.user_id,
            user_action=payload.user_action,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_candidate_error_status(error_code))
    return success_response(request, data=_serialize_candidate_detail(draft))


@router.post("/api/v2/ai/candidate-drafts/{candidate_draft_id}/reject")
def reject_candidate_draft(candidate_draft_id: str, payload: RejectCandidateDraftRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_candidate_review_service()
    try:
        draft = service.reject_candidate(
            candidate_draft_id,
            candidate_version_id=payload.candidate_version_id,
            user_id=payload.user_id,
            reason=payload.reason,
            user_action=payload.user_action,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_candidate_error_status(error_code))
    return success_response(request, data=_serialize_candidate_detail(draft))


@router.post("/api/v2/ai/candidate-drafts/{candidate_draft_id}/apply")
def apply_candidate_draft(candidate_draft_id: str, payload: ApplyCandidateDraftRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_candidate_review_service()
    try:
        result = service.apply_candidate_to_draft(
            candidate_draft_id,
            candidate_version_id=payload.candidate_version_id,
            user_id=payload.user_id,
            expected_chapter_version=payload.expected_chapter_version,
            user_action=payload.user_action,
            apply_mode=payload.apply_mode,
            selection_range=payload.selection_range,
            cursor_position=payload.cursor_position,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_candidate_error_status(error_code))
    return success_response(request, data=result)


@router.post("/api/v2/ai/candidate-drafts/{candidate_draft_id}/rewrites")
def rewrite_candidate_draft(candidate_draft_id: str, payload: RewriteCandidateDraftRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_candidate_rewrite_service()
    try:
        result = service.request_rewrite(
            candidate_draft_id=candidate_draft_id,
            source_version_id=payload.source_version_id,
            trigger_type=payload.trigger_type,
            review_report_id=payload.review_report_id,
            user_instruction=payload.user_instruction,
            user_id=payload.user_id,
            user_action=payload.user_action,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=_candidate_error_status(error_code))
    rewrite_request = service.get_rewrite_request(str(result["rewrite_request_id"]))
    revision_round = service.get_revision_round(str(result["revision_round_id"]))
    return success_response(
        request,
        data={
            "draft": _serialize_candidate_detail(result["draft"]),
            "target_version": _serialize_candidate_version(result["target_version"]),
            "rewrite_request": rewrite_request.model_dump(mode="json"),
            "revision_round": revision_round.model_dump(mode="json"),
        },
    )
