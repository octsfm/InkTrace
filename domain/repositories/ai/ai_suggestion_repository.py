from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AISuggestion, AISuggestionBatch


class AISuggestionRepository(ABC):
    @abstractmethod
    def save(self, suggestion: AISuggestion) -> AISuggestion:
        raise NotImplementedError

    @abstractmethod
    def get(self, suggestion_id: str) -> AISuggestion:
        raise NotImplementedError

    @abstractmethod
    def list_suggestions(
        self,
        *,
        work_id: str,
        chapter_id: str = "",
        target_ref_id: str = "",
    ) -> list[AISuggestion]:
        raise NotImplementedError

    @abstractmethod
    def save_batch(self, batch: AISuggestionBatch) -> AISuggestionBatch:
        raise NotImplementedError

    @abstractmethod
    def get_batch(self, batch_id: str) -> AISuggestionBatch:
        raise NotImplementedError
