from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import ContextPackSnapshot
from domain.repositories.ai.context_pack_repository import ContextPackRepository
from infrastructure.database.session import get_database_path


class FileContextPackStore(ContextPackRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("context_packs.json")

    def save(self, snapshot: ContextPackSnapshot) -> ContextPackSnapshot:
        payload = self._load_payload()
        payload[snapshot.context_pack_id] = snapshot.model_dump(mode="json")
        self._save_payload(payload)
        return snapshot

    def get(self, context_pack_id: str) -> ContextPackSnapshot:
        payload = self._load_payload()
        raw = payload.get(context_pack_id)
        if raw is None:
            raise ValueError("context_pack_not_found")
        return ContextPackSnapshot.model_validate(raw)

    def get_latest_by_work(self, work_id: str, chapter_id: str = "") -> ContextPackSnapshot | None:
        payload = self._load_payload()
        items = [ContextPackSnapshot.model_validate(item) for item in payload.values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        if not items:
            return None
        return sorted(items, key=lambda item: item.created_at, reverse=True)[0]

    def list_by_work(self, work_id: str) -> list[ContextPackSnapshot]:
        payload = self._load_payload()
        items = [ContextPackSnapshot.model_validate(item) for item in payload.values() if item.get("work_id") == work_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return {}
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
