"""
Character实体模块

作者：孔利群
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from domain.types import CharacterId, NovelId, ChapterId, CharacterRole
from domain.exceptions import InvalidOperationError


@dataclass(frozen=True)
class CharacterRelationship:
    """
    人物关系值对象
    
    表示两个人物之间的关系。
    """
    target_id: CharacterId
    relation_type: str
    description: str = ""


@dataclass
class Character:
    """
    人物实体
    
    表示小说中的一个人物，包含基本信息、能力、关系和状态。
    """
    id: CharacterId
    novel_id: NovelId
    name: str
    role: CharacterRole
    background: str
    personality: str
    created_at: datetime
    updated_at: datetime
    aliases: List[str] = field(default_factory=list)
    abilities: List[str] = field(default_factory=list)
    relationships: List[CharacterRelationship] = field(default_factory=list)
    current_state: str = ""
    appearance_count: int = 0
    first_appearance: Optional[ChapterId] = None

    @property
    def is_protagonist(self) -> bool:
        """检查是否为主角"""
        return self.role == CharacterRole.PROTAGONIST

    def add_alias(self, alias: str, updated_at: datetime) -> None:
        """
        添加别名
        
        Args:
            alias: 别名
            updated_at: 更新时间
        """
        if alias not in self.aliases:
            self.aliases.append(alias)
            self.updated_at = updated_at

    def add_ability(self, ability: str, updated_at: datetime) -> None:
        """
        添加能力
        
        Args:
            ability: 能力名称
            updated_at: 更新时间
        """
        if ability not in self.abilities:
            self.abilities.append(ability)
            self.updated_at = updated_at

    def add_relationship(
        self, 
        relationship: CharacterRelationship, 
        updated_at: datetime
    ) -> None:
        """
        添加人物关系
        
        Args:
            relationship: 人物关系
            updated_at: 更新时间
        """
        existing = self.get_relationship(relationship.target_id)
        if existing:
            self.relationships.remove(existing)
        self.relationships.append(relationship)
        self.updated_at = updated_at

    def get_relationship(
        self, 
        target_id: CharacterId
    ) -> Optional[CharacterRelationship]:
        """
        获取与指定人物的关系
        
        Args:
            target_id: 目标人物ID
            
        Returns:
            人物关系，不存在则返回None
        """
        for rel in self.relationships:
            if rel.target_id == target_id:
                return rel
        return None

    def update_state(self, new_state: str, updated_at: datetime) -> None:
        """
        更新人物状态
        
        Args:
            new_state: 新状态
            updated_at: 更新时间
        """
        self.current_state = new_state
        self.updated_at = updated_at

    def increment_appearance(
        self, 
        chapter_id: ChapterId, 
        updated_at: datetime
    ) -> None:
        """
        增加出场次数
        
        Args:
            chapter_id: 出场章节ID
            updated_at: 更新时间
        """
        if self.first_appearance is None:
            self.first_appearance = chapter_id
        self.appearance_count += 1
        self.updated_at = updated_at
