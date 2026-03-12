"""
大模型客户端接口模块

作者：孔利群
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class LLMClient(ABC):
    """
    大模型客户端接口
    
    定义与大模型交互的标准接口。
    """

    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            生成的文本
        """
        pass

    @abstractmethod
    async def chat(
        self, 
        messages: List[Dict], 
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> str:
        """
        对话生成
        
        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            生成的回复
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型名称"""
        pass

    @property
    @abstractmethod
    def max_context_tokens(self) -> int:
        """最大上下文token数"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """检查客户端是否可用"""
        pass
