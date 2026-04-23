"""
Projects v2 路由。

说明：
- 按 DDD + Workflow 方式组织导入、整理、分支、计划、写作、记忆刷新闭环。
- 该路由与旧路由并行，路径前缀仍为 /api/projects，新增子路径不与旧接口冲突。
"""

from __future__ import annotations

import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import File, Form, UploadFile

from application.dto.request_dto import ContinuationContextRequest
from application.dto.request_dto import (
    BranchesRequest,
    ChapterPlanRequest,
    ExtractStyleRequirementsRequest,
    ImportProjectRequest,
    OrganizeRequest,
    RefreshMemoryRequest,
    StyleRequirementsRequest,
    WriteCommitRequest,
    WritePreviewRequest,
    WriteRequest,
)
from application.dto.response_dto import (
    ChapterTaskResponse,
    ChapterPlanEnvelope,
    ContinuationContextResponse,
    ProjectMemoryEnvelope,
    ProjectMemoryViewEnvelope,
    StyleRequirementsEnvelope,
    WriteBatchResultResponse,
    WritePreviewResponse,
    WriteResultResponse,
)
from application.services.v2_workflow_service import V2WorkflowService
from presentation.api.dependencies import (
    get_v2_workflow_service,
    get_project_service,
    get_plot_arc_service,
    get_chapter_arc_binding_repo,
    get_arc_progress_snapshot_repo,
)
from domain.types import NovelId
from application.services.plot_arc_service import PlotArcService
from domain.repositories.chapter_arc_binding_repository import IChapterArcBindingRepository
from domain.repositories.arc_progress_snapshot_repository import IArcProgressSnapshotRepository


router = APIRouter(prefix="/api/projects", tags=["projects-v2"])


def _snapshot_to_dict(item):
    created = getattr(item, "created_at", None)
    if hasattr(created, "isoformat"):
        created_value = created.isoformat()
    else:
        created_value = str(created or "")
    return {
        "snapshot_id": str(getattr(item, "snapshot_id", "") or ""),
        "arc_id": str(getattr(item, "arc_id", "") or ""),
        "chapter_id": str(getattr(item, "chapter_id", "") or ""),
        "chapter_number": int(getattr(item, "chapter_number", 0) or 0),
        "stage_before": str(getattr(item, "stage_before", "") or ""),
        "stage_after": str(getattr(item, "stage_after", "") or ""),
        "progress_summary": str(getattr(item, "progress_summary", "") or ""),
        "change_reason": str(getattr(item, "change_reason", "") or ""),
        "new_conflicts": list(getattr(item, "new_conflicts", []) or []),
        "new_payoffs": list(getattr(item, "new_payoffs", []) or []),
        "created_at": created_value,
    }


@router.post("/import")
async def import_project(
    request: ImportProjectRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.import_project(
            project_name=request.project_name,
            author=request.author,
            genre=request.genre,
            target_word_count=request.target_word_count,
            novel_file_path=request.novel_file_path,
            import_mode=request.import_mode,
            chapter_items=request.chapter_items,
            outline_file_path=request.outline_file_path,
            auto_organize=request.auto_organize,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import/upload")
async def import_project_upload(
    project_name: str = Form(...),
    author: str = Form(""),
    genre: str = Form(""),
    target_word_count: int = Form(8000000),
    import_mode: str = Form("full"),
    novel_file: UploadFile = File(...),
    outline_file: UploadFile | None = File(default=None),
    auto_organize: bool = Form(True),
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    temp_dir = tempfile.mkdtemp(prefix="inktrace_v2_upload_")
    novel_path = os.path.join(temp_dir, novel_file.filename or "novel.txt")
    outline_path = ""
    try:
        with open(novel_path, "wb") as f:
            f.write(await novel_file.read())
        if outline_file is not None:
            outline_path = os.path.join(temp_dir, outline_file.filename or "outline.txt")
            with open(outline_path, "wb") as f:
                f.write(await outline_file.read())
        return await service.import_project(
            project_name=project_name,
            author=author,
            genre=genre,
            target_word_count=target_word_count,
            novel_file_path=novel_path,
            import_mode=import_mode,
            outline_file_path=outline_path,
            auto_organize=auto_organize,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/by-novel/{novel_id}")
def get_project_by_novel(
    novel_id: str,
    project_service=Depends(get_project_service),
):
    project = project_service.get_project_by_novel(NovelId(novel_id)) or project_service.ensure_project_for_novel(NovelId(novel_id))
    return {
        "id": str(project.id),
        "name": project.name,
        "novel_id": str(project.novel_id),
        "genre": project.config.genre.value,
        "status": project.status.value,
    }


@router.post("/{project_id}/organize")
async def organize_project(
    project_id: str,
    request: OrganizeRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        capacity_plan = {}
        if request.batch_size_chapters is not None:
            capacity_plan["batch_size_chapters"] = int(request.batch_size_chapters)
        return await service.organize_project(
            project_id,
            request.mode,
            request.rebuild_memory,
            capacity_plan=capacity_plan or None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/memory", response_model=ProjectMemoryEnvelope)
def get_memory(
    project_id: str,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    return {"project_id": project_id, "memory": service.get_memory(project_id)}


@router.get("/{project_id}/memory-view", response_model=ProjectMemoryViewEnvelope)
def get_memory_view(
    project_id: str,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    return {"project_id": project_id, "memory_view": service.get_memory_view(project_id)}


@router.get("/{project_id}/continuation-context", response_model=ContinuationContextResponse)
def get_continuation_context(
    project_id: str,
    chapter_id: str = "",
    chapter_number: int = 0,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    context = service.build_continuation_context(project_id, chapter_id, chapter_number)
    return {
        "project_id": context.project_id,
        "chapter_id": context.chapter_id,
        "chapter_number": context.chapter_number,
        "recent_chapter_memories": context.recent_chapter_memories,
        "last_chapter_tail": context.last_chapter_tail,
        "relevant_characters": context.relevant_characters,
        "relevant_foreshadowing": context.relevant_foreshadowing,
        "global_constraints": context.global_constraints,
        "chapter_outline": context.chapter_outline,
        "chapter_task_seed": context.chapter_task_seed,
        "active_arcs": context.active_arcs,
        "target_arc": context.target_arc,
        "recent_arc_progress": context.recent_arc_progress,
        "arc_bindings": context.arc_bindings,
        "style_requirements": context.style_requirements,
        "created_at": context.created_at.isoformat(),
    }


@router.post("/{project_id}/continuation-context/build", response_model=ContinuationContextResponse)
def build_continuation_context(
    project_id: str,
    request: ContinuationContextRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    context = service.build_continuation_context(project_id, request.chapter_id, 0)
    return {
        "project_id": context.project_id,
        "chapter_id": context.chapter_id,
        "chapter_number": context.chapter_number,
        "recent_chapter_memories": context.recent_chapter_memories,
        "last_chapter_tail": context.last_chapter_tail,
        "relevant_characters": context.relevant_characters,
        "relevant_foreshadowing": context.relevant_foreshadowing,
        "global_constraints": context.global_constraints,
        "chapter_outline": context.chapter_outline,
        "chapter_task_seed": context.chapter_task_seed,
        "active_arcs": context.active_arcs,
        "target_arc": context.target_arc,
        "recent_arc_progress": context.recent_arc_progress,
        "arc_bindings": context.arc_bindings,
        "style_requirements": context.style_requirements,
        "created_at": context.created_at.isoformat(),
    }


@router.get("/{project_id}/chapter-tasks", response_model=list[ChapterTaskResponse])
def get_chapter_tasks(
    project_id: str,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    return service.list_chapter_tasks(project_id)


@router.get("/{project_id}/style-requirements", response_model=StyleRequirementsEnvelope)
def get_style_requirements(
    project_id: str,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return service.get_style_requirements(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{project_id}/style-requirements", response_model=StyleRequirementsEnvelope)
def update_style_requirements(
    project_id: str,
    request: StyleRequirementsRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return service.update_style_requirements(project_id, request.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/style-requirements/extract", response_model=StyleRequirementsEnvelope)
def extract_style_requirements(
    project_id: str,
    request: ExtractStyleRequirementsRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return service.extract_style_requirements_from_samples(project_id, request.sample_chapter_count)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/workflow-jobs")
def get_workflow_jobs(
    project_id: str,
    limit: int = Query(default=30, ge=1, le=200),
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    return {"project_id": project_id, "workflow_jobs": service.list_workflow_jobs(project_id, limit)}


@router.get("/{project_id}/writing-sessions")
def get_writing_sessions(
    project_id: str,
    limit: int = Query(default=30, ge=1, le=200),
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    return {"project_id": project_id, "writing_sessions": service.list_writing_sessions(project_id, limit)}


@router.get("/{project_id}/trace")
def get_project_trace(
    project_id: str,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    return service.get_project_trace(project_id)


@router.post("/{project_id}/branches")
async def generate_branches(
    project_id: str,
    request: BranchesRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.generate_branches(project_id, request.direction_hint, request.branch_count)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/branches")
def list_branches(
    project_id: str,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return {"branches": service.v2_repo.list_branches(project_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/plot-arcs")
def list_plot_arcs(
    project_id: str,
    service: PlotArcService = Depends(get_plot_arc_service),
    snapshot_repo: IArcProgressSnapshotRepository = Depends(get_arc_progress_snapshot_repo),
):
    try:
        arcs = service.list_arcs(project_id)
        return {
            "project_id": project_id,
            "plot_arcs": [
                {
                    "arc_id": arc.arc_id,
                    "title": arc.title,
                    "arc_type": arc.arc_type,
                    "priority": arc.priority,
                    "status": arc.status,
                    "current_stage": arc.current_stage,
                    "latest_progress_summary": arc.latest_progress_summary,
                    "next_push_suggestion": arc.next_push_suggestion,
                    "covered_chapter_count": len(arc.covered_chapter_ids or []),
                    "latest_snapshot": _snapshot_to_dict((snapshot_repo.list_by_arc(arc.arc_id) or [None])[0]) if (snapshot_repo.list_by_arc(arc.arc_id) or []) else {},
                }
                for arc in arcs
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/plot-arcs/active")
def list_active_plot_arcs(
    project_id: str,
    service: PlotArcService = Depends(get_plot_arc_service),
    snapshot_repo: IArcProgressSnapshotRepository = Depends(get_arc_progress_snapshot_repo),
):
    try:
        arcs = service.list_active_arcs(project_id)
        return {
            "project_id": project_id,
            "plot_arcs": [
                {
                    "arc_id": arc.arc_id,
                    "title": arc.title,
                    "arc_type": arc.arc_type,
                    "priority": arc.priority,
                    "status": arc.status,
                    "current_stage": arc.current_stage,
                    "latest_progress_summary": arc.latest_progress_summary,
                    "next_push_suggestion": arc.next_push_suggestion,
                    "covered_chapter_count": len(arc.covered_chapter_ids or []),
                    "latest_snapshot": _snapshot_to_dict((snapshot_repo.list_by_arc(arc.arc_id) or [None])[0]) if (snapshot_repo.list_by_arc(arc.arc_id) or []) else {},
                }
                for arc in arcs
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chapters/{chapter_id}/arcs")
def list_chapter_arcs(
    chapter_id: str,
    binding_repo: IChapterArcBindingRepository = Depends(get_chapter_arc_binding_repo),
    snapshot_repo: IArcProgressSnapshotRepository = Depends(get_arc_progress_snapshot_repo),
    plot_arc_service: PlotArcService = Depends(get_plot_arc_service),
):
    try:
        bindings = binding_repo.list_by_chapter(chapter_id)
        arc_type_map = {}
        if bindings:
            first_project_id = str(bindings[0].project_id or "")
            if first_project_id:
                arc_type_map = {arc.arc_id: arc.arc_type for arc in (plot_arc_service.list_arcs(first_project_id) or [])}
        return {
            "chapter_id": chapter_id,
            "bindings": [
                {
                    "binding_id": item.binding_id,
                    "project_id": item.project_id,
                    "arc_id": item.arc_id,
                    "arc_type": arc_type_map.get(item.arc_id, ""),
                    "binding_role": item.binding_role,
                    "push_type": item.push_type,
                    "confidence": item.confidence,
                    "latest_snapshot": _snapshot_to_dict((snapshot_repo.list_by_arc(item.arc_id) or [None])[0]) if (snapshot_repo.list_by_arc(item.arc_id) or []) else {},
                }
                for item in bindings
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/chapter-plan", response_model=ChapterPlanEnvelope)
async def create_plan(
    project_id: str,
    request: ChapterPlanRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.create_chapter_plan(
            project_id,
            request.branch_id,
            request.chapter_count,
            request.target_words_per_chapter,
            request.planning_mode,
            request.target_arc_id,
            request.allow_deep_planning,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/write", response_model=WriteResultResponse)
async def write_by_plan(
    project_id: str,
    request: WriteRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.execute_writing(project_id, request.plan_ids, request.auto_commit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/write/preview", response_model=WritePreviewResponse)
async def write_preview(
    project_id: str,
    request: WritePreviewRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.execute_write_preview(
            project_id,
            request.plan_id,
            request.target_word_count,
            request.style_requirements,
            request.planning_mode,
            request.target_arc_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/write/commit", response_model=WriteBatchResultResponse)
async def write_commit(
    project_id: str,
    request: WriteCommitRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.execute_write_commit(
            project_id,
            request.plan_ids,
            request.chapter_count,
            request.auto_commit,
            request.planning_mode,
            request.target_arc_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/refresh-memory", response_model=ProjectMemoryViewEnvelope)
async def refresh_memory(
    project_id: str,
    request: RefreshMemoryRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.refresh_memory(project_id, request.from_chapter_number, request.to_chapter_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
