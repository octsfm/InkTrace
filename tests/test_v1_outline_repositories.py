from datetime import datetime, timezone
from uuid import uuid4

from application.services.v1.work_service import WorkService
from domain.entities.writing_assets import ChapterOutline, WorkOutline
from infrastructure.database.repositories import ChapterRepo, ChapterOutlineRepo, WorkOutlineRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def setup_db(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _node(chapter_ref=None, children=None):
    return {
        "node_id": str(uuid4()),
        "text": "节点",
        "chapter_ref": chapter_ref,
        "children": children or [],
    }


def test_work_outline_repo_roundtrip_and_clear_chapter_refs(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "work-outline")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter = ChapterRepo().list_by_work(work.id)[0]
    repo = WorkOutlineRepo()
    now = datetime.now(timezone.utc)
    tree = [_node(chapter.id.value, [_node(chapter.id.value), _node("other-chapter")])]

    repo.save(WorkOutline(
        id="outline-1",
        work_id=work.id,
        content_text="全书大纲文本",
        content_tree_json=tree,
        version=1,
        created_at=now,
        updated_at=now,
    ))

    saved = repo.find_by_work(work.id)
    assert saved is not None
    assert saved.content_text == "全书大纲文本"
    assert saved.content_tree_json[0]["chapter_ref"] == chapter.id.value

    repo.clear_chapter_refs(work.id, chapter.id.value)
    cleared = repo.find_by_work(work.id)
    assert cleared.content_tree_json[0]["chapter_ref"] is None
    assert cleared.content_tree_json[0]["children"][0]["chapter_ref"] is None
    assert cleared.content_tree_json[0]["children"][1]["chapter_ref"] == "other-chapter"

    repo.delete_by_work(work.id)
    assert repo.find_by_work(work.id) is None
    get_database_path.cache_clear()


def test_chapter_outline_repo_roundtrip_and_delete(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "chapter-outline")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter = ChapterRepo().list_by_work(work.id)[0]
    repo = ChapterOutlineRepo()
    now = datetime.now(timezone.utc)

    repo.save(ChapterOutline(
        id="chapter-outline-1",
        chapter_id=chapter.id.value,
        content_text="章节细纲",
        content_tree_json=[_node(chapter.id.value)],
        version=1,
        created_at=now,
        updated_at=now,
    ))

    saved = repo.find_by_chapter(chapter.id.value)
    assert saved is not None
    assert saved.content_text == "章节细纲"
    assert saved.version == 1

    saved.version = 2
    saved.content_text = "章节细纲更新"
    saved.updated_at = datetime.now(timezone.utc)
    repo.save(saved)
    assert repo.find_by_chapter(chapter.id.value).version == 2
    assert repo.find_by_chapter(chapter.id.value).content_text == "章节细纲更新"

    repo.delete_by_chapter(chapter.id.value)
    assert repo.find_by_chapter(chapter.id.value) is None
    get_database_path.cache_clear()


def test_chapter_outline_repo_delete_by_work(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "chapter-outline-delete-work")
    work_service = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo())
    work = work_service.create_work("Work", "")
    chapter = ChapterRepo().list_by_work(work.id)[0]
    repo = ChapterOutlineRepo()
    now = datetime.now(timezone.utc)
    repo.save(ChapterOutline(
        id="chapter-outline-1",
        chapter_id=chapter.id.value,
        content_text="章节细纲",
        content_tree_json=[],
        version=1,
        created_at=now,
        updated_at=now,
    ))

    repo.delete_by_work(work.id)

    assert repo.find_by_chapter(chapter.id.value) is None
    get_database_path.cache_clear()
