from datetime import datetime, timezone

from application.services.v1.io_service import IOService
from infrastructure.database.session import get_connection
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def test_io_service_imports_uploaded_txt_into_work(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-service.db"
    raw_bytes = "第一章 起点\n这里是第一章。\n第二章 进展\n这里是第二章。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("novel.txt", raw_bytes, title="导入作品", author="作者甲")
    chapters = ChapterRepo().list_by_work(work.id)

    assert work.title == "导入作品"
    assert len(chapters) == 2
    assert chapters[0].title == "起点"
    assert chapters[1].title == "进展"

    get_database_path.cache_clear()


def test_io_service_imports_gb18030_uploaded_txt(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-gb18030.db"
    raw_bytes = "第一章 起点\n这里是第一章。".encode("gb18030")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("gb18030.txt", raw_bytes, title="编码导入", author="作者甲")
    chapters = ChapterRepo().list_by_work(work.id)

    assert work.title == "编码导入"
    assert len(chapters) == 1
    assert chapters[0].title == "起点"
    assert chapters[0].content == "这里是第一章。"

    get_database_path.cache_clear()


def test_io_service_rebuilds_order_from_physical_chapter_sequence(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-physical-order.db"
    raw_bytes = "第三章 先出现\n正文三。\n第一章 后出现\n正文一。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("physical.txt", raw_bytes, title="物理顺序导入", author="作者乙")
    chapters = ChapterRepo().list_by_work(work.id)

    assert [chapter.title for chapter in chapters] == ["先出现", "后出现"]
    assert [chapter.number for chapter in chapters] == [1, 2]
    assert [chapter.order_index for chapter in chapters] == [1, 2]

    get_database_path.cache_clear()


def test_io_service_imports_plain_txt_as_single_full_book_chapter(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-fullbook.db"
    raw_bytes = "这是一个没有章节标记的完整正文。\n第二段继续展开剧情。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("plain.txt", raw_bytes, title="整本导入", author="作者乙")
    chapters = ChapterRepo().list_by_work(work.id)

    assert work.title == "整本导入"
    assert len(chapters) == 1
    assert chapters[0].title == "全本导入"
    assert chapters[0].content == "这是一个没有章节标记的完整正文。\n第二段继续展开剧情。"

    get_database_path.cache_clear()


def test_io_service_imports_empty_txt_as_single_empty_chapter(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-empty.db"

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("empty.txt", b"", title="空文件导入", author="作者丙")
    chapters = ChapterRepo().list_by_work(work.id)

    assert work.title == "空文件导入"
    assert len(chapters) == 1
    assert chapters[0].title == "全本导入"
    assert chapters[0].content == ""
    assert chapters[0].word_count == 0

    get_database_path.cache_clear()


def test_io_service_imports_intro_and_recalculates_sequential_order(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-intro.db"
    raw_bytes = "这里是前言内容。\n仍然属于前言。\n\n第一章 起点\n这里是第一章。\n\n第三章 转折\n这里是第三章。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("intro.txt", raw_bytes, title="带前言导入", author="作者丁")
    chapters = ChapterRepo().list_by_work(work.id)

    assert [chapter.title for chapter in chapters] == ["前言", "起点", "转折"]
    assert [chapter.number for chapter in chapters] == [1, 2, 3]
    assert [chapter.order_index for chapter in chapters] == [1, 2, 3]
    assert chapters[0].content == "这里是前言内容。\n仍然属于前言。"
    assert chapters[1].content == "这里是第一章。"
    assert chapters[2].content == "这里是第三章。"

    get_database_path.cache_clear()


def test_io_service_rejects_oversized_upload(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-too-large.db"

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    raw_bytes = b"a" * (IOService.MAX_UPLOAD_SIZE_BYTES + 1)

    try:
        service.import_txt_upload("too-large.txt", raw_bytes, title="超限作品", author="作者戊")
        assert False, "expected txt_file_too_large"
    except ValueError as exc:
        assert str(exc) == "txt_file_too_large"

    get_database_path.cache_clear()


def test_io_service_import_is_atomic(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-atomic.db"
    raw_bytes = "第一章 起点\n正文一。\n第二章 进展\n正文二。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    original_save = service.chapter_repo._save_with_connection
    state = {"count": 0}

    def broken_save(conn, chapter):
        state["count"] += 1
        original_save(conn, chapter)
        if state["count"] == 2:
            raise RuntimeError("boom")

    service.chapter_repo._save_with_connection = broken_save

    try:
        service.import_txt_upload("atomic.txt", raw_bytes, title="原子导入", author="作者己")
        assert False, "expected atomic import failure"
    except RuntimeError as exc:
        assert str(exc) == "boom"

    assert WorkRepo().list_all() == []
    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0] == 0

    get_database_path.cache_clear()


def test_io_service_exports_txt(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export.db"
    raw_bytes = "第一章 起点\n这里是第一章。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("novel.txt", raw_bytes, title="导出作品", author="作者甲")
    filename, content = service.export_txt(work.id)

    assert filename == f"导出作品-{datetime.now(timezone.utc).strftime('%Y%m%d')}.txt"
    decoded = content.decode("utf-8")
    assert "导出作品" not in decoded
    assert "第1章 起点" in decoded

    get_database_path.cache_clear()


def test_io_service_exports_txt_by_order_index(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export-order.db"
    raw_bytes = "第一章 起点\n正文一。\n第二章 进展\n正文二。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("novel-order.txt", raw_bytes, title="顺序导出作品", author="作者戊")
    chapters = ChapterRepo().list_by_work(work.id)
    first = chapters[0]
    second = chapters[1]
    first.order_index = 2
    first.number = 2
    second.order_index = 1
    second.number = 1
    ChapterRepo().save(first)
    ChapterRepo().save(second)

    _, content = service.export_txt(work.id)
    decoded = content.decode("utf-8")

    assert decoded.index("第1章 进展") < decoded.index("第2章 起点")

    get_database_path.cache_clear()


def test_io_service_exports_empty_file_when_work_has_no_chapters(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export-empty.db"

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.work_service.create_work("空导出作品", "作者癸")
    chapters = ChapterRepo().list_by_work(work.id)
    assert len(chapters) == 1
    ChapterRepo().delete(chapters[0].id.value)

    _, content = service.export_txt(work.id)

    assert content == b""

    get_database_path.cache_clear()


def test_io_service_export_respects_options(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export-options.db"
    raw_bytes = "第一章 起点\n正文一。\n第二章 进展\n正文二。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("novel-options.txt", raw_bytes, title="选项导出作品", author="作者辛")

    _, without_titles = service.export_txt(work.id, include_titles=False, gap_lines=0)
    _, with_double_gap = service.export_txt(work.id, include_titles=True, gap_lines=2)

    assert "第1章 起点" not in without_titles.decode("utf-8")
    assert "\n\n\n" in with_double_gap.decode("utf-8")

    get_database_path.cache_clear()


def test_io_service_export_rejects_missing_work(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export-missing.db"

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())

    try:
        service.export_txt("missing-work-id")
        assert False, "expected work_not_found"
    except ValueError as exc:
        assert str(exc) == "work_not_found"

    get_database_path.cache_clear()


def test_io_service_export_rejects_invalid_gap_lines(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export-invalid-gap.db"

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.work_service.create_work("非法间距导出", "作者壬")

    try:
        service.export_txt(work.id, gap_lines=3)
        assert False, "expected invalid_input"
    except ValueError as exc:
        assert str(exc) == "invalid_input"

    get_database_path.cache_clear()


def test_io_service_export_does_not_modify_work_or_chapters(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export-readonly.db"
    raw_bytes = "第一章 起点\n正文一。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("readonly.txt", raw_bytes, title="只读导出作品", author="作者癸")
    before_work = WorkRepo().find_by_id(work.id)
    before_chapters = ChapterRepo().list_by_work(work.id)

    service.export_txt(work.id)

    after_work = WorkRepo().find_by_id(work.id)
    after_chapters = ChapterRepo().list_by_work(work.id)

    assert after_work is not None
    assert before_work is not None
    assert after_work.updated_at == before_work.updated_at
    assert after_work.word_count == before_work.word_count
    assert [(item.id.value, item.version, item.updated_at) for item in after_chapters] == [
        (item.id.value, item.version, item.updated_at) for item in before_chapters
    ]

    get_database_path.cache_clear()
