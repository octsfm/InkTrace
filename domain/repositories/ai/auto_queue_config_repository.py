from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AutoQueueConfig


class AutoQueueConfigRepository(ABC):
    @abstractmethod
    def save(self, config: AutoQueueConfig) -> AutoQueueConfig:
        raise NotImplementedError

    @abstractmethod
    def get_by_work(self, work_id: str) -> AutoQueueConfig | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, config_id: str) -> AutoQueueConfig | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, config: AutoQueueConfig) -> AutoQueueConfig:
        raise NotImplementedError
