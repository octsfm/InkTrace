from datetime import datetime

from domain.entities.chapter import Chapter
from domain.entities.edit_session import EditSession
from domain.entities.work import Work
from domain.types import ChapterId, ChapterStatus, NovelId
from infrastructure.database.repositories import ChapterRepo, EditSessionRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def test_v1_repositories_roundtrip(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "repos.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    now = datetime(2026, 4, 28, 12, 0, 0)
    work = Work(
        id="work-1",
        title="作品A",
        author="作者A",
        created_at=now,
        updated_at=now,
        current_word_count=1200,
    )
    chapter = Chapter(
        id=ChapterId("chapter-1"),
        novel_id=NovelId("work-1"),
        number=1,
        title="第一章",
        content="正文",
        status=ChapterStatus.DRAFT,
        created_at=now,
        updated_at=now,
        order_index=1,
        version=1,
    )
    session = EditSession(
        work_id="work-1",
        last_open_chapter_id="chapter-1",
        cursor_position=8,
        scroll_top=16,
        updated_at=now,
    )

    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    session_repo = EditSessionRepo()

    work_repo.save(work)
    chapter_repo.save(chapter)
    session_repo.save(session)

    assert work_repo.find_by_id("work-1").title == "作品A"
    assert chapter_repo.find_by_id("chapter-1").order_index == 1
    assert len(chapter_repo.list_by_work("work-1")) == 1
    assert session_repo.find_by_work_id("work-1").last_open_chapter_id == "chapter-1"

    get_database_path.cache_clear()
