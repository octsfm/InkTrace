"""
CharacterState值对象模块

作者：孔利群
"""

# 文件路径：domain/value_objects/character_state.py


from dataclasses import dataclass
from typing import List

from domain.types import CharacterId, ChapterId


@dataclass(frozen=True)
class CharacterState:
    """
    人物状态值对象
    
    表示人物在某一时刻的状态快照。
    """
# 文件：模块：character_state

    character_id: CharacterId
    location: str
    cultivation_level: str
    health_status: str
    emotional_state: str
    possessions: List[str]
    active_goals: List[str]
    chapter_id: ChapterId
