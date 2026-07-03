from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from domain.entities.ai.models import ChapterMention, MentionEntityType, MentionStatus
from domain.repositories.ai.chapter_mention_repository import ChapterMentionRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class SQLiteChapterMentionRepository(ChapterMentionRepository):
    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def replace_by_chapter(self, chapter_id: str, mentions: list[ChapterMention]) -> list[ChapterMention]:
        normalized_chapter_id = str(chapter_id or "")
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            existing_rows = conn.execute(
                "SELECT mention_id FROM chapter_mentions WHERE chapter_id = ?",
                (normalized_chapter_id,),
            ).fetchall()
            existing_ids = {str(row["mention_id"]) for row in existing_rows}
            next_items: list[ChapterMention] = []
            seen_ids: set[str] = set()
            for item in mentions:
                mention_id = str(item.mention_id or "").strip() or f"m_{uuid4().hex[:12]}"
                normalized = item.model_copy(
                    update={
                        "mention_id": mention_id,
                        "chapter_id": normalized_chapter_id,
                    }
                )
                conn.execute(
                    """
                    INSERT INTO chapter_mentions (
                        mention_id, chapter_id, work_id, entity_type, entity_id, entity_name_snapshot,
                        start_pos, end_pos, source, ai_suggestion_id, status, is_active,
                        validation_detail, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(mention_id) DO UPDATE SET
                        chapter_id = excluded.chapter_id,
                        work_id = excluded.work_id,
                        entity_type = excluded.entity_type,
                        entity_id = excluded.entity_id,
                        entity_name_snapshot = excluded.entity_name_snapshot,
                        start_pos = excluded.start_pos,
                        end_pos = excluded.end_pos,
                        source = excluded.source,
                        ai_suggestion_id = excluded.ai_suggestion_id,
                        status = excluded.status,
                        is_active = excluded.is_active,
                        validation_detail = excluded.validation_detail,
                        updated_at = excluded.updated_at
                    """,
                    self._params(normalized),
                )
                next_items.append(normalized)
                seen_ids.add(mention_id)
            omitted_ids = sorted(existing_ids - seen_ids)
            for mention_id in omitted_ids:
                conn.execute(
                    """
                    UPDATE chapter_mentions
                    SET status = ?, is_active = 0
                    WHERE mention_id = ?
                    """,
                    (MentionStatus.BROKEN.value, mention_id),
                )
            conn.commit()
            return self.get_by_chapter(normalized_chapter_id)
        finally:
            conn.close()

    def get_by_chapter(self, chapter_id: str) -> list[ChapterMention]:
        return self._query(
            """
            SELECT * FROM chapter_mentions
            WHERE chapter_id = ?
            ORDER BY start_pos ASC, created_at ASC
            """,
            (str(chapter_id or ""),),
        )

    def get_by_id(self, mention_id: str) -> ChapterMention | None:
        items = self._query(
            "SELECT * FROM chapter_mentions WHERE mention_id = ?",
            (str(mention_id or ""),),
        )
        return items[0] if items else None

    def mark_entity_deleted(self, entity_type: MentionEntityType, entity_id: str) -> None:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                UPDATE chapter_mentions
                SET status = ?, is_active = 0
                WHERE entity_type = ? AND entity_id = ?
                """,
                (MentionStatus.INACTIVE_ENTITY.value, entity_type.value, str(entity_id or "")),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_entity(self, entity_type: MentionEntityType, entity_id: str) -> list[ChapterMention]:
        return self._query(
            """
            SELECT * FROM chapter_mentions
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY created_at ASC
            """,
            (entity_type.value, str(entity_id or "")),
        )

    def _query(self, sql: str, params: tuple[object, ...]) -> list[ChapterMention]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_mention(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _row_to_mention(row: sqlite3.Row) -> ChapterMention:
        return ChapterMention.model_validate(
            {
                "mention_id": row["mention_id"],
                "chapter_id": row["chapter_id"],
                "work_id": row["work_id"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "entity_name_snapshot": row["entity_name_snapshot"],
                "start_pos": int(row["start_pos"] or 0),
                "end_pos": int(row["end_pos"] or 0),
                "source": row["source"],
                "ai_suggestion_id": row["ai_suggestion_id"],
                "status": row["status"],
                "is_active": bool(row["is_active"]),
                "validation_detail": row["validation_detail"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    @staticmethod
    def _params(item: ChapterMention) -> tuple[object, ...]:
        return (
            item.mention_id,
            item.chapter_id,
            item.work_id,
            item.entity_type.value,
            item.entity_id,
            item.entity_name_snapshot,
            item.start_pos,
            item.end_pos,
            item.source.value,
            item.ai_suggestion_id,
            item.status.value,
            1 if item.is_active else 0,
            item.validation_detail,
            item.created_at,
            item.updated_at,
        )
