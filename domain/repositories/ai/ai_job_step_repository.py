from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AIJobStep


class AIJobStepRepository(ABC):
    @abstractmethod
    def create_step(self, step: AIJobStep) -> AIJobStep:
        raise NotImplementedError

    @abstractmethod
    def save_step(self, step: AIJobStep) -> AIJobStep:
        raise NotImplementedError

    @abstractmethod
    def list_steps(self, job_id: str) -> list[AIJobStep]:
        raise NotImplementedError
