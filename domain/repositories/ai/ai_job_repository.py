from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AIJob


class AIJobRepository(ABC):
    @abstractmethod
    def create_job(self, job: AIJob) -> AIJob:
        raise NotImplementedError

    @abstractmethod
    def get_job(self, job_id: str) -> AIJob:
        raise NotImplementedError

    @abstractmethod
    def save_job(self, job: AIJob) -> AIJob:
        raise NotImplementedError

    @abstractmethod
    def list_jobs(self, work_id: str | None = None, status: str | None = None) -> list[AIJob]:
        raise NotImplementedError
