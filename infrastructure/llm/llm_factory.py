"""
大模型客户端工厂模块

作者：孔利群
"""

# 文件路径：infrastructure/llm/llm_factory.py


import asyncio
from typing import Optional
from dataclasses import dataclass

from infrastructure.llm.base_client import LLMClient
from infrastructure.llm.deepseek_client import DeepSeekClient
from infrastructure.llm.kimi_client import KimiClient


@dataclass
class LLMConfig:
    """大模型配置"""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"


class LLMFactory:
    """
    大模型客户端工厂
    
    管理主备模型切换。
    """

    def __init__(self, config: LLMConfig):
        """
        初始化工厂
        
        Args:
            config: 大模型配置（必须包含API密钥）
        """
        self.config = config
        self._primary_client: Optional[LLMClient] = None
        self._backup_client: Optional[LLMClient] = None
        self._current_client: Optional[LLMClient] = None

    @property
    def primary_client(self) -> LLMClient:
        """获取主模型客户端"""
        if self._primary_client is None:
            self._primary_client = DeepSeekClient(
                api_key=self.config.deepseek_api_key,
                base_url=self.config.deepseek_base_url,
                model=self.config.deepseek_model
            )
        return self._primary_client

    @property
    def backup_client(self) -> LLMClient:
        """获取备用模型客户端"""
        if self._backup_client is None:
            self._backup_client = KimiClient(
                api_key=self.config.kimi_api_key,
                base_url=self.config.kimi_base_url,
                model=self.config.kimi_model
            )
        return self._backup_client

    async def get_client(self) -> LLMClient:
        """
        获取可用客户端
        
        优先使用主模型，失败时切换备用模型。
        
        Returns:
            可用的LLM客户端
        """
        if self._current_client is None:
            if await self.primary_client.is_available():
                self._current_client = self.primary_client
            else:
                self._current_client = self.backup_client
        
        return self._current_client

    async def switch_to_backup(self) -> LLMClient:
        """
        切换到备用模型
        
        Returns:
            备用模型客户端
        """
        self._current_client = self.backup_client
        return self._current_client

    async def reset_to_primary(self) -> LLMClient:
        """
        重置为主模型
        
        Returns:
            主模型客户端
        """
        if await self.primary_client.is_available():
            self._current_client = self.primary_client
        return self._current_client
