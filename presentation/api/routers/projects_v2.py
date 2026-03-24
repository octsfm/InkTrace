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
from pydantic import BaseModel, Field

from application.services.v2_workflow_service import V2WorkflowService
from presentation.api.dependencies import get_v2_workflow_service, get_project_service
from domain.types import NovelId


router = APIRouter(prefix="/api/projects", tags=["projects-v2"])


class ImportProjectRequest(BaseModel):
    project_name: str = Field(..., min_length=1)
    genre: str = ""
    novel_file_path: str = Field(..., min_length=1)
    outline_file_path: str = ""
    auto_organize: bool = True


class OrganizeRequest(BaseModel):
    mode: str = "chapter_first"
    rebuild_memory: bool = True


class BranchesRequest(BaseModel):
    direction_hint: str = ""
    branch_count: int = Field(default=4, ge=3, le=5)


class ChapterPlanRequest(BaseModel):
    branch_id: str
    chapter_count: int = Field(default=3, ge=1, le=10)
    target_words_per_chapter: int = Field(default=2500, ge=500, le=10000)


class WriteRequest(BaseModel):
    plan_ids: list[str]
    auto_commit: bool = True


class RefreshMemoryRequest(BaseModel):
    from_chapter_number: int = Field(..., ge=1)
    to_chapter_number: int = Field(..., ge=1)


@router.post("/import")
async def import_project(
    request: ImportProjectRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.import_project(
            project_name=request.project_name,
            genre=request.genre,
            novel_file_path=request.novel_file_path,
            outline_file_path=request.outline_file_path,
            auto_organize=request.auto_organize,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import/upload")
async def import_project_upload(
    project_name: str = Form(...),
    genre: str = Form(""),
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
            genre=genre,
            novel_file_path=novel_path,
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
    project = project_service.get_project_by_novel(NovelId(novel_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
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
        return await service.organize_project(project_id, request.mode, request.rebuild_memory)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/memory")
def get_memory(
    project_id: str,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    return {"project_id": project_id, "memory": service.get_memory(project_id)}


@router.get("/{project_id}/memory-view")
def get_memory_view(
    project_id: str,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    return {"project_id": project_id, "memory_view": service.get_memory_view(project_id)}


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


@router.post("/{project_id}/chapter-plan")
def create_plan(
    project_id: str,
    request: ChapterPlanRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return service.create_chapter_plan(project_id, request.branch_id, request.chapter_count, request.target_words_per_chapter)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/write")
async def write_by_plan(
    project_id: str,
    request: WriteRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.execute_writing(project_id, request.plan_ids, request.auto_commit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/refresh-memory")
async def refresh_memory(
    project_id: str,
    request: RefreshMemoryRequest,
    service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        return await service.refresh_memory(project_id, request.from_chapter_number, request.to_chapter_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
