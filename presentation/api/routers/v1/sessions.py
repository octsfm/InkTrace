from fastapi import APIRouter

from application.services.v1 import SessionService
from presentation.api.routers.v1.schemas import SessionResponse, SessionSaveRequest, V1APIError, serialize_session

router = APIRouter(prefix="/api/v1/works", tags=["v1-sessions"])

@router.get("/{work_id}/session", response_model=SessionResponse)
def get_session(work_id: str):
    service = SessionService()
    try:
        session = service.get_session(work_id)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if str(exc) == "chapter_not_found":
            raise V1APIError("chapter_not_found") from exc
        raise
    return serialize_session(session)


@router.put("/{work_id}/session", response_model=SessionResponse)
def save_session(work_id: str, request: SessionSaveRequest):
    service = SessionService()
    try:
        session = service.save_session(
            work_id,
            chapter_id=request.last_open_chapter_id,
            cursor_position=request.cursor_position,
            scroll_top=request.scroll_top,
        )
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if str(exc) == "chapter_not_found":
            raise V1APIError("chapter_not_found") from exc
        raise
    return serialize_session(session)
