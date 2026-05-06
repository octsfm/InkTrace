import pytest

from application.services.v1.work_service import WorkService
from application.services.v1.writing_asset_service import WritingAssetService
from infrastructure.database.repositories import (
    CharacterRepo,
    ChapterOutlineRepo,
    ChapterRepo,
    ForeshadowRepo,
    TimelineEventRepo,
    WorkOutlineRepo,
    WorkRepo,
)
from infrastructure.database.session import get_database_path, initialize_database


def setup_db(monkeypatch, tmp_path, name):
    db_path = tmp_path / "runtime" / f"{name}.db"
    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    get_database_path.cache_clear()
    initialize_database()


def build_service():
    return WritingAssetService(
        work_repo=WorkRepo(),
        chapter_repo=ChapterRepo(),
        work_outline_repo=WorkOutlineRepo(),
        chapter_outline_repo=ChapterOutlineRepo(),
        timeline_event_repo=TimelineEventRepo(),
        foreshadow_repo=ForeshadowRepo(),
        character_repo=CharacterRepo(),
    )


def create_work():
    return WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")


def test_writing_asset_service_character_crud_and_aliases_normalization(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-character")
    work = create_work()
    service = build_service()

    created = service.create_character(work.id, {
        "name": " 林知夏 ",
        "description": "主角",
        "aliases": [" 小夏 ", "小夏", "", "Xia"],
    })
    assert created.name == "林知夏"
    assert created.aliases_json == '["小夏","Xia"]'

    updated = service.update_character(
        created.id,
        {"name": "林知夏", "aliases": None},
        expected_version=1,
    )
    assert updated.aliases_json == "[]"
    assert updated.version == 2

    service.delete_character(created.id)
    assert service.list_characters(work.id) == []
    get_database_path.cache_clear()


def test_writing_asset_service_character_search_name_and_aliases(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-character-search")
    work = create_work()
    service = build_service()
    service.create_character(work.id, {"name": "Lin Zhi Xia", "aliases": ["Summer"]})
    service.create_character(work.id, {"name": "陈远", "aliases": ["CY"]})

    assert [item.name for item in service.list_characters(work.id, "lin")] == ["Lin Zhi Xia"]
    assert [item.name for item in service.list_characters(work.id, "sum")] == ["Lin Zhi Xia"]
    assert [item.name for item in service.list_characters(work.id, "cy")] == ["陈远"]
    get_database_path.cache_clear()


def test_writing_asset_service_character_version_conflict(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-character-conflict")
    work = create_work()
    service = build_service()
    created = service.create_character(work.id, {"name": "林知夏"})

    with pytest.raises(ValueError, match="asset_version_conflict"):
        service.update_character(created.id, {"name": "冲突"}, expected_version=0)

    get_database_path.cache_clear()


def test_writing_asset_service_character_rejects_empty_name(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-character-invalid")
    work = create_work()
    service = build_service()

    with pytest.raises(ValueError, match="invalid_input"):
        service.create_character(work.id, {"name": "   "})

    get_database_path.cache_clear()
