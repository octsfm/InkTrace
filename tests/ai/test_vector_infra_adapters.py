from __future__ import annotations

from application.services.ai.context_vector_recall_service import ContextVectorRecallService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.ai.providers.local_embedding_provider import LocalEmbeddingProvider
from infrastructure.persistence.chroma_vector_store import ChromaVectorStore


class _RecallQuery:
    def __init__(self, *, work_id: str, query_text: str, top_k: int = 3, score_threshold: float = 0.6) -> None:
        self.work_id = work_id
        self.query_text = query_text
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.target_chapter_id = ""
        self.allow_stale = False
        self.request_id = "req_adapter"
        self.trace_id = "trace_adapter"


def _build_services():
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    return work_service, chapter_service


def test_local_embedding_provider_returns_stable_embeddings() -> None:
    provider = LocalEmbeddingProvider(vector_dimension=16)

    embedding_a = provider.embed_text(text="灯塔里的海图线索")
    embedding_b = provider.embed_text(text="灯塔里的海图线索")
    batch = provider.embed_batch(texts=["灯塔里的海图线索", "海雾中的钟声"])
    info = provider.get_embedding_model_info()

    assert len(embedding_a) == 16
    assert embedding_a == embedding_b
    assert len(batch) == 2
    assert all(len(item) == 16 for item in batch)
    assert info.vector_dimension == 16


def test_chroma_vector_store_upsert_and_search_similar(tmp_path) -> None:
    provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="test_vectors")

    vector_id = store.upsert_vector(
        vector_id="vec_001",
        embedding=provider.embed_text(text="顾迟在旧灯塔里发现海图残页"),
        metadata={
            "work_id": "work_1",
            "chapter_id": "chapter_1",
            "chunk_id": "chunk_1",
            "status": "active",
            "source": "confirmed_chapter",
            "chapter_title": "第一章",
            "text_excerpt": "顾迟在旧灯塔里发现海图残页",
        },
    )

    results = store.search_similar(
        query_embedding=provider.embed_text(text="回收旧灯塔和海图残页线索"),
        work_id="work_1",
        top_k=3,
        score_threshold=0.1,
        exclude_chapter_ids=[],
        allow_stale=False,
    )

    assert vector_id == "vec_001"
    assert len(results) == 1
    assert results[0]["vector_id"] == "vec_001"
    assert results[0]["metadata"]["chapter_id"] == "chapter_1"
    assert results[0]["text_excerpt"] == "顾迟在旧灯塔里发现海图残页"
    assert results[0]["score"] >= 0.1


def test_context_vector_recall_service_uses_real_adapters(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("真实向量召回作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(chapter.id.value, title="第一章", content="顾迟在旧灯塔里发现父亲留下的海图残页。", expected_version=1)
    provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="recall_vectors")
    store.upsert_vector(
        vector_id="vec_ctx_1",
        embedding=provider.embed_text(text="顾迟在旧灯塔里发现父亲留下的海图残页。"),
        metadata={
            "work_id": work.id,
            "chapter_id": chapter.id.value,
            "chunk_id": "chunk_ctx_1",
            "status": "active",
            "source": "confirmed_chapter",
            "chapter_title": "第一章",
            "text_excerpt": "顾迟在旧灯塔里发现父亲留下的海图残页。",
        },
    )
    service = ContextVectorRecallService(
        chapter_service=chapter_service,
        embedding_provider=provider,
        vector_store=store,
    )

    items = service.recall(
        _RecallQuery(work_id=work.id, query_text="请回收旧灯塔和海图残页线索", top_k=2, score_threshold=0.1)
    )

    assert len(items) == 1
    assert items[0]["source_id"] == chapter.id.value
    assert items[0]["metadata"]["recall_backend"] == "vector_store_port"
    assert items[0]["metadata"]["vector_id"] == "vec_ctx_1"
