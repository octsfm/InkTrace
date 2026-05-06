from datetime import datetime, timezone

from application.services.v1.work_service import WorkService
from domain.entities.writing_assets import CharacterProfile
from infrastructure.database.repositories import CharacterRepo, ChapterRepo, WorkRepo
from infrastructure.database.repositories.character_repo import normalize_aliases_json
from infrastructure.database.session import get_database_path, initialize_database


def setup_db(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def _character(character_id, work_id, name="林知夏", aliases_json=None):
    now = datetime.now(timezone.utc)
    return CharacterProfile(
        id=character_id,
        work_id=work_id,
        name=name,
        description="人物描述",
        aliases_json=aliases_json if aliases_json is not None else '[" 小夏 ","小夏","","Xia"]',
        version=1,
        created_at=now,
        updated_at=now,
    )


def test_character_repo_crud_and_aliases_normalization(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "character-crud")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    repo = CharacterRepo()

    repo.save(_character("character-1", work.id))

    found = repo.find_by_id("character-1")
    assert found is not None
    assert found.aliases_json == '["小夏","Xia"]'

    found.name = "林知夏改"
    found.aliases_json = None
    found.version = 2
    found.updated_at = datetime.now(timezone.utc)
    repo.save(found)
    updated = repo.find_by_id("character-1")
    assert updated.name == "林知夏改"
    assert updated.aliases_json == "[]"
    assert updated.version == 2

    repo.delete("character-1")
    assert repo.find_by_id("character-1") is None
    get_database_path.cache_clear()


def test_character_repo_searches_name_and_aliases_case_insensitive(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "character-search")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    repo = CharacterRepo()
    repo.save(_character("character-1", work.id, name="Lin Zhi Xia", aliases_json='["Summer"]'))
    repo.save(_character("character-2", work.id, name="陈远", aliases_json='["CY"]'))

    assert [item.id for item in repo.list_by_work(work.id, "lin")] == ["character-1"]
    assert [item.id for item in repo.list_by_work(work.id, "SUM")] == ["character-1"]
    assert [item.id for item in repo.list_by_work(work.id, "cy")] == ["character-2"]
    get_database_path.cache_clear()


def test_character_repo_delete_by_work_and_alias_helper():
    assert normalize_aliases_json(None) == "[]"
    assert normalize_aliases_json([]) == "[]"
    assert normalize_aliases_json([" A ", "a", "B", ""]) == '["A","B"]'
