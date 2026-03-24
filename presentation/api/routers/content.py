from typing import Any, Dict, Optional
import hashlib
import logging
import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from application.agent_mvp import AnalysisTool, NovelMemory, TaskContext
from application.agent_mvp.memory import merge_memory
from application.dto.request_dto import ImportNovelRequest
from application.dto.response_dto import PlotAnalysisResponse, StyleAnalysisResponse
from application.services.content_service import ContentService
from application.services.project_service import ProjectService
from application.services.v2_workflow_service import V2WorkflowService
from domain.entities.organize_job import OrganizeJob
from domain.repositories.organize_job_repository import IOrganizeJobRepository
from domain.types import NovelId, OrganizeJobStatus
from presentation.api.dependencies import (
    get_content_service,
    get_llm_factory,
    get_organize_job_repo,
    get_project_service,
    get_v2_workflow_service,
)


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


def _make_source_hash(novel_text: str, outline_context: Dict[str, Any]) -> str:
    outline_text = "|".join(
        [
            str(outline_context.get("premise") or ""),
            str(outline_context.get("story_background") or ""),
            str(outline_context.get("world_setting") or ""),
        ]
    )
    payload = f"{novel_text}\n##outline##\n{outline_text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_progress_payload(
    current: int,
    total: int,
    status: str,
    message: str,
    resumable: bool = False,
    source_hash: str = "",
    last_error: str = "",
) -> Dict[str, Any]:
    percent = 0 if total <= 0 else int(current / total * 100)
    return {
        "current": current,
        "total": total,
        "percent": percent,
        "status": status,
        "message": message,
        "resumable": resumable,
        "source_hash": source_hash,
        "last_error": last_error,
    }


def _cache_progress(novel_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    PROGRESS_CACHE[novel_id] = payload
    return payload


def _is_not_found_error(message: str) -> bool:
    lowered = message.lower()
    novel_missing = "\u5c0f\u8bf4\u4e0d\u5b58\u5728"
    project_missing = "\u9879\u76ee\u4e0d\u5b58\u5728"
    return "not found" in lowered or novel_missing in message or project_missing in message


def _job_to_progress(job: Optional[OrganizeJob]) -> Dict[str, Any]:
    if not job:
        return _build_progress_payload(0, 0, OrganizeJobStatus.IDLE.value, "No organize job")
    if job.status == OrganizeJobStatus.DONE:
        message = f"Organize complete ({job.total_chunks}/{job.total_chunks})"
    elif job.status == OrganizeJobStatus.ERROR:
        message = job.last_error or "Organize failed"
    elif job.completed_chunks > 0:
        message = f"Ready to resume from chunk {job.completed_chunks + 1}"
    else:
        message = "Organize job ready"
    resumable = job.status in {OrganizeJobStatus.RUNNING, OrganizeJobStatus.ERROR} and job.completed_chunks < job.total_chunks
    return _build_progress_payload(
        current=job.completed_chunks,
        total=job.total_chunks,
        status=job.status.value,
        message=message,
        resumable=resumable,
        source_hash=job.source_hash,
        last_error=job.last_error,
    )


def _apply_outline_context(memory: Dict[str, Any], outline_context: Dict[str, Any]) -> Dict[str, Any]:
    if not outline_context:
        return memory
    premise = str(outline_context.get("premise") or "").strip()
    story_background = str(outline_context.get("story_background") or "").strip()
    world_setting = str(outline_context.get("world_setting") or "").strip()
    if premise:
        plot_outline = str(memory.get("plot_outline") or "").strip()
        memory["plot_outline"] = " | ".join([part for part in [premise, plot_outline] if part])
    outline_world_parts = [part for part in [world_setting, story_background] if part]
    if outline_world_parts:
        world_text = str(memory.get("world_settings") or "").strip()
        memory["world_settings"] = " | ".join(
            [part for part in [*outline_world_parts, world_text] if part]
        )
    return memory


def _safe_get_outline_context(content_service: ContentService, novel_id: str) -> Dict[str, Any]:
    getter = getattr(content_service, "get_outline_context", None)
    if not callable(getter):
        return {}
    outline_context = getter(novel_id)
    return outline_context if isinstance(outline_context, dict) else {}


async def _analyze_and_bind_memory(
    novel_id: str,
    content_service: ContentService,
    project_service: ProjectService,
    organize_job_repo: IOrganizeJobRepository,
    llm_factory,
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    logger.info("[Structure] start novel_id=%s force_rebuild=%s", novel_id, force_rebuild)
    novel_id_vo = NovelId(novel_id)
    project = project_service.ensure_project_for_novel(novel_id_vo)
    novel_text = content_service.get_novel_text(novel_id)
    outline_context = _safe_get_outline_context(content_service, novel_id)
    source_hash = _make_source_hash(novel_text, outline_context)

    job = organize_job_repo.find_by_novel_id(novel_id_vo) or OrganizeJob(novel_id=novel_id_vo)
    if force_rebuild or job.source_hash != source_hash:
        job.reset(source_hash)
        organize_job_repo.save(job)
    elif job.status == OrganizeJobStatus.DONE and isinstance(job.checkpoint_memory, dict) and any(job.checkpoint_memory.values()):
        _cache_progress(novel_id, _job_to_progress(job))
        return {"project_id": project.id.value, "memory": job.checkpoint_memory}

    if not novel_text.strip():
        empty_memory = NovelMemory().to_agent_context()
        project_service.bind_memory_to_novel(novel_id_vo, empty_memory)
        job.reset(source_hash, 0)
        job.checkpoint_memory = empty_memory
        job.mark_done()
        organize_job_repo.save(job)
        _cache_progress(novel_id, _job_to_progress(job))
        return {"project_id": project.id.value, "memory": empty_memory}

    analyzer = AnalysisTool(llm_factory.primary_client, llm_factory.backup_client)
    structure = await analyzer.execute_async(
        TaskContext(novel_id=novel_id, goal="organize_structure"),
        {"mode": "structure_mode", "novel_text": novel_text},
    )
    if structure.status != "success":
        message = "Failed to split source text into chunks"
        job.mark_error(message)
        organize_job_repo.save(job)
        _cache_progress(novel_id, _job_to_progress(job))
        raise ValueError(message)

    chapters = structure.payload.get("chapters") or []
    if not chapters:
        message = "No analyzable chunks were found"
        job.mark_error(message)
        organize_job_repo.save(job)
        _cache_progress(novel_id, _job_to_progress(job))
        raise ValueError(message)

    total_chunks = len(chapters)
    resume_from = 0 if force_rebuild else min(int(job.completed_chunks or 0), total_chunks)
    merged_memory: Dict[str, Any] = {}
    if resume_from > 0 and isinstance(job.checkpoint_memory, dict):
        merged_memory = job.checkpoint_memory
    job.total_chunks = total_chunks
    job.mark_running()
    organize_job_repo.save(job)
    _cache_progress(
        novel_id,
        _build_progress_payload(
            current=resume_from,
            total=total_chunks,
            status=OrganizeJobStatus.RUNNING.value,
            message=f"Analyzing chunks {resume_from}/{total_chunks}",
            resumable=resume_from > 0,
            source_hash=source_hash,
        ),
    )

    for idx, chapter in enumerate(chapters[resume_from:], resume_from + 1):
        chapter_title = chapter.get("title") or chapter.get("index")
        incremental = await analyzer.execute_async(
            TaskContext(novel_id=novel_id, goal="organize_incremental"),
            {"mode": "incremental_mode", "chapter": chapter},
        )
        if incremental.status != "success":
            message = f"Chunk analysis failed at {chapter_title}"
            job.mark_error(message)
            organize_job_repo.save(job)
            _cache_progress(novel_id, _job_to_progress(job))
            raise ValueError(message)
        merged_memory = merge_memory(merged_memory, incremental.payload)
        job.update_checkpoint(idx, total_chunks, merged_memory)
        job.mark_running()
        organize_job_repo.save(job)
        _cache_progress(
            novel_id,
            _build_progress_payload(
                current=idx,
                total=total_chunks,
                status=OrganizeJobStatus.RUNNING.value,
                message=f"Analyzing chunks {idx}/{total_chunks}",
                resumable=idx < total_chunks,
                source_hash=source_hash,
            ),
        )

    consolidate = await analyzer.execute_async(
        TaskContext(novel_id=novel_id, goal="organize_consolidate"),
        {"mode": "consolidate_mode", "memory": merged_memory},
    )
    if consolidate.status != "success":
        message = "Failed to consolidate analyzed chunks"
        job.mark_error(message)
        organize_job_repo.save(job)
        _cache_progress(novel_id, _job_to_progress(job))
        raise ValueError(message)

    merged_memory = merge_memory(merged_memory, consolidate.payload)
    merged_memory = _apply_outline_context(merged_memory, outline_context)
    progress_text = str(merged_memory.get("current_progress") or "").strip()
    final_summary = f"Organize complete: analyzed {total_chunks} chunks"
    merged_memory["current_progress"] = (
        f"{progress_text} | {final_summary}" if progress_text and final_summary not in progress_text else (final_summary or progress_text)
    )
    project_service.bind_memory_to_novel(novel_id_vo, merged_memory)
    job.update_checkpoint(total_chunks, total_chunks, merged_memory)
    job.mark_done()
    organize_job_repo.save(job)
    _cache_progress(novel_id, _job_to_progress(job))
    return {"project_id": project.id.value, "memory": merged_memory}


@router.post("/import")
async def import_novel(
    request: ImportNovelRequest,
    service: ContentService = Depends(get_content_service),
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        novel = service.import_novel(request)
        project = project_service.ensure_project_for_novel(NovelId(request.novel_id))
        organize_result = await v2_service.organize_project(project.id.value, "chapter_first", True)
        return {
            "novel": _to_dict(novel),
            "project_id": project.id.value,
            "memory": v2_service.get_memory(project.id.value),
            "memory_view": organize_result.get("memory_view") or {},
            "analysis_status": "done",
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
                "TXT encoding decode failed",
                "File encoding is not supported. Please use UTF-8 or GB18030.",
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("IMPORT_INTERNAL_ERROR", str(e), "Import failed, please try again later."),
        )


@router.post("/import/upload")
async def import_novel_upload(
    novel_id: str = Form(...),
    novel_file: UploadFile = File(...),
    outline_file: Optional[UploadFile] = File(default=None),
    service: ContentService = Depends(get_content_service),
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
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

        request = ImportNovelRequest(novel_id=novel_id, file_path=novel_path, outline_path=outline_path)
        novel = service.import_novel(request)
        project = project_service.ensure_project_for_novel(NovelId(novel_id))
        organize_result = await v2_service.organize_project(project.id.value, "chapter_first", True)
        return {
            "novel": _to_dict(novel),
            "project_id": project.id.value,
            "memory": v2_service.get_memory(project.id.value),
            "memory_view": organize_result.get("memory_view") or {},
            "analysis_status": "done",
            "outline_uploaded": bool(outline_path),
        }
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail=_error_detail(
                "IMPORT_ENCODING_INVALID",
                "TXT encoding decode failed",
                "File encoding is not supported. Please use UTF-8 or GB18030.",
            ),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("IMPORT_INTERNAL_ERROR", str(e), "Import failed, please try again later."),
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/style/{novel_id}", response_model=StyleAnalysisResponse)
async def analyze_style(
    novel_id: str,
    service: ContentService = Depends(get_content_service),
):
    try:
        return service.analyze_style(novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/plot/{novel_id}", response_model=PlotAnalysisResponse)
async def analyze_plot(
    novel_id: str,
    service: ContentService = Depends(get_content_service),
):
    try:
        return service.analyze_plot(novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/memory/{novel_id}")
async def get_memory_by_novel(
    novel_id: str,
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        project = project_service.get_project_by_novel(NovelId(novel_id))
        if not project:
            project = project_service.ensure_project_for_novel(NovelId(novel_id))
        memory = v2_service.get_memory(project.id.value) or {}
        memory_view = v2_service.get_memory_view(project.id.value) or {}
        return {
            "project_id": project.id.value,
            "memory": memory,
            "memory_view": memory_view,
            "compat_mode": True,
            "route": "content_compat_v2",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/organize/{novel_id}")
async def organize_story_structure(
    novel_id: str,
    force_rebuild: bool = Query(False),
    project_service: ProjectService = Depends(get_project_service),
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        logger.info("[StructureAPI] request novel_id=%s force_rebuild=%s", novel_id, force_rebuild)
        project = project_service.ensure_project_for_novel(NovelId(novel_id))
        _cache_progress(
            novel_id,
            _build_progress_payload(
                0,
                1,
                OrganizeJobStatus.RUNNING.value,
                "正在按v2工作流整理故事结构（0%）",
            ),
        )
        v2_result = await v2_service.organize_project(project.id.value, "chapter_first", force_rebuild)
        progress = PROGRESS_CACHE.get(novel_id) or _job_to_progress(organize_job_repo.find_by_novel_id(NovelId(novel_id)))
        if progress.get("status") != OrganizeJobStatus.DONE.value:
            progress = _cache_progress(
                novel_id,
                _build_progress_payload(
                    1,
                    1,
                    OrganizeJobStatus.DONE.value,
                    "v2整理完成（100%）",
                ),
            )
        return {
            "status": "done",
            "project_id": project.id.value,
            "memory": v2_service.get_memory(project.id.value),
            "memory_view": v2_result.get("memory_view") or {},
            "progress": progress,
        }
    except ValueError as e:
        message = str(e)
        job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
        if job:
            job.mark_error(message)
            organize_job_repo.save(job)
            _cache_progress(novel_id, _job_to_progress(job))
        else:
            _cache_progress(
                novel_id,
                _build_progress_payload(0, 0, OrganizeJobStatus.ERROR.value, message, last_error=message),
            )
        if _is_not_found_error(message):
            raise HTTPException(
                status_code=404,
                detail=_error_detail("NOVEL_NOT_FOUND", message, "Novel not found, please create or import it first."),
            )
        raise HTTPException(
            status_code=400,
            detail=_error_detail("STRUCTURE_INPUT_INVALID", message, "Story organize failed. Please review the content and try again."),
        )
    except Exception as e:
        message = str(e)
        job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
        if job:
            job.mark_error(message)
            organize_job_repo.save(job)
            _cache_progress(novel_id, _job_to_progress(job))
        else:
            _cache_progress(
                novel_id,
                _build_progress_payload(0, 0, OrganizeJobStatus.ERROR.value, message, last_error=message),
            )
        logger.exception("[StructureAPI] unexpected error novel_id=%s", novel_id)
        raise HTTPException(
            status_code=500,
            detail=_error_detail("STRUCTURE_INTERNAL_ERROR", message, "Story organize failed. Please try again later."),
        )


@router.get("/organize/progress/{novel_id}")
async def get_organize_progress(
    novel_id: str,
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
):
    cached = PROGRESS_CACHE.get(novel_id)
    if cached:
        return cached
    job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
    progress = _job_to_progress(job)
    if job:
        PROGRESS_CACHE[novel_id] = progress
    return progress
