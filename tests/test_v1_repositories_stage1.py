from datetime import datetime, timezone

from domain.entities.edit_session import EditSession
from domain.entities.work import Work
from infrastructure.database.repositories import ChapterRepo, EditSessionRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService


def setup_db(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def test_work_repo_crud(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "work-repo-crud")
    repo = WorkRepo()
    now = datetime.now(timezone.utc)
    work = Work(id="work-1", title="Work", author="Author", current_word_count=12, created_at=now, updated_at=now)

    repo.save(work)
    found = repo.find_by_id("work-1")
    assert found is not None
    assert found.title == "Work"

    work.title = "Renamed"
    repo.save(work)
    assert repo.find_by_id("work-1").title == "Renamed"

    repo.delete("work-1")
    assert repo.find_by_id("work-1") is None
    get_database_path.cache_clear()


def test_edit_session_repo_upsert_does_not_touch_chapter_content(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "session-repo-upsert")
    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    chapter_service = ChapterService(chapter_repo=ChapterRepo(), work_repo=WorkRepo())
    work = work_service.create_work("Work", "")
    chapter = chapter_service.list_chapters(work.id)[0]
    saved = chapter_service.update_chapter(chapter.id.value, content="正文", expected_version=1)

    repo = EditSessionRepo()
    now = datetime.now(timezone.utc)
    repo.save(EditSession(work_id=work.id, last_open_chapter_id=saved.id.value, cursor_position=7, scroll_top=9, updated_at=now))
    repo.save(EditSession(work_id=work.id, last_open_chapter_id=saved.id.value, cursor_position=70, scroll_top=90, updated_at=now))

    session = repo.find_by_work_id(work.id)
    reloaded = ChapterRepo().find_by_id(saved.id.value)
    assert session.cursor_position == 70
    assert session.scroll_top == 90
    assert reloaded.content == "正文"
    get_database_path.cache_clear()


def test_delete_chapter_returns_safe_focus_and_normalizes_order(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "delete-normalize")
    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    chapter_service = ChapterService(chapter_repo=ChapterRepo(), work_repo=WorkRepo())
    work = work_service.create_work("Work", "")
    first = chapter_service.list_chapters(work.id)[0]
    second = chapter_service.create_chapter(work.id, title="Second")
    third = chapter_service.create_chapter(work.id, title="Third")

    next_focus = chapter_service.delete_chapter(second.id.value)
    chapters = chapter_service.list_chapters(work.id)

    assert next_focus == third.id.value
    assert [item.id.value for item in chapters] == [first.id.value, third.id.value]
    assert [item.order_index for item in chapters] == [1, 2]

    next_focus = chapter_service.delete_chapter(third.id.value)
    assert next_focus == first.id.value

    next_focus = chapter_service.delete_chapter(first.id.value)
    assert next_focus == ""
    assert chapter_service.list_chapters(work.id) == []
    get_database_path.cache_clear()
