"""Novel management API routes."""

from __future__ import annotations

from datetime import datetime
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from application.dto.request_dto import CreateNovelRequest
from application.dto.response_dto import NovelResponse
from application.services.project_service import ProjectService
from domain.entities.chapter import Chapter
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.novel_repository import INovelRepository
from domain.types import ChapterId, ChapterStatus, GenreType, NovelId
from presentation.api.dependencies import (
    get_chapter_repo,
    get_novel_repo,
    get_project_service,
)


router = APIRouter(prefix="/api/novels", tags=["novels"])


class ChapterUpdatePayload(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class ChapterCreatePayload(BaseModel):
    title: Optional[str] = ""
    content: Optional[str] = ""


@router.post("/", response_model=NovelResponse)
async def create_novel(
    request: CreateNovelRequest,
    service: ProjectService = Depends(get_project_service),
) -> NovelResponse:
    try:
        genre = GenreType(request.genre)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"无效的题材类型: {request.genre}") from exc

    project = service.create_project(
        name=request.title,
        genre=genre,
        target_words=request.target_word_count,
        author=request.author,
    )

    return NovelResponse(
        id=str(project.novel_id),
        title=project.name,
        author=request.author,
        genre=project.config.genre.value,
        word_count=0,
        target_word_count=project.config.target_words,
        current_word_count=0,
        chapter_count=0,
        chapters=[],
        memory=None,
        status=project.status.value,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.get("/", response_model=List[NovelResponse])
async def list_novels(
    service: ProjectService = Depends(get_project_service),
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    novel_repo: INovelRepository = Depends(get_novel_repo),
) -> List[NovelResponse]:
    projects = service.list_projects()
    return [_project_to_novel_response(project, chapter_repo, novel_repo) for project in projects]


@router.get("/{novel_id}", response_model=NovelResponse)
async def get_novel(
    novel_id: str,
    include_chapters: bool = Query(True),
    service: ProjectService = Depends(get_project_service),
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    novel_repo: INovelRepository = Depends(get_novel_repo),
) -> NovelResponse:
    project = service.get_project_by_novel(NovelId(novel_id))
    if not project:
        raise HTTPException(status_code=404, detail="小说不存在")
    return _project_to_novel_response(project, chapter_repo, novel_repo, include_chapters=include_chapters)


@router.get("/{novel_id}/chapters")
async def list_chapters(
    novel_id: str,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    novel_repo: INovelRepository = Depends(get_novel_repo),
) -> dict:
    novel = novel_repo.find_by_id(NovelId(novel_id))
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    chapters = chapter_repo.find_by_novel(NovelId(novel_id))
    return {
        "novel_id": novel_id,
        "chapters": [
            {
                "id": str(chapter.id),
                "number": chapter.number,
                "title": chapter.title,
                "word_count": chapter.word_count,
                "status": chapter.status.value,
                "updated_at": chapter.updated_at.isoformat(),
            }
            for chapter in chapters
        ],
    }


@router.get("/{novel_id}/chapters/{chapter_id}")
async def get_chapter_detail(
    novel_id: str,
    chapter_id: str,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
) -> dict:
    chapter = chapter_repo.find_by_id(ChapterId(chapter_id))
    if not chapter or chapter.novel_id.value != novel_id:
        raise HTTPException(status_code=404, detail="章节不存在")
    return {
        "id": chapter.id.value,
        "novel_id": chapter.novel_id.value,
        "number": chapter.number,
        "title": chapter.title,
        "content": chapter.content,
        "status": chapter.status.value,
        "word_count": chapter.word_count,
        "updated_at": chapter.updated_at.isoformat(),
    }


@router.post("/{novel_id}/chapters")
async def create_chapter(
    novel_id: str,
    payload: ChapterCreatePayload,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    novel_repo: INovelRepository = Depends(get_novel_repo),
) -> dict:
    novel = novel_repo.find_by_id(NovelId(novel_id))
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    chapters = chapter_repo.find_by_novel(NovelId(novel_id))
    next_number = (max(item.number for item in chapters) if chapters else 0) + 1
    now = datetime.now()
    default_title = f"第{next_number}章"
    chapter = Chapter(
        id=ChapterId(str(uuid.uuid4())),
        novel_id=NovelId(novel_id),
        number=next_number,
        title=(payload.title or default_title).strip() or default_title,
        content=payload.content or "",
        status=ChapterStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    chapter_repo.save(chapter)
    _sync_novel_statistics(novel, chapter_repo.find_by_novel(novel.id), now)
    novel_repo.save(novel)
    return {
        "id": chapter.id.value,
        "novel_id": novel_id,
        "number": chapter.number,
        "title": chapter.title,
        "content": chapter.content,
        "status": chapter.status.value,
        "word_count": chapter.word_count,
        "updated_at": chapter.updated_at.isoformat(),
    }


@router.put("/{novel_id}/chapters/{chapter_id}")
async def update_chapter(
    novel_id: str,
    chapter_id: str,
    payload: ChapterUpdatePayload,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    novel_repo: INovelRepository = Depends(get_novel_repo),
) -> dict:
    chapter = chapter_repo.find_by_id(ChapterId(chapter_id))
    if not chapter or chapter.novel_id.value != novel_id:
        raise HTTPException(status_code=404, detail="章节不存在")
    if payload.title is None and payload.content is None:
        raise HTTPException(status_code=400, detail="缺少可更新字段")

    now = datetime.now()
    if payload.title is not None:
        chapter.update_title(payload.title, now)
    if payload.content is not None:
        chapter.update_content(payload.content, now)
    chapter_repo.save(chapter)

    novel = novel_repo.find_by_id(NovelId(novel_id))
    if novel:
        _sync_novel_statistics(novel, chapter_repo.find_by_novel(novel.id), now)
        novel_repo.save(novel)

    return {
        "id": chapter.id.value,
        "number": chapter.number,
        "title": chapter.title,
        "content": chapter.content,
        "word_count": chapter.word_count,
        "updated_at": chapter.updated_at.isoformat(),
    }


@router.delete("/{novel_id}/chapters/{chapter_id}")
async def delete_chapter(
    novel_id: str,
    chapter_id: str,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    novel_repo: INovelRepository = Depends(get_novel_repo),
) -> dict:
    chapter = chapter_repo.find_by_id(ChapterId(chapter_id))
    if not chapter or chapter.novel_id.value != novel_id:
        raise HTTPException(status_code=404, detail="章节不存在")

    chapter_repo.delete(chapter.id)
    remaining = chapter_repo.find_by_novel(NovelId(novel_id))
    novel = novel_repo.find_by_id(NovelId(novel_id))
    if novel:
        _sync_novel_statistics(novel, remaining, datetime.now())
        novel_repo.save(novel)
    return {
        "deleted_chapter_id": chapter_id,
        "chapter_count": len(remaining),
        "word_count": sum(item.word_count for item in remaining),
    }


@router.delete("/{novel_id}")
async def delete_novel(
    novel_id: str,
    service: ProjectService = Depends(get_project_service),
) -> dict:
    project = service.get_project_by_novel(NovelId(novel_id))
    if not project:
        raise HTTPException(status_code=404, detail="小说不存在")

    service.delete_project(project.id)
    return {"message": "删除成功"}


def _project_to_novel_response(
    project,
    chapter_repo: IChapterRepository,
    novel_repo: INovelRepository,
    include_chapters: bool = True,
) -> NovelResponse:
    chapters = chapter_repo.find_by_novel(project.novel_id)
    novel = novel_repo.find_by_id(project.novel_id)
    current_word_count = sum(chapter.word_count for chapter in chapters)
    return NovelResponse(
        id=str(project.novel_id),
        title=project.name,
        author=novel.author if novel else "",
        genre=project.config.genre.value,
        word_count=current_word_count,
        target_word_count=project.config.target_words,
        current_word_count=current_word_count,
        chapter_count=len(chapters),
        chapters=[
            {
                "id": str(chapter.id),
                "number": chapter.number,
                "title": chapter.title,
                "word_count": chapter.word_count,
                "status": chapter.status.value,
                "updated_at": chapter.updated_at.isoformat(),
            }
            for chapter in chapters
        ] if include_chapters else [],
        memory=None,
        status=project.status.value,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


def _sync_novel_statistics(novel, chapters, updated_at: datetime) -> None:
    novel.current_word_count = sum(chapter.word_count for chapter in chapters)
    novel.updated_at = updated_at
