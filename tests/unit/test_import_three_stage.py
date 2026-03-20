from fastapi.testclient import TestClient

from application.agent_mvp.chapter_splitter import split_into_chapters
from application.agent_mvp.memory import merge_memory
from domain.types import NovelId
from presentation.api import dependencies
from presentation.api.app import create_app


class _FakeProject:
    def __init__(self, project_id: str):
        self.id = type("ProjectIdBox", (), {"value": project_id})()


class _FakeProjectService:
    def __init__(self, memory=None):
        self._memory = memory if memory is not None else {}
        self.bind_count = 0

    def ensure_project_for_novel(self, novel_id):
        return _FakeProject("project-three-stage")

    def get_memory_by_novel(self, novel_id):
        return self._memory

    def bind_memory_to_novel(self, novel_id, memory):
        self._memory = memory
        self.bind_count += 1
        return _FakeProject("project-three-stage")


class _FakeContentService:
    def get_novel_text(self, novel_id):
        return "第1章 开端\n林渊进入古城。\n\n第2章 追索\n林渊调查遗迹符纹。"

    def get_outline_context(self, novel_id):
        return {}


class _FakeLLMFactory:
    primary_client = None
    backup_client = None


class _FakeOrganizeJobRepo:
    def __init__(self):
        self.job = None

    def find_by_novel_id(self, novel_id: NovelId):
        return self.job

    def save(self, job):
        self.job = job

    def delete(self, novel_id: NovelId):
        self.job = None


def _make_client(overrides):
    app = create_app()
    app.dependency_overrides = overrides
    return TestClient(app)


def test_split_into_chapters_supports_multi_patterns_and_fallback():
    zh_text = "第1章 开端\n内容A\n\n第2章 转折\n内容B"
    en_text = "Chapter 1 Start\nAAA\n\nChapter 2 Turn\nBBB"
    fallback_text = "段落1\n\n段落2\n\n段落3\n\n段落4\n\n段落5\n\n段落6\n\n段落7"

    zh = split_into_chapters(zh_text)
    en = split_into_chapters(en_text)
    fb = split_into_chapters(fallback_text)

    assert len(zh) == 2
    assert len(en) == 2
    assert len(fb) >= 1
    assert zh[0].title.startswith("第1章")
    assert en[0].title.lower().startswith("chapter 1")


def test_merge_memory_keeps_existing_character_and_merges_incrementally():
    old_memory = {
        "characters": [{"name": "林渊", "traits": ["冷静"], "relationships": {"沈清": "同伴"}}],
        "world_settings": ["古城存在血脉机关"],
        "plot_outline": ["主角进入古城"],
        "writing_style": {"tone": "紧张", "pacing": "中速", "narrative_style": "第三人称"},
    }
    new_memory = {
        "characters": [{"name": "林渊", "traits": ["坚韧"], "relationships": {"沈清": "信任"}}],
        "world_settings": ["符纹可记录祖先记忆"],
        "plot_outline": ["主角发现家族密卷"],
        "writing_style": {"tone": "压迫感"},
    }

    merged = merge_memory(old_memory, new_memory)
    assert len(merged["characters"]) == 1
    assert set(merged["characters"][0]["traits"]) == {"冷静", "坚韧"}
    assert merged["characters"][0]["relationships"]["沈清"] in {"同伴", "信任"}
    assert "古城存在血脉机关" in str(merged["world_settings"])
    assert "符纹可记录祖先记忆" in str(merged["world_settings"])
    assert "主角进入古城" in str(merged["plot_outline"])
    assert "主角发现家族密卷" in str(merged["plot_outline"])
    assert "压迫感" in str(merged["writing_style"])
    assert "中速" in str(merged["writing_style"])


def test_organize_story_runs_three_stage_and_updates_progress():
    fake_project_service = _FakeProjectService(memory={})
    fake_content_service = _FakeContentService()
    client = _make_client(
        {
            dependencies.get_project_service: lambda: fake_project_service,
            dependencies.get_content_service: lambda: fake_content_service,
            dependencies.get_llm_factory: lambda: _FakeLLMFactory(),
            dependencies.get_organize_job_repo: lambda: _FakeOrganizeJobRepo(),
        }
    )

    response = client.post("/api/content/organize/novel-three-stage")
    assert response.status_code == 200
    payload = response.json()
    memory = payload["memory"]
    assert isinstance(memory["current_progress"], str)
    assert "Organize complete" in memory["current_progress"]
    assert payload["progress"]["status"] == "done"
    assert fake_project_service.bind_count == 1
