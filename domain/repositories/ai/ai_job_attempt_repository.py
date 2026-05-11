from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AIJobAttempt


class AIJobAttemptRepository(ABC):
    @abstractmethod
    def create_attempt(self, attempt: AIJobAttempt) -> AIJobAttempt:
        raise NotImplementedError

    @abstractmethod
    def save_attempt(self, attempt: AIJobAttempt) -> AIJobAttempt:
        raise NotImplementedError

    @abstractmethod
    def list_attempts(self, step_id: str) -> list[AIJobAttempt]:
        raise NotImplementedError
