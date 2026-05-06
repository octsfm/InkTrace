import inspect

from domain.repositories.workbench import (
    CharacterRepository,
    ChapterOutlineRepository,
    ForeshadowRepository,
    TimelineEventRepository,
    WorkOutlineRepository,
)


def test_structured_asset_repository_interfaces_are_importable():
    assert WorkOutlineRepository
    assert ChapterOutlineRepository
    assert TimelineEventRepository
    assert ForeshadowRepository
    assert CharacterRepository


def test_structured_asset_repository_interfaces_define_data_access_methods_only():
    assert set(WorkOutlineRepository.__annotations__) == set()
    assert "find_by_work" in WorkOutlineRepository.__dict__
    assert "save" in WorkOutlineRepository.__dict__
    assert "clear_chapter_refs" in WorkOutlineRepository.__dict__

    assert "find_by_chapter" in ChapterOutlineRepository.__dict__
    assert "delete_by_work" in ChapterOutlineRepository.__dict__

    assert "list_by_work" in TimelineEventRepository.__dict__
    assert "reorder" in TimelineEventRepository.__dict__
    assert "clear_chapter_ref" in TimelineEventRepository.__dict__

    assert "list_by_work" in ForeshadowRepository.__dict__
    assert "clear_chapter_ref" in ForeshadowRepository.__dict__

    assert "list_by_work" in CharacterRepository.__dict__
    assert "delete_by_work" in CharacterRepository.__dict__


def test_structured_asset_repository_interfaces_do_not_reference_legacy_semantics():
    source = inspect.getsource(inspect.getmodule(WorkOutlineRepository))
    assert "NovelRepository" not in source
    assert "story_model" not in source
    assert "plot_arc" not in source
    assert "copilot" not in source
