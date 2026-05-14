from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    AIReviewRequest,
    AIReviewResult,
    AIReviewRiskLevel,
    AIReviewStatus,
    AIReviewTargetType,
    ReviewIssue,
)
from domain.repositories.ai.ai_review_repository import AIReviewRepository
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from domain.repositories.ai.initialization_repository import InitializationRepository
from domain.repositories.ai.story_memory_repository import StoryMemoryRepository
from domain.repositories.ai.story_state_repository import StoryStateRepository
from domain.services.ai.reviewer import ReviewerPort


class AIReviewApplicationService:
    def __init__(
        self,
        *,
        work_service: WorkService,
        chapter_service: ChapterService,
        candidate_draft_repository: CandidateDraftRepository,
        ai_review_repository: AIReviewRepository,
        reviewer: ReviewerPort,
        initialization_repository: InitializationRepository | None = None,
        story_memory_repository: StoryMemoryRepository | None = None,
        story_state_repository: StoryStateRepository | None = None,
    ) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._candidate_draft_repository = candidate_draft_repository
        self._ai_review_repository = ai_review_repository
        self._reviewer = reviewer
        self._initialization_repository = initialization_repository
        self._story_memory_repository = story_memory_repository
        self._story_state_repository = story_state_repository

    def review_candidate_draft(
        self,
        candidate_draft_id: str,
        *,
        created_by: str | None = None,
        user_instruction: str | None = None,
        review_scope: str = "basic_quality+apply_risk",
        allow_degraded: bool = True,
        idempotency_key: str = "",
    ) -> AIReviewResult:
        draft = self._candidate_draft_repository.get(candidate_draft_id)
        chapter = self._get_chapter(draft.work_id, draft.chapter_id)
        self._work_service.get_work(draft.work_id)
        existing = self._find_existing_review(
            candidate_draft_id=candidate_draft_id,
            review_scope=review_scope,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return existing

        created_by = created_by or "user_action"
        if created_by != "user_action":
            raise ValueError("caller_type_not_allowed")

        warnings = self._collect_review_warnings(draft)
        status = AIReviewStatus.COMPLETED_WITH_WARNINGS if warnings else AIReviewStatus.COMPLETED
        request = AIReviewRequest(
            review_id=f"rv_{uuid.uuid4().hex[:12]}",
            work_id=draft.work_id,
            chapter_id=draft.chapter_id,
            candidate_draft_id=draft.candidate_draft_id,
            review_target_type=AIReviewTargetType.CANDIDATE_DRAFT,
            review_target_ref=f"candidate_draft:{draft.candidate_draft_id}",
            review_mode="candidate_draft_review",
            review_scope=review_scope,
            allow_degraded=allow_degraded,
            idempotency_key=idempotency_key,
            created_by=created_by,
            user_instruction=str(user_instruction or "").strip(),
        )
        review_context = self.build_review_context(
            candidate_draft_id,
            review_mode=request.review_mode,
            user_instruction=request.user_instruction,
        )
        try:
            raw_output = self._reviewer.review(
                review_context=review_context,
                review_mode=request.review_mode,
                user_instruction=request.user_instruction,
            )
            validated = self.validate_review_output(raw_output)
            result = AIReviewResult(
                review_id=request.review_id,
                work_id=draft.work_id,
                chapter_id=draft.chapter_id,
                candidate_draft_id=draft.candidate_draft_id,
                status=status,
                summary=str(validated.get("summary", "")),
                warnings=warnings,
                issues=[ReviewIssue.model_validate(item) for item in validated.get("issues", [])],
                suggestions=[str(item) for item in validated.get("suggestions", [])],
                risk_level=AIReviewRiskLevel(str(validated.get("risk_level", "low"))),
                consistency_notes=[str(item) for item in validated.get("consistency_notes", [])],
                style_notes=[str(item) for item in validated.get("style_notes", [])],
                logic_notes=[str(item) for item in validated.get("logic_notes", [])],
                reviewer_model_role=str(validated.get("reviewer_model_role", "reviewer")),
                provider_name=str(validated.get("provider_name", "")),
                model_name=str(validated.get("model_name", "")),
                created_at=self._now(),
                metadata={
                    "review_mode": request.review_mode,
                    "review_scope": request.review_scope,
                    "review_target_type": request.review_target_type.value,
                    "review_target_ref": request.review_target_ref,
                    "chapter_title": chapter.title,
                    "warnings": warnings,
                    "idempotency_key_hash": self._hash_idempotency_key(idempotency_key),
                },
            )
        except Exception as exc:
            result = AIReviewResult(
                review_id=request.review_id,
                work_id=draft.work_id,
                chapter_id=draft.chapter_id,
                candidate_draft_id=draft.candidate_draft_id,
                status=AIReviewStatus.FAILED,
                summary="AIReview unavailable",
                issues=[],
                suggestions=[],
                risk_level=AIReviewRiskLevel.LOW,
                consistency_notes=[],
                style_notes=[],
                logic_notes=[],
                reviewer_model_role="reviewer",
                provider_name="fake",
                model_name="fake-reviewer",
                created_at=self._now(),
                metadata={
                    "review_mode": request.review_mode,
                    "review_scope": request.review_scope,
                    "review_error_code": exc.__class__.__name__,
                    "idempotency_key_hash": self._hash_idempotency_key(idempotency_key),
                },
            )
        return self._ai_review_repository.save(result)

    def get_ai_review(self, review_id: str) -> AIReviewResult:
        return self._ai_review_repository.get(review_id)

    def list_ai_reviews(
        self,
        *,
        work_id: str,
        chapter_id: str | None = None,
        candidate_draft_id: str | None = None,
    ) -> list[AIReviewResult]:
        return self._ai_review_repository.list_reviews(
            work_id=work_id,
            chapter_id=chapter_id or "",
            candidate_draft_id=candidate_draft_id or "",
        )

    def build_review_context(self, candidate_draft_id: str, *, review_mode: str, user_instruction: str) -> dict[str, object]:
        draft = self._candidate_draft_repository.get(candidate_draft_id)
        chapter = self._get_chapter(draft.work_id, draft.chapter_id)
        story_memory = self._story_memory_repository.get_latest_snapshot_by_work(draft.work_id) if self._story_memory_repository else None
        story_state = self._story_state_repository.get_latest_analysis_baseline_by_work(draft.work_id) if self._story_state_repository else None
        return {
            "work_id": draft.work_id,
            "chapter_id": draft.chapter_id,
            "chapter_title": chapter.title,
            "candidate_draft_id": draft.candidate_draft_id,
            "candidate_draft_content": str(draft.content or "")[:500],
            "candidate_draft_preview": draft.content_preview,
            "source_context_pack_id": draft.source_context_pack_id,
            "story_memory_summary": story_memory.global_summary[:200] if story_memory else "",
            "story_state_summary": story_state.current_position_summary[:200] if story_state else "",
            "review_mode": review_mode,
            "user_instruction": str(user_instruction or "")[:200],
        }

    def validate_review_output(self, raw_output: dict[str, object]) -> dict[str, object]:
        if not isinstance(raw_output, dict):
            raise ValueError("review_output_invalid")
        summary = str(raw_output.get("summary", "")).strip()
        issues = raw_output.get("issues", [])
        if not summary:
            raise ValueError("review_output_invalid")
        if not isinstance(issues, list):
            raise ValueError("review_output_invalid")
        return raw_output

    def _find_existing_review(self, *, candidate_draft_id: str, review_scope: str, idempotency_key: str) -> AIReviewResult | None:
        if not idempotency_key:
            return None
        idempotency_hash = self._hash_idempotency_key(idempotency_key)
        items = self._ai_review_repository.list_reviews(work_id=self._candidate_draft_repository.get(candidate_draft_id).work_id)
        for item in items:
            if item.candidate_draft_id != candidate_draft_id:
                continue
            if item.metadata.get("idempotency_key_hash") != idempotency_hash:
                continue
            if item.metadata.get("review_scope", "basic_quality+apply_risk") != review_scope:
                raise ValueError("review_idempotency_conflict")
            return item
        return None

    @staticmethod
    def _collect_review_warnings(draft) -> list[str]:  # noqa: ANN001
        warnings: list[str] = []
        context_pack_status = str(draft.metadata.get("context_pack_status", "") or "")
        if context_pack_status == "degraded":
            warnings.append("degraded_candidate_warning")
        if str(draft.metadata.get("stale", "") or "").lower() in {"1", "true", "yes", "stale"}:
            warnings.append("stale_candidate_warning")
        return warnings

    @staticmethod
    def _hash_idempotency_key(idempotency_key: str) -> str:
        if not idempotency_key:
            return ""
        return hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()

    def _get_chapter(self, work_id: str, chapter_id: str):
        chapters = self._chapter_service.list_chapters(work_id)
        for chapter in chapters:
            if chapter.id.value == chapter_id:
                return chapter
        raise ValueError("chapter_not_found")

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
