"""
Kimi客户端模块

作者：孔利群
"""

# 文件路径：infrastructure/llm/kimi_client.py


import logging
from typing import List, Dict, Optional

import httpx

from infrastructure.llm.base_client import LLMClient
from domain.exceptions import (
    LLMClientError, 
    APIKeyError, 
    RateLimitError, 
    NetworkError,
    TokenLimitError
)


class KimiClient(LLMClient):
    """
    Kimi大模型客户端
    
    使用Kimi (Moonshot) API进行文本生成。
    支持连接复用、错误处理、系统提示和Token控制。
    """

    def __init__(
        self, 
        api_key: str, 
        base_url: str = "https://api.moonshot.cn/v1",
        model: str = "moonshot-v1-8k",
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        """
        初始化Kimi客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self._model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # 创建复用的HTTP客户端（连接池）
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )

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
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示词
            system_prompt: 系统提示（可选）
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            生成的文本
            
        Raises:
            TokenLimitError: Token超限
            APIKeyError: API密钥错误
            RateLimitError: 限流错误
            NetworkError: 网络错误
            LLMClientError: 其他LLM客户端错误
        """
        # Token控制：截断过长的输入
        prompt = self._truncate_input(prompt, max_chars=50000)
        
        # 构建消息列表
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
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
            
        Raises:
            TokenLimitError: Token超限
            APIKeyError: API密钥错误
            RateLimitError: 限流错误
            NetworkError: 网络错误
            LLMClientError: 其他LLM客户端错误
        """
        if not self.api_key:
            raise ValueError("API key is missing")

        self.logger.info(f"[Kimi] 调用大模型, model={self._model}, max_tokens={max_tokens}, temperature={temperature}")
        self.logger.info(f"[Kimi] API Key前4位: {self.api_key[:4] if len(self.api_key) >= 4 else 'N/A'}")

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

        # 重试机制
        last_error = None
        for attempt in range(self.max_retries):
            try:
                print(">>> CALLING LLM API")
                # 使用复用的HTTP客户端
                response = await self._client.post(url, json=payload, headers=headers)
                
                # 错误处理
                if response.status_code == 401:
                    raise APIKeyError("Kimi", "API密钥无效")
                elif response.status_code == 429:
                    retry_after = response.headers.get("retry-after")
                    raise RateLimitError(
                        "Kimi", 
                        retry_after=int(retry_after) if retry_after else None
                    )
                elif response.status_code >= 500:
                    raise NetworkError("Kimi", f"服务器错误: {response.status_code}")
                
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
            except APIKeyError:
                raise
            except RateLimitError:
                raise
            except httpx.TimeoutException as e:
                last_error = NetworkError("Kimi", f"请求超时: {str(e)}")
                self.logger.warning(f"Kimi请求超时，尝试{attempt + 1}/{self.max_retries}")
            except httpx.NetworkError as e:
                last_error = NetworkError("Kimi", str(e))
                self.logger.warning(f"Kimi网络错误，尝试{attempt + 1}/{self.max_retries}")
            except Exception as e:
                last_error = LLMClientError(f"Kimi API错误: {str(e)}")
                self.logger.error(f"Kimi API错误: {str(e)}")
        
        # 所有重试都失败
        raise last_error or LLMClientError("Kimi请求失败")

    def _truncate_input(self, text: str, max_chars: int = 50000) -> str:
        """
        截断输入文本以控制Token数量
        
        Args:
            text: 输入文本
            max_chars: 最大字符数
            
        Returns:
            截断后的文本
        """
        if len(text) > max_chars:
            self.logger.warning(f"输入文本过长({len(text)}字符)，截断至{max_chars}字符")
            return text[:max_chars]
        return text

    async def is_available(self) -> bool:
        """检查客户端是否可用"""
        try:
            result = await self.generate("测试", max_tokens=10)
            return len(result) > 0
        except Exception as e:
            self.logger.error(f"Kimi客户端不可用: {str(e)}")
            return False

    async def close(self):
        """关闭HTTP客户端，释放资源"""
        await self._client.aclose()
        self.logger.info("Kimi客户端已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
