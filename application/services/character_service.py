"""
人物管理服务

作者：孔利群
"""

# 文件路径：application/services/character_service.py


from typing import Optional, List
import uuid

from domain.entities.character import Character, CharacterRelation, CharacterRelationship
from domain.repositories.character_repository import ICharacterRepository
from domain.types import CharacterId, NovelId, CharacterRole, RelationType, ChapterId


class CharacterService:
    """人物管理服务"""
    
    def __init__(self, character_repo: ICharacterRepository):
        self.character_repo = character_repo
    
    def create_character(
        self,
        novel_id: NovelId,
        name: str,
        role: CharacterRole,
        background: str = "",
        personality: str = "",
        appearance: str = ""
    ) -> Character:
        """创建人物"""
# 文件：模块：character_service

        character = Character(
            id=CharacterId(str(uuid.uuid4())),
            novel_id=novel_id,
            name=name,
            role=role,
            background=background,
            personality=personality,
            appearance=appearance
        )
        self.character_repo.save(character)
        return character
    
    def get_character(self, character_id: CharacterId) -> Optional[Character]:
        """获取人物"""
        return self.character_repo.find_by_id(character_id)
    
    def list_characters(self, novel_id: NovelId) -> List[Character]:
        """获取小说的所有人物"""
# 文件：模块：character_service

        return self.character_repo.find_by_novel_id(novel_id)
    
    def list_characters_by_role(
        self,
        novel_id: NovelId,
        role: CharacterRole
    ) -> List[Character]:
        """根据角色类型获取人物"""
        characters = self.character_repo.find_by_novel_id(novel_id)
        return [c for c in characters if c.role == role]
    
    def update_character(
        self,
        character_id: CharacterId,
        name: Optional[str] = None,
        background: Optional[str] = None,
        personality: Optional[str] = None,
        appearance: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        title: Optional[str] = None
    ) -> Character:
        """更新人物信息"""
# 文件：模块：character_service

        character = self.character_repo.find_by_id(character_id)
        if not character:
            raise ValueError(f"人物不存在: {character_id}")
        
        if name is not None:
            character.name = name
        if background is not None:
            character.background = background
        if personality is not None:
            character.personality = personality
        if appearance is not None:
            character.appearance = appearance
        if age is not None:
            character.age = age
        if gender is not None:
            character.gender = gender
        if title is not None:
            character.title = title
        
        character.updated_at = character.updated_at.__class__.now()
        self.character_repo.save(character)
        return character
    
    def delete_character(self, character_id: CharacterId) -> None:
        """删除人物"""
        self.character_repo.delete(character_id)
    
    def add_character_relation(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
        relation_type: RelationType,
        description: str = ""
    ) -> Character:
        """添加人物关系"""
# 文件：模块：character_service

        character = self.character_repo.find_by_id(character_id)
        if not character:
            raise ValueError(f"人物不存在: {character_id}")
        
        relation = CharacterRelation(
            target_id=target_id,
            relation_type=relation_type,
            description=description
        )
        character.add_detailed_relation(relation)
        self.character_repo.save(character)
        return character
    
    def remove_character_relation(
        self,
        character_id: CharacterId,
        target_id: CharacterId
    ) -> Character:
        """移除人物关系"""
        character = self.character_repo.find_by_id(character_id)
        if not character:
            raise ValueError(f"人物不存在: {character_id}")
        
        character.remove_detailed_relation(target_id)
        self.character_repo.save(character)
        return character
    
    def get_character_relations(
        self,
        character_id: CharacterId
    ) -> List[CharacterRelation]:
        """获取人物的所有关系"""
# 文件：模块：character_service

        character = self.character_repo.find_by_id(character_id)
        if not character:
            raise ValueError(f"人物不存在: {character_id}")
        return character.detailed_relations
    
    def update_character_state(
        self,
        character_id: CharacterId,
        new_state: str
    ) -> Character:
        """更新人物状态"""
        character = self.character_repo.find_by_id(character_id)
        if not character:
            raise ValueError(f"人物不存在: {character_id}")
        
        character.update_state(new_state)
        self.character_repo.save(character)
        return character
    
    def get_character_state_history(
        self,
        character_id: CharacterId
    ) -> List[str]:
        """获取人物状态历史"""
# 文件：模块：character_service

        character = self.character_repo.find_by_id(character_id)
        if not character:
            raise ValueError(f"人物不存在: {character_id}")
        return character.state_history
    
    def add_character_ability(
        self,
        character_id: CharacterId,
        ability: str
    ) -> Character:
        """添加人物能力"""
        character = self.character_repo.find_by_id(character_id)
        if not character:
            raise ValueError(f"人物不存在: {character_id}")
        
        character.add_ability(ability)
        self.character_repo.save(character)
        return character
    
    def search_characters(
        self,
        novel_id: NovelId,
        keyword: str
    ) -> List[Character]:
        """搜索人物"""
# 文件：模块：character_service

        characters = self.character_repo.find_by_novel_id(novel_id)
        keyword_lower = keyword.lower()
        return [
            c for c in characters
            if keyword_lower in c.name.lower()
            or keyword_lower in c.background.lower()
            or keyword_lower in c.personality.lower()
        ]
