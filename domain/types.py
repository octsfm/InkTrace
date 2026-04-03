"""
领域层类型定义

作者：孔利群
"""

# 文件路径：domain/types.py


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
# 文件：模块：types

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
# 文件：模块：types

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
# 文件：模块：types

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
# 文件：模块：types

    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"


@dataclass(frozen=True)
class ProjectId:
    """项目ID值对象"""
    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProjectId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class TemplateId:
    """模板ID值对象"""
# 文件：模块：types

    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TemplateId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class TechniqueId:
    """功法ID值对象"""
    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TechniqueId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class FactionId:
    """势力ID值对象"""
# 文件：模块：types

    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FactionId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class LocationId:
    """地点ID值对象"""
    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LocationId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class ItemId:
    """物品ID值对象"""
# 文件：模块：types

    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ItemId):
            return False
        return self.value == other.value


@dataclass(frozen=True)
class WorldviewId:
    """世界观ID值对象"""
    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorldviewId):
            return False
        return self.value == other.value


class ProjectStatus(Enum):
    """项目状态枚举"""
# 文件：模块：types

    ACTIVE = "active"
    ARCHIVED = "archived"


class OrganizeJobStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSE_REQUESTED = "pause_requested"
    PAUSED = "paused"
    RESUME_REQUESTED = "resume_requested"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    DONE = "done"
    ERROR = "error"


class GenreType(Enum):
    """题材类型枚举"""
    XUANHUAN = "xuanhuan"
    XIANXIA = "xianxia"
    DUSHI = "dushi"
    LISHI = "lishi"
    KEHUAN = "kehuan"
    WUXIA = "wuxia"
    QIHUAN = "qihuan"
    OTHER = "other"


class RelationType(Enum):
    """人物关系类型枚举"""
# 文件：模块：types

    FAMILY = "family"
    FRIEND = "friend"
    ENEMY = "enemy"
    LOVER = "lover"
    MASTER_DISCIPLE = "master_disciple"
    ALLY = "ally"
    RIVAL = "rival"
    OTHER = "other"


class ItemType(Enum):
    """物品类型枚举"""
    ARTIFACT = "artifact"
    PILL = "pill"
    MATERIAL = "material"
    SCRIPTURE = "scripture"
    OTHER = "other"
