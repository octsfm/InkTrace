import hashlib

from fastapi.testclient import TestClient

from domain.entities.organize_job import OrganizeJob
from domain.types import NovelId, OrganizeJobStatus
from presentation.api import dependencies
from presentation.api.app import create_app
from presentation.api.routers import content as content_router


class _FakeProject:
    def __init__(self, project_id: str):
        self.id = type("ProjectIdBox", (), {"value": project_id})()


class _FakeProjectService:
    def __init__(self, memory=None):
        self._memory = memory if memory is not None else {}
        self.bind_count = 0

    def ensure_project_for_novel(self, novel_id):
        return _FakeProject("project-organize")

    def get_memory_by_novel(self, novel_id):
        return self._memory

    def bind_memory_to_novel(self, novel_id, memory):
        self._memory = memory
        self.bind_count += 1
        return _FakeProject("project-organize")


class _FakeContentService:
    def __init__(self, novel_text: str, outline_context=None):
        self._novel_text = novel_text
        self._outline_context = outline_context or {}

    def get_novel_text(self, novel_id):
        return self._novel_text

    def get_outline_context(self, novel_id):
        return self._outline_context


class _FakeOrganizeJobRepo:
    def __init__(self, job=None):
        self.job = job
        self.save_count = 0

    def find_by_novel_id(self, novel_id):
        return self.job

    def save(self, job):
        self.job = job
        self.save_count += 1

    def delete(self, novel_id):
        self.job = None


class _FakeLLMFactory:
    primary_client = None
    backup_client = None


class _FakeAnalysisTool:
    incremental_calls = []

    def __init__(self, primary_client=None, backup_client=None):
        pass

    async def execute_async(self, task_context, tool_input):
        mode = tool_input.get("mode")
        if mode == "structure_mode":
            return type(
                "Result",
                (),
                {
                    "status": "success",
                    "payload": {
                        "chapters": [
                            {"index": 1, "title": "chunk-1", "content": "aaa"},
                            {"index": 2, "title": "chunk-2", "content": "bbb"},
                            {"index": 3, "title": "chunk-3", "content": "ccc"},
                        ]
                    },
                },
            )()
        if mode == "incremental_mode":
            chapter = tool_input["chapter"]
            self.__class__.incremental_calls.append(chapter["index"])
            return type(
                "Result",
                (),
                {
                    "status": "success",
                    "payload": {
                        "characters": [{"name": f"char-{chapter['index']}", "traits": ["t"], "relationships": {}}],
                        "world_settings": f"world-{chapter['index']}",
                        "plot_outline": f"plot-{chapter['index']}",
                        "writing_style": "style",
                        "current_progress": f"chunk-{chapter['index']}",
                        "events": [
                            {
                                "event": f"event-{chapter['index']}",
                                "actors": [f"char-{chapter['index']}"],
                                "action": "act",
                                "result": "result",
                                "impact": "impact",
                            }
                        ],
                    },
                },
            )()
        if mode == "consolidate_mode":
            return type("Result", (), {"status": "success", "payload": {}})()
        raise AssertionError(f"unexpected mode {mode}")


def _make_client(project_service, content_service, organize_job_repo):
    app = create_app()
    app.dependency_overrides = {
        dependencies.get_project_service: lambda: project_service,
        dependencies.get_content_service: lambda: content_service,
        dependencies.get_organize_job_repo: lambda: organize_job_repo,
        dependencies.get_llm_factory: lambda: _FakeLLMFactory(),
    }
    return TestClient(app)


def test_organize_resumes_from_persisted_checkpoint():
    _FakeAnalysisTool.incremental_calls = []
    original_tool = content_router.AnalysisTool
    content_router.AnalysisTool = _FakeAnalysisTool
    try:
        novel_text = "source text"
        outline_context = {}
        source_hash = hashlib.sha256(f"{novel_text}\n##outline##\n||".encode("utf-8")).hexdigest()
        checkpoint_memory = {
            "characters": [{"name": "char-1", "traits": ["old"], "relationships": {}}],
            "world_settings": "world-1",
            "plot_outline": "plot-1",
            "writing_style": "style",
            "current_progress": "chunk-1",
            "events": [{"event": "event-1", "actors": ["char-1"], "action": "act", "result": "result", "impact": "impact"}],
        }
        job = OrganizeJob(
            novel_id=NovelId("novel-resume"),
            source_hash=source_hash,
            total_chunks=3,
            completed_chunks=1,
            checkpoint_memory=checkpoint_memory,
            status=OrganizeJobStatus.RUNNING,
        )
        project_service = _FakeProjectService(memory={})
        content_service = _FakeContentService(novel_text, outline_context)
        organize_job_repo = _FakeOrganizeJobRepo(job)
        client = _make_client(project_service, content_service, organize_job_repo)

        response = client.post("/api/content/organize/novel-resume")

        assert response.status_code == 200
        assert _FakeAnalysisTool.incremental_calls == [2, 3]
        assert organize_job_repo.job.status == OrganizeJobStatus.DONE
        assert organize_job_repo.job.completed_chunks == 3
        assert project_service.bind_count == 1
    finally:
        content_router.AnalysisTool = original_tool


def test_get_organize_progress_reads_persisted_job_when_cache_is_empty():
    novel_id = NovelId("novel-progress")
    job = OrganizeJob(
        novel_id=novel_id,
        source_hash="hash",
        total_chunks=5,
        completed_chunks=2,
        checkpoint_memory={},
        status=OrganizeJobStatus.ERROR,
        last_error="network interrupted",
    )
    project_service = _FakeProjectService(memory={})
    content_service = _FakeContentService("source text")
    organize_job_repo = _FakeOrganizeJobRepo(job)
    content_router.PROGRESS_CACHE.pop("novel-progress", None)
    client = _make_client(project_service, content_service, organize_job_repo)

    response = client.get("/api/content/organize/progress/novel-progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["current"] == 2
    assert payload["total"] == 5
    assert payload["resumable"] is True
