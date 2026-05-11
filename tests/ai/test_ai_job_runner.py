from __future__ import annotations

import pytest

from application.services.ai.ai_job_runner import AIJobRunner
from application.services.ai.ai_job_service import AIJobService
from domain.entities.ai.models import AIJobStatus
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore


def _build_service(tmp_path) -> AIJobService:
    store = FileAIJobStore(tmp_path / "ai_jobs.json")
    return AIJobService(job_repository=store, step_repository=store, attempt_repository=store)


def test_ai_job_runner_raises_when_handler_missing(tmp_path) -> None:
    service = _build_service(tmp_path)
    runner = AIJobRunner(job_service=service)
    job = service.create_job(job_type="continuation", work_id="work-1", steps=[])

    with pytest.raises(ValueError, match="job_handler_not_registered"):
        runner.run(job.job_id)


def test_ai_job_runner_marks_job_succeeded_on_successful_handler(tmp_path) -> None:
    service = _build_service(tmp_path)
    runner = AIJobRunner(job_service=service)
    job = service.create_job(job_type="continuation", work_id="work-1", steps=[])

    def _handler(job_id: str, job_service: AIJobService) -> None:
        job_service.mark_job_completed(job_id, result_summary={"ok": True})

    runner.register("continuation", _handler)
    result = runner.run(job.job_id)

    assert result.status == AIJobStatus.COMPLETED
    assert result.result_summary["ok"] is True


def test_ai_job_runner_marks_job_failed_on_handler_error(tmp_path) -> None:
    service = _build_service(tmp_path)
    runner = AIJobRunner(job_service=service)
    job = service.create_job(job_type="continuation", work_id="work-1", steps=[])

    def _handler(_: str, __: AIJobService) -> None:
        raise RuntimeError("boom")

    runner.register("continuation", _handler)
    result = runner.run(job.job_id)

    assert result.status == AIJobStatus.FAILED
    assert result.error_code == "job_handler_failed"


def test_ai_job_runner_does_not_override_cancelled_job(tmp_path) -> None:
    service = _build_service(tmp_path)
    runner = AIJobRunner(job_service=service)
    job = service.create_job(job_type="continuation", work_id="work-1", steps=[])

    def _handler(job_id: str, job_service: AIJobService) -> None:
        job_service.cancel_job(job_id, reason="user_cancelled")
        job_service.mark_job_completed(job_id, result_summary={"late": True})

    runner.register("continuation", _handler)
    result = runner.run(job.job_id)

    assert result.status == AIJobStatus.CANCELLED
    assert result.status_reason == "user_cancelled"
