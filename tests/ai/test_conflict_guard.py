from __future__ import annotations

from pathlib import Path

from application.services.ai.agent_trace_service import AgentTraceService
from application.services.ai.conflict_guard_service import ConflictGuardService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    AISuggestionActionType,
    AISuggestionType,
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
    CandidateDraftVersion,
    CandidateDraftVersionStatus,
    ConflictRecordStatus,
    ConflictSeverity,
    ConflictType,
    WritingTask,
    WritingTaskStatus,
)
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_suggestion_store import FileAISuggestionStore
from infrastructure.database.repositories.ai.file_agent_trace_store import FileAgentTraceStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_conflict_guard_store import FileConflictGuardStore
from infrastructure.database.repositories.ai.file_direction_plan_store import FileDirectionPlanStore


def _build_services(tmp_path: Path, *, allow_override_blocking: bool = False):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    conflict_store = FileConflictGuardStore(tmp_path / "conflict_guard.json")
    suggestion_store = FileAISuggestionStore(tmp_path / "conflict_suggestions.json")
    direction_store = FileDirectionPlanStore(tmp_path / "direction_plan.json")
    trace_store = FileAgentTraceStore(tmp_path / "conflict_trace.json")
    trace_service = AgentTraceService(repository=trace_store)
    guard_service = ConflictGuardService(
        conflict_guard_repository=conflict_store,
        candidate_draft_repository=candidate_store,
        chapter_service=chapter_service,
        ai_suggestion_repository=suggestion_store,
        direction_plan_repository=direction_store,
        trace_service=trace_service,
        allow_override_blocking=allow_override_blocking,
    )
    return work_service, chapter_service, candidate_store, conflict_store, suggestion_store, direction_store, guard_service, trace_service


def _seed_candidate(
    tmp_path: Path,
    *,
    version_warning_codes: list[str] | None = None,
    stale_status: str = "fresh",
    allow_override_blocking: bool = False,
):
    work_service, chapter_service, candidate_store, conflict_store, suggestion_store, direction_store, guard_service, trace_service = _build_services(
        tmp_path,
        allow_override_blocking=allow_override_blocking,
    )
    work = work_service.create_work("Conflict Work", "Author")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="Chapter One",
        content="Original chapter text.",
        expected_version=1,
    )
    draft = candidate_store.save(
        CandidateDraft(
            candidate_draft_id="cd_conflict",
            work_id=work.id,
            chapter_id=chapter.id.value,
            source_context_pack_id="cp_1",
            source_job_id="job_1",
            writing_task_id="wt_1",
            status=CandidateDraftStatus.ACCEPTED,
            selected_version_id="ver_1",
            accepted_version_id="ver_1",
            content="Candidate continuation.",
            content_preview="Candidate continuation.",
            word_count=2,
            char_count=23,
            validation_status=CandidateDraftValidationStatus.PASSED,
            writer_model_role="writer",
            provider_name="fake",
            model_name="fake-writer",
            created_by="workflow",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    candidate_store.save_version(
        CandidateDraftVersion(
            candidate_version_id="ver_1",
            candidate_draft_id=draft.candidate_draft_id,
            work_id=draft.work_id,
            chapter_id=draft.chapter_id,
            version_no=1,
            status=CandidateDraftVersionStatus.ACCEPTED,
            content="Candidate continuation.",
            content_summary="Candidate continuation.",
            word_count=2,
            warning_codes=list(version_warning_codes or []),
            stale_status=stale_status,
            created_by="writer_agent",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    direction_store.save_writing_task(
        WritingTask(
            writing_task_id="wt_1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            target_chapter_id=chapter.id.value,
            status=WritingTaskStatus.READY,
            writing_goal="推进本章",
            must_include=[],
            must_not_include=["直接揭晓终局"],
            required_beats=[],
            created_by="planner_agent",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    return chapter_service, candidate_store, conflict_store, suggestion_store, direction_store, guard_service, draft, chapter, trace_service


def test_conflict_guard_precheck_creates_blocking_apply_version_conflict_record(tmp_path: Path) -> None:
    _, _, conflict_store, _, _, guard_service, draft, chapter, _ = _seed_candidate(tmp_path)

    result = guard_service.precheck_apply_conflicts(
        candidate_draft_id=draft.candidate_draft_id,
        candidate_version_id="ver_1",
        expected_chapter_version=chapter.version + 1,
        request_id="req_conflict_precheck",
        trace_id="trace_conflict_precheck",
    )

    assert result.blocking_count == 1
    assert result.total_conflicts == 1
    assert result.record_refs
    record = conflict_store.get_record(result.record_refs[0])
    assert record.conflict_type == ConflictType.APPLY_VERSION_CONFLICT
    assert record.severity == ConflictSeverity.BLOCKING
    assert record.status == ConflictRecordStatus.DETECTED
    assert record.candidate_draft_id == draft.candidate_draft_id
    assert record.candidate_version_id == "ver_1"


def test_conflict_guard_precheck_creates_warning_record_and_conflict_resolution_suggestion_for_stale_inputs(tmp_path: Path) -> None:
    _, _, conflict_store, suggestion_store, _, guard_service, draft, chapter, _ = _seed_candidate(
        tmp_path,
        version_warning_codes=["context_pack_degraded"],
        stale_status="stale",
    )

    result = guard_service.precheck_apply_conflicts(
        candidate_draft_id=draft.candidate_draft_id,
        candidate_version_id="ver_1",
        expected_chapter_version=chapter.version,
        request_id="req_conflict_warning",
        trace_id="trace_conflict_warning",
    )
    items = suggestion_store.list_suggestions(work_id=draft.work_id, chapter_id=draft.chapter_id)

    assert result.blocking_count == 0
    assert result.warning_count == 1
    assert result.total_conflicts == 1
    record = conflict_store.get_record(result.record_refs[0])
    assert record.conflict_type == ConflictType.CANDIDATE_VERSION_CONFLICT
    assert record.severity == ConflictSeverity.WARNING
    assert record.warning_codes == ["context_pack_degraded"]
    assert record.summary
    assert len(items) == 1
    assert items[0].suggestion_type == AISuggestionType.CONFLICT_RESOLUTION_SUGGESTION
    assert items[0].target.target_ref_id == record.record_id
    assert items[0].action.action_type == AISuggestionActionType.OPEN_CONFLICT_RESOLUTION


def test_conflict_guard_async_detection_failure_is_recorded_as_failed_without_blocking_apply(tmp_path: Path) -> None:
    _, candidate_store, conflict_store, _, _, guard_service, draft, _, _ = _seed_candidate(tmp_path)
    version = candidate_store.get_version("ver_1").model_copy(
        update={
            "warning_codes": ["detection_timeout"],
            "stale_status": "fresh",
        }
    )
    candidate_store.save_version(version)

    result = guard_service.record_async_detection_failure(
        candidate_draft_id=draft.candidate_draft_id,
        candidate_version_id="ver_1",
        error_code="detection_timeout",
        safe_message="检测结果可能不完整",
        request_id="req_conflict_async_failed",
        trace_id="trace_conflict_async_failed",
    )

    assert result.detection_status.value == "failed"
    assert result.total_conflicts == 1
    assert result.blocking_count == 0
    record = conflict_store.get_record(result.record_refs[0])
    assert record.status == ConflictRecordStatus.FAILED
    assert record.severity == ConflictSeverity.WARNING
    assert record.conflict_type == ConflictType.CANDIDATE_VERSION_CONFLICT
    assert record.summary == "检测结果可能不完整"
    assert record.warning_codes == ["detection_timeout"]


def test_conflict_guard_precheck_creates_info_record_for_fresh_warning_free_candidate(tmp_path: Path) -> None:
    _, _, conflict_store, _, _, guard_service, draft, chapter, _ = _seed_candidate(tmp_path)

    result = guard_service.precheck_apply_conflicts(
        candidate_draft_id=draft.candidate_draft_id,
        candidate_version_id="ver_1",
        expected_chapter_version=chapter.version,
        request_id="req_conflict_info",
        trace_id="trace_conflict_info",
    )

    assert result.blocking_count == 0
    assert result.warning_count == 0
    assert result.info_count == 1
    record = conflict_store.get_record(result.record_refs[0])
    assert record.severity == ConflictSeverity.INFO
    assert record.conflict_type == ConflictType.CANDIDATE_VERSION_CONFLICT
    assert "未发现阻断性冲突" in record.summary


def test_conflict_guard_precheck_creates_direction_plan_conflict_when_candidate_hits_must_not_include(tmp_path: Path) -> None:
    _, candidate_store, conflict_store, suggestion_store, _, guard_service, draft, chapter, _ = _seed_candidate(tmp_path)
    candidate_store.save_version(
        candidate_store.get_version("ver_1").model_copy(
            update={
                "content": "候选稿中直接揭晓终局，导致计划失效。",
                "content_summary": "直接揭晓终局",
            }
        )
    )

    result = guard_service.precheck_apply_conflicts(
        candidate_draft_id=draft.candidate_draft_id,
        candidate_version_id="ver_1",
        expected_chapter_version=chapter.version,
        request_id="req_conflict_direction_plan",
        trace_id="trace_conflict_direction_plan",
    )

    assert result.warning_count == 1
    records = [conflict_store.get_record(record_id) for record_id in result.record_refs]
    direction_record = next(item for item in records if item.conflict_type == ConflictType.DIRECTION_PLAN_CONFLICT)
    assert direction_record.severity == ConflictSeverity.WARNING
    assert "must_not_include" in direction_record.evidence_refs[0]
    assert direction_record.warning_codes == ["writing_task_forbidden_item_hit"]
    suggestions = suggestion_store.list_suggestions(work_id=draft.work_id, chapter_id=draft.chapter_id)
    assert any(item.target.target_ref_id == direction_record.record_id for item in suggestions)


def test_conflict_guard_precheck_creates_direction_plan_conflicts_when_required_items_are_missing(tmp_path: Path) -> None:
    _, candidate_store, conflict_store, suggestion_store, direction_store, guard_service, draft, chapter, _ = _seed_candidate(tmp_path)
    direction_store.save_writing_task(
        direction_store.get_writing_task("wt_1").model_copy(
            update={
                "must_include": ["钟声", "旧标记"],
                "required_beats": ["锁定钟声来源"],
            }
        )
    )
    candidate_store.save_version(
        candidate_store.get_version("ver_1").model_copy(
            update={
                "content": "候选稿只描写了海风与雾气，没有任何关键线索。",
                "content_summary": "缺少关键节拍",
            }
        )
    )

    result = guard_service.precheck_apply_conflicts(
        candidate_draft_id=draft.candidate_draft_id,
        candidate_version_id="ver_1",
        expected_chapter_version=chapter.version,
        request_id="req_conflict_required_items",
        trace_id="trace_conflict_required_items",
    )

    records = [conflict_store.get_record(record_id) for record_id in result.record_refs]
    direction_records = [item for item in records if item.conflict_type == ConflictType.DIRECTION_PLAN_CONFLICT]
    assert result.warning_count == 3
    assert len(direction_records) == 3
    assert {item.warning_codes[0] for item in direction_records} == {
        "writing_task_required_item_missing",
        "writing_task_required_beat_missing",
    }
    suggestions = suggestion_store.list_suggestions(work_id=draft.work_id, chapter_id=draft.chapter_id)
    assert len([item for item in suggestions if item.suggestion_type == AISuggestionType.CONFLICT_RESOLUTION_SUGGESTION]) >= 2


def test_conflict_guard_records_resolve_and_override_trace_events(tmp_path: Path) -> None:
    _, _, conflict_store, _, _, guard_service, draft, chapter, trace_service = _seed_candidate(
        tmp_path,
        version_warning_codes=["context_pack_degraded"],
        stale_status="stale",
        allow_override_blocking=True,
    )

    result = guard_service.precheck_apply_conflicts(
        candidate_draft_id=draft.candidate_draft_id,
        candidate_version_id="ver_1",
        expected_chapter_version=chapter.version,
        request_id="req_conflict_trace",
        trace_id="trace_conflict_trace",
    )
    warning_record = conflict_store.get_record(result.record_refs[0])
    guard_service.decide_record(
        warning_record.record_id,
        decision="resolved",
        user_id="ui-user",
        user_action=True,
        request_id="req_conflict_resolved",
        trace_id="trace_conflict_trace",
        note="已人工确认",
    )

    blocking_record = conflict_store.save_record(
        warning_record.model_copy(
            update={
                "record_id": "cgr_override_allowed",
                "conflict_type": ConflictType.UNKNOWN_CONFLICT,
                "severity": ConflictSeverity.BLOCKING,
                "status": ConflictRecordStatus.ACKNOWLEDGED,
                "trace_id": "trace_conflict_trace",
            }
        )
    )
    guard_service.decide_record(
        blocking_record.record_id,
        decision="overridden",
        user_id="ui-user",
        user_action=True,
        request_id="req_conflict_overridden",
        trace_id="trace_conflict_trace",
        note="允许覆盖",
    )

    event_types = [item.event_type for item in trace_service.list_events("trace_conflict_trace")]
    assert "conflict_resolved" in event_types
    assert "conflict_overridden" in event_types
