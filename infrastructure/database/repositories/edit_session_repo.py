from __future__ import annotations

from datetime import datetime
from typing import Optional

from domain.entities.edit_session import EditSession
from infrastructure.database.session import get_connection, initialize_database


class EditSessionRepo:
    def __init__(self) -> None:
        initialize_database()

    def find_by_work_id(self, work_id: str) -> Optional[EditSession]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT work_id, last_open_chapter_id, cursor_position, scroll_top, updated_at
                FROM edit_sessions
                WHERE work_id = ?
                """,
                (str(work_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, session: EditSession) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO edit_sessions (work_id, last_open_chapter_id, cursor_position, scroll_top, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(work_id) DO UPDATE SET
                    last_open_chapter_id = excluded.last_open_chapter_id,
                    cursor_position = excluded.cursor_position,
                    scroll_top = excluded.scroll_top,
                    updated_at = excluded.updated_at
                """,
                (
                    session.work_id,
                    session.last_open_chapter_id,
                    session.cursor_position,
                    session.scroll_top,
                    session.updated_at.isoformat(),
                ),
            )

    @staticmethod
    def _row_to_entity(row) -> EditSession:
        return EditSession(
            work_id=str(row["work_id"]),
            last_open_chapter_id=str(row["last_open_chapter_id"]),
            cursor_position=int(row["cursor_position"]),
            scroll_top=int(row["scroll_top"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
