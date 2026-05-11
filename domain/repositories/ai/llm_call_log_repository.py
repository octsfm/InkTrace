from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import LLMCallLog


class LLMCallLogRepository(ABC):
    @abstractmethod
    def append(self, entry: LLMCallLog) -> None:
        raise NotImplementedError
