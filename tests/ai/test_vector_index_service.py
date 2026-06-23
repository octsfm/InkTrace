from __future__ import annotations

from datetime import datetime, timezone

from application.services.ai.vector_index_service import VectorIndexService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import AIJobStatus
from infrastructure.ai.providers.local_embedding_provider import LocalEmbeddingProvider
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.persistence.chroma_vector_store import ChromaVectorStore
from infrastructure.persistence.sqlite_vector_index_repo import SQLiteVectorIndexRepository


def _build_services():
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    return work_service, chapter_service


def _publish_chapter(chapter_service: ChapterService, chapter_id: str) -> None:
    chapter = chapter_service.chapter_repo.find_by_id(chapter_id)
    assert chapter is not None
    chapter.publish(datetime.now(timezone.utc))
    chapter_service.chapter_repo.save(chapter)


class _CancellingEmbeddingProvider(LocalEmbeddingProvider):
    def __init__(self, *, on_embed=None, vector_dimension: int = 16) -> None:
        super().__init__(vector_dimension=vector_dimension)
        self._on_embed = on_embed

    def embed_text(self, *, text: str, request_id: str = "", trace_id: str = "") -> list[float]:
        result = super().embed_text(text=text, request_id=request_id, trace_id=trace_id)
        if self._on_embed is not None:
            self._on_embed()
        return result


class _FailingAfterFirstEmbedProvider(LocalEmbeddingProvider):
    def __init__(self, *, vector_dimension: int = 16) -> None:
        super().__init__(vector_dimension=vector_dimension)
        self._call_count = 0

    def embed_text(self, *, text: str, request_id: str = "", trace_id: str = "") -> list[float]:
        self._call_count += 1
        if self._call_count > 1:
            raise RuntimeError("embedding_failed")
        return super().embed_text(text=text, request_id=request_id, trace_id=trace_id)


def test_vector_index_service_builds_index_only_for_published_chapters(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("索引构建作品", "作者")
    published = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        published.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。" * 40,
        expected_version=1,
    )
    _publish_chapter(chapter_service, published.id.value)
    draft = chapter_service.create_chapter(work.id, "第二章")
    chapter_service.update_chapter(
        draft.id.value,
        content="这是一段仍处于草稿态的内容，不应进入正式索引。",
        expected_version=1,
    )
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="build_index")
    service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=provider,
        vector_store=store,
        vector_index_repository=repo,
    )

    result = service.build_initial_index(work.id)
    chunks = repo.get_chunks_by_work(work.id)
    status = repo.get_index_status_by_work(work.id)

    assert result.index_status == "ready"
    assert result.indexed_chapter_count == 1
    assert result.indexed_chunk_count >= 1
    assert result.failed_chunk_count == 0
    assert all(item.chapter_id != draft.id.value for item in chunks)
    assert all(item.chapter_id == published.id.value for item in chunks)
    assert status is not None
    assert status["index_status"] == "ready"
    assert status["chunk_count"] == result.indexed_chunk_count


def test_vector_index_service_marks_small_chunk_warning_for_short_published_chapter(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("短章节索引作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟回头看见塔顶微弱的灯。",
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="small_chunk")
    service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=provider,
        vector_store=store,
        vector_index_repository=repo,
    )

    result = service.build_initial_index(work.id)
    chunks = repo.get_chunks_by_work(work.id)

    assert result.index_status == "ready"
    assert result.indexed_chapter_count == 1
    assert result.indexed_chunk_count == 1
    assert result.warning_count == 1
    assert "small_chunk" in result.warnings
    assert chunks[0].index_status == "active"


def test_vector_index_service_marks_chapter_stale_without_auto_reindex(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("章节过期作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。" * 30,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="stale_mark")
    service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=provider,
        vector_store=store,
        vector_index_repository=repo,
    )

    initial = service.build_initial_index(work.id)
    old_chunk = repo.get_chunks_by_chapter(work.id, chapter.id.value)[0]
    old_vector_id = f"vec_{old_chunk.chunk_id}"

    stale_count = service.mark_chapter_stale(work.id, chapter.id.value)
    chunks = repo.get_chunks_by_chapter(work.id, chapter.id.value)
    status = repo.get_index_status_by_work(work.id)
    vector_status = store.get_vector_status(vector_id=old_vector_id)

    assert initial.index_status == "ready"
    assert stale_count >= 1
    assert any(item.index_status == "stale" for item in chunks)
    assert status is not None
    assert status["index_status"] == "stale"
    assert status["stale_status"] == "partial_stale"
    assert vector_status is not None
    assert vector_status["status"] == "stale"


def test_vector_index_service_reindexes_single_chapter_after_stale_mark(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("章节重建作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。" * 30,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="chapter_reindex")
    service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=provider,
        vector_store=store,
        vector_index_repository=repo,
    )

    service.build_initial_index(work.id)
    old_chunks = repo.get_chunks_by_chapter(work.id, chapter.id.value)
    old_vector_ids = [f"vec_{item.chunk_id}" for item in old_chunks]
    chapter_service.update_chapter(
        chapter.id.value,
        content="顾迟在旧灯塔里发现父亲留下的海图残页，并在夹层中找到新的航线标记。" * 30,
        expected_version=2,
    )
    service.mark_chapter_stale(work.id, chapter.id.value)

    result = service.reindex_chapter(work.id, chapter.id.value)
    chunks = repo.get_chunks_by_chapter(work.id, chapter.id.value)
    active_chunks = [item for item in chunks if item.index_status == "active"]
    stale_chunks = [item for item in chunks if item.index_status == "stale"]
    status = repo.get_index_status_by_work(work.id)

    assert result.index_status == "ready"
    assert result.indexed_chapter_count == 1
    assert result.indexed_chunk_count >= 1
    assert active_chunks
    assert stale_chunks
    assert all(item.content_hash != old_chunks[0].content_hash for item in active_chunks)
    assert status is not None
    assert status["index_status"] == "ready"
    for vector_id in old_vector_ids:
        vector_status = store.get_vector_status(vector_id=vector_id)
        assert vector_status is not None
        assert vector_status["status"] == "stale"


def test_vector_index_service_reindexes_whole_work_under_controlled_entry(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("全书重建作品", "作者")
    chapter_one = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter_one.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。" * 30,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter_one.id.value)
    chapter_two = chapter_service.create_chapter(work.id, "第二章")
    chapter_service.update_chapter(
        chapter_two.id.value,
        content="第二章的潮汐图指向更远的海域，暗示下一轮冲突。" * 30,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter_two.id.value)
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="work_reindex")
    service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=provider,
        vector_store=store,
        vector_index_repository=repo,
    )

    service.build_initial_index(work.id)
    chapter_service.update_chapter(
        chapter_two.id.value,
        content="第二章的潮汐图指向更远的海域，并暴露主角误判的代价。" * 30,
        expected_version=2,
    )
    service.mark_chapter_stale(work.id, chapter_two.id.value)

    result = service.reindex_work(work.id)
    status = repo.get_index_status_by_work(work.id)
    active_chunk_ids = {item.chunk_id for item in repo.get_chunks_by_work(work.id) if item.index_status == "active"}

    assert result.index_status == "ready"
    assert result.indexed_chapter_count == 2
    assert result.indexed_chunk_count >= 2
    assert status is not None
    assert status["index_status"] == "ready"
    assert status["stale_status"] == "fresh"
    assert active_chunk_ids


def test_vector_index_service_marks_removed_chapter_deleted_and_blocks_old_vectors(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("章节删除作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。" * 30,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="delete_index")
    service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=provider,
        vector_store=store,
        vector_index_repository=repo,
    )

    service.build_initial_index(work.id)
    old_chunks = repo.get_chunks_by_chapter(work.id, chapter.id.value)
    old_vector_ids = [f"vec_{item.chunk_id}" for item in old_chunks]

    deleted_count = service.remove_chapter_from_index(work.id, chapter.id.value)
    chunks = repo.get_chunks_by_chapter(work.id, chapter.id.value)
    status = repo.get_index_status_by_work(work.id)

    assert deleted_count >= 1
    assert chunks
    assert all(item.index_status == "deleted" for item in chunks)
    assert status is not None
    assert status["index_status"] == "stale"
    assert status["stale_status"] == "partial_stale"
    for vector_id in old_vector_ids:
        assert store.get_vector_status(vector_id=vector_id) is None


def test_vector_index_service_ignores_late_embedding_result_after_cancel(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("取消后迟到结果作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。" * 30,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    cancelled = {"value": False}
    provider = _CancellingEmbeddingProvider(on_embed=lambda: cancelled.__setitem__("value", True), vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="cancel_guard")
    service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=provider,
        vector_store=store,
        vector_index_repository=repo,
    )

    result = service.build_initial_index(work.id, should_continue=lambda: not cancelled["value"])
    chunks = repo.get_chunks_by_work(work.id)
    status = repo.get_index_status_by_work(work.id)

    assert result.index_status == "failed"
    assert result.failed_chunk_count >= 1
    assert result.degraded_reason == "index_build_failed"
    assert not chunks
    assert status is not None
    assert status["index_status"] == "failed"
    assert status["chunk_count"] == 0


def test_vector_index_service_preserves_old_index_when_work_reindex_fails(tmp_path) -> None:
    work_service, chapter_service = _build_services()
    work = work_service.create_work("重建失败保留旧索引作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。" * 80,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    initial_provider = LocalEmbeddingProvider(vector_dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"), collection_name="preserve_old_index")
    service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=initial_provider,
        vector_store=store,
        vector_index_repository=repo,
    )
    initial = service.build_initial_index(work.id)
    old_chunks = repo.get_chunks_by_work(work.id)
    old_vector_ids = [f"vec_{item.chunk_id}" for item in old_chunks]

    chapter_service.update_chapter(
        chapter.id.value,
        content="顾迟在旧灯塔里发现父亲留下的海图残页，并在夹层中找到新的航线标记。" * 80,
        expected_version=2,
    )
    failing_service = VectorIndexService(
        chapter_service=chapter_service,
        embedding_provider=_FailingAfterFirstEmbedProvider(vector_dimension=16),
        vector_store=store,
        vector_index_repository=repo,
    )

    result = failing_service.reindex_work(work.id)
    chunks = repo.get_chunks_by_work(work.id)
    active_chunks = [item for item in chunks if item.index_status == "active"]

    assert initial.index_status == "ready"
    assert result.index_status == "failed" or result.index_status == "degraded"
    assert active_chunks
    assert {item.chunk_id for item in old_chunks}.issubset({item.chunk_id for item in active_chunks})
    for vector_id in old_vector_ids:
        vector_status = store.get_vector_status(vector_id=vector_id)
        assert vector_status is not None
        assert vector_status["status"] == "active"
