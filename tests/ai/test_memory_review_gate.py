from __future__ import annotations

from pathlib import Path

from application.services.ai.agent_trace_service import AgentTraceService
from application.services.ai.conflict_guard_service import ConflictGuardService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    AIReviewResult,
    AIReviewRiskLevel,
    AIReviewStatus,
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
    CandidateDraftVersion,
    CandidateDraftVersionStatus,
    MemoryGateState,
    MemoryReviewDecisionType,
    MemoryRevisionRecordType,
    MemoryRevisionStatus,
    MemorySuggestionDecisionType,
    MemorySuggestionStatus,
    MemoryTargetType,
    StoryMemorySnapshot,
    StoryStateSnapshot,
)
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_review_store import FileAIReviewStore
from infrastructure.database.repositories.ai.file_ai_suggestion_store import FileAISuggestionStore
from infrastructure.database.repositories.ai.file_agent_trace_store import FileAgentTraceStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_conflict_guard_store import FileConflictGuardStore
from infrastructure.database.repositories.ai.file_direction_plan_store import FileDirectionPlanStore
from infrastructure.database.repositories.ai.file_memory_review_store import FileMemoryReviewStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore


class _CriticalAuditTraceStub:
    def record_audit_event(self, **kwargs):
        raise ValueError("critical_audit_write_failed")


def _build_service(tmp_path: Path):
    from application.services.ai.memory_review_gate_service import MemoryReviewGateService

    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    review_store = FileAIReviewStore(tmp_path / "reviews.json")
    memory_store = FileStoryMemoryStore(tmp_path / "story_memory.json")
    state_store = FileStoryStateStore(tmp_path / "story_state.json")
    review_gate_store = FileMemoryReviewStore(tmp_path / "memory_review.json")
    conflict_store = FileConflictGuardStore(tmp_path / "conflicts.json")
    ai_suggestion_store = FileAISuggestionStore(tmp_path / "ai_suggestions.json")
    direction_store = FileDirectionPlanStore(tmp_path / "direction_plan.json")
    trace_store = FileAgentTraceStore(tmp_path / "memory_trace.json")
    trace_service = AgentTraceService(repository=trace_store)
    conflict_guard_service = ConflictGuardService(
        conflict_guard_repository=conflict_store,
        candidate_draft_repository=candidate_store,
        chapter_service=chapter_service,
        ai_suggestion_repository=ai_suggestion_store,
        direction_plan_repository=direction_store,
        ai_review_repository=review_store,
        trace_service=trace_service,
    )
    service = MemoryReviewGateService(
        memory_review_repository=review_gate_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
        ai_review_repository=review_store,
        candidate_draft_repository=candidate_store,
        conflict_guard_service=conflict_guard_service,
        trace_service=trace_service,
    )
    return {
        "work_service": work_service,
        "chapter_service": chapter_service,
        "candidate_store": candidate_store,
        "review_store": review_store,
        "memory_store": memory_store,
        "state_store": state_store,
        "review_gate_store": review_gate_store,
        "service": service,
        "trace_service": trace_service,
    }


def _build_service_with_trace_stub(tmp_path: Path):
    bundle = _build_service(tmp_path)
    from application.services.ai.memory_review_gate_service import MemoryReviewGateService

    bundle["service"] = MemoryReviewGateService(
        memory_review_repository=bundle["review_gate_store"],
        story_memory_repository=bundle["memory_store"],
        story_state_repository=bundle["state_store"],
        ai_review_repository=bundle["review_store"],
        candidate_draft_repository=bundle["candidate_store"],
        conflict_guard_service=None,
        trace_service=_CriticalAuditTraceStub(),
    )
    return bundle


def _seed_review_context(tmp_path: Path):
    bundle = _build_service(tmp_path)
    work_service = bundle["work_service"]
    chapter_service = bundle["chapter_service"]
    candidate_store = bundle["candidate_store"]
    review_store = bundle["review_store"]
    memory_store = bundle["memory_store"]
    state_store = bundle["state_store"]

    work = work_service.create_work("S9 Work", "Author")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章 灯塔地图",
        content="顾迟在灯塔里整理父亲留下的地图碎片。",
        expected_version=1,
    )
    memory_store.save_snapshot(
        StoryMemorySnapshot(
            snapshot_id="memory_base",
            work_id=work.id,
            source_initialization_id="init_1",
            source_job_id="job_1",
            source_chapter_ids=[chapter.id.value],
            source_chapter_versions={chapter.id.value: chapter.version},
            global_summary="顾迟尚未确认地图的真实用途。",
            chapter_summaries=[{"chapter_id": chapter.id.value, "chapter_title": chapter.title, "summary": "灯塔线索待确认。"}],
            characters=["顾迟"],
            locations=["灯塔"],
            plot_threads=["父亲地图之谜"],
            created_at="2026-05-22T00:00:00+00:00",
        )
    )
    state_store.save_analysis_baseline(
        StoryStateSnapshot(
            story_state_id="state_base",
            work_id=work.id,
            source_initialization_id="init_1",
            source_job_id="job_1",
            latest_chapter_id=chapter.id.value,
            latest_chapter_version=chapter.version,
            current_position_summary="顾迟仍在灯塔内调查父亲地图。",
            active_characters=["顾迟"],
            active_locations=["灯塔"],
            unresolved_threads=["地图的指向"],
            continuity_notes=["baseline"],
            source_snapshot_id="memory_base",
            created_at="2026-05-22T00:00:00+00:00",
        )
    )
    candidate_store.save(
        CandidateDraft(
            candidate_draft_id="cd_memory_gate",
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="sess_memory_gate",
            source_context_pack_id="cp_1",
            source_job_id="job_1",
            status=CandidateDraftStatus.ACCEPTED,
            selected_version_id="ver_memory_gate",
            accepted_version_id="ver_memory_gate",
            content="顾迟意识到父亲地图指向了废弃航道。",
            content_preview="顾迟意识到父亲地图指向了废弃航道。",
            word_count=1,
            char_count=18,
            validation_status=CandidateDraftValidationStatus.PASSED,
            writer_model_role="writer",
            provider_name="fake",
            model_name="fake-writer",
            created_by="workflow",
            created_at="2026-05-22T00:00:00+00:00",
            updated_at="2026-05-22T00:00:00+00:00",
        )
    )
    candidate_store.save_version(
        CandidateDraftVersion(
            candidate_version_id="ver_memory_gate",
            candidate_draft_id="cd_memory_gate",
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="sess_memory_gate",
            version_no=1,
            status=CandidateDraftVersionStatus.ACCEPTED,
            content="顾迟意识到父亲地图指向了废弃航道。",
            content_summary="发现地图指向废弃航道",
            word_count=1,
            created_by="writer_agent",
            created_at="2026-05-22T00:00:00+00:00",
            updated_at="2026-05-22T00:00:00+00:00",
        )
    )
    review_store.save(
        AIReviewResult(
            review_id="rv_memory_gate",
            work_id=work.id,
            chapter_id=chapter.id.value,
            candidate_draft_id="cd_memory_gate",
            status=AIReviewStatus.COMPLETED,
            summary="需要同步更新地图线索与当前推进状态。",
            warnings=[],
            issues=[
                {
                    "issue_id": "issue_continuity_1",
                    "severity": "medium",
                    "category": "continuity",
                    "message": "地图线索已经被明确，但当前状态摘要仍未更新。",
                    "suggestion": "将当前状态改为顾迟已确认地图指向废弃航道。",
                }
            ],
            suggestions=["补齐记忆更新"],
            risk_level=AIReviewRiskLevel.MEDIUM,
            consistency_notes=["需要同步 story state"],
            style_notes=[],
            logic_notes=[],
            reviewer_model_role="reviewer",
            provider_name="fake",
            model_name="fake-reviewer",
            created_at="2026-05-22T00:00:00+00:00",
            metadata={},
        )
    )
    return bundle, work.id, chapter.id.value


def test_memory_review_gate_generates_review_suggestions_and_supports_approve_apply_rollback(tmp_path: Path) -> None:
    bundle, work_id, chapter_id = _seed_review_context(tmp_path)
    service = bundle["service"]
    trace_service = bundle["trace_service"]

    gate = service.generate_from_review("rv_memory_gate")
    assert gate.state == MemoryGateState.OPEN

    listed = service.list_gates(work_id=work_id, chapter_id=chapter_id)
    assert listed[0].state == MemoryGateState.WAITING_FOR_USER

    suggestions = service.list_gate_suggestions(gate.gate_id)
    assert len(suggestions) == 2
    assert {item.target_memory_type for item in suggestions} == {MemoryTargetType.STORY_MEMORY, MemoryTargetType.STORY_STATE}
    assert {item.status for item in suggestions} == {MemorySuggestionStatus.SHOWN}

    state_suggestion = next(item for item in suggestions if item.target_memory_type == MemoryTargetType.STORY_STATE)
    memory_suggestion = next(item for item in suggestions if item.target_memory_type == MemoryTargetType.STORY_MEMORY)

    partial_gate = service.approve_suggestion(
        gate.gate_id,
        state_suggestion.id,
        idempotency_key="s9-approve-state-1",
        user_id="ui-user",
        user_action=True,
        request_id="req_memory_approve_1",
        trace_id="trace_memory_approve_1",
    )
    assert partial_gate.state == MemoryGateState.PARTIALLY_APPROVED
    approved_state_suggestion = service.get_suggestion(state_suggestion.id)
    assert approved_state_suggestion.decision == MemorySuggestionDecisionType.APPROVED
    assert approved_state_suggestion.status == MemorySuggestionStatus.ACCEPTED

    approved_gate = service.edit_and_approve_suggestion(
        gate.gate_id,
        memory_suggestion.id,
        idempotency_key="s9-edit-approve-memory-1",
        user_id="ui-user",
        user_action=True,
        request_id="req_memory_approve_2",
        trace_id="trace_memory_approve_2",
        proposed_value_summary="顾迟已经确认地图指向废弃航道，并将其记为父亲遗留的关键航线线索。",
        decision_note="补全记忆摘要",
    )
    assert approved_gate.state == MemoryGateState.APPROVED
    edited_memory_suggestion = service.get_suggestion(memory_suggestion.id)
    assert edited_memory_suggestion.decision == MemorySuggestionDecisionType.EDITED_APPROVED
    assert edited_memory_suggestion.status == MemorySuggestionStatus.EDITED
    event_types = [item.event_type for item in trace_service.list_events("trace_memory_approve_2")]
    assert "memory_revision_created" in event_types

    apply_result = service.apply_gate(
        gate.gate_id,
        user_id="ui-user",
        user_action=True,
        idempotency_key="s9-apply-1",
        request_id="req_memory_apply",
        trace_id="trace_memory_apply",
    )
    assert apply_result["gate"].state == MemoryGateState.APPLIED
    assert {item["apply_status"] for item in apply_result["apply_results"]} == {"success"}

    latest_memory = bundle["memory_store"].get_latest_snapshot_by_work(work_id)
    latest_state = bundle["state_store"].get_latest_analysis_baseline_by_work(work_id)
    assert latest_memory is not None
    assert latest_state is not None
    assert latest_memory.snapshot_id != "memory_base"
    assert latest_state.story_state_id != "state_base"
    assert "关键航线线索" in latest_memory.global_summary
    assert "废弃航道" in latest_state.current_position_summary

    revisions = service.list_revisions(work_id=work_id, chapter_id=chapter_id)
    applied_memory_revision = next(item for item in revisions if item["target_asset"] == "story_memory")
    assert applied_memory_revision["status"] == MemoryRevisionStatus.APPLIED.value

    rollback_revision = service.rollback_revision(
        applied_memory_revision["revision_id"],
        user_id="ui-user",
        user_action=True,
        idempotency_key="s9-rollback-1",
        request_id="req_memory_rollback",
        trace_id="trace_memory_rollback",
    )
    assert rollback_revision["revision_type"] == MemoryRevisionRecordType.ROLLBACK.value
    assert rollback_revision["status"] == MemoryRevisionStatus.APPLIED.value

    rolled_back_memory = bundle["memory_store"].get_latest_snapshot_by_work(work_id)
    assert rolled_back_memory is not None
    assert rolled_back_memory.global_summary == "顾迟尚未确认地图的真实用途。"


def test_memory_review_gate_defer_rejects_invalid_apply_and_preserves_gate_waiting_state(tmp_path: Path) -> None:
    bundle, work_id, chapter_id = _seed_review_context(tmp_path)
    service = bundle["service"]

    gate = service.generate_from_review("rv_memory_gate")
    suggestion = service.list_gate_suggestions(gate.gate_id)[0]

    deferred_gate = service.defer_suggestion(
        gate.gate_id,
        suggestion.id,
        idempotency_key="s9-defer-1",
        user_id="ui-user",
        user_action=True,
        request_id="req_memory_defer",
        trace_id="trace_memory_defer",
        decision_note="稍后处理",
    )
    assert deferred_gate.state == MemoryGateState.WAITING_FOR_USER
    deferred_suggestion = service.get_suggestion(suggestion.id)
    assert deferred_suggestion.status == MemorySuggestionStatus.SHOWN
    assert deferred_suggestion.decision == MemorySuggestionDecisionType.DEFERRED

    try:
        service.apply_gate(
            gate.gate_id,
            user_id="ui-user",
            user_action=True,
            idempotency_key="s9-apply-deferred",
            request_id="req_memory_apply_deferred",
            trace_id="trace_memory_apply_deferred",
        )
    except ValueError as exc:
        assert str(exc) == "memory_revision_apply_blocked"
    else:
        raise AssertionError("apply on deferred gate should fail")

    service.reject_suggestion(
        gate.gate_id,
        suggestion.id,
        idempotency_key="s9-reject-1",
        user_id="ui-user",
        user_action=True,
        request_id="req_memory_reject",
        trace_id="trace_memory_reject",
        decision_note="当前不采纳",
    )
    rejected = service.get_suggestion(suggestion.id)
    assert rejected.status == MemorySuggestionStatus.REJECTED
    assert rejected.decision == MemorySuggestionDecisionType.REJECTED
    assert service.list_gates(work_id=work_id, chapter_id=chapter_id)


def test_memory_review_gate_rejecting_one_suggestion_does_not_close_gate_when_others_remain(tmp_path: Path) -> None:
    bundle, work_id, chapter_id = _seed_review_context(tmp_path)
    service = bundle["service"]

    gate = service.generate_from_review("rv_memory_gate")
    suggestions = service.list_gate_suggestions(gate.gate_id)
    assert len(suggestions) == 2

    updated_gate = service.reject_suggestion(
        gate.gate_id,
        suggestions[0].id,
        idempotency_key="s9-reject-partial-1",
        user_id="ui-user",
        user_action=True,
        request_id="req_memory_reject_partial",
        trace_id="trace_memory_reject_partial",
        decision_note="先拒绝其中一条",
    )

    assert updated_gate.state == MemoryGateState.WAITING_FOR_USER
    refreshed = service.get_gate(gate.gate_id)
    assert refreshed.state == MemoryGateState.WAITING_FOR_USER
    remaining = service.get_suggestion(suggestions[1].id)
    assert remaining.status == MemorySuggestionStatus.SHOWN


def test_memory_review_gate_rollback_is_blocked_when_target_memory_version_has_changed(tmp_path: Path) -> None:
    bundle, work_id, chapter_id = _seed_review_context(tmp_path)
    service = bundle["service"]

    gate = service.generate_from_review("rv_memory_gate")
    suggestions = service.list_gate_suggestions(gate.gate_id)
    for suggestion in suggestions:
        service.approve_suggestion(
            gate.gate_id,
            suggestion.id,
            idempotency_key=f"idem_{suggestion.id}",
            user_id="ui-user",
            user_action=True,
            request_id=f"req_{suggestion.id}",
            trace_id=f"trace_{suggestion.id}",
        )

    service.apply_gate(
        gate.gate_id,
        user_id="ui-user",
        user_action=True,
        idempotency_key="s9-apply-before-rollback-block",
        request_id="req_memory_apply_before_rollback_block",
        trace_id="trace_memory_apply_before_rollback_block",
    )
    revisions = service.list_revisions(work_id=work_id, chapter_id=chapter_id)
    applied_memory_revision = next(item for item in revisions if item["target_asset"] == "story_memory")

    latest_memory = bundle["memory_store"].get_latest_snapshot_by_work(work_id)
    assert latest_memory is not None
    bundle["memory_store"].save_snapshot(
        latest_memory.model_copy(
            update={
                "snapshot_id": "memory_external_change",
                "global_summary": "外部流程已修改正式记忆。",
                "created_at": "2026-12-31T23:59:59+00:00",
            }
        )
    )

    try:
        service.rollback_revision(
            applied_memory_revision["revision_id"],
            user_id="ui-user",
            user_action=True,
            idempotency_key="s9-rollback-version-blocked",
            request_id="req_memory_rollback_version_blocked",
            trace_id="trace_memory_rollback_version_blocked",
        )
    except ValueError as exc:
        assert str(exc) == "memory_revision_apply_blocked"
    else:
        raise AssertionError("rollback should be blocked when target memory version changed")


def test_memory_review_gate_fail_safe_blocks_high_risk_actions_when_critical_audit_fails(tmp_path: Path) -> None:
    bundle, work_id, chapter_id = _seed_review_context(tmp_path)
    from application.services.ai.memory_review_gate_service import MemoryReviewGateService

    service = MemoryReviewGateService(
        memory_review_repository=bundle["review_gate_store"],
        story_memory_repository=bundle["memory_store"],
        story_state_repository=bundle["state_store"],
        ai_review_repository=bundle["review_store"],
        candidate_draft_repository=bundle["candidate_store"],
        conflict_guard_service=None,
        trace_service=_CriticalAuditTraceStub(),
    )
    gate = service.generate_from_review("rv_memory_gate")
    suggestions = service.list_gate_suggestions(gate.gate_id)

    try:
        service.approve_suggestion(
            gate.gate_id,
            suggestions[0].id,
            idempotency_key="s9-audit-approve-fail-1",
            user_id="ui-user",
            user_action=True,
            request_id="req_memory_audit_fail_approve",
            trace_id="trace_memory_audit_fail_approve",
        )
    except ValueError as exc:
        assert str(exc) == "critical_audit_write_failed"
    else:
        raise AssertionError("critical audit failure should block approve_memory")

    assert service.get_suggestion(suggestions[0].id).decision == MemorySuggestionDecisionType.NONE
