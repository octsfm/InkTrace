"""
世界观聚合根

作者：孔利群
"""

# 文件路径：domain/entities/worldview.py


from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from domain.types import WorldviewId, NovelId
from domain.entities.technique import Technique
from domain.entities.faction import Faction
from domain.entities.location import Location
from domain.entities.item import Item


@dataclass
class PowerSystem:
    """力量体系值对象"""
    name: str
    levels: List[str] = field(default_factory=list)
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "levels": self.levels,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PowerSystem":
        return cls(
            name=data.get("name", ""),
            levels=data.get("levels", []),
            description=data.get("description", "")
        )


@dataclass
class Worldview:
    """世界观聚合根"""
# 文件：模块：worldview

    id: WorldviewId
    novel_id: NovelId
    name: str = ""
    power_system: Optional[PowerSystem] = None
    currency_system: Dict[str, Any] = field(default_factory=dict)
    timeline: Dict[str, Any] = field(default_factory=dict)
    techniques: List[Technique] = field(default_factory=list)
    factions: List[Faction] = field(default_factory=list)
    locations: List[Location] = field(default_factory=list)
    items: List[Item] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_technique(self, technique: Technique) -> None:
        self.techniques.append(technique)
        self.updated_at = datetime.now()
    
    def remove_technique(self, technique_id: str) -> None:
        self.techniques = [t for t in self.techniques if str(t.id) != technique_id]
        self.updated_at = datetime.now()
    
    def get_technique(self, technique_id: str) -> Optional[Technique]:
        for t in self.techniques:
            if str(t.id) == technique_id:
                return t
        return None
    
    def add_faction(self, faction: Faction) -> None:
        self.factions.append(faction)
        self.updated_at = datetime.now()
    
    def remove_faction(self, faction_id: str) -> None:
        self.factions = [f for f in self.factions if str(f.id) != faction_id]
        self.updated_at = datetime.now()
    
    def get_faction(self, faction_id: str) -> Optional[Faction]:
        for f in self.factions:
            if str(f.id) == faction_id:
                return f
        return None
    
    def add_location(self, location: Location) -> None:
        self.locations.append(location)
        self.updated_at = datetime.now()
    
    def remove_location(self, location_id: str) -> None:
        self.locations = [l for l in self.locations if str(l.id) != location_id]
        self.updated_at = datetime.now()
    
    def get_location(self, location_id: str) -> Optional[Location]:
        for l in self.locations:
            if str(l.id) == location_id:
                return l
        return None
    
    def add_item(self, item: Item) -> None:
        self.items.append(item)
        self.updated_at = datetime.now()
    
    def remove_item(self, item_id: str) -> None:
        self.items = [i for i in self.items if str(i.id) != item_id]
        self.updated_at = datetime.now()
    
    def get_item(self, item_id: str) -> Optional[Item]:
        for i in self.items:
            if str(i.id) == item_id:
                return i
        return None
    
    def set_power_system(self, power_system: PowerSystem) -> None:
        self.power_system = power_system
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "name": self.name,
            "power_system": self.power_system.to_dict() if self.power_system else None,
            "currency_system": self.currency_system,
            "timeline": self.timeline,
            "techniques": [t.to_dict() for t in self.techniques],
            "factions": [f.to_dict() for f in self.factions],
            "locations": [l.to_dict() for l in self.locations],
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Worldview":
        return cls(
            id=WorldviewId(data["id"]),
            novel_id=NovelId(data["novel_id"]),
            name=data.get("name", ""),
            power_system=PowerSystem.from_dict(data["power_system"]) if data.get("power_system") else None,
            currency_system=data.get("currency_system", {}),
            timeline=data.get("timeline", {}),
            techniques=[Technique.from_dict(t) for t in data.get("techniques", [])],
            factions=[Faction.from_dict(f) for f in data.get("factions", [])],
            locations=[Location.from_dict(l) for l in data.get("locations", [])],
            items=[Item.from_dict(i) for i in data.get("items", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
