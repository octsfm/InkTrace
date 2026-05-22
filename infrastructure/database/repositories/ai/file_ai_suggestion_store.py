from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import AISuggestion, AISuggestionBatch
from domain.repositories.ai.ai_suggestion_repository import AISuggestionRepository
from infrastructure.database.session import get_database_path


class FileAISuggestionStore(AISuggestionRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("ai_suggestions.json")

    def save(self, suggestion: AISuggestion) -> AISuggestion:
        payload = self._load_payload()
        payload["suggestions"][suggestion.suggestion_id] = suggestion.model_dump(mode="json", exclude={"is_expired"})
        self._save_payload(payload)
        return suggestion

    def get(self, suggestion_id: str) -> AISuggestion:
        payload = self._load_payload()
        raw = payload["suggestions"].get(suggestion_id)
        if raw is None:
            raise ValueError("ai_suggestion_not_found")
        return AISuggestion.model_validate(raw)

    def list_suggestions(
        self,
        *,
        work_id: str,
        chapter_id: str = "",
        target_ref_id: str = "",
    ) -> list[AISuggestion]:
        payload = self._load_payload()
        items = [AISuggestion.model_validate(item) for item in payload["suggestions"].values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        if target_ref_id:
            items = [item for item in items if item.target.target_ref_id == target_ref_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_batch(self, batch: AISuggestionBatch) -> AISuggestionBatch:
        payload = self._load_payload()
        payload["batches"][batch.batch_id] = batch.model_dump(mode="json")
        self._save_payload(payload)
        return batch

    def get_batch(self, batch_id: str) -> AISuggestionBatch:
        payload = self._load_payload()
        raw = payload["batches"].get(batch_id)
        if raw is None:
            raise ValueError("ai_suggestion_batch_not_found")
        return AISuggestionBatch.model_validate(raw)

    def _load_payload(self) -> dict[str, dict[str, dict[str, object]]]:
        if not self._file_path.exists():
            return {"suggestions": {}, "batches": {}}
        raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        if "suggestions" in raw or "batches" in raw:
            return {
                "suggestions": dict(raw.get("suggestions", {})),
                "batches": dict(raw.get("batches", {})),
            }
        return {"suggestions": dict(raw), "batches": {}}

    def _save_payload(self, payload: dict[str, dict[str, dict[str, object]]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
