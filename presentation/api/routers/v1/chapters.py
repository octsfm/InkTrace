from fastapi import APIRouter

from application.services.v1 import ChapterService
from presentation.api.routers.v1.schemas import (
    ChapterCreateRequest,
    ChapterDeleteResponse,
    ChapterListResponse,
    ChapterReorderRequest,
    ChapterResponse,
    ChapterUpdateRequest,
    V1APIError,
    build_conflict_response,
    serialize_chapter,
)

router = APIRouter(prefix="/api/v1", tags=["v1-chapters"])

@router.get("/works/{work_id}/chapters", response_model=ChapterListResponse)
def list_chapters(work_id: str):
    service = ChapterService()
    items = service.list_chapters(work_id)
    return {"work_id": work_id, "items": [serialize_chapter(item) for item in items], "total": len(items)}


@router.post("/works/{work_id}/chapters", response_model=ChapterResponse)
def create_chapter(work_id: str, request: ChapterCreateRequest):
    service = ChapterService()
    try:
        chapter = service.create_chapter(work_id, request.title, request.after_chapter_id)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        raise
    return serialize_chapter(chapter)


@router.put("/chapters/{chapter_id}", response_model=ChapterResponse)
def update_chapter(chapter_id: str, request: ChapterUpdateRequest):
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
            raise V1APIError("chapter_not_found") from exc
        if str(exc) == "version_conflict":
            current = service.chapter_repo.find_by_id(chapter_id)
            raise V1APIError(
                "version_conflict",
                payload=build_conflict_response(
                    "version_conflict",
                    server_version=current.version,
                    resource_type="chapter",
                    resource_id=chapter_id,
                ),
            ) from exc
        raise
    return serialize_chapter(chapter)


@router.delete("/chapters/{chapter_id}", response_model=ChapterDeleteResponse)
def delete_chapter(chapter_id: str):
    service = ChapterService()
    try:
        next_chapter_id = service.delete_chapter(chapter_id)
    except ValueError as exc:
        if str(exc) == "chapter_not_found":
            raise V1APIError("chapter_not_found") from exc
        raise
    return {"ok": True, "id": chapter_id, "next_chapter_id": next_chapter_id}


@router.put("/works/{work_id}/chapters/reorder", response_model=ChapterListResponse)
def reorder_chapters(work_id: str, request: ChapterReorderRequest):
    service = ChapterService()
    try:
        items = service.reorder_chapters(
            work_id,
            [{"id": item.id, "order_index": item.order_index} for item in request.items],
        )
    except ValueError as exc:
        if str(exc) == "invalid_input":
            raise V1APIError("invalid_input") from exc
        raise
    return {"work_id": work_id, "items": [serialize_chapter(item) for item in items], "total": len(items)}
