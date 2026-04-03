from typing import Dict, List, Optional, Tuple

from application.prompts.prompt_constants import PLANNING_MODE_DEEP, PLANNING_MODE_LIGHT
from application.prompts.prompt_rules import DEEP_PLANNING_TRIGGER_RULES
from application.services.logging_service import build_log_context, get_logger
from application.services.plot_arc_service import PlotArcService
from domain.entities.plot_arc import PlotArc


class ArcPlanningService:
    def __init__(self, plot_arc_service: PlotArcService):
        self.plot_arc_service = plot_arc_service
        self.logger = get_logger(__name__)

    def select_arcs(
        self,
        project_id: str,
        planning_mode: str = PLANNING_MODE_LIGHT,
        preferred_arc_id: str = "",
        allow_deep_planning: bool = False,
        trigger_context: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        active_arcs = self.plot_arc_service.list_active_arcs(project_id)
        effective_mode, trigger_reason = self.resolve_planning_mode(
            requested_mode=planning_mode,
            allow_deep_planning=allow_deep_planning,
            active_arcs=active_arcs,
            preferred_arc_id=preferred_arc_id,
            trigger_context=trigger_context or {},
        )
        if not active_arcs:
            return {
                "target_arc": None,
                "secondary_arcs": [],
                "planning_mode": effective_mode,
                "planning_reason": trigger_reason,
            }
        priority_order = {"core": 0, "major": 1, "minor": 2}
        active_arcs.sort(key=lambda arc: priority_order.get(arc.priority, 3))
        target = self._find_preferred(active_arcs, preferred_arc_id) or active_arcs[0]
        secondary_limit = 2 if effective_mode == PLANNING_MODE_LIGHT else 4
        secondary = [arc for arc in active_arcs if arc.arc_id != target.arc_id][:secondary_limit]
        result = {
            "target_arc": target,
            "secondary_arcs": secondary,
            "planning_mode": effective_mode,
            "planning_reason": trigger_reason,
        }
        self.logger.info(
            "剧情弧规划完成",
            extra=build_log_context(
                event="arc_planning_deep_finished" if effective_mode == PLANNING_MODE_DEEP else "arc_planning_light_finished",
                project_id=project_id,
                arc_id=getattr(target, "arc_id", ""),
                planning_mode=effective_mode,
                reason=trigger_reason,
                secondary_arc_count=len(secondary),
            ),
        )
        return result

    def resolve_planning_mode(
        self,
        requested_mode: str,
        allow_deep_planning: bool,
        active_arcs: List[PlotArc],
        preferred_arc_id: str,
        trigger_context: Dict[str, object],
    ) -> Tuple[str, str]:
        if requested_mode == PLANNING_MODE_DEEP and allow_deep_planning:
            return PLANNING_MODE_DEEP, "manual_deep_planning"
        if not allow_deep_planning:
            return PLANNING_MODE_LIGHT, "default_light_planning"
        reasons = self._collect_deep_trigger_reasons(active_arcs, preferred_arc_id, trigger_context)
        if reasons:
            return PLANNING_MODE_DEEP, "|".join(reasons)
        return PLANNING_MODE_LIGHT, "default_light_planning"

    def _collect_deep_trigger_reasons(
        self,
        active_arcs: List[PlotArc],
        preferred_arc_id: str,
        trigger_context: Dict[str, object],
    ) -> List[str]:
        reasons: List[str] = []
        target_stage = str(trigger_context.get("target_arc_stage") or "")
        chapters_since_progress = int(trigger_context.get("chapters_since_target_arc_progress") or 0)
        consistency_warning = bool(trigger_context.get("consistency_warning") or False)
        preferred_found = any(arc.arc_id == preferred_arc_id for arc in active_arcs) if preferred_arc_id else False
        if preferred_arc_id and preferred_found:
            reasons.append(DEEP_PLANNING_TRIGGER_RULES[0])
        if target_stage in {"escalation", "crisis", "turning_point"}:
            reasons.append(DEEP_PLANNING_TRIGGER_RULES[1])
        if consistency_warning:
            reasons.append(DEEP_PLANNING_TRIGGER_RULES[2])
        if chapters_since_progress >= 3:
            reasons.append(DEEP_PLANNING_TRIGGER_RULES[3])
        if len(active_arcs) >= 5:
            reasons.append(DEEP_PLANNING_TRIGGER_RULES[4])
        return reasons

    def _find_preferred(self, arcs: List[PlotArc], preferred_arc_id: str) -> Optional[PlotArc]:
        if not preferred_arc_id:
            return None
        for arc in arcs:
            if arc.arc_id == preferred_arc_id:
                return arc
        return None
