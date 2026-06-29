import asyncio
import json
from pathlib import Path

from application.services.ai.output_validation_service import OutputValidationService
from application.services.ai.prompt_registry import PromptRegistry
from application.services.ai.style_dna_extraction_service import StyleDNAExtractionService
from domain.entities.ai.models import LLMResponse, LLMUsage
from domain.entities.ai.models import StyleProfile, StyleProfileSourceType, StyleProfileStatus
from infrastructure.persistence.sqlite_style_profile_repo import SQLiteStyleProfileRepository


def _build_profile(
    *,
    profile_id: str,
    work_id: str,
    version: int,
    status: StyleProfileStatus,
    created_at: str,
    confirmed_at: str = "",
) -> StyleProfile:
    return StyleProfile(
        profile_id=profile_id,
        work_id=work_id,
        source_type=StyleProfileSourceType.USER_UPLOAD,
        source_ref=f"upload_{profile_id}",
        source_text_hash=f"sha256:{profile_id}",
        source_text_length=2400,
        confidence=0.79,
        low_confidence_reason="",
        avg_sentence_length=16.2,
        sentence_length_variance=4.1,
        short_sentence_ratio=0.25,
        long_sentence_ratio=0.07,
        compound_sentence_ratio=0.31,
        avg_paragraph_length=72.0,
        paragraph_length_variance=10.4,
        dialogue_ratio=0.29,
        psychological_ratio=0.21,
        action_ratio=0.27,
        description_ratio=0.23,
        narrative_perspective="third_person_limited",
        tense_preference="past",
        style_summary="简洁冷静，节奏克制。",
        style_tags=["简洁", "克制"],
        version=version,
        status=status,
        created_at=created_at,
        updated_at=created_at,
        confirmed_at=confirmed_at,
    )


class _StubModelRouter:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        content = self._responses.pop(0)
        return LLMResponse(
            provider_name="fake",
            model_name="fake-chat",
            content=content,
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(input_tokens=12, output_tokens=18, total_tokens=30),
            finish_reason="stop",
        )


def _prompt_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "application" / "prompts" / "ai"


def test_style_dna_service_extract_creates_pending_profile_and_persists_it(tmp_path) -> None:
    repo = SQLiteStyleProfileRepository(tmp_path / "style-profile.db")
    router = _StubModelRouter(
        [
            json.dumps(
                {
                    "confidence": 0.78,
                    "avg_sentence_length": 16.2,
                    "sentence_length_variance": 4.1,
                    "short_sentence_ratio": 0.25,
                    "long_sentence_ratio": 0.07,
                    "compound_sentence_ratio": 0.31,
                    "avg_paragraph_length": 72.0,
                    "paragraph_length_variance": 10.4,
                    "dialogue_ratio": 0.29,
                    "psychological_ratio": 0.21,
                    "action_ratio": 0.27,
                    "description_ratio": 0.23,
                    "narrative_perspective": "third_person_limited",
                    "tense_preference": "past",
                    "style_summary": "简洁冷静，节奏克制。",
                    "style_tags": ["简洁", "克制"],
                },
                ensure_ascii=False,
            )
        ]
    )
    service = StyleDNAExtractionService(
        profile_repository=repo,
        model_router=router,
        prompt_registry=PromptRegistry(prompt_directory=_prompt_dir()),
        output_validator=OutputValidationService(),
    )

    source_text = "这是用于提取文风特征的标杆文本。" * 40
    result = asyncio.run(
        service.extract(
            work_id="work_001",
            source_text=source_text,
            source_type=StyleProfileSourceType.USER_UPLOAD,
            source_ref="upload_001",
        )
    )

    stored = repo.get_by_id(result.profile.profile_id)
    assert stored is not None
    assert result.profile.status == StyleProfileStatus.PENDING_CONFIRM
    assert result.profile.work_id == "work_001"
    assert result.profile.source_type == StyleProfileSourceType.USER_UPLOAD
    assert result.profile.source_ref == "upload_001"
    assert result.profile.source_text_length == len(source_text)
    assert result.profile.source_text_hash != ""
    assert result.confidence == result.profile.confidence
    assert result.warnings == []
    assert router.requests[0].model_role == "style_extractor"
    assert router.requests[0].prompt_key == "style_dna_extraction"
    assert router.requests[0].output_schema_key == "style_dna_output"
    assert source_text in router.requests[0].messages[-1]["content"]


def test_style_dna_service_extract_marks_low_confidence_when_source_text_too_short(tmp_path) -> None:
    repo = SQLiteStyleProfileRepository(tmp_path / "style-profile.db")
    router = _StubModelRouter(
        [
            json.dumps(
                {
                    "confidence": 0.92,
                    "avg_sentence_length": 10.0,
                    "sentence_length_variance": 2.0,
                    "short_sentence_ratio": 0.5,
                    "long_sentence_ratio": 0.01,
                    "compound_sentence_ratio": 0.12,
                    "avg_paragraph_length": 42.0,
                    "paragraph_length_variance": 6.0,
                    "dialogue_ratio": 0.18,
                    "psychological_ratio": 0.16,
                    "action_ratio": 0.38,
                    "description_ratio": 0.28,
                    "narrative_perspective": "first_person",
                    "tense_preference": "present",
                    "style_summary": "短句为主，动作描写更突出。",
                    "style_tags": ["短句", "动作"],
                },
                ensure_ascii=False,
            )
        ]
    )
    service = StyleDNAExtractionService(
        profile_repository=repo,
        model_router=router,
        prompt_registry=PromptRegistry(prompt_directory=_prompt_dir()),
        output_validator=OutputValidationService(),
    )

    source_text = "短文本" * 40
    result = asyncio.run(
        service.extract(
            work_id="work_001",
            source_text=source_text,
            source_type=StyleProfileSourceType.MANUAL,
            source_ref="manual_001",
        )
    )

    assert result.profile.confidence < 0.5
    assert result.profile.low_confidence_reason == "source_text_too_short"
    assert result.confidence == result.profile.confidence
    assert "source_text_too_short" in result.warnings


def test_style_dna_service_confirm_archives_old_active_and_activates_pending_profile(tmp_path) -> None:
    repo = SQLiteStyleProfileRepository(tmp_path / "style-profile.db")
    service = StyleDNAExtractionService(profile_repository=repo)
    old_active = _build_profile(
        profile_id="sp_active_001",
        work_id="work_001",
        version=1,
        status=StyleProfileStatus.ACTIVE,
        created_at="2026-06-23T09:00:00Z",
        confirmed_at="2026-06-23T09:05:00Z",
    )
    pending = _build_profile(
        profile_id="sp_pending_002",
        work_id="work_001",
        version=2,
        status=StyleProfileStatus.PENDING_CONFIRM,
        created_at="2026-06-23T10:00:00Z",
    )
    repo.save(old_active)
    repo.save(pending)

    confirmed = service.confirm("sp_pending_002")
    current_active = service.get_active("work_001")
    history = service.get_history("work_001")

    assert confirmed.status == StyleProfileStatus.ACTIVE
    assert confirmed.confirmed_at != ""
    assert current_active is not None
    assert current_active.profile_id == "sp_pending_002"
    assert any(item.profile_id == "sp_active_001" and item.status == StyleProfileStatus.ARCHIVED for item in history)


def test_style_dna_service_disable_and_delete_follow_frozen_rules(tmp_path) -> None:
    repo = SQLiteStyleProfileRepository(tmp_path / "style-profile.db")
    service = StyleDNAExtractionService(profile_repository=repo)
    pending = _build_profile(
        profile_id="sp_pending_001",
        work_id="work_001",
        version=1,
        status=StyleProfileStatus.PENDING_CONFIRM,
        created_at="2026-06-23T10:00:00Z",
    )
    active = _build_profile(
        profile_id="sp_active_001",
        work_id="work_001",
        version=2,
        status=StyleProfileStatus.ACTIVE,
        created_at="2026-06-23T11:00:00Z",
        confirmed_at="2026-06-23T11:05:00Z",
    )
    repo.save(pending)
    repo.save(active)

    disabled = service.disable("sp_active_001")
    service.delete("sp_pending_001")
    service.delete("sp_active_001")

    assert disabled.status == StyleProfileStatus.DISABLED
    assert service.get_active("work_001") is None
    assert repo.get_by_id("sp_pending_001") is None
    archived = repo.get_by_id("sp_active_001")
    assert archived is not None
    assert archived.status == StyleProfileStatus.ARCHIVED
