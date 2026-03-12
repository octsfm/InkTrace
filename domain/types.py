"""
领域层类型定义

作者：孔利群
"""

from dataclasses import dataclass
from enum import Enum
from typing import NewType


@dataclass(frozen=True)
class NovelId:
    """小说ID值对象"""
    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NovelId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class ChapterId:
    """章节ID值对象"""
    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ChapterId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class CharacterId:
    """人物ID值对象"""
    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CharacterId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class OutlineId:
    """大纲ID值对象"""
    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OutlineId):
            return False
        return self.value == other.value


class ChapterStatus(Enum):
    """章节状态枚举"""
    DRAFT = "draft"
    PUBLISHED = "published"


class PlotType(Enum):
    """剧情类型枚举"""
    MAIN = "main"
    SUB = "sub"
    FORESHADOWING = "foreshadowing"


class PlotStatus(Enum):
    """剧情状态枚举"""
    PLANNED = "planned"
    ONGOING = "ongoing"
    COMPLETED = "completed"


class CharacterRole(Enum):
    """人物角色枚举"""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
