from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import StoryStateSnapshot


class StoryStateRepository(ABC):
    @abstractmethod
    def save_analysis_baseline(self, story_state: StoryStateSnapshot) -> StoryStateSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_latest_analysis_baseline_by_work(self, work_id: str) -> StoryStateSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    def mark_story_state_stale(self, story_state_id: str, stale_reason: str) -> StoryStateSnapshot | None:
        raise NotImplementedError
