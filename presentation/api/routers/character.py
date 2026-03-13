"""
人物管理API路由

作者：孔利群
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.services.character_service import CharacterService
from domain.entities.character import Character, CharacterRelation
from domain.types import CharacterId, NovelId, CharacterRole, RelationType


router = APIRouter(prefix="/api/novels/{novel_id}/characters", tags=["characters"])


class CreateCharacterRequest(BaseModel):
    name: str
    role: str
    background: str = ""
    personality: str = ""
    appearance: str = ""
    age: Optional[int] = None
    gender: str = ""
    title: str = ""


class UpdateCharacterRequest(BaseModel):
    name: Optional[str] = None
    background: Optional[str] = None
    personality: Optional[str] = None
    appearance: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    title: Optional[str] = None


class AddRelationRequest(BaseModel):
    target_id: str
    relation_type: str
    description: str = ""


class CharacterResponse(BaseModel):
    id: str
    novel_id: str
    name: str
    role: str
    background: str
    personality: str
    appearance: str
    age: Optional[int]
    gender: str
    title: str
    abilities: List[str]
    current_state: str
    appearance_count: int


class RelationResponse(BaseModel):
    target_id: str
    relation_type: str
    description: str


def get_character_service() -> CharacterService:
    from presentation.api.dependencies import get_character_service
    return get_character_service()


@router.post("", response_model=CharacterResponse)
def create_character(
    novel_id: str,
    request: CreateCharacterRequest,
    service: CharacterService = Depends(get_character_service)
):
    """创建人物"""
    try:
        role = CharacterRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的角色类型: {request.role}")
    
    character = service.create_character(
        novel_id=NovelId(novel_id),
        name=request.name,
        role=role,
        background=request.background,
        personality=request.personality,
        appearance=request.appearance
    )
    
    if request.age is not None:
        character.age = request.age
    if request.gender:
        character.gender = request.gender
    if request.title:
        character.title = request.title
    
    return _character_to_response(character)


@router.get("", response_model=List[CharacterResponse])
def list_characters(
    novel_id: str,
    role: Optional[str] = None,
    keyword: Optional[str] = None,
    service: CharacterService = Depends(get_character_service)
):
    """获取人物列表"""
    if keyword:
        characters = service.search_characters(NovelId(novel_id), keyword)
    elif role:
        try:
            character_role = CharacterRole(role)
            characters = service.list_characters_by_role(NovelId(novel_id), character_role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的角色类型: {role}")
    else:
        characters = service.list_characters(NovelId(novel_id))
    
    return [_character_to_response(c) for c in characters]


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(
    novel_id: str,
    character_id: str,
    service: CharacterService = Depends(get_character_service)
):
    """获取人物详情"""
    character = service.get_character(CharacterId(character_id))
    if not character:
        raise HTTPException(status_code=404, detail="人物不存在")
    return _character_to_response(character)


@router.put("/{character_id}", response_model=CharacterResponse)
def update_character(
    novel_id: str,
    character_id: str,
    request: UpdateCharacterRequest,
    service: CharacterService = Depends(get_character_service)
):
    """更新人物"""
    character = service.update_character(
        CharacterId(character_id),
        name=request.name,
        background=request.background,
        personality=request.personality,
        appearance=request.appearance,
        age=request.age,
        gender=request.gender,
        title=request.title
    )
    return _character_to_response(character)


@router.delete("/{character_id}")
def delete_character(
    novel_id: str,
    character_id: str,
    service: CharacterService = Depends(get_character_service)
):
    """删除人物"""
    service.delete_character(CharacterId(character_id))
    return {"message": "人物已删除"}


@router.post("/{character_id}/relations", response_model=RelationResponse)
def add_relation(
    novel_id: str,
    character_id: str,
    request: AddRelationRequest,
    service: CharacterService = Depends(get_character_service)
):
    """添加人物关系"""
    try:
        relation_type = RelationType(request.relation_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的关系类型: {request.relation_type}")
    
    character = service.add_character_relation(
        CharacterId(character_id),
        CharacterId(request.target_id),
        relation_type,
        request.description
    )
    
    relation = character.get_detailed_relation(CharacterId(request.target_id))
    return _relation_to_response(relation)


@router.get("/{character_id}/relations", response_model=List[RelationResponse])
def get_relations(
    novel_id: str,
    character_id: str,
    service: CharacterService = Depends(get_character_service)
):
    """获取人物关系"""
    relations = service.get_character_relations(CharacterId(character_id))
    return [_relation_to_response(r) for r in relations]


@router.delete("/{character_id}/relations/{target_id}")
def remove_relation(
    novel_id: str,
    character_id: str,
    target_id: str,
    service: CharacterService = Depends(get_character_service)
):
    """移除人物关系"""
    service.remove_character_relation(
        CharacterId(character_id),
        CharacterId(target_id)
    )
    return {"message": "关系已删除"}


@router.post("/{character_id}/state")
def update_state(
    novel_id: str,
    character_id: str,
    state: str,
    service: CharacterService = Depends(get_character_service)
):
    """更新人物状态"""
    character = service.update_character_state(CharacterId(character_id), state)
    return {"message": "状态已更新", "current_state": character.current_state}


@router.get("/{character_id}/states", response_model=List[str])
def get_state_history(
    novel_id: str,
    character_id: str,
    service: CharacterService = Depends(get_character_service)
):
    """获取人物状态历史"""
    return service.get_character_state_history(CharacterId(character_id))


def _character_to_response(character: Character) -> CharacterResponse:
    return CharacterResponse(
        id=str(character.id),
        novel_id=str(character.novel_id),
        name=character.name,
        role=character.role.value,
        background=character.background,
        personality=character.personality,
        appearance=character.appearance,
        age=character.age,
        gender=character.gender,
        title=character.title,
        abilities=character.abilities,
        current_state=character.current_state,
        appearance_count=character.appearance_count
    )


def _relation_to_response(relation: CharacterRelation) -> RelationResponse:
    return RelationResponse(
        target_id=str(relation.target_id),
        relation_type=relation.relation_type.value,
        description=relation.description
    )
