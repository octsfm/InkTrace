from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from domain.entities.chapter import Chapter
from domain.types import ChapterId, ChapterStatus, NovelId
from infrastructure.database.session import get_connection, initialize_database


class ChapterRepo:
    def __init__(self) -> None:
        initialize_database()
        self._columns = self._load_columns()

    def _load_columns(self) -> set[str]:
        with get_connection() as conn:
            rows = conn.execute("PRAGMA table_info(chapters)").fetchall()
        return {str(row["name"]) for row in rows}

    def list_by_work(self, work_id: str) -> List[Chapter]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, work_id, title, content, word_count, order_index, version, created_at, updated_at
                FROM chapters
                WHERE work_id = ?
                ORDER BY order_index ASC
                """,
                (str(work_id),),
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def find_by_id(self, chapter_id: str) -> Optional[Chapter]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, work_id, title, content, word_count, order_index, version, created_at, updated_at
                FROM chapters
                WHERE id = ?
                """,
                (str(chapter_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def _build_save_payload(self, chapter: Chapter) -> tuple[str, tuple]:
        insert_columns = [
            "id",
            "work_id",
            "title",
            "content",
            "word_count",
            "order_index",
            "version",
            "created_at",
            "updated_at",
        ]
        insert_values = [
            chapter.id.value,
            chapter.work_id.value,
            chapter.title,
            chapter.content,
            chapter.word_count,
            chapter.order_index,
            chapter.version,
            chapter.created_at.isoformat(),
            chapter.updated_at.isoformat(),
        ]
        update_assignments = [
            "title = excluded.title",
            "content = excluded.content",
            "word_count = excluded.word_count",
            "order_index = excluded.order_index",
            "version = excluded.version",
            "updated_at = excluded.updated_at",
        ]

        # Legacy columns are synchronized only when present in an existing database.
        if "novel_id" in self._columns:
            insert_columns.append("novel_id")
            insert_values.append(chapter.work_id.value)
            update_assignments.append("novel_id = excluded.novel_id")
        if "number" in self._columns:
            insert_columns.append("number")
            insert_values.append(chapter.order_index)
            update_assignments.append("number = excluded.number")
        if "chapter_number" in self._columns:
            insert_columns.append("chapter_number")
            insert_values.append(chapter.order_index)
            update_assignments.append("chapter_number = excluded.chapter_number")
        if "summary" in self._columns:
            insert_columns.append("summary")
            insert_values.append(chapter.summary)
            update_assignments.append("summary = excluded.summary")
        if "status" in self._columns:
            insert_columns.append("status")
            insert_values.append(chapter.status.value)
            update_assignments.append("status = excluded.status")

        columns_sql = ", ".join(insert_columns)
        placeholders_sql = ", ".join(["?"] * len(insert_columns))
        update_sql = ",\n                    ".join(update_assignments)
        sql = f"""
                INSERT INTO chapters ({columns_sql})
                VALUES ({placeholders_sql})
                ON CONFLICT(id) DO UPDATE SET
                    {update_sql}
                """
        return sql, tuple(insert_values)

    def _save_with_connection(self, conn: sqlite3.Connection, chapter: Chapter) -> None:
        sql, params = self._build_save_payload(chapter)
        conn.execute(sql, params)

    def save(self, chapter: Chapter) -> None:
        with get_connection() as conn:
            self._save_with_connection(conn, chapter)

    def save_many(self, chapters: List[Chapter]) -> None:
        if not chapters:
            return
        with get_connection() as conn:
            for chapter in chapters:
                self._save_with_connection(conn, chapter)

    def reorder(self, work_id: str, mappings: list[dict]) -> None:
        if not mappings:
            return
        updated_at = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            for item in mappings:
                order_index = int(item["order_index"])
                conn.execute(
                    """
                    UPDATE chapters
                    SET order_index = ?, updated_at = ?
                    WHERE id = ? AND work_id = ?
                    """,
                    (order_index, updated_at, str(item["id"]), str(work_id)),
                )
                if "number" in self._columns:
                    conn.execute(
                        "UPDATE chapters SET number = ? WHERE id = ? AND work_id = ?",
                        (order_index, str(item["id"]), str(work_id)),
                    )
                if "chapter_number" in self._columns:
                    conn.execute(
                        "UPDATE chapters SET chapter_number = ? WHERE id = ? AND work_id = ?",
                        (order_index, str(item["id"]), str(work_id)),
                    )

    def delete(self, chapter_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM chapters WHERE id = ?", (str(chapter_id),))

    @staticmethod
    def _row_to_entity(row) -> Chapter:
        return Chapter(
            id=ChapterId(str(row["id"])),
            work_id=NovelId(str(row["work_id"])),
            title=str(row["title"]),
            content=str(row["content"]),
            status=ChapterStatus.DRAFT,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            order_index=int(row["order_index"]),
            version=int(row["version"]),
        )
