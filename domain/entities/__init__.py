# 文件：模块：__init__
"""
领域层实体模块

作者：孔利群
"""

# 文件路径：domain/entities/__init__.py


from domain.entities.chapter import Chapter
from domain.entities.character import Character, CharacterRelationship
from domain.entities.outline import Outline, VolumeOutline, PlotNode
from domain.entities.novel import Novel

__all__ = [
    'Chapter', 
    'Character', 
    'CharacterRelationship',
    'Outline',
    'VolumeOutline',
    'PlotNode',
    'Novel'
]
