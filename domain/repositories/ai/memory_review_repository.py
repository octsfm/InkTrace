from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import (
    MemoryReviewGate,
    MemoryRevisionApplyResult,
    MemoryRevisionDecision,
    MemoryUpdateSuggestion,
    StoryMemoryRevision,
    StoryStateRevision,
)


class MemoryReviewRepository(ABC):
    @abstractmethod
    def claim_idempotency_key(self, *, idempotency_key: str, operation_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_suggestion(self, suggestion: MemoryUpdateSuggestion) -> MemoryUpdateSuggestion:
        raise NotImplementedError

    @abstractmethod
    def get_suggestion(self, suggestion_id: str) -> MemoryUpdateSuggestion:
        raise NotImplementedError

    @abstractmethod
    def list_suggestions(self, *, work_id: str, chapter_id: str = "", gate_id: str = "") -> list[MemoryUpdateSuggestion]:
        raise NotImplementedError

    @abstractmethod
    def save_gate(self, gate: MemoryReviewGate) -> MemoryReviewGate:
        raise NotImplementedError

    @abstractmethod
    def get_gate(self, gate_id: str) -> MemoryReviewGate:
        raise NotImplementedError

    @abstractmethod
    def list_gates(self, *, work_id: str, chapter_id: str = "") -> list[MemoryReviewGate]:
        raise NotImplementedError

    @abstractmethod
    def save_story_memory_revision(self, revision: StoryMemoryRevision) -> StoryMemoryRevision:
        raise NotImplementedError

    @abstractmethod
    def save_story_state_revision(self, revision: StoryStateRevision) -> StoryStateRevision:
        raise NotImplementedError

    @abstractmethod
    def get_story_memory_revision(self, revision_id: str) -> StoryMemoryRevision:
        raise NotImplementedError

    @abstractmethod
    def get_story_state_revision(self, revision_id: str) -> StoryStateRevision:
        raise NotImplementedError

    @abstractmethod
    def list_story_memory_revisions(self, *, work_id: str, chapter_id: str = "", source_suggestion_id: str = "") -> list[StoryMemoryRevision]:
        raise NotImplementedError

    @abstractmethod
    def list_story_state_revisions(self, *, work_id: str, chapter_id: str = "", source_suggestion_id: str = "") -> list[StoryStateRevision]:
        raise NotImplementedError

    @abstractmethod
    def save_decision(self, decision: MemoryRevisionDecision) -> MemoryRevisionDecision:
        raise NotImplementedError

    @abstractmethod
    def list_decisions(self, revision_id: str) -> list[MemoryRevisionDecision]:
        raise NotImplementedError

    @abstractmethod
    def save_apply_result(self, result: MemoryRevisionApplyResult) -> MemoryRevisionApplyResult:
        raise NotImplementedError

    @abstractmethod
    def get_apply_result(self, result_id: str) -> MemoryRevisionApplyResult:
        raise NotImplementedError
