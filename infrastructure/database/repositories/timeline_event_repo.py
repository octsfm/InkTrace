from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from domain.entities.writing_assets import TimelineEvent
from infrastructure.database.session import get_connection, initialize_database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TimelineEventRepo:
    def __init__(self) -> None:
        initialize_database()

    def list_by_work(self, work_id: str) -> list[TimelineEvent]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, work_id, order_index, title, description, chapter_id, version, created_at, updated_at
                FROM timeline_events
                WHERE work_id = ?
                ORDER BY order_index ASC
                """,
                (str(work_id),),
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def find_by_id(self, event_id: str) -> Optional[TimelineEvent]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, work_id, order_index, title, description, chapter_id, version, created_at, updated_at
                FROM timeline_events
                WHERE id = ?
                """,
                (str(event_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, event: TimelineEvent) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO timeline_events (
                    id, work_id, order_index, title, description, chapter_id, version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    work_id = excluded.work_id,
                    order_index = excluded.order_index,
                    title = excluded.title,
                    description = excluded.description,
                    chapter_id = excluded.chapter_id,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    str(event.id),
                    str(event.work_id),
                    int(event.order_index),
                    str(event.title or ""),
                    str(event.description or ""),
                    str(event.chapter_id) if event.chapter_id else None,
                    int(event.version or 1),
                    event.created_at.isoformat(),
                    event.updated_at.isoformat(),
                ),
            )

    def delete(self, event_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM timeline_events WHERE id = ?", (str(event_id),))

    def reorder(self, work_id: str, mappings: list[dict]) -> list[TimelineEvent]:
        updated_at = _now_iso()
        with get_connection() as conn:
            for item in mappings:
                conn.execute(
                    """
                    UPDATE timeline_events
                    SET order_index = ?, updated_at = ?
                    WHERE id = ? AND work_id = ?
                    """,
                    (int(item["order_index"]), updated_at, str(item["id"]), str(work_id)),
                )
        return self.list_by_work(work_id)

    def clear_chapter_ref(self, chapter_id: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE timeline_events
                SET chapter_id = NULL, updated_at = ?
                WHERE chapter_id = ?
                """,
                (_now_iso(), str(chapter_id)),
            )

    def delete_by_work(self, work_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM timeline_events WHERE work_id = ?", (str(work_id),))

    @staticmethod
    def _row_to_entity(row) -> TimelineEvent:
        return TimelineEvent(
            id=str(row["id"]),
            work_id=str(row["work_id"]),
            order_index=int(row["order_index"]),
            title=str(row["title"]),
            description=str(row["description"]),
            chapter_id=str(row["chapter_id"]) if row["chapter_id"] is not None else None,
            version=int(row["version"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
