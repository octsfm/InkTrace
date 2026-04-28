from application.services.v1.session_service import SessionService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, EditSessionRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def test_session_service_defaults_to_first_chapter(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "session-service.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    session_service = SessionService(
        session_repo=EditSessionRepo(),
        chapter_repo=ChapterRepo(),
        work_repo=WorkRepo(),
    )
    work = work_service.create_work("测试作品", "作者甲")
    first_chapter = ChapterRepo().list_by_work(work.id)[0]

    session = session_service.get_session(work.id)

    assert session.last_open_chapter_id == first_chapter.id.value
    assert session.cursor_position == 0
    assert session.scroll_top == 0

    get_database_path.cache_clear()


def test_session_service_persists_viewport(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "session-service-save.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    session_service = SessionService(
        session_repo=EditSessionRepo(),
        chapter_repo=ChapterRepo(),
        work_repo=WorkRepo(),
    )
    work = work_service.create_work("测试作品", "作者甲")
    first_chapter = ChapterRepo().list_by_work(work.id)[0]

    saved = session_service.save_session(
        work.id,
        chapter_id=first_chapter.id.value,
        cursor_position=128,
        scroll_top=256,
    )

    assert saved.last_open_chapter_id == first_chapter.id.value
    assert saved.cursor_position == 128
    assert saved.scroll_top == 256

    get_database_path.cache_clear()
