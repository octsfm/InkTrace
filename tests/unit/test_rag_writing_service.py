import asyncio
from types import SimpleNamespace

from application.services.rag_writing_service import RAGWritingService
from domain.types import NovelId


class _FakeVectorRepo:
    pass


class _FakeChapterRepo:
    def __init__(self):
        self.saved = []

    def find_by_novel(self, _novel_id):
        return []

    def save(self, chapter):
        self.saved.append(chapter)


class _FakeNovelRepo:
    def find_by_id(self, _novel_id):
        return SimpleNamespace(title="测试小说")


class _FakeRAGRetrieval:
    def get_context_for_writing(self, novel_id, writing_prompt):
        return {"chapters": [], "characters": [], "worldview": []}


class _FakeLLMClient:
    async def generate(self, prompt, max_tokens=2100, temperature=0.7):
        return {"ok": True, "text": "这是RAG续写结果"}


class _FakeLLMFactory:
    primary_client = _FakeLLMClient()


def test_rag_writing_service_uses_async_primary_client():
    service = RAGWritingService(
        vector_repo=_FakeVectorRepo(),
        chapter_repo=_FakeChapterRepo(),
        novel_repo=_FakeNovelRepo(),
        rag_retrieval=_FakeRAGRetrieval(),
        llm_factory=_FakeLLMFactory(),
    )
    chapter = asyncio.run(service.write_chapter(NovelId("novel_1"), "继续推进", 800))
    assert chapter.content == "这是RAG续写结果"
    assert chapter.number == 1
