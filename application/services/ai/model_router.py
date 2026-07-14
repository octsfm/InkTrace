from __future__ import annotations

from application.services.ai.provider_registry import ProviderRegistry
from application.services.ai.security import SettingsCipher
from application.services.ai.llm_call_logger import LLMCallLogger
from datetime import UTC, datetime
from domain.entities.ai.models import LLMCallStatus
from domain.entities.ai.models import AIProviderConfig, LLMRequest, LLMResponse, ModelSelection
from domain.repositories.ai.ai_settings_repository import AISettingsRepository
from domain.services.ai.provider import ModelRoleConfigError, ProviderConfigurationError


class ModelRouter:
    _RUNTIME_ROLE_FALLBACKS = {
        "outline_analyzer": "analysis",
        "manuscript_analyzer": "analysis",
        "memory_extractor": "analysis",
        "style_extractor": "analysis",
        "planner": "planning",
        "writing_task_builder": "planning",
        "opening_strategy_planner": "planning",
        "quick_trial_writer": "writer",
        "opening_writer": "writer",
        "opening_risk_checker": "reviewer",
        "polisher": "rewriter",
        "dialogue_writer": "rewriter",
        "scene_generator": "rewriter",
    }

    def __init__(
        self,
        settings_repository: AISettingsRepository,
        provider_registry: ProviderRegistry,
        settings_cipher: SettingsCipher | None = None,
        attempt_guard=None,
        llm_call_logger: LLMCallLogger | None = None,
    ) -> None:
        self._settings_repository = settings_repository
        self._provider_registry = provider_registry
        self._settings_cipher = settings_cipher or SettingsCipher()
        self._attempt_guard = attempt_guard
        self._llm_call_logger = llm_call_logger

    def resolve_model(self, model_role: str) -> ModelSelection:
        settings = self._settings_repository.load()
        selection = settings.model_role_mappings.get(model_role)
        if selection is None:
            fallback_role = self._RUNTIME_ROLE_FALLBACKS.get(model_role, "")
            selection = settings.model_role_mappings.get(fallback_role)
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
        return self.generate_with_selection(request,selection)

    def generate_with_selection(self,request: LLMRequest,selection: ModelSelection) -> LLMResponse:
        if self._attempt_guard is not None:
            self._attempt_guard.before_attempt(request, selection)
        provider_config = self._get_provider_config(selection.provider_name)
        provider = self._provider_registry.get(selection.provider_name)
        started_at=datetime.now(UTC)
        try:
            response=provider.generate(request=request, provider_config=provider_config, model_name=selection.model_name)
        except Exception as exc:
            if not request.external_logging: self._record(request,selection,LLMCallStatus.FAILED,started_at,error_code=getattr(exc,"error_code",str(exc) or "provider_failed"),error_message=str(exc))
            raise
        if not request.external_logging:
            self._record(request,selection,LLMCallStatus.SUCCEEDED,started_at,usage=response.token_usage)
            response=self.after_logged_attempt(request,response,selection)
        return response

    def after_logged_attempt(self,request,response,selection=None):
        selected=selection or self.resolve_model(request.model_role)
        decision=self._attempt_guard.after_logged_attempt(request,selected) if self._attempt_guard is not None else {"allowed":True,"control":"allow","reason_code":"no_enabled_budget"}
        return response.model_copy(update={"further_provider_calls_allowed":bool(decision.get("allowed",False)),"budget_status":str(decision.get("reason_code","") or "")})

    def _record(self,request,selection,status,started_at,usage=None,error_code="",error_message="") -> None:
        if self._llm_call_logger is None:
            return
        snapshot=self._attempt_guard.price_snapshot(request,selection) if self._attempt_guard is not None else {}
        try:
            self._llm_call_logger.record(prompt_key=request.prompt_key,prompt_version=request.prompt_version,work_id=request.work_id,model_role=request.model_role,provider_name=selection.provider_name,model_name=selection.model_name,request_id=request.request_id,trace_id=request.trace_id,status=status,started_at=started_at,finished_at=datetime.now(UTC),usage=usage,error_code=error_code,error_message=error_message,output_schema_key=request.output_schema_key,job_id=request.job_id,session_id=request.session_id,run_id=request.run_id,price_snapshot_override=snapshot)
        except Exception as exc:
            raise RuntimeError("P2_LLM_USAGE_AUDIT_FAILED") from exc

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
        if provider_name == "fake":
            return provider_config
        if encrypted_api_key:
            try:
                decrypted_api_key = self._settings_cipher.decrypt(encrypted_api_key)
            except Exception as exc:
                raise ProviderConfigurationError("provider_key_invalid") from exc
            return provider_config.model_copy(update={"encrypted_api_key": decrypted_api_key})
        return provider_config
