"""
伏笔仓储SQLite实现

作者：孔利群
"""

import sqlite3
from datetime import datetime
from typing import Optional, List

from domain.entities.foreshadow import Foreshadow, ForeshadowStatus
from domain.repositories.foreshadow_repository import IForeshadowRepository
from domain.types import ForeshadowId, NovelId, ChapterId


class SQLiteForeshadowRepository(IForeshadowRepository):
    """伏笔仓储SQLite实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_table()
    
    def _init_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS foreshadows (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT NOT NULL,
                    chapter_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    foreshadow_type TEXT DEFAULT 'plot',
                    status TEXT DEFAULT 'pending',
                    resolved_chapter_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id),
                    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
                )
            """)
            conn.commit()
    
    def find_by_id(self, foreshadow_id: ForeshadowId) -> Optional[Foreshadow]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM foreshadows WHERE id = ?", (str(foreshadow_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_foreshadow(row)
        return None
    
    def find_by_novel(self, novel_id: NovelId) -> List[Foreshadow]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM foreshadows WHERE novel_id = ? ORDER BY created_at DESC",
                (str(novel_id),)
            )
            return [self._row_to_foreshadow(row) for row in cursor.fetchall()]
    
    def find_pending(self, novel_id: NovelId) -> List[Foreshadow]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM foreshadows WHERE novel_id = ? AND status = 'pending' ORDER BY created_at DESC",
                (str(novel_id),)
            )
            return [self._row_to_foreshadow(row) for row in cursor.fetchall()]
    
    def find_by_chapter(self, chapter_id: ChapterId) -> List[Foreshadow]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM foreshadows WHERE chapter_id = ?",
                (str(chapter_id),)
            )
            return [self._row_to_foreshadow(row) for row in cursor.fetchall()]
    
    def save(self, foreshadow: Foreshadow) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO foreshadows 
                (id, novel_id, chapter_id, content, foreshadow_type, status, resolved_chapter_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(foreshadow.id),
                str(foreshadow.novel_id),
                str(foreshadow.chapter_id),
                foreshadow.content,
                foreshadow.foreshadow_type,
                foreshadow.status.value,
                str(foreshadow.resolved_chapter_id) if foreshadow.resolved_chapter_id else None,
                foreshadow.created_at.isoformat(),
                foreshadow.updated_at.isoformat()
            ))
            conn.commit()
    
    def delete(self, foreshadow_id: ForeshadowId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM foreshadows WHERE id = ?", (str(foreshadow_id),))
            conn.commit()
    
    def resolve(self, foreshadow_id: ForeshadowId, chapter_id: ChapterId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE foreshadows SET status = 'resolved', resolved_chapter_id = ?, updated_at = ? WHERE id = ?",
                (ForeshadowStatus.RESOLVED.value, str(chapter_id), datetime.now().isoformat(), str(foreshadow_id))
            )
            conn.commit()
    
    def count(self, novel_id: NovelId) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM foreshadows WHERE novel_id = ?", (str(novel_id),)
            )
            return cursor.fetchone()[0]
    
    def _row_to_foreshadow(self, row: sqlite3.Row) -> Foreshadow:
        return Foreshadow(
            id=ForeshadowId(row["id"]),
            novel_id=NovelId(row["novel_id"]),
            chapter_id=ChapterId(row["chapter_id"]),
            content=row["content"],
            foreshadow_type=row["foreshadow_type"],
            status=ForeshadowStatus(row["status"]),
            resolved_chapter_id=ChapterId(row["resolved_chapter_id"]) if row["resolved_chapter_id"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
