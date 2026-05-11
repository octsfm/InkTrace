from __future__ import annotations

from datetime import UTC, datetime

from application.services.ai.model_router import ModelRouter
from application.services.ai.security import SettingsCipher
from domain.entities.ai.models import (
    AIProviderConfig,
    AIProviderTestStatus,
    AISettings,
    ModelSelection,
    build_default_model_role_mappings,
)
from domain.repositories.ai.ai_settings_repository import AISettingsRepository


class AISettingsService:
    def __init__(
        self,
        settings_repository: AISettingsRepository,
        model_router: ModelRouter,
        settings_cipher: SettingsCipher,
    ) -> None:
        self._settings_repository = settings_repository
        self._model_router = model_router
        self._settings_cipher = settings_cipher

    def get_public_settings(self) -> dict[str, object]:
        settings = self._settings_repository.load()
        merged_mappings = build_default_model_role_mappings()
        merged_mappings.update(settings.model_role_mappings)
        return {
            "provider_configs": [self._serialize_provider_config(config) for _, config in sorted(settings.provider_configs.items())],
            "model_role_mappings": {
                role: selection.model_dump(mode="json") for role, selection in sorted(merged_mappings.items())
            },
        }

    def update_settings(
        self,
        provider_configs: list[dict[str, object]],
        model_role_mappings: dict[str, dict[str, str]],
    ) -> dict[str, object]:
        current = self._settings_repository.load()
        updated_provider_configs = dict(current.provider_configs)
        for payload in provider_configs:
            provider_name = str(payload["provider_name"])
            existing = updated_provider_configs.get(provider_name)
            encrypted_api_key = existing.encrypted_api_key if existing else ""
            api_key = str(payload.get("api_key") or "")
            if api_key:
                encrypted_api_key = self._settings_cipher.encrypt(api_key)
            updated_provider_configs[provider_name] = AIProviderConfig(
                provider_name=provider_name,
                enabled=bool(payload.get("enabled", True)),
                encrypted_api_key=encrypted_api_key,
                default_model=str(payload.get("default_model") or (existing.default_model if existing else "")),
                timeout=int(payload.get("timeout") or (existing.timeout if existing else 30)),
                base_url=str(payload.get("base_url") or (existing.base_url if existing and existing.base_url else "")) or None,
                last_test_status=existing.last_test_status if existing else AIProviderTestStatus.NOT_TESTED,
                last_test_at=existing.last_test_at if existing else "",
                last_test_error_code=existing.last_test_error_code if existing else "",
                last_test_error_message=existing.last_test_error_message if existing else "",
            )

        merged_model_role_mappings = dict(current.model_role_mappings)
        for role, payload in model_role_mappings.items():
            merged_model_role_mappings[str(role)] = ModelSelection(
                provider_name=str(payload["provider_name"]),
                model_name=str(payload["model_name"]),
            )

        saved = self._settings_repository.save(
            AISettings(
                provider_configs=updated_provider_configs,
                model_role_mappings=merged_model_role_mappings,
            )
        )
        return {
            "provider_configs": [self._serialize_provider_config(config) for _, config in sorted(saved.provider_configs.items())],
            "model_role_mappings": {
                role: selection.model_dump(mode="json") for role, selection in sorted(saved.model_role_mappings.items())
            },
        }

    def test_provider_connection(self, provider_name: str, model_name: str = "") -> dict[str, str]:
        settings = self._settings_repository.load()
        config = settings.provider_configs.get(provider_name)
        if config is None:
            raise ValueError("provider_config_missing")
        try:
            result = self._model_router.test_connection(provider_name=provider_name, model_name=model_name)
            config = config.model_copy(
                update={
                    "last_test_status": AIProviderTestStatus.OK,
                    "last_test_at": datetime.now(UTC).isoformat(),
                    "last_test_error_code": "",
                    "last_test_error_message": "",
                }
            )
            settings.provider_configs[provider_name] = config
            self._settings_repository.save(settings)
            return result
        except Exception as exc:
            error_code = getattr(exc, "error_code", str(exc) or "provider_unknown_error")
            config = config.model_copy(
                update={
                    "last_test_status": AIProviderTestStatus.FAILED,
                    "last_test_at": datetime.now(UTC).isoformat(),
                    "last_test_error_code": error_code,
                    "last_test_error_message": str(exc),
                }
            )
            settings.provider_configs[provider_name] = config
            self._settings_repository.save(settings)
            raise

    def _serialize_provider_config(self, config: AIProviderConfig) -> dict[str, object]:
        api_key_masked = self._mask_api_key(self._settings_cipher.decrypt(config.encrypted_api_key)) if config.encrypted_api_key else ""
        return {
            "provider_name": config.provider_name,
            "enabled": config.enabled,
            "key_configured": config.key_configured,
            "api_key_masked": api_key_masked,
            "default_model": config.default_model,
            "timeout": config.timeout,
            "base_url": config.base_url,
            "last_test_status": config.last_test_status.value,
            "last_test_at": config.last_test_at,
            "last_test_error_code": config.last_test_error_code,
            "last_test_error_message": config.last_test_error_message,
        }

    def _mask_api_key(self, api_key: str) -> str:
        if not api_key:
            return ""
        if len(api_key) <= 5:
            return "*" * len(api_key)
        return f"{api_key[:3]}{'*' * (len(api_key) - 5)}{api_key[-2:]}"
