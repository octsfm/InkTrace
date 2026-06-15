from __future__ import annotations

from fastapi import APIRouter, Request

from domain.entities.ai.models import ChapterAdvanceDecision
from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import AdvanceMultiChapterRequest, SessionActionRequest, StartMultiChapterRequest

router = APIRouter(tags=["v2-ai-multi-chapter"])


def _ensure_gate_request(request: Request, *, caller_type: str, user_action: bool, idempotency_key: str):
    if caller_type != "user_action":
        return error_response(request, error_code="P2_CALLER_FORBIDDEN", status_code=403)
    if not user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


def _serialize_progress(progress) -> dict[str, object]:
    return {
        "session_id": progress.session_id,
        "status": progress.status.value,
        "current_index": progress.current_index,
        "target_chapters": progress.target_chapters,
        "completed_count": progress.completed_count,
        "blocked_count": progress.blocked_count,
        "per_chapter": [
            {
                "chapter_index": item.chapter_index,
                "status": item.status.value,
                "candidate_draft_id": item.candidate_draft_id,
                "candidate_draft_status": item.candidate_draft_status,
                "word_count": item.word_count,
                "review_summary": item.review_summary,
            }
            for item in progress.per_chapter
        ],
    }


@router.post("/api/v2/ai/multi-chapter/start", status_code=202)
async def start_multi_chapter(payload: StartMultiChapterRequest, request: Request):
    if payload.caller_type != "user_action":
        return error_response(request, error_code="P2_CALLER_FORBIDDEN", status_code=403)
    service = dependencies.get_multi_chapter_service()
    try:
        session = service.start(
            work_id=payload.work_id,
            start_chapter_id=payload.start_chapter_id,
            target_chapters=payload.target_chapters,
            user_instruction=payload.user_instruction,
            caller_type=payload.caller_type,
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 403 if error_code == "P2_CALLER_FORBIDDEN" else 404 if error_code in {"work_not_found", "chapter_not_found"} else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(
        request,
        data={
            "session_id": session.session_id,
            "status": session.status.value,
            "target_chapters": session.target_chapters,
            "created_at": session.created_at,
        },
    )


@router.get("/api/v2/ai/multi-chapter/{session_id}/progress")
async def get_multi_chapter_progress(session_id: str, request: Request):
    service = dependencies.get_multi_chapter_service()
    try:
        progress = service.get_progress(session_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_progress(progress))


@router.post("/api/v2/ai/multi-chapter/{session_id}/advance")
async def advance_multi_chapter(session_id: str, payload: AdvanceMultiChapterRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_multi_chapter_service()
    try:
        session = service.advance_to_next_chapter(
            session_id,
            decision=ChapterAdvanceDecision(payload.decision),
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 403 if error_code == "P2_CALLER_FORBIDDEN" else 404 if error_code == "multi_chapter_session_not_found" else 409 if error_code == "not_waiting_user_decision" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(
        request,
        data={
            "session_id": session.session_id,
            "status": session.status.value,
            "current_index": session.current_index,
            "next_chapter_available": session.current_index < session.target_chapters,
        },
    )


@router.post("/api/v2/ai/multi-chapter/{session_id}/pause")
async def pause_multi_chapter(session_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_multi_chapter_service()
    try:
        session = service.pause(session_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"session_id": session.session_id, "status": session.status.value, "paused_at": session.updated_at})


@router.post("/api/v2/ai/multi-chapter/{session_id}/resume")
async def resume_multi_chapter(session_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_multi_chapter_service()
    try:
        session = service.resume(session_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"session_id": session.session_id, "status": session.status.value, "current_index": session.current_index})


@router.post("/api/v2/ai/multi-chapter/{session_id}/cancel")
async def cancel_multi_chapter(session_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_multi_chapter_service()
    try:
        session = service.cancel(session_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"session_id": session.session_id, "status": session.status.value, "cancelled_at": session.updated_at})


@router.get("/api/v2/ai/multi-chapter/{session_id}/chapters")
async def list_multi_chapter_items(session_id: str, request: Request):
    service = dependencies.get_multi_chapter_service()
    try:
        items = service.list_chapters(session_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(
        request,
        data={
            "chapters": [
                {
                    "chapter_index": item.chapter_index,
                    "status": item.status.value,
                    "candidate_draft_id": item.candidate_draft_id,
                    "candidate_draft_status": item.candidate_draft_status,
                    "word_count": item.word_count,
                    "review_summary": item.review_summary,
                }
                for item in items
            ]
        },
    )

