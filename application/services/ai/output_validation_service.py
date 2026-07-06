from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from domain.entities.ai.models import OutputValidationResult
from domain.validators.selection_rewrite_schema import SelectionRewriteOutputModel


class _ProviderConnectionResultModel(BaseModel):
    ok: bool
    message: str


class _StyleDNAOutputModel(BaseModel):
    confidence: float
    avg_sentence_length: float
    sentence_length_variance: float
    short_sentence_ratio: float
    long_sentence_ratio: float
    compound_sentence_ratio: float
    avg_paragraph_length: float
    paragraph_length_variance: float
    dialogue_ratio: float
    psychological_ratio: float
    action_ratio: float
    description_ratio: float
    narrative_perspective: str
    tense_preference: str
    style_summary: str
    style_tags: list[str]


class OutputValidationService:
    def __init__(self) -> None:
        self._schema_registry: dict[str, type[BaseModel]] = {
            "provider_connection_result": _ProviderConnectionResultModel,
            "style_dna_output": _StyleDNAOutputModel,
            "selection_rewrite_schema": SelectionRewriteOutputModel,
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
