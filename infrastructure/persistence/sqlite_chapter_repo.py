"""
SQLite章节仓储实现

作者：孔利群
"""

import sqlite3
from typing import Optional, List
from datetime import datetime

from domain.types import ChapterId, NovelId, ChapterStatus
from domain.entities.chapter import Chapter
from domain.repositories.chapter_repository import IChapterRepository


class SQLiteChapterRepository(IChapterRepository):
    """SQLite章节仓储实现"""

    def __init__(self, db_path: str):
        """
        初始化仓储
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chapters (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT NOT NULL,
                    number INTEGER NOT NULL,
                    title TEXT,
                    content TEXT,
                    word_count INTEGER,
                    summary TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            ''')

    def save(self, chapter: Chapter) -> None:
        """保存章节"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO chapters 
                (id, novel_id, number, title, content, word_count, summary, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chapter.id.value,
                chapter.novel_id.value,
                chapter.number,
                chapter.title,
                chapter.content,
                chapter.word_count,
                chapter.summary,
                chapter.status.value,
                chapter.created_at.isoformat(),
                chapter.updated_at.isoformat()
            ))

    def find_by_id(self, chapter_id: ChapterId) -> Optional[Chapter]:
        """根据ID查找章节"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM chapters WHERE id = ?', 
                (chapter_id.value,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_chapter(row)
            return None

    def find_by_novel(self, novel_id: NovelId) -> List[Chapter]:
        """查找小说的所有章节"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM chapters WHERE novel_id = ? ORDER BY number',
                (novel_id.value,)
            )
            rows = cursor.fetchall()
            return [self._row_to_chapter(row) for row in rows]

    def find_latest(self, novel_id: NovelId, count: int) -> List[Chapter]:
        """查找小说的最新N个章节"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM chapters WHERE novel_id = ? ORDER BY number DESC LIMIT ?',
                (novel_id.value, count)
            )
            rows = cursor.fetchall()
            return [self._row_to_chapter(row) for row in rows]

    def delete(self, chapter_id: ChapterId) -> None:
        """删除章节"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM chapters WHERE id = ?', (chapter_id.value,))

    def _row_to_chapter(self, row: sqlite3.Row) -> Chapter:
        """将数据库行转换为章节实体"""
        return Chapter(
            id=ChapterId(row['id']),
            novel_id=NovelId(row['novel_id']),
            number=row['number'],
            title=row['title'] or '',
            content=row['content'] or '',
            status=ChapterStatus(row['status']),
            summary=row['summary'] or '',
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
