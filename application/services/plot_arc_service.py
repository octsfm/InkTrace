from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List

from application.services.logging_service import build_log_context, get_logger
from domain.entities.plot_arc import PlotArc
from domain.repositories.plot_arc_repository import IPlotArcRepository


class PlotArcService:
    def __init__(self, plot_arc_repo: IPlotArcRepository):
        self.plot_arc_repo = plot_arc_repo
        self.logger = get_logger(__name__)

    def list_arcs(self, project_id: str) -> List[PlotArc]:
        arcs = self.plot_arc_repo.find_by_project(project_id)
        changed = False
        for arc in arcs:
            if self._repair_arc_for_display(arc):
                self.plot_arc_repo.save(arc)
                changed = True
        return self.plot_arc_repo.find_by_project(project_id) if changed else arcs

    def list_active_arcs(self, project_id: str) -> List[PlotArc]:
        arcs = self.list_arcs(project_id)
        return [arc for arc in arcs if arc.status == "active"]

    def _compact_arc_text(self, value: str, fallback: str = "") -> str:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            return fallback
        if len(text) <= 90:
            return text
        return f"{text[:90].rstrip('，；。,. ')}..."

    def _repair_arc_for_display(self, arc: PlotArc) -> bool:
        changed = False
        title = str(arc.title or "").strip()
        if title.lower() == "main story arc":
            arc.title = "主线推进弧"
            changed = True
        elif title.lower().endswith(" character arc"):
            arc.title = f"{title[:-14].strip()}人物弧" if title[:-14].strip() else "人物成长弧"
            changed = True
        elif title.lower() in {"supporting pressure arc", "supporting world arc"}:
            arc.title = "支线压力弧"
            changed = True

        compact_summary = self._compact_arc_text(arc.latest_progress_summary or "")
        if compact_summary and compact_summary != (arc.latest_progress_summary or ""):
            arc.latest_progress_summary = compact_summary
            changed = True

        compact_push = self._compact_arc_text(arc.next_push_suggestion or "")
        if not compact_push:
            compact_push = {
                "main_arc": "继续推进当前主线冲突。",
                "character_arc": "继续施加人物选择与代价。",
                "supporting_arc": "让支线因素重新影响主线。",
            }.get(arc.arc_type, "继续推进当前剧情冲突。")
        if compact_push != (arc.next_push_suggestion or ""):
            arc.next_push_suggestion = compact_push
            changed = True

        return changed

    def clear_project_arcs(self, project_id: str) -> None:
        if hasattr(self.plot_arc_repo, "delete_by_project"):
            self.plot_arc_repo.delete_by_project(project_id)

    def _normalize_arc_type(self, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"main", "mainline", "main_story"}:
            normalized = "main_arc"
        elif normalized in {"character", "character_story"}:
            normalized = "character_arc"
        elif normalized in {"support", "supporting", "sub"}:
            normalized = "supporting_arc"
        if normalized not in {"main_arc", "character_arc", "supporting_arc"}:
            return "supporting_arc"
        return normalized

    def _normalize_priority(self, value: str, arc_type: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"core", "major", "minor"}:
            return normalized
        if arc_type == "main_arc":
            return "core"
        if arc_type == "character_arc":
            return "major"
        return "minor"

    def _normalize_status(self, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"active", "dormant", "completed", "archived"}:
            return normalized
        return "active"

    def _normalize_stage(self, value: str, covered_count: int, status: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"setup", "early_push", "escalation", "crisis", "turning_point", "payoff", "aftermath"}:
            return normalized
        if status == "completed":
            return "payoff"
        if status == "archived":
            return "aftermath"
        if covered_count >= 14:
            return "turning_point"
        if covered_count >= 9:
            return "crisis"
        if covered_count >= 5:
            return "escalation"
        if covered_count >= 3:
            return "early_push"
        return "setup"

    def _normalize_arc_record(self, project_id: str, item: Dict[str, object], chapter_ids: List[str]) -> PlotArc:
        covered_chapter_ids = [str(x).strip() for x in (item.get("covered_chapter_ids") or chapter_ids) if str(x).strip()][:30]
        arc_type = self._normalize_arc_type(str(item.get("arc_type") or "supporting_arc"))
        priority = self._normalize_priority(str(item.get("priority") or ""), arc_type)
        status = self._normalize_status(str(item.get("status") or "active"))
        current_stage = self._normalize_stage(str(item.get("current_stage") or ""), len(covered_chapter_ids), status)
        stage_reason = str(item.get("stage_reason") or "").strip() or f"normalized_from_{max(1, len(covered_chapter_ids))}_chapters"
        try:
            stage_confidence = float(item.get("stage_confidence") or 0.0)
        except (TypeError, ValueError):
            stage_confidence = 0.0
        if stage_confidence <= 0:
            stage_confidence = 0.45 + min(0.4, len(covered_chapter_ids) * 0.04)
        return PlotArc(
            arc_id=str(item.get("arc_id") or f"arc_{uuid.uuid4().hex[:10]}").strip(),
            project_id=project_id,
            title=str(item.get("title") or "Untitled Arc").strip(),
            arc_type=arc_type,
            priority=priority,
            status=status,
            goal=str(item.get("goal") or "").strip(),
            core_conflict=str(item.get("core_conflict") or "").strip(),
            stakes=str(item.get("stakes") or "").strip(),
            start_chapter_number=int(item.get("start_chapter_number") or 0),
            end_chapter_number=int(item.get("end_chapter_number") or 0),
            current_stage=current_stage,
            stage_reason=stage_reason,
            stage_confidence=max(0.35, min(0.95, stage_confidence)),
            key_turning_points=[str(x).strip() for x in (item.get("key_turning_points") or []) if str(x).strip()][:8],
            must_resolve_points=[str(x).strip() for x in (item.get("must_resolve_points") or []) if str(x).strip()][:8],
            related_characters=[str(x).strip() for x in (item.get("related_characters") or []) if str(x).strip()][:8],
            related_items=[str(x).strip() for x in (item.get("related_items") or []) if str(x).strip()][:8],
            related_world_rules=[str(x).strip() for x in (item.get("related_world_rules") or []) if str(x).strip()][:8],
            covered_chapter_ids=covered_chapter_ids,
            latest_progress_summary=str(item.get("latest_progress_summary") or "").strip(),
            latest_result=str(item.get("latest_result") or "").strip(),
            next_push_suggestion=str(item.get("next_push_suggestion") or "").strip(),
        )

    def extract_initial_arcs(self, project_id: str, memory: Dict[str, object], chapter_ids: List[str]) -> List[PlotArc]:
        declared_arcs = [item for item in (memory.get("plot_arcs") or []) if isinstance(item, dict)]
        if declared_arcs:
            existing = self.plot_arc_repo.find_by_project(project_id)
            if not existing:
                for item in declared_arcs:
                    arc = self._normalize_arc_record(project_id, item, chapter_ids)
                    self.plot_arc_repo.save(arc)
                    self.logger.info(
                        "剧情弧抽取完成",
                        extra=build_log_context(
                            event="plot_arc_extracted",
                            project_id=project_id,
                            arc_id=arc.arc_id,
                            arc_type=arc.arc_type,
                            status=arc.status,
                            priority=arc.priority,
                        ),
                    )
                self.enforce_active_arc_limit(project_id, limit=5, minimum=3)
            return self.plot_arc_repo.find_by_project(project_id)

        existing = self.plot_arc_repo.find_by_project(project_id)
        if existing:
            return existing
        main_plot_lines = [str(x).strip() for x in (memory.get("main_plot_lines") or []) if str(x).strip()]
        world_lines = [str(x).strip() for x in (memory.get("world_summary") or []) if str(x).strip()]
        characters = [str((x or {}).get("name") or "").strip() for x in (memory.get("main_characters") or [])]
        arcs: List[PlotArc] = []
        if main_plot_lines:
            arcs.append(
                PlotArc(
                    arc_id=f"arc_{uuid.uuid4().hex[:10]}",
                    project_id=project_id,
                    title="主线推进弧",
                    arc_type="main_arc",
                    priority="core",
                    status="active",
                    goal=main_plot_lines[0],
                    core_conflict=main_plot_lines[1] if len(main_plot_lines) > 1 else main_plot_lines[0],
                    current_stage="setup",
                    stage_reason="fallback_from_main_plot_lines",
                    covered_chapter_ids=chapter_ids[:5],
                    latest_progress_summary=main_plot_lines[0][:80],
                    next_push_suggestion="继续推进当前主线冲突。",
                )
            )
        if characters:
            arcs.append(
                PlotArc(
                    arc_id=f"arc_{uuid.uuid4().hex[:10]}",
                    project_id=project_id,
                    title=f"{characters[0]}人物弧",
                    arc_type="character_arc",
                    priority="major",
                    status="active",
                    goal=f"Push the key change of {characters[0]}",
                    core_conflict=f"{characters[0]} must choose between goal and cost",
                    current_stage="setup",
                    stage_reason="fallback_from_character_summary",
                    related_characters=[characters[0]],
                    covered_chapter_ids=chapter_ids[:5],
                    latest_progress_summary="Character arc initialized.",
                    next_push_suggestion=f"在下一章让{characters[0]}承担新的代价。",
                )
            )
        if world_lines:
            arcs.append(
                PlotArc(
                    arc_id=f"arc_{uuid.uuid4().hex[:10]}",
                    project_id=project_id,
                    title="支线压力弧",
                    arc_type="supporting_arc",
                    priority="minor",
                    status="dormant",
                    goal=world_lines[0],
                    core_conflict=world_lines[0],
                    current_stage="setup",
                    stage_reason="fallback_from_world_summary",
                    related_world_rules=world_lines[:3],
                    covered_chapter_ids=chapter_ids[:3],
                    latest_progress_summary=world_lines[0][:80],
                    next_push_suggestion="让支线设定重新影响主线推进。",
                )
            )
        for arc in arcs[:5]:
            self.plot_arc_repo.save(arc)
            self.logger.info(
                "剧情弧抽取完成",
                extra=build_log_context(
                    event="plot_arc_extracted",
                    project_id=project_id,
                    arc_id=arc.arc_id,
                    arc_type=arc.arc_type,
                    status=arc.status,
                    priority=arc.priority,
                ),
            )
        self.enforce_active_arc_limit(project_id, limit=5, minimum=3)
        return self.plot_arc_repo.find_by_project(project_id)

    def enforce_active_arc_limit(self, project_id: str, limit: int = 5, minimum: int = 3) -> None:
        arcs = self.plot_arc_repo.find_by_project(project_id)
        active = [arc for arc in arcs if arc.status == "active"]
        priority_order = {"core": 0, "major": 1, "minor": 2}
        if len(active) < minimum:
            dormant = [arc for arc in arcs if arc.status == "dormant"]
            dormant.sort(key=lambda x: priority_order.get(x.priority, 3))
            for arc in dormant[: max(0, minimum - len(active))]:
                arc.status = "active"
                arc.updated_at = datetime.now()
                self.plot_arc_repo.save(arc)
                self.logger.info(
                    "剧情弧恢复活跃",
                    extra=build_log_context(event="plot_arc_activated", project_id=project_id, arc_id=arc.arc_id),
                )
            active = [arc for arc in self.plot_arc_repo.find_by_project(project_id) if arc.status == "active"]
        if len(active) <= limit:
            return
        active.sort(key=lambda x: priority_order.get(x.priority, 3))
        for arc in active[limit:]:
            arc.status = "dormant"
            arc.updated_at = datetime.now()
            self.plot_arc_repo.save(arc)
            self.logger.info(
                "剧情弧降为休眠",
                extra=build_log_context(event="plot_arc_dormanted", project_id=project_id, arc_id=arc.arc_id),
            )
