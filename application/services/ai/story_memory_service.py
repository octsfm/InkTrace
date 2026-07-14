from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import (
    ChapterAnalysisResult,
    HierarchicalStorySummary,
    InitializationRecord,
    OutlineAnalysisResult,
    StoryMemorySnapshot,
)
from domain.repositories.ai.story_memory_repository import StoryMemoryRepository
from domain.services.ai.character_names import normalize_character_names


class StoryMemoryService:
    def __init__(self, repository: StoryMemoryRepository) -> None:
        self._repository = repository

    def build_snapshot(
        self,
        *,
        initialization: InitializationRecord,
        outline_analysis: OutlineAnalysisResult,
        chapter_results: list[ChapterAnalysisResult],
        hierarchical_story_summary: HierarchicalStorySummary,
    ) -> StoryMemorySnapshot:
        successful = [item for item in chapter_results if item.status.value == "succeeded"]
        character_states = self._latest_character_states(successful)
        setting_facts = self._unique_dicts(
            [dict(value) for item in successful for value in item.setting_fact_delta],
            key="description",
        )
        foreshadow_candidates = self._unique_dicts(
            [dict(value) for item in successful for value in item.foreshadow_candidate_delta],
            key="description",
        )
        unresolved_questions = self._unique(
            [value for item in successful for value in item.unresolved_threads]
        )
        timeline_facts = self._unique([value for item in successful for value in item.timeline_info])
        warnings = self._unique([value for item in successful for value in item.warnings])
        confidence = (
            sum(float(item.analysis_confidence or 0.0) for item in successful) / len(chapter_results)
            if chapter_results
            else 0.0
        )
        now = self._now()
        snapshot = StoryMemorySnapshot(
            snapshot_id=f"memory_{uuid.uuid4().hex[:12]}",
            work_id=initialization.work_id,
            source_initialization_id=initialization.initialization_id,
            source_job_id=initialization.job_id,
            source_chapter_ids=[item.chapter_id for item in chapter_results],
            source_chapter_versions=initialization.source_chapter_versions,
            global_summary=hierarchical_story_summary.global_summary,
            chapter_summaries=[
                {"chapter_id": item.chapter_id, "chapter_title": item.chapter_title, "summary": item.summary}
                for item in successful
            ],
            stage_summaries=list(hierarchical_story_summary.stage_summaries),
            volume_summaries=list(hierarchical_story_summary.volume_summaries),
            characters=normalize_character_names([name for item in successful for name in item.characters]),
            locations=self._unique([name for item in successful for name in item.locations]),
            plot_threads=self._unique(
                [*hierarchical_story_summary.main_plot_threads, *[name for item in successful for name in item.unresolved_threads]]
            ),
            scene_details=[scene for item in successful for scene in item.scene_details][:20],
            source_analysis_version=initialization.initialization_id,
            chapter_analysis_ids=[f"{item.chapter_id}@{item.chapter_version}" for item in successful],
            current_story_summary={
                "summary": hierarchical_story_summary.global_summary,
                "current_story_phase": hierarchical_story_summary.current_story_phase,
                "analyzed_chapter_count": len(successful),
                "total_chapter_count": len(chapter_results),
            },
            character_states=character_states,
            setting_facts=setting_facts,
            foreshadow_candidates=foreshadow_candidates,
            unresolved_questions=self._unique(
                [*hierarchical_story_summary.unresolved_questions, *unresolved_questions]
            ),
            timeline_facts=timeline_facts,
            warnings=self._unique([*warnings, *hierarchical_story_summary.warnings]),
            confidence=max(0.0, min(confidence, hierarchical_story_summary.analysis_confidence, 1.0)),
            created_at=now,
            updated_at=now,
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

    def _latest_character_states(self, chapter_results: list[ChapterAnalysisResult]) -> list[dict[str, object]]:
        latest: dict[str, dict[str, object]] = {}
        order: list[str] = []
        for item in chapter_results:
            for raw_state in item.character_state_delta:
                state = dict(raw_state)
                name = str(state.get("character_name") or "").strip()
                if not name:
                    continue
                if name not in order:
                    order.append(name)
                latest[name] = state
        return [latest[name] for name in order]

    @staticmethod
    def _unique_dicts(items: list[dict[str, object]], *, key: str) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        seen: set[str] = set()
        for item in items:
            identity = str(item.get(key) or "").strip()
            if not identity or identity in seen:
                continue
            seen.add(identity)
            result.append(item)
        return result

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
