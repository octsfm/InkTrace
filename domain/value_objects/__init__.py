# 文件：模块：__init__
"""
值对象模块

作者：孔利群
"""

# 文件路径：domain/value_objects/__init__.py


from domain.value_objects.style_profile import StyleProfile
from domain.value_objects.character_state import CharacterState
from domain.value_objects.writing_config import WritingConfig

__all__ = [
    'StyleProfile',
    'CharacterState',
    'WritingConfig'
]
