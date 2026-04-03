from application.services.arc_writeback_service import ArcWritebackService
from domain.entities.plot_arc import PlotArc
from infrastructure.persistence.sqlite_arc_progress_snapshot_repo import SQLiteArcProgressSnapshotRepository
from infrastructure.persistence.sqlite_chapter_arc_binding_repo import SQLiteChapterArcBindingRepository
from infrastructure.persistence.sqlite_plot_arc_repo import SQLitePlotArcRepository


def test_arc_writeback_advances_stage_with_transition_signal(tmp_path):
    db_path = str(tmp_path / "arc_writeback.db")
    arc_repo = SQLitePlotArcRepository(db_path)
    snapshot_repo = SQLiteArcProgressSnapshotRepository(db_path)
    binding_repo = SQLiteChapterArcBindingRepository(db_path)
    service = ArcWritebackService(arc_repo, snapshot_repo, binding_repo)
    arc = PlotArc(
        arc_id="arc_1",
        project_id="p1",
        title="主线弧",
        arc_type="main_arc",
        priority="core",
        status="active",
        current_stage="setup",
    )
    arc_repo.save(arc)
    service.writeback_chapter_arc(
        project_id="p1",
        chapter_id="c1",
        chapter_number=1,
        target_arc_id="arc_1",
        progress_summary="本章目标明确且阻力出现，线索已抛出",
    )
    updated = arc_repo.find_by_id("arc_1")
    assert updated is not None
    assert updated.current_stage == "early_push"
    assert len(snapshot_repo.list_by_arc("arc_1")) == 1
    assert len(binding_repo.list_by_chapter("c1")) == 1


def test_arc_writeback_keeps_stage_without_transition_signal(tmp_path):
    db_path = str(tmp_path / "arc_writeback_2.db")
    arc_repo = SQLitePlotArcRepository(db_path)
    snapshot_repo = SQLiteArcProgressSnapshotRepository(db_path)
    binding_repo = SQLiteChapterArcBindingRepository(db_path)
    service = ArcWritebackService(arc_repo, snapshot_repo, binding_repo)
    arc = PlotArc(
        arc_id="arc_2",
        project_id="p1",
        title="支线弧",
        arc_type="supporting_arc",
        priority="minor",
        status="active",
        current_stage="early_push",
    )
    arc_repo.save(arc)
    service.writeback_chapter_arc(
        project_id="p1",
        chapter_id="c2",
        chapter_number=2,
        target_arc_id="arc_2",
        progress_summary="本章承接前情，信息增量有限，主要进行情绪铺垫",
    )
    updated = arc_repo.find_by_id("arc_2")
    assert updated is not None
    assert updated.current_stage == "early_push"
