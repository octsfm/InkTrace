from __future__ import annotations

import asyncio
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
            SimpleNamespace(id=SimpleNamespace(value="chapter_1"), number=1, title="第一章", content="第一章内容"),
            SimpleNamespace(id=SimpleNamespace(value="chapter_2"), number=2, title="第二章", content="第二章内容"),
        ]


class _FakeNovelRepo:
    pass


class _FakeOutlineRepo:
    def find_by_novel(self, novel_id: NovelId):
        return None


class _FakeLLMFactory:
    primary_client = None
    backup_client = None


class _FakeV2Repo:
    def __init__(self):
        self._active = {}

    def find_active_project_memory(self, project_id: str):
        return self._active.get(project_id)


class _FakeChapterOutlineRepo:
    def __init__(self):
        self.saved = {}

    def find_by_chapter_id(self, chapter_id):
        return self.saved.get(str(chapter_id))

    def save(self, outline):
        self.saved[str(outline.chapter_id)] = outline


class _EmptyRepo:
    def find_by_project_id(self, *_args, **_kwargs):
        return []

    def find_by_chapter_id(self, *_args, **_kwargs):
        return []

    def save(self, *_args, **_kwargs):
        return None

    def replace_by_project(self, *_args, **_kwargs):
        return None


def _build_service(**kwargs):
    return V2WorkflowService(
        project_service=kwargs.get("project_service", _FakeProjectService()),
        content_service=kwargs.get("content_service", _FakeContentService()),
        chapter_repo=kwargs.get("chapter_repo", _FakeChapterRepo()),
        novel_repo=kwargs.get("novel_repo", _FakeNovelRepo()),
        outline_repo=kwargs.get("outline_repo", _FakeOutlineRepo()),
        llm_factory=kwargs.get("llm_factory", _FakeLLMFactory()),
        v2_repo=kwargs.get("v2_repo", _FakeV2Repo()),
        global_constraints_repo=kwargs.get("global_constraints_repo", _EmptyRepo()),
        chapter_analysis_memory_repo=kwargs.get("chapter_analysis_memory_repo", _EmptyRepo()),
        chapter_continuation_memory_repo=kwargs.get("chapter_continuation_memory_repo", _EmptyRepo()),
        chapter_outline_repo=kwargs.get("chapter_outline_repo", _FakeChapterOutlineRepo()),
        chapter_task_repo=kwargs.get("chapter_task_repo", _EmptyRepo()),
        structural_draft_repo=kwargs.get("structural_draft_repo", _EmptyRepo()),
        detemplated_draft_repo=kwargs.get("detemplated_draft_repo", _EmptyRepo()),
        draft_integrity_check_repo=kwargs.get("draft_integrity_check_repo", _EmptyRepo()),
        style_requirements_repo=kwargs.get("style_requirements_repo", _EmptyRepo()),
    )


def test_build_chapter_units_chapter_first_mode():
    service = _build_service()
    units = service._build_chapter_units(NovelId("novel_1"), "chapter_first")
    assert len(units) == 2
    assert units[0]["id"] == "chapter_1"
    assert units[0]["title"] == "第一章"
    assert units[0]["index"] == 1
    assert units[1]["title"] == "第二章"


def test_memory_payload_version_switches_incrementally():
    repo = _FakeV2Repo()
    repo._active["proj_1"] = {"version": 3}
    service = _build_service(v2_repo=repo)
    payload = service._to_project_memory_payload("proj_1", {"characters": [], "world_facts": {}})
    assert payload["version"] == 4


def test_memory_view_uses_outline_context_summary_fallback():
    service = _build_service()
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
    service = _build_service(project_service=_FakeProjectService(memory={}), v2_repo=repo)
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
    service = _build_service(project_service=_FakeProjectService(memory={"world_settings": "旧设定A；旧设定B", "plot_outline": "旧主线"}), v2_repo=repo)
    memory = service._load_structured_memory("proj_1", NovelId("novel_1"), {"premise": "A"})
    assert memory["world_facts"]["background"][:2] == ["旧设定A", "旧设定B"]
    assert memory["chapter_summaries"] == ["旧主线"]


def test_memory_view_filters_garbled_text():
    service = _build_service()
    view = service._to_memory_view_payload(
        "proj_1",
        {
            "id": "memory_1",
            "characters": [{"name": "瑙掕壊A", "traits": ["???"]}, {"name": "主角", "traits": ["坚韧", "冷静"]}],
            "world_facts": {"background": ["chunk=2 分析完成", "古城封印松动"]},
            "plot_arcs": [{"title": "主线", "summary": "chunk=3 分析完成"}, {"title": "古城危机", "summary": "三方势力冲突升级"}],
            "chapter_summaries": ["???", "主角发现封印裂缝"],
            "style_profile": {"narrative_pov": "第三人称", "tone_tags": ["紧张"], "rhythm_tags": ["中快"]},
            "outline_context": {"summary": ["????", "封印松动带来危机"]},
            "current_state": {"latest_summary": "chunk=2 分析完成"},
        },
    )
    assert view["main_characters"][0]["name"] == "主角"
    assert "chunk=" not in "；".join(view["world_summary"])
    assert "chunk=" not in "；".join(view["main_plot_lines"])
    assert view["outline_summary"] == ["封印松动带来危机"]


def test_organize_logs_started_and_finished(monkeypatch):
    from application.services import v2_workflow_service as mod

    class _PS:
        def get_project(self, project_id):
            return SimpleNamespace(id=SimpleNamespace(value="proj_1"), novel_id=NovelId("novel_1"))

        def bind_memory_to_novel(self, novel_id, memory):
            return None

    class _Repo:
        def __init__(self):
            self._active = {}

        def find_active_project_memory(self, project_id):
            return None

        def start_workflow_job(self, *args, **kwargs):
            return "job_1"

        def finish_workflow_job(self, *args, **kwargs):
            return None

        def save_project_memory(self, payload):
            return None

        def save_memory_view(self, payload):
            return None

    class _Analyzer:
        async def execute_async(self, ctx, payload):
            return SimpleNamespace(status="success", payload={"chapter_summaries": ["ok"]})

    events = []

    class _Logger:
        def info(self, _msg, extra=None):
            events.append((extra or {}).get("event"))

        def error(self, _msg, extra=None):
            events.append((extra or {}).get("event"))

        def warning(self, _msg, extra=None):
            events.append((extra or {}).get("event"))

    monkeypatch.setattr(mod, "AnalysisTool", lambda *_args, **_kwargs: _Analyzer())
    service = _build_service(project_service=_PS(), v2_repo=_Repo())
    service.logger = _Logger()
    asyncio.run(service.organize_project("proj_1", "chapter_first", True))
    assert "organize_started" in events
    assert "chapter_analysis_started" in events
    assert "chapter_analysis_finished" in events
    assert "organize_finished" in events


def test_organize_logs_failed_chapter(monkeypatch):
    from application.services import v2_workflow_service as mod

    class _PS:
        def get_project(self, project_id):
            return SimpleNamespace(id=SimpleNamespace(value="proj_1"), novel_id=NovelId("novel_1"))

        def bind_memory_to_novel(self, novel_id, memory):
            return None

    class _Repo:
        def find_active_project_memory(self, project_id):
            return None

        def start_workflow_job(self, *args, **kwargs):
            return "job_1"

        def finish_workflow_job(self, *args, **kwargs):
            return None

        def save_project_memory(self, payload):
            return None

        def save_memory_view(self, payload):
            return None

    class _Analyzer:
        async def execute_async(self, ctx, payload):
            return SimpleNamespace(status="failed", payload={})

    events = []

    class _Logger:
        def info(self, _msg, extra=None):
            events.append((extra or {}).get("event"))

        def error(self, _msg, extra=None):
            events.append((extra or {}).get("event"))

        def warning(self, _msg, extra=None):
            events.append((extra or {}).get("event"))

    monkeypatch.setattr(mod, "AnalysisTool", lambda *_args, **_kwargs: _Analyzer())
    service = _build_service(project_service=_PS(), v2_repo=_Repo())
    service.logger = _Logger()
    try:
        asyncio.run(service.organize_project("proj_1", "chapter_first", True))
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert "chapter_analysis_failed" in events


def test_organize_generates_and_saves_chapter_outlines(monkeypatch):
    from application.services import v2_workflow_service as mod

    class _PS:
        def get_project(self, project_id):
            return SimpleNamespace(id=SimpleNamespace(value="proj_1"), novel_id=NovelId("novel_1"))

        def bind_memory_to_novel(self, novel_id, memory):
            return None

    class _Repo:
        def find_active_project_memory(self, project_id):
            return None

        def start_workflow_job(self, *args, **kwargs):
            return "job_1"

        def finish_workflow_job(self, *args, **kwargs):
            return None

        def save_project_memory(self, payload):
            return None

        def save_memory_view(self, payload):
            return None

    class _Analyzer:
        async def execute_async(self, ctx, payload):
            return SimpleNamespace(status="success", payload={"chapter_summaries": ["ok"]})

    class _PromptAI:
        async def analyze_to_outline(self, chapter_title, chapter_content, **kwargs):
            return {
                "outline_draft": {
                    "goal": f"推进{chapter_title}",
                    "conflict": f"{chapter_content}的冲突",
                    "events": ["事件1", "事件2"],
                    "character_progress": "角色推进",
                    "ending_hook": "悬念收尾",
                    "opening_continuation": "承接上章",
                    "notes": "自动整理生成",
                },
                "used_fallback": False,
            }

    monkeypatch.setattr(mod, "AnalysisTool", lambda *_args, **_kwargs: _Analyzer())
    outline_repo = _FakeChapterOutlineRepo()
    service = _build_service(project_service=_PS(), v2_repo=_Repo(), chapter_outline_repo=outline_repo)
    service.prompt_ai_service = _PromptAI()

    asyncio.run(service.organize_project("proj_1", "chapter_first", True))

    first_outline = outline_repo.find_by_chapter_id("chapter_1")
    second_outline = outline_repo.find_by_chapter_id("chapter_2")
    assert first_outline is not None
    assert second_outline is not None
    assert first_outline.goal == "推进第一章"
    assert second_outline.notes == "自动整理生成"
