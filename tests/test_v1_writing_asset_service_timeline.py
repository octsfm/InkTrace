import pytest

from application.services.v1.work_service import WorkService
from application.services.v1.writing_asset_service import WritingAssetService
from infrastructure.database.repositories import (
    ChapterOutlineRepo,
    ChapterRepo,
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
    )


def create_work():
    return WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")


def test_writing_asset_service_timeline_crud(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-timeline-crud")
    work = create_work()
    chapter = ChapterRepo().list_by_work(work.id)[0]
    service = build_service()

    first = service.create_timeline_event(work.id, {
        "title": "事件一",
        "description": "描述一",
        "chapter_id": chapter.id.value,
    })
    second = service.create_timeline_event(work.id, {"title": "事件二"})

    assert [item.id for item in service.list_timeline_events(work.id)] == [first.id, second.id]
    assert first.order_index == 1
    assert second.order_index == 2

    updated = service.update_timeline_event(
        first.id,
        {"title": "事件一更新", "chapter_id": None},
        expected_version=1,
    )
    assert updated.title == "事件一更新"
    assert updated.chapter_id is None
    assert updated.version == 2

    service.delete_timeline_event(second.id)
    assert [item.id for item in service.list_timeline_events(work.id)] == [first.id]
    get_database_path.cache_clear()


def test_writing_asset_service_timeline_version_conflict(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-timeline-conflict")
    work = create_work()
    service = build_service()
    event = service.create_timeline_event(work.id, {"title": "事件"})

    with pytest.raises(ValueError, match="asset_version_conflict"):
        service.update_timeline_event(event.id, {"title": "冲突"}, expected_version=0)

    get_database_path.cache_clear()


def test_writing_asset_service_timeline_reorder_requires_complete_mapping(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-timeline-reorder")
    work = create_work()
    service = build_service()
    first = service.create_timeline_event(work.id, {"title": "事件一"})
    second = service.create_timeline_event(work.id, {"title": "事件二"})

    reordered = service.reorder_timeline_events(work.id, [
        {"id": second.id, "order_index": 1},
        {"id": first.id, "order_index": 2},
    ])
    assert [item.id for item in reordered] == [second.id, first.id]
    assert [item.order_index for item in reordered] == [1, 2]

    invalid_mappings = [
        [{"id": first.id, "order_index": 1}],
        [{"id": first.id, "order_index": 1}, {"id": first.id, "order_index": 2}],
        [{"id": first.id, "order_index": 1}, {"id": "missing", "order_index": 2}],
        [{"id": first.id, "order_index": 1}, {"id": second.id, "order_index": 3}],
    ]
    for mappings in invalid_mappings:
        with pytest.raises(ValueError, match="invalid_input"):
            service.reorder_timeline_events(work.id, mappings)

    get_database_path.cache_clear()


def test_writing_asset_service_timeline_rejects_missing_chapter_ref(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-timeline-invalid-chapter")
    work = create_work()
    service = build_service()

    with pytest.raises(ValueError, match="invalid_input"):
        service.create_timeline_event(work.id, {"title": "事件", "chapter_id": "missing-chapter"})

    get_database_path.cache_clear()
