from __future__ import annotations

import uuid
from datetime import UTC, datetime

from application.services.ai.llm_call_logger import LLMCallLogger
from application.services.ai.output_validation_service import OutputValidationService
from application.services.ai.provider_registry import ProviderRegistry
from domain.entities.ai.models import (
    LLMCallStatus,
    LLMRequest,
    QuickTrialRequest,
    QuickTrialResult,
)
from domain.repositories.ai.ai_settings_repository import AISettingsRepository
from domain.repositories.ai.llm_call_log_repository import LLMCallLogRepository
from domain.services.ai.provider import AIInfraError, ProviderConfigurationError


class QuickTrialApplicationService:
    def __init__(
        self,
        *,
        settings_repository: AISettingsRepository,
        model_router,
        provider_registry: ProviderRegistry,
        llm_call_log_repository: LLMCallLogRepository,
    ) -> None:
        self._settings_repository = settings_repository
        self._model_router = model_router
        self._provider_registry = provider_registry
        self._call_logger = LLMCallLogger(llm_call_log_repository)
        self._output_validation_service = OutputValidationService()

    def run_quick_trial(self, request: QuickTrialRequest) -> QuickTrialResult:
        input_text = str(request.input_text or "").strip()
        if not input_text:
            raise ValueError("quick_trial_input_empty")

        started_at = datetime.now(UTC)
        trial_id = request.trial_id or f"trial_{uuid.uuid4().hex[:12]}"
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"

        try:
            provider_name, model_name, model_role = self._resolve_target(request)
            llm_request = LLMRequest(
                model_role=model_role or "quick_trial_writer",
                prompt_key="quick_trial",
                prompt_version="p0",
                output_schema_key=request.output_schema_key,
                request_id=request_id,
                trace_id=trace_id,
                messages=self._build_messages(request),
            )
            response = self._generate(
                provider_name=provider_name,
                model_name=model_name,
                llm_request=llm_request,
            )
            validation = self._validate_output(
                raw_output=response.content,
                output_schema_key=request.output_schema_key,
                max_output_chars=request.max_output_chars,
            )
            status = "succeeded" if validation.success else "validation_failed"
            finished_at = datetime.now(UTC)
            self._call_logger.record(
                prompt_key="quick_trial",
                prompt_version="p0",
                model_role=model_role or "quick_trial_writer",
                provider_name=provider_name,
                model_name=model_name,
                request_id=request_id,
                trace_id=trace_id,
                status=LLMCallStatus.SUCCEEDED if validation.success else LLMCallStatus.FAILED,
                started_at=started_at,
                finished_at=finished_at,
                usage=response.token_usage,
                error_code="" if validation.success else "quick_trial_output_invalid",
                error_message="" if validation.success else validation.message,
                output_schema_key=request.output_schema_key,
            )
            output_text = str(validation.parsed_output) if validation.success else ""
            return QuickTrialResult(
                trial_id=trial_id,
                status=status,
                output_text=output_text,
                output_preview=output_text[:200],
                validation_status="passed" if validation.success else "failed",
                validation_errors=[] if validation.success else [validation.message or validation.error_code],
                provider_name=provider_name,
                model_name=model_name,
                model_role=model_role or "quick_trial_writer",
                request_id=request_id,
                created_at=finished_at.isoformat(),
                metadata=dict(request.metadata),
            )
        except (ValueError, AIInfraError) as exc:
            finished_at = datetime.now(UTC)
            error_code = getattr(exc, "error_code", str(exc))
            self._call_logger.record(
                prompt_key="quick_trial",
                prompt_version="p0",
                model_role=request.model_role or "quick_trial_writer",
                provider_name=request.provider_name,
                model_name=request.model_name,
                request_id=request_id,
                trace_id=trace_id,
                status=LLMCallStatus.FAILED,
                started_at=started_at,
                finished_at=finished_at,
                error_code=error_code,
                error_message=str(exc),
                output_schema_key=request.output_schema_key,
            )
            raise ValueError(error_code) from exc

    def _resolve_target(self, request: QuickTrialRequest) -> tuple[str, str, str]:
        if request.provider_name and request.model_name:
            settings = self._settings_repository.load()
            provider = self._provider_registry.get(request.provider_name)
            provider_config = settings.provider_configs.get(request.provider_name)
            if provider_config is None:
                raise ProviderConfigurationError("provider_config_missing")
            if not provider_config.enabled:
                raise ProviderConfigurationError("provider_disabled")
            if not provider.supports_model(request.model_name):
                raise ProviderConfigurationError("model_not_supported")
            return request.provider_name, request.model_name, request.model_role or "quick_trial_writer"

        if not request.model_role:
            raise ValueError("quick_trial_target_missing")
        selection = self._model_router.resolve_model(request.model_role)
        return selection.provider_name, selection.model_name, request.model_role

    def _build_messages(self, request: QuickTrialRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if str(request.system_prompt or "").strip():
            messages.append({"role": "system", "content": str(request.system_prompt).strip()})
        messages.append({"role": "user", "content": str(request.input_text).strip()})
        return messages

    def _generate(self, *, provider_name: str, model_name: str, llm_request: LLMRequest):
        settings = self._settings_repository.load()
        provider = self._provider_registry.get(provider_name)
        provider_config = settings.provider_configs.get(provider_name)
        if provider_config is None:
            raise ProviderConfigurationError("provider_config_missing")
        if not provider_config.enabled:
            raise ProviderConfigurationError("provider_disabled")
        return provider.generate(request=llm_request, provider_config=provider_config, model_name=model_name)

    def _validate_output(self, *, raw_output: str, output_schema_key: str, max_output_chars: int):
        validation = self._output_validation_service.validate(output_schema_key, raw_output)
        if not validation.success:
            return validation
        text = str(validation.parsed_output or "").strip()
        if len(text) > max_output_chars:
            return self._output_validation_service.validate(output_schema_key, "")
        return validation
