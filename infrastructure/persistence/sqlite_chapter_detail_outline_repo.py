from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Optional

from domain.entities.chapter_detail_outline import (
    ChapterDetailOutline,
    ChapterDetailOutlineScene,
)
from domain.repositories.chapter_detail_outline_repository import IChapterDetailOutlineRepository
from domain.types import ChapterId
from infrastructure.persistence.sqlite_utils import connect_sqlite


class SQLiteChapterDetailOutlineRepository(IChapterDetailOutlineRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_table()

    def _init_table(self) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chapter_detail_outlines (
                    chapter_id TEXT PRIMARY KEY,
                    scenes_json TEXT DEFAULT '[]',
                    notes TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.commit()

    def find_by_chapter_id(self, chapter_id: ChapterId) -> Optional[ChapterDetailOutline]:
        with connect_sqlite(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM chapter_detail_outlines WHERE chapter_id = ?",
                (str(chapter_id),),
            ).fetchone()
            if not row:
                return None
            try:
                scenes_raw = json.loads(row["scenes_json"] or "[]")
            except Exception:
                scenes_raw = []
            scenes = []
            for item in scenes_raw or []:
                if not isinstance(item, dict):
                    continue
                scenes.append(
                    ChapterDetailOutlineScene(
                        scene_no=int(item.get("scene_no") or 0),
                        goal=str(item.get("goal") or ""),
                        conflict=str(item.get("conflict") or ""),
                        turning_point=str(item.get("turning_point") or ""),
                        hook=str(item.get("hook") or ""),
                        foreshadow=str(item.get("foreshadow") or ""),
                        target_words=int(item.get("target_words") or 0),
                    )
                )
            return ChapterDetailOutline(
                chapter_id=ChapterId(row["chapter_id"]),
                scenes=scenes,
                notes=str(row["notes"] or ""),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            )

    def save(self, outline: ChapterDetailOutline) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chapter_detail_outlines
                (chapter_id, scenes_json, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(outline.chapter_id),
                    json.dumps(
                        [
                            {
                                "scene_no": int(scene.scene_no or 0),
                                "goal": str(scene.goal or ""),
                                "conflict": str(scene.conflict or ""),
                                "turning_point": str(scene.turning_point or ""),
                                "hook": str(scene.hook or ""),
                                "foreshadow": str(scene.foreshadow or ""),
                                "target_words": int(scene.target_words or 0),
                            }
                            for scene in (outline.scenes or [])
                        ],
                        ensure_ascii=False,
                    ),
                    str(outline.notes or ""),
                    outline.created_at.isoformat(),
                    outline.updated_at.isoformat(),
                ),
            )
            conn.commit()
