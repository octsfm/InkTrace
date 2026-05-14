from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Sequence

from application.services.v1.chapter_service import ChapterService
from domain.entities.ai.models import CandidateDraft, CandidateDraftStatus
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository


class CandidateReviewService:
    def __init__(
        self,
        *,
        candidate_draft_repository: CandidateDraftRepository,
        chapter_service: ChapterService,
        initialization_service=None,
    ) -> None:
        self._candidate_draft_repository = candidate_draft_repository
        self._chapter_service = chapter_service
        self._initialization_service = initialization_service

    def get_candidate_draft(self, candidate_draft_id: str) -> CandidateDraft:
        return self._candidate_draft_repository.get(candidate_draft_id)

    def list_candidate_drafts(self, work_id: str, chapter_id: str | None = None) -> list[CandidateDraft]:
        return self._candidate_draft_repository.list_by_work(work_id, chapter_id=chapter_id or "")

    def accept_candidate(self, candidate_draft_id: str, *, user_id: str = "", user_action: bool = False) -> CandidateDraft:
        self._require_user_action(user_action)
        draft = self.get_candidate_draft(candidate_draft_id)
        if draft.status == CandidateDraftStatus.APPLIED:
            raise ValueError("candidate_already_applied")
        if draft.status == CandidateDraftStatus.REJECTED:
            raise ValueError("candidate_already_rejected")
        if draft.status not in {CandidateDraftStatus.PENDING_REVIEW, CandidateDraftStatus.ACCEPTED}:
            raise ValueError("candidate_status_invalid")
        if draft.status == CandidateDraftStatus.ACCEPTED:
            return draft
        return self._save_with_status(
            draft,
            CandidateDraftStatus.ACCEPTED,
            {
                "review_decision": "accept",
                "reviewed_by": user_id,
                "reviewed_at": self._now(),
            },
        )

    def reject_candidate(
        self,
        candidate_draft_id: str,
        *,
        user_id: str = "",
        reason: str = "",
        user_action: bool = False,
    ) -> CandidateDraft:
        self._require_user_action(user_action)
        draft = self.get_candidate_draft(candidate_draft_id)
        if draft.status == CandidateDraftStatus.APPLIED:
            raise ValueError("candidate_already_applied")
        if draft.status == CandidateDraftStatus.REJECTED:
            return draft
        if draft.status not in {CandidateDraftStatus.PENDING_REVIEW, CandidateDraftStatus.ACCEPTED}:
            raise ValueError("candidate_status_invalid")
        return self._save_with_status(
            draft,
            CandidateDraftStatus.REJECTED,
            {
                "review_decision": "reject",
                "reviewed_by": user_id,
                "reviewed_at": self._now(),
                "reject_reason": str(reason or ""),
            },
        )

    def apply_candidate_to_draft(
        self,
        candidate_draft_id: str,
        *,
        user_id: str = "",
        expected_chapter_version: int | None,
        user_action: bool = False,
        apply_mode: str = "append_to_chapter_end",
        selection_range: Sequence[int] | None = None,
        cursor_position: int | None = None,
        idempotency_key: str = "",
    ) -> dict[str, object]:
        self._require_user_action(user_action)
        if expected_chapter_version is None:
            raise ValueError("expected_chapter_version_required")
        if not str(idempotency_key or "").strip():
            raise ValueError("idempotency_key_missing")
        draft = self.get_candidate_draft(candidate_draft_id)
        existing_idempotency_hash = str(draft.metadata.get("apply_idempotency_key_hash", "") or "")
        new_idempotency_hash = self._hash_idempotency_key(idempotency_key)
        if draft.status == CandidateDraftStatus.REJECTED:
            raise ValueError("candidate_already_rejected")
        if draft.status == CandidateDraftStatus.APPLIED:
            if existing_idempotency_hash and existing_idempotency_hash == new_idempotency_hash:
                return {
                    "candidate_draft_id": draft.candidate_draft_id,
                    "status": draft.status.value,
                    "applied_chapter_id": str(draft.metadata.get("applied_chapter_id", draft.chapter_id)),
                    "chapter_version": int(draft.metadata.get("applied_chapter_version", expected_chapter_version)),
                    "apply_result_ref": draft.metadata.get("apply_result_ref", ""),
                    "stale_marked": True,
                    "duplicate_request": True,
                }
            raise ValueError("candidate_already_applied")
        if draft.status not in {CandidateDraftStatus.PENDING_REVIEW, CandidateDraftStatus.ACCEPTED}:
            raise ValueError("candidate_status_invalid")
        if not str(draft.content or "").strip():
            raise ValueError("candidate_content_empty")

        chapter = self._get_chapter(draft.work_id, draft.chapter_id)
        if chapter.work_id.value != draft.work_id or chapter.id.value != draft.chapter_id:
            raise ValueError("candidate_chapter_mismatch")
        if chapter.version != int(expected_chapter_version):
            raise ValueError("chapter_version_conflict")

        next_content = self._build_applied_content(
            original_content=chapter.content,
            candidate_content=draft.content,
            apply_mode=apply_mode,
            selection_range=selection_range,
            cursor_position=cursor_position,
        )
        try:
            updated_chapter = self._chapter_service.update_chapter(
                draft.chapter_id,
                content=next_content,
                expected_version=int(expected_chapter_version),
                force_override=False,
            )
        except ValueError as exc:
            if str(exc) == "version_conflict":
                raise ValueError("chapter_version_conflict") from exc
            raise

        applied_at = self._now()
        updated_draft = self._save_with_status(
            draft,
            CandidateDraftStatus.APPLIED,
            {
                "review_decision": draft.metadata.get("review_decision", "apply"),
                "applied_by": user_id,
                "applied_at": applied_at,
                "applied_chapter_id": draft.chapter_id,
                "apply_mode": apply_mode,
                "apply_result_ref": f"chapter:{draft.chapter_id}:version:{updated_chapter.version}",
                "applied_chapter_version": updated_chapter.version,
                "apply_idempotency_key_hash": new_idempotency_hash,
            },
        )
        self._mark_stale(draft.work_id)
        return {
            "candidate_draft_id": updated_draft.candidate_draft_id,
            "status": updated_draft.status.value,
            "applied_chapter_id": updated_chapter.id.value,
            "chapter_version": updated_chapter.version,
            "apply_result_ref": updated_draft.metadata.get("apply_result_ref", ""),
            "stale_marked": True,
        }

    def _save_with_status(
        self,
        draft: CandidateDraft,
        status: CandidateDraftStatus,
        metadata_updates: dict[str, object],
    ) -> CandidateDraft:
        metadata = dict(draft.metadata)
        metadata.update(metadata_updates)
        updated = draft.model_copy(update={"status": status, "updated_at": self._now(), "metadata": metadata})
        return self._candidate_draft_repository.save(updated)

    def _get_chapter(self, work_id: str, chapter_id: str):
        chapters = self._chapter_service.list_chapters(work_id)
        for chapter in chapters:
            if chapter.id.value == chapter_id:
                return chapter
        raise ValueError("chapter_not_found")

    def _build_applied_content(
        self,
        *,
        original_content: str,
        candidate_content: str,
        apply_mode: str,
        selection_range: Sequence[int] | None,
        cursor_position: int | None,
    ) -> str:
        original = str(original_content or "")
        candidate = str(candidate_content or "").strip()
        if apply_mode in {"replace_chapter_draft", "whole_chapter_replace"}:
            raise ValueError("apply_mode_not_supported")
        if apply_mode == "append_to_chapter_end":
            if not original.strip():
                return candidate
            return f"{original.rstrip()}\n\n{candidate}"
        if apply_mode == "replace_selection":
            if not selection_range or len(selection_range) != 2:
                raise ValueError("apply_target_missing")
            start, end = int(selection_range[0]), int(selection_range[1])
            if start < 0 or end < start or end > len(original):
                raise ValueError("apply_target_missing")
            return f"{original[:start]}{candidate}{original[end:]}"
        if apply_mode == "insert_at_cursor":
            if cursor_position is None:
                raise ValueError("apply_target_missing")
            position = int(cursor_position)
            if position < 0 or position > len(original):
                raise ValueError("apply_target_missing")
            return f"{original[:position]}{candidate}{original[position:]}"
        raise ValueError("apply_mode_not_supported")

    def _mark_stale(self, work_id: str) -> None:
        if self._initialization_service is None:
            return
        self._initialization_service.mark_stale(work_id, reason="candidate_applied")

    @staticmethod
    def _require_user_action(user_action: bool) -> None:
        if not user_action:
            raise ValueError("user_confirmation_required")

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _hash_idempotency_key(idempotency_key: str) -> str:
        return hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
