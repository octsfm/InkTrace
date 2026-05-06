from datetime import datetime, timezone

from application.services.v1.work_service import WorkService
from domain.entities.writing_assets import Foreshadow
from infrastructure.database.repositories import ChapterRepo, ForeshadowRepo, WorkRepo
from infrastructure.database.session import get_database_path, initialize_database


def setup_db(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _foreshadow(item_id, work_id, status="open", introduced=None, resolved=None):
    now = datetime.now(timezone.utc)
    return Foreshadow(
        id=item_id,
        work_id=work_id,
        status=status,
        title=f"{item_id} title",
        description=f"{item_id} description",
        introduced_chapter_id=introduced,
        resolved_chapter_id=resolved,
        version=1,
        created_at=now,
        updated_at=now,
    )


def test_foreshadow_repo_crud_and_status_filter(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "foreshadow-crud")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    repo = ForeshadowRepo()
    repo.save(_foreshadow("foreshadow-1", work.id, "open"))
    repo.save(_foreshadow("foreshadow-2", work.id, "resolved"))

    assert {item.id for item in repo.list_by_work(work.id)} == {"foreshadow-1", "foreshadow-2"}
    assert [item.id for item in repo.list_by_work(work.id, "open")] == ["foreshadow-1"]
    assert [item.id for item in repo.list_by_work(work.id, "resolved")] == ["foreshadow-2"]

    found = repo.find_by_id("foreshadow-1")
    found.title = "Updated"
    found.version = 2
    found.updated_at = datetime.now(timezone.utc)
    repo.save(found)
    assert repo.find_by_id("foreshadow-1").title == "Updated"
    assert repo.find_by_id("foreshadow-1").version == 2

    repo.delete("foreshadow-2")
    assert repo.find_by_id("foreshadow-2") is None
    get_database_path.cache_clear()


def test_foreshadow_repo_clear_chapter_refs_keeps_records(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "foreshadow-clear-ref")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter = ChapterRepo().list_by_work(work.id)[0]
    repo = ForeshadowRepo()
    repo.save(_foreshadow("foreshadow-1", work.id, "resolved", chapter.id.value, chapter.id.value))

    repo.clear_chapter_ref(chapter.id.value)

    found = repo.find_by_id("foreshadow-1")
    assert found is not None
    assert found.introduced_chapter_id is None
    assert found.resolved_chapter_id is None
    get_database_path.cache_clear()


def test_foreshadow_repo_delete_by_work(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "foreshadow-delete-work")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    repo = ForeshadowRepo()
    repo.save(_foreshadow("foreshadow-1", work.id))

    repo.delete_by_work(work.id)

    assert repo.list_by_work(work.id) == []
    get_database_path.cache_clear()
