import json
import os
import sqlite3
from datetime import datetime
from typing import Optional

from domain.entities.chapter_outline import ChapterOutline
from domain.repositories.chapter_outline_repository import IChapterOutlineRepository
from domain.types import ChapterId


class SQLiteChapterOutlineRepository(IChapterOutlineRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_table()

    def _init_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chapter_outlines (
                    chapter_id TEXT PRIMARY KEY,
                    goal TEXT DEFAULT '',
                    conflict TEXT DEFAULT '',
                    events TEXT DEFAULT '[]',
                    character_progress TEXT DEFAULT '',
                    ending_hook TEXT DEFAULT '',
                    opening_continuation TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            self._ensure_column(conn, "chapter_outlines", "character_progress", "TEXT DEFAULT ''")
            self._ensure_column(conn, "chapter_outlines", "opening_continuation", "TEXT DEFAULT ''")
            conn.commit()

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = {row[1] for row in rows}
        if column_name in columns:
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def find_by_chapter_id(self, chapter_id: ChapterId) -> Optional[ChapterOutline]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM chapter_outlines WHERE chapter_id = ?",
                (str(chapter_id),),
            ).fetchone()
            if not row:
                return None
            try:
                events = json.loads(row["events"] or "[]")
            except Exception:
                events = []
            return ChapterOutline(
                chapter_id=ChapterId(row["chapter_id"]),
                goal=row["goal"] or "",
                conflict=row["conflict"] or "",
                events=[str(x) for x in (events or [])],
                character_progress=row["character_progress"] or "",
                ending_hook=row["ending_hook"] or "",
                opening_continuation=row["opening_continuation"] or "",
                notes=row["notes"] or "",
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            )

    def save(self, outline: ChapterOutline) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chapter_outlines
                (chapter_id, goal, conflict, events, character_progress, ending_hook, opening_continuation, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(outline.chapter_id),
                    outline.goal,
                    outline.conflict,
                    json.dumps(outline.events or [], ensure_ascii=False),
                    outline.character_progress,
                    outline.ending_hook,
                    outline.opening_continuation,
                    outline.notes,
                    outline.created_at.isoformat(),
                    outline.updated_at.isoformat(),
                ),
            )
            conn.commit()
