from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from application.services.v1 import ChapterService

router = APIRouter(prefix="/api/v1", tags=["v1-chapters"])


class CreateChapterRequest(BaseModel):
    title: str = ""
    after_chapter_id: str = ""


class UpdateChapterRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    expected_version: int | None = None
    force_override: bool = False


class ReorderChaptersRequest(BaseModel):
    chapter_ids: list[str]


def _serialize_chapter(chapter):
    return {
        "id": chapter.id.value,
        "work_id": chapter.novel_id.value,
        "title": chapter.title,
        "content": chapter.content,
        "chapter_number": chapter.number,
        "order_index": chapter.order_index,
        "version": chapter.version,
        "created_at": chapter.created_at.isoformat(),
        "updated_at": chapter.updated_at.isoformat(),
    }


@router.get("/works/{work_id}/chapters")
def list_chapters(work_id: str):
    service = ChapterService()
    items = service.list_chapters(work_id)
    return {"work_id": work_id, "items": [_serialize_chapter(item) for item in items], "total": len(items)}


@router.post("/works/{work_id}/chapters")
def create_chapter(work_id: str, request: CreateChapterRequest):
    service = ChapterService()
    try:
        chapter = service.create_chapter(work_id, request.title, request.after_chapter_id)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise HTTPException(status_code=404, detail="work_not_found") from exc
        raise
    return _serialize_chapter(chapter)


@router.put("/chapters/{chapter_id}")
def update_chapter(chapter_id: str, request: UpdateChapterRequest):
    service = ChapterService()
    try:
        chapter = service.update_chapter(
            chapter_id,
            title=request.title,
            content=request.content,
            expected_version=request.expected_version,
            force_override=request.force_override,
        )
    except ValueError as exc:
        if str(exc) == "chapter_not_found":
            raise HTTPException(status_code=404, detail="chapter_not_found") from exc
        if str(exc) == "chapter_version_conflict":
            raise HTTPException(status_code=409, detail="chapter_version_conflict") from exc
        raise
    return _serialize_chapter(chapter)


@router.delete("/chapters/{chapter_id}")
def delete_chapter(chapter_id: str):
    service = ChapterService()
    try:
        next_chapter_id = service.delete_chapter(chapter_id)
    except ValueError as exc:
        if str(exc) == "chapter_not_found":
            raise HTTPException(status_code=404, detail="chapter_not_found") from exc
        raise
    return {"ok": True, "id": chapter_id, "next_chapter_id": next_chapter_id}


@router.put("/works/{work_id}/chapters/reorder")
def reorder_chapters(work_id: str, request: ReorderChaptersRequest):
    service = ChapterService()
    items = service.reorder_chapters(work_id, request.chapter_ids)
    return {"work_id": work_id, "items": [_serialize_chapter(item) for item in items], "total": len(items)}
