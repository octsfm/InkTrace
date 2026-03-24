from __future__ import annotations

from types import SimpleNamespace

from application.services.v2_workflow_service import V2WorkflowService
from domain.types import NovelId


class _FakeProjectService:
    def __init__(self, memory=None):
        self.memory = memory or {}

    def get_memory_by_novel(self, novel_id: NovelId):
        return self.memory


class _FakeContentService:
    def get_novel_text(self, novel_id: str) -> str:
        return "段落1\n\n段落2"


class _FakeChapterRepo:
    def find_by_novel(self, novel_id: NovelId):
        return [
            SimpleNamespace(number=1, title="第一章", content="第一章内容"),
            SimpleNamespace(number=2, title="第二章", content="第二章内容"),
        ]


class _FakeNovelRepo:
    pass


class _FakeOutlineRepo:
    pass


class _FakeLLMFactory:
    primary_client = None
    backup_client = None


class _FakeV2Repo:
    def __init__(self):
        self._active = {}

    def find_active_project_memory(self, project_id: str):
        return self._active.get(project_id)


def test_build_chapter_units_chapter_first_mode():
    service = V2WorkflowService(
        project_service=_FakeProjectService(),
        content_service=_FakeContentService(),
        chapter_repo=_FakeChapterRepo(),
        novel_repo=_FakeNovelRepo(),
        outline_repo=_FakeOutlineRepo(),
        llm_factory=_FakeLLMFactory(),
        v2_repo=_FakeV2Repo(),
    )
    units = service._build_chapter_units(NovelId("novel_1"), "chapter_first")
    assert len(units) == 2
    assert units[0]["title"] == "第一章"
    assert units[0]["index"] == 1
    assert units[1]["title"] == "第二章"


def test_memory_payload_version_switches_incrementally():
    repo = _FakeV2Repo()
    repo._active["proj_1"] = {"version": 3}
    service = V2WorkflowService(
        project_service=_FakeProjectService(),
        content_service=_FakeContentService(),
        chapter_repo=_FakeChapterRepo(),
        novel_repo=_FakeNovelRepo(),
        outline_repo=_FakeOutlineRepo(),
        llm_factory=_FakeLLMFactory(),
        v2_repo=repo,
    )
    payload = service._to_project_memory_payload("proj_1", {"characters": [], "world_facts": {}})
    assert payload["version"] == 4


def test_memory_view_uses_outline_context_summary_fallback():
    service = V2WorkflowService(
        project_service=_FakeProjectService(),
        content_service=_FakeContentService(),
        chapter_repo=_FakeChapterRepo(),
        novel_repo=_FakeNovelRepo(),
        outline_repo=_FakeOutlineRepo(),
        llm_factory=_FakeLLMFactory(),
        v2_repo=_FakeV2Repo(),
    )
    view = service._to_memory_view_payload(
        "proj_1",
        {
            "id": "memory_1",
            "characters": [],
            "world_facts": {},
            "chapter_summaries": [],
            "style_profile": {},
            "outline_context": {
                "premise": "前提A",
                "story_background": "背景B",
                "world_setting": "设定C",
            },
            "current_state": {},
        },
    )
    assert view["outline_summary"] == ["前提A", "背景B", "设定C"]


def test_load_structured_memory_uses_empty_when_not_legacy():
    repo = _FakeV2Repo()
    service = V2WorkflowService(
        project_service=_FakeProjectService(memory={}),
        content_service=_FakeContentService(),
        chapter_repo=_FakeChapterRepo(),
        novel_repo=_FakeNovelRepo(),
        outline_repo=_FakeOutlineRepo(),
        llm_factory=_FakeLLMFactory(),
        v2_repo=repo,
    )
    memory = service._load_structured_memory("proj_1", NovelId("novel_1"), {"premise": "A"})
    assert "world_facts" in memory
    assert memory["world_facts"] == {
        "background": [],
        "power_system": [],
        "organizations": [],
        "locations": [],
        "rules": [],
        "artifacts": [],
    }


def test_load_structured_memory_uses_legacy_only_for_old_schema():
    repo = _FakeV2Repo()
    service = V2WorkflowService(
        project_service=_FakeProjectService(memory={"world_settings": "旧设定A；旧设定B", "plot_outline": "旧主线"}),
        content_service=_FakeContentService(),
        chapter_repo=_FakeChapterRepo(),
        novel_repo=_FakeNovelRepo(),
        outline_repo=_FakeOutlineRepo(),
        llm_factory=_FakeLLMFactory(),
        v2_repo=repo,
    )
    memory = service._load_structured_memory("proj_1", NovelId("novel_1"), {"premise": "A"})
    assert memory["world_facts"]["background"][:2] == ["旧设定A", "旧设定B"]
    assert memory["chapter_summaries"] == ["旧主线"]
