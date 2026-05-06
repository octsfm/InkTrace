from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from domain.entities.writing_assets import ChapterOutline, WorkOutline
from infrastructure.database.session import get_connection, initialize_database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _from_json_text(value: str) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _clear_chapter_ref_in_tree(value: Any, chapter_id: str) -> Any:
    if isinstance(value, list):
        return [_clear_chapter_ref_in_tree(item, chapter_id) for item in value]
    if not isinstance(value, dict):
        return value
    next_value = dict(value)
    if next_value.get("chapter_ref") == chapter_id:
        next_value["chapter_ref"] = None
    if isinstance(next_value.get("children"), list):
        next_value["children"] = [_clear_chapter_ref_in_tree(item, chapter_id) for item in next_value["children"]]
    return next_value


class WorkOutlineRepo:
    def __init__(self) -> None:
        initialize_database()

    def find_by_work(self, work_id: str) -> Optional[WorkOutline]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, work_id, content_text, content_tree_json, version, created_at, updated_at
                FROM work_outlines
                WHERE work_id = ?
                """,
                (str(work_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, outline: WorkOutline) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO work_outlines (
                    id, work_id, content_text, content_tree_json, version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    work_id = excluded.work_id,
                    content_text = excluded.content_text,
                    content_tree_json = excluded.content_tree_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    str(outline.id),
                    str(outline.work_id),
                    str(outline.content_text or ""),
                    _to_json_text(outline.content_tree_json),
                    int(outline.version or 1),
                    outline.created_at.isoformat(),
                    outline.updated_at.isoformat(),
                ),
            )

    def clear_chapter_refs(self, work_id: str, chapter_id: str) -> None:
        outline = self.find_by_work(work_id)
        if outline is None:
            return
        cleared_tree = _clear_chapter_ref_in_tree(outline.content_tree_json, str(chapter_id))
        updated_at = _now_iso()
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE work_outlines
                SET content_tree_json = ?, updated_at = ?
                WHERE work_id = ?
                """,
                (_to_json_text(cleared_tree), updated_at, str(work_id)),
            )

    def delete_by_work(self, work_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM work_outlines WHERE work_id = ?", (str(work_id),))

    @staticmethod
    def _row_to_entity(row) -> WorkOutline:
        return WorkOutline(
            id=str(row["id"]),
            work_id=str(row["work_id"]),
            content_text=str(row["content_text"]),
            content_tree_json=_from_json_text(str(row["content_tree_json"])),
            version=int(row["version"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class ChapterOutlineRepo:
    def __init__(self) -> None:
        initialize_database()

    def find_by_chapter(self, chapter_id: str) -> Optional[ChapterOutline]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, chapter_id, content_text, content_tree_json, version, created_at, updated_at
                FROM chapter_outlines
                WHERE chapter_id = ?
                """,
                (str(chapter_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, outline: ChapterOutline) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chapter_outlines (
                    id, chapter_id, content_text, content_tree_json, version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    chapter_id = excluded.chapter_id,
                    content_text = excluded.content_text,
                    content_tree_json = excluded.content_tree_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    str(outline.id),
                    str(outline.chapter_id),
                    str(outline.content_text or ""),
                    _to_json_text(outline.content_tree_json),
                    int(outline.version or 1),
                    outline.created_at.isoformat(),
                    outline.updated_at.isoformat(),
                ),
            )

    def delete_by_chapter(self, chapter_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM chapter_outlines WHERE chapter_id = ?", (str(chapter_id),))

    def delete_by_work(self, work_id: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                DELETE FROM chapter_outlines
                WHERE chapter_id IN (
                    SELECT id FROM chapters WHERE work_id = ?
                )
                """,
                (str(work_id),),
            )

    @staticmethod
    def _row_to_entity(row) -> ChapterOutline:
        return ChapterOutline(
            id=str(row["id"]),
            chapter_id=str(row["chapter_id"]),
            content_text=str(row["content_text"]),
            content_tree_json=_from_json_text(str(row["content_tree_json"])),
            version=int(row["version"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
