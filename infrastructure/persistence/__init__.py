# 文件：模块：__init__
"""
持久化层模块

作者：孔利群
"""

# 文件路径：infrastructure/persistence/__init__.py


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
