from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import (
    AISuggestion,
    AISuggestionAction,
    AISuggestionActionType,
    AISuggestionBatch,
    AISuggestionDecision,
    AISuggestionDecisionType,
    AISuggestionPriority,
    AISuggestionSeverity,
    AISuggestionSource,
    AISuggestionStatus,
    AISuggestionTarget,
    AISuggestionType,
)
from domain.repositories.ai.ai_review_repository import AIReviewRepository
from domain.repositories.ai.ai_suggestion_repository import AISuggestionRepository
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from application.services.ai.candidate_rewrite_service import CandidateRewriteService


class AISuggestionService:
    def __init__(
        self,
        *,
        ai_suggestion_repository: AISuggestionRepository,
        ai_review_repository: AIReviewRepository,
        candidate_draft_repository: CandidateDraftRepository,
        candidate_rewrite_service: CandidateRewriteService,
    ) -> None:
        self._ai_suggestion_repository = ai_suggestion_repository
        self._ai_review_repository = ai_review_repository
        self._candidate_draft_repository = candidate_draft_repository
        self._candidate_rewrite_service = candidate_rewrite_service

    def generate_from_review(self, review_id: str) -> AISuggestionBatch:
        review = self._ai_review_repository.get(review_id)
        draft = self._candidate_draft_repository.get(review.candidate_draft_id)
        source_version_id = draft.selected_version_id or self._candidate_draft_repository.list_versions(draft.candidate_draft_id)[-1].candidate_version_id
        now = self._now()
        suggestion_ids: list[str] = []

        for issue in list(review.issues or []):
            suggestion = AISuggestion(
                suggestion_id=f"ais_{uuid.uuid4().hex[:10]}",
                work_id=review.work_id,
                chapter_id=review.chapter_id,
                agent_session_id=draft.agent_session_id,
                source=AISuggestionSource(
                    source_type="review_issue",
                    source_ref_id=getattr(issue, "issue_id", ""),
                    source_agent_type="reviewer",
                    source_agent_session_id=draft.agent_session_id,
                    source_version_id=source_version_id,
                ),
                target=AISuggestionTarget(
                    target_type="candidate_draft_version",
                    target_ref_id=source_version_id,
                    target_scope="version",
                    target_snapshot_ref=draft.direction_plan_snapshot_id,
                ),
                suggestion_type=self._map_issue_to_suggestion_type(str(getattr(issue, "category", "") or "")),
                severity=self._map_severity(str(getattr(issue, "severity", "medium") or "medium")),
                priority=AISuggestionPriority.HIGH,
                title=str(getattr(issue, "message", "") or "AI 建议"),
                summary=str(getattr(issue, "suggestion", "") or str(getattr(issue, "message", "") or "")),
                rationale=review.summary,
                proposed_action="转化为 RewriteInstruction",
                status=AISuggestionStatus.GENERATED,
                created_by="reviewer_agent",
                created_at=now,
                updated_at=now,
                request_id=review.review_id,
                action=AISuggestionAction(
                    action_type=AISuggestionActionType.CONVERT_TO_REWRITE_INSTRUCTION,
                    requires_user_action=True,
                    action_status="pending",
                ),
                batch_id="",
                metadata={"review_id": review.review_id},
            )
            self._ai_suggestion_repository.save(suggestion)
            suggestion_ids.append(suggestion.suggestion_id)

        if str(review.risk_level.value) in {"medium", "high"}:
            risk = AISuggestion(
                suggestion_id=f"ais_{uuid.uuid4().hex[:10]}",
                work_id=review.work_id,
                chapter_id=review.chapter_id,
                agent_session_id=draft.agent_session_id,
                source=AISuggestionSource(
                    source_type="review_report",
                    source_ref_id=review.review_id,
                    source_agent_type="reviewer",
                    source_agent_session_id=draft.agent_session_id,
                    source_version_id=source_version_id,
                ),
                target=AISuggestionTarget(
                    target_type="candidate_draft_version",
                    target_ref_id=source_version_id,
                    target_scope="version",
                    target_snapshot_ref=draft.direction_plan_snapshot_id,
                ),
                suggestion_type=AISuggestionType.RISK_WARNING,
                severity=AISuggestionSeverity.HIGH,
                priority=AISuggestionPriority.HIGH,
                title="高风险提示",
                summary=review.summary or "当前版本存在高风险问题。",
                rationale="risk_warning 只允许 acknowledge 或 dismiss，不允许自动执行。",
                proposed_action="人工确认后继续处理",
                status=AISuggestionStatus.GENERATED,
                created_by="reviewer_agent",
                created_at=now,
                updated_at=now,
                request_id=review.review_id,
                action=AISuggestionAction(
                    action_type=AISuggestionActionType.DISMISS_ONLY,
                    requires_user_action=True,
                    action_status="pending",
                ),
                batch_id="",
                metadata={"review_id": review.review_id},
            )
            self._ai_suggestion_repository.save(risk)
            suggestion_ids.append(risk.suggestion_id)

        batch = AISuggestionBatch(
            batch_id=f"aisb_{uuid.uuid4().hex[:10]}",
            work_id=review.work_id,
            chapter_id=review.chapter_id,
            agent_session_id=draft.agent_session_id,
            source_report_id=review.review_id,
            suggestion_ids=suggestion_ids,
            generated_count=len(suggestion_ids),
            stale_count=0,
            created_at=now,
        )
        self._ai_suggestion_repository.save_batch(batch)
        for suggestion_id in suggestion_ids:
            suggestion = self._ai_suggestion_repository.get(suggestion_id)
            self._ai_suggestion_repository.save(suggestion.model_copy(update={"batch_id": batch.batch_id}))
        return batch

    def list_suggestions(self, *, work_id: str, chapter_id: str = "", target_ref_id: str = "") -> list[AISuggestion]:
        items = self._ai_suggestion_repository.list_suggestions(work_id=work_id, chapter_id=chapter_id, target_ref_id=target_ref_id)
        shown: list[AISuggestion] = []
        for item in items:
            if item.status == AISuggestionStatus.GENERATED:
                item = self._ai_suggestion_repository.save(item.model_copy(update={"status": AISuggestionStatus.SHOWN, "updated_at": self._now()}))
            shown.append(item)
        return shown

    def get_suggestion(self, suggestion_id: str) -> AISuggestion:
        item = self._ai_suggestion_repository.get(suggestion_id)
        if item.status == AISuggestionStatus.GENERATED:
            item = self._ai_suggestion_repository.save(item.model_copy(update={"status": AISuggestionStatus.SHOWN, "updated_at": self._now()}))
        return item

    def accept_suggestion(self, suggestion_id: str, *, user_id: str, user_action: bool) -> AISuggestion:
        self._require_user_action(user_action)
        item = self._ai_suggestion_repository.get(suggestion_id)
        return self._save_decision(item, decision=AISuggestionDecisionType.ACCEPTED, status=AISuggestionStatus.ACCEPTED, user_id=user_id)

    def dismiss_suggestion(self, suggestion_id: str, *, user_id: str, user_action: bool, note: str = "") -> AISuggestion:
        self._require_user_action(user_action)
        item = self._ai_suggestion_repository.get(suggestion_id)
        return self._save_decision(
            item,
            decision=AISuggestionDecisionType.DISMISSED,
            status=AISuggestionStatus.DISMISSED,
            user_id=user_id,
            note=note,
        )

    def convert_suggestion(
        self,
        suggestion_id: str,
        *,
        user_id: str,
        user_action: bool,
        idempotency_key: str,
    ) -> AISuggestion:
        self._require_user_action(user_action)
        if not str(idempotency_key or "").strip():
            raise ValueError("idempotency_key_required")
        item = self._ai_suggestion_repository.get(suggestion_id)
        if item.suggestion_type == AISuggestionType.RISK_WARNING:
            raise ValueError("suggestion_convert_forbidden")
        if item.action.action_type == AISuggestionActionType.CONVERT_TO_REWRITE_INSTRUCTION:
            rewrite = self._candidate_rewrite_service.request_rewrite(
                candidate_draft_id=item.metadata.get("candidate_draft_id", "") or self._candidate_draft_id_from_target(item.target.target_ref_id),
                source_version_id=item.target.target_ref_id,
                trigger_type="review_based",
                review_report_id=item.metadata.get("review_id", ""),
                user_instruction=item.summary,
                user_id=user_id,
                user_action=True,
                idempotency_key=idempotency_key,
            )
            action = item.action.model_copy(
                update={
                    "action_payload_ref": f"rewrite_request:{rewrite['rewrite_request_id']}",
                    "action_status": "completed",
                }
            )
        elif item.suggestion_type == AISuggestionType.MEMORY_UPDATE_SUGGESTION_REF:
            action = item.action.model_copy(
                update={"action_payload_ref": f"memory_review_gate:{item.target.target_ref_id}", "action_status": "completed"}
            )
        elif item.suggestion_type == AISuggestionType.CONFLICT_RESOLUTION_SUGGESTION:
            action = item.action.model_copy(
                update={"action_payload_ref": f"conflict_guard:{item.target.target_ref_id}", "action_status": "completed"}
            )
        else:
            action = item.action.model_copy(
                update={"action_payload_ref": f"suggestion_action:{item.target.target_ref_id}", "action_status": "completed"}
            )
        updated = self._save_decision(
            item.model_copy(update={"action": action}),
            decision=AISuggestionDecisionType.CONVERTED,
            status=AISuggestionStatus.CONVERTED,
            user_id=user_id,
        )
        return updated

    @staticmethod
    def _map_issue_to_suggestion_type(category: str) -> AISuggestionType:
        mapping = {
            "style": AISuggestionType.STYLE_SUGGESTION,
            "plot": AISuggestionType.PLOT_SUGGESTION,
            "character": AISuggestionType.CHARACTER_SUGGESTION,
            "foreshadow": AISuggestionType.FORESHADOW_SUGGESTION,
            "continuity": AISuggestionType.REWRITE_SUGGESTION,
        }
        return mapping.get(category, AISuggestionType.REWRITE_SUGGESTION)

    @staticmethod
    def _map_severity(value: str) -> AISuggestionSeverity:
        mapping = {
            "low": AISuggestionSeverity.LOW,
            "medium": AISuggestionSeverity.MEDIUM,
            "high": AISuggestionSeverity.HIGH,
        }
        return mapping.get(value, AISuggestionSeverity.MEDIUM)

    def _save_decision(
        self,
        item: AISuggestion,
        *,
        decision: AISuggestionDecisionType,
        status: AISuggestionStatus,
        user_id: str,
        note: str = "",
    ) -> AISuggestion:
        now = self._now()
        updated = item.model_copy(
            update={
                "decision": decision,
                "status": status,
                "decided_by": user_id,
                "updated_at": now,
                "decision_log": AISuggestionDecision(
                    suggestion_id=item.suggestion_id,
                    decision=decision,
                    decided_by=user_id,
                    decision_note=note,
                    decided_at=now,
                ),
            }
        )
        return self._ai_suggestion_repository.save(updated)

    def _candidate_draft_id_from_target(self, target_ref_id: str) -> str:
        version = self._candidate_draft_repository.get_version(target_ref_id)
        return version.candidate_draft_id

    @staticmethod
    def _require_user_action(user_action: bool) -> None:
        if not user_action:
            raise ValueError("action_not_allowed")

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _hash_idempotency_key(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
