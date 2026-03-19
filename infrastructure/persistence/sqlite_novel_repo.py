"""
SQLite小说仓储实现

作者：孔利群
"""

# 文件路径：infrastructure/persistence/sqlite_novel_repo.py


import sqlite3
import json
from typing import Optional, List
from datetime import datetime

from domain.types import NovelId
from domain.entities.novel import Novel
from domain.repositories.novel_repository import INovelRepository


class SQLiteNovelRepository(INovelRepository):
    """SQLite小说仓储实现"""

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
                CREATE TABLE IF NOT EXISTS novels (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT,
                    genre TEXT,
                    target_word_count INTEGER,
                    current_word_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')

    def save(self, novel: Novel) -> None:
        """保存小说"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO novels 
                (id, title, author, genre, target_word_count, current_word_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                novel.id.value,
                novel.title,
                novel.author,
                novel.genre,
                novel.target_word_count,
                novel.current_word_count,
                novel.created_at.isoformat(),
                novel.updated_at.isoformat()
            ))

    def find_by_id(self, novel_id: NovelId) -> Optional[Novel]:
        """根据ID查找小说"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM novels WHERE id = ?', 
                (novel_id.value,)
            )
            row = cursor.fetchone()
            
            if row:
                return Novel(
                    id=NovelId(row['id']),
                    title=row['title'],
                    author=row['author'] or '',
                    genre=row['genre'] or '',
                    target_word_count=row['target_word_count'] or 0,
                    current_word_count=row['current_word_count'] or 0,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
            return None

    def find_all(self) -> List[Novel]:
        """查找所有小说"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM novels ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            return [
                Novel(
                    id=NovelId(row['id']),
                    title=row['title'],
                    author=row['author'] or '',
                    genre=row['genre'] or '',
                    target_word_count=row['target_word_count'] or 0,
                    current_word_count=row['current_word_count'] or 0,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
                for row in rows
            ]

    def delete(self, novel_id: NovelId) -> None:
        """删除小说"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM novels WHERE id = ?', (novel_id.value,))
