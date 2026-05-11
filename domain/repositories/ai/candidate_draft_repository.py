from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import CandidateDraft


class CandidateDraftRepository(ABC):
    @abstractmethod
    def save(self, draft: CandidateDraft) -> CandidateDraft:
        raise NotImplementedError

    @abstractmethod
    def get(self, candidate_draft_id: str) -> CandidateDraft:
        raise NotImplementedError

    @abstractmethod
    def list_by_work(self, work_id: str, chapter_id: str = "") -> list[CandidateDraft]:
        raise NotImplementedError
