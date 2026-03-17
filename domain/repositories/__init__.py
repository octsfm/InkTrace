# 文件：模块：__init__
"""
仓储接口模块

作者：孔利群
"""

# 文件路径：domain/repositories/__init__.py


from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.character_repository import ICharacterRepository
from domain.repositories.outline_repository import IOutlineRepository

__all__ = [
    'INovelRepository',
    'IChapterRepository',
    'ICharacterRepository',
    'IOutlineRepository'
]
