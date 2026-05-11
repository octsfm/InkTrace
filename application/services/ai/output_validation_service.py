from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from domain.entities.ai.models import OutputValidationResult


class _ProviderConnectionResultModel(BaseModel):
    ok: bool
    message: str


class OutputValidationService:
    def __init__(self) -> None:
        self._schema_registry: dict[str, type[BaseModel]] = {
            "provider_connection_result": _ProviderConnectionResultModel,
        }

    def validate(self, output_schema_key: str, raw_output: Any) -> OutputValidationResult:
        if output_schema_key == "plain_text":
            text = str(raw_output or "").strip()
            if not text:
                return OutputValidationResult(success=False, error_code="output_schema_invalid", message="plain_text_empty")
            lowered = text.lower()
            if lowered.startswith("error:") or "provider_auth_failed" in lowered:
                return OutputValidationResult(success=False, error_code="output_schema_invalid", message="plain_text_provider_error")
            return OutputValidationResult(success=True, parsed_output=text)

        model = self._schema_registry.get(output_schema_key)
        if model is None:
            return OutputValidationResult(success=False, error_code="output_schema_missing", message=output_schema_key)

        try:
            payload = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
            validated = model.model_validate(payload)
            return OutputValidationResult(success=True, parsed_output=validated.model_dump())
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            return OutputValidationResult(success=False, error_code="output_schema_invalid", message=str(exc))
