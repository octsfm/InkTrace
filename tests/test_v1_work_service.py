from datetime import datetime, timezone

from application.services.v1.session_service import SessionService
from application.services.v1.work_service import WorkService
from domain.entities.writing_assets import CharacterProfile, ChapterOutline, Foreshadow, TimelineEvent, WorkOutline
from infrastructure.database.repositories import (
    ChapterOutlineRepo,
    ChapterRepo,
    CharacterRepo,
    EditSessionRepo,
    ForeshadowRepo,
    TimelineEventRepo,
    WorkOutlineRepo,
    WorkRepo,
)
from infrastructure.database.session import get_database_path, initialize_database


def test_work_service_creates_first_empty_chapter(monkeypatch, tmp_path):
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
    assert chapters[0].title == ""
    assert chapters[0].content == ""
    assert chapters[0].version == 1

    get_database_path.cache_clear()


def test_work_service_delete_cascades_workbench_data(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime" / "work-service-delete.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()

    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    session_service = SessionService(
        session_repo=EditSessionRepo(),
        chapter_repo=chapter_repo,
        work_repo=work_repo,
    )

    work = service.create_work("待删除作品", "作者乙")
    survivor = service.create_work("保留作品", "作者丙")
    chapter = chapter_repo.list_by_work(work.id)[0]
    now = datetime.now(timezone.utc)

    session_service.save_session(
        work.id,
        chapter_id=chapter.id.value,
        cursor_position=12,
        scroll_top=34,
    )
    WorkOutlineRepo().save(WorkOutline(
        id="work-outline-1",
        work_id=work.id,
        content_text="全书大纲",
        content_tree_json=[{"node_id": "node-1", "text": "节点", "chapter_ref": chapter.id.value, "children": []}],
        version=1,
        created_at=now,
        updated_at=now,
    ))
    ChapterOutlineRepo().save(ChapterOutline(
        id="chapter-outline-1",
        chapter_id=chapter.id.value,
        content_text="章节细纲",
        content_tree_json=[],
        version=1,
        created_at=now,
        updated_at=now,
    ))
    TimelineEventRepo().save(TimelineEvent(
        id="timeline-1",
        work_id=work.id,
        order_index=1,
        title="时间线事件",
        description="事件描述",
        chapter_id=chapter.id.value,
        version=1,
        created_at=now,
        updated_at=now,
    ))
    ForeshadowRepo().save(Foreshadow(
        id="foreshadow-1",
        work_id=work.id,
        status="open",
        title="伏笔",
        description="伏笔描述",
        introduced_chapter_id=chapter.id.value,
        resolved_chapter_id=None,
        version=1,
        created_at=now,
        updated_at=now,
    ))
    CharacterRepo().save(CharacterProfile(
        id="character-1",
        work_id=work.id,
        name="角色甲",
        description="角色描述",
        aliases_json='["甲"]',
        version=1,
        created_at=now,
        updated_at=now,
    ))

    service.delete_work(work.id)

    assert work_repo.find_by_id(work.id) is None
    assert chapter_repo.list_by_work(work.id) == []
    assert EditSessionRepo().find_by_work_id(work.id) is None
    assert WorkOutlineRepo().find_by_work(work.id) is None
    assert ChapterOutlineRepo().find_by_chapter(chapter.id.value) is None
    assert TimelineEventRepo().list_by_work(work.id) == []
    assert ForeshadowRepo().list_by_work(work.id, None) == []
    assert CharacterRepo().list_by_work(work.id) == []
    assert work_repo.find_by_id(survivor.id) is not None
    assert chapter_repo.list_by_work(survivor.id) != []

    get_database_path.cache_clear()
