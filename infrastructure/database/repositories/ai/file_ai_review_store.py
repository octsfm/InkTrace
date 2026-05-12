from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import AIReviewResult
from domain.repositories.ai.ai_review_repository import AIReviewRepository
from infrastructure.database.session import get_database_path


class FileAIReviewStore(AIReviewRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("ai_reviews.json")

    def save(self, review: AIReviewResult) -> AIReviewResult:
        payload = self._load_payload()
        payload[review.review_id] = review.model_dump(mode="json")
        self._save_payload(payload)
        return review

    def get(self, review_id: str) -> AIReviewResult:
        payload = self._load_payload()
        raw = payload.get(review_id)
        if raw is None:
            raise ValueError("review_result_not_found")
        return AIReviewResult.model_validate(raw)

    def list_reviews(
        self,
        *,
        work_id: str,
        chapter_id: str = "",
        candidate_draft_id: str = "",
    ) -> list[AIReviewResult]:
        payload = self._load_payload()
        items = [AIReviewResult.model_validate(item) for item in payload.values() if item.get("work_id") == work_id]
        if chapter_id:
            items = [item for item in items if item.chapter_id == chapter_id]
        if candidate_draft_id:
            items = [item for item in items if item.candidate_draft_id == candidate_draft_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return {}
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
