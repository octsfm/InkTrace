from __future__ import annotations

from application.services.ai.provider_registry import ProviderRegistry
from application.services.ai.security import SettingsCipher
from domain.entities.ai.models import AIProviderConfig, LLMRequest, LLMResponse, ModelSelection
from domain.repositories.ai.ai_settings_repository import AISettingsRepository
from domain.services.ai.provider import ModelRoleConfigError, ProviderConfigurationError


class ModelRouter:
    def __init__(
        self,
        settings_repository: AISettingsRepository,
        provider_registry: ProviderRegistry,
        settings_cipher: SettingsCipher | None = None,
    ) -> None:
        self._settings_repository = settings_repository
        self._provider_registry = provider_registry
        self._settings_cipher = settings_cipher or SettingsCipher()

    def resolve_model(self, model_role: str) -> ModelSelection:
        settings = self._settings_repository.load()
        selection = settings.model_role_mappings.get(model_role)
        if selection is None:
            raise ModelRoleConfigError(model_role)
        provider_config = settings.provider_configs.get(selection.provider_name)
        if provider_config is None:
            raise ProviderConfigurationError("provider_config_missing")
        if not provider_config.enabled:
            raise ProviderConfigurationError("provider_disabled")
        provider = self._provider_registry.get(selection.provider_name)
        if not provider.supports_model(selection.model_name):
            raise ProviderConfigurationError("model_not_supported")
        return selection

    def generate(self, request: LLMRequest) -> LLMResponse:
        selection = self.resolve_model(request.model_role)
        provider_config = self._get_provider_config(selection.provider_name)
        provider = self._provider_registry.get(selection.provider_name)
        return provider.generate(request=request, provider_config=provider_config, model_name=selection.model_name)

    def test_connection(self, provider_name: str, model_name: str | None = None) -> dict[str, str]:
        provider_config = self._get_provider_config(provider_name)
        chosen_model = model_name or provider_config.default_model
        if not chosen_model:
            raise ProviderConfigurationError("provider_model_missing")
        provider = self._provider_registry.get(provider_name)
        if not provider.supports_model(chosen_model):
            raise ProviderConfigurationError("model_not_supported")
        if not provider_config.encrypted_api_key:
            raise ProviderConfigurationError("provider_key_missing")
        return provider.test_connection(provider_config=provider_config, model_name=chosen_model)

    def _get_provider_config(self, provider_name: str) -> AIProviderConfig:
        settings = self._settings_repository.load()
        provider_config = settings.provider_configs.get(provider_name)
        if provider_config is None:
            raise ProviderConfigurationError("provider_config_missing")
        if not provider_config.enabled:
            raise ProviderConfigurationError("provider_disabled")
        encrypted_api_key = provider_config.encrypted_api_key
        if encrypted_api_key:
            try:
                decrypted_api_key = self._settings_cipher.decrypt(encrypted_api_key)
            except Exception as exc:
                raise ProviderConfigurationError("provider_key_invalid") from exc
            return provider_config.model_copy(update={"encrypted_api_key": decrypted_api_key})
        return provider_config
