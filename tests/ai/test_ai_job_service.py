from __future__ import annotations

import pytest

from application.services.ai.ai_job_service import AIJobService
from domain.entities.ai.models import AIJobStatus, AIJobStepStatus
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore


def _build_service(tmp_path) -> AIJobService:
    store = FileAIJobStore(tmp_path / "ai_jobs.json")
    return AIJobService(job_repository=store, step_repository=store, attempt_repository=store)


def test_ai_job_service_create_and_complete_job(tmp_path) -> None:
    service = _build_service(tmp_path)

    job = service.create_job(
        job_type="continuation",
        work_id="work-1",
        chapter_id="chapter-1",
        steps=[
            {"step_type": "build_context_pack", "step_name": "Build Context Pack"},
            {"step_type": "run_writer_step", "step_name": "Run Writer Step"},
        ],
    )

    started = service.start_job(job.job_id)
    steps = service.get_job_steps(job.job_id)
    service.mark_step_running(job.job_id, steps[0].step_id)
    service.mark_step_completed(job.job_id, steps[0].step_id, summary="context ready")
    service.mark_step_running(job.job_id, steps[1].step_id)
    service.mark_step_completed(job.job_id, steps[1].step_id, summary="writer done")
    completed = service.mark_job_completed(job.job_id, result_summary={"candidate_ready": True}, result_ref="candidate:1")

    assert started.status == AIJobStatus.RUNNING
    assert completed.status == AIJobStatus.COMPLETED
    assert completed.progress.completed_steps == 2
    assert completed.progress.percent == 100
    assert completed.result_ref == "candidate:1"


def test_ai_job_service_cancelled_job_ignores_late_completion(tmp_path) -> None:
    service = _build_service(tmp_path)
    job = service.create_job(
        job_type="ai_initialization",
        work_id="work-1",
        steps=[{"step_type": "outline_analysis", "step_name": "Outline Analysis"}],
    )

    service.start_job(job.job_id)
    cancelled = service.cancel_job(job.job_id, reason="user_cancelled")
    late = service.mark_job_completed(job.job_id, result_summary={"ignored": True})

    assert cancelled.status == AIJobStatus.CANCELLED
    assert late.status == AIJobStatus.CANCELLED
    assert late.status_reason == "user_cancelled"


def test_ai_job_service_retry_job_and_step_from_failed_state(tmp_path) -> None:
    service = _build_service(tmp_path)
    job = service.create_job(
        job_type="manuscript_analysis",
        work_id="work-1",
        steps=[{"step_type": "manuscript_chapter_analysis", "step_name": "Analyze Chapter"}],
    )
    step = service.get_job_steps(job.job_id)[0]

    service.start_job(job.job_id)
    service.mark_step_running(job.job_id, step.step_id)
    failed_step = service.mark_step_failed(job.job_id, step.step_id, error_code="provider_timeout", error_message="timeout")
    failed_job = service.mark_job_failed(job.job_id, error_code="provider_timeout", error_message="timeout")
    retried_job = service.retry_job(job.job_id)
    retried_step = service.retry_step(job.job_id, step.step_id)

    assert failed_step.status == AIJobStepStatus.FAILED
    assert failed_job.status == AIJobStatus.FAILED
    assert retried_job.status == AIJobStatus.QUEUED
    assert retried_step.status == AIJobStepStatus.PENDING
    assert retried_step.attempt_count == 1


def test_ai_job_service_marks_partial_success_without_new_status(tmp_path) -> None:
    service = _build_service(tmp_path)
    job = service.create_job(
        job_type="manuscript_analysis",
        work_id="work-1",
        steps=[
            {"step_type": "manuscript_chapter_analysis", "step_name": "Analyze Chapter 1", "can_skip": True},
            {"step_type": "manuscript_chapter_analysis", "step_name": "Analyze Chapter 2", "can_skip": True},
        ],
    )
    step_1, step_2 = service.get_job_steps(job.job_id)

    service.start_job(job.job_id)
    service.mark_step_running(job.job_id, step_1.step_id)
    service.mark_step_completed(job.job_id, step_1.step_id)
    service.mark_step_failed(job.job_id, step_2.step_id, error_code="provider_unavailable", error_message="down")
    partial = service.mark_job_partial_success(job.job_id, result_summary={"failed_chapters": 1})

    assert partial.status == AIJobStatus.COMPLETED
    assert partial.result_summary["completion_mode"] == "partial_success"
    assert partial.progress.failed_step_count == 1


def test_ai_job_service_recover_after_restart_pauses_running_job(tmp_path) -> None:
    service = _build_service(tmp_path)
    job = service.create_job(
        job_type="continuation",
        work_id="work-1",
        steps=[{"step_type": "build_context_pack", "step_name": "Build Context Pack"}],
    )
    step = service.get_job_steps(job.job_id)[0]
    service.start_job(job.job_id)
    service.mark_step_running(job.job_id, step.step_id)

    recovered = service.recover_after_restart()

    refreshed_job = service.get_job(job.job_id)
    refreshed_step = service.get_job_steps(job.job_id)[0]
    assert recovered == [job.job_id]
    assert refreshed_job.status == AIJobStatus.PAUSED
    assert refreshed_job.status_reason == "service_restarted"
    assert refreshed_step.status == AIJobStepStatus.PAUSED


def test_ai_job_service_can_pause_and_restart_job(tmp_path) -> None:
    service = _build_service(tmp_path)
    job = service.create_job(
        job_type="continuation",
        work_id="work-1",
        steps=[{"step_type": "run_writer_step", "step_name": "Run Writer Step"}],
    )

    service.start_job(job.job_id)
    paused = service.pause_job(job.job_id, reason="user_requested_pause")
    resumed = service.start_job(job.job_id)

    assert paused.status == AIJobStatus.PAUSED
    assert paused.status_reason == "user_requested_pause"
    assert resumed.status == AIJobStatus.RUNNING


def test_ai_job_service_rejects_invalid_terminal_transition(tmp_path) -> None:
    service = _build_service(tmp_path)
    job = service.create_job(
        job_type="continuation",
        work_id="work-1",
        steps=[{"step_type": "run_writer_step", "step_name": "Run Writer Step"}],
    )

    service.cancel_job(job.job_id, reason="user_cancelled")

    with pytest.raises(ValueError, match="job_not_retryable"):
        service.start_job(job.job_id)
