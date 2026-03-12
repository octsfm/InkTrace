"""
Kimi客户端模块

作者：孔利群
"""

from typing import List, Dict

from infrastructure.llm.base_client import LLMClient


class KimiClient(LLMClient):
    """
    Kimi大模型客户端
    
    使用Kimi (Moonshot) API进行文本生成。
    """

    def __init__(
        self, 
        api_key: str, 
        base_url: str = "https://api.moonshot.cn/v1",
        model: str = "moonshot-v1-8k"
    ):
        """
        初始化Kimi客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self._model = model

    @property
    def model_name(self) -> str:
        """模型名称"""
        return self._model

    @property
    def max_context_tokens(self) -> int:
        """最大上下文token数"""
        if "128k" in self._model:
            return 131072
        elif "32k" in self._model:
            return 32768
        elif "8k" in self._model:
            return 8192
        return 8192

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
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, max_tokens, temperature)

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
        try:
            import httpx
        except ImportError:
            raise ImportError("请安装httpx: pip install httpx")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        """检查客户端是否可用"""
        try:
            result = await self.generate("测试", max_tokens=10)
            return len(result) > 0
        except Exception:
            return False
