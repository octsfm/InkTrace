from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import ChapterAnalysisResult, InitializationRecord, StoryMemorySnapshot, StoryStateSnapshot
from domain.repositories.ai.story_state_repository import StoryStateRepository
from domain.services.ai.character_names import normalize_character_names


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
        recent = successful[-3:]
        current_character_states = self._latest_character_states(recent)
        active_characters = [
            str(item.get("character_name") or "").strip()
            for item in current_character_states
            if str(item.get("character_name") or "").strip()
        ]
        active_locations = self._unique([name for item in recent for name in item.locations])
        unresolved_questions = self._unique([name for item in successful for name in item.unresolved_threads])
        active_conflicts = self._unique(
            [name for item in recent for name in (item.deviations_from_outline + item.unresolved_threads)]
        )
        active_foreshadows = self._unique_dicts(
            [dict(value) for item in successful for value in item.foreshadow_candidate_delta],
            key="description",
        )
        important_setting_facts = self._unique_dicts(
            [dict(value) for item in recent for value in item.setting_fact_delta],
            key="description",
        )
        timeline = self._unique([value for item in successful for value in item.timeline_info])
        recent_key_events = self._unique([value for item in recent for value in item.plot_points])
        hierarchical_phase = str(story_memory_snapshot.current_story_summary.get("current_story_phase") or "").strip()
        confidence = sum(float(item.analysis_confidence or 0.0) for item in successful) / len(successful)
        now = self._now()
        story_state = StoryStateSnapshot(
            story_state_id=f"state_{uuid.uuid4().hex[:12]}",
            work_id=initialization.work_id,
            source_initialization_id=initialization.initialization_id,
            source_job_id=initialization.job_id,
            latest_chapter_id=latest.chapter_id,
            latest_chapter_version=latest.chapter_version,
            current_position_summary=latest.summary,
            active_characters=normalize_character_names(active_characters),
            active_locations=active_locations,
            unresolved_threads=unresolved_questions,
            continuity_notes=[f"baseline_source=confirmed_chapter_analysis", f"source_snapshot_id={story_memory_snapshot.snapshot_id}"],
            source_snapshot_id=story_memory_snapshot.snapshot_id,
            source_chapter_analysis_ids=[f"{item.chapter_id}@{item.chapter_version}" for item in successful],
            current_chapter_id=latest.chapter_id,
            current_chapter_order=chapter_results.index(latest) + 1,
            current_story_phase=hierarchical_phase or str(latest.plot_progress or latest.chapter_position or latest.summary),
            current_time_position=timeline[-1] if timeline else "",
            current_character_states=current_character_states,
            active_conflicts=active_conflicts,
            active_foreshadows=active_foreshadows,
            resolved_foreshadows=[],
            important_setting_facts=important_setting_facts,
            current_location_scope=active_locations,
            recent_key_events=recent_key_events,
            unresolved_questions=unresolved_questions,
            analysis_confidence=max(0.0, min(confidence, 1.0)),
            created_at=now,
            updated_at=now,
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

    @staticmethod
    def _latest_character_states(chapter_results: list[ChapterAnalysisResult]) -> list[dict[str, object]]:
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
