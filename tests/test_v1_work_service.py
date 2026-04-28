from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def test_work_service_creates_first_chapter(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "work-service.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = service.create_work("测试作品", "作者甲")
    chapters = service.chapter_repo.list_by_work(work.id)

    assert work.title == "测试作品"
    assert len(chapters) == 1
    assert chapters[0].number == 1
    assert chapters[0].order_index == 1
    assert chapters[0].title == "第1章"

    get_database_path.cache_clear()
