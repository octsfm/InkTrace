"""
内容管理API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/content.py


from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException

from application.agent_mvp import AnalysisTool, NovelMemory, TaskContext
from application.agent_mvp.memory import merge_memory
from application.services.content_service import ContentService
from application.services.project_service import ProjectService
from application.dto.request_dto import ImportNovelRequest
from application.dto.response_dto import NovelResponse, StyleAnalysisResponse, PlotAnalysisResponse
from domain.types import NovelId
from presentation.api.dependencies import get_content_service, get_llm_factory, get_project_service


router = APIRouter(prefix="/api/content", tags=["content"])


def _error_detail(code: str, message: str, user_message: str) -> Dict[str, Any]:
    return {"code": code, "message": message, "user_message": user_message}


def _to_dict(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model)


async def _analyze_and_bind_memory(
    novel_id: str,
    content_service: ContentService,
    project_service: ProjectService,
    llm_factory
) -> Dict[str, Any]:
    project = project_service.ensure_project_for_novel(NovelId(novel_id))
    existing_memory = project_service.get_memory_by_novel(NovelId(novel_id))
    if isinstance(existing_memory, dict) and any(existing_memory.values()):
        return {"project_id": project.id.value, "memory": existing_memory}
    novel_text = content_service.get_novel_text(novel_id)
    if not novel_text.strip():
        empty_memory = NovelMemory().to_agent_context()
        project_service.bind_memory_to_novel(NovelId(novel_id), empty_memory)
        return {"project_id": project.id.value, "memory": empty_memory}
    analyzer = AnalysisTool(llm_factory.primary_client, llm_factory.backup_client)
    structure = await analyzer.execute_async(
        TaskContext(novel_id=novel_id, goal="导入后章节拆分"),
        {"mode": "structure_mode", "novel_text": novel_text}
    )
    if structure.status != "success":
        raise ValueError("章节拆分失败")
    chapters = structure.payload.get("chapters") or []
    if not chapters:
        raise ValueError("未识别到可分析章节")
    merged_memory: Dict[str, Any] = {}
    for chapter in chapters:
        incremental = await analyzer.execute_async(
            TaskContext(novel_id=novel_id, goal="导入后增量分析"),
            {"mode": "incremental_mode", "chapter": chapter}
        )
        if incremental.status != "success":
            raise ValueError(f"章节分析失败: {chapter.get('title') or chapter.get('index')}")
        merged_memory = merge_memory(merged_memory, incremental.payload)
    consolidate = await analyzer.execute_async(
        TaskContext(novel_id=novel_id, goal="导入后全局收敛"),
        {"mode": "consolidate_mode", "memory": merged_memory}
    )
    if consolidate.status != "success":
        raise ValueError("全局收敛失败")
    merged_memory = merge_memory(merged_memory, consolidate.payload)
    progress = merged_memory.get("current_progress") or {}
    progress["latest_chapter_number"] = len(chapters)
    progress["latest_goal"] = "导入完成"
    progress["last_summary"] = f"已完成{len(chapters)}章增量分析并收敛"
    merged_memory["current_progress"] = progress
    project_service.bind_memory_to_novel(NovelId(novel_id), merged_memory)
    return {"project_id": project.id.value, "memory": merged_memory}


@router.post("/import")
async def import_novel(
    request: ImportNovelRequest,
    service: ContentService = Depends(get_content_service),
    project_service: ProjectService = Depends(get_project_service),
    llm_factory=Depends(get_llm_factory)
):
    """
    导入小说文件
    
    Args:
        request: 导入请求
        service: 内容服务
        
    Returns:
        小说响应
    """
# 文件：模块：content

    try:
        novel = service.import_novel(request)
        memory_result = await _analyze_and_bind_memory(
            request.novel_id,
            service,
            project_service,
            llm_factory
        )
        return {
            "novel": _to_dict(novel),
            "project_id": memory_result["project_id"],
            "memory": memory_result["memory"],
            "analysis_status": "done"
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/style/{novel_id}", response_model=StyleAnalysisResponse)
async def analyze_style(
    novel_id: str,
    service: ContentService = Depends(get_content_service)
):
    """
    分析小说文风
    
    Args:
        novel_id: 小说ID
        service: 内容服务
        
    Returns:
        文风分析响应
    """
# 文件：模块：content

    try:
        return service.analyze_style(novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/plot/{novel_id}", response_model=PlotAnalysisResponse)
async def analyze_plot(
    novel_id: str,
    service: ContentService = Depends(get_content_service)
):
    """
    分析小说剧情
    
    Args:
        novel_id: 小说ID
        service: 内容服务
        
    Returns:
        剧情分析响应
    """
# 文件：模块：content

    try:
        return service.analyze_plot(novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/memory/{novel_id}")
async def get_memory_by_novel(
    novel_id: str,
    project_service: ProjectService = Depends(get_project_service)
):
    try:
        project = project_service.ensure_project_for_novel(NovelId(novel_id))
        return {
            "project_id": project.id.value,
            "memory": project_service.get_memory_by_novel(NovelId(novel_id))
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/organize/{novel_id}")
async def organize_story_structure(
    novel_id: str,
    service: ContentService = Depends(get_content_service),
    project_service: ProjectService = Depends(get_project_service),
    llm_factory=Depends(get_llm_factory)
):
    try:
        result = await _analyze_and_bind_memory(novel_id, service, project_service, llm_factory)
        return {"status": "done", "project_id": result["project_id"], "memory": result["memory"]}
    except ValueError as e:
        message = str(e)
        if "小说不存在" in message:
            raise HTTPException(
                status_code=404,
                detail=_error_detail("NOVEL_NOT_FOUND", message, "未找到对应作品，请先创建或导入。")
            )
        raise HTTPException(
            status_code=400,
            detail=_error_detail("STRUCTURE_INPUT_INVALID", message, "故事结构整理失败，请检查内容后重试。")
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("STRUCTURE_INTERNAL_ERROR", str(e), "故事结构整理失败，请稍后再试。")
        )
