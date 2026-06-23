from __future__ import annotations

from domain.entities.ai.models import ChapterChunk, ChunkEmbedding
from infrastructure.persistence.sqlite_vector_index_repo import SQLiteVectorIndexRepository


def test_chapter_chunk_and_chunk_embedding_models_preserve_required_fields() -> None:
    chunk = ChapterChunk(
        chunk_id="chunk_001",
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_order=3,
        chunk_index=1,
        text_excerpt="顾迟在旧灯塔里发现海图残页。",
        content_hash="hash_001",
        token_count=12,
        start_offset=0,
        end_offset=18,
        source="confirmed_chapter",
        index_status="active",
        stale_status="fresh",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
    )
    embedding = ChunkEmbedding(
        embedding_id="embedding_001",
        chunk_id="chunk_001",
        work_id="work_001",
        chapter_id="chapter_001",
        embedding_model="local-hash-embedding",
        embedding_provider="local",
        embedding_version="v1",
        vector_id="vec_001",
        content_hash="hash_001",
        status="active",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
    )

    assert chunk.source == "confirmed_chapter"
    assert chunk.index_status == "active"
    assert chunk.stale_status == "fresh"
    assert embedding.vector_id == "vec_001"
    assert embedding.content_hash == chunk.content_hash


def test_sqlite_vector_index_repository_persists_chunks_embeddings_and_status(tmp_path) -> None:
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    chunk = ChapterChunk(
        chunk_id="chunk_001",
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_order=1,
        chunk_index=0,
        text_excerpt="顾迟在旧灯塔里发现海图残页。",
        content_hash="hash_001",
        token_count=12,
        start_offset=0,
        end_offset=18,
        source="confirmed_chapter",
        index_status="active",
        stale_status="fresh",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
    )
    embedding = ChunkEmbedding(
        embedding_id="embedding_001",
        chunk_id="chunk_001",
        work_id="work_001",
        chapter_id="chapter_001",
        embedding_model="local-hash-embedding",
        embedding_provider="local",
        embedding_version="v1",
        vector_id="vec_001",
        content_hash="hash_001",
        status="active",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
    )

    saved_chunk = repo.save_chunk(chunk)
    saved_embedding = repo.save_embedding_metadata(embedding)
    status = repo.update_index_status(
        "work_001",
        {
            "work_id": "work_001",
            "index_status": "ready",
            "stale_status": "fresh",
            "chunk_count": 1,
            "active_embedding_count": 1,
            "updated_at": "2026-06-15T10:05:00Z",
        },
    )

    by_work = repo.get_chunks_by_work("work_001")
    by_chapter = repo.get_chunks_by_chapter("work_001", "chapter_001")
    stale_count = repo.mark_chunks_stale_by_chapter("work_001", "chapter_001")
    stale_items = repo.list_stale_chunks("work_001")
    current_status = repo.get_index_status_by_work("work_001")

    assert saved_chunk.chunk_id == "chunk_001"
    assert saved_embedding.embedding_id == "embedding_001"
    assert status["index_status"] == "ready"
    assert len(by_work) == 1
    assert len(by_chapter) == 1
    assert stale_count == 1
    assert stale_items[0].chunk_id == "chunk_001"
    assert stale_items[0].stale_status == "stale"
    assert current_status is not None
    assert current_status["chunk_count"] == 1


def test_sqlite_vector_index_repository_marks_embedding_metadata_stale_and_deleted(tmp_path) -> None:
    repo = SQLiteVectorIndexRepository(tmp_path / "vector-index.db")
    chunk = ChapterChunk(
        chunk_id="chunk_001",
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_order=1,
        chunk_index=0,
        text_excerpt="顾迟在旧灯塔里发现海图残页。",
        content_hash="hash_001",
        token_count=12,
        start_offset=0,
        end_offset=18,
        source="confirmed_chapter",
        index_status="active",
        stale_status="fresh",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
    )
    embedding = ChunkEmbedding(
        embedding_id="embedding_001",
        chunk_id="chunk_001",
        work_id="work_001",
        chapter_id="chapter_001",
        embedding_model="local-hash-embedding",
        embedding_provider="local",
        embedding_version="v1",
        vector_id="vec_001",
        content_hash="hash_001",
        status="active",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
    )

    repo.save_chunk(chunk)
    repo.save_embedding_metadata(embedding)

    stale_count = repo.mark_embeddings_stale_by_chapter("work_001", "chapter_001")
    stale_items = repo.get_embedding_metadata_by_chapter("work_001", "chapter_001")

    assert stale_count == 1
    assert len(stale_items) == 1
    assert stale_items[0].status == "stale"

    deleted_count = repo.mark_embeddings_deleted_by_chapter("work_001", "chapter_001")
    deleted_items = repo.get_embedding_metadata_by_chapter("work_001", "chapter_001")

    assert deleted_count == 1
    assert len(deleted_items) == 1
    assert deleted_items[0].status == "deleted"
