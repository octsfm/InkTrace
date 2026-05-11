from __future__ import annotations

from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from domain.entities.ai.models import (
    AIJob,
    AIJobAttempt,
    AIJobAttemptStatus,
    AIJobProgress,
    AIJobStatus,
    AIJobStep,
    AIJobStepStatus,
)


def test_ai_job_repository_creates_and_reads_job(tmp_path) -> None:
    store = FileAIJobStore(tmp_path / "ai_jobs.json")
    job = AIJob(
        job_id="job-1",
        work_id="work-1",
        chapter_id="chapter-1",
        job_type="continuation",
        status=AIJobStatus.QUEUED,
        progress=AIJobProgress(total_steps=1),
    )

    store.create_job(job)

    loaded = store.get_job("job-1")

    assert loaded.job_id == "job-1"
    assert loaded.job_type == "continuation"
    assert loaded.progress.total_steps == 1


def test_ai_job_repository_updates_status_lists_steps_and_attempts(tmp_path) -> None:
    store = FileAIJobStore(tmp_path / "ai_jobs.json")
    job = AIJob(
        job_id="job-1",
        work_id="work-1",
        chapter_id="chapter-1",
        job_type="ai_initialization",
        status=AIJobStatus.QUEUED,
        progress=AIJobProgress(total_steps=1),
    )
    step = AIJobStep(
        step_id="step-1",
        job_id="job-1",
        step_type="outline_analysis",
        step_name="Outline Analysis",
        status=AIJobStepStatus.PENDING,
        order_index=1,
    )
    attempt = AIJobAttempt(
        attempt_id="attempt-1",
        job_id="job-1",
        step_id="step-1",
        attempt_no=1,
        request_id="req-1",
        trace_id="trace-1",
        provider_name="fake",
        model_name="fake-chat",
        model_role="writer",
        prompt_key="continuation_writer_p0",
        prompt_version="v1",
        output_schema_key="plain_text",
        status=AIJobAttemptStatus.COMPLETED,
    )

    store.create_job(job)
    store.create_step(step)
    store.create_attempt(attempt)
    store.save_job(job.model_copy(update={"status": AIJobStatus.RUNNING}))
    store.save_step(step.model_copy(update={"status": AIJobStepStatus.RUNNING}))

    by_work = store.list_jobs(work_id="work-1")
    by_status = store.list_jobs(status=AIJobStatus.RUNNING.value)
    steps = store.list_steps("job-1")
    attempts = store.list_attempts("step-1")

    assert [item.job_id for item in by_work] == ["job-1"]
    assert [item.job_id for item in by_status] == ["job-1"]
    assert steps[0].status == AIJobStepStatus.RUNNING
    assert attempts[0].request_id == "req-1"
