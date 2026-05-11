from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import InitializationRecord
from domain.repositories.ai.initialization_repository import InitializationRepository
from infrastructure.database.session import get_database_path


class FileInitializationStore(InitializationRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("ai_initializations.json")

    def save(self, initialization: InitializationRecord) -> InitializationRecord:
        payload = self._load_payload()
        payload[initialization.initialization_id] = initialization.model_dump(mode="json")
        self._save_payload(payload)
        return initialization

    def get(self, initialization_id: str) -> InitializationRecord:
        payload = self._load_payload()
        raw = payload.get(initialization_id)
        if raw is None:
            raise ValueError("initialization_not_found")
        return InitializationRecord.model_validate(raw)

    def get_by_job_id(self, job_id: str) -> InitializationRecord | None:
        payload = self._load_payload()
        for item in payload.values():
            if item.get("job_id") == job_id:
                return InitializationRecord.model_validate(item)
        return None

    def get_latest_by_work(self, work_id: str) -> InitializationRecord | None:
        payload = self._load_payload()
        items = [InitializationRecord.model_validate(item) for item in payload.values() if item.get("work_id") == work_id]
        if not items:
            return None
        return sorted(items, key=lambda item: item.created_at, reverse=True)[0]

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return {}
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
