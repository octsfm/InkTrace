import pytest

from application.services.v1.work_service import WorkService
from application.services.v1.writing_asset_service import WritingAssetService
from infrastructure.database.repositories import (
    ChapterOutlineRepo,
    ChapterRepo,
    ForeshadowRepo,
    TimelineEventRepo,
    WorkOutlineRepo,
    WorkRepo,
)
from infrastructure.database.session import get_database_path, initialize_database


def setup_db(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def build_service():
    return WritingAssetService(
        work_repo=WorkRepo(),
        chapter_repo=ChapterRepo(),
        work_outline_repo=WorkOutlineRepo(),
        chapter_outline_repo=ChapterOutlineRepo(),
        timeline_event_repo=TimelineEventRepo(),
        foreshadow_repo=ForeshadowRepo(),
    )


def create_work():
    return WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")


def test_writing_asset_service_foreshadow_default_open_and_status_switch(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-foreshadow")
    work = create_work()
    chapter = ChapterRepo().list_by_work(work.id)[0]
    service = build_service()

    open_item = service.create_foreshadow(work.id, {
        "title": "伏笔一",
        "description": "描述",
        "introduced_chapter_id": chapter.id.value,
    })
    resolved_item = service.create_foreshadow(work.id, {
        "title": "伏笔二",
        "status": "resolved",
        "resolved_chapter_id": chapter.id.value,
    })

    assert [item.id for item in service.list_foreshadows(work.id)] == [open_item.id]
    assert [item.id for item in service.list_foreshadows(work.id, "resolved")] == [resolved_item.id]

    updated = service.update_foreshadow(
        open_item.id,
        {"status": "resolved", "resolved_chapter_id": chapter.id.value},
        expected_version=1,
    )
    assert updated.status == "resolved"
    assert updated.resolved_chapter_id == chapter.id.value
    assert updated.version == 2

    get_database_path.cache_clear()


def test_writing_asset_service_foreshadow_version_conflict(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-foreshadow-conflict")
    work = create_work()
    service = build_service()
    item = service.create_foreshadow(work.id, {"title": "伏笔"})

    with pytest.raises(ValueError, match="asset_version_conflict"):
        service.update_foreshadow(item.id, {"title": "冲突"}, expected_version=0)

    get_database_path.cache_clear()


def test_writing_asset_service_foreshadow_rejects_invalid_status_and_chapter(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-foreshadow-invalid")
    work = create_work()
    service = build_service()

    with pytest.raises(ValueError, match="invalid_input"):
        service.create_foreshadow(work.id, {"title": "伏笔", "status": "closed"})
    with pytest.raises(ValueError, match="invalid_input"):
        service.create_foreshadow(work.id, {"title": "伏笔", "introduced_chapter_id": "missing"})

    get_database_path.cache_clear()


def test_writing_asset_service_foreshadow_delete(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-foreshadow-delete")
    work = create_work()
    service = build_service()
    item = service.create_foreshadow(work.id, {"title": "伏笔"})

    service.delete_foreshadow(item.id)

    assert service.list_foreshadows(work.id, None) == []
    get_database_path.cache_clear()
