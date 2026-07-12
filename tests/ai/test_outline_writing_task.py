from __future__ import annotations

from datetime import UTC, datetime
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from application.services.ai.ai_suggestion_service import AISuggestionService
from application.services.ai.planning_api_service import PlanningAPIService
from domain.entities.ai.models import (
    AISuggestion,
    AISuggestionAction,
    AISuggestionActionType,
    AISuggestionPriority,
    AISuggestionSeverity,
    AISuggestionSource,
    AISuggestionStatus,
    AISuggestionTarget,
    AISuggestionType,
    ChapterPlan,
    DirectionPlanStatus,
    WritingTaskStatus,
)
from infrastructure.database.repositories.ai.file_ai_suggestion_store import FileAISuggestionStore
from infrastructure.database.repositories.ai.file_chapter_plan_store import FileChapterPlanStore
from infrastructure.database.repositories.ai.file_direction_plan_store import FileDirectionPlanStore
from domain.entities.writing_assets import ChapterOutline
from domain.value_objects.outline_snapshot import outline_content_hash


class _ChapterAssets:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.outline = ChapterOutline("co-1", "chapter-1", "本章原始大纲", [], 5, now, now)

    def get_chapter_outline(self, chapter_id: str) -> ChapterOutline:
        if chapter_id != self.outline.chapter_id:
            raise ValueError("chapter_not_found")
        return self.outline


class _TraceSpy:
    def __init__(self, *, fail_at: str = "") -> None:
        self.fail_at = fail_at
        self.calls: list[tuple[str, dict[str, object]]] = []

    def ensure_operation_trace(self, **kwargs):
        self.calls.append(("ensure", dict(kwargs)))
        if self.fail_at == "ensure":
            raise RuntimeError("trace ensure failed")
        return SimpleNamespace(trace_id=kwargs["trace_id"])

    def record_audit_event(self, **kwargs):
        self.calls.append(("audit", dict(kwargs)))
        if self.fail_at == "audit":
            raise RuntimeError("trace event write failed")
        return SimpleNamespace(event_type=kwargs["event_type"])


class _BlockingTrace(_TraceSpy):
    def __init__(self) -> None:
        super().__init__()
        self.first_audit_entered = Event()
        self.second_audit_entered = Event()
        self.release_first_audit = Event()

    def record_audit_event(self, **kwargs):
        result = super().record_audit_event(**kwargs)
        audit_count = sum(1 for name, _ in self.calls if name == "audit")
        if audit_count == 1:
            self.first_audit_entered.set()
            self.release_first_audit.wait(timeout=2)
        else:
            self.second_audit_entered.set()
        return result


def _confirmed_plan(store: FileChapterPlanStore) -> ChapterPlan:
    return store.save(
        ChapterPlan(
            chapter_plan_id="plan-1",
            work_id="work-1",
            chapter_id="chapter-1",
            direction_proposal_id="direction-1",
            selected_option_id="option-1",
            selection_id="selection-1",
            agent_session_id="session-1",
            source_context_pack_id="context-1",
            status=DirectionPlanStatus.CONFIRMED,
            version=2,
            plan_summary="主角在灯塔找到线索",
            stale_status="fresh",
            created_at="2026-07-11T00:00:00+00:00",
            updated_at="2026-07-11T00:00:00+00:00",
        )
    )


def _suggestion(store: FileAISuggestionStore) -> AISuggestion:
    return store.save(
        AISuggestion(
            suggestion_id="ais-writing-task-1",
            work_id="work-1",
            chapter_id="chapter-1",
            source=AISuggestionSource(source_type="outline_assist", source_ref_id="ais-writing-task-1"),
            target=AISuggestionTarget(target_type="chapter_outline", target_ref_id="chapter-1"),
            suggestion_type=AISuggestionType.WRITING_TASK_SUGGESTION,
            severity=AISuggestionSeverity.MEDIUM,
            priority=AISuggestionPriority.MEDIUM,
            title="本章写作要点",
            status=AISuggestionStatus.GENERATED,
            action=AISuggestionAction(
                action_type=AISuggestionActionType.CREATE_WRITING_TASK,
                requires_user_action=True,
                action_status="pending",
            ),
            payload={
                "chapter_id": "chapter-1",
                "target_revision": 5,
                "target_content_hash": outline_content_hash("本章原始大纲", []),
                "chapter_plan_id": "plan-1",
                "task_title": "寻找灯塔线索",
                "writing_goal": "让主角发现父亲留下的标记",
                "must_include": ["旧标记"],
                "must_not_include": ["揭晓终局"],
                "target_word_count": 2200,
                "tone_guidance": "克制而紧张",
                "required_beats": ["进入夹层"],
                "context_summary": "承接上一章结尾",
            },
            agent_session_id="session-outline-1",
            request_id="request-outline-1",
            trace_id="trace-outline-1",
            created_at="2026-07-11T00:00:00+00:00",
            updated_at="2026-07-11T00:00:00+00:00",
        )
    )


def test_writing_task_convert_creates_pending_once_and_confirm_makes_it_consumable(tmp_path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    plans = FileChapterPlanStore(tmp_path / "plans.json")
    tasks = FileDirectionPlanStore(tmp_path / "directions.json")
    _confirmed_plan(plans)
    suggestion = _suggestion(suggestions)
    trace = _TraceSpy()
    service = AISuggestionService(
        ai_suggestion_repository=suggestions,
        ai_review_repository=object(),
        candidate_draft_repository=object(),
        candidate_rewrite_service=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
        trace_service=trace,
    )

    converted = service.convert_suggestion(
        suggestion.suggestion_id,
        user_id="writer-1",
        user_action=True,
        idempotency_key="convert-1",
        decision_note="  保存为本章写作计划  ",
    )
    repeated = service.convert_suggestion(
        suggestion.suggestion_id,
        user_id="writer-1",
        user_action=True,
        idempotency_key="convert-1",
        decision_note="保存为本章写作计划",
    )
    task_id = converted.action.action_payload_ref.split(":", 1)[1]
    task = tasks.get_writing_task(task_id)

    assert repeated.action.action_payload_ref == converted.action.action_payload_ref
    assert len(tasks.list_writing_tasks("work-1")) == 1
    assert task.status == WritingTaskStatus.PENDING
    assert task.request_id == suggestion.request_id
    assert task.trace_id == suggestion.trace_id
    assert tasks.get_active_writing_task("work-1", chapter_id="chapter-1") is None
    assert [name for name, _ in trace.calls] == ["ensure", "audit"]
    assert trace.calls[1][1]["event_type"] == "user_decision_recorded"
    assert trace.calls[1][1]["high_risk_user_action"] is True
    assert trace.calls[1][1]["payload_digest"]["user_id"] == "writer-1"

    planning = PlanningAPIService(
        work_service=object(),
        chapter_service=object(),
        context_pack_service=object(),
        tool_facade=object(),
        orchestrator=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
        trace_service=trace,
    )
    confirmed = planning.confirm_writing_task(
        writing_task_id=task_id,
        user_id="writer-1",
        request_id="request-1",
        trace_id="trace-1",
        user_action=True,
        idempotency_key="confirm-1",
        decision_note="  ready for drafting  ",
    )

    assert confirmed.status == WritingTaskStatus.READY
    assert confirmed.request_id == suggestion.request_id
    assert confirmed.trace_id == suggestion.trace_id
    assert confirmed.metadata["confirmed_trace_id"] == suggestion.trace_id
    assert confirmed.metadata["confirmation_note"] == "ready for drafting"
    assert tasks.get_active_writing_task("work-1", chapter_id="chapter-1").writing_task_id == task_id
    refreshed_confirmation = planning.confirm_writing_task(
        writing_task_id=task_id,
        user_id="writer-1",
        request_id="request-refresh",
        trace_id="trace-refresh",
        user_action=True,
        idempotency_key="confirm-1",
        decision_note="ready for drafting",
    )
    assert refreshed_confirmation.status == WritingTaskStatus.READY
    assert [name for name, _ in trace.calls] == ["ensure", "audit", "ensure", "audit"]
    assert trace.calls[3][1]["event_type"] == "user_decision_recorded"
    assert trace.calls[3][1]["high_risk_user_action"] is True
    assert trace.calls[3][1]["payload_digest"]["user_id"] == "writer-1"

    for changed_request in (
        {"user_id": "another-writer", "decision_note": "保存为本章写作计划"},
        {"user_id": "writer-1", "decision_note": "改成另一份计划"},
    ):
        with pytest.raises(ValueError, match="^P2_IDEMPOTENCY_CONFLICT$"):
            service.convert_suggestion(
                suggestion.suggestion_id,
                user_id=changed_request["user_id"],
                user_action=True,
                idempotency_key="convert-1",
                decision_note=changed_request["decision_note"],
            )

    for changed_request in (
        {"user_id": "another-writer", "decision_note": "ready for drafting"},
        {"user_id": "writer-1", "decision_note": "use a different plan"},
    ):
        with pytest.raises(ValueError, match="^P2_IDEMPOTENCY_CONFLICT$"):
            planning.confirm_writing_task(
                writing_task_id=task_id,
                user_id=changed_request["user_id"],
                request_id="request-conflict",
                trace_id="untrusted-trace",
                user_action=True,
                idempotency_key="confirm-1",
                decision_note=changed_request["decision_note"],
            )

    try:
        service.convert_suggestion(
            suggestion.suggestion_id,
            user_id="writer-1",
            user_action=True,
            idempotency_key="convert-different",
        )
    except ValueError as exc:
        assert str(exc) == "P2_IDEMPOTENCY_CONFLICT"
    else:
        raise AssertionError("a converted suggestion cannot be reused with another idempotency key")
    assert len(tasks.list_writing_tasks("work-1")) == 1


def test_writing_task_convert_and_confirm_idempotency_sections_are_process_wide(tmp_path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "locked-suggestions.json")
    plans = FileChapterPlanStore(tmp_path / "locked-plans.json")
    tasks = FileDirectionPlanStore(tmp_path / "locked-directions.json")
    _confirmed_plan(plans)
    suggestion = _suggestion(suggestions)
    convert_trace = _BlockingTrace()

    def suggestion_service() -> AISuggestionService:
        return AISuggestionService(
            ai_suggestion_repository=suggestions,
            ai_review_repository=object(),
            candidate_draft_repository=object(),
            candidate_rewrite_service=object(),
            direction_plan_repository=tasks,
            chapter_plan_repository=plans,
            writing_asset_service=_ChapterAssets(),
            trace_service=convert_trace,
        )

    convert_results: list[object] = []

    def convert() -> None:
        try:
            convert_results.append(
                suggestion_service().convert_suggestion(
                    suggestion.suggestion_id,
                    user_id="writer-1",
                    user_action=True,
                    idempotency_key="shared-convert",
                    decision_note="保存为计划",
                )
            )
        except Exception as exc:  # pragma: no cover - asserted below
            convert_results.append(exc)

    first_convert = Thread(target=convert)
    second_convert = Thread(target=convert)
    first_convert.start()
    assert convert_trace.first_audit_entered.wait(timeout=1)
    second_convert.start()
    assert not convert_trace.second_audit_entered.wait(timeout=0.2)
    convert_trace.release_first_audit.set()
    first_convert.join(timeout=2)
    second_convert.join(timeout=2)

    assert len(convert_results) == 2
    assert not any(isinstance(result, Exception) for result in convert_results)
    assert sum(1 for name, _ in convert_trace.calls if name == "audit") == 1
    converted = suggestions.get(suggestion.suggestion_id)
    task_id = converted.action.action_payload_ref.split(":", 1)[1]

    confirm_trace = _BlockingTrace()

    def planning_service() -> PlanningAPIService:
        return PlanningAPIService(
            work_service=object(),
            chapter_service=object(),
            context_pack_service=object(),
            tool_facade=object(),
            orchestrator=object(),
            direction_plan_repository=tasks,
            chapter_plan_repository=plans,
            writing_asset_service=_ChapterAssets(),
            trace_service=confirm_trace,
        )

    confirm_results: list[object] = []

    def confirm() -> None:
        try:
            confirm_results.append(
                planning_service().confirm_writing_task(
                    writing_task_id=task_id,
                    user_id="writer-1",
                    request_id="confirm-request",
                    trace_id="untrusted-request-trace",
                    user_action=True,
                    idempotency_key="shared-confirm",
                    decision_note="确认使用",
                )
            )
        except Exception as exc:  # pragma: no cover - asserted below
            confirm_results.append(exc)

    first_confirm = Thread(target=confirm)
    second_confirm = Thread(target=confirm)
    first_confirm.start()
    assert confirm_trace.first_audit_entered.wait(timeout=1)
    second_confirm.start()
    assert not confirm_trace.second_audit_entered.wait(timeout=0.2)
    confirm_trace.release_first_audit.set()
    first_confirm.join(timeout=2)
    second_confirm.join(timeout=2)

    assert len(confirm_results) == 2
    assert not any(isinstance(result, Exception) for result in confirm_results)
    assert sum(1 for name, _ in confirm_trace.calls if name == "audit") == 1
    assert tasks.get_writing_task(task_id).status == WritingTaskStatus.READY


def test_writing_task_idempotency_key_cannot_move_between_resource_ids(tmp_path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "resource-suggestions.json")
    plans = FileChapterPlanStore(tmp_path / "resource-plans.json")
    tasks = FileDirectionPlanStore(tmp_path / "resource-directions.json")
    _confirmed_plan(plans)
    first = _suggestion(suggestions)
    second = suggestions.save(
        first.model_copy(
            update={
                "suggestion_id": "ais-writing-task-2",
                "source": AISuggestionSource(
                    source_type="outline_assist",
                    source_ref_id="ais-writing-task-2",
                ),
            }
        )
    )
    trace = _TraceSpy()
    suggestion_service = AISuggestionService(
        ai_suggestion_repository=suggestions,
        ai_review_repository=object(),
        candidate_draft_repository=object(),
        candidate_rewrite_service=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
        trace_service=trace,
    )
    first_converted = suggestion_service.convert_suggestion(
        first.suggestion_id,
        user_id="writer-1",
        user_action=True,
        idempotency_key="resource-convert-key",
        decision_note="保存为计划",
    )

    with pytest.raises(ValueError, match="^P2_IDEMPOTENCY_CONFLICT$"):
        suggestion_service.convert_suggestion(
            second.suggestion_id,
            user_id="writer-1",
            user_action=True,
            idempotency_key="resource-convert-key",
            decision_note="保存为计划",
        )

    second_converted = suggestion_service.convert_suggestion(
        second.suggestion_id,
        user_id="writer-1",
        user_action=True,
        idempotency_key="second-convert-key",
        decision_note="保存为计划",
    )
    first_task_id = first_converted.action.action_payload_ref.split(":", 1)[1]
    second_task_id = second_converted.action.action_payload_ref.split(":", 1)[1]
    planning = PlanningAPIService(
        work_service=object(),
        chapter_service=object(),
        context_pack_service=object(),
        tool_facade=object(),
        orchestrator=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
        trace_service=trace,
    )
    planning.confirm_writing_task(
        writing_task_id=first_task_id,
        user_id="writer-1",
        request_id="first-confirm",
        trace_id="ignored-first-trace",
        user_action=True,
        idempotency_key="resource-confirm-key",
        decision_note="确认使用",
    )

    with pytest.raises(ValueError, match="^P2_IDEMPOTENCY_CONFLICT$"):
        planning.confirm_writing_task(
            writing_task_id=second_task_id,
            user_id="writer-1",
            request_id="second-confirm",
            trace_id="ignored-second-trace",
            user_action=True,
            idempotency_key="resource-confirm-key",
            decision_note="确认使用",
        )

    assert tasks.get_writing_task(second_task_id).status == WritingTaskStatus.PENDING


@pytest.mark.parametrize("failure_mode", ["missing_service", "blank_trace", "ensure", "audit"])
def test_writing_task_convert_fails_safe_before_task_or_suggestion_progress_when_audit_is_unavailable(
    tmp_path,
    failure_mode: str,
) -> None:
    suggestions = FileAISuggestionStore(tmp_path / f"suggestions-{failure_mode}.json")
    plans = FileChapterPlanStore(tmp_path / f"plans-{failure_mode}.json")
    tasks = FileDirectionPlanStore(tmp_path / f"directions-{failure_mode}.json")
    _confirmed_plan(plans)
    suggestion = _suggestion(suggestions)
    if failure_mode == "blank_trace":
        suggestion = suggestions.save(suggestion.model_copy(update={"trace_id": ""}))
    trace = None if failure_mode == "missing_service" else _TraceSpy(
        fail_at=failure_mode if failure_mode in {"ensure", "audit"} else ""
    )
    service = AISuggestionService(
        ai_suggestion_repository=suggestions,
        ai_review_repository=object(),
        candidate_draft_repository=object(),
        candidate_rewrite_service=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
        trace_service=trace,
    )

    with pytest.raises(ValueError, match="^P2_OUTLINE_AUDIT_WRITE_FAILED$"):
        service.convert_suggestion(
            suggestion.suggestion_id,
            user_id="writer-1",
            user_action=True,
            idempotency_key=f"convert-{failure_mode}",
        )

    assert tasks.list_writing_tasks("work-1") == []
    unchanged = suggestions.get(suggestion.suggestion_id)
    assert unchanged.status == AISuggestionStatus.GENERATED
    assert unchanged.action.action_status == "pending"


@pytest.mark.parametrize("failure_mode", ["missing_service", "blank_trace", "ensure", "audit"])
def test_writing_task_confirm_fails_safe_before_ready_when_audit_is_unavailable(
    tmp_path,
    failure_mode: str,
) -> None:
    suggestions = FileAISuggestionStore(tmp_path / f"suggestions-confirm-{failure_mode}.json")
    plans = FileChapterPlanStore(tmp_path / f"plans-confirm-{failure_mode}.json")
    tasks = FileDirectionPlanStore(tmp_path / f"directions-confirm-{failure_mode}.json")
    _confirmed_plan(plans)
    suggestion = _suggestion(suggestions)
    conversion_trace = _TraceSpy()
    suggestion_service = AISuggestionService(
        ai_suggestion_repository=suggestions,
        ai_review_repository=object(),
        candidate_draft_repository=object(),
        candidate_rewrite_service=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
        trace_service=conversion_trace,
    )
    converted = suggestion_service.convert_suggestion(
        suggestion.suggestion_id,
        user_id="writer-1",
        user_action=True,
        idempotency_key=f"convert-confirm-{failure_mode}",
    )
    task_id = converted.action.action_payload_ref.split(":", 1)[1]
    if failure_mode == "blank_trace":
        task = tasks.get_writing_task(task_id)
        tasks.save_writing_task(task.model_copy(update={"trace_id": ""}))
    trace = None if failure_mode == "missing_service" else _TraceSpy(
        fail_at=failure_mode if failure_mode in {"ensure", "audit"} else ""
    )
    planning = PlanningAPIService(
        work_service=object(),
        chapter_service=object(),
        context_pack_service=object(),
        tool_facade=object(),
        orchestrator=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
        trace_service=trace,
    )

    with pytest.raises(ValueError, match="^P2_OUTLINE_AUDIT_WRITE_FAILED$"):
        planning.confirm_writing_task(
            writing_task_id=task_id,
            user_id="writer-1",
            request_id="request-confirm-1",
            trace_id="trace-confirm-1",
            user_action=True,
            idempotency_key=f"confirm-{failure_mode}",
        )

    unchanged = tasks.get_writing_task(task_id)
    assert unchanged.status == WritingTaskStatus.PENDING
    assert not unchanged.metadata.get("user_confirmed")


def test_outline_assist_ownership_checks_are_read_only_and_false_for_unknown_ids(tmp_path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "suggestions-ownership.json")
    plans = FileChapterPlanStore(tmp_path / "plans-ownership.json")
    tasks = FileDirectionPlanStore(tmp_path / "directions-ownership.json")
    suggestion = _suggestion(suggestions)
    suggestion_service = AISuggestionService(
        ai_suggestion_repository=suggestions,
        ai_review_repository=object(),
        candidate_draft_repository=object(),
        candidate_rewrite_service=object(),
    )
    planning = PlanningAPIService(
        work_service=object(),
        chapter_service=object(),
        context_pack_service=object(),
        tool_facade=object(),
        orchestrator=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
    )

    assert suggestion_service.is_outline_assist_suggestion(suggestion.suggestion_id) is True
    assert suggestion_service.is_outline_assist_suggestion("missing") is False
    non_outline = suggestion.model_copy(
        update={
            "suggestion_id": "same-type-from-reviewer",
            "source": AISuggestionSource(source_type="review_issue", source_ref_id="review-1"),
        }
    )
    suggestions.save(non_outline)
    assert suggestion_service.is_outline_assist_suggestion(non_outline.suggestion_id) is False
    assert suggestions.get(suggestion.suggestion_id).status == AISuggestionStatus.GENERATED
    assert planning.is_outline_assist_writing_task("missing") is False


def test_writing_task_convert_requires_current_confirmed_plan(tmp_path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    plans = FileChapterPlanStore(tmp_path / "plans.json")
    tasks = FileDirectionPlanStore(tmp_path / "directions.json")
    suggestion = _suggestion(suggestions)
    service = AISuggestionService(
        ai_suggestion_repository=suggestions,
        ai_review_repository=object(),
        candidate_draft_repository=object(),
        candidate_rewrite_service=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
    )

    try:
        service.convert_suggestion(
            suggestion.suggestion_id,
            user_id="writer-1",
            user_action=True,
            idempotency_key="convert-missing-plan",
        )
    except ValueError as exc:
        assert str(exc) == "P2_WRITING_TASK_PREREQUISITE_MISSING"
    else:
        raise AssertionError("missing confirmed plan must block conversion")
    assert tasks.list_writing_tasks("work-1") == []


def test_writing_task_convert_reports_outline_conflict_when_chapter_outline_changed(tmp_path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    plans = FileChapterPlanStore(tmp_path / "plans.json")
    tasks = FileDirectionPlanStore(tmp_path / "directions.json")
    _confirmed_plan(plans)
    suggestion = _suggestion(suggestions)
    assets = _ChapterAssets()
    assets.outline = ChapterOutline(
        assets.outline.id,
        assets.outline.chapter_id,
        "作者后来改过的本章大纲",
        [],
        6,
        assets.outline.created_at,
        datetime.now(UTC),
    )
    service = AISuggestionService(
        ai_suggestion_repository=suggestions,
        ai_review_repository=object(),
        candidate_draft_repository=object(),
        candidate_rewrite_service=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=assets,
    )

    try:
        service.convert_suggestion(
            suggestion.suggestion_id,
            user_id="writer-1",
            user_action=True,
            idempotency_key="convert-stale-outline",
        )
    except ValueError as exc:
        assert str(exc) == "P2_OUTLINE_TARGET_CONFLICT"
    else:
        raise AssertionError("changed chapter outline must block conversion")
    assert tasks.list_writing_tasks("work-1") == []


def test_p2_suggestion_decisions_cannot_move_pending_failed_or_converted_backwards(tmp_path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    plans = FileChapterPlanStore(tmp_path / "plans.json")
    tasks = FileDirectionPlanStore(tmp_path / "directions.json")
    service = AISuggestionService(
        ai_suggestion_repository=suggestions,
        ai_review_repository=object(),
        candidate_draft_repository=object(),
        candidate_rewrite_service=object(),
        direction_plan_repository=tasks,
        chapter_plan_repository=plans,
        writing_asset_service=_ChapterAssets(),
    )
    template = _suggestion(suggestions)

    for status in (AISuggestionStatus.PENDING, AISuggestionStatus.FAILED, AISuggestionStatus.CONVERTED):
        item = template.model_copy(update={"suggestion_id": f"ais-{status.value}", "status": status})
        suggestions.save(item)
        try:
            service.accept_suggestion(item.suggestion_id, user_id="writer-1", user_action=True)
        except ValueError as exc:
            assert str(exc) == "action_not_allowed"
        else:
            raise AssertionError(f"accept must reject {status.value}")
        try:
            service.dismiss_suggestion(item.suggestion_id, user_id="writer-1", user_action=True)
        except ValueError as exc:
            assert str(exc) == "action_not_allowed"
        else:
            raise AssertionError(f"dismiss must reject {status.value}")
