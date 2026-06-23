from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.vector_index_service import VectorIndexService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import AIJob, AIJobStatus, AIJobStep, VectorIndexBuildResult
from domain.repositories.ai.ai_job_attempt_repository import AIJobAttemptRepository
from domain.repositories.ai.ai_job_repository import AIJobRepository
from domain.repositories.ai.ai_job_step_repository import AIJobStepRepository


logger = logging.getLogger(__name__)


class VectorReindexApplicationService:
    def __init__(
        self,
        *,
        work_service: WorkService,
        chapter_service: ChapterService,
        job_repository: AIJobRepository,
        step_repository: AIJobStepRepository,
        attempt_repository: AIJobAttemptRepository,
        vector_index_service: VectorIndexService,
    ) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._job_service = AIJobService(
            job_repository=job_repository,
            step_repository=step_repository,
            attempt_repository=attempt_repository,
        )
        self._vector_index_service = vector_index_service

    def start_reindex(
        self,
        *,
        work_id: str,
        index_scope: str,
        target_chapter_ids: list[str] | None = None,
        created_by: str = "user_action",
        idempotency_key: str = "",
        force_rebuild: bool = False,
        reason: str = "",
        source_job_id: str = "",
        auto_run: bool = True,
    ) -> AIJob:
        self._work_service.get_work(work_id)
        normalized_scope = str(index_scope or "").strip()
        if normalized_scope not in {"full_work", "chapter"}:
            raise ValueError("invalid_index_scope")
        normalized_targets = list(dict.fromkeys(str(item).strip() for item in (target_chapter_ids or []) if str(item).strip()))
        if normalized_scope == "chapter" and not normalized_targets:
            raise ValueError("target_chapter_ids_required")
        reusable_job = self._find_reusable_job(
            work_id=work_id,
            index_scope=normalized_scope,
            target_chapter_ids=normalized_targets,
            idempotency_key=idempotency_key,
        )
        if reusable_job is not None:
            return reusable_job.model_copy(
                update={
                    "metadata": {
                        **dict(reusable_job.metadata or {}),
                        "reused_existing_job": True,
                    }
                }
            )
        self._ensure_no_running_job(work_id=work_id)
        job = self._job_service.create_job(
            job_type="vector_indexing",
            work_id=work_id,
            chapter_id=normalized_targets[0] if normalized_scope == "chapter" else None,
            created_by=created_by,
            idempotency_key=str(idempotency_key or ""),
            payload={
                "work_id": work_id,
                "index_scope": normalized_scope,
                "target_chapter_ids_csv": ",".join(normalized_targets),
                "target_chapter_count": len(normalized_targets),
                "force_rebuild": bool(force_rebuild),
                "reason": str(reason or ""),
                "source_job_id": str(source_job_id or ""),
            },
            steps=[
                {
                    "step_type": "build_vector_index",
                    "step_name": "Build Vector Index",
                }
            ],
        )
        logger.info(
            "vector reindex queued job_id=%s work_id=%s index_scope=%s target_chapter_count=%s force_rebuild=%s",
            job.job_id,
            work_id,
            normalized_scope,
            len(normalized_targets),
            bool(force_rebuild),
        )
        return self.run_reindex(job.job_id) if auto_run else job

    def run_reindex(self, job_id: str) -> AIJob:
        job = self._job_service.get_job(job_id)
        if job.status == AIJobStatus.CANCELLED:
            return job
        if job.status in {AIJobStatus.QUEUED, AIJobStatus.PAUSED}:
            self._job_service.start_job(job_id)
        elif job.status == AIJobStatus.COMPLETED:
            return job
        elif job.status == AIJobStatus.FAILED:
            raise ValueError("job_not_runnable")
        step = self._get_build_step(job_id)
        self._job_service.mark_step_running(job_id, step.step_id)
        try:
            result = self._execute_reindex(self._job_service.get_job(job_id))
        except Exception as exc:
            self._job_service.mark_step_failed(
                job_id,
                step.step_id,
                error_code="vector_index_build_failed",
                error_message=str(exc),
            )
            return self._job_service.mark_job_failed(
                job_id,
                error_code="vector_index_build_failed",
                error_message=str(exc),
            )

        current_job = self._job_service.get_job(job_id)
        if current_job.status == AIJobStatus.CANCELLED:
            return current_job

        if result.index_status == "failed":
            logger.warning(
                "vector reindex failed job_id=%s work_id=%s index_scope=%s failed_chunk_count=%s warning_count=%s degraded_reason=%s",
                current_job.job_id,
                current_job.work_id,
                str(current_job.payload.get("index_scope", "") or ""),
                int(result.failed_chunk_count or 0),
                int(result.warning_count or 0),
                str(result.degraded_reason or ""),
            )
            self._job_service.mark_step_failed(
                job_id,
                step.step_id,
                error_code="vector_index_build_failed",
                error_message=result.degraded_reason or "vector_index_build_failed",
                warning_count=max(int(result.warning_count or 0), 0),
            )
            return self._job_service.mark_job_failed(
                job_id,
                error_code="vector_index_build_failed",
                error_message=result.degraded_reason or "vector_index_build_failed",
            )

        step_warning_count = max(int(result.warning_count or 0), 1 if result.index_status == "degraded" else 0)
        logger.info(
            "vector reindex completed job_id=%s work_id=%s index_scope=%s index_status=%s indexed_chapter_count=%s indexed_chunk_count=%s failed_chunk_count=%s warning_count=%s",
            current_job.job_id,
            current_job.work_id,
            str(current_job.payload.get("index_scope", "") or ""),
            result.index_status,
            int(result.indexed_chapter_count or 0),
            int(result.indexed_chunk_count or 0),
            int(result.failed_chunk_count or 0),
            int(result.warning_count or 0),
        )
        self._job_service.mark_step_completed(
            job_id,
            step.step_id,
            summary=self._build_step_summary(result),
            warning_count=step_warning_count,
            status_reason="vector_index_degraded" if result.index_status == "degraded" else "",
        )
        result_summary = self._build_result_summary(job=current_job, result=result)
        return self._job_service.mark_job_completed(
            job_id,
            result_summary=result_summary,
            result_ref=f"vector_index_status:{current_job.work_id}",
        )

    def get_job(self, job_id: str) -> AIJob:
        return self._job_service.get_job(job_id)

    def get_job_steps(self, job_id: str) -> list[AIJobStep]:
        return self._job_service.get_job_steps(job_id)

    def cancel_job(self, job_id: str, *, reason: str) -> AIJob:
        return self._job_service.cancel_job(job_id, reason=reason)

    def pause_job(self, job_id: str, *, reason: str) -> AIJob:
        return self._job_service.pause_job(job_id, reason=reason)

    def resume_job(self, job_id: str, *, reason: str) -> AIJob:
        return self._job_service.resume_job(job_id, reason=reason)

    def retry_job(self, job_id: str) -> AIJob:
        retried = self._job_service.retry_job(job_id)
        for step in self._job_service.get_job_steps(job_id):
            if step.status.value == "failed":
                self._job_service.retry_step(job_id, step.step_id)
        return self._job_service.get_job(retried.job_id)

    def resume_and_run(self, job_id: str, *, reason: str) -> AIJob:
        self._job_service.resume_job(job_id, reason=reason)
        return self.run_reindex(job_id)

    def retry_and_run(self, job_id: str) -> AIJob:
        self.retry_job(job_id)
        return self.run_reindex(job_id)

    def _execute_reindex(self, job: AIJob) -> VectorIndexBuildResult:
        index_scope = str(job.payload.get("index_scope", "") or "")
        should_continue = lambda: self._job_service.get_job(job.job_id).status != AIJobStatus.CANCELLED
        if index_scope == "full_work":
            return self._vector_index_service.reindex_work(job.work_id, should_continue=should_continue)
        target_chapter_ids = self._parse_target_chapter_ids(job)
        results = [
            self._vector_index_service.reindex_chapter(job.work_id, chapter_id, should_continue=should_continue)
            for chapter_id in target_chapter_ids
        ]
        return self._merge_results(results)

    def _find_reusable_job(
        self,
        *,
        work_id: str,
        index_scope: str,
        target_chapter_ids: list[str],
        idempotency_key: str,
    ) -> AIJob | None:
        normalized_key = str(idempotency_key or "").strip()
        if not normalized_key:
            return None
        matched_job: AIJob | None = None
        for job in self._list_vector_jobs(work_id):
            if str(job.idempotency_key or "").strip() != normalized_key:
                continue
            if not self._is_job_within_reuse_window(job):
                continue
            same_scope = str(job.payload.get("index_scope", "") or "") == index_scope
            same_targets = self._parse_target_chapter_ids(job) == target_chapter_ids
            if not same_scope or not same_targets:
                raise ValueError("P2_VECTOR_IDEMPOTENCY_CONFLICT")
            matched_job = job
            break
        return matched_job

    def _ensure_no_running_job(self, *, work_id: str) -> None:
        for job in self._list_vector_jobs(work_id):
            if job.status in {AIJobStatus.QUEUED, AIJobStatus.RUNNING, AIJobStatus.PAUSED}:
                raise ValueError("P2_VECTOR_INDEXING_IN_PROGRESS")

    def _list_vector_jobs(self, work_id: str) -> list[AIJob]:
        return [job for job in self._job_service.list_jobs(work_id=work_id) if job.job_type == "vector_indexing"]

    def _is_job_within_reuse_window(self, job: AIJob) -> bool:
        created_at = str(job.created_at or "").strip()
        if not created_at:
            return False
        try:
            created = datetime.fromisoformat(created_at)
        except ValueError:
            return False
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created >= datetime.now(timezone.utc) - timedelta(hours=24)

    def _merge_results(self, results: list[VectorIndexBuildResult]) -> VectorIndexBuildResult:
        indexed_chapter_count = sum(int(item.indexed_chapter_count or 0) for item in results)
        indexed_chunk_count = sum(int(item.indexed_chunk_count or 0) for item in results)
        failed_chunk_count = sum(int(item.failed_chunk_count or 0) for item in results)
        warnings: list[str] = []
        degraded_reason = ""
        has_degraded = False
        for item in results:
            warnings.extend(str(warning) for warning in item.warnings if str(warning).strip())
            if item.degraded_reason and not degraded_reason:
                degraded_reason = item.degraded_reason
            if item.index_status in {"degraded", "failed"}:
                has_degraded = True
        normalized_warnings = list(dict.fromkeys(warnings))
        if indexed_chunk_count <= 0 and failed_chunk_count > 0:
            index_status = "failed"
        elif has_degraded:
            index_status = "degraded"
        elif indexed_chunk_count > 0:
            index_status = "ready"
        else:
            index_status = "degraded"
        return VectorIndexBuildResult(
            index_status=index_status,
            indexed_chapter_count=indexed_chapter_count,
            indexed_chunk_count=indexed_chunk_count,
            failed_chunk_count=failed_chunk_count,
            warning_count=len(normalized_warnings),
            degraded_reason=degraded_reason if index_status != "ready" else "",
            warnings=normalized_warnings,
        )

    def _get_build_step(self, job_id: str) -> AIJobStep:
        for step in self._job_service.get_job_steps(job_id):
            if step.step_type == "build_vector_index":
                return step
        raise ValueError("build_vector_index_step_not_found")

    def _build_step_summary(self, result: VectorIndexBuildResult) -> str:
        return (
            f"indexed_chapters={int(result.indexed_chapter_count or 0)}; "
            f"indexed_chunks={int(result.indexed_chunk_count or 0)}; "
            f"failed_chunks={int(result.failed_chunk_count or 0)}"
        )

    def _build_result_summary(self, *, job: AIJob, result: VectorIndexBuildResult) -> dict[str, object]:
        summary: dict[str, object] = {
            "index_scope": str(job.payload.get("index_scope", "") or ""),
            "target_chapter_ids": ",".join(self._parse_target_chapter_ids(job)),
            "target_chapter_count": len(self._parse_target_chapter_ids(job)),
            "index_status": result.index_status,
            "indexed_chapter_count": int(result.indexed_chapter_count or 0),
            "indexed_chunk_count": int(result.indexed_chunk_count or 0),
            "failed_chunk_count": int(result.failed_chunk_count or 0),
            "warning_count": int(result.warning_count or 0),
        }
        if result.degraded_reason:
            summary["degraded_reason"] = result.degraded_reason
        if result.warnings:
            summary["warnings"] = list(result.warnings)
        if result.index_status == "degraded" or int(result.failed_chunk_count or 0) > 0:
            summary["completion_mode"] = "partial_success"
        return summary

    def _parse_target_chapter_ids(self, job: AIJob) -> list[str]:
        raw_value = str(job.payload.get("target_chapter_ids_csv", "") or "")
        return [item.strip() for item in raw_value.split(",") if item.strip()]
