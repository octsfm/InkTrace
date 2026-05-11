from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import StoryStateSnapshot
from domain.repositories.ai.story_state_repository import StoryStateRepository
from infrastructure.database.session import get_database_path


class FileStoryStateStore(StoryStateRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("story_state_snapshots.json")

    def save_analysis_baseline(self, story_state: StoryStateSnapshot) -> StoryStateSnapshot:
        payload = self._load_payload()
        payload[story_state.story_state_id] = story_state.model_dump(mode="json")
        self._save_payload(payload)
        return story_state

    def get_latest_analysis_baseline_by_work(self, work_id: str) -> StoryStateSnapshot | None:
        payload = self._load_payload()
        items = [StoryStateSnapshot.model_validate(item) for item in payload.values() if item.get("work_id") == work_id]
        if not items:
            return None
        return sorted(items, key=lambda item: item.created_at, reverse=True)[0]

    def mark_story_state_stale(self, story_state_id: str, stale_reason: str) -> StoryStateSnapshot | None:
        payload = self._load_payload()
        raw = payload.get(story_state_id)
        if raw is None:
            return None
        story_state = StoryStateSnapshot.model_validate(raw).model_copy(
            update={"stale_status": "stale", "stale_reason": stale_reason}
        )
        payload[story_state_id] = story_state.model_dump(mode="json")
        self._save_payload(payload)
        return story_state

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return {}
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
