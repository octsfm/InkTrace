"""
LLM配置仓储接口模块

作者：孔利群
"""

# 文件路径：domain/repositories/llm_config_repository.py


from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.llm_config import LLMConfig


class ILLMConfigRepository(ABC):
    """LLM配置仓储接口"""
    
    @abstractmethod
    def save(self, config: LLMConfig) -> LLMConfig:
        """
# 文件：模块：llm_config_repository

        保存配置
        
        Args:
            config: 配置实体
            
        Returns:
            保存后的配置实体
        """
        pass
    
    @abstractmethod
    def get(self) -> Optional[LLMConfig]:
        """
# 文件：模块：llm_config_repository

        获取配置
        
        Returns:
            配置实体，不存在则返回None
        """
        pass
    
    @abstractmethod
    def delete(self) -> bool:
        """
# 文件：模块：llm_config_repository

        删除配置
        
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    def exists(self) -> bool:
        """
# 文件：模块：llm_config_repository

        检查配置是否存在
        
        Returns:
            是否存在配置
        """
        pass