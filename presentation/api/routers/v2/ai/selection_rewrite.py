from __future__ import annotations

from fastapi import APIRouter, Request

from domain.entities.ai.models import SelectionRewriteCandidate, SelectionRewriteMode
from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import V2AIOperationRequest, V2AIBaseModel

router = APIRouter(tags=["v2-ai-selection-rewrite"])


class CreateSelectionRewriteRequest(V2AIBaseModel):
    work_id: str
    chapter_id: str
    chapter_revision: int
    draft_revision: int
    draft_text_hash: str
    draft_length: int
    source_text: str
    source_hash: str
    start_pos: int
    end_pos: int
    context_before: str = ""
    context_after: str = ""
    mode: str
    caller_type: str = "user_action"


class ApplySelectionRewriteRequest(V2AIOperationRequest):
    final_text: str | None = None
    chapter_revision: int
    draft_revision: int
    draft_text_hash: str
    draft_length: int
    range_text: str
    user_action: bool = False


def _reject_invalid_caller_type(request: Request, *, caller_type: str) -> object | None:
    if caller_type and caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    return None


def _candidate_value(item: SelectionRewriteCandidate | dict[str, object], name: str, default: object = "") -> object:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _serialize_candidate(item: SelectionRewriteCandidate | dict[str, object]) -> dict[str, object]:
    return {
        "rewrite_id": _candidate_value(item, "rewrite_id", ""),
        "chapter_id": _candidate_value(item, "chapter_id", ""),
        "work_id": _candidate_value(item, "work_id", ""),
        "rewrite_mode": _candidate_value(item, "rewrite_mode", ""),
        "source_text": _candidate_value(item, "source_text", ""),
        "source_start_pos": _candidate_value(item, "source_start_pos", 0),
        "source_end_pos": _candidate_value(item, "source_end_pos", 0),
        "rewritten_text": _candidate_value(item, "rewritten_text", ""),
        "applied_text": _candidate_value(item, "applied_text", ""),
        "word_count_before": _candidate_value(item, "word_count_before", 0),
        "word_count_after": _candidate_value(item, "word_count_after", 0),
        "diff_summary": _candidate_value(item, "diff_summary", ""),
        "status": _candidate_value(item, "status", ""),
        "draft_revision": _candidate_value(item, "draft_revision", 0),
        "draft_text_hash": _candidate_value(item, "draft_text_hash", ""),
        "draft_length": _candidate_value(item, "draft_length", 0),
        "request_id": _candidate_value(item, "request_id", ""),
        "error_code": _candidate_value(item, "error_code", ""),
        "error_message": _candidate_value(item, "error_message", ""),
    }


def _error_response_for_code(request: Request, error_code: str):
    if error_code == "selection_rewrite_not_found":
        return error_response(request, error_code=error_code, status_code=404)
    if error_code in {"selection_conflict", "selection_text_mismatch"}:
        return error_response(request, error_code=error_code, status_code=409)
    if error_code == "caller_type_forbidden":
        return error_response(request, error_code=error_code, status_code=403)
    return error_response(request, error_code=error_code, status_code=400)


@router.post("/api/v2/ai/selection-rewrite")
async def create_selection_rewrite(payload: CreateSelectionRewriteRequest, request: Request):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
    service = dependencies.get_selection_rewrite_service()
    try:
        candidate = await service.rewrite(
            work_id=payload.work_id,
            chapter_id=payload.chapter_id,
            chapter_revision=payload.chapter_revision,
            draft_revision=payload.draft_revision,
            draft_text_hash=payload.draft_text_hash,
            draft_length=payload.draft_length,
            source_text=payload.source_text,
            source_hash=payload.source_hash,
            start_pos=payload.start_pos,
            end_pos=payload.end_pos,
            context_before=payload.context_before,
            context_after=payload.context_after,
            mode=SelectionRewriteMode(str(payload.mode or "")),
            caller_type=payload.caller_type,
        )
    except ValueError as exc:
        return _error_response_for_code(request, str(exc))
    return success_response(request, data=_serialize_candidate(candidate))


@router.get("/api/v2/ai/selection-rewrite/{rewrite_id}")
async def get_selection_rewrite(rewrite_id: str, request: Request):
    service = dependencies.get_selection_rewrite_service()
    try:
        candidate = await service.get_candidate(rewrite_id)
    except ValueError as exc:
        return _error_response_for_code(request, str(exc))
    return success_response(request, data=_serialize_candidate(candidate))


@router.get("/api/v2/ai/selection-rewrite/chapters/{chapter_id}/history")
async def list_selection_rewrite_history(chapter_id: str, request: Request):
    service = dependencies.get_selection_rewrite_service()
    items = await service.list_candidates_by_chapter(chapter_id)
    return success_response(request, data={"items": [_serialize_candidate(item) for item in items]})


@router.delete("/api/v2/ai/selection-rewrite/chapters/{chapter_id}/history")
async def clear_selection_rewrite_history(chapter_id: str, request: Request):
    service = dependencies.get_selection_rewrite_service()
    result = await service.clear_chapter_history(chapter_id)
    return success_response(request, data=result)


@router.post("/api/v2/ai/selection-rewrite/{rewrite_id}/apply")
async def apply_selection_rewrite(rewrite_id: str, payload: ApplySelectionRewriteRequest, request: Request):
    denied = _reject_invalid_caller_type(request, caller_type=payload.caller_type)
    if denied is not None:
        return denied
    service = dependencies.get_selection_rewrite_service()
    try:
        result = await service.apply(
            rewrite_id,
            final_text=payload.final_text,
            chapter_revision=payload.chapter_revision,
            draft_revision=payload.draft_revision,
            draft_text_hash=payload.draft_text_hash,
            draft_length=payload.draft_length,
            range_text=payload.range_text,
            caller_type=payload.caller_type,
        )
    except ValueError as exc:
        return _error_response_for_code(request, str(exc))
    return success_response(request, data=result)


@router.post("/api/v2/ai/selection-rewrite/{rewrite_id}/reject")
async def reject_selection_rewrite(rewrite_id: str, request: Request):
    service = dependencies.get_selection_rewrite_service()
    try:
        candidate = await service.reject(rewrite_id)
    except ValueError as exc:
        return _error_response_for_code(request, str(exc))
    return success_response(
        request,
        data={
            "rewrite_id": _candidate_value(candidate, "rewrite_id", ""),
            "status": _candidate_value(candidate, "status", ""),
        },
    )
