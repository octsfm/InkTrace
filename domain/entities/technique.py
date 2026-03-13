"""
功法实体

作者：孔利群
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from domain.types import TechniqueId, NovelId


@dataclass(frozen=True)
class TechniqueLevel:
    """功法等级值对象"""
    name: str
    rank: int
    
    def __lt__(self, other: "TechniqueLevel") -> bool:
        return self.rank < other.rank
    
    def __le__(self, other: "TechniqueLevel") -> bool:
        return self.rank <= other.rank
    
    def __gt__(self, other: "TechniqueLevel") -> bool:
        return self.rank > other.rank
    
    def __ge__(self, other: "TechniqueLevel") -> bool:
        return self.rank >= other.rank
    
    def to_dict(self) -> dict:
        return {"name": self.name, "rank": self.rank}
    
    @classmethod
    def from_dict(cls, data: dict) -> "TechniqueLevel":
        return cls(name=data["name"], rank=data["rank"])


@dataclass
class Technique:
    """功法实体"""
    id: TechniqueId
    novel_id: NovelId
    name: str
    level: Optional[TechniqueLevel] = None
    description: str = ""
    effect: str = ""
    requirement: str = ""
    creator: str = ""
    techniques: List[TechniqueId] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update_level(self, level: TechniqueLevel) -> None:
        self.level = level
        self.updated_at = datetime.now()
    
    def update_description(self, description: str) -> None:
        self.description = description
        self.updated_at = datetime.now()
    
    def update_effect(self, effect: str) -> None:
        self.effect = effect
        self.updated_at = datetime.now()
    
    def update_requirement(self, requirement: str) -> None:
        self.requirement = requirement
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "name": self.name,
            "level": self.level.to_dict() if self.level else None,
            "description": self.description,
            "effect": self.effect,
            "requirement": self.requirement,
            "creator": self.creator,
            "techniques": [str(t) for t in self.techniques],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Technique":
        return cls(
            id=TechniqueId(data["id"]),
            novel_id=NovelId(data["novel_id"]),
            name=data["name"],
            level=TechniqueLevel.from_dict(data["level"]) if data.get("level") else None,
            description=data.get("description", ""),
            effect=data.get("effect", ""),
            requirement=data.get("requirement", ""),
            creator=data.get("creator", ""),
            techniques=[TechniqueId(t) for t in data.get("techniques", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
