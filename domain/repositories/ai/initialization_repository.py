from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import InitializationRecord


class InitializationRepository(ABC):
    @abstractmethod
    def save(self, initialization: InitializationRecord) -> InitializationRecord:
        raise NotImplementedError

    @abstractmethod
    def get(self, initialization_id: str) -> InitializationRecord:
        raise NotImplementedError

    @abstractmethod
    def get_by_job_id(self, job_id: str) -> InitializationRecord | None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_by_work(self, work_id: str) -> InitializationRecord | None:
        raise NotImplementedError
