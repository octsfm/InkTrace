from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import ConflictDetectionResult, ConflictGuardDecision, ConflictGuardRecord


class ConflictGuardRepository(ABC):
    @abstractmethod
    def save_record(self, record: ConflictGuardRecord) -> ConflictGuardRecord:
        raise NotImplementedError

    @abstractmethod
    def get_record(self, record_id: str) -> ConflictGuardRecord:
        raise NotImplementedError

    @abstractmethod
    def list_records(
        self,
        *,
        work_id: str = "",
        chapter_id: str = "",
        candidate_draft_id: str = "",
        candidate_version_id: str = "",
    ) -> list[ConflictGuardRecord]:
        raise NotImplementedError

    @abstractmethod
    def save_result(self, result: ConflictDetectionResult) -> ConflictDetectionResult:
        raise NotImplementedError

    @abstractmethod
    def get_result(self, result_id: str) -> ConflictDetectionResult:
        raise NotImplementedError

    @abstractmethod
    def save_decision(self, decision: ConflictGuardDecision) -> ConflictGuardDecision:
        raise NotImplementedError
