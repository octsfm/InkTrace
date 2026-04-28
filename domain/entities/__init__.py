# 文件：模块：__init__
"""
领域层实体模块

作者：孔利群
"""

# 文件路径：domain/entities/__init__.py


from domain.entities.chapter import Chapter
from domain.entities.edit_session import EditSession
from domain.entities.outline import Outline, VolumeOutline, PlotNode
from domain.entities.novel import Novel
from domain.entities.work import Work

__all__ = [
    'Chapter',
    'EditSession',
    'Outline',
    'VolumeOutline',
    'PlotNode',
    'Novel',
    'Work'
]
