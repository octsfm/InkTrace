from __future__ import annotations

from application.services.ai.context_vector_recall_service import ContextVectorRecallService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.services.ai.embedding_provider import EmbeddingModelInfo
from domain.types import NovelId
from domain.value_objects.embedding import EmbeddingMetadata, SearchResult
from infrastructure.database.repositories import ChapterRepo, WorkRepo


class _StubVectorRepository:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.calls: list[dict[str, object]] = []

    def search(self, query: str, novel_id: NovelId | None = None, source_type: str | None = None, n_results: int = 5):
        self.calls.append(
            {
                "query": query,
                "novel_id": str(novel_id) if novel_id is not None else "",
                "source_type": source_type,
                "n_results": n_results,
            }
        )
        return list(self.results)


class _RecallQuery:
    def __init__(self, *, work_id: str, query_text: str, top_k: int = 3, score_threshold: float = 0.6) -> None:
        self.work_id = work_id
        self.query_text = query_text
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.target_chapter_id = ""
        self.allow_stale = False
        self.request_id = "req_test"
        self.trace_id = "trace_test"


class _StubEmbeddingProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def embed_text(self, *, text: str, request_id: str = "", trace_id: str = "") -> list[float]:
        self.calls.append({"text": text, "request_id": request_id, "trace_id": trace_id})
        return [0.1, 0.2, 0.3]

    def get_embedding_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            provider_name="local-test",
            model_name="test-embedding",
            model_version="v1",
            vector_dimension=3,
        )


class _StubVectorStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search_similar(
        self,
        *,
        query_embedding: list[float],
        work_id: str,
        top_k: int = 5,
        score_threshold: float = 0.6,
        exclude_chapter_ids: list[str] | None = None,
        allow_stale: bool = False,
    ) -> list[dict[str, object]]:
        self.calls.append(
            {
                "query_embedding": list(query_embedding),
                "work_id": work_id,
                "top_k": top_k,
                "score_threshold": score_threshold,
                "exclude_chapter_ids": list(exclude_chapter_ids or []),
                "allow_stale": allow_stale,
            }
        )
        return [
            {
                "vector_id": "v_port_1",
                "score": 0.94,
                "text_excerpt": "通过正式 VectorStorePort 命中的灯塔片段",
                "metadata": {
                    "work_id": work_id,
                    "chapter_id": "chapter_port_1",
                    "chunk_id": "chunk_port_1",
                    "status": "active",
                    "source": "confirmed_chapter",
                    "chapter_title": "第一章",
                },
            }
        ]


def _build_services():
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    return work_service, chapter_service


def test_context_vector_recall_service_prefers_vector_repository_results_when_available() -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("向量召回作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="本地章节正文不会被优先使用。", expected_version=1)
    vector_repo = _StubVectorRepository(
        [
            SearchResult(
                id="vec_001",
                content="向量召回命中的旧灯塔片段",
                score=0.91,
                metadata=EmbeddingMetadata(
                    source_type="confirmed_chapter",
                    source_id=chapter.id.value,
                    novel_id=work.id,
                    chunk_index=2,
                    content_preview="旧灯塔片段",
                ),
            )
        ]
    )
    service = ContextVectorRecallService(chapter_service=chapter_service, vector_repository=vector_repo)

    items = service.recall(
        _RecallQuery(work_id=work.id, query_text="继续写作，回收旧灯塔线索", top_k=2, score_threshold=0.6)
    )

    assert len(items) == 1
    assert items[0]["source_id"] == chapter.id.value
    assert "向量召回命中的旧灯塔片段" in items[0]["content_text"]
    assert items[0]["metadata"]["recall_backend"] == "vector_repository"
    assert items[0]["metadata"]["vector_id"] == "vec_001"
    assert vector_repo.calls[0]["source_type"] == "confirmed_chapter"


def test_context_vector_recall_service_prefers_formal_ports_when_available() -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("正式端口召回作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="本地章节正文不应抢在正式端口前被使用。", expected_version=1)
    embedding_provider = _StubEmbeddingProvider()
    vector_store = _StubVectorStore()
    service = ContextVectorRecallService(
        chapter_service=chapter_service,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    items = service.recall(
        _RecallQuery(work_id=work.id, query_text="继续写作，回收灯塔线索", top_k=2, score_threshold=0.6)
    )

    assert len(items) == 1
    assert items[0]["source_id"] == "chapter_port_1"
    assert items[0]["metadata"]["recall_backend"] == "vector_store_port"
    assert items[0]["metadata"]["vector_id"] == "v_port_1"
    assert embedding_provider.calls[0]["request_id"] == "req_test"
    assert vector_store.calls[0]["work_id"] == work.id
    assert vector_store.calls[0]["top_k"] == 2


def test_context_vector_recall_service_falls_back_to_local_matching_when_vector_repository_returns_empty() -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("回退召回作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。",
        expected_version=1,
    )
    vector_repo = _StubVectorRepository([])
    service = ContextVectorRecallService(chapter_service=chapter_service, vector_repository=vector_repo)

    items = service.recall(
        _RecallQuery(work_id=work.id, query_text="请回收旧灯塔和海图残页线索", top_k=2, score_threshold=0.6)
    )

    assert len(items) == 1
    assert items[0]["source_id"] == chapter.id.value
    assert items[0]["metadata"]["recall_backend"] == "local_fallback"
    assert "海图残页" in items[0]["content_text"]
