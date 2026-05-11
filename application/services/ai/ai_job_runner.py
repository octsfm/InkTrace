from __future__ import annotations

from collections.abc import Callable

from application.services.ai.ai_job_service import AIJobService
from domain.entities.ai.models import AIJob


JobHandler = Callable[[str, AIJobService], None]


class AIJobRunner:
    def __init__(self, job_service: AIJobService) -> None:
        self._job_service = job_service
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    def run(self, job_id: str) -> AIJob:
        job = self._job_service.get_job(job_id)
        handler = self._handlers.get(job.job_type)
        if handler is None:
            raise ValueError("job_handler_not_registered")
        started = self._job_service.start_job(job_id)
        try:
            handler(job_id, self._job_service)
        except Exception as exc:
            return self._job_service.mark_job_failed(job_id, error_code="job_handler_failed", error_message=str(exc))
        return self._job_service.get_job(started.job_id)
