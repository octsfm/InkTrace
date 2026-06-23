from __future__ import annotations

from application.services.ai.vector_reindex_service import VectorReindexApplicationService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import AIJobStatus, VectorIndexBuildResult
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore


class _StubVectorIndexService:
    def __init__(
        self,
        *,
        work_result: VectorIndexBuildResult | None = None,
        chapter_results: dict[str, VectorIndexBuildResult] | None = None,
    ) -> None:
        self._work_result = work_result or VectorIndexBuildResult(
            index_status="ready",
            indexed_chapter_count=2,
            indexed_chunk_count=4,
        )
        self._chapter_results = dict(chapter_results or {})
        self.work_calls: list[tuple[str, bool]] = []
        self.chapter_calls: list[tuple[str, str, bool]] = []

    def reindex_work(self, work_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
        self.work_calls.append((work_id, bool(should_continue() if callable(should_continue) else True)))
        return self._work_result

    def reindex_chapter(self, work_id: str, chapter_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
        self.chapter_calls.append((work_id, chapter_id, bool(should_continue() if callable(should_continue) else True)))
        return self._chapter_results.get(
            chapter_id,
            VectorIndexBuildResult(
                index_status="ready",
                indexed_chapter_count=1,
                indexed_chunk_count=2,
            ),
        )


def _build_service(tmp_path, vector_index_service: _StubVectorIndexService):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    store = FileAIJobStore(tmp_path / "ai_jobs.json")
    service = VectorReindexApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        job_repository=store,
        step_repository=store,
        attempt_repository=store,
        vector_index_service=vector_index_service,
    )
    return service, work_service, chapter_service


def test_vector_reindex_service_runs_full_work_reindex_job(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService(
        work_result=VectorIndexBuildResult(
            index_status="ready",
            indexed_chapter_count=2,
            indexed_chunk_count=5,
        )
    )
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("全书重建作品", "作者")

    job = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
    )
    steps = {step.step_type: step for step in service.get_job_steps(job.job_id)}

    assert job.job_type == "vector_indexing"
    assert job.status == AIJobStatus.COMPLETED
    assert job.result_ref == f"vector_index_status:{work.id}"
    assert job.result_summary["index_scope"] == "full_work"
    assert job.result_summary["index_status"] == "ready"
    assert job.result_summary["indexed_chunk_count"] == 5
    assert "build_vector_index" in steps
    assert steps["build_vector_index"].status.value == "completed"
    assert vector_index_service.work_calls == [(work.id, True)]


def test_vector_reindex_service_marks_partial_success_for_chapter_reindex(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService(
        chapter_results={
            "chapter-a": VectorIndexBuildResult(
                index_status="ready",
                indexed_chapter_count=1,
                indexed_chunk_count=2,
            ),
            "chapter-b": VectorIndexBuildResult(
                index_status="degraded",
                indexed_chapter_count=0,
                indexed_chunk_count=0,
                failed_chunk_count=1,
                warning_count=1,
                degraded_reason="target_chapter_not_confirmed",
                warnings=["target_chapter_not_confirmed"],
            ),
        }
    )
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("章节重建作品", "作者")

    job = service.start_reindex(
        work_id=work.id,
        index_scope="chapter",
        target_chapter_ids=["chapter-a", "chapter-b"],
        created_by="user_action",
    )
    step = service.get_job_steps(job.job_id)[0]

    assert job.status == AIJobStatus.COMPLETED
    assert job.result_ref == f"vector_index_status:{work.id}"
    assert job.result_summary["completion_mode"] == "partial_success"
    assert job.result_summary["index_scope"] == "chapter"
    assert job.result_summary["index_status"] == "degraded"
    assert job.result_summary["target_chapter_count"] == 2
    assert step.status.value == "completed"
    assert step.warning_count == 1
    assert step.status_reason == "vector_index_degraded"


def test_vector_reindex_service_marks_job_failed_when_reindex_fails(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService(
        work_result=VectorIndexBuildResult(
            index_status="failed",
            indexed_chapter_count=0,
            indexed_chunk_count=0,
            failed_chunk_count=2,
            degraded_reason="index_build_failed",
        )
    )
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("失败重建作品", "作者")

    job = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
    )
    step = service.get_job_steps(job.job_id)[0]

    assert job.status == AIJobStatus.FAILED
    assert job.error_code == "vector_index_build_failed"
    assert step.status.value == "failed"
    assert step.error_code == "vector_index_build_failed"


def test_vector_reindex_service_does_not_run_cancelled_job(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService()
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("取消重建作品", "作者")

    job = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
        auto_run=False,
    )
    service.cancel_job(job.job_id, reason="user_cancelled")
    cancelled = service.run_reindex(job.job_id)

    assert cancelled.status == AIJobStatus.CANCELLED
    assert cancelled.status_reason == "user_cancelled"
    assert vector_index_service.work_calls == []


def test_vector_reindex_service_can_pause_and_resume_job(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService()
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("暂停恢复重建作品", "作者")

    job = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
        auto_run=False,
    )
    paused = service.pause_job(job.job_id, reason="user_requested_pause")
    resumed = service.resume_job(job.job_id, reason="user_requested_resume")

    assert paused.status == AIJobStatus.PAUSED
    assert paused.status_reason == "user_requested_pause"
    assert resumed.status == AIJobStatus.RUNNING
    assert resumed.status_reason == "user_requested_resume"


def test_vector_reindex_service_can_retry_failed_job(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService(
        work_result=VectorIndexBuildResult(
            index_status="failed",
            indexed_chapter_count=0,
            indexed_chunk_count=0,
            failed_chunk_count=1,
            degraded_reason="index_build_failed",
        )
    )
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("失败重试重建作品", "作者")

    job = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
    )
    retried = service.retry_job(job.job_id)
    step = service.get_job_steps(job.job_id)[0]

    assert job.status == AIJobStatus.FAILED
    assert retried.status == AIJobStatus.QUEUED
    assert retried.status_reason == "retry_requested"
    assert step.status.value == "pending"


def test_vector_reindex_service_resume_and_run_continues_paused_job(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService()
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("恢复继续重建作品", "作者")

    job = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
        auto_run=False,
    )
    service.pause_job(job.job_id, reason="user_requested_pause")
    resumed = service.resume_and_run(job.job_id, reason="user_requested_resume")

    assert resumed.status == AIJobStatus.COMPLETED
    assert resumed.result_summary["index_status"] == "ready"
    assert vector_index_service.work_calls == [(work.id, True)]


def test_vector_reindex_service_retry_and_run_continues_failed_job(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService(
        work_result=VectorIndexBuildResult(
            index_status="failed",
            indexed_chapter_count=0,
            indexed_chunk_count=0,
            failed_chunk_count=1,
            degraded_reason="index_build_failed",
        )
    )
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("失败继续重建作品", "作者")

    failed = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
    )
    vector_index_service._work_result = VectorIndexBuildResult(
        index_status="ready",
        indexed_chapter_count=1,
        indexed_chunk_count=3,
    )
    retried = service.retry_and_run(failed.job_id)

    assert failed.status == AIJobStatus.FAILED
    assert retried.status == AIJobStatus.COMPLETED
    assert retried.result_summary["index_status"] == "ready"
    assert vector_index_service.work_calls == [(work.id, True), (work.id, True)]


def test_vector_reindex_service_reuses_existing_job_for_same_idempotency_key(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService()
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("幂等重建作品", "作者")

    first = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
        idempotency_key="idem_vector_reindex_job",
        auto_run=False,
    )
    second = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
        idempotency_key="idem_vector_reindex_job",
        auto_run=False,
    )

    assert first.job_id == second.job_id
    assert second.metadata["reused_existing_job"] is True
    assert vector_index_service.work_calls == []


def test_vector_reindex_service_rejects_running_job_for_same_work(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService()
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("并发重建作品", "作者")

    first = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
        auto_run=False,
    )

    assert first.status == AIJobStatus.QUEUED
    try:
        service.start_reindex(
            work_id=work.id,
            index_scope="chapter",
            target_chapter_ids=["chapter-a"],
            created_by="user_action",
            auto_run=False,
        )
    except ValueError as exc:
        assert str(exc) == "P2_VECTOR_INDEXING_IN_PROGRESS"
    else:
        raise AssertionError("expected concurrent reindex to be rejected")


def test_vector_reindex_service_stores_reason_and_force_rebuild_payload(tmp_path) -> None:
    vector_index_service = _StubVectorIndexService()
    service, work_service, _chapter_service = _build_service(tmp_path, vector_index_service)
    work = work_service.create_work("重建原因作品", "作者")

    job = service.start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
        force_rebuild=True,
        reason="多章正文已更新，需要重建索引",
        auto_run=False,
    )

    assert job.payload["force_rebuild"] is True
    assert job.payload["reason"] == "多章正文已更新，需要重建索引"
