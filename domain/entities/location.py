"""
地点实体

作者：孔利群
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from domain.types import LocationId, NovelId, FactionId


@dataclass
class Location:
    """地点实体"""
    id: LocationId
    novel_id: NovelId
    name: str
    description: str = ""
    parent_id: Optional[LocationId] = None
    faction_id: Optional[FactionId] = None
    children: List[LocationId] = field(default_factory=list)
    importance: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def set_parent(self, parent_id: LocationId) -> None:
        self.parent_id = parent_id
        self.updated_at = datetime.now()
    
    def set_faction(self, faction_id: FactionId) -> None:
        self.faction_id = faction_id
        self.updated_at = datetime.now()
    
    def add_child(self, child_id: LocationId) -> None:
        if child_id not in self.children:
            self.children.append(child_id)
            self.updated_at = datetime.now()
    
    def remove_child(self, child_id: LocationId) -> None:
        if child_id in self.children:
            self.children.remove(child_id)
            self.updated_at = datetime.now()
    
    def set_importance(self, importance: int) -> None:
        self.importance = max(0, importance)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "name": self.name,
            "description": self.description,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "faction_id": str(self.faction_id) if self.faction_id else None,
            "children": [str(c) for c in self.children],
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        return cls(
            id=LocationId(data["id"]),
            novel_id=NovelId(data["novel_id"]),
            name=data["name"],
            description=data.get("description", ""),
            parent_id=LocationId(data["parent_id"]) if data.get("parent_id") else None,
            faction_id=FactionId(data["faction_id"]) if data.get("faction_id") else None,
            children=[LocationId(c) for c in data.get("children", [])],
            importance=data.get("importance", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
