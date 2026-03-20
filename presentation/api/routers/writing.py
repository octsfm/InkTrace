"""
续写服务API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/writing.py


import hashlib
import os
import uuid
from datetime import datetime
from types import SimpleNamespace
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from application.agent_mvp import (
    AgentOrchestrator,
    ContinueWritingTool,
    ExecutionContext,
    RAGSearchTool,
    StoryBranchTool,
    TaskContext,
    WritingGenerateTool
)
from application.services.project_service import ProjectService
from application.services.writing_service import WritingService
from application.dto.request_dto import ContinueWritingRequest, GenerateBranchesRequest, GenerateChapterRequest, PlanPlotRequest
from application.dto.response_dto import ContinueWritingResponse, GenerateChapterResponse
from infrastructure.llm.llm_factory import LLMFactory
from domain.entities.chapter import Chapter
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.novel_repository import INovelRepository
from domain.types import ChapterId, ChapterStatus, NovelId
from presentation.api.dependencies import get_chapter_repo, get_llm_factory, get_novel_repo, get_project_service, get_writing_service


router = APIRouter(prefix="/api/writing", tags=["writing"])


def _error_detail(code: str, message: str, user_message: str):
    return {"code": code, "message": message, "user_message": user_message}


def _is_agent_enabled() -> bool:
    return os.environ.get("INKTRACE_ENABLE_AGENT", "false").lower() in {"1", "true", "yes", "on"}


def _gray_ratio() -> int:
    raw = os.environ.get("INKTRACE_AGENT_GRAY_RATIO", "0").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 0
    return max(0, min(100, value))


def _has_llm_credentials() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("KIMI_API_KEY"))


def _has_available_llm_client(llm_factory: LLMFactory) -> bool:
    return bool(
        getattr(llm_factory.config, "deepseek_api_key", "")
        or getattr(llm_factory.config, "kimi_api_key", "")
    )


def _fallback_generate_response(request: GenerateChapterRequest) -> GenerateChapterResponse:
    fallback_result = WritingGenerateTool().execute(
        TaskContext(
            novel_id=request.novel_id,
            goal=request.goal,
            target_word_count=request.target_word_count
        ),
        {
            "goal": request.goal,
            "target_word_count": request.target_word_count
        }
    )
    payload = fallback_result.payload or {}
    return GenerateChapterResponse(
        chapter_id=str(payload.get("chapter_title") or "fallback-chapter"),
        content=str(payload.get("content") or ""),
        word_count=int(payload.get("word_count") or 0),
        metadata={"route": "legacy_fallback", "gray_ratio": _gray_ratio()}
    )


def _should_use_agent(request: GenerateChapterRequest) -> bool:
    if not _is_agent_enabled():
        return False
    ratio = _gray_ratio()
    if ratio <= 0:
        return False
    if ratio >= 100:
        return True
    key = f"{request.novel_id}:{request.trace_id or request.goal}"
    bucket = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % 100
    return bucket < ratio


def _build_legacy_generate_request(request: GenerateChapterRequest):
    return SimpleNamespace(
        novel_id=request.novel_id,
        target_word_count=request.target_word_count,
        enable_style_mimicry=bool((request.options or {}).get("enable_style_mimicry", False)),
        enable_consistency_check=bool((request.options or {}).get("enable_consistency_check", False)),
        plot_direction=request.goal
    )


def _build_legacy_plan_request(request: PlanPlotRequest):
    return SimpleNamespace(
        novel_id=request.novel_id,
        chapter_count=request.chapter_count,
        direction=request.goal
    )


@router.post("/plan", response_model=List[dict])
async def plan_plot(
    request: PlanPlotRequest,
    service: WritingService = Depends(get_writing_service)
):
    """
    规划剧情走向
    
    Args:
        request: 规划请求
        service: 续写服务
        
    Returns:
        剧情节点列表
    """
# 文件：模块：writing

    try:
        return service.plan_plot(_build_legacy_plan_request(request))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate", response_model=GenerateChapterResponse)
async def generate_chapter(
    request: GenerateChapterRequest,
    service: WritingService = Depends(get_writing_service),
    project_service: ProjectService = Depends(get_project_service),
    llm_factory: LLMFactory = Depends(get_llm_factory)
):
    """
    生成章节
    
    Args:
        request: 生成请求
        service: 续写服务
        
    Returns:
        生成响应
    """
# 文件：模块：writing

    try:
        if _should_use_agent(request):
            memory = {}
            try:
                project_service.ensure_project_for_novel(NovelId(request.novel_id))
                memory = project_service.get_memory_by_novel(NovelId(request.novel_id))
            except ValueError:
                memory = {}
            task_context = TaskContext(
                novel_id=request.novel_id,
                goal=request.goal,
                target_word_count=request.target_word_count
            )
            task_context.memory = memory
            execution_context = ExecutionContext(timeout_seconds=12, max_steps=4)
            orchestrator = AgentOrchestrator(
                tools={
                    "RAGSearchTool": RAGSearchTool(),
                    "WritingGenerateTool": WritingGenerateTool()
                }
            )
            agent_result = orchestrator.run(task_context, execution_context)
            final_output = agent_result.get("final_output") or {}
            content = str(final_output.get("content") or "")
            if not content:
                raise HTTPException(status_code=500, detail="Agent链路未生成内容")
            return GenerateChapterResponse(
                chapter_id=str(final_output.get("chapter_title") or "agent-mvp-chapter"),
                content=content,
                word_count=int(final_output.get("word_count") or len(content)),
                metadata={
                    "route": "agent",
                    "gray_ratio": _gray_ratio(),
                    "steps": agent_result.get("steps"),
                    "request_id": agent_result.get("request_id")
                }
            )

        if not _has_available_llm_client(llm_factory):
            return _fallback_generate_response(request)
        try:
            legacy_response = service.generate_chapter(_build_legacy_generate_request(request))
        except Exception:
            return _fallback_generate_response(request)
        metadata = legacy_response.metadata or {}
        metadata.update({"route": "legacy", "gray_ratio": _gray_ratio()})
        legacy_response.metadata = metadata
        return legacy_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/branches")
async def generate_story_branches(
    request: GenerateBranchesRequest,
    project_service: ProjectService = Depends(get_project_service),
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    llm_factory: LLMFactory = Depends(get_llm_factory)
):
    try:
        novel_id = NovelId(request.novel_id)
        project_service.ensure_project_for_novel(novel_id)
        memory = project_service.get_memory_by_novel(novel_id)
        if not memory:
            raise HTTPException(
                status_code=400,
                detail=_error_detail("MEMORY_REQUIRED", "memory为空", "请先整理故事结构后再生成剧情分支。")
            )
        chapters = chapter_repo.find_by_novel(novel_id)
        latest_text = request.current_chapter_content or (chapters[-1].content if chapters else "")
        tool = StoryBranchTool(llm_factory.primary_client, llm_factory.backup_client)
        task_context = TaskContext(
            novel_id=request.novel_id,
            goal=request.direction_hint or "按主线推进",
            target_word_count=0
        )
        task_context.memory = memory
        result = await tool.execute_async(
            task_context,
            {
                "memory": memory,
                "current_chapter_content": latest_text,
                "direction_hint": request.direction_hint or "",
                "branch_count": request.branch_count
            }
        )
        if result.status != "success":
            error = result.error or {}
            raise HTTPException(
                status_code=400,
                detail=_error_detail(
                    error.get("code") or "BRANCH_FAILED",
                    error.get("message") or "剧情分支生成失败",
                    "剧情分支生成失败，请稍后重试。"
                )
            )
        return {
            "branches": (result.payload or {}).get("branches") or [],
            "memory_snapshot": memory,
            "latest_chapter_number": chapters[-1].number if chapters else 0
        }
    except ValueError as e:
        message = str(e)
        if "小说不存在" in message or "项目不存在" in message:
            raise HTTPException(
                status_code=404,
                detail=_error_detail("NOVEL_NOT_FOUND", message, "未找到对应作品，请先创建或导入。")
            )
        raise HTTPException(
            status_code=400,
            detail=_error_detail("BRANCH_INPUT_INVALID", message, "剧情分支参数有误，请检查后重试。")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("BRANCH_INTERNAL_ERROR", str(e), "剧情分支生成失败，请稍后重试。")
        )


@router.post("/continue", response_model=ContinueWritingResponse)
async def continue_writing(
    request: ContinueWritingRequest,
    project_service: ProjectService = Depends(get_project_service),
    chapter_repo: IChapterRepository = Depends(get_chapter_repo),
    novel_repo: INovelRepository = Depends(get_novel_repo),
    llm_factory: LLMFactory = Depends(get_llm_factory)
):
    try:
        idempotency_key = f"{request.novel_id}:{request.goal}:{request.trace_id or 'default'}"
        project_service.ensure_project_for_novel(NovelId(request.novel_id))
        memory = project_service.get_memory_by_novel(NovelId(request.novel_id))
        if not memory:
            raise HTTPException(
                status_code=400,
                detail=_error_detail("MEMORY_REQUIRED", "memory为空", "请先整理故事结构后再继续创作。")
            )
        novel_id = NovelId(request.novel_id)
        chapters = chapter_repo.find_by_novel(novel_id)
        latest_chapter = chapters[-1] if chapters else None
        next_number = (latest_chapter.number + 1) if latest_chapter else 1
        task_context = TaskContext(
            novel_id=request.novel_id,
            goal=request.goal,
            target_word_count=request.target_word_count
        )
        task_context.memory = memory
        tool = ContinueWritingTool(llm_factory.primary_client, llm_factory.backup_client)
        result = await tool.execute_async(
            task_context,
            {
                "direction": request.goal,
                "memory": memory,
                "chapters": [{"content": ch.content, "number": ch.number, "title": ch.title} for ch in chapters[-8:]],
                "target_word_count": request.target_word_count,
                "idempotency_key": idempotency_key
            }
        )
        if result.status != "success":
            error = result.error or {}
            raise HTTPException(
                status_code=400,
                detail=_error_detail(
                    error.get("code") or "CONTINUE_FAILED",
                    error.get("message") or "续写失败",
                    "当前章节创作失败，请调整目标后重试。"
                )
            )
        chapter_text = str((result.payload or {}).get("chapter_text") or "")
        now = datetime.now()
        chapter = Chapter(
            id=ChapterId(str(uuid.uuid4())),
            novel_id=novel_id,
            number=next_number,
            title=f"第{next_number}章",
            content=chapter_text,
            status=ChapterStatus.DRAFT,
            created_at=now,
            updated_at=now
        )
        chapter_repo.save(chapter)
        novel = novel_repo.find_by_id(novel_id)
        if novel:
            novel.add_chapter(chapter, now)
            novel_repo.save(novel)
        progress = memory.get("current_progress") or {}
        progress.update(
            {
                "latest_chapter_number": next_number,
                "latest_goal": request.goal,
                "last_summary": chapter_text[:120]
            }
        )
        memory["current_progress"] = progress
        project_service.bind_memory_to_novel(novel_id, memory)
        return ContinueWritingResponse(
            content=chapter_text,
            word_count=len(chapter_text),
            metadata={
                "route": "continue_tool",
                "used_memory": (result.payload or {}).get("used_memory", {}),
                "project_bound": True,
                "chapter_number": next_number
            }
        )
    except ValueError as e:
        message = str(e)
        if "小说不存在" in message or "项目不存在" in message:
            raise HTTPException(
                status_code=404,
                detail=_error_detail("NOVEL_NOT_FOUND", message, "未找到对应作品，请先创建或导入。")
            )
        raise HTTPException(
            status_code=400,
            detail=_error_detail("CONTINUE_INPUT_INVALID", message, "续写参数有误，请检查后重试。")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("CONTINUE_INTERNAL_ERROR", str(e), "续写失败，请稍后再试。")
        )
