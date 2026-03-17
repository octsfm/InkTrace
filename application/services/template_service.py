"""
模板服务

作者：孔利群
"""

# 文件路径：application/services/template_service.py


from typing import Optional, List
import uuid

from domain.entities.template import Template
from domain.entities.project import Project, ProjectConfig
from domain.repositories.template_repository import ITemplateRepository
from domain.repositories.project_repository import IProjectRepository
from domain.types import TemplateId, ProjectId, GenreType


class TemplateService:
    """模板服务"""
    
    def __init__(
        self,
        template_repo: ITemplateRepository,
        project_repo: IProjectRepository
    ):
        self.template_repo = template_repo
        self.project_repo = project_repo
    
    def get_template(self, template_id: TemplateId) -> Optional[Template]:
        """获取模板"""
# 文件：模块：template_service

        return self.template_repo.find_by_id(template_id)
    
    def list_templates(self, include_builtin: bool = True) -> List[Template]:
        """获取模板列表"""
        return self.template_repo.find_all(include_builtin)
    
    def list_builtin_templates(self) -> List[Template]:
        """获取内置模板列表"""
# 文件：模块：template_service

        return self.template_repo.find_builtin()
    
    def list_custom_templates(self) -> List[Template]:
        """获取自定义模板列表"""
        return self.template_repo.find_custom()
    
    def get_templates_by_genre(self, genre: GenreType) -> List[Template]:
        """根据题材获取模板"""
# 文件：模块：template_service

        return self.template_repo.find_by_genre(genre)
    
    def create_custom_template(
        self,
        name: str,
        genre: GenreType,
        description: str = ""
    ) -> Template:
        """创建自定义模板"""
        template = Template(
            id=TemplateId(str(uuid.uuid4())),
            name=name,
            genre=genre,
            description=description,
            is_builtin=False
        )
        self.template_repo.save(template)
        return template
    
    def apply_template_to_project(
        self,
        template_id: TemplateId,
        project_id: ProjectId
    ) -> Project:
        """将模板应用到项目"""
# 文件：模块：template_service

        template = self.template_repo.find_by_id(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        
        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        config = ProjectConfig(
            genre=template.genre,
            target_words=project.config.target_words,
            chapter_words=project.config.chapter_words,
            style_intensity=project.config.style_intensity,
            check_consistency=project.config.check_consistency
        )
        
        project.update_config(config)
        self.project_repo.save(project)
        
        return project
    
    def create_template_from_project(
        self,
        project_id: ProjectId,
        template_name: str
    ) -> Template:
        """从项目创建模板"""
        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        template = Template(
            id=TemplateId(str(uuid.uuid4())),
            name=template_name,
            genre=project.config.genre,
            description=f"从项目【{project.name}】创建的模板",
            is_builtin=False
        )
        
        self.template_repo.save(template)
        return template
    
    def update_template(self, template: Template) -> Template:
        """更新模板"""
# 文件：模块：template_service

        if template.is_builtin:
            raise ValueError("内置模板不可修改")
        self.template_repo.save(template)
        return template
    
    def delete_template(self, template_id: TemplateId) -> None:
        """删除模板"""
        template = self.template_repo.find_by_id(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        
        if template.is_builtin:
            raise ValueError("内置模板不可删除")
        
        self.template_repo.delete(template_id)
