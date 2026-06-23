from __future__ import annotations

import sqlite3
from pathlib import Path

from domain.entities.ai.models import ChapterChunk, ChunkEmbedding
from domain.repositories.ai.vector_index_repository import VectorIndexRepositoryPort
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class SQLiteVectorIndexRepository(VectorIndexRepositoryPort):
    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def save_chunk(self, chunk: ChapterChunk) -> ChapterChunk:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO chapter_chunks (
                    chunk_id, work_id, chapter_id, chapter_order, chunk_index,
                    text_excerpt, content_hash, token_count, start_offset, end_offset,
                    source, index_status, stale_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    work_id = excluded.work_id,
                    chapter_id = excluded.chapter_id,
                    chapter_order = excluded.chapter_order,
                    chunk_index = excluded.chunk_index,
                    text_excerpt = excluded.text_excerpt,
                    content_hash = excluded.content_hash,
                    token_count = excluded.token_count,
                    start_offset = excluded.start_offset,
                    end_offset = excluded.end_offset,
                    source = excluded.source,
                    index_status = excluded.index_status,
                    stale_status = excluded.stale_status,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                self._chunk_params(chunk),
            )
            conn.commit()
            return chunk
        finally:
            conn.close()

    def save_embedding_metadata(self, metadata: ChunkEmbedding) -> ChunkEmbedding:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO chunk_embeddings (
                    embedding_id, chunk_id, work_id, chapter_id, embedding_model,
                    embedding_provider, embedding_version, vector_id, content_hash,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(embedding_id) DO UPDATE SET
                    chunk_id = excluded.chunk_id,
                    work_id = excluded.work_id,
                    chapter_id = excluded.chapter_id,
                    embedding_model = excluded.embedding_model,
                    embedding_provider = excluded.embedding_provider,
                    embedding_version = excluded.embedding_version,
                    vector_id = excluded.vector_id,
                    content_hash = excluded.content_hash,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                self._embedding_params(metadata),
            )
            conn.commit()
            return metadata
        finally:
            conn.close()

    def get_embedding_metadata_by_chapter(self, work_id: str, chapter_id: str) -> list[ChunkEmbedding]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(
                """
                SELECT * FROM chunk_embeddings
                WHERE work_id = ? AND chapter_id = ?
                ORDER BY created_at ASC, embedding_id ASC
                """,
                (work_id, chapter_id),
            ).fetchall()
            return [ChunkEmbedding.model_validate(dict(row)) for row in rows]
        finally:
            conn.close()

    def get_chunks_by_work(self, work_id: str) -> list[ChapterChunk]:
        return self._query_chunks(
            "SELECT * FROM chapter_chunks WHERE work_id = ? ORDER BY chapter_order ASC, chunk_index ASC",
            (work_id,),
        )

    def get_chunks_by_chapter(self, work_id: str, chapter_id: str) -> list[ChapterChunk]:
        return self._query_chunks(
            """
            SELECT * FROM chapter_chunks
            WHERE work_id = ? AND chapter_id = ?
            ORDER BY chunk_index ASC
            """,
            (work_id, chapter_id),
        )

    def mark_chunks_stale_by_chapter(self, work_id: str, chapter_id: str) -> int:
        return self._update_chunk_status(
            work_id=work_id,
            chapter_id=chapter_id,
            index_status="stale",
            stale_status="stale",
        )

    def mark_chunks_deleted_by_chapter(self, work_id: str, chapter_id: str) -> int:
        return self._update_chunk_status(
            work_id=work_id,
            chapter_id=chapter_id,
            index_status="deleted",
            stale_status="stale",
        )

    def mark_embeddings_stale_by_chapter(self, work_id: str, chapter_id: str) -> int:
        return self._update_embedding_status(work_id=work_id, chapter_id=chapter_id, status="stale")

    def mark_embeddings_deleted_by_chapter(self, work_id: str, chapter_id: str) -> int:
        return self._update_embedding_status(work_id=work_id, chapter_id=chapter_id, status="deleted")

    def get_index_status_by_work(self, work_id: str) -> dict[str, object] | None:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            row = conn.execute("SELECT * FROM vector_index_status WHERE work_id = ?", (work_id,)).fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            conn.close()

    def update_index_status(self, work_id: str, status: dict[str, object]) -> dict[str, object]:
        payload = {
            "work_id": work_id,
            "index_status": str(status.get("index_status", "missing") or "missing"),
            "stale_status": str(status.get("stale_status", "fresh") or "fresh"),
            "chunk_count": int(status.get("chunk_count", 0) or 0),
            "active_embedding_count": int(status.get("active_embedding_count", 0) or 0),
            "updated_at": str(status.get("updated_at", "") or ""),
        }
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO vector_index_status (
                    work_id, index_status, stale_status, chunk_count, active_embedding_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(work_id) DO UPDATE SET
                    index_status = excluded.index_status,
                    stale_status = excluded.stale_status,
                    chunk_count = excluded.chunk_count,
                    active_embedding_count = excluded.active_embedding_count,
                    updated_at = excluded.updated_at
                """,
                (
                    payload["work_id"],
                    payload["index_status"],
                    payload["stale_status"],
                    payload["chunk_count"],
                    payload["active_embedding_count"],
                    payload["updated_at"],
                ),
            )
            conn.commit()
            return payload
        finally:
            conn.close()

    def list_stale_chunks(self, work_id: str = "") -> list[ChapterChunk]:
        if work_id:
            return self._query_chunks(
                """
                SELECT * FROM chapter_chunks
                WHERE work_id = ? AND stale_status != 'fresh'
                ORDER BY chapter_order ASC, chunk_index ASC
                """,
                (work_id,),
            )
        return self._query_chunks(
            """
            SELECT * FROM chapter_chunks
            WHERE stale_status != 'fresh'
            ORDER BY work_id ASC, chapter_order ASC, chunk_index ASC
            """,
            (),
        )

    def _update_chunk_status(self, *, work_id: str, chapter_id: str, index_status: str, stale_status: str) -> int:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            cursor = conn.execute(
                """
                UPDATE chapter_chunks
                SET index_status = ?, stale_status = ?
                WHERE work_id = ? AND chapter_id = ?
                """,
                (index_status, stale_status, work_id, chapter_id),
            )
            conn.commit()
            return int(cursor.rowcount or 0)
        finally:
            conn.close()

    def _update_embedding_status(self, *, work_id: str, chapter_id: str, status: str) -> int:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            cursor = conn.execute(
                """
                UPDATE chunk_embeddings
                SET status = ?, updated_at = ?
                WHERE work_id = ? AND chapter_id = ?
                """,
                (status, self._now(), work_id, chapter_id),
            )
            conn.commit()
            return int(cursor.rowcount or 0)
        finally:
            conn.close()

    def _query_chunks(self, sql: str, params: tuple[object, ...]) -> list[ChapterChunk]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_chunk(row) for row in rows]
        finally:
            conn.close()

    def _row_to_chunk(self, row: sqlite3.Row) -> ChapterChunk:
        return ChapterChunk.model_validate(dict(row))

    def _chunk_params(self, chunk: ChapterChunk) -> tuple[object, ...]:
        return (
            chunk.chunk_id,
            chunk.work_id,
            chunk.chapter_id,
            chunk.chapter_order,
            chunk.chunk_index,
            chunk.text_excerpt,
            chunk.content_hash,
            chunk.token_count,
            chunk.start_offset,
            chunk.end_offset,
            chunk.source,
            chunk.index_status,
            chunk.stale_status,
            chunk.created_at,
            chunk.updated_at,
        )

    def _embedding_params(self, metadata: ChunkEmbedding) -> tuple[object, ...]:
        return (
            metadata.embedding_id,
            metadata.chunk_id,
            metadata.work_id,
            metadata.chapter_id,
            metadata.embedding_model,
            metadata.embedding_provider,
            metadata.embedding_version,
            metadata.vector_id,
            metadata.content_hash,
            metadata.status,
            metadata.created_at,
            metadata.updated_at,
        )

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
