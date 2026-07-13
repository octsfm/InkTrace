from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import LLMRequest, StyleDNAExtractionResult, StyleProfile, StyleProfileStatus
from domain.repositories.ai.style_profile_repository import StyleProfileRepository


class StyleDNAExtractionService:
    def __init__(
        self,
        *,
        profile_repository: StyleProfileRepository,
        model_router=None,
        prompt_registry=None,
        output_validator=None,
        trace_service=None,
    ) -> None:
        self._profile_repository = profile_repository
        self._model_router = model_router
        self._prompt_registry = prompt_registry
        self._output_validator = output_validator
        self._trace_service = trace_service

    async def extract(
        self,
        *,
        work_id: str,
        source_text: str,
        source_type,
        source_ref: str = "",
    ) -> StyleDNAExtractionResult:
        normalized_source_text = str(source_text or "").strip()
        if not normalized_source_text:
            raise ValueError("style_dna_source_text_empty")
        self._ensure_extract_dependencies()

        template = self._prompt_registry.get_template("style_dna_extraction", version="v1")
        rendered_prompt = self._prompt_registry.render(
            "style_dna_extraction",
            {"source_text": normalized_source_text},
            version="v1",
        )
        source_text_length = len(normalized_source_text)
        warnings: list[str] = []
        low_confidence_reason = ""
        forced_low_confidence = source_text_length < 500
        if forced_low_confidence:
            low_confidence_reason = "source_text_too_short"
            warnings.append(low_confidence_reason)

        validation = None
        for _attempt in range(3):
            request = LLMRequest(
                model_role=template.model_role,
                work_id=work_id,
                prompt_key=template.prompt_key,
                prompt_version=template.prompt_version,
                output_schema_key=template.output_schema_key,
                request_id=f"req_{uuid.uuid4().hex[:12]}",
                trace_id=f"trace_{uuid.uuid4().hex[:12]}",
                max_tokens=2048,
                messages=[{"role": "user", "content": rendered_prompt}],
            )
            response = self._model_router.generate(request)
            validation = self._output_validator.validate(template.output_schema_key, response.content)
            if validation.success:
                break
        if validation is None or not validation.success:
            raise ValueError("style_dna_output_invalid")

        parsed_output = dict(validation.parsed_output or {})
        confidence = float(parsed_output.get("confidence", 0.0) or 0.0)
        if forced_low_confidence:
            confidence = min(confidence, 0.49)

        now = self._now()
        profile = StyleProfile(
            profile_id=f"sp_{uuid.uuid4().hex[:12]}",
            work_id=work_id,
            source_type=source_type,
            source_ref=source_ref,
            source_text_hash=self._hash_source_text(normalized_source_text),
            source_text_length=source_text_length,
            confidence=confidence,
            low_confidence_reason=low_confidence_reason,
            avg_sentence_length=float(parsed_output.get("avg_sentence_length", 0.0) or 0.0),
            sentence_length_variance=float(parsed_output.get("sentence_length_variance", 0.0) or 0.0),
            short_sentence_ratio=float(parsed_output.get("short_sentence_ratio", 0.0) or 0.0),
            long_sentence_ratio=float(parsed_output.get("long_sentence_ratio", 0.0) or 0.0),
            compound_sentence_ratio=float(parsed_output.get("compound_sentence_ratio", 0.0) or 0.0),
            avg_paragraph_length=float(parsed_output.get("avg_paragraph_length", 0.0) or 0.0),
            paragraph_length_variance=float(parsed_output.get("paragraph_length_variance", 0.0) or 0.0),
            dialogue_ratio=float(parsed_output.get("dialogue_ratio", 0.0) or 0.0),
            psychological_ratio=float(parsed_output.get("psychological_ratio", 0.0) or 0.0),
            action_ratio=float(parsed_output.get("action_ratio", 0.0) or 0.0),
            description_ratio=float(parsed_output.get("description_ratio", 0.0) or 0.0),
            narrative_perspective=str(parsed_output.get("narrative_perspective", "") or ""),
            tense_preference=str(parsed_output.get("tense_preference", "") or ""),
            style_summary=str(parsed_output.get("style_summary", "") or ""),
            style_tags=[str(item) for item in parsed_output.get("style_tags", [])],
            version=self._next_version(work_id),
            status=StyleProfileStatus.PENDING_CONFIRM,
            created_at=now,
            updated_at=now,
            confirmed_at="",
        )
        self._profile_repository.save(profile)
        return StyleDNAExtractionResult(
            profile=profile,
            confidence=profile.confidence,
            warnings=warnings,
        )

    def confirm(self, profile_id: str) -> StyleProfile:
        profile = self._load(profile_id)
        if profile.status != StyleProfileStatus.PENDING_CONFIRM:
            raise ValueError("profile_not_confirmable")
        self._archive_current_active(profile.work_id, exclude_profile_id=profile.profile_id)
        confirmed = profile.model_copy(
            update={
                "status": StyleProfileStatus.ACTIVE,
                "confirmed_at": self._now(),
                "updated_at": self._now(),
            }
        )
        return self._profile_repository.update(confirmed)

    def disable(self, profile_id: str) -> StyleProfile:
        profile = self._load(profile_id)
        if profile.status == StyleProfileStatus.DISABLED:
            return profile
        disabled = profile.model_copy(
            update={
                "status": StyleProfileStatus.DISABLED,
                "updated_at": self._now(),
            }
        )
        return self._profile_repository.update(disabled)

    def get_active(self, work_id: str) -> StyleProfile | None:
        return self._profile_repository.get_active(work_id)

    def get_history(self, work_id: str) -> list[StyleProfile]:
        return self._profile_repository.get_history(work_id)

    def get_profile(self, profile_id: str) -> StyleProfile:
        return self._load(profile_id)

    def delete(self, profile_id: str) -> None:
        profile = self._load(profile_id)
        if profile.status == StyleProfileStatus.PENDING_CONFIRM:
            self._profile_repository.delete(profile_id)
            return
        archived = profile.model_copy(
            update={
                "status": StyleProfileStatus.ARCHIVED,
                "updated_at": self._now(),
            }
        )
        self._profile_repository.update(archived)

    def _archive_current_active(self, work_id: str, *, exclude_profile_id: str = "") -> None:
        current_active = self._profile_repository.get_active(work_id)
        if current_active is None or current_active.profile_id == exclude_profile_id:
            return
        archived = current_active.model_copy(
            update={
                "status": StyleProfileStatus.ARCHIVED,
                "updated_at": self._now(),
            }
        )
        self._profile_repository.update(archived)

    def _load(self, profile_id: str) -> StyleProfile:
        profile = self._profile_repository.get_by_id(profile_id)
        if profile is None:
            raise ValueError("style_profile_not_found")
        return profile

    def _ensure_extract_dependencies(self) -> None:
        if self._model_router is None or self._prompt_registry is None or self._output_validator is None:
            raise ValueError("style_dna_extract_dependencies_missing")

    def _hash_source_text(self, source_text: str) -> str:
        return f"sha256:{hashlib.sha256(source_text.encode('utf-8')).hexdigest()}"

    def _next_version(self, work_id: str) -> int:
        history = self._profile_repository.get_history(work_id)
        if not history:
            return 1
        return max(int(item.version or 1) for item in history) + 1

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
