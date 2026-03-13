"""
模板API路由

作者：孔利群
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.services.template_service import TemplateService
from domain.entities.template import Template
from domain.types import TemplateId, ProjectId, GenreType


router = APIRouter(prefix="/api/templates", tags=["templates"])


class CreateTemplateRequest(BaseModel):
    name: str
    genre: str
    description: str = ""


class TemplateResponse(BaseModel):
    id: str
    name: str
    genre: str
    description: str
    is_builtin: bool


class TemplateDetailResponse(BaseModel):
    id: str
    name: str
    genre: str
    description: str
    worldview_framework: dict
    character_templates: list
    plot_templates: list
    style_reference: dict
    is_builtin: bool


def get_template_service() -> TemplateService:
    from presentation.api.dependencies import get_template_service
    return get_template_service()


@router.get("", response_model=List[TemplateResponse])
def list_templates(
    include_builtin: bool = True,
    service: TemplateService = Depends(get_template_service)
):
    """获取模板列表"""
    templates = service.list_templates(include_builtin)
    return [_template_to_response(t) for t in templates]


@router.get("/builtin", response_model=List[TemplateResponse])
def list_builtin_templates(service: TemplateService = Depends(get_template_service)):
    """获取内置模板列表"""
    templates = service.list_builtin_templates()
    return [_template_to_response(t) for t in templates]


@router.get("/custom", response_model=List[TemplateResponse])
def list_custom_templates(service: TemplateService = Depends(get_template_service)):
    """获取自定义模板列表"""
    templates = service.list_custom_templates()
    return [_template_to_response(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(template_id: str, service: TemplateService = Depends(get_template_service)):
    """获取模板详情"""
    template = service.get_template(TemplateId(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return _template_to_detail_response(template)


@router.post("", response_model=TemplateResponse)
def create_template(
    request: CreateTemplateRequest,
    service: TemplateService = Depends(get_template_service)
):
    """创建自定义模板"""
    try:
        genre = GenreType(request.genre)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的题材类型: {request.genre}")
    
    template = service.create_custom_template(
        name=request.name,
        genre=genre,
        description=request.description
    )
    return _template_to_response(template)


@router.post("/{template_id}/apply/{project_id}")
def apply_template(
    template_id: str,
    project_id: str,
    service: TemplateService = Depends(get_template_service)
):
    """将模板应用到项目"""
    try:
        project = service.apply_template_to_project(
            TemplateId(template_id),
            ProjectId(project_id)
        )
        return {"message": "模板应用成功", "project_id": str(project.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}")
def delete_template(template_id: str, service: TemplateService = Depends(get_template_service)):
    """删除模板"""
    try:
        service.delete_template(TemplateId(template_id))
        return {"message": "模板已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _template_to_response(template: Template) -> TemplateResponse:
    return TemplateResponse(
        id=str(template.id),
        name=template.name,
        genre=template.genre.value,
        description=template.description,
        is_builtin=template.is_builtin
    )


def _template_to_detail_response(template: Template) -> TemplateDetailResponse:
    return TemplateDetailResponse(
        id=str(template.id),
        name=template.name,
        genre=template.genre.value,
        description=template.description,
        worldview_framework=template.worldview_framework,
        character_templates=[t.to_dict() for t in template.character_templates],
        plot_templates=[t.to_dict() for t in template.plot_templates],
        style_reference=template.style_reference,
        is_builtin=template.is_builtin
    )
