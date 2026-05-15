from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import (
    AIJob,
    AIJobAttempt,
    AIJobAttemptStatus,
    AIJobProgress,
    AIJobStatus,
    AIJobStep,
    AIJobStepStatus,
)
from domain.repositories.ai.ai_job_attempt_repository import AIJobAttemptRepository
from domain.repositories.ai.ai_job_repository import AIJobRepository
from domain.repositories.ai.ai_job_step_repository import AIJobStepRepository


class AIJobService:
    def __init__(
        self,
        job_repository: AIJobRepository,
        step_repository: AIJobStepRepository,
        attempt_repository: AIJobAttemptRepository,
    ) -> None:
        self._job_repository = job_repository
        self._step_repository = step_repository
        self._attempt_repository = attempt_repository

    def create_job(
        self,
        *,
        job_type: str,
        work_id: str,
        chapter_id: str | None = None,
        steps: list[dict[str, object]] | None = None,
        created_by: str = "user_action",
        payload: dict[str, object] | None = None,
    ) -> AIJob:
        now = self._now()
        job = AIJob(
            job_id=f"job_{uuid.uuid4().hex[:12]}",
            work_id=work_id,
            chapter_id=chapter_id,
            job_type=job_type,
            status=AIJobStatus.QUEUED,
            progress=AIJobProgress(total_steps=len(steps or []), status=AIJobStatus.QUEUED.value, updated_at=now),
            created_by=created_by,
            payload=self._sanitize_mapping(payload or {}),
            created_at=now,
            updated_at=now,
        )
        self._job_repository.create_job(job)
        for index, step_payload in enumerate(steps or [], start=1):
            step = AIJobStep(
                step_id=f"step_{uuid.uuid4().hex[:12]}",
                job_id=job.job_id,
                step_type=str(step_payload["step_type"]),
                step_name=str(step_payload.get("step_name") or step_payload["step_type"]),
                status=AIJobStepStatus.PENDING,
                order_index=index,
                label=str(step_payload.get("step_name") or step_payload["step_type"]),
                can_skip=bool(step_payload.get("can_skip", False)),
                metadata=self._sanitize_mapping(step_payload.get("metadata") or {}),
            )
            self._step_repository.create_step(step)
        return self.get_job(job.job_id)

    def get_job(self, job_id: str) -> AIJob:
        job = self._job_repository.get_job(job_id)
        return self._job_repository.save_job(self._sync_progress(job))

    def list_jobs(self, work_id: str | None = None, status: str | None = None) -> list[AIJob]:
        return [self._sync_progress(job) for job in self._job_repository.list_jobs(work_id=work_id, status=status)]

    def get_job_steps(self, job_id: str) -> list[AIJobStep]:
        job = self._job_repository.get_job(job_id)
        steps = [self._enrich_step(step, job.status) for step in self._step_repository.list_steps(job_id)]
        for step in steps:
            self._step_repository.save_step(step)
        return steps

    def add_step(self, job_id: str, *, step_type: str, step_name: str, metadata: dict[str, object] | None = None) -> AIJobStep:
        job = self._job_repository.get_job(job_id)
        order_index = len(self._step_repository.list_steps(job_id)) + 1
        step = AIJobStep(
            step_id=f"step_{uuid.uuid4().hex[:12]}",
            job_id=job.job_id,
            step_type=step_type,
            step_name=step_name,
            status=AIJobStepStatus.PENDING,
            order_index=order_index,
            label=step_name,
            metadata=self._sanitize_mapping(metadata or {}),
        )
        saved = self._step_repository.create_step(step)
        self._job_repository.save_job(self._sync_progress(job))
        return saved

    def start_job(self, job_id: str) -> AIJob:
        job = self._job_repository.get_job(job_id)
        if job.status not in {AIJobStatus.QUEUED, AIJobStatus.PAUSED}:
            raise ValueError("job_not_retryable")
        now = self._now()
        updated = job.model_copy(
            update={
                "status": AIJobStatus.RUNNING,
                "started_at": job.started_at or now,
                "paused_at": "",
                "updated_at": now,
                "status_reason": "",
            }
        )
        return self._job_repository.save_job(self._sync_progress(updated))

    def pause_job(self, job_id: str, *, reason: str) -> AIJob:
        job = self._job_repository.get_job(job_id)
        if job.status not in {AIJobStatus.RUNNING, AIJobStatus.QUEUED}:
            raise ValueError("job_not_pausable")
        now = self._now()
        updated = job.model_copy(
            update={
                "status": AIJobStatus.PAUSED,
                "paused_at": now,
                "updated_at": now,
                "status_reason": reason,
            }
        )
        saved = self._job_repository.save_job(self._sync_progress(updated))
        for step in self._step_repository.list_steps(job_id):
            if step.status == AIJobStepStatus.RUNNING:
                self._step_repository.save_step(
                    self._enrich_step(
                        step.model_copy(update={"status": AIJobStepStatus.PAUSED, "status_reason": reason}),
                        AIJobStatus.PAUSED,
                    )
                )
        return saved

    def mark_step_running(self, job_id: str, step_id: str) -> AIJobStep:
        step = self._get_step(job_id, step_id)
        now = self._now()
        updated = step.model_copy(
            update={
                "status": AIJobStepStatus.RUNNING,
                "started_at": step.started_at or now,
                "finished_at": "",
                "error_code": "",
                "error_message": "",
                "status_reason": "",
            }
        )
        saved = self._step_repository.save_step(updated)
        self._job_repository.save_job(self._sync_progress(self._job_repository.get_job(job_id)))
        return saved

    def mark_step_completed(self, job_id: str, step_id: str, summary: str = "") -> AIJobStep:
        step = self._get_step(job_id, step_id)
        if self._job_repository.get_job(job_id).status == AIJobStatus.CANCELLED:
            return step
        updated = step.model_copy(
            update={
                "status": AIJobStepStatus.COMPLETED,
                "progress": 100,
                "finished_at": self._now(),
                "summary": summary,
                "error_code": "",
                "error_message": "",
                "status_reason": "",
            }
        )
        saved = self._step_repository.save_step(updated)
        self._job_repository.save_job(self._sync_progress(self._job_repository.get_job(job_id)))
        return saved

    def mark_step_failed(self, job_id: str, step_id: str, *, error_code: str, error_message: str) -> AIJobStep:
        step = self._get_step(job_id, step_id)
        updated = step.model_copy(
            update={
                "status": AIJobStepStatus.FAILED,
                "finished_at": self._now(),
                "error_code": error_code,
                "error_message": self._sanitize_text(error_message),
                "attempt_count": step.attempt_count + 1,
            }
        )
        saved = self._step_repository.save_step(updated)
        self._job_repository.save_job(self._sync_progress(self._job_repository.get_job(job_id)))
        return saved

    def mark_step_skipped(self, job_id: str, step_id: str, *, reason: str) -> AIJobStep:
        step = self._get_step(job_id, step_id)
        updated = step.model_copy(
            update={
                "status": AIJobStepStatus.SKIPPED,
                "finished_at": self._now(),
                "status_reason": reason,
                "progress": 100,
            }
        )
        saved = self._step_repository.save_step(updated)
        self._job_repository.save_job(self._sync_progress(self._job_repository.get_job(job_id)))
        return saved

    def mark_job_completed(self, job_id: str, *, result_summary: dict[str, object], result_ref: str = "") -> AIJob:
        job = self._job_repository.get_job(job_id)
        if job.status == AIJobStatus.CANCELLED:
            return self._job_repository.save_job(self._sync_progress(job))
        updated = job.model_copy(
            update={
                "status": AIJobStatus.COMPLETED,
                "updated_at": self._now(),
                "finished_at": self._now(),
                "result_summary": self._sanitize_mapping(result_summary),
                "result_ref": result_ref,
                "error_code": "",
                "error_message": "",
            }
        )
        return self._job_repository.save_job(self._sync_progress(updated))

    def mark_job_failed(self, job_id: str, *, error_code: str, error_message: str) -> AIJob:
        job = self._job_repository.get_job(job_id)
        updated = job.model_copy(
            update={
                "status": AIJobStatus.FAILED,
                "updated_at": self._now(),
                "finished_at": "",
                "error_code": error_code,
                "error_message": self._sanitize_text(error_message),
            }
        )
        return self._job_repository.save_job(self._sync_progress(updated))

    def mark_job_partial_success(self, job_id: str, *, result_summary: dict[str, object]) -> AIJob:
        summary = self._sanitize_mapping(result_summary)
        summary["completion_mode"] = "partial_success"
        return self.mark_job_completed(job_id, result_summary=summary)

    def cancel_job(self, job_id: str, *, reason: str) -> AIJob:
        job = self._job_repository.get_job(job_id)
        if job.status in {AIJobStatus.COMPLETED, AIJobStatus.CANCELLED}:
            return self._job_repository.save_job(self._sync_progress(job))
        updated = job.model_copy(
            update={
                "status": AIJobStatus.CANCELLED,
                "updated_at": self._now(),
                "cancelled_at": self._now(),
                "status_reason": reason,
            }
        )
        return self._job_repository.save_job(self._sync_progress(updated))

    def retry_job(self, job_id: str) -> AIJob:
        job = self._job_repository.get_job(job_id)
        if job.status != AIJobStatus.FAILED:
            raise ValueError("job_not_retryable")
        updated = job.model_copy(
            update={
                "status": AIJobStatus.QUEUED,
                "updated_at": self._now(),
                "error_code": "",
                "error_message": "",
                "finished_at": "",
                "status_reason": "retry_requested",
            }
        )
        return self._job_repository.save_job(self._sync_progress(updated))

    def retry_step(self, job_id: str, step_id: str) -> AIJobStep:
        step = self._get_step(job_id, step_id)
        job = self._job_repository.get_job(job_id)
        if step.status != AIJobStepStatus.FAILED or job.status not in {AIJobStatus.FAILED, AIJobStatus.RUNNING, AIJobStatus.PAUSED, AIJobStatus.QUEUED}:
            raise ValueError("step_not_retryable")
        updated = step.model_copy(
            update={
                "status": AIJobStepStatus.PENDING,
                "started_at": "",
                "finished_at": "",
                "error_code": "",
                "error_message": "",
                "status_reason": "",
            }
        )
        saved = self._step_repository.save_step(self._enrich_step(updated, job.status))
        self._job_repository.save_job(self._sync_progress(job))
        return saved

    def recover_after_restart(self) -> list[str]:
        recovered_job_ids: list[str] = []
        for job in self._job_repository.list_jobs():
            if job.status == AIJobStatus.RUNNING:
                paused_job = job.model_copy(
                    update={
                        "status": AIJobStatus.PAUSED,
                        "paused_at": self._now(),
                        "updated_at": self._now(),
                        "status_reason": "service_restarted",
                    }
                )
                self._job_repository.save_job(self._sync_progress(paused_job))
                for step in self._step_repository.list_steps(job.job_id):
                    if step.status == AIJobStepStatus.RUNNING:
                        self._step_repository.save_step(
                            self._enrich_step(
                                step.model_copy(update={"status": AIJobStepStatus.PAUSED, "status_reason": "service_restarted"}),
                                AIJobStatus.PAUSED,
                            )
                        )
                recovered_job_ids.append(job.job_id)
        return recovered_job_ids

    def record_attempt(
        self,
        *,
        job_id: str,
        step_id: str,
        request_id: str,
        trace_id: str,
        provider_name: str = "",
        model_name: str = "",
        model_role: str = "",
        prompt_key: str = "",
        prompt_version: str = "",
        output_schema_key: str = "",
        status: AIJobAttemptStatus = AIJobAttemptStatus.RUNNING,
        error_code: str = "",
        error_message: str = "",
        retry_reason: str = "",
    ) -> AIJobAttempt:
        attempt_no = len(self._attempt_repository.list_attempts(step_id)) + 1
        attempt = AIJobAttempt(
            attempt_id=f"attempt_{uuid.uuid4().hex[:12]}",
            job_id=job_id,
            step_id=step_id,
            attempt_no=attempt_no,
            request_id=request_id,
            trace_id=trace_id,
            provider_name=provider_name,
            model_name=model_name,
            model_role=model_role,
            prompt_key=prompt_key,
            prompt_version=prompt_version,
            output_schema_key=output_schema_key,
            status=status,
            started_at=self._now(),
            finished_at=self._now() if status != AIJobAttemptStatus.RUNNING else "",
            error_code=error_code,
            error_message=self._sanitize_text(error_message),
            retry_reason=retry_reason,
        )
        return self._attempt_repository.create_attempt(attempt)

    def _get_step(self, job_id: str, step_id: str) -> AIJobStep:
        for step in self._step_repository.list_steps(job_id):
            if step.step_id == step_id:
                job = self._job_repository.get_job(job_id)
                return self._enrich_step(step, job.status)
        raise ValueError("step_not_found")

    def _sync_progress(self, job: AIJob) -> AIJob:
        steps = [self._enrich_step(step, job.status) for step in self._step_repository.list_steps(job.job_id)]
        completed_steps = sum(1 for step in steps if step.status in {AIJobStepStatus.COMPLETED, AIJobStepStatus.SKIPPED})
        failed_steps = sum(1 for step in steps if step.status == AIJobStepStatus.FAILED)
        skipped_steps = sum(1 for step in steps if step.status == AIJobStepStatus.SKIPPED)
        current_step = next((step for step in steps if step.status in {AIJobStepStatus.RUNNING, AIJobStepStatus.PENDING, AIJobStepStatus.PAUSED}), None)
        total_steps = len(steps)
        percent = 100 if total_steps == 0 and job.status == AIJobStatus.COMPLETED else int((completed_steps / total_steps) * 100) if total_steps else 0
        progress = AIJobProgress(
            total_steps=total_steps,
            completed_steps=completed_steps,
            current_step=current_step.step_type if current_step else "",
            current_step_label=current_step.step_name if current_step else "",
            percent=percent,
            status=job.status.value,
            error_code=job.error_code,
            error_message=job.error_message,
            failed_step_count=failed_steps,
            skipped_step_count=skipped_steps,
            updated_at=self._now(),
        )
        return job.model_copy(update={"progress": progress, "updated_at": self._now()})

    def _enrich_step(self, step: AIJobStep, job_status: AIJobStatus) -> AIJobStep:
        can_retry = step.status == AIJobStepStatus.FAILED and job_status not in {AIJobStatus.CANCELLED, AIJobStatus.COMPLETED} and step.attempt_count < step.max_attempts
        can_skip = step.can_skip and step.status == AIJobStepStatus.FAILED and job_status not in {AIJobStatus.CANCELLED, AIJobStatus.COMPLETED}
        return step.model_copy(update={"can_retry": can_retry, "can_skip": can_skip})

    def _sanitize_text(self, value: str) -> str:
        text = str(value or "")
        return text.replace("\n", " ").strip()[:300]

    def _sanitize_mapping(self, value: dict[str, object]) -> dict[str, object]:
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if any(token in key.lower() for token in ("prompt", "content", "api_key", "text")):
                continue
            if isinstance(item, (str, int, float, bool)) or item is None:
                sanitized[key] = item
            else:
                sanitized[key] = str(item)
        return sanitized

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
