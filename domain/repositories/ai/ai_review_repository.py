from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AIReviewResult


class AIReviewRepository(ABC):
    @abstractmethod
    def save(self, review: AIReviewResult) -> AIReviewResult:
        raise NotImplementedError

    @abstractmethod
    def get(self, review_id: str) -> AIReviewResult:
        raise NotImplementedError

    @abstractmethod
    def list_reviews(
        self,
        *,
        work_id: str,
        chapter_id: str = "",
        candidate_draft_id: str = "",
    ) -> list[AIReviewResult]:
        raise NotImplementedError
