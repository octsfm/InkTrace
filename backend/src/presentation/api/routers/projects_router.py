"""
重构版项目主路由。

路由只负责：
- 参数接收
- 调用workflow
- 输出响应
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.src.application.workflows.workflows import (
    CreateChapterPlanWorkflow,
    ExecuteWritingWorkflow,
    GenerateBranchesWorkflow,
    ImportProjectWorkflow,
    OrganizeNovelWorkflow,
    RefreshMemoryWorkflow,
    WorkflowContext,
)
from backend.src.presentation.api.schemas import (
    CreateChapterPlanRequest,
    ExecuteWritingRequest,
    GenerateBranchesRequest,
    ImportProjectRequest,
    OrganizeProjectRequest,
    RefreshMemoryRequest,
)


router = APIRouter(prefix="/api/projects", tags=["projects-v2"])


def get_workflow_context() -> WorkflowContext:
    """
    依赖注入占位。

    注意：
    - 这里应由具体基础设施实现注入真实仓储。
    - 当前重构稿返回占位对象，由 app.py 中替换为真实实现。
    """
    raise NotImplementedError("请在装配层注入真实WorkflowContext")


@router.post("/import")
def import_project(
    request: ImportProjectRequest,
    ctx: WorkflowContext = Depends(get_workflow_context),
):
    return ImportProjectWorkflow(ctx).execute(request.model_dump())


@router.post("/{project_id}/organize")
def organize_project(
    project_id: str,
    request: OrganizeProjectRequest,
    ctx: WorkflowContext = Depends(get_workflow_context),
):
    return OrganizeNovelWorkflow(ctx).execute(project_id, request.mode, request.rebuild_memory)


@router.get("/{project_id}/memory")
def get_project_memory(
    project_id: str,
    ctx: WorkflowContext = Depends(get_workflow_context),
):
    memory = ctx.memory_repo.find_active_by_project(project_id)
    return {"project_id": project_id, "memory": memory.__dict__ if memory else {}}


@router.get("/{project_id}/memory-view")
def get_project_memory_view(
    project_id: str,
    ctx: WorkflowContext = Depends(get_workflow_context),
):
    view = ctx.memory_view_repo.find_by_project(project_id)
    return {"project_id": project_id, "memory_view": view.__dict__ if view else {}}


@router.post("/{project_id}/branches")
def generate_branches(
    project_id: str,
    request: GenerateBranchesRequest,
    ctx: WorkflowContext = Depends(get_workflow_context),
):
    return GenerateBranchesWorkflow(ctx).execute(project_id, request.direction_hint, request.branch_count)


@router.post("/{project_id}/chapter-plan")
def create_chapter_plan(
    project_id: str,
    request: CreateChapterPlanRequest,
    ctx: WorkflowContext = Depends(get_workflow_context),
):
    return CreateChapterPlanWorkflow(ctx).execute(
        project_id=project_id,
        branch_id=request.branch_id,
        chapter_count=request.chapter_count,
        target_words_per_chapter=request.target_words_per_chapter,
    )


@router.post("/{project_id}/write")
def execute_writing(
    project_id: str,
    request: ExecuteWritingRequest,
    ctx: WorkflowContext = Depends(get_workflow_context),
):
    return ExecuteWritingWorkflow(ctx).execute(project_id, request.plan_ids, request.auto_commit)


@router.post("/{project_id}/refresh-memory")
def refresh_memory(
    project_id: str,
    request: RefreshMemoryRequest,
    ctx: WorkflowContext = Depends(get_workflow_context),
):
    return RefreshMemoryWorkflow(ctx).execute(project_id, request.from_chapter_number, request.to_chapter_number)
