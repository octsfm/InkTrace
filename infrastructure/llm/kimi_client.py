"""
Kimi客户端模块

作者：孔利群
"""

# 文件路径：infrastructure/llm/kimi_client.py


import asyncio
import logging
import re
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

        total_chars = sum(len(str(item.get("content", "") or "")) for item in messages or [])
        self.logger.info(f"[Kimi] 请求消息数={len(messages or [])}, 总字符数={total_chars}")
        self.validate_request_budget(messages=messages, max_tokens=max_tokens, stage="chat")

        # 重试机制
        last_error = None
        for attempt in range(self.max_retries):
            try:
                print(">>> CALLING LLM API")
                # 使用复用的HTTP客户端
                response = await self._client.post(url, json=payload, headers=headers)
                
                # 错误处理
                if response.status_code == 400:
                    error_body = self._extract_error_body(response)
                    self.logger.error(f"Kimi API 400 响应: {error_body}")
                    if "context" in error_body.lower() or "token" in error_body.lower():
                        current_tokens, max_context_tokens = self._parse_token_limit(error_body)
                        raise TokenLimitError(
                            "Kimi",
                            current_tokens=current_tokens,
                            max_tokens=max_context_tokens or self.max_context_tokens,
                            stage="chat",
                            model_name=self._model,
                            request_id=str(response.headers.get("x-request-id") or response.headers.get("x-req-id") or ""),
                            message=f"请求超过上下文限制: {error_body}",
                        )
                    raise LLMClientError(f"Kimi API 请求无效: {error_body}")
                if response.status_code == 401:
                    raise APIKeyError("Kimi", "API密钥无效")
                elif response.status_code == 429:
                    retry_after = self._parse_retry_after_seconds(response.headers.get("retry-after"))
                    last_error = RateLimitError("Kimi", retry_after=retry_after)
                    if attempt < self.max_retries - 1:
                        backoff_seconds = self._compute_backoff_seconds(attempt, retry_after)
                        self.logger.warning(
                            "Kimi触发429限流，%s秒后进行第%s次重试",
                            backoff_seconds,
                            attempt + 2,
                        )
                        await asyncio.sleep(backoff_seconds)
                        continue
                    raise last_error
                elif response.status_code >= 500:
                    raise NetworkError("Kimi", f"服务器错误: {response.status_code}")
                
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
            except APIKeyError:
                raise
            except RateLimitError as error:
                last_error = error
                if attempt < self.max_retries - 1:
                    backoff_seconds = self._compute_backoff_seconds(attempt, error.retry_after)
                    self.logger.warning(
                        "Kimi限流异常，%s秒后进行第%s次重试",
                        backoff_seconds,
                        attempt + 2,
                    )
                    await asyncio.sleep(backoff_seconds)
                    continue
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

    def _parse_retry_after_seconds(self, retry_after: Optional[str]) -> Optional[int]:
        value = str(retry_after or "").strip()
        if not value:
            return None
        direct = re.match(r"^\d+$", value)
        if direct:
            return max(0, int(value))
        numeric = re.search(r"\d+", value)
        if numeric:
            return max(0, int(numeric.group(0)))
        return None

    def _compute_backoff_seconds(self, attempt: int, retry_after: Optional[int]) -> int:
        if isinstance(retry_after, int) and retry_after > 0:
            return min(retry_after, 30)
        return min(2 ** max(0, attempt), 16)

    def _extract_error_body(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error_obj = payload.get("error")
                if isinstance(error_obj, dict):
                    message = error_obj.get("message") or error_obj.get("type") or error_obj.get("code")
                    if message:
                        return str(message)
                message = payload.get("message") or payload.get("detail")
                if message:
                    return str(message)
            return str(payload)
        except Exception:
            return (response.text or "").strip()[:500]

    def estimate_request_tokens(self, messages: List[Dict], max_tokens: int = 0) -> Dict[str, int]:
        text_chars = sum(len(str(item.get("content", "") or "")) for item in (messages or []))
        # 粗略估算：中文/英文混合场景按约 3 字符 ≈ 1 token，再加消息结构开销。
        input_tokens = int(text_chars / 3) + max(32, len(messages or []) * 12)
        output_tokens = max(0, int(max_tokens or 0))
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "max_context_tokens": int(self.max_context_tokens),
        }

    def validate_request_budget(
        self,
        *,
        messages: List[Dict],
        max_tokens: int,
        stage: str = "chat",
        request_id: str = "",
    ) -> Dict[str, int]:
        estimate = self.estimate_request_tokens(messages=messages, max_tokens=max_tokens)
        max_context = int(estimate["max_context_tokens"])
        reserve_tokens = max(256, int(max_context * 0.06))
        safe_cap = max(512, max_context - reserve_tokens)
        estimated_total = int(estimate["total_tokens"])
        if estimated_total > safe_cap:
            raise TokenLimitError(
                "Kimi",
                current_tokens=estimated_total,
                max_tokens=safe_cap,
                stage=stage,
                model_name=self._model,
                request_id=request_id,
                message=(
                    f"请求前预算拦截: estimated_total={estimated_total}, "
                    f"safe_cap={safe_cap}, reserve={reserve_tokens}"
                ),
            )
        return {
            **estimate,
            "reserve_tokens": reserve_tokens,
            "safe_cap_tokens": safe_cap,
        }

    def _parse_token_limit(self, message: str) -> tuple[Optional[int], Optional[int]]:
        text = str(message or "")
        pair = re.search(r"(\d+)\s*/\s*(\d+)", text)
        if pair:
            return int(pair.group(1)), int(pair.group(2))
        cn_pair = re.search(r"当前\s*(\d+)\s*(?:tokens?|token)?\s*[，, ]+\s*最大\s*(\d+)", text)
        if cn_pair:
            return int(cn_pair.group(1)), int(cn_pair.group(2))
        requested = re.search(r"requested[^0-9]*(\d+)", text, re.IGNORECASE)
        max_ctx = re.search(r"(?:max(?:imum)?\s*(?:context|length)?|limit)[^0-9]*(\d+)", text, re.IGNORECASE)
        return (int(requested.group(1)) if requested else None, int(max_ctx.group(1)) if max_ctx else None)

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
