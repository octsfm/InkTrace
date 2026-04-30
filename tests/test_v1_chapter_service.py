from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def setup_services(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()
    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    chapter_repo = ChapterRepo()
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=WorkRepo())
    work = work_service.create_work("测试作品", "作者甲")
    return work, chapter_service, chapter_repo


def test_chapter_service_appends_new_chapter_to_end(monkeypatch, tmp_path):
    work, chapter_service, _ = setup_services(monkeypatch, tmp_path, "chapter-service")
    first = chapter_service.list_chapters(work.id)[0]

    second = chapter_service.create_chapter(work.id, title="第二章", after_chapter_id=first.id.value)
    third = chapter_service.create_chapter(work.id, title="第三章", after_chapter_id=first.id.value)
    chapters = chapter_service.list_chapters(work.id)

    assert second.number == 2
    assert third.number == 3
    assert [item.title for item in chapters] == ["", "第二章", "第三章"]
    assert [item.order_index for item in chapters] == [1, 2, 3]
    assert [item.number for item in chapters] == [1, 2, 3]

    get_database_path.cache_clear()


def test_chapter_service_detects_version_conflict_and_reorders_with_complete_mapping(monkeypatch, tmp_path):
    work, chapter_service, _ = setup_services(monkeypatch, tmp_path, "chapter-service-reorder")
    first = chapter_service.list_chapters(work.id)[0]
    second = chapter_service.create_chapter(work.id, title="第二章")
    third = chapter_service.create_chapter(work.id, title="第三章")

    try:
        chapter_service.update_chapter(first.id.value, content="正文A", expected_version=99)
        assert False, "expected version conflict"
    except ValueError as exc:
        assert str(exc) == "version_conflict"

    reordered = chapter_service.reorder_chapters(work.id, [
        {"id": third.id.value, "order_index": 1},
        {"id": first.id.value, "order_index": 2},
        {"id": second.id.value, "order_index": 3},
    ])

    assert [item.id.value for item in reordered] == [third.id.value, first.id.value, second.id.value]
    assert [item.number for item in reordered] == [1, 2, 3]

    get_database_path.cache_clear()


def test_chapter_service_reorder_rejects_incomplete_mapping(monkeypatch, tmp_path):
    work, chapter_service, _ = setup_services(monkeypatch, tmp_path, "chapter-service-reorder-invalid")
    first = chapter_service.list_chapters(work.id)[0]
    second = chapter_service.create_chapter(work.id, title="第二章")

    invalid_cases = [
        [{"id": first.id.value, "order_index": 1}],
        [{"id": first.id.value, "order_index": 1}, {"id": first.id.value, "order_index": 2}],
        [{"id": first.id.value, "order_index": 1}, {"id": "extra", "order_index": 2}],
        [{"id": first.id.value, "order_index": 1}, {"id": second.id.value, "order_index": 3}],
    ]
    for items in invalid_cases:
        try:
            chapter_service.reorder_chapters(work.id, items)
            assert False, "expected invalid_input"
        except ValueError as exc:
            assert str(exc) == "invalid_input"

    get_database_path.cache_clear()


def test_chapter_service_reorder_is_atomic(monkeypatch, tmp_path):
    work, chapter_service, chapter_repo = setup_services(monkeypatch, tmp_path, "chapter-service-reorder-atomic")
    first = chapter_service.list_chapters(work.id)[0]
    second = chapter_service.create_chapter(work.id, title="第二章")
    third = chapter_service.create_chapter(work.id, title="第三章")

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
        chapter_service.reorder_chapters(work.id, [
            {"id": third.id.value, "order_index": 1},
            {"id": first.id.value, "order_index": 2},
            {"id": second.id.value, "order_index": 3},
        ])
        assert False, "expected atomic reorder failure"
    except RuntimeError as exc:
        assert str(exc) == "boom"

    reloaded = ChapterRepo().list_by_work(work.id)
    assert [item.id.value for item in reloaded] == [first.id.value, second.id.value, third.id.value]
    assert [item.order_index for item in reloaded] == [1, 2, 3]
    assert [item.number for item in reloaded] == [1, 2, 3]

    get_database_path.cache_clear()


def test_chapter_service_force_override_bypasses_version_conflict(monkeypatch, tmp_path):
    work, chapter_service, _ = setup_services(monkeypatch, tmp_path, "chapter-service-force")
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


def test_chapter_service_save_recalculates_word_count_and_title_does_not_affect_it(monkeypatch, tmp_path):
    work, chapter_service, _ = setup_services(monkeypatch, tmp_path, "chapter-service-word-count")
    chapter = chapter_service.list_chapters(work.id)[0]

    saved = chapter_service.update_chapter(
        chapter.id.value,
        title="标题不计数",
        content="你 好\nInk\tTrace",
        expected_version=1,
    )
    renamed = chapter_service.update_chapter(saved.id.value, title="只改标题", expected_version=2)

    assert saved.word_count == 10
    assert renamed.word_count == 10
    assert renamed.title == "只改标题"

    get_database_path.cache_clear()
