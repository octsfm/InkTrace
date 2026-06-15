from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import CitationLink


class CitationLinkRepository(ABC):
    @abstractmethod
    def save(self, citation: CitationLink) -> CitationLink:
        raise NotImplementedError

    @abstractmethod
    def save_batch(self, citations: list[CitationLink]) -> list[CitationLink]:
        raise NotImplementedError

    @abstractmethod
    def get_by_candidate_version(self, candidate_version_id: str) -> list[CitationLink]:
        raise NotImplementedError

    @abstractmethod
    def get_by_candidate_draft(self, candidate_draft_id: str) -> list[CitationLink]:
        raise NotImplementedError

    @abstractmethod
    def get_by_source(self, source_type: str, source_id: str) -> list[CitationLink]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, citation_id: str) -> CitationLink | None:
        raise NotImplementedError

