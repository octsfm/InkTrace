from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import ChapterPlan


class ChapterPlanRepository(ABC):
    @abstractmethod
    def save(self, plan: ChapterPlan) -> ChapterPlan:
        raise NotImplementedError

    @abstractmethod
    def get(self, chapter_plan_id: str) -> ChapterPlan:
        raise NotImplementedError

    @abstractmethod
    def list_by_work(self, work_id: str, chapter_id: str = "") -> list[ChapterPlan]:
        raise NotImplementedError
