from __future__ import annotations

from datetime import datetime
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
                SELECT id, work_id, title, content, chapter_number, order_index, version, created_at, updated_at
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
                SELECT id, work_id, title, content, chapter_number, order_index, version, created_at, updated_at
                FROM chapters
                WHERE id = ?
                """,
                (str(chapter_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, chapter: Chapter) -> None:
        insert_columns = [
            "id",
            "work_id",
            "title",
            "content",
            "chapter_number",
            "order_index",
            "version",
            "created_at",
            "updated_at",
        ]
        insert_values = [
            chapter.id.value,
            chapter.novel_id.value,
            chapter.title,
            chapter.content,
            chapter.number,
            chapter.order_index,
            chapter.version,
            chapter.created_at.isoformat(),
            chapter.updated_at.isoformat(),
        ]
        update_assignments = [
            "title = excluded.title",
            "content = excluded.content",
            "chapter_number = excluded.chapter_number",
            "order_index = excluded.order_index",
            "version = excluded.version",
            "updated_at = excluded.updated_at",
        ]

        if "novel_id" in self._columns:
            insert_columns.append("novel_id")
            insert_values.append(chapter.novel_id.value)
            update_assignments.append("novel_id = excluded.novel_id")

        if "number" in self._columns:
            insert_columns.append("number")
            insert_values.append(chapter.number)
            update_assignments.append("number = excluded.number")

        if "word_count" in self._columns:
            insert_columns.append("word_count")
            insert_values.append(chapter.word_count)
            update_assignments.append("word_count = excluded.word_count")

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
        with get_connection() as conn:
            conn.execute(
                f"""
                INSERT INTO chapters ({columns_sql})
                VALUES ({placeholders_sql})
                ON CONFLICT(id) DO UPDATE SET
                    {update_sql}
                """,
                tuple(insert_values),
            )

    def delete(self, chapter_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM chapters WHERE id = ?", (str(chapter_id),))

    @staticmethod
    def _row_to_entity(row) -> Chapter:
        return Chapter(
            id=ChapterId(str(row["id"])),
            novel_id=NovelId(str(row["work_id"])),
            number=int(row["chapter_number"]),
            title=str(row["title"]),
            content=str(row["content"]),
            status=ChapterStatus.DRAFT,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            order_index=int(row["order_index"]),
            version=int(row["version"]),
        )
