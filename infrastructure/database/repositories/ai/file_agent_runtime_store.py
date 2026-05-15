from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import AgentObservation, AgentSession, AgentStep
from domain.repositories.ai.agent_observation_repository import AgentObservationRepository
from domain.repositories.ai.agent_session_repository import AgentSessionRepository
from domain.repositories.ai.agent_step_repository import AgentStepRepository
from infrastructure.database.session import get_database_path


class FileAgentRuntimeStore(AgentSessionRepository, AgentStepRepository, AgentObservationRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("agent_runtime.json")

    def create_session(self, session: AgentSession) -> AgentSession:
        payload = self._load_payload()
        payload["sessions"][session.session_id] = session.model_dump(mode="json")
        self._save_payload(payload)
        return session

    def get_session(self, session_id: str) -> AgentSession:
        payload = self._load_payload()
        raw = payload["sessions"].get(session_id)
        if raw is None:
            raise ValueError("session_not_found")
        return AgentSession.model_validate(raw)

    def save_session(self, session: AgentSession) -> AgentSession:
        return self.create_session(session)

    def list_sessions(self, work_id: str | None = None, status: str | None = None) -> list[AgentSession]:
        payload = self._load_payload()
        items = [AgentSession.model_validate(item) for item in payload["sessions"].values()]
        if work_id:
            items = [item for item in items if item.work_id == work_id]
        if status:
            items = [item for item in items if item.status.value == status]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def create_step(self, step: AgentStep) -> AgentStep:
        payload = self._load_payload()
        payload["steps"][step.step_id] = step.model_dump(mode="json")
        self._save_payload(payload)
        return step

    def get_step(self, step_id: str) -> AgentStep:
        payload = self._load_payload()
        raw = payload["steps"].get(step_id)
        if raw is None:
            raise ValueError("step_not_found")
        return AgentStep.model_validate(raw)

    def save_step(self, step: AgentStep) -> AgentStep:
        return self.create_step(step)

    def list_steps(self, session_id: str) -> list[AgentStep]:
        payload = self._load_payload()
        items = [AgentStep.model_validate(item) for item in payload["steps"].values() if item["session_id"] == session_id]
        return sorted(items, key=lambda item: item.order_index)

    def create_observation(self, observation: AgentObservation) -> AgentObservation:
        payload = self._load_payload()
        payload["observations"][observation.observation_id] = observation.model_dump(mode="json")
        self._save_payload(payload)
        return observation

    def list_observations(self, step_id: str) -> list[AgentObservation]:
        payload = self._load_payload()
        items = [
            AgentObservation.model_validate(item) for item in payload["observations"].values() if item["step_id"] == step_id
        ]
        return sorted(items, key=lambda item: item.created_at)

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return {"sessions": {}, "steps": {}, "observations": {}}
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        payload.setdefault("sessions", {})
        payload.setdefault("steps", {})
        payload.setdefault("observations", {})
        return payload

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
