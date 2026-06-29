from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import StyleProfile


class StyleProfileRepository(ABC):
    @abstractmethod
    def save(self, profile: StyleProfile) -> StyleProfile:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, profile_id: str) -> StyleProfile | None:
        raise NotImplementedError

    @abstractmethod
    def get_active(self, work_id: str) -> StyleProfile | None:
        raise NotImplementedError

    @abstractmethod
    def get_history(self, work_id: str) -> list[StyleProfile]:
        raise NotImplementedError

    @abstractmethod
    def update(self, profile: StyleProfile) -> StyleProfile:
        raise NotImplementedError

    @abstractmethod
    def delete(self, profile_id: str) -> None:
        raise NotImplementedError
