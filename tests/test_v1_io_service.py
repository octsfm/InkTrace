from pathlib import Path

from application.services.v1.io_service import IOService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def test_io_service_imports_txt_into_work(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-service.db"
    source_path = tmp_path / "novel.txt"
    source_path.write_text("第一章 起点\n这里是第一章。\n第二章 进展\n这里是第二章。", encoding="utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt(str(source_path), title="导入作品", author="作者甲")
    chapters = ChapterRepo().list_by_work(work.id)

    assert work.title == "导入作品"
    assert len(chapters) == 2
    assert chapters[0].title == "起点"
    assert chapters[1].title == "进展"

    get_database_path.cache_clear()


def test_io_service_imports_uploaded_txt_into_work(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-upload.db"
    raw_bytes = "第一章 起点\n这里是第一章。\n第二章 进展\n这里是第二章。".encode("utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt_upload("upload.txt", raw_bytes, title="上传作品", author="作者上传")
    chapters = ChapterRepo().list_by_work(work.id)

    assert work.title == "上传作品"
    assert len(chapters) == 2
    assert chapters[0].title == "起点"
    assert chapters[1].title == "进展"

    get_database_path.cache_clear()


def test_io_service_path_import_allowed_reads_env(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-env.db"

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    monkeypatch.delenv("INKTRACE_ALLOW_PATH_IMPORT", raising=False)
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    assert service.path_import_allowed() is False

    monkeypatch.setenv("INKTRACE_ALLOW_PATH_IMPORT", "true")
    assert service.path_import_allowed() is True

    get_database_path.cache_clear()


def test_io_service_imports_plain_txt_as_single_full_book_chapter(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-fullbook.db"
    source_path = tmp_path / "plain.txt"
    source_path.write_text("这是一个没有章节标记的完整正文。\n第二段继续展开剧情。", encoding="utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt(str(source_path), title="整本导入", author="作者乙")
    chapters = ChapterRepo().list_by_work(work.id)

    assert work.title == "整本导入"
    assert len(chapters) == 1
    assert chapters[0].title == "全本导入"
    assert chapters[0].content == "这是一个没有章节标记的完整正文。\n第二段继续展开剧情。"

    get_database_path.cache_clear()


def test_io_service_imports_empty_txt_as_single_empty_chapter(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-empty.db"
    source_path = tmp_path / "empty.txt"
    source_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt(str(source_path), title="空文件导入", author="作者丙")
    chapters = ChapterRepo().list_by_work(work.id)

    assert work.title == "空文件导入"
    assert len(chapters) == 1
    assert chapters[0].title == "全本导入"
    assert chapters[0].content == ""
    assert chapters[0].word_count == 0

    get_database_path.cache_clear()


def test_io_service_imports_intro_and_recalculates_sequential_order(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-intro.db"
    source_path = tmp_path / "intro.txt"
    source_path.write_text(
        "这里是前言内容。\n仍然属于前言。\n\n第一章 起点\n这里是第一章。\n\n第三章 转折\n这里是第三章。",
        encoding="utf-8",
    )

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt(str(source_path), title="带前言导入", author="作者丁")
    chapters = ChapterRepo().list_by_work(work.id)

    assert [chapter.title for chapter in chapters] == ["前言", "起点", "转折"]
    assert [chapter.number for chapter in chapters] == [1, 2, 3]
    assert [chapter.order_index for chapter in chapters] == [1, 2, 3]
    assert chapters[0].content == "这里是前言内容。\n仍然属于前言。"
    assert chapters[1].content == "这里是第一章。"
    assert chapters[2].content == "这里是第三章。"

    get_database_path.cache_clear()


def test_io_service_exports_txt(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export.db"
    source_path = tmp_path / "novel.txt"
    output_path = tmp_path / "out" / "work.txt"
    source_path.write_text("第一章 起点\n这里是第一章。", encoding="utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt(str(source_path), title="导出作品", author="作者甲")
    exported = Path(service.export_txt(work.id, str(output_path)))

    assert exported.exists()
    content = exported.read_text(encoding="utf-8")
    assert "导出作品" in content
    assert "第1章 起点" in content

    get_database_path.cache_clear()


def test_io_service_exports_txt_by_order_index(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export-order.db"
    source_path = tmp_path / "novel-order.txt"
    output_path = tmp_path / "out" / "ordered-work.txt"
    source_path.write_text("第一章 起点\n正文一。\n第二章 进展\n正文二。", encoding="utf-8")

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.import_txt(str(source_path), title="顺序导出作品", author="作者戊")
    chapters = ChapterRepo().list_by_work(work.id)
    first = chapters[0]
    second = chapters[1]
    first.order_index = 2
    first.number = 2
    second.order_index = 1
    second.number = 1
    ChapterRepo().save(first)
    ChapterRepo().save(second)

    exported = Path(service.export_txt(work.id, str(output_path)))
    content = exported.read_text(encoding="utf-8")

    assert exported.exists()
    assert content.index("第1章 进展") < content.index("第2章 起点")

    get_database_path.cache_clear()


def test_io_service_exports_empty_file_when_work_has_no_chapters(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "io-export-empty.db"
    output_path = tmp_path / "out" / "empty-work.txt"

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = IOService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.work_service.create_work("空导出作品", "作者癸")
    chapters = ChapterRepo().list_by_work(work.id)
    assert len(chapters) == 1
    ChapterRepo().delete(chapters[0].id.value)

    exported = Path(service.export_txt(work.id, str(output_path)))

    assert exported.exists()
    assert exported.read_text(encoding="utf-8") == ""

    get_database_path.cache_clear()
