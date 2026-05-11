from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import ContextPackSnapshot


class ContextPackRepository(ABC):
    @abstractmethod
    def save(self, snapshot: ContextPackSnapshot) -> ContextPackSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get(self, context_pack_id: str) -> ContextPackSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_latest_by_work(self, work_id: str, chapter_id: str = "") -> ContextPackSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_work(self, work_id: str) -> list[ContextPackSnapshot]:
        raise NotImplementedError
