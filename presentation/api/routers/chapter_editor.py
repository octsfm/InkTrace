from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from application.dto.request_dto import ChapterAIActionRequest, ChapterOutlineRequest, UpdateChapterRequest
from application.dto.response_dto import ChapterAIActionResponse
from application.services.chapter_ai_service import ChapterAIService
from application.services.logging_service import build_log_context, get_logger
from application.services.project_service import ProjectService
from application.services.v2_workflow_service import V2WorkflowService
from domain.entities.chapter_outline import ChapterOutline
from domain.repositories.chapter_outline_repository import IChapterOutlineRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.types import ChapterId
from presentation.api.dependencies import (
    get_chapter_ai_service,
    get_chapter_outline_repo,
    get_chapter_repo,
    get_project_service,
    get_v2_workflow_service,
)


router = APIRouter(prefix="/api/chapters", tags=["章节编辑"])
logger = get_logger(__name__)


class ChapterImportPayload(BaseModel):
    action: str = "import"
    content: str = ""
    style: str = ""
    target_word_count: int = 2200
    outline: dict = Field(default_factory=dict)
    raw_text: str
    title: str = ""
    global_memory_summary: str = ""
    global_outline_summary: str = ""
    recent_chapter_summaries: list[str] = Field(default_factory=list)


def _load_chapter(chapter_id: str, chapter_repo: IChapterRepository):
    chapter = chapter_repo.find_by_id(ChapterId(chapter_id))
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@router.get("/{chapter_id}")
async def get_chapter(chapter_id: str, chapter_repo: IChapterRepository = Depends(get_chapter_repo)):
    chapter = _load_chapter(chapter_id, chapter_repo)
    logger.info(
        "章节已读取",
        extra=build_log_context(
            event="chapter_loaded",
            chapter_id=chapter.id.value,
            chapter_number=chapter.number,
            novel_id=chapter.novel_id.value,
        ),
    )
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


@router.put("/{chapter_id}")
async def update_chapter(
    chapter_id: str,
    request: UpdateChapterRequest,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    chapter = _load_chapter(chapter_id, chapter_repo)
    if request.title is not None:
        chapter.update_title(request.title, datetime.now())
    if request.content is not None:
        chapter.update_content(request.content, datetime.now())
    chapter_repo.save(chapter)
    refreshed = False
    refresh_error = ""
    try:
        project = project_service.get_project_by_novel(chapter.novel_id)
        if project:
            await v2_service.refresh_memory(project.id.value, chapter.number, chapter.number)
            refreshed = True
    except Exception as e:
        refreshed = False
        refresh_error = str(e)
    result = {
        "id": chapter.id.value,
        "updated_at": chapter.updated_at.isoformat(),
        "memory_refreshed": refreshed,
        "memory_refresh_error": refresh_error,
    }
    logger.info(
        "章节已保存",
        extra=build_log_context(
            event="chapter_saved",
            chapter_id=chapter.id.value,
            chapter_number=chapter.number,
            novel_id=chapter.novel_id.value,
            memory_refreshed=refreshed,
        ),
    )
    return result


@router.get("/{chapter_id}/outline")
async def get_chapter_outline(
    chapter_id: str,
    repo: IChapterOutlineRepository = Depends(get_chapter_outline_repo),
):
    outline = repo.find_by_chapter_id(ChapterId(chapter_id))
    if not outline:
        return {
            "chapter_id": chapter_id,
            "goal": "",
            "conflict": "",
            "events": [],
            "character_progress": "",
            "ending_hook": "",
            "notes": "",
        }
    return {
        "chapter_id": chapter_id,
        "goal": outline.goal,
        "conflict": outline.conflict,
        "events": outline.events,
        "character_progress": outline.character_progress,
        "ending_hook": outline.ending_hook,
        "notes": outline.notes,
        "updated_at": outline.updated_at.isoformat(),
        "memory_refresh_required": False,
    }
    logger.info(
        "章节大纲已保存",
        extra=build_log_context(
            event="chapter_outline_saved",
            chapter_id=chapter_id,
        ),
    )
    return payload


@router.get("/{chapter_id}/context")
async def get_chapter_context(
    chapter_id: str,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    chapter = _load_chapter(chapter_id, chapter_repo)
    project = project_service.get_project_by_novel(chapter.novel_id)
    if not project:
        raise HTTPException(status_code=404, detail="章节所属项目不存在")
    payload = v2_service.get_chapter_editor_context(project.id.value, chapter.number)
    logger.info(
        "章节上下文已加载",
        extra=build_log_context(
            event="chapter_context_loaded",
            chapter_id=chapter.id.value,
            chapter_number=chapter.number,
            novel_id=chapter.novel_id.value,
        ),
    )
    return payload


@router.put("/{chapter_id}/outline")
async def save_chapter_outline(
    chapter_id: str,
    request: ChapterOutlineRequest,
    repo: IChapterOutlineRepository = Depends(get_chapter_outline_repo),
):
    now = datetime.now()
    existed = repo.find_by_chapter_id(ChapterId(chapter_id))
    outline = ChapterOutline(
        chapter_id=ChapterId(chapter_id),
        goal=request.goal,
        conflict=request.conflict,
        events=[str(x) for x in (request.events or [])],
        character_progress=request.character_progress,
        ending_hook=request.ending_hook,
        notes=request.notes,
        created_at=existed.created_at if existed else now,
        updated_at=now,
    )
    repo.save(outline)
    payload = {
        "chapter_id": chapter_id,
        "goal": outline.goal,
        "conflict": outline.conflict,
        "events": outline.events,
        "character_progress": outline.character_progress,
        "ending_hook": outline.ending_hook,
        "notes": outline.notes,
        "updated_at": outline.updated_at.isoformat(),
    }
    logger.info(
        "章节大纲已保存",
        extra=build_log_context(
            event="chapter_outline_saved",
            chapter_id=chapter_id,
        ),
    )
    return payload


def _outline_dict(chapter_id: str, repo: IChapterOutlineRepository) -> dict:
    outline = repo.find_by_chapter_id(ChapterId(chapter_id))
    if not outline:
        return {"goal": "", "conflict": "", "events": [], "character_progress": "", "ending_hook": "", "notes": ""}
    return {
        "goal": outline.goal,
        "conflict": outline.conflict,
        "events": outline.events,
        "character_progress": outline.character_progress,
        "ending_hook": outline.ending_hook,
        "notes": outline.notes,
    }


@router.post("/{chapter_id}/import")
async def import_chapter_content(
    chapter_id: str,
    request: ChapterImportPayload,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    outline_repo: IChapterOutlineRepository = Depends(get_chapter_outline_repo),
    service: ChapterAIService = Depends(get_chapter_ai_service),
):
    chapter = _load_chapter(chapter_id, chapter_repo)
    logger.info(
        "导入章节开始",
        extra=build_log_context(
            event="chapter_import_started",
            chapter_id=chapter.id.value,
            chapter_number=chapter.number,
            novel_id=chapter.novel_id.value,
        ),
    )
    try:
        raw_text = request.raw_text or request.content
        parsed = service.parse_imported_chapter(raw_text, request.title or chapter.title or f"第{chapter.number}章")
        outline_result = await service.analyze_to_outline(
            parsed.get("title") or chapter.title or "",
            parsed.get("content") or "",
            request.global_memory_summary or "；".join(request.recent_chapter_summaries or []),
            request.global_outline_summary,
            request.recent_chapter_summaries,
        )
    except Exception as exc:
        logger.error(
            "导入章节失败",
            extra=build_log_context(
                event="chapter_import_failed",
                chapter_id=chapter.id.value,
                chapter_number=chapter.number,
                novel_id=chapter.novel_id.value,
                error=str(exc),
            ),
        )
        raise
    outline_draft = outline_result.get("outline_draft") or {}
    used_fallback = bool(outline_result.get("used_fallback"))
    now = datetime.now()
    existed = outline_repo.find_by_chapter_id(chapter.id)
    outline = ChapterOutline(
        chapter_id=chapter.id,
        goal=outline_draft.get("goal") or "",
        conflict=outline_draft.get("conflict") or "",
        events=[str(x) for x in (outline_draft.get("events") or [])],
        character_progress=outline_draft.get("character_progress") or "",
        ending_hook=outline_draft.get("ending_hook") or "",
        notes=outline_draft.get("notes") or "",
        created_at=existed.created_at if existed else now,
        updated_at=now,
    )
    outline_repo.save(outline)
    payload = {
        "chapter_id": chapter_id,
        "action": "import",
        "title": parsed.get("title") or "",
        "content": parsed.get("content") or "",
        "memory_refresh_required": False,
        "used_fallback": used_fallback,
        "outline_draft": {
            "goal": outline.goal,
            "conflict": outline.conflict,
            "events": outline.events,
            "character_progress": outline.character_progress,
            "ending_hook": outline.ending_hook,
            "notes": outline.notes,
        },
    }
    logger.info(
        "导入章节完成",
        extra=build_log_context(
            event="chapter_import_finished",
            chapter_id=chapter.id.value,
            chapter_number=chapter.number,
            novel_id=chapter.novel_id.value,
            used_fallback=used_fallback,
        ),
    )
    return payload


@router.post("/{chapter_id}/ai/optimize", response_model=ChapterAIActionResponse)
async def ai_optimize(
    chapter_id: str,
    request: ChapterAIActionRequest,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    outline_repo: IChapterOutlineRepository = Depends(get_chapter_outline_repo),
    service: ChapterAIService = Depends(get_chapter_ai_service),
):
    chapter = _load_chapter(chapter_id, chapter_repo)
    logger.info(
        "章节AI开始",
        extra=build_log_context(event="chapter_ai_started", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="optimize"),
    )
    outline = request.outline if isinstance(request.outline, dict) else _outline_dict(chapter_id, outline_repo)
    try:
        result = await service.optimize(
            chapter,
            outline,
            global_memory_summary=request.global_memory_summary,
            global_outline_summary=request.global_outline_summary,
            recent_chapter_summaries=request.recent_chapter_summaries,
        )
    except Exception as exc:
        logger.error("章节AI失败", extra=build_log_context(event="chapter_ai_failed", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="optimize", error=str(exc)))
        raise
    response = ChapterAIActionResponse(
        chapter_id=chapter_id,
        action="optimize",
        result_text=str(result.get("result_text") or ""),
        analysis=result.get("analysis") or {},
        outline_draft=result.get("outline_draft") if isinstance(result.get("outline_draft"), dict) else None,
        used_fallback=bool(result.get("used_fallback")),
    )
    logger.info(
        "章节AI完成",
        extra=build_log_context(event="chapter_ai_finished", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="optimize"),
    )
    return response


@router.post("/{chapter_id}/ai/continue", response_model=ChapterAIActionResponse)
async def ai_continue(
    chapter_id: str,
    request: ChapterAIActionRequest,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    outline_repo: IChapterOutlineRepository = Depends(get_chapter_outline_repo),
    service: ChapterAIService = Depends(get_chapter_ai_service),
):
    chapter = _load_chapter(chapter_id, chapter_repo)
    logger.info(
        "章节AI开始",
        extra=build_log_context(event="chapter_ai_started", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="continue"),
    )
    outline = request.outline if isinstance(request.outline, dict) else _outline_dict(chapter_id, outline_repo)
    try:
        result = await service.continue_writing(
            chapter,
            request.target_word_count,
            outline,
            global_memory_summary=request.global_memory_summary,
            global_outline_summary=request.global_outline_summary,
            recent_chapter_summaries=request.recent_chapter_summaries,
        )
    except Exception as exc:
        logger.error("章节AI失败", extra=build_log_context(event="chapter_ai_failed", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="continue", error=str(exc)))
        raise
    response = ChapterAIActionResponse(
        chapter_id=chapter_id,
        action="continue",
        result_text=str(result.get("result_text") or ""),
        analysis=result.get("analysis") or {},
        outline_draft=result.get("outline_draft") if isinstance(result.get("outline_draft"), dict) else None,
        used_fallback=bool(result.get("used_fallback")),
    )
    logger.info(
        "章节AI完成",
        extra=build_log_context(event="chapter_ai_finished", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="continue"),
    )
    return response


@router.post("/{chapter_id}/ai/rewrite-style", response_model=ChapterAIActionResponse)
async def ai_rewrite_style(
    chapter_id: str,
    request: ChapterAIActionRequest,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    outline_repo: IChapterOutlineRepository = Depends(get_chapter_outline_repo),
    service: ChapterAIService = Depends(get_chapter_ai_service),
):
    chapter = _load_chapter(chapter_id, chapter_repo)
    logger.info(
        "章节AI开始",
        extra=build_log_context(event="chapter_ai_started", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="rewrite-style"),
    )
    outline = request.outline if isinstance(request.outline, dict) else _outline_dict(chapter_id, outline_repo)
    try:
        result = await service.rewrite_style(
            chapter,
            request.style,
            outline,
            global_memory_summary=request.global_memory_summary,
            global_outline_summary=request.global_outline_summary,
            recent_chapter_summaries=request.recent_chapter_summaries,
        )
    except Exception as exc:
        logger.error("章节AI失败", extra=build_log_context(event="chapter_ai_failed", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="rewrite-style", error=str(exc)))
        raise
    response = ChapterAIActionResponse(
        chapter_id=chapter_id,
        action="rewrite-style",
        result_text=str(result.get("result_text") or ""),
        analysis=result.get("analysis") or {},
        outline_draft=result.get("outline_draft") if isinstance(result.get("outline_draft"), dict) else None,
        used_fallback=bool(result.get("used_fallback")),
    )
    logger.info(
        "章节AI完成",
        extra=build_log_context(event="chapter_ai_finished", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="rewrite-style"),
    )
    return response


@router.post("/{chapter_id}/ai/analyze", response_model=ChapterAIActionResponse)
async def ai_analyze(
    chapter_id: str,
    request: ChapterAIActionRequest,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    outline_repo: IChapterOutlineRepository = Depends(get_chapter_outline_repo),
    service: ChapterAIService = Depends(get_chapter_ai_service),
):
    chapter = _load_chapter(chapter_id, chapter_repo)
    logger.info(
        "章节AI开始",
        extra=build_log_context(event="chapter_ai_started", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="analyze"),
    )
    outline = request.outline if isinstance(request.outline, dict) else _outline_dict(chapter_id, outline_repo)
    try:
        result = await service.analyze(
            chapter,
            outline,
            global_memory_summary=request.global_memory_summary,
            global_outline_summary=request.global_outline_summary,
            recent_chapter_summaries=request.recent_chapter_summaries,
        )
    except Exception as exc:
        logger.error("章节AI失败", extra=build_log_context(event="chapter_ai_failed", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="analyze", error=str(exc)))
        raise
    response = ChapterAIActionResponse(
        chapter_id=chapter_id,
        action="analyze",
        result_text=str(result.get("result_text") or ""),
        analysis=result.get("analysis") or {},
        outline_draft=result.get("outline_draft") if isinstance(result.get("outline_draft"), dict) else None,
        used_fallback=bool(result.get("used_fallback")),
    )
    logger.info(
        "章节AI完成",
        extra=build_log_context(event="chapter_ai_finished", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="analyze"),
    )
    return response


@router.post("/{chapter_id}/ai/generate-from-outline", response_model=ChapterAIActionResponse)
async def ai_generate_from_outline(
    chapter_id: str,
    request: ChapterAIActionRequest,
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    outline_repo: IChapterOutlineRepository = Depends(get_chapter_outline_repo),
    service: ChapterAIService = Depends(get_chapter_ai_service),
):
    chapter = _load_chapter(chapter_id, chapter_repo)
    logger.info(
        "章节AI开始",
        extra=build_log_context(event="chapter_ai_started", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="generate-from-outline"),
    )
    outline = request.outline if isinstance(request.outline, dict) else _outline_dict(chapter_id, outline_repo)
    try:
        result = await service.generate_from_outline(
            chapter,
            outline,
            request.target_word_count,
            global_memory_summary=request.global_memory_summary,
            global_outline_summary=request.global_outline_summary,
            recent_chapter_summaries=request.recent_chapter_summaries,
        )
    except Exception as exc:
        logger.error("章节AI失败", extra=build_log_context(event="chapter_ai_failed", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="generate-from-outline", error=str(exc)))
        raise
    response = ChapterAIActionResponse(
        chapter_id=chapter_id,
        action="generate-from-outline",
        result_text=str(result.get("result_text") or ""),
        analysis=result.get("analysis") or {},
        outline_draft=result.get("outline_draft") if isinstance(result.get("outline_draft"), dict) else None,
        used_fallback=bool(result.get("used_fallback")),
    )
    logger.info(
        "章节AI完成",
        extra=build_log_context(event="chapter_ai_finished", chapter_id=chapter.id.value, chapter_number=chapter.number, novel_id=chapter.novel_id.value, action="generate-from-outline"),
    )
    return response
