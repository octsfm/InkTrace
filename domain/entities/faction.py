"""
势力实体

作者：孔利群
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from domain.types import FactionId, NovelId, LocationId


@dataclass(frozen=True)
class FactionRelation:
    """势力关系值对象"""
    target_id: FactionId
    relation_type: str
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "target_id": str(self.target_id),
            "relation_type": self.relation_type,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FactionRelation":
        return cls(
            target_id=FactionId(data["target_id"]),
            relation_type=data["relation_type"],
            description=data.get("description", "")
        )


@dataclass
class Faction:
    """势力实体"""
    id: FactionId
    novel_id: NovelId
    name: str
    level: str = ""
    description: str = ""
    territory: str = ""
    leader: str = ""
    headquarters: Optional[LocationId] = None
    relations: List[FactionRelation] = field(default_factory=list)
    members_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_relation(self, relation: FactionRelation) -> None:
        existing = self.get_relation(relation.target_id)
        if existing:
            self.relations.remove(existing)
        self.relations.append(relation)
        self.updated_at = datetime.now()
    
    def get_relation(self, target_id: FactionId) -> Optional[FactionRelation]:
        for rel in self.relations:
            if rel.target_id == target_id:
                return rel
        return None
    
    def remove_relation(self, target_id: FactionId) -> None:
        relation = self.get_relation(target_id)
        if relation:
            self.relations.remove(relation)
            self.updated_at = datetime.now()
    
    def set_headquarters(self, location_id: LocationId) -> None:
        self.headquarters = location_id
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "name": self.name,
            "level": self.level,
            "description": self.description,
            "territory": self.territory,
            "leader": self.leader,
            "headquarters": str(self.headquarters) if self.headquarters else None,
            "relations": [r.to_dict() for r in self.relations],
            "members_count": self.members_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Faction":
        return cls(
            id=FactionId(data["id"]),
            novel_id=NovelId(data["novel_id"]),
            name=data["name"],
            level=data.get("level", ""),
            description=data.get("description", ""),
            territory=data.get("territory", ""),
            leader=data.get("leader", ""),
            headquarters=LocationId(data["headquarters"]) if data.get("headquarters") else None,
            relations=[FactionRelation.from_dict(r) for r in data.get("relations", [])],
            members_count=data.get("members_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
