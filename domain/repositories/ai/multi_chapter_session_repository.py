from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import MultiChapterSession


class MultiChapterSessionRepository(ABC):
    @abstractmethod
    def save(self, session: MultiChapterSession) -> MultiChapterSession:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, session_id: str) -> MultiChapterSession | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_work_id(self, work_id: str) -> list[MultiChapterSession]:
        raise NotImplementedError

    @abstractmethod
    def list_active(self, work_id: str) -> list[MultiChapterSession]:
        raise NotImplementedError

