"""
DDD重构版仓储接口定义。

说明：
- 仅声明领域接口，不依赖具体数据库实现。
- Application/Workflow 层通过这些接口完成用例编排。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from backend.src.domain.shared.types.models import (
    Chapter,
    ChapterPlan,
    LLMConfig,
    MemoryView,
    Novel,
    Outline,
    Project,
    ProjectMemory,
    StoryBranch,
    WorkflowJob,
    WritingSession,
)


class ProjectRepository(ABC):
    @abstractmethod
    def save(self, project: Project) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, project_id: str) -> Optional[Project]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[Project]:
        raise NotImplementedError


class NovelRepository(ABC):
    @abstractmethod
    def save(self, novel: Novel) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, novel_id: str) -> Optional[Novel]:
        raise NotImplementedError


class ChapterRepository(ABC):
    @abstractmethod
    def save(self, chapter: Chapter) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_novel(self, novel_id: str) -> List[Chapter]:
        raise NotImplementedError


class OutlineRepository(ABC):
    @abstractmethod
    def save(self, outline: Outline) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_project(self, project_id: str) -> Optional[Outline]:
        raise NotImplementedError


class ProjectMemoryRepository(ABC):
    @abstractmethod
    def save(self, memory: ProjectMemory) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_active_by_project(self, project_id: str) -> Optional[ProjectMemory]:
        raise NotImplementedError


class MemoryViewRepository(ABC):
    @abstractmethod
    def save(self, view: MemoryView) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_project(self, project_id: str) -> Optional[MemoryView]:
        raise NotImplementedError


class StoryBranchRepository(ABC):
    @abstractmethod
    def save_many(self, branches: List[StoryBranch]) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_project(self, project_id: str) -> List[StoryBranch]:
        raise NotImplementedError


class ChapterPlanRepository(ABC):
    @abstractmethod
    def save_many(self, plans: List[ChapterPlan]) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_ids(self, plan_ids: List[str]) -> List[ChapterPlan]:
        raise NotImplementedError


class WritingSessionRepository(ABC):
    @abstractmethod
    def save(self, session: WritingSession) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, session_id: str) -> Optional[WritingSession]:
        raise NotImplementedError


class LLMConfigRepository(ABC):
    @abstractmethod
    def save(self, config: LLMConfig) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_active(self, provider: str) -> Optional[LLMConfig]:
        raise NotImplementedError


class WorkflowJobRepository(ABC):
    @abstractmethod
    def save(self, job: WorkflowJob) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, job_id: str) -> Optional[WorkflowJob]:
        raise NotImplementedError
