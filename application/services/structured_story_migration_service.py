import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Tuple

from domain.entities.chapter_analysis_memory import ChapterAnalysisMemory
from domain.entities.chapter_arc_binding import ChapterArcBinding
from domain.entities.chapter_continuation_memory import ChapterContinuationMemory
from domain.entities.chapter_task import ChapterTask
from domain.entities.arc_progress_snapshot import ArcProgressSnapshot
from domain.entities.detemplated_draft import DetemplatedDraft
from domain.entities.draft_integrity_check import DraftIntegrityCheck
from domain.entities.global_constraints import GlobalConstraints
from domain.entities.plot_arc import PlotArc
from domain.entities.structural_draft import StructuralDraft
from domain.entities.style_requirements import StyleRequirements
from domain.constants.story_constants import DEFAULT_FORESHADOWING_ACTION, DEFAULT_HOOK_STRENGTH
from domain.constants.story_enums import (
    GENERATION_STAGE_DETEMPLATED,
    GENERATION_STAGE_STRUCTURAL,
    STYLE_SOURCE_MANUAL,
    WRITING_STATUS_READY,
)
from presentation.api.dependencies import (
    DB_PATH,
    get_chapter_analysis_memory_repo,
    get_chapter_continuation_memory_repo,
    get_chapter_task_repo,
    get_detemplated_draft_repo,
    get_draft_integrity_check_repo,
    get_global_constraints_repo,
    get_plot_arc_repo,
    get_arc_progress_snapshot_repo,
    get_chapter_arc_binding_repo,
    get_structural_draft_repo,
    get_style_requirements_repo,
    get_v2_repo,
)


class StructuredStoryMigrationService:
    def __init__(self):
        self.v2_repo = get_v2_repo()
        self.global_constraints_repo = get_global_constraints_repo()
        self.chapter_analysis_memory_repo = get_chapter_analysis_memory_repo()
        self.chapter_continuation_memory_repo = get_chapter_continuation_memory_repo()
        self.chapter_task_repo = get_chapter_task_repo()
        self.plot_arc_repo = get_plot_arc_repo()
        self.arc_progress_snapshot_repo = get_arc_progress_snapshot_repo()
        self.chapter_arc_binding_repo = get_chapter_arc_binding_repo()
        self.structural_draft_repo = get_structural_draft_repo()
        self.detemplated_draft_repo = get_detemplated_draft_repo()
        self.draft_integrity_check_repo = get_draft_integrity_check_repo()
        self.style_requirements_repo = get_style_requirements_repo()

    def run(self) -> Dict[str, int]:
        rows = self._scan_unmigrated_active_rows()
        migrated = 0
        skipped = 0
        for project_id, raw in rows:
            if not project_id:
                skipped += 1
                continue
            if self._migrate_project(project_id, raw):
                migrated += 1
            else:
                skipped += 1
        return {"migrated_projects": migrated, "skipped": skipped}

    def _scan_unmigrated_active_rows(self) -> List[Tuple[str, sqlite3.Row]]:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            columns = {row[1] for row in conn.execute("PRAGMA table_info(project_memories)").fetchall()}
            active_filter = " WHERE is_active = 1" if "is_active" in columns else ""
            if "structured_story_migrated" in columns:
                sql = f"SELECT * FROM project_memories{active_filter} {'AND' if active_filter else 'WHERE'} COALESCE(structured_story_migrated, 0) = 0"
            else:
                sql = f"SELECT * FROM project_memories{active_filter}"
            rows = conn.execute(sql).fetchall()
            return [(str(row["project_id"] or ""), row) for row in rows]

    def _safe_json(self, text: Any, default):
        try:
            value = json.loads(text or "")
        except Exception:
            return default
        return value if isinstance(value, type(default)) else default

    def _stable_id(self, prefix: str, project_id: str, payload: Dict[str, Any]) -> str:
        seed = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_URL, f'{project_id}:{seed}').hex[:12]}"

    def _normalize_foreshadowing_action(self, value: str) -> str:
        mapping = {"advance": "推进", "bury": "埋", "retrieve": "回收", "推进": "推进", "埋": "埋", "回收": "回收"}
        return mapping.get(str(value or "").strip(), "推进")

    def _normalize_hook_strength(self, value: str) -> str:
        mapping = {"weak": "弱", "medium": "中", "strong": "强", "弱": "弱", "中": "中", "强": "强"}
        return mapping.get(str(value or "").strip(), "中")

    def _migrate_project(self, project_id: str, row: sqlite3.Row) -> bool:
        now = datetime.now()
        global_constraints = self._safe_json(row["global_constraints_json"], {})
        if isinstance(global_constraints, dict) and any(global_constraints.values()):
            self.global_constraints_repo.save(
                GlobalConstraints(
                    id=str(global_constraints.get("id") or f"gc_{project_id}"),
                    project_id=project_id,
                    main_plot=str(global_constraints.get("main_plot") or ""),
                    hidden_plot=str(global_constraints.get("hidden_plot") or ""),
                    core_selling_points=[str(x) for x in (global_constraints.get("core_selling_points") or [])],
                    protagonist_core_traits=[str(x) for x in (global_constraints.get("protagonist_core_traits") or [])],
                    must_keep_threads=[str(x) for x in (global_constraints.get("must_keep_threads") or [])],
                    genre_guardrails=[str(x) for x in (global_constraints.get("genre_guardrails") or [])],
                    source_type=str(global_constraints.get("source_type") or STYLE_SOURCE_MANUAL),
                    version=int(global_constraints.get("version") or 1),
                    created_at=now,
                    updated_at=now,
                )
            )
        style = self._safe_json(row["style_requirements_json"], {})
        if isinstance(style, dict):
            self.style_requirements_repo.save(
                StyleRequirements(
                    id=str(style.get("id") or f"style_{project_id}"),
                    project_id=project_id,
                    author_voice_keywords=[str(x) for x in (style.get("author_voice_keywords") or [])],
                    avoid_patterns=[str(x) for x in (style.get("avoid_patterns") or [])],
                    preferred_rhythm=str(style.get("preferred_rhythm") or ""),
                    narrative_distance=str(style.get("narrative_distance") or ""),
                    dialogue_density=str(style.get("dialogue_density") or ""),
                    source_type=str(style.get("source_type") or STYLE_SOURCE_MANUAL),
                    version=int(style.get("version") or 1),
                    created_at=now,
                    updated_at=now,
                )
            )
        for item in self._safe_json(row["chapter_analysis_memories_json"], []):
            if isinstance(item, dict):
                self.chapter_analysis_memory_repo.save(ChapterAnalysisMemory(id=str(item.get("id") or self._stable_id("cam", project_id, item)), chapter_id=str(item.get("chapter_id") or ""), chapter_number=int(item.get("chapter_number") or 0), chapter_title=str(item.get("chapter_title") or ""), summary=str(item.get("summary") or ""), events=[str(x) for x in (item.get("events") or [])], plot_role=str(item.get("plot_role") or ""), conflict=str(item.get("conflict") or ""), foreshadowing=[str(x) for x in (item.get("foreshadowing") or [])], hook=str(item.get("hook") or ""), problems=[str(x) for x in (item.get("problems") or [])], version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in self._safe_json(row["chapter_continuation_memories_json"], []):
            if isinstance(item, dict):
                self.chapter_continuation_memory_repo.save(ChapterContinuationMemory(id=str(item.get("id") or self._stable_id("ccm", project_id, item)), chapter_id=str(item.get("chapter_id") or ""), chapter_number=int(item.get("chapter_number") or 0), chapter_title=str(item.get("chapter_title") or ""), scene_summary=str(item.get("scene_summary") or ""), scene_state=item.get("scene_state") or {}, protagonist_state=item.get("protagonist_state") or {}, active_characters=item.get("active_characters") or [], active_conflicts=[str(x) for x in (item.get("active_conflicts") or [])], immediate_threads=[str(x) for x in (item.get("immediate_threads") or [])], long_term_threads=[str(x) for x in (item.get("long_term_threads") or [])], recent_reveals=[str(x) for x in (item.get("recent_reveals") or [])], must_continue_points=[str(x) for x in (item.get("must_continue_points") or [])], forbidden_jumps=[str(x) for x in (item.get("forbidden_jumps") or [])], tone_and_pacing=item.get("tone_and_pacing") or {}, last_hook=str(item.get("last_hook") or ""), version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in self._safe_json(row["chapter_tasks_json"], []):
            if isinstance(item, dict):
                self.chapter_task_repo.save(ChapterTask(id=str(item.get("id") or self._stable_id("task", project_id, item)), chapter_id=str(item.get("chapter_id") or ""), project_id=project_id, branch_id=str(item.get("branch_id") or ""), chapter_number=int(item.get("chapter_number") or 0), chapter_function=str(item.get("chapter_function") or ""), goals=[str(x) for x in (item.get("goals") or [])], must_continue_points=[str(x) for x in (item.get("must_continue_points") or [])], forbidden_jumps=[str(x) for x in (item.get("forbidden_jumps") or [])], required_foreshadowing_action=self._normalize_foreshadowing_action(str(item.get("required_foreshadowing_action") or DEFAULT_FORESHADOWING_ACTION)), required_hook_strength=self._normalize_hook_strength(str(item.get("required_hook_strength") or DEFAULT_HOOK_STRENGTH)), pace_target=str(item.get("pace_target") or ""), opening_continuation=str(item.get("opening_continuation") or ""), chapter_payoff=str(item.get("chapter_payoff") or ""), style_bias=str(item.get("style_bias") or ""), status=str(item.get("status") or WRITING_STATUS_READY), version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in self._safe_json(row["structural_drafts_json"], []):
            if isinstance(item, dict):
                self.structural_draft_repo.save(StructuralDraft(id=str(item.get("id") or self._stable_id("struct", project_id, item)), chapter_id=str(item.get("chapter_id") or ""), project_id=project_id, chapter_number=int(item.get("chapter_number") or 0), title=str(item.get("title") or ""), content=str(item.get("content") or ""), source_task_id=str(item.get("source_task_id") or ""), model_name=str(item.get("model_name") or ""), used_fallback=bool(item.get("used_fallback")), generation_stage=str(item.get("generation_stage") or GENERATION_STAGE_STRUCTURAL), version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in self._safe_json(row["detemplated_drafts_json"], []):
            if isinstance(item, dict):
                self.detemplated_draft_repo.save(DetemplatedDraft(id=str(item.get("id") or self._stable_id("det", project_id, item)), chapter_id=str(item.get("chapter_id") or ""), project_id=project_id, chapter_number=int(item.get("chapter_number") or 0), title=str(item.get("title") or ""), content=str(item.get("content") or ""), based_on_structural_draft_id=str(item.get("based_on_structural_draft_id") or ""), style_requirements_snapshot=item.get("style_requirements_snapshot") or {}, model_name=str(item.get("model_name") or ""), used_fallback=bool(item.get("used_fallback")), generation_stage=str(item.get("generation_stage") or GENERATION_STAGE_DETEMPLATED), version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in self._safe_json(row["draft_integrity_checks_json"], []):
            if isinstance(item, dict):
                self.draft_integrity_check_repo.save(DraftIntegrityCheck(id=str(item.get("id") or self._stable_id("check", project_id, item)), chapter_id=str(item.get("chapter_id") or ""), project_id=project_id, structural_draft_id=str(item.get("structural_draft_id") or ""), detemplated_draft_id=str(item.get("detemplated_draft_id") or ""), event_integrity_ok=bool(item.get("event_integrity_ok")), motivation_integrity_ok=bool(item.get("motivation_integrity_ok")), foreshadowing_integrity_ok=bool(item.get("foreshadowing_integrity_ok")), hook_integrity_ok=bool(item.get("hook_integrity_ok")), continuity_ok=bool(item.get("continuity_ok")), arc_consistency_ok=bool(item.get("arc_consistency_ok", True)), title_alignment_ok=bool(item.get("title_alignment_ok", True)), progression_integrity_ok=bool(item.get("progression_integrity_ok", True)), risk_notes=[str(x) for x in (item.get("risk_notes") or [])], issue_list=[issue for issue in (item.get("issue_list") or []) if isinstance(issue, dict)], revision_suggestion=str(item.get("revision_suggestion") or ""), revision_attempted=bool(item.get("revision_attempted")), revision_succeeded=bool(item.get("revision_succeeded")), created_at=now))
        for item in self._safe_json(row["plot_arcs_json"] if "plot_arcs_json" in row.keys() else "[]", []):
            if isinstance(item, dict):
                self.plot_arc_repo.save(
                    PlotArc(
                        arc_id=str(item.get("arc_id") or self._stable_id("arc", project_id, item)),
                        project_id=project_id,
                        title=str(item.get("title") or "Migrated Arc"),
                        arc_type=str(item.get("arc_type") or "supporting_arc"),
                        priority=str(item.get("priority") or "minor"),
                        status=str(item.get("status") or "active"),
                        goal=str(item.get("goal") or ""),
                        core_conflict=str(item.get("core_conflict") or ""),
                        stakes=str(item.get("stakes") or ""),
                        start_chapter_number=int(item.get("start_chapter_number") or 0),
                        end_chapter_number=int(item.get("end_chapter_number") or 0),
                        current_stage=str(item.get("current_stage") or "setup"),
                        stage_reason=str(item.get("stage_reason") or ""),
                        stage_confidence=float(item.get("stage_confidence") or 0.6),
                        key_turning_points=[str(x) for x in (item.get("key_turning_points") or [])],
                        must_resolve_points=[str(x) for x in (item.get("must_resolve_points") or [])],
                        related_characters=[str(x) for x in (item.get("related_characters") or [])],
                        related_items=[str(x) for x in (item.get("related_items") or [])],
                        related_world_rules=[str(x) for x in (item.get("related_world_rules") or [])],
                        covered_chapter_ids=[str(x) for x in (item.get("covered_chapter_ids") or [])],
                        latest_progress_summary=str(item.get("latest_progress_summary") or ""),
                        latest_result=str(item.get("latest_result") or ""),
                        next_push_suggestion=str(item.get("next_push_suggestion") or ""),
                        created_at=now,
                        updated_at=now,
                    )
                )
        for item in self._safe_json(row["chapter_arc_bindings_json"] if "chapter_arc_bindings_json" in row.keys() else "[]", []):
            if isinstance(item, dict):
                self.chapter_arc_binding_repo.save(
                    ChapterArcBinding(
                        binding_id=str(item.get("binding_id") or self._stable_id("binding", project_id, item)),
                        project_id=project_id,
                        chapter_id=str(item.get("chapter_id") or ""),
                        arc_id=str(item.get("arc_id") or ""),
                        binding_role=str(item.get("binding_role") or "background"),
                        push_type=str(item.get("push_type") or "advance"),
                        confidence=float(item.get("confidence") or 0.6),
                        created_at=now,
                    )
                )
        for item in self._safe_json(row["arc_progress_snapshots_json"] if "arc_progress_snapshots_json" in row.keys() else "[]", []):
            if isinstance(item, dict):
                self.arc_progress_snapshot_repo.save(
                    ArcProgressSnapshot(
                        snapshot_id=str(item.get("snapshot_id") or self._stable_id("snapshot", project_id, item)),
                        arc_id=str(item.get("arc_id") or ""),
                        chapter_id=str(item.get("chapter_id") or ""),
                        chapter_number=int(item.get("chapter_number") or 0),
                        stage_before=str(item.get("stage_before") or "setup"),
                        stage_after=str(item.get("stage_after") or "setup"),
                        progress_summary=str(item.get("progress_summary") or ""),
                        change_reason=str(item.get("change_reason") or ""),
                        new_conflicts=[str(x) for x in (item.get("new_conflicts") or [])],
                        new_payoffs=[str(x) for x in (item.get("new_payoffs") or [])],
                        created_at=now,
                    )
                )
        self.v2_repo.mark_structured_story_migrated(project_id)
        return True
