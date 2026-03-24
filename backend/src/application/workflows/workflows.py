"""
Application Workflow 编排层。

每个 Workflow 只负责编排：
- 校验输入
- 组织调用顺序
- 聚合输出
不放置底层实现细节（如SQL、HTTP调用）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from backend.src.domain.shared.repositories.interfaces import (
    ChapterPlanRepository,
    ChapterRepository,
    MemoryViewRepository,
    NovelRepository,
    OutlineRepository,
    ProjectMemoryRepository,
    ProjectRepository,
    StoryBranchRepository,
    WorkflowJobRepository,
)


@dataclass
class WorkflowContext:
    project_repo: ProjectRepository
    novel_repo: NovelRepository
    chapter_repo: ChapterRepository
    outline_repo: OutlineRepository
    memory_repo: ProjectMemoryRepository
    memory_view_repo: MemoryViewRepository
    branch_repo: StoryBranchRepository
    plan_repo: ChapterPlanRepository
    workflow_job_repo: WorkflowJobRepository


class ImportProjectWorkflow:
    """导入正文与大纲 -> 创建项目上下文。"""

    def __init__(self, ctx: WorkflowContext):
        self.ctx = ctx

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "workflow": "import_project",
            "status": "accepted",
            "input": payload,
        }


class OrganizeNovelWorkflow:
    """章节级整理 -> 构建结构化memory -> 生成memory_view。"""

    def __init__(self, ctx: WorkflowContext):
        self.ctx = ctx

    def execute(self, project_id: str, mode: str, rebuild_memory: bool) -> Dict[str, Any]:
        memory_view = self.ctx.memory_view_repo.find_by_project(project_id)
        return {
            "workflow": "organize_novel",
            "project_id": project_id,
            "mode": mode,
            "rebuild_memory": rebuild_memory,
            "memory_view": memory_view.__dict__ if memory_view else {},
        }


class GenerateBranchesWorkflow:
    """基于project_memory + outline_context + current_state 生成剧情分支。"""

    def __init__(self, ctx: WorkflowContext):
        self.ctx = ctx

    def execute(self, project_id: str, direction_hint: str, branch_count: int) -> Dict[str, Any]:
        branches = self.ctx.branch_repo.find_by_project(project_id)
        return {
            "workflow": "generate_branches",
            "project_id": project_id,
            "direction_hint": direction_hint,
            "branch_count": branch_count,
            "branches": [b.__dict__ for b in branches][:branch_count],
        }


class CreateChapterPlanWorkflow:
    """基于分支生成N章计划。"""

    def __init__(self, ctx: WorkflowContext):
        self.ctx = ctx

    def execute(self, project_id: str, branch_id: str, chapter_count: int, target_words_per_chapter: int) -> Dict[str, Any]:
        return {
            "workflow": "create_chapter_plan",
            "project_id": project_id,
            "branch_id": branch_id,
            "chapter_count": chapter_count,
            "target_words_per_chapter": target_words_per_chapter,
            "plans": [],
        }


class ExecuteWritingWorkflow:
    """按章节计划逐章生成正文并提交。"""

    def __init__(self, ctx: WorkflowContext):
        self.ctx = ctx

    def execute(self, project_id: str, plan_ids: List[str], auto_commit: bool) -> Dict[str, Any]:
        plans = self.ctx.plan_repo.find_by_ids(plan_ids)
        return {
            "workflow": "execute_writing",
            "project_id": project_id,
            "plan_count": len(plans),
            "auto_commit": auto_commit,
            "generated_chapter_ids": [],
        }


class RefreshMemoryWorkflow:
    """新章节生成后增量刷新memory并返回memory_view。"""

    def __init__(self, ctx: WorkflowContext):
        self.ctx = ctx

    def execute(self, project_id: str, from_chapter_number: int, to_chapter_number: int) -> Dict[str, Any]:
        memory_view = self.ctx.memory_view_repo.find_by_project(project_id)
        return {
            "workflow": "refresh_memory",
            "project_id": project_id,
            "from_chapter_number": from_chapter_number,
            "to_chapter_number": to_chapter_number,
            "memory_view": memory_view.__dict__ if memory_view else {},
        }
