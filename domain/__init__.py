# 文件：模块：__init__
"""
领域层基础模块

作者：孔利群
"""

# 文件路径：domain/__init__.py


from domain.types import (
    NovelId, ChapterId, CharacterId, OutlineId,
    ChapterStatus, PlotType, PlotStatus, CharacterRole
)
from domain.exceptions import (
    DomainException, EntityNotFoundError, InvalidEntityStateError,
    InvalidOperationError, ValidationError
)

__all__ = [
    'NovelId', 'ChapterId', 'CharacterId', 'OutlineId',
    'ChapterStatus', 'PlotType', 'PlotStatus', 'CharacterRole',
    'DomainException', 'EntityNotFoundError', 'InvalidEntityStateError',
    'InvalidOperationError', 'ValidationError'
]
