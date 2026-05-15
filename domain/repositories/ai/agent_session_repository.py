from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AgentSession


class AgentSessionRepository(ABC):
    @abstractmethod
    def create_session(self, session: AgentSession) -> AgentSession:
        raise NotImplementedError

    @abstractmethod
    def get_session(self, session_id: str) -> AgentSession:
        raise NotImplementedError

    @abstractmethod
    def save_session(self, session: AgentSession) -> AgentSession:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(self, work_id: str | None = None, status: str | None = None) -> list[AgentSession]:
        raise NotImplementedError
