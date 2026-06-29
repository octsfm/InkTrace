from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AutoQueueRun


class AutoQueueRunRepository(ABC):
    @abstractmethod
    def save(self, run: AutoQueueRun) -> AutoQueueRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, run_id: str) -> AutoQueueRun | None:
        raise NotImplementedError

    @abstractmethod
    def get_active(self, work_id: str) -> AutoQueueRun | None:
        raise NotImplementedError

    @abstractmethod
    def get_history(self, work_id: str, limit: int = 20) -> list[AutoQueueRun]:
        raise NotImplementedError

    @abstractmethod
    def update(self, run: AutoQueueRun) -> AutoQueueRun:
        raise NotImplementedError
