from uuid import uuid4

import pytest

from application.services.v1.work_service import WorkService
from application.services.v1.writing_asset_service import WritingAssetService
from domain.value_objects.outline_snapshot import outline_content_hash
from infrastructure.database.repositories import ChapterOutlineRepo, ChapterRepo, WorkOutlineRepo, WorkRepo
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
    )


def _node(**overrides):
    payload = {
        "node_id": str(uuid4()),
        "text": "节点",
        "children": [],
        "chapter_ref": None,
    }
    payload.update(overrides)
    return payload


def test_writing_asset_service_saves_work_outline_and_increments_version(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-work-outline")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    service = build_service()

    created = service.save_work_outline(
        work.id,
        content_text="全书大纲",
        content_tree_json=[_node()],
        expected_version=1,
    )
    assert created.version == 1

    updated = service.save_work_outline(
        work.id,
        content_text="全书大纲更新",
        content_tree_json=[_node(collapsed=True)],
        expected_version=1,
    )
    assert updated.version == 2
    assert updated.content_text == "全书大纲更新"

    get_database_path.cache_clear()


def test_writing_asset_service_work_outline_rejects_version_conflict(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-work-outline-conflict")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    service = build_service()
    service.save_work_outline(work.id, content_text="全书大纲", content_tree_json=[], expected_version=1)

    with pytest.raises(ValueError, match="asset_version_conflict"):
        service.save_work_outline(work.id, content_text="冲突", content_tree_json=[], expected_version=0)

    get_database_path.cache_clear()


def test_writing_asset_service_saves_chapter_outline_and_validates_tree(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-chapter-outline")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter = ChapterRepo().list_by_work(work.id)[0]
    service = build_service()

    saved = service.save_chapter_outline(
        chapter.id.value,
        content_text="章节细纲",
        content_tree_json=[_node(chapter_ref=chapter.id.value)],
        expected_version=1,
    )
    assert saved.version == 1
    assert saved.content_tree_json[0]["chapter_ref"] == chapter.id.value

    with pytest.raises(ValueError, match="invalid_input"):
        service.save_chapter_outline(
            chapter.id.value,
            content_text="非法",
            content_tree_json=[_node(ai_summary="禁止")],
            expected_version=1,
        )

    get_database_path.cache_clear()


def test_writing_asset_service_get_outline_requires_existing_resource(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-outline-not-found")
    service = build_service()

    with pytest.raises(ValueError, match="work_not_found"):
        service.get_work_outline("missing-work")
    with pytest.raises(ValueError, match="chapter_not_found"):
        service.get_chapter_outline("missing-chapter")

    get_database_path.cache_clear()


def test_writing_asset_service_exposes_controlled_chapter_ownership_query(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path, "service-chapter-ownership")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter = ChapterRepo().list_by_work(work.id)[0]
    service = build_service()

    assert service.chapter_belongs_to_work(chapter_id=chapter.id.value, work_id=work.id) is True
    assert service.chapter_belongs_to_work(chapter_id="missing-chapter", work_id=work.id) is False
    assert service.chapter_belongs_to_work(chapter_id=chapter.id.value, work_id="other-work") is False

    get_database_path.cache_clear()


@pytest.mark.parametrize("target_kind", ["work_outline", "chapter_outline"])
def test_outline_save_rejects_virtual_v1_hash_after_concurrent_first_persist(
    monkeypatch,
    tmp_path,
    target_kind,
):
    setup_db(monkeypatch, tmp_path, f"virtual-v1-race-{target_kind}")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter_id = ChapterRepo().list_by_work(work.id)[0].id.value
    service = build_service()

    if target_kind == "work_outline":
        virtual = service.get_work_outline(work.id)
        service.save_work_outline(
            work.id,
            content_text="V1 抢先保存的作品大纲",
            content_tree_json=[],
            expected_version=1,
        )
        with pytest.raises(ValueError, match="asset_version_conflict"):
            service.save_work_outline(
                work.id,
                content_text="P2 准备写入的作品大纲",
                content_tree_json=[],
                expected_version=1,
                expected_content_hash=outline_content_hash(virtual.content_text, virtual.content_tree_json),
            )
        stored = service.get_work_outline(work.id)
        assert stored.content_text == "V1 抢先保存的作品大纲"
    else:
        virtual = service.get_chapter_outline(chapter_id)
        service.save_chapter_outline(
            chapter_id,
            content_text="V1 抢先保存的章节大纲",
            content_tree_json=[],
            expected_version=1,
        )
        with pytest.raises(ValueError, match="asset_version_conflict"):
            service.save_chapter_outline(
                chapter_id,
                content_text="P2 准备写入的章节大纲",
                content_tree_json=[],
                expected_version=1,
                expected_content_hash=outline_content_hash(virtual.content_text, virtual.content_tree_json),
            )
        stored = service.get_chapter_outline(chapter_id)
        assert stored.content_text == "V1 抢先保存的章节大纲"

    assert stored.version == 1
    get_database_path.cache_clear()


@pytest.mark.parametrize("target_kind", ["work_outline", "chapter_outline"])
def test_outline_force_override_keeps_bypassing_optional_hash_guard(monkeypatch, tmp_path, target_kind):
    setup_db(monkeypatch, tmp_path, f"force-hash-{target_kind}")
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("Work", "")
    chapter_id = ChapterRepo().list_by_work(work.id)[0].id.value
    service = build_service()

    if target_kind == "work_outline":
        service.save_work_outline(work.id, content_text="已有作品大纲", content_tree_json=[])
        saved = service.save_work_outline(
            work.id,
            content_text="强制覆盖作品大纲",
            content_tree_json=[],
            expected_version=999,
            expected_content_hash=outline_content_hash("错误基线", []),
            force_override=True,
        )
    else:
        service.save_chapter_outline(chapter_id, content_text="已有章节大纲", content_tree_json=[])
        saved = service.save_chapter_outline(
            chapter_id,
            content_text="强制覆盖章节大纲",
            content_tree_json=[],
            expected_version=999,
            expected_content_hash=outline_content_hash("错误基线", []),
            force_override=True,
        )

    assert saved.version == 2
    get_database_path.cache_clear()
