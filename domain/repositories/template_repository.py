"""
模板仓储接口

作者：孔利群
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities.template import Template
from domain.types import TemplateId, GenreType


class ITemplateRepository(ABC):
    """模板仓储接口"""
    
    @abstractmethod
    def find_by_id(self, template_id: TemplateId) -> Optional[Template]:
        """根据ID查找模板"""
        pass
    
    @abstractmethod
    def find_by_genre(self, genre: GenreType) -> List[Template]:
        """根据题材查找模板"""
        pass
    
    @abstractmethod
    def find_all(self, include_builtin: bool = True) -> List[Template]:
        """查找所有模板"""
        pass
    
    @abstractmethod
    def find_builtin(self) -> List[Template]:
        """查找内置模板"""
        pass
    
    @abstractmethod
    def find_custom(self) -> List[Template]:
        """查找自定义模板"""
        pass
    
    @abstractmethod
    def save(self, template: Template) -> None:
        """保存模板"""
        pass
    
    @abstractmethod
    def delete(self, template_id: TemplateId) -> None:
        """删除模板"""
        pass
