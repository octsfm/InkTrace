from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import AISettings
from domain.repositories.ai.ai_settings_repository import AISettingsRepository
from infrastructure.database.session import get_database_path


class FileAISettingsStore(AISettingsRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("ai_settings.json")

    def load(self) -> AISettings:
        if not self._file_path.exists():
            return AISettings()
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        return AISettings.model_validate(payload)

    def save(self, settings: AISettings) -> AISettings:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(settings.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        return settings
