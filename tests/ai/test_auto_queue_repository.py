from domain.entities.ai.models import (
    AutoQueueConfig,
    AutoQueueRun,
    AutoQueueStatus,
    AutoQueueStopRecord,
    StopCondition,
    StopSeverity,
)
from infrastructure.persistence.sqlite_auto_queue_config_repo import SQLiteAutoQueueConfigRepository
from infrastructure.persistence.sqlite_auto_queue_run_repo import SQLiteAutoQueueRunRepository


def test_auto_queue_models_preserve_required_fields() -> None:
    config = AutoQueueConfig(
        config_id="aqc_001",
        work_id="work_001",
        target_chapters=10,
        target_word_count=50000,
        stop_at_sequence_end=True,
        stop_on_blocking_review=True,
        max_consecutive_blocking=2,
        stop_on_budget_exceeded=True,
        max_consecutive_revision_failures=3,
        stop_on_foreshadow_premature=True,
        budget_limit_tokens=500000,
        enabled=True,
        created_at="2026-06-24T11:00:00Z",
        updated_at="2026-06-24T11:00:00Z",
    )
    stop_record = AutoQueueStopRecord(
        stop_reason=StopCondition.BUDGET_EXCEEDED,
        stop_severity=StopSeverity.BUDGET,
        stop_context={"generated_count": 4},
        stopped_at="2026-06-24T11:20:00Z",
        user_action_required=True,
        suggested_action="adjust_budget",
    )
    run = AutoQueueRun(
        run_id="aqr_001",
        job_id="job_aq_001",
        config_id="aqc_001",
        work_id="work_001",
        multi_chapter_session_id="mcs_001",
        status=AutoQueueStatus.STOPPED,
        generated_count=4,
        total_word_count=12600,
        consumed_tokens=520000,
        current_stop_evaluation={"should_stop": True},
        stop_record=stop_record,
        current_candidate_story_state={"chapter": 4},
        queue_state_snapshots=[{"chapter": 1}, {"chapter": 2}],
        consecutive_blocking_count=2,
        consecutive_revision_failure_count=0,
        error_code="P2_BUDGET_EXCEEDED",
        error_message="budget exceeded",
        request_id="req_001",
        trace_id="trace_001",
        created_at="2026-06-24T11:00:00Z",
        updated_at="2026-06-24T11:20:00Z",
        started_at="2026-06-24T11:01:00Z",
        stopped_at="2026-06-24T11:20:00Z",
        finished_at="",
    )
    assert run.status == AutoQueueStatus.STOPPED
    assert run.job_id == "job_aq_001"
    assert run.stop_record is not None
    assert run.stop_record.stop_reason == StopCondition.BUDGET_EXCEEDED
    assert run.stop_record.suggested_action == "adjust_budget"


def test_sqlite_auto_queue_repositories_persist_config_active_and_history_runs(tmp_path) -> None:
    config_repo = SQLiteAutoQueueConfigRepository(tmp_path / "auto-queue.db")
    run_repo = SQLiteAutoQueueRunRepository(tmp_path / "auto-queue.db")

    config = AutoQueueConfig(
        config_id="aqc_001",
        work_id="work_001",
        target_chapters=5,
        target_word_count=0,
        stop_at_sequence_end=True,
        stop_on_blocking_review=True,
        max_consecutive_blocking=2,
        stop_on_budget_exceeded=True,
        max_consecutive_revision_failures=3,
        stop_on_foreshadow_premature=True,
        budget_limit_tokens=200000,
        enabled=True,
        created_at="2026-06-24T11:00:00Z",
        updated_at="2026-06-24T11:00:00Z",
    )
    running = AutoQueueRun(
        run_id="aqr_running_001",
        job_id="job_aq_running_001",
        config_id="aqc_001",
        work_id="work_001",
        multi_chapter_session_id="mcs_001",
        status=AutoQueueStatus.RUNNING,
        generated_count=2,
        total_word_count=6200,
        consumed_tokens=82000,
        current_stop_evaluation={},
        stop_record=None,
        current_candidate_story_state={"chapter": 2},
        queue_state_snapshots=[{"chapter": 1}],
        consecutive_blocking_count=0,
        consecutive_revision_failure_count=0,
        error_code="",
        error_message="",
        request_id="req_running",
        trace_id="trace_running",
        created_at="2026-06-24T11:00:00Z",
        updated_at="2026-06-24T11:10:00Z",
        started_at="2026-06-24T11:01:00Z",
        stopped_at="",
        finished_at="",
    )
    stopped = running.model_copy(
        update={
            "run_id": "aqr_stopped_001",
            "status": AutoQueueStatus.STOPPED,
            "generated_count": 4,
            "updated_at": "2026-06-24T11:30:00Z",
            "stopped_at": "2026-06-24T11:30:00Z",
            "stop_record": AutoQueueStopRecord(
                stop_reason=StopCondition.USER_MANUAL_STOP,
                stop_severity=StopSeverity.USER,
                stop_context={"generated_count": 4},
                stopped_at="2026-06-24T11:30:00Z",
                user_action_required=False,
                suggested_action="resume_queue",
            ),
        }
    )

    config_repo.save(config)
    run_repo.save(running)
    run_repo.save(stopped)

    loaded_config = config_repo.get_by_work("work_001")
    active_run = run_repo.get_active("work_001")
    history = run_repo.get_history("work_001")

    assert loaded_config is not None
    assert loaded_config.config_id == "aqc_001"
    assert active_run is not None
    assert active_run.run_id == "aqr_running_001"
    assert active_run.job_id == "job_aq_running_001"
    assert [item.run_id for item in history] == ["aqr_stopped_001", "aqr_running_001"]
