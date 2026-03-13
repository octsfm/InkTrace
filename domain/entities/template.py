"""
模板实体

作者：孔利群
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from domain.types import TemplateId, GenreType


@dataclass
class CharacterTemplate:
    """人物模板值对象"""
    role: str
    name_pattern: str
    traits: List[str] = field(default_factory=list)
    background_template: str = ""
    abilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "name_pattern": self.name_pattern,
            "traits": self.traits,
            "background_template": self.background_template,
            "abilities": self.abilities
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CharacterTemplate":
        return cls(
            role=data.get("role", ""),
            name_pattern=data.get("name_pattern", ""),
            traits=data.get("traits", []),
            background_template=data.get("background_template", ""),
            abilities=data.get("abilities", [])
        )


@dataclass
class PlotTemplate:
    """剧情模板值对象"""
    name: str
    description: str
    stages: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "stages": self.stages,
            "key_events": self.key_events
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlotTemplate":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            stages=data.get("stages", []),
            key_events=data.get("key_events", [])
        )


@dataclass
class Template:
    """模板实体"""
    id: TemplateId
    name: str
    genre: GenreType
    description: str = ""
    worldview_framework: Dict[str, Any] = field(default_factory=dict)
    character_templates: List[CharacterTemplate] = field(default_factory=list)
    plot_templates: List[PlotTemplate] = field(default_factory=list)
    style_reference: Dict[str, Any] = field(default_factory=dict)
    is_builtin: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_character_template(self, template: CharacterTemplate) -> None:
        self.character_templates.append(template)
        self.updated_at = datetime.now()
    
    def add_plot_template(self, template: PlotTemplate) -> None:
        self.plot_templates.append(template)
        self.updated_at = datetime.now()
    
    def update_worldview_framework(self, framework: Dict[str, Any]) -> None:
        self.worldview_framework = framework
        self.updated_at = datetime.now()
    
    def update_style_reference(self, style: Dict[str, Any]) -> None:
        self.style_reference = style
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "genre": self.genre.value,
            "description": self.description,
            "worldview_framework": self.worldview_framework,
            "character_templates": [t.to_dict() for t in self.character_templates],
            "plot_templates": [t.to_dict() for t in self.plot_templates],
            "style_reference": self.style_reference,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Template":
        return cls(
            id=TemplateId(data["id"]),
            name=data["name"],
            genre=GenreType(data["genre"]),
            description=data.get("description", ""),
            worldview_framework=data.get("worldview_framework", {}),
            character_templates=[CharacterTemplate.from_dict(t) for t in data.get("character_templates", [])],
            plot_templates=[PlotTemplate.from_dict(t) for t in data.get("plot_templates", [])],
            style_reference=data.get("style_reference", {}),
            is_builtin=data.get("is_builtin", False),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
