import asyncio
from dataclasses import dataclass, field

from application.services.chapter_allocation_service import ChapterAllocationService
from application.services.detemplating_rewriter import DetemplatingRewriter
from application.services.memory_writeback_service import MemoryWritebackService


@dataclass
class _FakeNovelId:
    value: str = "novel-1"


@dataclass
class _FakeProject:
    novel_id: _FakeNovelId = field(default_factory=_FakeNovelId)


@dataclass
class _FakeChapter:
    number: int


class _FakeProjectService:
    def get_project(self, _project_id):
        return _FakeProject()


class _FakeChapterRepo:
    def find_by_novel(self, _novel_id):
        return [_FakeChapter(7), _FakeChapter(8)]


class _FakeWorkflowService:
    def __init__(self):
        self.project_service = _FakeProjectService()
        self.chapter_repo = _FakeChapterRepo()

    def _ensure_chapter_title(self, title: str, number: int):
        return title or f"第{number}章"


def test_chapter_allocation_service_allocates_contiguous_numbers():
    service = ChapterAllocationService(_FakeWorkflowService())
    result = service.allocate("project-1", 2, ["计划标题A", ""], ["", "模型标题B"])
    assert result[0]["chapter_number"] == 9
    assert result[0]["final_title"] == "计划标题A"
    assert result[1]["chapter_number"] == 10
    assert result[1]["final_title"] == "模型标题B"


def test_chapter_allocation_service_uses_task_title_fallback():
    service = ChapterAllocationService(_FakeWorkflowService())
    result = service.allocate("project-1", 1, [""], [""], ["短任务标题"])
    assert result[0]["final_title"] == "第9章 短任务标题"


class _FailDetemplateWorkflow:
    class _PromptAIService:
        async def rewrite_detemplated_draft(self, *_args, **_kwargs):
            raise RuntimeError("rewrite failed")

    def __init__(self):
        self.prompt_ai_service = self._PromptAIService()


def test_detemplating_rewriter_falls_back_to_structural_content():
    service = DetemplatingRewriter(_FailDetemplateWorkflow())
    structural = {"id": "s1", "project_id": "p1", "chapter_id": "c1", "chapter_number": 3, "title": "章标题", "content": "结构稿正文"}
    result = asyncio.run(service.rewrite(structural, {"id": "t1", "branch_id": "b1"}, {}, {}))
    assert result["used_fallback"] is True
    assert result["content"] == "结构稿正文"


@dataclass
class _FakeProjectId:
    value: str = "project-1"


@dataclass
class _FakeProjectEntity:
    id: _FakeProjectId = field(default_factory=_FakeProjectId)
    novel_id: _FakeNovelId = field(default_factory=_FakeNovelId)


class _UnexpectedSaveRepo:
    def save(self, *_args, **_kwargs):
        raise AssertionError("auto_commit=false 不应写入")


class _NoCommitWorkflow:
    def __init__(self):
        self.chapter_repo = _UnexpectedSaveRepo()
        self.structural_draft_repo = _UnexpectedSaveRepo()
        self.detemplated_draft_repo = _UnexpectedSaveRepo()
        self.draft_integrity_check_repo = _UnexpectedSaveRepo()
        self.chapter_task_repo = _UnexpectedSaveRepo()
        self.v2_repo = _UnexpectedSaveRepo()
        self.prompt_ai_service = type("PromptAI", (), {"extract_continuation_memory": staticmethod(lambda **_kwargs: None)})()

    def get_memory_view(self, _project_id):
        return {"project_id": "project-1"}

    def _to_project_memory_payload(self, *_args, **_kwargs):
        return {}

    def _sync_primary_repositories(self, *_args, **_kwargs):
        return None

    def _to_memory_view_payload(self, *_args, **_kwargs):
        return {}


def test_memory_writeback_service_skips_writeback_when_auto_commit_false():
    service = MemoryWritebackService(_NoCommitWorkflow())
    result = asyncio.run(service.write_batch(_FakeProjectEntity(), {"chapter_summaries": []}, [], auto_commit=False))
    assert result["chapter_saved"] is False
    assert result["memory_refreshed"] is False
    assert result["updated_memory_view"] == {"project_id": "project-1"}
