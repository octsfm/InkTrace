"""
持久化层模块

作者：孔利群
"""

from infrastructure.persistence.sqlite_novel_repo import SQLiteNovelRepository
from infrastructure.persistence.sqlite_chapter_repo import SQLiteChapterRepository
from infrastructure.persistence.sqlite_character_repo import SQLiteCharacterRepository
from infrastructure.persistence.sqlite_outline_repo import SQLiteOutlineRepository

__all__ = [
    'SQLiteNovelRepository',
    'SQLiteChapterRepository',
    'SQLiteCharacterRepository',
    'SQLiteOutlineRepository'
]
