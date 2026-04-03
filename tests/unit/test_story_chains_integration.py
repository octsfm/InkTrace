import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from domain.entities.chapter import Chapter
from domain.types import ChapterId, ChapterStatus, NovelId
from presentation.api import dependencies
from presentation.api.app import create_app


class _FakeProject:
    def __init__(self, project_id: str):
        self.id = type("ProjectIdBox", (), {"value": project_id})()


class _FakeProjectService:
    def __init__(self, memory=None, ensure_error: str = ""):
        self._memory = memory if memory is not None else {}
        self._ensure_error = ensure_error
        self.bind_count = 0

    def ensure_project_for_novel(self, novel_id):
        if self._ensure_error:
            raise ValueError(self._ensure_error)
        return _FakeProject("project-1")

    def get_project_by_novel(self, novel_id):
        return None

    def get_memory_by_novel(self, novel_id):
        return self._memory

    def bind_memory_to_novel(self, novel_id, memory):
        self._memory = memory
        self.bind_count += 1
        return _FakeProject("project-1")


class _FakeContentService:
    def __init__(self):
        self.novel_text_called = False

    def get_novel_text(self, novel_id):
        self.novel_text_called = True
        return "测试文本"

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


class _FakeChapterRepo:
    def __init__(self, chapters=None):
        self._chapters = chapters or []

    def find_by_novel(self, novel_id):
        return list(self._chapters)

    def save(self, chapter):
        self._chapters.append(chapter)


class _FakeNovel:
    def __init__(self):
        self.chapters = []

    def add_chapter(self, chapter, updated_at):
        self.chapters.append(chapter)


class _FakeNovelRepo:
    def __init__(self):
        self.novel = _FakeNovel()

    def find_by_id(self, novel_id):
        return self.novel

    def save(self, novel):
        self.novel = novel


class _FakeV2WorkflowService:
    def __init__(self, mode: str = "ok", chapter_repo: _FakeChapterRepo = None, project_service: _FakeProjectService = None):
        self.mode = mode
        self.chapter_repo = chapter_repo
        self.project_service = project_service

    async def organize_project(self, project_id: str, strategy: str, force_rebuild: bool, progress_callback=None):
        if self.mode == "organize_fail":
            raise ValueError("小说不存在")
        if progress_callback:
            await progress_callback({"current": 1, "total": 1, "status": "done", "stage": "done", "message": "完成"})
        return {"memory_view": {"main_plot_lines": ["主线"]}}

    def get_memory(self, project_id: str):
        return {"chapter_summaries": ["第1章摘要"]}

    async def generate_branches(self, project_id: str, direction_hint: str, branch_count: int):
        return {"branches": [{"id": "branch_1", "title": "分支A"}]}

    async def create_chapter_plan(
        self,
        project_id: str,
        branch_id: str,
        chapter_count: int,
        target_words_per_chapter: int,
        planning_mode: str = "light_planning",
        target_arc_id: str = "",
        allow_deep_planning: bool = False,
    ):
        return {"plans": [{"id": "plan_1"}]}

    async def execute_writing(self, project_id: str, plan_ids, auto_commit: bool):
        if self.mode == "continue_fail":
            raise ValueError("memory missing")
        if self.chapter_repo:
            self.chapter_repo.save(
                Chapter(
                    id=ChapterId(str(uuid.uuid4())),
                    novel_id=NovelId("novel-1"),
                    number=2,
                    title="第2章",
                    content="第二章内容",
                    status=ChapterStatus.DRAFT,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
        return {"latest_content": "第二章内容"}

    async def refresh_memory(self, project_id: str, from_chapter_number: int, to_chapter_number: int):
        if self.project_service:
            current = dict((self.project_service._memory or {}).get("current_progress") or {})
            current["latest_chapter_number"] = to_chapter_number
            self.project_service._memory["current_progress"] = current
        return {"ok": True}


def _make_client(overrides):
    app = create_app()
    app.dependency_overrides = overrides
    return TestClient(app)


def test_organize_story_returns_error_code_when_novel_missing():
    fake_project_service = _FakeProjectService(memory={}, ensure_error="小说不存在")
    fake_content_service = _FakeContentService()
    client = _make_client(
        {
            dependencies.get_project_service: lambda: fake_project_service,
            dependencies.get_content_service: lambda: fake_content_service,
            dependencies.get_llm_factory: lambda: _FakeLLMFactory(),
            dependencies.get_organize_job_repo: lambda: _FakeOrganizeJobRepo(),
            dependencies.get_v2_workflow_service: lambda: _FakeV2WorkflowService(mode="organize_fail"),
        }
    )
    response = client.post("/api/content/organize/novel-x")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "NOVEL_NOT_FOUND"


def test_organize_story_rebuilds_memory_instead_of_reusing_existing_snapshot():
    existing_memory = {
        "characters": [{"name": "孔凡圣", "traits": ["谨慎"], "relationships": {}}],
        "world_settings": ["旧设定"],
        "plot_outline": ["旧主线"],
        "writing_style": {"tone": "紧张", "pacing": "中速", "narrative_style": "第三人称"},
        "current_progress": "旧摘要",
    }
    fake_project_service = _FakeProjectService(memory=existing_memory)
    fake_content_service = _FakeContentService()
    client = _make_client(
        {
            dependencies.get_project_service: lambda: fake_project_service,
            dependencies.get_content_service: lambda: fake_content_service,
            dependencies.get_llm_factory: lambda: _FakeLLMFactory(),
            dependencies.get_organize_job_repo: lambda: _FakeOrganizeJobRepo(),
            dependencies.get_v2_workflow_service: lambda: _FakeV2WorkflowService(mode="ok", project_service=fake_project_service),
        }
    )
    response = client.post("/api/content/organize/novel-y")
    assert response.status_code == 200
    payload = response.json()
    assert payload["progress"]["status"] == "done"
    assert payload["metadata"]["task_role"] == "GLOBAL_ANALYSIS"
    assert payload["metadata"]["routed_model"] == "kimi"
    assert "memory_view" in payload


def test_continue_writing_returns_error_code_when_memory_missing():
    fake_project_service = _FakeProjectService(memory={})
    fake_chapter_repo = _FakeChapterRepo()
    fake_novel_repo = _FakeNovelRepo()
    client = _make_client(
        {
            dependencies.get_project_service: lambda: fake_project_service,
            dependencies.get_chapter_repo: lambda: fake_chapter_repo,
            dependencies.get_novel_repo: lambda: fake_novel_repo,
            dependencies.get_v2_workflow_service: lambda: _FakeV2WorkflowService(mode="continue_fail"),
        }
    )
    response = client.post(
        "/api/writing/continue",
        json={"novel_id": "novel-z", "goal": "第2章：延展冲突", "target_word_count": 1200},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "CONTINUE_INPUT_INVALID"


def test_continue_writing_persists_next_chapter_and_updates_progress():
    memory = {
        "characters": [{"name": "孔凡圣", "traits": ["谨慎", "坚韧"], "relationships": {"苏清月": "同伴"}}],
        "world_settings": ["古城遗迹存在血脉机关"],
        "plot_outline": ["遗迹开启：主角获得密卷"],
        "writing_style": {"tone": "悬疑紧张", "pacing": "中快节奏", "narrative_style": "第三人称近距离"},
        "events": [{"event": "主角获得密卷", "actors": ["孔凡圣"], "action": "获得", "result": "掌握线索", "impact": "推进主线"}],
        "current_progress": {"latest_chapter_number": 1, "latest_goal": "第1章", "last_summary": "上章摘要"},
    }
    fake_project_service = _FakeProjectService(memory=memory)
    chapter_one = Chapter(
        id=ChapterId(str(uuid.uuid4())),
        novel_id=NovelId("novel-1"),
        number=1,
        title="第1章",
        content="第一章内容",
        status=ChapterStatus.DRAFT,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    fake_chapter_repo = _FakeChapterRepo(chapters=[chapter_one])
    fake_novel_repo = _FakeNovelRepo()
    client = _make_client(
        {
            dependencies.get_project_service: lambda: fake_project_service,
            dependencies.get_chapter_repo: lambda: fake_chapter_repo,
            dependencies.get_novel_repo: lambda: fake_novel_repo,
            dependencies.get_v2_workflow_service: lambda: _FakeV2WorkflowService(mode="ok", chapter_repo=fake_chapter_repo, project_service=fake_project_service),
        }
    )
    response = client.post(
        "/api/writing/continue",
        json={"novel_id": "novel-1", "goal": "第2章：承接第一章并推进主线", "target_word_count": 1200},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["chapter_number"] == 2
    assert fake_project_service.get_memory_by_novel(NovelId("novel-1"))["current_progress"]["latest_chapter_number"] == 2
