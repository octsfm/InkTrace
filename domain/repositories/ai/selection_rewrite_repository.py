from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import SelectionRewriteCandidate


class SelectionRewriteRepository(ABC):
    @abstractmethod
    def save(self, candidate: SelectionRewriteCandidate) -> SelectionRewriteCandidate:
        raise NotImplementedError

    @abstractmethod
    def get(self, rewrite_id: str) -> SelectionRewriteCandidate | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_chapter(self, chapter_id: str) -> list[SelectionRewriteCandidate]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_chapter(self, chapter_id: str) -> int:
        raise NotImplementedError
