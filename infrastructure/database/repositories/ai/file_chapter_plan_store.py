from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import ChapterPlan
from domain.repositories.ai.chapter_plan_repository import ChapterPlanRepository
from infrastructure.database.session import get_database_path


class FileChapterPlanStore(ChapterPlanRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("chapter_plans.json")

    def save(self, plan: ChapterPlan) -> ChapterPlan:
        payload = self._load_payload()
        payload[plan.chapter_plan_id] = plan.model_dump(mode="json")
        self._save_payload(payload)
        return plan

    def get(self, chapter_plan_id: str) -> ChapterPlan:
        payload = self._load_payload()
        raw = payload.get(chapter_plan_id)
        if raw is None:
            raise ValueError("chapter_plan_not_found")
        return ChapterPlan.model_validate(raw)

    def list_by_work(self, work_id: str, chapter_id: str = "") -> list[ChapterPlan]:
        payload = self._load_payload()
        items = [ChapterPlan.model_validate(item) for item in payload.values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        return sorted(items, key=lambda item: (item.created_at, item.chapter_plan_id), reverse=True)

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return {}
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
