from application.services.arc_planning_service import ArcPlanningService
from domain.entities.plot_arc import PlotArc


class _FakePlotArcService:
    def __init__(self, arcs):
        self._arcs = arcs

    def list_active_arcs(self, _project_id: str):
        return list(self._arcs)


def _build_arcs():
    return [
        PlotArc(arc_id="a1", project_id="p1", title="主线", arc_type="main_arc", priority="core", status="active", current_stage="setup"),
        PlotArc(arc_id="a2", project_id="p1", title="人物", arc_type="character_arc", priority="major", status="active", current_stage="escalation"),
        PlotArc(arc_id="a3", project_id="p1", title="支线", arc_type="supporting_arc", priority="minor", status="active", current_stage="early_push"),
    ]


def test_arc_planning_defaults_to_light():
    service = ArcPlanningService(_FakePlotArcService(_build_arcs()))
    result = service.select_arcs(project_id="p1", planning_mode="light_planning", allow_deep_planning=False)
    assert result["planning_mode"] == "light_planning"
    assert result["planning_reason"] == "default_light_planning"
    assert result["target_arc"].arc_id == "a1"
    assert len(result["secondary_arcs"]) == 2


def test_arc_planning_auto_triggers_deep_mode():
    service = ArcPlanningService(_FakePlotArcService(_build_arcs()))
    result = service.select_arcs(
        project_id="p1",
        planning_mode="light_planning",
        allow_deep_planning=True,
        preferred_arc_id="a2",
        trigger_context={
            "target_arc_stage": "escalation",
            "chapters_since_target_arc_progress": 3,
            "consistency_warning": True,
        },
    )
    assert result["planning_mode"] == "deep_planning"
    assert "target_arc_near_stage_transition" in result["planning_reason"]
    assert "consistency_warning_detected" in result["planning_reason"]
