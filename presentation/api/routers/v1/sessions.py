from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from application.services.v1 import SessionService

router = APIRouter(prefix="/api/v1/works", tags=["v1-sessions"])


class SaveSessionRequest(BaseModel):
    chapter_id: str = ""
    cursor_position: int = 0
    scroll_top: int = 0


@router.get("/{work_id}/session")
def get_session(work_id: str):
    service = SessionService()
    try:
        session = service.get_session(work_id)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise HTTPException(status_code=404, detail="work_not_found") from exc
        raise
    return {
        "work_id": session.work_id,
        "last_open_chapter_id": session.last_open_chapter_id,
        "cursor_position": session.cursor_position,
        "scroll_top": session.scroll_top,
        "updated_at": session.updated_at.isoformat(),
    }


@router.put("/{work_id}/session")
def save_session(work_id: str, request: SaveSessionRequest):
    service = SessionService()
    try:
        session = service.save_session(
            work_id,
            chapter_id=request.chapter_id,
            cursor_position=request.cursor_position,
            scroll_top=request.scroll_top,
        )
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise HTTPException(status_code=404, detail="work_not_found") from exc
        raise
    return {
        "work_id": session.work_id,
        "last_open_chapter_id": session.last_open_chapter_id,
        "cursor_position": session.cursor_position,
        "scroll_top": session.scroll_top,
        "updated_at": session.updated_at.isoformat(),
    }
