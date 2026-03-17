"""
Character实体模块

作者：孔利群
"""

# 文件路径：domain/entities/character.py


from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from domain.types import CharacterId, NovelId, ChapterId, CharacterRole, FactionId, TechniqueId, RelationType
from domain.exceptions import InvalidOperationError


@dataclass(frozen=True)
class CharacterRelation:
    """
    人物关系值对象
    
    表示两个人物之间的详细关系。
    """
# 文件：模块：character

    target_id: CharacterId
    relation_type: RelationType
    description: str = ""
    start_chapter: Optional[ChapterId] = None
    
    def to_dict(self) -> dict:
        return {
            "target_id": str(self.target_id),
            "relation_type": self.relation_type.value,
            "description": self.description,
            "start_chapter": str(self.start_chapter) if self.start_chapter else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CharacterRelation":
        return cls(
            target_id=CharacterId(data["target_id"]),
            relation_type=RelationType(data["relation_type"]),
            description=data.get("description", ""),
            start_chapter=ChapterId(data["start_chapter"]) if data.get("start_chapter") else None
        )


@dataclass(frozen=True)
class CharacterRelationship:
    """
    人物关系值对象（兼容一期）
    
    表示两个人物之间的关系。
    """
# 文件：模块：character

    target_id: CharacterId
    relation_type: str
    description: str = ""


@dataclass
class Character:
    """
    人物实体
    
    表示小说中的一个人物，包含基本信息、能力、关系和状态。
    """
# 文件：模块：character

    id: CharacterId
    novel_id: NovelId
    name: str
    role: CharacterRole
    background: str = ""
    personality: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 一期属性
    aliases: List[str] = field(default_factory=list)
    abilities: List[str] = field(default_factory=list)
    relationships: List[CharacterRelationship] = field(default_factory=list)
    current_state: str = ""
    appearance_count: int = 0
    first_appearance: Optional[ChapterId] = None
    
    # 二期扩展属性
    appearance: str = ""
    techniques: List[TechniqueId] = field(default_factory=list)
    faction_id: Optional[FactionId] = None
    detailed_relations: List[CharacterRelation] = field(default_factory=list)
    state_history: List[str] = field(default_factory=list)
    age: Optional[int] = None
    gender: str = ""
    title: str = ""

    @property
    def is_protagonist(self) -> bool:
        """检查是否为主角"""
        return self.role == CharacterRole.PROTAGONIST

    def add_alias(self, alias: str, updated_at: datetime = None) -> None:
        """添加别名"""
# 文件：模块：character

        if alias not in self.aliases:
            self.aliases.append(alias)
            self.updated_at = updated_at or datetime.now()

    def add_ability(self, ability: str, updated_at: datetime = None) -> None:
        """添加能力"""
        if ability not in self.abilities:
            self.abilities.append(ability)
            self.updated_at = updated_at or datetime.now()

    def add_relationship(
        self, 
        relationship: CharacterRelationship, 
        updated_at: datetime = None
    ) -> None:
        """添加人物关系"""
# 文件：模块：character

        existing = self.get_relationship(relationship.target_id)
        if existing:
            self.relationships.remove(existing)
        self.relationships.append(relationship)
        self.updated_at = updated_at or datetime.now()

    def get_relationship(
        self, 
        target_id: CharacterId
    ) -> Optional[CharacterRelationship]:
        """获取与指定人物的关系"""
        for rel in self.relationships:
            if rel.target_id == target_id:
                return rel
        return None

    def update_state(self, new_state: str, updated_at: datetime = None) -> None:
        """更新人物状态"""
# 文件：模块：character

        if self.current_state:
            self.state_history.append(self.current_state)
        self.current_state = new_state
        self.updated_at = updated_at or datetime.now()

    def increment_appearance(
        self, 
        chapter_id: ChapterId, 
        updated_at: datetime = None
    ) -> None:
        """增加出场次数"""
        if self.first_appearance is None:
            self.first_appearance = chapter_id
        self.appearance_count += 1
        self.updated_at = updated_at or datetime.now()

    def add_technique(self, technique_id: TechniqueId, updated_at: datetime = None) -> None:
        """添加功法"""
# 文件：模块：character

        if technique_id not in self.techniques:
            self.techniques.append(technique_id)
            self.updated_at = updated_at or datetime.now()

    def remove_technique(self, technique_id: TechniqueId, updated_at: datetime = None) -> None:
        """移除功法"""
        if technique_id in self.techniques:
            self.techniques.remove(technique_id)
            self.updated_at = updated_at or datetime.now()

    def set_faction(self, faction_id: FactionId, updated_at: datetime = None) -> None:
        """设置所属势力"""
# 文件：模块：character

        self.faction_id = faction_id
        self.updated_at = updated_at or datetime.now()

    def add_detailed_relation(self, relation: CharacterRelation, updated_at: datetime = None) -> None:
        """添加详细人物关系"""
        existing = self.get_detailed_relation(relation.target_id)
        if existing:
            self.detailed_relations.remove(existing)
        self.detailed_relations.append(relation)
        self.updated_at = updated_at or datetime.now()

    def get_detailed_relation(self, target_id: CharacterId) -> Optional[CharacterRelation]:
        """获取详细人物关系"""
# 文件：模块：character

        for rel in self.detailed_relations:
            if rel.target_id == target_id:
                return rel
        return None

    def remove_detailed_relation(self, target_id: CharacterId, updated_at: datetime = None) -> None:
        """移除详细人物关系"""
        relation = self.get_detailed_relation(target_id)
        if relation:
            self.detailed_relations.remove(relation)
            self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> dict:
        """转换为字典"""
# 文件：模块：character

        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "name": self.name,
            "role": self.role.value,
            "background": self.background,
            "personality": self.personality,
            "aliases": self.aliases,
            "abilities": self.abilities,
            "relationships": [
                {"target_id": str(r.target_id), "relation_type": r.relation_type, "description": r.description}
                for r in self.relationships
            ],
            "current_state": self.current_state,
            "appearance_count": self.appearance_count,
            "first_appearance": str(self.first_appearance) if self.first_appearance else None,
            "appearance": self.appearance,
            "techniques": [str(t) for t in self.techniques],
            "faction_id": str(self.faction_id) if self.faction_id else None,
            "detailed_relations": [r.to_dict() for r in self.detailed_relations],
            "state_history": self.state_history,
            "age": self.age,
            "gender": self.gender,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        """从字典创建"""
        return cls(
            id=CharacterId(data["id"]),
            novel_id=NovelId(data["novel_id"]),
            name=data["name"],
            role=CharacterRole(data["role"]),
            background=data.get("background", ""),
            personality=data.get("personality", ""),
            aliases=data.get("aliases", []),
            abilities=data.get("abilities", []),
            relationships=[
                CharacterRelationship(
                    target_id=CharacterId(r["target_id"]),
                    relation_type=r["relation_type"],
                    description=r.get("description", "")
                ) for r in data.get("relationships", [])
            ],
            current_state=data.get("current_state", ""),
            appearance_count=data.get("appearance_count", 0),
            first_appearance=ChapterId(data["first_appearance"]) if data.get("first_appearance") else None,
            appearance=data.get("appearance", ""),
            techniques=[TechniqueId(t) for t in data.get("techniques", [])],
            faction_id=FactionId(data["faction_id"]) if data.get("faction_id") else None,
            detailed_relations=[CharacterRelation.from_dict(r) for r in data.get("detailed_relations", [])],
            state_history=data.get("state_history", []),
            age=data.get("age"),
            gender=data.get("gender", ""),
            title=data.get("title", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )
