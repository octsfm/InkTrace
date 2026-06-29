from domain.entities.ai.models import (
    AIReviewResult,
    AIReviewRiskLevel,
    AIReviewStatus,
    AutoQueueConfig,
    AutoQueueMode,
    AutoQueueRun,
    AutoQueueStatus,
    ReviewIssue,
    StopCondition,
    StopSeverity,
)
from application.services.ai.stop_condition_evaluator import StopConditionEvaluator


class _StubPlotArcRepository:
    def __init__(self, sequence_status: str = "") -> None:
        self._sequence_status = sequence_status

    def get_active_sequence_arc(self, work_id: str, chapter_no: int = 0):
        _ = work_id, chapter_no
        if not self._sequence_status:
            return None
        return type("SequenceArcStub", (), {"status": self._sequence_status})()


class _StubBudgetService:
    def __init__(self, exceeded: bool = False) -> None:
        self._exceeded = exceeded

    def check_auto_queue_budget(self, run_id: str):
        _ = run_id
        return type(
            "BudgetResult",
            (),
            {
                "exceeded": self._exceeded,
                "estimated_total_tokens": 520000,
                "suggested_action": "adjust_budget",
            },
        )()


def _build_config(**updates) -> AutoQueueConfig:
    payload = {
        "config_id": "aqc_001",
        "work_id": "work_001",
        "queue_mode": AutoQueueMode.SAFE,
        "target_chapters": 5,
        "target_word_count": 0,
        "stop_at_sequence_end": True,
        "stop_on_blocking_review": True,
        "max_consecutive_blocking": 2,
        "stop_on_budget_exceeded": True,
        "max_consecutive_revision_failures": 3,
        "stop_on_foreshadow_premature": True,
        "budget_limit_tokens": 200000,
        "enabled": True,
        "created_at": "2026-06-24T11:00:00Z",
        "updated_at": "2026-06-24T11:00:00Z",
    }
    payload.update(updates)
    return AutoQueueConfig(**payload)


def _build_run(**updates) -> AutoQueueRun:
    payload = {
        "run_id": "aqr_001",
        "config_id": "aqc_001",
        "work_id": "work_001",
        "multi_chapter_session_id": "mcs_001",
        "status": AutoQueueStatus.RUNNING,
        "queue_mode": AutoQueueMode.SAFE,
        "generated_count": 1,
        "total_word_count": 3200,
        "consumed_tokens": 60000,
        "current_stop_evaluation": {},
        "stop_record": None,
        "current_candidate_story_state": {},
        "queue_state_snapshots": [],
        "consecutive_blocking_count": 0,
        "consecutive_revision_failure_count": 0,
        "error_code": "",
        "error_message": "",
        "request_id": "req_001",
        "trace_id": "trace_001",
        "created_at": "2026-06-24T11:00:00Z",
        "updated_at": "2026-06-24T11:00:00Z",
        "started_at": "2026-06-24T11:01:00Z",
        "stopped_at": "",
        "finished_at": "",
    }
    payload.update(updates)
    return AutoQueueRun(**payload)


def _build_review(*, blocking: bool = False, provider_error: str = "") -> AIReviewResult:
    return AIReviewResult(
        review_id="review_001",
        work_id="work_001",
        chapter_id="chapter_001",
        candidate_draft_id="draft_001",
        status=AIReviewStatus.COMPLETED,
        summary="review summary",
        warnings=[],
        issues=[
            ReviewIssue(
                issue_id="issue_001",
                severity="blocking" if blocking else "medium",
                category="consistency",
                message="blocking conflict" if blocking else "minor issue",
                suggestion="fix it",
            )
        ],
        suggestions=[],
        risk_level=AIReviewRiskLevel.HIGH if blocking else AIReviewRiskLevel.LOW,
        consistency_notes=[],
        style_notes=[],
        logic_notes=[],
        provider_name="kimi",
        model_name="kimi-review",
        created_at="2026-06-24T11:00:00Z",
        metadata={"provider_error": provider_error},
    )


def test_stop_condition_evaluator_stops_on_budget_exceeded_before_normal_completion() -> None:
    evaluator = StopConditionEvaluator(
        plot_arc_repository=_StubPlotArcRepository(),
        budget_service=_StubBudgetService(exceeded=True),
    )

    result = evaluator.evaluate(_build_run(generated_count=5), _build_config(), _build_review())

    assert result.should_stop is True
    assert result.condition == StopCondition.BUDGET_EXCEEDED
    assert result.severity == StopSeverity.BUDGET
    assert result.suggested_action == "adjust_budget"


def test_stop_condition_evaluator_stops_on_consecutive_blocking_reviews() -> None:
    evaluator = StopConditionEvaluator(plot_arc_repository=_StubPlotArcRepository(), budget_service=None)

    result = evaluator.evaluate(
        _build_run(consecutive_blocking_count=1),
        _build_config(max_consecutive_blocking=2),
        _build_review(blocking=True),
    )

    assert result.should_stop is True
    assert result.condition == StopCondition.BLOCKING_REVIEW_CONSECUTIVE
    assert result.severity == StopSeverity.ABNORMAL
    assert result.user_action_required is True


def test_stop_condition_evaluator_marks_target_chapters_reached_as_normal_completion() -> None:
    evaluator = StopConditionEvaluator(
        plot_arc_repository=_StubPlotArcRepository(sequence_status="active"),
        budget_service=None,
    )

    result = evaluator.evaluate(
        _build_run(generated_count=5),
        _build_config(target_chapters=5, stop_at_sequence_end=False),
        _build_review(),
    )

    assert result.should_stop is True
    assert result.condition == StopCondition.TARGET_CHAPTERS_REACHED
    assert result.severity == StopSeverity.NORMAL


def test_stop_condition_evaluator_keeps_revision_failure_condition_reserved_for_now() -> None:
    evaluator = StopConditionEvaluator(plot_arc_repository=_StubPlotArcRepository(), budget_service=None)

    result = evaluator.evaluate(
        _build_run(consecutive_revision_failure_count=99),
        _build_config(max_consecutive_revision_failures=3, target_chapters=0, budget_limit_tokens=0),
        _build_review(),
    )

    assert result.condition != StopCondition.CONSECUTIVE_REVISION_FAILURE
