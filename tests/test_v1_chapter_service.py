from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def test_chapter_service_inserts_after_current_chapter(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "chapter-service.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    chapter_service = ChapterService(chapter_repo=ChapterRepo(), work_repo=WorkRepo())
    work = work_service.create_work("测试作品", "作者甲")
    first = chapter_service.list_chapters(work.id)[0]

    second = chapter_service.create_chapter(work.id, title="第二章", after_chapter_id=first.id.value)
    third = chapter_service.create_chapter(work.id, title="插入章", after_chapter_id=first.id.value)
    chapters = chapter_service.list_chapters(work.id)

    assert second.number == 2
    assert third.number == 2
    assert [item.title for item in chapters] == ["第1章", "插入章", "第二章"]
    assert [item.order_index for item in chapters] == [1, 2, 3]
    assert [item.number for item in chapters] == [1, 2, 3]

    get_database_path.cache_clear()


def test_chapter_service_detects_version_conflict_and_reorders(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "chapter-service-reorder.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    chapter_service = ChapterService(chapter_repo=ChapterRepo(), work_repo=WorkRepo())
    work = work_service.create_work("测试作品", "作者甲")
    first = chapter_service.list_chapters(work.id)[0]
    second = chapter_service.create_chapter(work.id, title="第二章", after_chapter_id=first.id.value)
    third = chapter_service.create_chapter(work.id, title="第三章", after_chapter_id=second.id.value)

    try:
        chapter_service.update_chapter(first.id.value, content="正文A", expected_version=99)
        assert False, "expected version conflict"
    except ValueError as exc:
        assert str(exc) == "chapter_version_conflict"

    reordered = chapter_service.reorder_chapters(work.id, [third.id.value, first.id.value, second.id.value])

    assert [item.id.value for item in reordered] == [third.id.value, first.id.value, second.id.value]
    assert [item.number for item in reordered] == [1, 2, 3]

    get_database_path.cache_clear()


def test_chapter_service_reorder_is_atomic(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "chapter-service-reorder-atomic.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    chapter_repo = ChapterRepo()
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=WorkRepo())
    work = work_service.create_work("测试作品", "作者甲")
    first = chapter_service.list_chapters(work.id)[0]
    second = chapter_service.create_chapter(work.id, title="第二章", after_chapter_id=first.id.value)
    third = chapter_service.create_chapter(work.id, title="第三章", after_chapter_id=second.id.value)

    original_save_many = chapter_repo.save_many

    def broken_save_many(chapters):
        failing_batch = list(chapters)
        original_save = chapter_repo._save_with_connection

        def fail_after_first(conn, chapter):
            original_save(conn, chapter)
            if chapter.id.value == failing_batch[0].id.value:
                raise RuntimeError("boom")

        chapter_repo._save_with_connection = fail_after_first
        try:
            original_save_many(failing_batch)
        finally:
            chapter_repo._save_with_connection = original_save

    chapter_repo.save_many = broken_save_many

    try:
        chapter_service.reorder_chapters(work.id, [third.id.value, first.id.value, second.id.value])
        assert False, "expected atomic reorder failure"
    except RuntimeError as exc:
        assert str(exc) == "boom"

    reloaded = ChapterRepo().list_by_work(work.id)
    assert [item.id.value for item in reloaded] == [first.id.value, second.id.value, third.id.value]
    assert [item.order_index for item in reloaded] == [1, 2, 3]
    assert [item.number for item in reloaded] == [1, 2, 3]

    get_database_path.cache_clear()


def test_chapter_service_force_override_bypasses_version_conflict(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "chapter-service-force.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    chapter_service = ChapterService(chapter_repo=ChapterRepo(), work_repo=WorkRepo())
    work = work_service.create_work("测试作品", "作者甲")
    chapter = chapter_service.list_chapters(work.id)[0]

    first_saved = chapter_service.update_chapter(chapter.id.value, content="远端正文", expected_version=1)
    overridden = chapter_service.update_chapter(
        chapter.id.value,
        content="本地覆盖正文",
        expected_version=1,
        force_override=True,
    )

    assert first_saved.version == 2
    assert overridden.content == "本地覆盖正文"
    assert overridden.version == 3

    get_database_path.cache_clear()
