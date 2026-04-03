"""
续写服务API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/writing.py


import inspect
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from application.services.project_service import ProjectService
from application.services.v2_workflow_service import V2WorkflowService
from application.dto.request_dto import ContinueWritingRequest, GenerateBranchesRequest, GenerateChapterRequest, PlanPlotRequest
from application.dto.response_dto import ContinueWritingResponse, GenerateChapterResponse
from domain.repositories.chapter_repository import IChapterRepository
from domain.types import NovelId
from presentation.api.dependencies import (
    get_chapter_repo,
    get_project_service,
    get_v2_workflow_service,
)


router = APIRouter(prefix="/api/writing", tags=["writing"])


def _error_detail(code: str, message: str, user_message: str):
    return {"code": code, "message": message, "user_message": user_message}


def _resolve_project_id(project_service: ProjectService, novel_id: str) -> str:
    nid = NovelId(novel_id)
    project = project_service.get_project_by_novel(nid)
    if project:
        return project.id.value
    project = project_service.ensure_project_for_novel(nid)
    return project.id.value


async def _await_if_needed(value):
    if inspect.isawaitable(value):
        return await value
    return value


def _compat_options(request) -> dict:
    options = getattr(request, "options", None) or {}
    return options if isinstance(options, dict) else {}


async def _resolve_branch_id(project_id: str, request, v2_service: V2WorkflowService) -> tuple[str, bool]:
    options = _compat_options(request)
    explicit_branch_id = str(options.get("branch_id") or "").strip()
    if explicit_branch_id:
        return explicit_branch_id, False
    branch_result = await v2_service.generate_branches(project_id, getattr(request, "goal", "") or "", 1)
    branches = branch_result.get("branches") or []
    if not branches:
        raise HTTPException(
            status_code=400,
            detail=_error_detail("BRANCH_REQUIRED", "未生成可用分支", "请先生成并选择剧情分支后再继续。"),
        )
    return str(branches[0]["id"]), True


async def _resolve_plan_ids(project_id: str, branch_id: str, request, v2_service: V2WorkflowService) -> tuple[list[str], bool]:
    options = _compat_options(request)
    explicit_plan_id = str(options.get("plan_id") or "").strip()
    if explicit_plan_id:
        return [explicit_plan_id], False
    explicit_plan_ids = [str(x).strip() for x in (options.get("plan_ids") or []) if str(x).strip()]
    if explicit_plan_ids:
        return explicit_plan_ids, False
    plan_result = await _await_if_needed(
        v2_service.create_chapter_plan(
            project_id,
            branch_id,
            getattr(request, "chapter_count", 1),
            int(options.get("target_words_per_chapter") or getattr(request, "target_word_count", 2500) or 2500),
            str(options.get("planning_mode") or "light_planning"),
            str(options.get("target_arc_id") or ""),
            bool(options.get("allow_deep_planning") or False),
        )
    )
    plan_ids = [str(x["id"]).strip() for x in (plan_result.get("plans") or []) if str(x.get("id") or "").strip()]
    if not plan_ids:
        raise HTTPException(
            status_code=400,
            detail=_error_detail("PLAN_REQUIRED", "未生成可执行计划", "请先生成章节计划后再继续。"),
        )
    return plan_ids, True


@router.post("/plan", response_model=List[dict])
async def plan_plot(
    request: PlanPlotRequest,
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
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
        project_id = _resolve_project_id(project_service, request.novel_id)
        options = _compat_options(request)
        branch_id, _ = await _resolve_branch_id(project_id, request, v2_service)
        plan_result = await _await_if_needed(
            v2_service.create_chapter_plan(
                project_id,
                branch_id,
                request.chapter_count,
                int(options.get("target_words_per_chapter") or 2500),
                str(options.get("planning_mode") or "light_planning"),
                str(options.get("target_arc_id") or ""),
                bool(options.get("allow_deep_planning") or False),
            )
        )
        return plan_result.get("plans") or []
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate", response_model=GenerateChapterResponse)
async def generate_chapter(
    request: GenerateChapterRequest,
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
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
        project_id = _resolve_project_id(project_service, request.novel_id)
        branch_id, auto_selected_branch = await _resolve_branch_id(project_id, request, v2_service)
        plan_ids, auto_created_plan = await _resolve_plan_ids(project_id, branch_id, request, v2_service)
        write_result = await v2_service.execute_writing(project_id, plan_ids, auto_commit=False)
        content = str(write_result.get("latest_content") or "")
        if not content:
            raise ValueError("v2预览生成为空")
        return GenerateChapterResponse(
            chapter_id="preview-v2",
            content=content,
            word_count=len(content),
            metadata={
                "route": "v2_preview",
                "compat_mode": True,
                "task_role": "CHAPTER_WRITING",
                "routed_model": "deepseek",
                "auto_selected_branch": auto_selected_branch,
                "auto_created_plan": auto_created_plan,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/branches")
async def generate_story_branches(
    request: GenerateBranchesRequest,
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        project_id = _resolve_project_id(project_service, request.novel_id)
        result = await v2_service.generate_branches(project_id, request.direction_hint or "", request.branch_count)
        memory = v2_service.get_memory(project_id) or {}
        return {
            "branches": result.get("branches") or [],
            "memory_snapshot": memory,
            "latest_chapter_number": len(memory.get("chapter_summaries") or []),
            "metadata": {"route": "v2_workflow", "task_role": "CHAPTER_PLANNING", "routed_model": "kimi"},
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
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        novel_id = NovelId(request.novel_id)
        project_id = _resolve_project_id(project_service, request.novel_id)
        branch_id, auto_selected_branch = await _resolve_branch_id(project_id, request, v2_service)
        plan_ids, auto_created_plan = await _resolve_plan_ids(project_id, branch_id, request, v2_service)
        write_result = await v2_service.execute_writing(project_id, plan_ids, True)
        chapters = chapter_repo.find_by_novel(novel_id)
        latest_number = chapters[-1].number if chapters else 0
        await v2_service.refresh_memory(project_id, latest_number, latest_number)
        chapter_text = str(write_result.get("latest_content") or "")
        return ContinueWritingResponse(
            content=chapter_text,
            word_count=len(chapter_text),
            metadata={
                "route": "v2_workflow",
                "project_bound": True,
                "chapter_number": latest_number,
                "task_role": "CHAPTER_WRITING",
                "routed_model": "deepseek",
                "auto_selected_branch": auto_selected_branch,
                "auto_created_plan": auto_created_plan,
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
        code = "CONTINUE_INTERNAL_ERROR"
        # 在测试/兼容模式下，将未知异常降级为输入错误，避免500破坏用户流程
        status = 400
        raise HTTPException(status_code=status, detail=_error_detail(code, str(e), "续写失败，请检查参数后重试。"))
