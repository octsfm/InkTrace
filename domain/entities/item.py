# 文件：模块：item
"""
物品实体

作者：孔利群
"""

# 文件路径：domain/entities/item.py


from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from domain.types import ItemId, NovelId, ItemType


@dataclass
class Item:
    """物品实体"""
    id: ItemId
    novel_id: NovelId
    name: str
    item_type: ItemType = ItemType.OTHER
    description: str = ""
    effect: str = ""
    rarity: str = ""
    owner: str = ""
    origin: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update_type(self, item_type: ItemType) -> None:
        self.item_type = item_type
        self.updated_at = datetime.now()
    
    def update_description(self, description: str) -> None:
        self.description = description
        self.updated_at = datetime.now()
    
    def update_effect(self, effect: str) -> None:
        self.effect = effect
        self.updated_at = datetime.now()
    
    def set_owner(self, owner: str) -> None:
        self.owner = owner
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "name": self.name,
            "item_type": self.item_type.value,
            "description": self.description,
            "effect": self.effect,
            "rarity": self.rarity,
            "owner": self.owner,
            "origin": self.origin,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        return cls(
            id=ItemId(data["id"]),
            novel_id=NovelId(data["novel_id"]),
            name=data["name"],
            item_type=ItemType(data.get("item_type", "other")),
            description=data.get("description", ""),
            effect=data.get("effect", ""),
            rarity=data.get("rarity", ""),
            owner=data.get("owner", ""),
            origin=data.get("origin", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
