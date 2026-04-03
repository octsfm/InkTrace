from application.services.plot_arc_service import PlotArcService
from domain.entities.plot_arc import PlotArc
from infrastructure.persistence.sqlite_plot_arc_repo import SQLitePlotArcRepository


def test_plot_arc_service_restores_minimum_active_arcs(tmp_path):
    db_path = str(tmp_path / "plot_arc_window.db")
    repo = SQLitePlotArcRepository(db_path)
    service = PlotArcService(repo)
    repo.save(PlotArc(arc_id="core_active", project_id="p1", title="主线", arc_type="main_arc", priority="core", status="active"))
    repo.save(PlotArc(arc_id="core_dormant", project_id="p1", title="人物", arc_type="character_arc", priority="core", status="dormant"))
    repo.save(PlotArc(arc_id="major_dormant", project_id="p1", title="支线", arc_type="supporting_arc", priority="major", status="dormant"))
    repo.save(PlotArc(arc_id="minor_dormant", project_id="p1", title="余波", arc_type="supporting_arc", priority="minor", status="dormant"))

    service.enforce_active_arc_limit("p1", limit=5, minimum=3)

    active_ids = [arc.arc_id for arc in service.list_active_arcs("p1")]
    assert len(active_ids) == 3
    assert "core_active" in active_ids
    assert "core_dormant" in active_ids
    assert "major_dormant" in active_ids
    assert "minor_dormant" not in active_ids


def test_plot_arc_service_normalizes_declared_arcs(tmp_path):
    db_path = str(tmp_path / "plot_arc_normalized.db")
    repo = SQLitePlotArcRepository(db_path)
    service = PlotArcService(repo)

    arcs = service.extract_initial_arcs(
        "p2",
        {
            "plot_arcs": [
                {
                    "arc_id": "arc_a",
                    "title": "主线推进",
                    "arc_type": "mainline",
                    "priority": "",
                    "status": "unknown",
                    "current_stage": "",
                    "covered_chapter_ids": ["c1", "c2", "c3", "c4", "c5"],
                },
                {
                    "arc_id": "arc_b",
                    "title": "角色压力",
                    "arc_type": "character",
                    "priority": "important",
                    "status": "active",
                    "current_stage": "invalid",
                    "covered_chapter_ids": ["c1", "c2", "c3"],
                },
                {
                    "arc_id": "arc_c",
                    "title": "世界规则",
                    "arc_type": "support",
                    "priority": "low",
                    "status": "dormant",
                    "current_stage": "",
                    "covered_chapter_ids": ["c1"],
                },
            ]
        },
        ["c1", "c2", "c3", "c4", "c5"],
    )

    arc_map = {arc.arc_id: arc for arc in arcs}
    assert arc_map["arc_a"].arc_type == "main_arc"
    assert arc_map["arc_a"].priority == "core"
    assert arc_map["arc_a"].status == "active"
    assert arc_map["arc_a"].current_stage == "escalation"
    assert arc_map["arc_b"].arc_type == "character_arc"
    assert arc_map["arc_b"].priority == "major"
    assert arc_map["arc_b"].current_stage == "early_push"
    assert arc_map["arc_c"].arc_type == "supporting_arc"
    assert arc_map["arc_c"].priority == "minor"

    active_ids = [arc.arc_id for arc in service.list_active_arcs("p2")]
    assert len(active_ids) == 3
