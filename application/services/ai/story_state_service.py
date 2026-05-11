from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import ChapterAnalysisResult, InitializationRecord, StoryMemorySnapshot, StoryStateSnapshot
from domain.repositories.ai.story_state_repository import StoryStateRepository


class StoryStateService:
    def __init__(self, repository: StoryStateRepository) -> None:
        self._repository = repository

    def build_analysis_baseline(
        self,
        *,
        initialization: InitializationRecord,
        story_memory_snapshot: StoryMemorySnapshot,
        chapter_results: list[ChapterAnalysisResult],
    ) -> StoryStateSnapshot:
        successful = [item for item in chapter_results if item.status.value == "succeeded"]
        latest = successful[-1]
        story_state = StoryStateSnapshot(
            story_state_id=f"state_{uuid.uuid4().hex[:12]}",
            work_id=initialization.work_id,
            source_initialization_id=initialization.initialization_id,
            source_job_id=initialization.job_id,
            latest_chapter_id=latest.chapter_id,
            latest_chapter_version=latest.chapter_version,
            current_position_summary=latest.summary,
            active_characters=self._unique([name for item in successful[-3:] for name in item.characters]),
            active_locations=self._unique([name for item in successful[-3:] for name in item.locations]),
            unresolved_threads=self._unique([name for item in successful for name in item.unresolved_threads]),
            continuity_notes=[f"baseline_source=confirmed_chapter_analysis", f"source_snapshot_id={story_memory_snapshot.snapshot_id}"],
            source_snapshot_id=story_memory_snapshot.snapshot_id,
            created_at=self._now(),
        )
        return self._repository.save_analysis_baseline(story_state)

    def get_latest_analysis_baseline_by_work(self, work_id: str) -> StoryStateSnapshot | None:
        return self._repository.get_latest_analysis_baseline_by_work(work_id)

    def mark_story_state_stale(self, story_state_id: str, stale_reason: str) -> StoryStateSnapshot | None:
        return self._repository.mark_story_state_stale(story_state_id, stale_reason)

    def _unique(self, items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            clean = str(item or "").strip()
            if clean and clean not in result:
                result.append(clean)
        return result

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
