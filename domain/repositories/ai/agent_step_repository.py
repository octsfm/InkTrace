from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AgentStep


class AgentStepRepository(ABC):
    @abstractmethod
    def create_step(self, step: AgentStep) -> AgentStep:
        raise NotImplementedError

    @abstractmethod
    def get_step(self, step_id: str) -> AgentStep:
        raise NotImplementedError

    @abstractmethod
    def save_step(self, step: AgentStep) -> AgentStep:
        raise NotImplementedError

    @abstractmethod
    def list_steps(self, session_id: str) -> list[AgentStep]:
        raise NotImplementedError
