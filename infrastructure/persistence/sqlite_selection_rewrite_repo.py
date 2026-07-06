from __future__ import annotations

import sqlite3
from pathlib import Path

from domain.entities.ai.models import SelectionRewriteCandidate
from domain.repositories.ai.selection_rewrite_repository import SelectionRewriteRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class SQLiteSelectionRewriteRepository(SelectionRewriteRepository):
    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def save(self, candidate: SelectionRewriteCandidate) -> SelectionRewriteCandidate:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO selection_rewrite_candidates (
                    rewrite_id, chapter_id, work_id, rewrite_mode, source_text, source_hash,
                    source_start_pos, source_end_pos, rewritten_text, applied_text,
                    word_count_before, word_count_after, diff_summary, status, model_role,
                    chapter_revision, draft_revision, draft_text_hash, draft_length,
                    edited_before_apply, context_before, context_after, error_code,
                    error_message, request_id, trace_id, created_at, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rewrite_id) DO UPDATE SET
                    chapter_id = excluded.chapter_id,
                    work_id = excluded.work_id,
                    rewrite_mode = excluded.rewrite_mode,
                    source_text = excluded.source_text,
                    source_hash = excluded.source_hash,
                    source_start_pos = excluded.source_start_pos,
                    source_end_pos = excluded.source_end_pos,
                    rewritten_text = excluded.rewritten_text,
                    applied_text = excluded.applied_text,
                    word_count_before = excluded.word_count_before,
                    word_count_after = excluded.word_count_after,
                    diff_summary = excluded.diff_summary,
                    status = excluded.status,
                    model_role = excluded.model_role,
                    chapter_revision = excluded.chapter_revision,
                    draft_revision = excluded.draft_revision,
                    draft_text_hash = excluded.draft_text_hash,
                    draft_length = excluded.draft_length,
                    edited_before_apply = excluded.edited_before_apply,
                    context_before = excluded.context_before,
                    context_after = excluded.context_after,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    request_id = excluded.request_id,
                    trace_id = excluded.trace_id,
                    created_at = excluded.created_at,
                    applied_at = excluded.applied_at
                """,
                self._params(candidate),
            )
            conn.commit()
            return self.get(candidate.rewrite_id) or candidate
        finally:
            conn.close()

    def get(self, rewrite_id: str) -> SelectionRewriteCandidate | None:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            row = conn.execute(
                "SELECT * FROM selection_rewrite_candidates WHERE rewrite_id = ?",
                (str(rewrite_id or ""),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_candidate(row)
        finally:
            conn.close()

    def list_by_chapter(self, chapter_id: str) -> list[SelectionRewriteCandidate]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(
                """
                SELECT * FROM selection_rewrite_candidates
                WHERE chapter_id = ?
                ORDER BY created_at DESC, rewrite_id DESC
                """,
                (str(chapter_id or ""),),
            ).fetchall()
            return [self._row_to_candidate(row) for row in rows]
        finally:
            conn.close()

    def delete_by_chapter(self, chapter_id: str) -> int:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            cursor = conn.execute(
                "DELETE FROM selection_rewrite_candidates WHERE chapter_id = ?",
                (str(chapter_id or ""),),
            )
            conn.commit()
            return int(cursor.rowcount or 0)
        finally:
            conn.close()

    @staticmethod
    def _row_to_candidate(row: sqlite3.Row) -> SelectionRewriteCandidate:
        return SelectionRewriteCandidate.model_validate(
            {
                "rewrite_id": row["rewrite_id"],
                "chapter_id": row["chapter_id"],
                "work_id": row["work_id"],
                "rewrite_mode": row["rewrite_mode"],
                "source_text": row["source_text"],
                "source_hash": row["source_hash"],
                "source_start_pos": int(row["source_start_pos"] or 0),
                "source_end_pos": int(row["source_end_pos"] or 0),
                "rewritten_text": row["rewritten_text"],
                "applied_text": row["applied_text"],
                "word_count_before": int(row["word_count_before"] or 0),
                "word_count_after": int(row["word_count_after"] or 0),
                "diff_summary": row["diff_summary"],
                "status": row["status"],
                "model_role": row["model_role"],
                "chapter_revision": int(row["chapter_revision"] or 0),
                "draft_revision": int(row["draft_revision"] or 0),
                "draft_text_hash": row["draft_text_hash"],
                "draft_length": int(row["draft_length"] or 0),
                "edited_before_apply": bool(row["edited_before_apply"]),
                "context_before": row["context_before"],
                "context_after": row["context_after"],
                "error_code": row["error_code"],
                "error_message": row["error_message"],
                "request_id": row["request_id"],
                "trace_id": row["trace_id"],
                "created_at": row["created_at"],
                "applied_at": row["applied_at"],
            }
        )

    @staticmethod
    def _params(item: SelectionRewriteCandidate) -> tuple[object, ...]:
        return (
            item.rewrite_id,
            item.chapter_id,
            item.work_id,
            item.rewrite_mode.value,
            item.source_text,
            item.source_hash,
            item.source_start_pos,
            item.source_end_pos,
            item.rewritten_text,
            item.applied_text,
            item.word_count_before,
            item.word_count_after,
            item.diff_summary,
            item.status.value,
            item.model_role,
            item.chapter_revision,
            item.draft_revision,
            item.draft_text_hash,
            item.draft_length,
            1 if item.edited_before_apply else 0,
            item.context_before,
            item.context_after,
            item.error_code,
            item.error_message,
            item.request_id,
            item.trace_id,
            item.created_at,
            item.applied_at,
        )
