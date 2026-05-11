from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import StoryMemorySnapshot


class StoryMemoryRepository(ABC):
    @abstractmethod
    def save_snapshot(self, snapshot: StoryMemorySnapshot) -> StoryMemorySnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_latest_snapshot_by_work(self, work_id: str) -> StoryMemorySnapshot | None:
        raise NotImplementedError

    @abstractmethod
    def mark_snapshot_stale(self, snapshot_id: str, stale_reason: str) -> StoryMemorySnapshot | None:
        raise NotImplementedError
