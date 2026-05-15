from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AgentObservation


class AgentObservationRepository(ABC):
    @abstractmethod
    def create_observation(self, observation: AgentObservation) -> AgentObservation:
        raise NotImplementedError

    @abstractmethod
    def list_observations(self, step_id: str) -> list[AgentObservation]:
        raise NotImplementedError
