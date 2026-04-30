from application.services.v1.chapter_service import ChapterService
from application.services.v1.session_service import SessionService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, EditSessionRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def setup_services(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()
    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    chapter_service = ChapterService(chapter_repo=ChapterRepo(), work_repo=WorkRepo())
    session_service = SessionService(
        session_repo=EditSessionRepo(),
        chapter_repo=ChapterRepo(),
        work_repo=WorkRepo(),
    )
    return work_service, chapter_service, session_service


def test_session_service_defaults_to_first_chapter(monkeypatch, tmp_path):
    work_service, _, session_service = setup_services(monkeypatch, tmp_path, "session-service")
    work = work_service.create_work("测试作品", "作者甲")
    first_chapter = ChapterRepo().list_by_work(work.id)[0]

    session = session_service.get_session(work.id)

    assert session.last_open_chapter_id == first_chapter.id.value
    assert session.cursor_position == 0
    assert session.scroll_top == 0

    get_database_path.cache_clear()


def test_session_service_persists_viewport(monkeypatch, tmp_path):
    work_service, _, session_service = setup_services(monkeypatch, tmp_path, "session-service-save")
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


def test_session_service_accepts_active_chapter_id_alias(monkeypatch, tmp_path):
    work_service, chapter_service, session_service = setup_services(monkeypatch, tmp_path, "session-service-active-alias")
    work = work_service.create_work("测试作品", "作者甲")
    second = chapter_service.create_chapter(work.id, title="第二章")

    saved = session_service.save_session(
        work.id,
        active_chapter_id=second.id.value,
        cursor_position=18,
        scroll_top=36,
    )
    fetched = session_service.get_session(work.id)

    assert saved.last_open_chapter_id == second.id.value
    assert fetched.last_open_chapter_id == second.id.value
    assert fetched.cursor_position == 18
    assert fetched.scroll_top == 36

    get_database_path.cache_clear()


def test_session_service_fallbacks_to_first_chapter_when_saved_chapter_was_deleted(monkeypatch, tmp_path):
    work_service, chapter_service, session_service = setup_services(monkeypatch, tmp_path, "session-service-deleted-chapter")
    work = work_service.create_work("测试作品", "作者甲")
    first = chapter_service.list_chapters(work.id)[0]
    second = chapter_service.create_chapter(work.id, title="第二章")
    session_service.save_session(work.id, active_chapter_id=second.id.value, cursor_position=88, scroll_top=99)

    chapter_service.delete_chapter(second.id.value)
    session = session_service.get_session(work.id)

    assert session.last_open_chapter_id == first.id.value
    assert session.cursor_position == 0
    assert session.scroll_top == 0

    get_database_path.cache_clear()


def test_session_service_returns_empty_fallback_when_work_has_no_chapters(monkeypatch, tmp_path):
    work_service, chapter_service, session_service = setup_services(monkeypatch, tmp_path, "session-service-empty-work")
    work = work_service.create_work("测试作品", "作者甲")
    first = chapter_service.list_chapters(work.id)[0]
    chapter_service.delete_chapter(first.id.value)

    session = session_service.get_session(work.id)

    assert session.last_open_chapter_id == ""
    assert session.cursor_position == 0
    assert session.scroll_top == 0

    get_database_path.cache_clear()


def test_session_service_does_not_modify_chapter_content_title_or_version(monkeypatch, tmp_path):
    work_service, chapter_service, session_service = setup_services(monkeypatch, tmp_path, "session-service-no-content-touch")
    work = work_service.create_work("测试作品", "作者甲")
    chapter = chapter_service.list_chapters(work.id)[0]
    saved_chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="正文标题",
        content="正文内容",
        expected_version=1,
    )

    session_service.save_session(
        work.id,
        active_chapter_id=saved_chapter.id.value,
        cursor_position=7,
        scroll_top=9,
    )
    reloaded = ChapterRepo().find_by_id(saved_chapter.id.value)

    assert reloaded.title == "正文标题"
    assert reloaded.content == "正文内容"
    assert reloaded.version == saved_chapter.version

    get_database_path.cache_clear()


def test_session_service_rejects_unknown_active_chapter(monkeypatch, tmp_path):
    work_service, _, session_service = setup_services(monkeypatch, tmp_path, "session-service-unknown-chapter")
    work = work_service.create_work("测试作品", "作者甲")

    try:
        session_service.save_session(work.id, active_chapter_id="missing-chapter", cursor_position=1, scroll_top=2)
        assert False, "expected chapter_not_found"
    except ValueError as exc:
        assert str(exc) == "chapter_not_found"

    get_database_path.cache_clear()
