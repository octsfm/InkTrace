from __future__ import annotations

from pathlib import Path

from application.services.ai.ai_suggestion_service import AISuggestionService
from application.services.ai.agent_trace_service import AgentTraceService
from application.services.ai.candidate_rewrite_service import CandidateRewriteService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    AIReviewResult,
    AIReviewRiskLevel,
    AIReviewStatus,
    AISuggestion,
    AISuggestionAction,
    AISuggestionActionType,
    AISuggestionDecisionType,
    AISuggestionPriority,
    AISuggestionSeverity,
    AISuggestionSource,
    AISuggestionStatus,
    AISuggestionTarget,
    AISuggestionType,
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
    CandidateDraftVersion,
    CandidateDraftVersionStatus,
    ReviewIssue,
)
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_review_store import FileAIReviewStore
from infrastructure.database.repositories.ai.file_ai_suggestion_store import FileAISuggestionStore
from infrastructure.database.repositories.ai.file_agent_trace_store import FileAgentTraceStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.ai.providers.fake_rewriter import FakeRewriter


def _build_services(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_suggestion.json")
    review_store = FileAIReviewStore(tmp_path / "review_suggestion.json")
    suggestion_store = FileAISuggestionStore(tmp_path / "ai_suggestions.json")
    trace_store = FileAgentTraceStore(tmp_path / "trace_suggestion.json")
    trace_service = AgentTraceService(repository=trace_store)
    rewrite_service = CandidateRewriteService(
        candidate_draft_repository=candidate_store,
        ai_review_repository=review_store,
        rewriter=FakeRewriter(),
    )
    suggestion_service = AISuggestionService(
        ai_suggestion_repository=suggestion_store,
        ai_review_repository=review_store,
        candidate_draft_repository=candidate_store,
        candidate_rewrite_service=rewrite_service,
        trace_service=trace_service,
    )
    return work_service, chapter_service, candidate_store, review_store, suggestion_store, suggestion_service, trace_service


def _seed_review_context(tmp_path: Path):
    work_service, chapter_service, candidate_store, review_store, suggestion_store, suggestion_service, trace_service = _build_services(tmp_path)
    work = work_service.create_work("P1-S7 Suggestion", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    draft = candidate_store.save(
        CandidateDraft(
            candidate_draft_id="cd_s1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="agent_session_reviewer",
            writing_task_id="wt_1",
            direction_plan_snapshot_id="snap_1",
            source_context_pack_id="cp_1",
            source_job_id="job_1",
            status=CandidateDraftStatus.PENDING_REVIEW,
            selected_version_id="ver_1",
            latest_version_no=1,
            content="顾迟在灯塔醒来，尚未发现父亲留下的地图。",
            content_preview="顾迟在灯塔醒来",
            word_count=1,
            char_count=20,
            validation_status=CandidateDraftValidationStatus.PASSED,
            created_by="workflow",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
            trace_id="trace_suggestion_service",
        )
    )
    candidate_store.save_version(
        CandidateDraftVersion(
            candidate_version_id="ver_1",
            candidate_draft_id=draft.candidate_draft_id,
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="agent_session_writer",
            version_no=1,
            status=CandidateDraftVersionStatus.REVIEW_COMPLETED,
            content=draft.content,
            content_summary=draft.content_preview,
            word_count=1,
            writing_task_id="wt_1",
            direction_plan_snapshot_id="snap_1",
            source_context_pack_id="cp_1",
            created_by="writer_agent",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    review = review_store.save(
        AIReviewResult(
            review_id="rv_s1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            candidate_draft_id=draft.candidate_draft_id,
            status=AIReviewStatus.COMPLETED,
            summary="建议补强父亲线索，并提示当前版本存在连续性风险。",
            issues=[
                ReviewIssue(
                    issue_id="issue_1",
                    severity="high",
                    category="continuity",
                    message="父亲线索出现过晚。",
                    suggestion="将地图线索提前到开篇。",
                )
            ],
            suggestions=["增加地图伏笔", "控制连续性风险"],
            risk_level=AIReviewRiskLevel.HIGH,
            created_at="2026-05-21T00:05:00+00:00",
            metadata={},
        )
    )
    return work, chapter, draft, review, suggestion_store, suggestion_service, trace_service


def test_ai_suggestion_service_generates_structured_suggestions_from_review_and_marks_shown(tmp_path: Path) -> None:
    _, chapter, draft, review, suggestion_store, suggestion_service, _ = _seed_review_context(tmp_path)

    batch = suggestion_service.generate_from_review(review.review_id)
    items = suggestion_service.list_suggestions(work_id=draft.work_id, chapter_id=chapter.id.value)

    assert batch.generated_count >= 2
    assert len(items) >= 2
    assert items[0].status == AISuggestionStatus.SHOWN
    assert any(item.suggestion_type == AISuggestionType.REWRITE_SUGGESTION for item in items)
    assert any(item.suggestion_type == AISuggestionType.RISK_WARNING for item in items)
    stored = suggestion_store.get(items[0].suggestion_id)
    assert stored.summary


def test_ai_suggestion_service_accept_dismiss_and_convert_follow_type_matrix(tmp_path: Path) -> None:
    _, _, draft, review, _, suggestion_service, trace_service = _seed_review_context(tmp_path)
    suggestion_service.generate_from_review(review.review_id)
    items = suggestion_service.list_suggestions(work_id=draft.work_id, chapter_id=draft.chapter_id)
    rewrite_item = next(item for item in items if item.suggestion_type == AISuggestionType.REWRITE_SUGGESTION)
    risk_item = next(item for item in items if item.suggestion_type == AISuggestionType.RISK_WARNING)

    accepted = suggestion_service.accept_suggestion(
        rewrite_item.suggestion_id,
        user_id="ui-user",
        user_action=True,
    )
    converted = suggestion_service.convert_suggestion(
        rewrite_item.suggestion_id,
        user_id="ui-user",
        user_action=True,
        idempotency_key="s7-convert-1",
    )
    dismissed = suggestion_service.dismiss_suggestion(
        risk_item.suggestion_id,
        user_id="ui-user",
        user_action=True,
        note="先人工关注",
    )

    assert accepted.decision == AISuggestionDecisionType.ACCEPTED
    assert accepted.status == AISuggestionStatus.ACCEPTED
    assert converted.status == AISuggestionStatus.CONVERTED
    assert converted.action.action_type == AISuggestionActionType.CONVERT_TO_REWRITE_INSTRUCTION
    assert converted.action.action_payload_ref.startswith("rewrite_request:")
    assert dismissed.decision == AISuggestionDecisionType.DISMISSED
    assert dismissed.status == AISuggestionStatus.DISMISSED
    trace_events = [item.event_type for item in trace_service.list_events(rewrite_item.trace_id)]
    assert "suggestion_accepted" in trace_events
    assert "suggestion_dismissed" in trace_events

    try:
        suggestion_service.convert_suggestion(
            risk_item.suggestion_id,
            user_id="ui-user",
            user_action=True,
            idempotency_key="s7-convert-risk",
        )
    except ValueError as exc:
        assert str(exc) == "suggestion_convert_forbidden"
    else:
        raise AssertionError("risk_warning should not be convertible")


def test_ai_suggestion_service_convert_conflict_resolution_suggestion_to_conflict_ref(tmp_path: Path) -> None:
    _, _, draft, _, suggestion_store, suggestion_service, _ = _seed_review_context(tmp_path)
    conflict_suggestion = suggestion_store.save(
        AISuggestion(
            suggestion_id="ais_conflict_1",
            work_id=draft.work_id,
            chapter_id=draft.chapter_id,
            agent_session_id=draft.agent_session_id,
            source=AISuggestionSource(
                source_type="conflict_guard_record",
                source_ref_id="cgr_1",
                source_agent_type="conflict_guard",
                source_agent_session_id=draft.agent_session_id,
                source_version_id="ver_1",
            ),
            target=AISuggestionTarget(
                target_type="conflict_guard_record",
                target_ref_id="cgr_1",
                target_scope="record",
                target_snapshot_ref="ver_1",
            ),
            suggestion_type=AISuggestionType.CONFLICT_RESOLUTION_SUGGESTION,
            severity=AISuggestionSeverity.HIGH,
            priority=AISuggestionPriority.HIGH,
            title="存在资产冲突",
            summary="建议先进入冲突处理。",
            rationale="ConflictGuard 已检测到 warning。",
            proposed_action="打开冲突处理入口",
            status=AISuggestionStatus.SHOWN,
            created_by="conflict_guard",
            created_at="2026-05-21T00:10:00+00:00",
            updated_at="2026-05-21T00:10:00+00:00",
            action=AISuggestionAction(
                action_type=AISuggestionActionType.OPEN_CONFLICT_RESOLUTION,
                requires_user_action=True,
                action_status="pending",
            ),
            metadata={"conflict_record_id": "cgr_1", "candidate_draft_id": draft.candidate_draft_id},
        )
    )

    converted = suggestion_service.convert_suggestion(
        conflict_suggestion.suggestion_id,
        user_id="ui-user",
        user_action=True,
        idempotency_key="s8-conflict-convert-1",
    )

    assert converted.status == AISuggestionStatus.CONVERTED
    assert converted.decision == AISuggestionDecisionType.CONVERTED
    assert converted.action.action_type == AISuggestionActionType.OPEN_CONFLICT_RESOLUTION
    assert converted.action.action_payload_ref == "conflict_guard:cgr_1"
