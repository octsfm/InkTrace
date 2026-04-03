from __future__ import annotations

import os
from typing import Any, Dict

from application.agent_mvp.model_router import ModelRouter
from application.services.logging_service import build_log_context, get_logger
from domain.entities.model_role import ModelRole
from infrastructure.llm.llm_factory import LLMFactory


KIMI_ROLES = {
    ModelRole.GLOBAL_ANALYSIS,
    ModelRole.CHAPTER_ANALYSIS,
    ModelRole.CONTINUATION_MEMORY_EXTRACTION,
    ModelRole.PLOT_ARC_EXTRACTION,
    ModelRole.ARC_STATE_UPDATE,
    ModelRole.ARC_SELECTION,
    ModelRole.CHAPTER_PLANNING,
    ModelRole.CONSISTENCY_VALIDATION,
}


class ModelRoleRouter:
    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
        self.mode = os.getenv("INKTRACE_MODEL_ROLE_MODE", "strict").strip().lower()
        self.logger = get_logger(__name__)

    def provider_for_role(self, role: ModelRole) -> str:
        return "kimi" if role in KIMI_ROLES else "deepseek"

    def _build_router(self, provider: str) -> ModelRouter:
        client_getter = getattr(self.llm_factory, "get_client_for_provider", None)
        if callable(client_getter):
            preferred_client = client_getter(provider)
        elif provider == "kimi":
            preferred_client = getattr(self.llm_factory, "kimi_client", None)
        else:
            preferred_client = getattr(self.llm_factory, "deepseek_client", None)
        fallback_client = None
        if self.mode == "degraded":
            fallback_getter = getattr(self.llm_factory, "get_fallback_client_for_provider", None)
            if callable(fallback_getter):
                fallback_client = fallback_getter(provider)
        return ModelRouter(preferred_client, fallback_client)

    async def generate(
        self,
        role: ModelRole,
        prompt: str,
        max_tokens: int = 1600,
        temperature: float = 0.35,
    ) -> Dict[str, Any]:
        provider = self.provider_for_role(role)
        degraded_mode = self.mode == "degraded"
        self.logger.info(
            "model role dispatched",
            extra=build_log_context(
                event="model_role_dispatched",
                task_role=role.value,
                model_name=provider,
                used_fallback=False,
            ),
        )
        if degraded_mode:
            self.logger.warning(
                "model role degraded mode enabled",
                extra=build_log_context(
                    event="model_role_degraded",
                    task_role=role.value,
                    model_name=provider,
                    used_fallback=False,
                ),
            )

        result = await self._build_router(provider).generate(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        result["task_role"] = role.value
        result["provider"] = provider
        result["degraded_mode"] = degraded_mode

        if not result.get("ok"):
            self.logger.error(
                "model role failed",
                extra=build_log_context(
                    event="model_role_failed",
                    task_role=role.value,
                    model_name=provider,
                    used_fallback=bool(result.get("route") == "fallback"),
                    error=str(result.get("error") or "unknown"),
                ),
            )

        return result
