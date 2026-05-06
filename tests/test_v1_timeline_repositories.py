from datetime import datetime, timezone

from application.services.v1.work_service import WorkService
from domain.entities.writing_assets import TimelineEvent
from infrastructure.database.repositories import ChapterRepo, TimelineEventRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def setup_db(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _event(event_id, work_id, order_index, chapter_id=None, title=None):
    now = datetime.now(timezone.utc)
    return TimelineEvent(
        id=event_id,
        work_id=work_id,
        order_index=order_index,
        title=title or event_id,
        description=f"{event_id} description",
        chapter_id=chapter_id,
        version=1,
        created_at=now,
        updated_at=now,
    )


def test_timeline_event_repo_crud_and_order(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "timeline-crud")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter = ChapterRepo().list_by_work(work.id)[0]
    repo = TimelineEventRepo()

    repo.save(_event("event-2", work.id, 2, chapter.id.value))
    repo.save(_event("event-1", work.id, 1, None))

    assert [item.id for item in repo.list_by_work(work.id)] == ["event-1", "event-2"]
    found = repo.find_by_id("event-2")
    assert found.chapter_id == chapter.id.value

    found.title = "Updated"
    found.version = 2
    found.updated_at = datetime.now(timezone.utc)
    repo.save(found)
    assert repo.find_by_id("event-2").title == "Updated"
    assert repo.find_by_id("event-2").version == 2

    repo.delete("event-1")
    assert [item.id for item in repo.list_by_work(work.id)] == ["event-2"]
    get_database_path.cache_clear()


def test_timeline_event_repo_reorder_batch_and_clear_chapter_ref(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "timeline-reorder")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter = ChapterRepo().list_by_work(work.id)[0]
    repo = TimelineEventRepo()
    repo.save(_event("event-1", work.id, 1, chapter.id.value))
    repo.save(_event("event-2", work.id, 2, chapter.id.value))

    reordered = repo.reorder(work.id, [
        {"id": "event-2", "order_index": 1},
        {"id": "event-1", "order_index": 2},
    ])

    assert [item.id for item in reordered] == ["event-2", "event-1"]
    assert [item.order_index for item in reordered] == [1, 2]

    repo.clear_chapter_ref(chapter.id.value)
    assert all(item.chapter_id is None for item in repo.list_by_work(work.id))
    get_database_path.cache_clear()


def test_timeline_event_repo_delete_by_work(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "timeline-delete-work")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    repo = TimelineEventRepo()
    repo.save(_event("event-1", work.id, 1))

    repo.delete_by_work(work.id)

    assert repo.list_by_work(work.id) == []
    get_database_path.cache_clear()
