from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import ChapterAnalysisResult, InitializationRecord, OutlineAnalysisResult, StoryMemorySnapshot
from domain.repositories.ai.story_memory_repository import StoryMemoryRepository


class StoryMemoryService:
    def __init__(self, repository: StoryMemoryRepository) -> None:
        self._repository = repository

    def build_snapshot(
        self,
        *,
        initialization: InitializationRecord,
        outline_analysis: OutlineAnalysisResult,
        chapter_results: list[ChapterAnalysisResult],
    ) -> StoryMemorySnapshot:
        successful = [item for item in chapter_results if item.status.value == "succeeded"]
        global_summary_parts = [outline_analysis.global_summary] + [item.summary for item in successful if item.summary]
        snapshot = StoryMemorySnapshot(
            snapshot_id=f"memory_{uuid.uuid4().hex[:12]}",
            work_id=initialization.work_id,
            source_initialization_id=initialization.initialization_id,
            source_job_id=initialization.job_id,
            source_chapter_ids=[item.chapter_id for item in chapter_results],
            source_chapter_versions=initialization.source_chapter_versions,
            global_summary=" ".join(part for part in global_summary_parts if part).strip()[:800],
            chapter_summaries=[
                {"chapter_id": item.chapter_id, "chapter_title": item.chapter_title, "summary": item.summary}
                for item in successful
            ],
            characters=self._unique([name for item in successful for name in item.characters]),
            locations=self._unique([name for item in successful for name in item.locations]),
            plot_threads=self._unique([name for item in successful for name in item.unresolved_threads or item.plot_points]),
            created_at=self._now(),
        )
        return self._repository.save_snapshot(snapshot)

    def get_latest_snapshot_by_work(self, work_id: str) -> StoryMemorySnapshot | None:
        return self._repository.get_latest_snapshot_by_work(work_id)

    def mark_snapshot_stale(self, snapshot_id: str, stale_reason: str) -> StoryMemorySnapshot | None:
        return self._repository.mark_snapshot_stale(snapshot_id, stale_reason)

    def _unique(self, items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            clean = str(item or "").strip()
            if clean and clean not in result:
                result.append(clean)
        return result

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
