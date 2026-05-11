from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import AIJob, AIJobAttempt, AIJobStep
from domain.repositories.ai.ai_job_attempt_repository import AIJobAttemptRepository
from domain.repositories.ai.ai_job_repository import AIJobRepository
from domain.repositories.ai.ai_job_step_repository import AIJobStepRepository
from infrastructure.database.session import get_database_path


class FileAIJobStore(AIJobRepository, AIJobStepRepository, AIJobAttemptRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("ai_jobs.json")

    def create_job(self, job: AIJob) -> AIJob:
        payload = self._load_payload()
        payload["jobs"][job.job_id] = job.model_dump(mode="json")
        self._save_payload(payload)
        return job

    def get_job(self, job_id: str) -> AIJob:
        payload = self._load_payload()
        raw = payload["jobs"].get(job_id)
        if raw is None:
            raise ValueError("job_not_found")
        return AIJob.model_validate(raw)

    def save_job(self, job: AIJob) -> AIJob:
        return self.create_job(job)

    def list_jobs(self, work_id: str | None = None, status: str | None = None) -> list[AIJob]:
        payload = self._load_payload()
        items = [AIJob.model_validate(item) for item in payload["jobs"].values()]
        if work_id:
            items = [item for item in items if item.work_id == work_id]
        if status:
            items = [item for item in items if item.status.value == status]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def create_step(self, step: AIJobStep) -> AIJobStep:
        payload = self._load_payload()
        payload["steps"][step.step_id] = step.model_dump(mode="json")
        self._save_payload(payload)
        return step

    def save_step(self, step: AIJobStep) -> AIJobStep:
        return self.create_step(step)

    def list_steps(self, job_id: str) -> list[AIJobStep]:
        payload = self._load_payload()
        items = [AIJobStep.model_validate(item) for item in payload["steps"].values() if item["job_id"] == job_id]
        return sorted(items, key=lambda item: item.order_index)

    def create_attempt(self, attempt: AIJobAttempt) -> AIJobAttempt:
        payload = self._load_payload()
        payload["attempts"][attempt.attempt_id] = attempt.model_dump(mode="json")
        self._save_payload(payload)
        return attempt

    def save_attempt(self, attempt: AIJobAttempt) -> AIJobAttempt:
        return self.create_attempt(attempt)

    def list_attempts(self, step_id: str) -> list[AIJobAttempt]:
        payload = self._load_payload()
        items = [AIJobAttempt.model_validate(item) for item in payload["attempts"].values() if item["step_id"] == step_id]
        return sorted(items, key=lambda item: item.attempt_no)

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return {"jobs": {}, "steps": {}, "attempts": {}}
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        payload.setdefault("jobs", {})
        payload.setdefault("steps", {})
        payload.setdefault("attempts", {})
        return payload

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
