"""
重构版 FastAPI 应用入口（DDD + 清洁架构装配层示例）。

说明：
- 该文件展示“依赖装配”职责。
- 具体持久化实现可替换为 SQLite 仓储。
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Optional

from fastapi import FastAPI

from backend.src.application.workflows.workflows import WorkflowContext
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
from backend.src.domain.shared.types.models import (
    Chapter,
    ChapterPlan,
    MemoryView,
    Novel,
    Outline,
    Project,
    ProjectMemory,
    StoryBranch,
    WorkflowJob,
)
from backend.src.presentation.api.routers.projects_router import (
    get_workflow_context,
    router as projects_router,
)


class _InMemoryProjectRepo(ProjectRepository):
    def __init__(self):
        self.data: Dict[str, Project] = {}

    def save(self, project: Project) -> None:
        self.data[project.id] = project

    def find_by_id(self, project_id: str) -> Optional[Project]:
        return self.data.get(project_id)

    def list_all(self) -> List[Project]:
        return list(self.data.values())


class _InMemoryNovelRepo(NovelRepository):
    def __init__(self):
        self.data: Dict[str, Novel] = {}

    def save(self, novel: Novel) -> None:
        self.data[novel.id] = novel

    def find_by_id(self, novel_id: str) -> Optional[Novel]:
        return self.data.get(novel_id)


class _InMemoryChapterRepo(ChapterRepository):
    def __init__(self):
        self.data: Dict[str, Chapter] = {}

    def save(self, chapter: Chapter) -> None:
        self.data[chapter.id] = chapter

    def find_by_novel(self, novel_id: str) -> List[Chapter]:
        return [v for v in self.data.values() if v.novel_id == novel_id]


class _InMemoryOutlineRepo(OutlineRepository):
    def __init__(self):
        self.data: Dict[str, Outline] = {}

    def save(self, outline: Outline) -> None:
        self.data[outline.id] = outline

    def find_by_project(self, project_id: str) -> Optional[Outline]:
        for value in self.data.values():
            if value.project_id == project_id:
                return value
        return None


class _InMemoryProjectMemoryRepo(ProjectMemoryRepository):
    def __init__(self):
        self.data: Dict[str, ProjectMemory] = {}

    def save(self, memory: ProjectMemory) -> None:
        self.data[memory.project_id] = memory

    def find_active_by_project(self, project_id: str) -> Optional[ProjectMemory]:
        return self.data.get(project_id)


class _InMemoryMemoryViewRepo(MemoryViewRepository):
    def __init__(self):
        self.data: Dict[str, MemoryView] = {}

    def save(self, view: MemoryView) -> None:
        self.data[view.project_id] = view

    def find_by_project(self, project_id: str) -> Optional[MemoryView]:
        return self.data.get(project_id)


class _InMemoryBranchRepo(StoryBranchRepository):
    def __init__(self):
        self.data: Dict[str, List[StoryBranch]] = {}

    def save_many(self, branches: List[StoryBranch]) -> None:
        if not branches:
            return
        self.data.setdefault(branches[0].project_id, [])
        self.data[branches[0].project_id].extend(branches)

    def find_by_project(self, project_id: str) -> List[StoryBranch]:
        return self.data.get(project_id, [])


class _InMemoryPlanRepo(ChapterPlanRepository):
    def __init__(self):
        self.data: Dict[str, ChapterPlan] = {}

    def save_many(self, plans: List[ChapterPlan]) -> None:
        for plan in plans:
            self.data[plan.id] = plan

    def find_by_ids(self, plan_ids: List[str]) -> List[ChapterPlan]:
        return [self.data[x] for x in plan_ids if x in self.data]


class _InMemoryWorkflowJobRepo(WorkflowJobRepository):
    def __init__(self):
        self.data: Dict[str, WorkflowJob] = {}

    def save(self, job: WorkflowJob) -> None:
        self.data[job.id] = job

    def find_by_id(self, job_id: str) -> Optional[WorkflowJob]:
        return self.data.get(job_id)


def _build_context() -> WorkflowContext:
    """集中装配 Workflow 所需依赖。"""
    return WorkflowContext(
        project_repo=_InMemoryProjectRepo(),
        novel_repo=_InMemoryNovelRepo(),
        chapter_repo=_InMemoryChapterRepo(),
        outline_repo=_InMemoryOutlineRepo(),
        memory_repo=_InMemoryProjectMemoryRepo(),
        memory_view_repo=_InMemoryMemoryViewRepo(),
        branch_repo=_InMemoryBranchRepo(),
        plan_repo=_InMemoryPlanRepo(),
        workflow_job_repo=_InMemoryWorkflowJobRepo(),
    )


def create_app() -> FastAPI:
    app = FastAPI(title="InkTrace DDD Refactor API", version="2.0.0")
    ctx = _build_context()
    app.dependency_overrides[get_workflow_context] = lambda: ctx
    app.include_router(projects_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "ddd-refactor"}

    @app.get("/debug/context")
    def debug_context():
        return {"projects": len(ctx.project_repo.list_all())}

    return app


app = create_app()
