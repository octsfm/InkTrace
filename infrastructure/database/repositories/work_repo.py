from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from domain.entities.work import Work
from infrastructure.database.session import get_connection, initialize_database


class WorkRepo:
    def __init__(self) -> None:
        initialize_database()

    def list_all(self) -> List[Work]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, author, current_word_count, created_at, updated_at FROM works ORDER BY updated_at DESC"
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def find_by_id(self, work_id: str) -> Optional[Work]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, title, author, current_word_count, created_at, updated_at FROM works WHERE id = ?",
                (str(work_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, work: Work) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO works (id, title, author, current_word_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    author = excluded.author,
                    current_word_count = excluded.current_word_count,
                    updated_at = excluded.updated_at
                """,
                (
                    work.id,
                    work.title,
                    work.author,
                    work.current_word_count,
                    work.created_at.isoformat(),
                    work.updated_at.isoformat(),
                ),
            )

    def delete(self, work_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM works WHERE id = ?", (str(work_id),))

    @staticmethod
    def _row_to_entity(row) -> Work:
        return Work(
            id=str(row["id"]),
            title=str(row["title"]),
            author=str(row["author"]),
            current_word_count=int(row["current_word_count"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
