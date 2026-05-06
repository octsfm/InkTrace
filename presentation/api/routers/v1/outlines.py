from fastapi import APIRouter

from application.services.v1 import build_writing_asset_service
from presentation.api.routers.v1.schemas import (
    ChapterOutlineResponse,
    OutlineSaveRequest,
    V1APIError,
    WorkOutlineResponse,
    build_conflict_response,
    serialize_chapter_outline,
    serialize_work_outline,
)

router = APIRouter(prefix="/api/v1", tags=["v1-outlines"])


@router.get("/works/{work_id}/outline", response_model=WorkOutlineResponse)
def get_work_outline(work_id: str):
    service = build_writing_asset_service()
    try:
        outline = service.get_work_outline(work_id)
    except ValueError as exc:
        if str(exc) == "work_not_found":
            raise V1APIError("work_not_found") from exc
        raise
    return serialize_work_outline(outline)


@router.put("/works/{work_id}/outline", response_model=WorkOutlineResponse)
def save_work_outline(work_id: str, request: OutlineSaveRequest):
    service = build_writing_asset_service()
    try:
        outline = service.save_work_outline(
            work_id,
            content_text=request.content_text,
            content_tree_json=request.content_tree_json,
            expected_version=request.expected_version,
            force_override=request.force_override,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "work_not_found":
            raise V1APIError("work_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        if code == "asset_version_conflict":
            current = service.work_outline_repo.find_by_work(work_id)
            raise V1APIError(
                "asset_version_conflict",
                payload=build_conflict_response(
                    "asset_version_conflict",
                    server_version=int(current.version if current else 1),
                    resource_type="work_outline",
                    resource_id=work_id,
                ),
            ) from exc
        raise
    return serialize_work_outline(outline)


@router.get("/chapters/{chapter_id}/outline", response_model=ChapterOutlineResponse)
def get_chapter_outline(chapter_id: str):
    service = build_writing_asset_service()
    try:
        outline = service.get_chapter_outline(chapter_id)
    except ValueError as exc:
        if str(exc) == "chapter_not_found":
            raise V1APIError("chapter_not_found") from exc
        raise
    return serialize_chapter_outline(outline)


@router.put("/chapters/{chapter_id}/outline", response_model=ChapterOutlineResponse)
def save_chapter_outline(chapter_id: str, request: OutlineSaveRequest):
    service = build_writing_asset_service()
    try:
        outline = service.save_chapter_outline(
            chapter_id,
            content_text=request.content_text,
            content_tree_json=request.content_tree_json,
            expected_version=request.expected_version,
            force_override=request.force_override,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "chapter_not_found":
            raise V1APIError("chapter_not_found") from exc
        if code == "invalid_input":
            raise V1APIError("invalid_input") from exc
        if code == "asset_version_conflict":
            current = service.chapter_outline_repo.find_by_chapter(chapter_id)
            raise V1APIError(
                "asset_version_conflict",
                payload=build_conflict_response(
                    "asset_version_conflict",
                    server_version=int(current.version if current else 1),
                    resource_type="chapter_outline",
                    resource_id=chapter_id,
                ),
            ) from exc
        raise
    return serialize_chapter_outline(outline)
