from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from domain.entities.chapter import Chapter
from domain.types import ChapterId, ChapterStatus, NovelId
from infrastructure.database.session import get_connection, initialize_database


class ChapterRepo:
    def __init__(self) -> None:
        initialize_database()

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
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chapters (id, work_id, title, content, chapter_number, order_index, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    chapter_number = excluded.chapter_number,
                    order_index = excluded.order_index,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    chapter.id.value,
                    chapter.novel_id.value,
                    chapter.title,
                    chapter.content,
                    chapter.number,
                    chapter.order_index,
                    chapter.version,
                    chapter.created_at.isoformat(),
                    chapter.updated_at.isoformat(),
                ),
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
