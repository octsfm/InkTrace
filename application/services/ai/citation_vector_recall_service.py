from __future__ import annotations

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService


class CitationVectorRecallService:
    """Minimal runtime recall adapter for citation verification queries."""

    def __init__(self, *, work_service: WorkService, chapter_service: ChapterService, writing_asset_service) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._writing_asset_service = writing_asset_service

    def recall(self, query):  # noqa: ANN001
        if not isinstance(query, dict):
            return []
        source_type = str(query.get("source_type") or "").strip()
        source_id = str(query.get("source_id") or "").strip()
        query_text = str(query.get("query_text") or "").strip()

        if source_type == "chapter":
            return self._recall_chapter(source_id=source_id, query_text=query_text)
        if source_type == "event":
            return self._recall_event(source_id=source_id, query_text=query_text)
        return []

    def _recall_chapter(self, *, source_id: str, query_text: str) -> list[dict[str, object]]:
        for work in self._work_service.list_works():
            for chapter in self._chapter_service.list_chapters(work.id):
                if chapter.id.value != source_id:
                    continue
                return [
                    {
                        "source_id": chapter.id.value,
                        "content_text": str(chapter.content or "")[:120],
                        "score": self._score(query_text=query_text, content_text=str(chapter.content or "")),
                    }
                ]
        return []

    def _recall_event(self, *, source_id: str, query_text: str) -> list[dict[str, object]]:
        for work in self._work_service.list_works():
            for item in self._writing_asset_service.list_timeline_events(work.id):
                if item.id != source_id:
                    continue
                description = str(item.description or "")
                return [
                    {
                        "source_id": item.id,
                        "content_text": description[:120],
                        "score": self._score(query_text=query_text, content_text=description),
                    }
                ]
        return []

    def _score(self, *, query_text: str, content_text: str) -> float:
        normalized_query = self._normalize(query_text)
        normalized_content = self._normalize(content_text)
        if not normalized_query or not normalized_content:
            return 0.0
        if normalized_query in normalized_content or normalized_content in normalized_query:
            return 0.98
        if self._has_fragment_match(normalized_query, normalized_content):
            return 0.93
        query_chars = {char for char in normalized_query if not char.isspace()}
        content_chars = {char for char in normalized_content if not char.isspace()}
        if not query_chars or not content_chars:
            return 0.0
        overlap = len(query_chars & content_chars) / max(len(query_chars), 1)
        if overlap <= 0:
            return 0.0
        return round(min(0.69, 0.45 + overlap * 0.4), 2)

    def _has_fragment_match(self, query_text: str, content_text: str) -> bool:
        if len(query_text) < 2:
            return False
        for size in range(min(4, len(query_text)), 1, -1):
            for index in range(0, len(query_text) - size + 1):
                fragment = query_text[index : index + size].strip()
                if fragment and fragment in content_text:
                    return True
        return False

    def _normalize(self, value: str) -> str:
        return "".join(str(value or "").strip().split())
