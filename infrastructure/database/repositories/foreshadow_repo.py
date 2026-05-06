from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from domain.entities.writing_assets import Foreshadow
from infrastructure.database.session import get_connection, initialize_database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ForeshadowRepo:
    def __init__(self) -> None:
        initialize_database()

    def list_by_work(self, work_id: str, status: str | None = None) -> list[Foreshadow]:
        params: list[str] = [str(work_id)]
        status_clause = ""
        if status is not None:
            status_clause = " AND status = ?"
            params.append(str(status))
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, work_id, status, title, description,
                       introduced_chapter_id, resolved_chapter_id,
                       version, created_at, updated_at
                FROM foreshadows
                WHERE work_id = ?{status_clause}
                ORDER BY updated_at DESC, id ASC
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def find_by_id(self, foreshadow_id: str) -> Optional[Foreshadow]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, work_id, status, title, description,
                       introduced_chapter_id, resolved_chapter_id,
                       version, created_at, updated_at
                FROM foreshadows
                WHERE id = ?
                """,
                (str(foreshadow_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, foreshadow: Foreshadow) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO foreshadows (
                    id, work_id, status, title, description,
                    introduced_chapter_id, resolved_chapter_id,
                    version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    work_id = excluded.work_id,
                    status = excluded.status,
                    title = excluded.title,
                    description = excluded.description,
                    introduced_chapter_id = excluded.introduced_chapter_id,
                    resolved_chapter_id = excluded.resolved_chapter_id,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    str(foreshadow.id),
                    str(foreshadow.work_id),
                    str(foreshadow.status or "open"),
                    str(foreshadow.title or ""),
                    str(foreshadow.description or ""),
                    str(foreshadow.introduced_chapter_id) if foreshadow.introduced_chapter_id else None,
                    str(foreshadow.resolved_chapter_id) if foreshadow.resolved_chapter_id else None,
                    int(foreshadow.version or 1),
                    foreshadow.created_at.isoformat(),
                    foreshadow.updated_at.isoformat(),
                ),
            )

    def delete(self, foreshadow_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM foreshadows WHERE id = ?", (str(foreshadow_id),))

    def clear_chapter_ref(self, chapter_id: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE foreshadows
                SET introduced_chapter_id = CASE WHEN introduced_chapter_id = ? THEN NULL ELSE introduced_chapter_id END,
                    resolved_chapter_id = CASE WHEN resolved_chapter_id = ? THEN NULL ELSE resolved_chapter_id END,
                    updated_at = ?
                WHERE introduced_chapter_id = ? OR resolved_chapter_id = ?
                """,
                (str(chapter_id), str(chapter_id), _now_iso(), str(chapter_id), str(chapter_id)),
            )

    def delete_by_work(self, work_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM foreshadows WHERE work_id = ?", (str(work_id),))

    @staticmethod
    def _row_to_entity(row) -> Foreshadow:
        return Foreshadow(
            id=str(row["id"]),
            work_id=str(row["work_id"]),
            status=str(row["status"]),
            title=str(row["title"]),
            description=str(row["description"]),
            introduced_chapter_id=str(row["introduced_chapter_id"]) if row["introduced_chapter_id"] is not None else None,
            resolved_chapter_id=str(row["resolved_chapter_id"]) if row["resolved_chapter_id"] is not None else None,
            version=int(row["version"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
