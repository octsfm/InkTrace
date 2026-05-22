from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import CandidateDraft, CandidateDraftVersion, RewriteInstruction, RewriteRequest, RevisionRound


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

    @abstractmethod
    def save_version(self, version: CandidateDraftVersion) -> CandidateDraftVersion:
        raise NotImplementedError

    @abstractmethod
    def get_version(self, candidate_version_id: str) -> CandidateDraftVersion:
        raise NotImplementedError

    @abstractmethod
    def list_versions(self, candidate_draft_id: str) -> list[CandidateDraftVersion]:
        raise NotImplementedError

    @abstractmethod
    def save_rewrite_request(self, request: RewriteRequest) -> RewriteRequest:
        raise NotImplementedError

    @abstractmethod
    def get_rewrite_request(self, rewrite_request_id: str) -> RewriteRequest:
        raise NotImplementedError

    @abstractmethod
    def list_rewrite_requests(self, candidate_draft_id: str) -> list[RewriteRequest]:
        raise NotImplementedError

    @abstractmethod
    def save_rewrite_instruction(self, instruction: RewriteInstruction) -> RewriteInstruction:
        raise NotImplementedError

    @abstractmethod
    def list_rewrite_instructions(self, rewrite_request_id: str) -> list[RewriteInstruction]:
        raise NotImplementedError

    @abstractmethod
    def save_revision_round(self, revision_round: RevisionRound) -> RevisionRound:
        raise NotImplementedError

    @abstractmethod
    def get_revision_round(self, revision_round_id: str) -> RevisionRound:
        raise NotImplementedError

    @abstractmethod
    def list_revision_rounds(self, candidate_draft_id: str) -> list[RevisionRound]:
        raise NotImplementedError
