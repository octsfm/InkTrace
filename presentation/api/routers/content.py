"""
内容管理API路由

作者：孔利群
"""

# 文件路径：presentation/api/routers/content.py


from typing import Any, Dict, Optional
import os
import shutil
import tempfile
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from application.agent_mvp import AnalysisTool, NovelMemory, TaskContext
from application.agent_mvp.memory import merge_memory
from application.services.content_service import ContentService
from application.services.project_service import ProjectService
from application.dto.request_dto import ImportNovelRequest
from application.dto.response_dto import NovelResponse, StyleAnalysisResponse, PlotAnalysisResponse
from domain.types import NovelId
from presentation.api.dependencies import get_content_service, get_llm_factory, get_project_service


router = APIRouter(prefix="/api/content", tags=["content"])
logger = logging.getLogger(__name__)
PROGRESS_CACHE: Dict[str, Dict[str, Any]] = {}


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
    llm_factory,
    force_rebuild: bool = False
) -> Dict[str, Any]:
    logger.info("[Structure] 开始整理故事结构 novel_id=%s force_rebuild=%s", novel_id, force_rebuild)
    project = project_service.ensure_project_for_novel(NovelId(novel_id))
    existing_memory = project_service.get_memory_by_novel(NovelId(novel_id))
    if (not force_rebuild) and isinstance(existing_memory, dict) and any(existing_memory.values()):
        logger.info("[Structure] 命中已有memory，跳过重建 novel_id=%s", novel_id)
        return {"project_id": project.id.value, "memory": existing_memory}
    novel_text = content_service.get_novel_text(novel_id)
    logger.info("[Structure] 获取小说文本完成 novel_id=%s text_length=%d", novel_id, len(novel_text))
    if not novel_text.strip():
        empty_memory = NovelMemory().to_agent_context()
        project_service.bind_memory_to_novel(NovelId(novel_id), empty_memory)
        logger.warning("[Structure] 小说文本为空，绑定空memory novel_id=%s", novel_id)
        return {"project_id": project.id.value, "memory": empty_memory}
    analyzer = AnalysisTool(llm_factory.primary_client, llm_factory.backup_client)
    structure = await analyzer.execute_async(
        TaskContext(novel_id=novel_id, goal="导入后章节拆分"),
        {"mode": "structure_mode", "novel_text": novel_text}
    )
    if structure.status != "success":
        logger.error("[Structure] 拆分失败 novel_id=%s status=%s error=%s", novel_id, structure.status, structure.error)
        raise ValueError("章节拆分失败")
    chapters = structure.payload.get("chapters") or []
    logger.info("[Structure] 文本拆分完成 novel_id=%s chunks=%d", novel_id, len(chapters))
    PROGRESS_CACHE[novel_id] = {
        "current": 0,
        "total": len(chapters),
        "percent": 0,
        "status": "running",
        "message": f"正在分析第 0 / {len(chapters)} 段（0%）"
    }
    if not chapters:
        logger.error("[Structure] 拆分后无可分析片段 novel_id=%s", novel_id)
        raise ValueError("未识别到可分析章节")
    merged_memory: Dict[str, Any] = {}
    for idx, chapter in enumerate(chapters, 1):
        chapter_title = chapter.get("title") or chapter.get("index")
        chapter_text = str(chapter.get("content") or "")
        logger.info(
            "[Structure] 开始增量分析 novel_id=%s chunk=%d/%d title=%s content_length=%d",
            novel_id,
            idx,
            len(chapters),
            chapter_title,
            len(chapter_text)
        )
        incremental = await analyzer.execute_async(
            TaskContext(novel_id=novel_id, goal="导入后增量分析"),
            {"mode": "incremental_mode", "chapter": chapter}
        )
        if incremental.status != "success":
            logger.error(
                "[Structure] 增量分析失败 novel_id=%s chunk=%d title=%s error=%s",
                novel_id,
                idx,
                chapter_title,
                incremental.error
            )
            raise ValueError(f"章节分析失败: {chapter.get('title') or chapter.get('index')}")
        merged_memory = merge_memory(merged_memory, incremental.payload)
        percent = int(idx / len(chapters) * 100)
        PROGRESS_CACHE[novel_id] = {
            "current": idx,
            "total": len(chapters),
            "percent": percent,
            "status": "running",
            "message": f"正在分析第 {idx} / {len(chapters)} 段（{percent}%）"
        }
        logger.info("[Structure] 增量分析完成 novel_id=%s chunk=%d/%d", novel_id, idx, len(chapters))
    logger.info("[Structure] 开始全局收敛 novel_id=%s", novel_id)
    consolidate = await analyzer.execute_async(
        TaskContext(novel_id=novel_id, goal="导入后全局收敛"),
        {"mode": "consolidate_mode", "memory": merged_memory}
    )
    if consolidate.status != "success":
        logger.error("[Structure] 全局收敛失败 novel_id=%s error=%s", novel_id, consolidate.error)
        raise ValueError("全局收敛失败")
    merged_memory = merge_memory(merged_memory, consolidate.payload)
    progress_text = str(merged_memory.get("current_progress") or "").strip()
    final_summary = f"导入完成：已完成{len(chapters)}段增量分析并收敛"
    merged_memory["current_progress"] = (
        f"{progress_text}；{final_summary}" if progress_text and final_summary not in progress_text else (final_summary or progress_text)
    )
    project_service.bind_memory_to_novel(NovelId(novel_id), merged_memory)
    PROGRESS_CACHE[novel_id] = {
        "current": len(chapters),
        "total": len(chapters),
        "percent": 100,
        "status": "done",
        "message": f"整理完成：已完成{len(chapters)}段分析（100%）"
    }
    logger.info(
        "[Structure] 整理完成并绑定memory novel_id=%s chunks=%d characters=%d events=%d",
        novel_id,
        len(chapters),
        len(merged_memory.get("characters") or []),
        len(merged_memory.get("events") or [])
    )
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
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail=_error_detail(
                "IMPORT_ENCODING_INVALID",
                "TXT编码解析失败",
                "文件编码不受支持，请使用UTF-8或GB18030后重试。"
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("IMPORT_INTERNAL_ERROR", str(e), "导入失败，请稍后重试。")
        )


@router.post("/import/upload")
async def import_novel_upload(
    novel_id: str = Form(...),
    novel_file: UploadFile = File(...),
    outline_file: Optional[UploadFile] = File(default=None),
    service: ContentService = Depends(get_content_service),
    project_service: ProjectService = Depends(get_project_service),
    llm_factory=Depends(get_llm_factory)
):
    temp_dir = tempfile.mkdtemp(prefix="inktrace_upload_")
    novel_path = os.path.join(temp_dir, novel_file.filename or "novel.txt")
    outline_path = None
    try:
        with open(novel_path, "wb") as f:
            f.write(await novel_file.read())
        if outline_file is not None:
            outline_path = os.path.join(temp_dir, outline_file.filename or "outline.txt")
            with open(outline_path, "wb") as f:
                f.write(await outline_file.read())

        request = ImportNovelRequest(novel_id=novel_id, file_path=novel_path)
        novel = service.import_novel(request)
        memory_result = await _analyze_and_bind_memory(
            novel_id,
            service,
            project_service,
            llm_factory
        )
        return {
            "novel": _to_dict(novel),
            "project_id": memory_result["project_id"],
            "memory": memory_result["memory"],
            "analysis_status": "done",
            "outline_uploaded": bool(outline_path)
        }
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail=_error_detail(
                "IMPORT_ENCODING_INVALID",
                "TXT编码解析失败",
                "文件编码不受支持，请使用UTF-8或GB18030后重试。"
            )
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("IMPORT_INTERNAL_ERROR", str(e), "导入失败，请稍后重试。")
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


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
        PROGRESS_CACHE[novel_id] = {
            "current": 0,
            "total": 0,
            "percent": 0,
            "status": "running",
            "message": "正在初始化整理任务（0%）"
        }
        logger.info("[StructureAPI] 收到整理请求 novel_id=%s", novel_id)
        result = await _analyze_and_bind_memory(novel_id, service, project_service, llm_factory, force_rebuild=True)
        logger.info("[StructureAPI] 整理请求完成 novel_id=%s project_id=%s", novel_id, result["project_id"])
        return {"status": "done", "project_id": result["project_id"], "memory": result["memory"]}
    except ValueError as e:
        message = str(e)
        progress = PROGRESS_CACHE.get(novel_id) or {"current": 0, "total": 0, "percent": 0}
        progress.update({"status": "error", "message": f"整理失败：{message}"})
        PROGRESS_CACHE[novel_id] = progress
        logger.warning("[StructureAPI] 整理请求参数错误 novel_id=%s error=%s", novel_id, message)
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
        progress = PROGRESS_CACHE.get(novel_id) or {"current": 0, "total": 0, "percent": 0}
        progress.update({"status": "error", "message": f"整理失败：{str(e)}"})
        PROGRESS_CACHE[novel_id] = progress
        logger.exception("[StructureAPI] 整理请求异常 novel_id=%s", novel_id)
        raise HTTPException(
            status_code=500,
            detail=_error_detail("STRUCTURE_INTERNAL_ERROR", str(e), "故事结构整理失败，请稍后再试。")
        )


@router.get("/organize/progress/{novel_id}")
async def get_organize_progress(novel_id: str):
    progress = PROGRESS_CACHE.get(novel_id) or {
        "current": 0,
        "total": 0,
        "percent": 0,
        "status": "idle",
        "message": "暂无整理任务"
    }
    return progress
