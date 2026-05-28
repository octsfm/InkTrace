from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import (
    MemoryApplyStatus,
    MemoryGateState,
    MemoryReviewGate,
    MemoryReviewDecisionType,
    MemoryRevisionApplyResult,
    MemoryRevisionDecision,
    MemoryRevisionRecordType,
    MemoryRevisionSource,
    MemoryRevisionStatus,
    MemorySuggestionDecisionType,
    MemorySuggestionSeverity,
    MemorySuggestionStatus,
    MemoryTargetType,
    MemoryUpdateCandidate,
    MemoryUpdateSuggestion,
    MemoryUpdateType,
    StoryMemoryRevision,
    StoryMemoryRevisionItem,
    StoryMemorySnapshot,
    StoryStateRevision,
    StoryStateSnapshot,
)
from domain.repositories.ai.ai_review_repository import AIReviewRepository
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from domain.repositories.ai.memory_review_repository import MemoryReviewRepository
from domain.repositories.ai.story_memory_repository import StoryMemoryRepository
from domain.repositories.ai.story_state_repository import StoryStateRepository


class MemoryReviewGateService:
    def __init__(
        self,
        *,
        memory_review_repository: MemoryReviewRepository,
        story_memory_repository: StoryMemoryRepository,
        story_state_repository: StoryStateRepository,
        ai_review_repository: AIReviewRepository,
        candidate_draft_repository: CandidateDraftRepository,
        conflict_guard_service=None,
        trace_service=None,
    ) -> None:
        self._memory_review_repository = memory_review_repository
        self._story_memory_repository = story_memory_repository
        self._story_state_repository = story_state_repository
        self._ai_review_repository = ai_review_repository
        self._candidate_draft_repository = candidate_draft_repository
        self._conflict_guard_service = conflict_guard_service
        self._trace_service = trace_service

    def generate_from_review(self, review_id: str):
        review = self._ai_review_repository.get(review_id)
        draft = self._candidate_draft_repository.get(review.candidate_draft_id)
        latest_memory = self._story_memory_repository.get_latest_snapshot_by_work(review.work_id)
        latest_state = self._story_state_repository.get_latest_analysis_baseline_by_work(review.work_id)
        now = self._now()
        suggestion_ids: list[str] = []

        for issue in list(review.issues or []):
            if str(getattr(issue, "category", "") or "") != "continuity":
                continue
            suggestion = self._build_story_state_suggestion(
                review_id=review.review_id,
                work_id=review.work_id,
                chapter_id=review.chapter_id,
                draft=draft,
                latest_state=latest_state,
                latest_memory=latest_memory,
                proposed_summary=str(getattr(issue, "suggestion", "") or review.summary or "").strip(),
                current_summary=latest_state.current_position_summary if latest_state else "",
                now=now,
            )
            self._memory_review_repository.save_suggestion(suggestion)
            suggestion_ids.append(suggestion.id)

        memory_summary = str(review.summary or "").strip()
        if memory_summary:
            suggestion = self._build_story_memory_suggestion(
                review_id=review.review_id,
                work_id=review.work_id,
                chapter_id=review.chapter_id,
                draft=draft,
                latest_memory=latest_memory,
                latest_state=latest_state,
                proposed_summary=memory_summary,
                current_summary=latest_memory.global_summary if latest_memory else "",
                now=now,
            )
            self._memory_review_repository.save_suggestion(suggestion)
            suggestion_ids.append(suggestion.id)

        gate = self._memory_review_repository.save_gate(
            self._build_gate(
                work_id=review.work_id,
                chapter_id=review.chapter_id,
                suggestion_ids=suggestion_ids,
                now=now,
            )
        )
        return gate

    def list_gates(self, *, work_id: str, chapter_id: str = ""):
        gates = self._memory_review_repository.list_gates(work_id=work_id, chapter_id=chapter_id)
        updated: list = []
        for gate in gates:
            if gate.state == MemoryGateState.OPEN:
                gate = self._memory_review_repository.save_gate(
                    gate.model_copy(update={"state": MemoryGateState.WAITING_FOR_USER})
                )
            updated.append(gate)
        return updated

    def get_gate(self, gate_id: str):
        gate = self._memory_review_repository.get_gate(gate_id)
        if gate.state == MemoryGateState.OPEN:
            gate = self._memory_review_repository.save_gate(gate.model_copy(update={"state": MemoryGateState.WAITING_FOR_USER}))
        return gate

    def list_gate_suggestions(self, gate_id: str):
        gate = self.get_gate(gate_id)
        suggestions = self._memory_review_repository.list_suggestions(work_id=gate.work_id, chapter_id=gate.chapter_id, gate_id=gate.gate_id)
        shown: list[MemoryUpdateSuggestion] = []
        for suggestion in suggestions:
            if suggestion.status == MemorySuggestionStatus.GENERATED:
                suggestion = self._memory_review_repository.save_suggestion(
                    suggestion.model_copy(update={"status": MemorySuggestionStatus.SHOWN, "updated_at": self._now()})
                )
            shown.append(suggestion)
        return shown

    def get_suggestion(self, suggestion_id: str):
        suggestion = self._memory_review_repository.get_suggestion(suggestion_id)
        if suggestion.status == MemorySuggestionStatus.GENERATED:
            suggestion = self._memory_review_repository.save_suggestion(
                suggestion.model_copy(update={"status": MemorySuggestionStatus.SHOWN, "updated_at": self._now()})
            )
        return suggestion

    def approve_suggestion(
        self,
        gate_id: str,
        suggestion_id: str,
        *,
        idempotency_key: str,
        user_id: str,
        user_action: bool,
        request_id: str,
        trace_id: str,
    ):
        self._require_user_action(user_action)
        self._claim_idempotency_key(idempotency_key, operation_name=f"approve:{gate_id}:{suggestion_id}")
        suggestion = self.get_suggestion(suggestion_id)
        self._record_high_risk_audit(
            trace_id=trace_id,
            session_id=suggestion.agent_session_id,
            step_id="",
            event_type="user_decision_recorded",
            summary="approve_memory",
            payload_digest={"decision_type": "approve_memory", "suggestion_id": suggestion_id},
        )
        now = self._now()
        updated = suggestion.model_copy(
            update={
                "decision": MemorySuggestionDecisionType.APPROVED,
                "decided_by": user_id,
                "decided_at": now,
                "status": MemorySuggestionStatus.ACCEPTED,
                "updated_at": now,
                "request_id": request_id,
                "trace_id": trace_id,
            }
        )
        self._memory_review_repository.save_suggestion(updated)
        self._persist_revisions_for_suggestion(updated, user_id=user_id, decision_note="", request_id=request_id, trace_id=trace_id)
        return self._refresh_gate_state(gate_id, operator_id=user_id)

    def edit_and_approve_suggestion(
        self,
        gate_id: str,
        suggestion_id: str,
        *,
        idempotency_key: str,
        user_id: str,
        user_action: bool,
        request_id: str,
        trace_id: str,
        proposed_value_summary: str,
        decision_note: str = "",
    ):
        self._require_user_action(user_action)
        self._claim_idempotency_key(idempotency_key, operation_name=f"edit_and_approve:{gate_id}:{suggestion_id}")
        suggestion = self.get_suggestion(suggestion_id)
        self._record_high_risk_audit(
            trace_id=trace_id,
            session_id=suggestion.agent_session_id,
            step_id="",
            event_type="user_decision_recorded",
            summary="approve_memory",
            payload_digest={"decision_type": "approve_memory", "suggestion_id": suggestion_id},
        )
        if not str(proposed_value_summary or "").strip():
            raise ValueError("memory_edit_value_required")
        now = self._now()
        candidate = suggestion.candidates[0] if suggestion.candidates else None
        updated_candidates = list(suggestion.candidates)
        if candidate is not None:
            updated_candidates[0] = candidate.model_copy(
                update={"proposed_value": proposed_value_summary.strip(), "rationale": decision_note or candidate.rationale}
            )
        updated = suggestion.model_copy(
            update={
                "proposed_value_summary": proposed_value_summary.strip(),
                "candidates": updated_candidates,
                "decision": MemorySuggestionDecisionType.EDITED_APPROVED,
                "decided_by": user_id,
                "decided_at": now,
                "status": MemorySuggestionStatus.EDITED,
                "updated_at": now,
                "request_id": request_id,
                "trace_id": trace_id,
            }
        )
        self._memory_review_repository.save_suggestion(updated)
        self._persist_revisions_for_suggestion(updated, user_id=user_id, decision_note=decision_note, request_id=request_id, trace_id=trace_id)
        return self._refresh_gate_state(gate_id, operator_id=user_id)

    def reject_suggestion(
        self,
        gate_id: str,
        suggestion_id: str,
        *,
        idempotency_key: str,
        user_id: str,
        user_action: bool,
        request_id: str,
        trace_id: str,
        decision_note: str = "",
    ):
        self._require_user_action(user_action)
        self._claim_idempotency_key(idempotency_key, operation_name=f"reject:{gate_id}:{suggestion_id}")
        suggestion = self.get_suggestion(suggestion_id)
        self._record_high_risk_audit(
            trace_id=trace_id,
            session_id=suggestion.agent_session_id,
            step_id="",
            event_type="user_decision_recorded",
            summary="reject_memory",
            payload_digest={"decision_type": "reject_memory", "suggestion_id": suggestion_id},
        )
        self._memory_review_repository.save_suggestion(
            suggestion.model_copy(
                update={
                    "decision": MemorySuggestionDecisionType.REJECTED,
                    "decided_by": user_id,
                    "decided_at": self._now(),
                    "status": MemorySuggestionStatus.REJECTED,
                    "updated_at": self._now(),
                    "request_id": request_id,
                    "trace_id": trace_id,
                }
            )
        )
        return self._refresh_gate_state(gate_id, operator_id=user_id)

    def defer_suggestion(
        self,
        gate_id: str,
        suggestion_id: str,
        *,
        idempotency_key: str,
        user_id: str,
        user_action: bool,
        request_id: str,
        trace_id: str,
        decision_note: str = "",
    ):
        self._require_user_action(user_action)
        self._claim_idempotency_key(idempotency_key, operation_name=f"defer:{gate_id}:{suggestion_id}")
        suggestion = self.get_suggestion(suggestion_id)
        self._memory_review_repository.save_suggestion(
            suggestion.model_copy(
                update={
                    "decision": MemorySuggestionDecisionType.DEFERRED,
                    "decided_by": user_id,
                    "decided_at": self._now(),
                    "status": MemorySuggestionStatus.SHOWN,
                    "updated_at": self._now(),
                    "request_id": request_id,
                    "trace_id": trace_id,
                }
            )
        )
        return self._refresh_gate_state(gate_id, operator_id=user_id)

    def apply_gate(
        self,
        gate_id: str,
        *,
        user_id: str,
        user_action: bool,
        idempotency_key: str,
        request_id: str,
        trace_id: str,
    ):
        self._require_user_action(user_action)
        self._claim_idempotency_key(idempotency_key, operation_name=f"apply_gate:{gate_id}")
        gate = self.get_gate(gate_id)
        self._record_high_risk_audit(
            trace_id=trace_id,
            session_id="",
            step_id="",
            event_type="memory_revision_applied",
            summary="apply_memory",
            payload_digest={"gate_id": gate_id},
        )
        suggestions = self.list_gate_suggestions(gate_id)
        approved_suggestions = [
            item
            for item in suggestions
            if item.decision in {MemorySuggestionDecisionType.APPROVED, MemorySuggestionDecisionType.EDITED_APPROVED}
        ]
        if not approved_suggestions:
            raise ValueError("memory_revision_apply_blocked")
        self._precheck_conflicts(approved_suggestions, request_id=request_id, trace_id=trace_id)
        apply_results: list[MemoryRevisionApplyResult] = []
        revision_ids: list[str] = []

        for suggestion in approved_suggestions:
            for revision in self._memory_review_repository.list_story_memory_revisions(
                work_id=gate.work_id,
                chapter_id=gate.chapter_id,
                source_suggestion_id=suggestion.id,
            ):
                apply_results.append(
                    self._apply_story_memory_revision(revision, user_id=user_id, request_id=request_id, trace_id=trace_id)
                )
                revision_ids.append(revision.id)
            for revision in self._memory_review_repository.list_story_state_revisions(
                work_id=gate.work_id,
                chapter_id=gate.chapter_id,
                source_suggestion_id=suggestion.id,
            ):
                apply_results.append(
                    self._apply_story_state_revision(revision, user_id=user_id, request_id=request_id, trace_id=trace_id)
                )
                revision_ids.append(revision.id)
            converted_status = MemorySuggestionStatus.CONVERTED
            self._memory_review_repository.save_suggestion(
                self._memory_review_repository.get_suggestion(suggestion.id).model_copy(
                    update={"status": converted_status, "updated_at": self._now()}
                )
            )

        applied_gate = self._memory_review_repository.save_gate(
            gate.model_copy(update={"state": MemoryGateState.APPLIED, "operator_id": user_id, "closed_at": self._now()})
        )
        return {
            "gate": applied_gate,
            "apply_results": [result.model_dump(mode="json") for result in apply_results],
            "revision_ids": revision_ids,
        }

    def list_revisions(self, *, work_id: str, chapter_id: str = "") -> list[dict[str, object]]:
        revisions: list[dict[str, object]] = []
        for item in self._memory_review_repository.list_story_memory_revisions(work_id=work_id, chapter_id=chapter_id):
            revisions.append(self._serialize_story_memory_revision(item))
        for item in self._memory_review_repository.list_story_state_revisions(work_id=work_id, chapter_id=chapter_id):
            revisions.append(self._serialize_story_state_revision(item))
        return sorted(revisions, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def get_revision(self, revision_id: str) -> dict[str, object]:
        try:
            return self._serialize_story_memory_revision(self._memory_review_repository.get_story_memory_revision(revision_id))
        except ValueError:
            return self._serialize_story_state_revision(self._memory_review_repository.get_story_state_revision(revision_id))

    def rollback_revision(
        self,
        revision_id: str,
        *,
        user_id: str,
        user_action: bool,
        idempotency_key: str,
        request_id: str,
        trace_id: str,
    ) -> dict[str, object]:
        self._require_user_action(user_action)
        self._claim_idempotency_key(idempotency_key, operation_name=f"rollback_revision:{revision_id}")
        self._record_high_risk_audit(
            trace_id=trace_id,
            session_id="",
            step_id="",
            event_type="memory_revision_rolled_back",
            summary="rollback_memory",
            payload_digest={"revision_id": revision_id},
        )
        try:
            revision = self._memory_review_repository.get_story_memory_revision(revision_id)
            if revision.status != MemoryRevisionStatus.APPLIED:
                raise ValueError("memory_rollback_not_allowed")
            self._precheck_conflicts_for_revision(
                source_suggestion_id=revision.source_suggestion_id,
                request_id=request_id,
                trace_id=trace_id,
            )
            latest_memory = self._story_memory_repository.get_latest_snapshot_by_work(revision.work_id)
            expected_current_ref = self._extract_applied_ref(revision.apply_result_ref, prefix="story_memory_snapshot:")
            if latest_memory is None or not expected_current_ref or latest_memory.snapshot_id != expected_current_ref:
                raise ValueError("memory_revision_apply_blocked")
            rollback = StoryMemoryRevision(
                id=f"memrev_{uuid.uuid4().hex[:10]}",
                work_id=revision.work_id,
                chapter_id=revision.chapter_id,
                source_suggestion_id=revision.source_suggestion_id,
                revision_items=[
                    item.model_copy(
                        update={
                            "id": f"memritem_{uuid.uuid4().hex[:10]}",
                            "revision_id": "",
                            "target_memory_ref_id": latest_memory.snapshot_id,
                            "before_value_summary": revision.after_summary,
                            "after_value_summary": revision.before_summary,
                        }
                    )
                    for item in revision.revision_items
                ],
                revision_type=MemoryRevisionRecordType.ROLLBACK,
                status=MemoryRevisionStatus.APPROVED,
                approved_by=user_id,
                approved_at=self._now(),
                before_summary=revision.after_summary,
                after_summary=revision.before_summary,
                request_id=request_id,
                trace_id=trace_id,
                created_at=self._now(),
                updated_at=self._now(),
            )
            rollback = rollback.model_copy(
                update={
                    "revision_items": [
                        item.model_copy(update={"revision_id": rollback.id}) for item in rollback.revision_items
                    ]
                }
            )
            self._memory_review_repository.save_story_memory_revision(rollback)
            self._record_revision_decision(rollback.id, MemoryReviewDecisionType.APPROVED, user_id, "", request_id)
            result = self._apply_story_memory_revision(rollback, user_id=user_id, request_id=request_id, trace_id=trace_id)
            saved = self._memory_review_repository.get_story_memory_revision(rollback.id).model_copy(
                update={"apply_result_ref": result.id}
            )
            self._memory_review_repository.save_story_memory_revision(saved)
            return self._serialize_story_memory_revision(saved)
        except ValueError as exc:
            if str(exc) != "memory_revision_not_found":
                raise

        state_revision = self._memory_review_repository.get_story_state_revision(revision_id)
        if state_revision.status != MemoryRevisionStatus.APPLIED:
            raise ValueError("memory_rollback_not_allowed")
        self._precheck_conflicts_for_revision(
            source_suggestion_id=state_revision.source_suggestion_id,
            request_id=request_id,
            trace_id=trace_id,
        )
        latest_state = self._story_state_repository.get_latest_analysis_baseline_by_work(state_revision.work_id)
        expected_current_ref = self._extract_applied_ref(state_revision.apply_result_ref, prefix="story_state_snapshot:")
        if latest_state is None or not expected_current_ref or latest_state.story_state_id != expected_current_ref:
            raise ValueError("memory_revision_apply_blocked")
        rollback = StoryStateRevision(
            id=f"strev_{uuid.uuid4().hex[:10]}",
            work_id=state_revision.work_id,
            chapter_id=state_revision.chapter_id,
            source_suggestion_id=state_revision.source_suggestion_id,
            state_items=[{"field_path": "current_position_summary", "before": state_revision.after_summary, "after": state_revision.before_summary}],
            target_state_ref=latest_state.story_state_id,
            version_guard=latest_state.story_state_id,
            revision_type=MemoryRevisionRecordType.ROLLBACK,
            status=MemoryRevisionStatus.APPROVED,
            approved_by=user_id,
            approved_at=self._now(),
            before_summary=state_revision.after_summary,
            after_summary=state_revision.before_summary,
            request_id=request_id,
            trace_id=trace_id,
            created_at=self._now(),
            updated_at=self._now(),
        )
        self._memory_review_repository.save_story_state_revision(rollback)
        self._record_revision_decision(rollback.id, MemoryReviewDecisionType.APPROVED, user_id, "", request_id)
        result = self._apply_story_state_revision(rollback, user_id=user_id, request_id=request_id, trace_id=trace_id)
        saved = self._memory_review_repository.get_story_state_revision(rollback.id).model_copy(update={"apply_result_ref": result.id})
        self._memory_review_repository.save_story_state_revision(saved)
        return self._serialize_story_state_revision(saved)

    def _persist_revisions_for_suggestion(
        self,
        suggestion: MemoryUpdateSuggestion,
        *,
        user_id: str,
        decision_note: str,
        request_id: str,
        trace_id: str,
    ) -> None:
        now = self._now()
        if suggestion.target_memory_type in {MemoryTargetType.STORY_MEMORY, MemoryTargetType.BOTH}:
            revision = StoryMemoryRevision(
                id=f"memrev_{uuid.uuid4().hex[:10]}",
                work_id=suggestion.work_id,
                chapter_id=suggestion.chapter_id,
                source_suggestion_id=suggestion.id,
                revision_items=[
                    StoryMemoryRevisionItem(
                        id=f"memritem_{uuid.uuid4().hex[:10]}",
                        revision_id="",
                        target_memory_type="story_memory",
                        target_memory_ref_id=suggestion.target_memory_ref_id or self._latest_memory_ref(suggestion.work_id),
                        revision_type=suggestion.revision_type,
                        before_value_summary=suggestion.current_value_summary,
                        after_value_summary=suggestion.proposed_value_summary,
                        evidence_refs=list(suggestion.evidence_refs),
                        status=MemoryRevisionStatus.PENDING,
                    )
                ],
                revision_type=MemoryRevisionRecordType.NORMAL,
                status=MemoryRevisionStatus.APPROVED,
                approved_by=user_id,
                approved_at=now,
                before_summary=suggestion.current_value_summary,
                after_summary=suggestion.proposed_value_summary,
                request_id=request_id,
                trace_id=trace_id,
                created_at=now,
                updated_at=now,
            )
            revision = revision.model_copy(
                update={
                    "revision_items": [item.model_copy(update={"revision_id": revision.id}) for item in revision.revision_items]
                }
            )
            self._memory_review_repository.save_story_memory_revision(revision)
            self._record_revision_created_trace(
                trace_id=trace_id,
                session_id=suggestion.agent_session_id,
                revision_id=revision.id,
                target_asset="story_memory",
                source_suggestion_id=suggestion.id,
            )
            self._record_revision_decision(revision.id, MemoryReviewDecisionType.APPROVED, user_id, decision_note, request_id)
        if suggestion.target_memory_type in {MemoryTargetType.STORY_STATE, MemoryTargetType.BOTH}:
            revision = StoryStateRevision(
                id=f"strev_{uuid.uuid4().hex[:10]}",
                work_id=suggestion.work_id,
                chapter_id=suggestion.chapter_id,
                source_suggestion_id=suggestion.id,
                state_items=[
                    {
                        "field_path": "current_position_summary",
                        "before": suggestion.current_value_summary,
                        "after": suggestion.proposed_value_summary,
                    }
                ],
                target_state_ref=suggestion.target_memory_ref_id or self._latest_state_ref(suggestion.work_id),
                version_guard=suggestion.target_memory_ref_id or self._latest_state_ref(suggestion.work_id),
                revision_type=MemoryRevisionRecordType.NORMAL,
                status=MemoryRevisionStatus.APPROVED,
                approved_by=user_id,
                approved_at=now,
                before_summary=suggestion.current_value_summary,
                after_summary=suggestion.proposed_value_summary,
                request_id=request_id,
                trace_id=trace_id,
                created_at=now,
                updated_at=now,
            )
            self._memory_review_repository.save_story_state_revision(revision)
            self._record_revision_created_trace(
                trace_id=trace_id,
                session_id=suggestion.agent_session_id,
                revision_id=revision.id,
                target_asset="story_state",
                source_suggestion_id=suggestion.id,
            )
            self._record_revision_decision(revision.id, MemoryReviewDecisionType.APPROVED, user_id, decision_note, request_id)

    def _apply_story_memory_revision(
        self,
        revision: StoryMemoryRevision,
        *,
        user_id: str,
        request_id: str,
        trace_id: str,
    ) -> MemoryRevisionApplyResult:
        latest = self._story_memory_repository.get_latest_snapshot_by_work(revision.work_id)
        expected_ref = revision.revision_items[0].target_memory_ref_id if revision.revision_items else ""
        if latest is not None and expected_ref and latest.snapshot_id != expected_ref:
            raise ValueError("memory_revision_apply_blocked")
        source = latest or StoryMemorySnapshot(
            snapshot_id="memory_empty",
            work_id=revision.work_id,
            source_initialization_id="",
            source_job_id="",
            created_at=self._now(),
        )
        new_snapshot = source.model_copy(
            update={
                "snapshot_id": f"memory_{uuid.uuid4().hex[:10]}",
                "source_job_id": revision.id,
                "global_summary": revision.after_summary or source.global_summary,
                "stale_status": "fresh",
                "stale_reason": "",
                "created_at": self._now(),
            }
        )
        self._story_memory_repository.save_snapshot(new_snapshot)
        result = self._memory_review_repository.save_apply_result(
            MemoryRevisionApplyResult(
                id=f"memapply_{uuid.uuid4().hex[:10]}",
                revision_id=revision.id,
                apply_status=MemoryApplyStatus.SUCCESS,
                applied_memory_refs=[f"story_memory_snapshot:{new_snapshot.snapshot_id}"],
                before_after_snapshot_ref=f"{source.snapshot_id}->{new_snapshot.snapshot_id}",
                applied_at=self._now(),
            )
        )
        saved = revision.model_copy(
            update={
                "status": MemoryRevisionStatus.APPLIED,
                "applied_by": user_id,
                "applied_at": result.applied_at,
                "apply_result_ref": result.id,
                "updated_at": self._now(),
                "request_id": request_id,
                "trace_id": trace_id,
                "revision_items": [
                    item.model_copy(update={"status": MemoryRevisionStatus.APPLIED, "target_memory_ref_id": source.snapshot_id or item.target_memory_ref_id})
                    for item in revision.revision_items
                ],
            }
        )
        self._memory_review_repository.save_story_memory_revision(saved)
        return result

    def _apply_story_state_revision(
        self,
        revision: StoryStateRevision,
        *,
        user_id: str,
        request_id: str,
        trace_id: str,
    ) -> MemoryRevisionApplyResult:
        latest = self._story_state_repository.get_latest_analysis_baseline_by_work(revision.work_id)
        if latest is not None and revision.version_guard and latest.story_state_id != revision.version_guard:
            raise ValueError("memory_revision_apply_blocked")
        source = latest or StoryStateSnapshot(
            story_state_id="state_empty",
            work_id=revision.work_id,
            source_initialization_id="",
            source_job_id="",
            created_at=self._now(),
        )
        new_state = source.model_copy(
            update={
                "story_state_id": f"state_{uuid.uuid4().hex[:10]}",
                "source_job_id": revision.id,
                "current_position_summary": revision.after_summary or source.current_position_summary,
                "continuity_notes": list(source.continuity_notes) + [f"revision:{revision.id}"],
                "stale_status": "fresh",
                "stale_reason": "",
                "created_at": self._now(),
            }
        )
        self._story_state_repository.save_analysis_baseline(new_state)
        result = self._memory_review_repository.save_apply_result(
            MemoryRevisionApplyResult(
                id=f"memapply_{uuid.uuid4().hex[:10]}",
                revision_id=revision.id,
                apply_status=MemoryApplyStatus.SUCCESS,
                applied_memory_refs=[f"story_state_snapshot:{new_state.story_state_id}"],
                before_after_snapshot_ref=f"{source.story_state_id}->{new_state.story_state_id}",
                applied_at=self._now(),
            )
        )
        saved = revision.model_copy(
            update={
                "status": MemoryRevisionStatus.APPLIED,
                "applied_by": user_id,
                "applied_at": result.applied_at,
                "apply_result_ref": result.id,
                "updated_at": self._now(),
                "request_id": request_id,
                "trace_id": trace_id,
            }
        )
        self._memory_review_repository.save_story_state_revision(saved)
        return result

    def _refresh_gate_state(
        self,
        gate_id: str,
        *,
        operator_id: str,
        close_if_terminal: bool = False,
    ):
        gate = self._memory_review_repository.get_gate(gate_id)
        suggestions = self._memory_review_repository.list_suggestions(work_id=gate.work_id, chapter_id=gate.chapter_id, gate_id=gate_id)
        approved_count = len(
            [item for item in suggestions if item.decision in {MemorySuggestionDecisionType.APPROVED, MemorySuggestionDecisionType.EDITED_APPROVED}]
        )
        rejected_count = len([item for item in suggestions if item.decision == MemorySuggestionDecisionType.REJECTED])
        pending_count = len(suggestions) - approved_count - rejected_count
        state = MemoryGateState.WAITING_FOR_USER
        if rejected_count == len(suggestions) and suggestions:
            state = MemoryGateState.REJECTED
        elif approved_count and (pending_count > 0 or rejected_count > 0):
            state = MemoryGateState.PARTIALLY_APPROVED
        elif approved_count == len(suggestions) and suggestions:
            state = MemoryGateState.APPROVED
        updated = gate.model_copy(
            update={
                "state": state,
                "operator_id": operator_id,
                "closed_at": self._now() if close_if_terminal and state in {MemoryGateState.REJECTED, MemoryGateState.APPLIED} else gate.closed_at,
            }
        )
        return self._memory_review_repository.save_gate(updated)

    def _precheck_conflicts(self, suggestions: list[MemoryUpdateSuggestion], *, request_id: str, trace_id: str) -> None:
        if self._conflict_guard_service is None:
            return
        for suggestion in suggestions:
            candidate_draft_id = str(suggestion.candidate_draft_id or "").strip()
            candidate_version_id = str(suggestion.candidate_version_id or "").strip()
            if not candidate_draft_id:
                continue
            draft = self._candidate_draft_repository.get(candidate_draft_id)
            version_id = candidate_version_id or draft.selected_version_id or draft.accepted_version_id
            result = self._conflict_guard_service.precheck_apply_conflicts(
                candidate_draft_id=candidate_draft_id,
                candidate_version_id=version_id,
                expected_chapter_version=self._candidate_chapter_version(draft.chapter_id, draft.work_id),
                request_id=request_id,
                trace_id=trace_id,
            )
            if result.blocking_count:
                raise ValueError("memory_revision_apply_blocked")

    def _precheck_conflicts_for_revision(self, *, source_suggestion_id: str, request_id: str, trace_id: str) -> None:
        suggestion_id = str(source_suggestion_id or "").strip()
        if not suggestion_id:
            return
        suggestion = self._memory_review_repository.get_suggestion(suggestion_id)
        self._precheck_conflicts([suggestion], request_id=request_id, trace_id=trace_id)

    def _claim_idempotency_key(self, idempotency_key: str, *, operation_name: str) -> None:
        self._memory_review_repository.claim_idempotency_key(
            idempotency_key=idempotency_key,
            operation_name=operation_name,
        )

    def _record_high_risk_audit(
        self,
        *,
        trace_id: str,
        session_id: str,
        step_id: str,
        event_type: str,
        summary: str,
        payload_digest: dict[str, object],
    ) -> None:
        if self._trace_service is None or not str(trace_id or "").strip():
            return
        self._trace_service.record_audit_event(
            trace_id=trace_id,
            session_id=session_id,
            step_id=step_id,
            event_type=event_type,
            summary=summary,
            payload_digest=payload_digest,
            high_risk_user_action=True,
        )

    def _record_revision_created_trace(
        self,
        *,
        trace_id: str,
        session_id: str,
        revision_id: str,
        target_asset: str,
        source_suggestion_id: str,
    ) -> None:
        if self._trace_service is None or not str(trace_id or "").strip():
            return
        self._trace_service.record_audit_event(
            trace_id=trace_id,
            session_id=session_id,
            step_id="",
            event_type="memory_revision_created",
            summary=revision_id,
            payload_digest={
                "revision_id": revision_id,
                "target_asset": target_asset,
                "source_suggestion_id": source_suggestion_id,
            },
        )

    def _extract_applied_ref(self, apply_result_ref: str, *, prefix: str) -> str:
        result_ref = str(apply_result_ref or "").strip()
        if not result_ref:
            return ""
        result = self._memory_review_repository.get_apply_result(result_ref)
        for item in result.applied_memory_refs:
            normalized = str(item or "").strip()
            if normalized.startswith(prefix):
                return normalized[len(prefix):]
        return ""

    def _candidate_chapter_version(self, chapter_id: str, work_id: str) -> int:
        work_drafts = self._candidate_draft_repository.list_by_work(work_id, chapter_id=chapter_id)
        if work_drafts:
            metadata = getattr(work_drafts[0], "metadata", {}) or {}
            if isinstance(metadata, dict) and metadata.get("chapter_version"):
                return int(metadata.get("chapter_version") or 0)
        latest_state = self._story_state_repository.get_latest_analysis_baseline_by_work(work_id)
        if latest_state and latest_state.latest_chapter_id == chapter_id:
            return latest_state.latest_chapter_version
        return 0

    def _record_revision_decision(
        self,
        revision_id: str,
        decision: MemoryReviewDecisionType,
        user_id: str,
        decision_note: str,
        request_id: str,
    ) -> None:
        self._memory_review_repository.save_decision(
            MemoryRevisionDecision(
                id=f"memdec_{uuid.uuid4().hex[:10]}",
                revision_id=revision_id,
                decision=decision,
                decided_by=user_id,
                decided_at=self._now(),
                decision_note=decision_note or request_id,
            )
        )

    def _build_gate(self, *, work_id: str, chapter_id: str, suggestion_ids: list[str], now: str):
        return MemoryReviewGate(
            gate_id=f"mrg_{uuid.uuid4().hex[:10]}",
            work_id=work_id,
            chapter_id=chapter_id,
            suggestion_ids=suggestion_ids,
            state=MemoryGateState.OPEN,
            open_at=now,
        )

    def _build_story_state_suggestion(
        self,
        *,
        review_id: str,
        work_id: str,
        chapter_id: str,
        draft,
        latest_state: StoryStateSnapshot | None,
        latest_memory: StoryMemorySnapshot | None,
        proposed_summary: str,
        current_summary: str,
        now: str,
    ) -> MemoryUpdateSuggestion:
        suggestion_id = f"mus_{uuid.uuid4().hex[:10]}"
        return MemoryUpdateSuggestion(
            id=suggestion_id,
            work_id=work_id,
            chapter_id=chapter_id,
            candidate_draft_id=draft.candidate_draft_id,
            candidate_version_id=draft.selected_version_id or draft.accepted_version_id,
            review_report_id=review_id,
            agent_session_id=draft.agent_session_id,
            source_type="review_report",
            source_ref_id=review_id,
            target_memory_type=MemoryTargetType.STORY_STATE,
            target_memory_ref_id=latest_state.story_state_id if latest_state else "",
            revision_type=MemoryUpdateType.STORY_STATE_UPDATE,
            proposed_value_summary=proposed_summary,
            current_value_summary=current_summary,
            evidence_refs=[
                MemoryRevisionSource(
                    source_type="review_issue",
                    entity_type="review_report",
                    entity_ref_id=review_id,
                    source_ref_id=review_id,
                    source_session_id=draft.agent_session_id,
                    source_version_id=draft.selected_version_id or draft.accepted_version_id,
                    excerpt=proposed_summary[:160],
                    relevance="story_state_update",
                )
            ],
            candidates=[
                MemoryUpdateCandidate(
                    candidate_id=f"muc_{uuid.uuid4().hex[:10]}",
                    suggestion_id=suggestion_id,
                    candidate_no=1,
                    field_path="current_position_summary",
                    field_label="当前状态摘要",
                    current_value=current_summary,
                    proposed_value=proposed_summary,
                    rationale=(latest_memory.global_summary if latest_memory else "review_report")[:200],
                    created_at=now,
                )
            ],
            confidence=0.81,
            severity=MemorySuggestionSeverity.WARNING,
            status=MemorySuggestionStatus.GENERATED,
            created_by="reviewer_agent",
            created_at=now,
            updated_at=now,
        )

    def _build_story_memory_suggestion(
        self,
        *,
        review_id: str,
        work_id: str,
        chapter_id: str,
        draft,
        latest_memory: StoryMemorySnapshot | None,
        latest_state: StoryStateSnapshot | None,
        proposed_summary: str,
        current_summary: str,
        now: str,
    ) -> MemoryUpdateSuggestion:
        suggestion_id = f"mus_{uuid.uuid4().hex[:10]}"
        return MemoryUpdateSuggestion(
            id=suggestion_id,
            work_id=work_id,
            chapter_id=chapter_id,
            candidate_draft_id=draft.candidate_draft_id,
            candidate_version_id=draft.selected_version_id or draft.accepted_version_id,
            review_report_id=review_id,
            agent_session_id=draft.agent_session_id,
            source_type="review_summary",
            source_ref_id=review_id,
            target_memory_type=MemoryTargetType.STORY_MEMORY,
            target_memory_ref_id=latest_memory.snapshot_id if latest_memory else "",
            revision_type=MemoryUpdateType.CONTINUITY_NOTE_ADD,
            proposed_value_summary=proposed_summary,
            current_value_summary=current_summary,
            evidence_refs=[
                MemoryRevisionSource(
                    source_type="review_report",
                    entity_type="review_report",
                    entity_ref_id=review_id,
                    source_ref_id=review_id,
                    source_session_id=draft.agent_session_id,
                    source_version_id=draft.selected_version_id or draft.accepted_version_id,
                    excerpt=(latest_state.current_position_summary if latest_state else proposed_summary)[:160],
                    relevance="story_memory_update",
                )
            ],
            candidates=[
                MemoryUpdateCandidate(
                    candidate_id=f"muc_{uuid.uuid4().hex[:10]}",
                    suggestion_id=suggestion_id,
                    candidate_no=1,
                    field_path="global_summary",
                    field_label="故事记忆摘要",
                    current_value=current_summary,
                    proposed_value=proposed_summary,
                    rationale="review_summary",
                    created_at=now,
                )
            ],
            confidence=0.74,
            severity=MemorySuggestionSeverity.INFO,
            status=MemorySuggestionStatus.GENERATED,
            created_by="reviewer_agent",
            created_at=now,
            updated_at=now,
        )

    def _latest_memory_ref(self, work_id: str) -> str:
        latest = self._story_memory_repository.get_latest_snapshot_by_work(work_id)
        return latest.snapshot_id if latest is not None else ""

    def _latest_state_ref(self, work_id: str) -> str:
        latest = self._story_state_repository.get_latest_analysis_baseline_by_work(work_id)
        return latest.story_state_id if latest is not None else ""

    @staticmethod
    def _serialize_story_memory_revision(revision: StoryMemoryRevision) -> dict[str, object]:
        payload = revision.model_dump(mode="json")
        payload["revision_id"] = revision.id
        payload["target_asset"] = "story_memory"
        return payload

    @staticmethod
    def _serialize_story_state_revision(revision: StoryStateRevision) -> dict[str, object]:
        payload = revision.model_dump(mode="json")
        payload["revision_id"] = revision.id
        payload["target_asset"] = "story_state"
        return payload

    @staticmethod
    def _require_user_action(user_action: bool) -> None:
        if not user_action:
            raise ValueError("action_not_allowed")

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
