from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from infrastructure.llm.base_client import LLMClient
from infrastructure.llm.deepseek_client import DeepSeekClient
from infrastructure.llm.kimi_client import KimiClient


@dataclass
class LLMConfig:
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_fallback_base_url: str = "https://api.deepseek.com/v1"
    deepseek_fallback_model: str = ""
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"
    kimi_fallback_base_url: str = "https://api.moonshot.cn/v1"
    kimi_fallback_model: str = ""


class LLMFactory:
    """
    Factory for provider-specific LLM clients.

    The new role-routing flow should use explicit provider names
    (`deepseek_client` / `kimi_client`) instead of primary/backup semantics.
    The legacy aliases remain for compatibility while the rest of the codebase
    is being migrated.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._deepseek_client: Optional[LLMClient] = None
        self._kimi_client: Optional[LLMClient] = None
        self._deepseek_fallback_client: Optional[LLMClient] = None
        self._kimi_fallback_client: Optional[LLMClient] = None
        self._legacy_current_client: Optional[LLMClient] = None

    @property
    def deepseek_client(self) -> LLMClient:
        if self._deepseek_client is None:
            self._deepseek_client = DeepSeekClient(
                api_key=self.config.deepseek_api_key,
                base_url=self.config.deepseek_base_url,
                model=self.config.deepseek_model,
            )
        return self._deepseek_client

    @property
    def kimi_client(self) -> LLMClient:
        if self._kimi_client is None:
            self._kimi_client = KimiClient(
                api_key=self.config.kimi_api_key,
                base_url=self.config.kimi_base_url,
                model=self.config.kimi_model,
            )
        return self._kimi_client

    @property
    def primary_client(self) -> LLMClient:
        return self.deepseek_client

    @property
    def backup_client(self) -> LLMClient:
        return self.kimi_client

    def get_client_for_provider(self, provider: str) -> LLMClient:
        normalized = str(provider or "").strip().lower()
        if normalized == "deepseek":
            return self.deepseek_client
        if normalized == "kimi":
            return self.kimi_client
        raise ValueError(f"Unsupported LLM provider: {provider}")

    def get_fallback_client_for_provider(self, provider: str) -> Optional[LLMClient]:
        """
        Reserved for provider-internal degraded mode.

        Hard rule: do not cross from Kimi duties to DeepSeek or vice versa.
        """
        normalized = str(provider or "").strip().lower()
        if normalized == "deepseek":
            fallback_model = str(self.config.deepseek_fallback_model or "").strip()
            if not fallback_model or fallback_model == self.config.deepseek_model:
                return None
            if self._deepseek_fallback_client is None:
                self._deepseek_fallback_client = DeepSeekClient(
                    api_key=self.config.deepseek_api_key,
                    base_url=self.config.deepseek_fallback_base_url or self.config.deepseek_base_url,
                    model=fallback_model,
                )
            return self._deepseek_fallback_client
        if normalized == "kimi":
            fallback_model = str(self.config.kimi_fallback_model or "").strip()
            if not fallback_model or fallback_model == self.config.kimi_model:
                return None
            if self._kimi_fallback_client is None:
                self._kimi_fallback_client = KimiClient(
                    api_key=self.config.kimi_api_key,
                    base_url=self.config.kimi_fallback_base_url or self.config.kimi_base_url,
                    model=fallback_model,
                )
            return self._kimi_fallback_client
        return None

    async def get_client(self) -> LLMClient:
        if self._legacy_current_client is None:
            if await self.deepseek_client.is_available():
                self._legacy_current_client = self.deepseek_client
            else:
                self._legacy_current_client = self.kimi_client
        return self._legacy_current_client

    async def switch_to_backup(self) -> LLMClient:
        self._legacy_current_client = self.kimi_client
        return self._legacy_current_client

    async def reset_to_primary(self) -> LLMClient:
        if await self.deepseek_client.is_available():
            self._legacy_current_client = self.deepseek_client
        return self._legacy_current_client
