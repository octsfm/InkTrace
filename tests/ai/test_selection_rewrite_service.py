from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.model_router import ModelRouter
from application.services.ai.prompt_registry import PromptRegistry
from application.services.ai.provider_registry import ProviderRegistry
from application.services.ai.security import SettingsCipher
from application.services.ai.selection_rewrite_service import SelectionRewriteService
from domain.entities.ai.models import AIProviderConfig, AISettings, LLMUsage, ModelSelection, SelectionRewriteCandidate, SelectionRewriteMode
from domain.entities.ai.models import LLMResponse
from infrastructure.ai.providers.fake_provider import FakeLLMProvider
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_ai_settings_store import FileAISettingsStore
from infrastructure.persistence.sqlite_selection_rewrite_repo import SQLiteSelectionRewriteRepository


class _EmptySelectionRewriteProvider(FakeLLMProvider):
    provider_name = "empty-selection"

    def __init__(self) -> None:
        super().__init__()
        self._supported_models = {"empty-selection-model"}

    def generate(self, request, provider_config, model_name):
        response = super().generate(request, provider_config, model_name)
        return response.model_copy(update={"content": ""})


class _StructuredSelectionRewriteProvider(FakeLLMProvider):
    provider_name = "structured-selection"

    def __init__(self) -> None:
        super().__init__()
        self._supported_models = {"structured-selection-model"}
        self.requests: list = []

    def generate(self, request, provider_config, model_name):
        self.requests.append(request)
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=model_name,
            content='{"rewritten_text":"月光静静落在旧窗台上","diff_summary":"补强环境描写","risk_notes":["保持原剧情事实"]}',
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            finish_reason="stop",
        )


class _CustomSelectionRewriteProvider(FakeLLMProvider):
    provider_name = "custom-selection"

    def __init__(self, content: str) -> None:
        super().__init__()
        self._supported_models = {"custom-selection-model"}
        self._content = content

    def generate(self, request, provider_config, model_name):
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=model_name,
            content=self._content,
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            finish_reason="stop",
        )


def _build_service(
    tmp_path: Path,
    *,
    provider_name: str = "fake",
    model_name: str = "fake-chat",
    provider=None,
    prompt_registry=None,
):
    settings_store = FileAISettingsStore(tmp_path / "ai_settings.json")
    repo = SQLiteSelectionRewriteRepository(tmp_path / "selection_rewrite.db")
    job_store = FileAIJobStore(tmp_path / "selection_rewrite_jobs.json")
    cipher = SettingsCipher("test-secret")
    settings_store.save(
        AISettings(
            provider_configs={
                provider_name: AIProviderConfig(
                    provider_name=provider_name,
                    enabled=True,
                    encrypted_api_key=cipher.encrypt("fake-api-key"),
                    default_model=model_name,
                )
            },
            model_role_mappings={
                "writer": ModelSelection(provider_name=provider_name, model_name=model_name),
                "rewriter": ModelSelection(provider_name=provider_name, model_name=model_name),
            },
        )
    )
    registry = ProviderRegistry()
    if provider is not None:
        registry.register(provider)
    elif provider_name == "fake":
        registry.register(FakeLLMProvider())
    else:
        registry.register(_EmptySelectionRewriteProvider())
    model_router = ModelRouter(
        settings_repository=settings_store,
        provider_registry=registry,
        settings_cipher=cipher,
    )
    job_service = AIJobService(
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
    )
    return SelectionRewriteService(
        rewrite_repository=repo,
        job_service=job_service,
        model_router=model_router,
        prompt_registry=prompt_registry,
    )


def _prompt_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "application" / "prompts" / "ai"


def test_selection_rewrite_service_queues_job_and_eventually_generates_pending_candidate(tmp_path) -> None:
    service = _build_service(tmp_path)
    source_text = "他走进房间"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=3,
        end_pos=8,
        mode=SelectionRewriteMode.REWRITE,
        caller_type="user_action",
    ))

    assert candidate.status.value == "generating"

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "pending"
    assert latest.rewritten_text
    assert latest.word_count_after > 0


def test_selection_rewrite_service_marks_candidate_failed_after_async_generation_when_output_invalid(tmp_path) -> None:
    service = _build_service(tmp_path, provider_name="empty-selection", model_name="empty-selection-model")
    source_text = "他走进房间"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=3,
        end_pos=8,
        mode=SelectionRewriteMode.REWRITE,
        caller_type="user_action",
    ))

    assert candidate.status.value == "generating"

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "failed"
    assert latest.error_code == "output_schema_invalid"


def test_selection_rewrite_service_uses_writer_prompt_contract_for_expand_mode(tmp_path) -> None:
    provider = _StructuredSelectionRewriteProvider()
    service = _build_service(
        tmp_path,
        provider_name=provider.provider_name,
        model_name="structured-selection-model",
        provider=provider,
    )
    source_text = "月落窗前"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=3,
        end_pos=11,
        mode=SelectionRewriteMode.EXPAND,
        caller_type="user_action",
    ))

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "pending"
    assert provider.requests
    request = provider.requests[0]
    assert request.model_role == "writer"
    assert request.prompt_key == "selection_expand_v1"
    assert request.prompt_version == "v1"
    assert request.output_schema_key == "selection_rewrite_schema"
    assert latest.diff_summary == "补强环境描写"


def test_selection_rewrite_service_uses_rewriter_prompt_contract_for_polish_mode(tmp_path) -> None:
    provider = _StructuredSelectionRewriteProvider()
    service = _build_service(
        tmp_path,
        provider_name=provider.provider_name,
        model_name="structured-selection-model",
        provider=provider,
    )
    source_text = "月落窗前"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=3,
        end_pos=11,
        mode=SelectionRewriteMode.POLISH,
        caller_type="user_action",
    ))

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "pending"
    assert provider.requests
    request = provider.requests[0]
    assert request.model_role == "rewriter"
    assert request.prompt_key == "selection_polish_v1"
    assert request.output_schema_key == "selection_rewrite_schema"
    assert latest.rewritten_text == "月光静静落在旧窗台上"


def test_selection_rewrite_service_renders_system_prompt_from_prompt_registry(tmp_path) -> None:
    provider = _StructuredSelectionRewriteProvider()
    service = _build_service(
        tmp_path,
        provider_name=provider.provider_name,
        model_name="structured-selection-model",
        provider=provider,
        prompt_registry=PromptRegistry(prompt_directory=_prompt_dir()),
    )
    source_text = "月落窗前"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=3,
        end_pos=11,
        mode=SelectionRewriteMode.EXPAND,
        caller_type="user_action",
    ))

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "pending"
    assert provider.requests
    system_message = provider.requests[0].messages[0]["content"]
    assert "月落窗前" in system_message
    assert "扩写" in system_message


def test_selection_rewrite_service_marks_expand_result_failed_when_length_ratio_too_short(tmp_path) -> None:
    provider = _CustomSelectionRewriteProvider(
        '{"rewritten_text":"月光静落","diff_summary":"扩写不足","risk_notes":[]}'
    )
    service = _build_service(
        tmp_path,
        provider_name=provider.provider_name,
        model_name="custom-selection-model",
        provider=provider,
    )
    source_text = "月落窗"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=3,
        end_pos=6,
        mode=SelectionRewriteMode.EXPAND,
        caller_type="user_action",
    ))

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "failed"
    assert latest.error_code == "output_schema_invalid"


def test_selection_rewrite_service_marks_abbreviate_result_failed_when_length_ratio_too_long(tmp_path) -> None:
    provider = _CustomSelectionRewriteProvider(
        '{"rewritten_text":"月光静静落在旧窗台上","diff_summary":"缩写失败","risk_notes":[]}'
    )
    service = _build_service(
        tmp_path,
        provider_name=provider.provider_name,
        model_name="custom-selection-model",
        provider=provider,
    )
    source_text = "月光落在窗台上风正紧"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=3,
        end_pos=14,
        mode=SelectionRewriteMode.ABBREVIATE,
        caller_type="user_action",
    ))

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "failed"
    assert latest.error_code == "output_schema_invalid"


def test_selection_rewrite_service_allows_expand_mode_with_default_fake_provider(tmp_path) -> None:
    service = _build_service(tmp_path)
    source_text = "月落窗前"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=3,
        end_pos=11,
        mode=SelectionRewriteMode.EXPAND,
        caller_type="user_action",
    ))

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "pending"
    assert latest.word_count_after >= int(latest.word_count_before * 1.5)


def test_selection_rewrite_service_persists_context_snapshots_and_uses_full_prompt_context(tmp_path) -> None:
    provider = _StructuredSelectionRewriteProvider()
    service = _build_service(
        tmp_path,
        provider_name=provider.provider_name,
        model_name="structured-selection-model",
        provider=provider,
        prompt_registry=PromptRegistry(prompt_directory=_prompt_dir()),
    )
    context_before = "前" * 120
    context_after = "后" * 120
    source_text = "月落窗前"

    candidate = asyncio.run(service.rewrite(
        work_id="work_001",
        chapter_id="chapter_001",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=300,
        source_text=source_text,
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        start_pos=120,
        end_pos=124,
        context_before=context_before,
        context_after=context_after,
        mode=SelectionRewriteMode.REWRITE,
        caller_type="user_action",
    ))

    deadline = time.time() + 2
    latest = candidate
    while time.time() < deadline:
        latest = asyncio.run(service.get_candidate(candidate.rewrite_id))
        if latest.status.value != "generating":
            break
        time.sleep(0.05)

    assert latest.status.value == "pending"
    assert latest.context_before == context_before[-100:]
    assert latest.context_after == context_after[:100]
    system_message = provider.requests[0].messages[0]["content"]
    assert context_before in system_message
    assert context_after in system_message


def test_selection_rewrite_service_marks_pending_candidate_expired_when_listing_history(tmp_path) -> None:
    service = _build_service(tmp_path)
    repo = SQLiteSelectionRewriteRepository(tmp_path / "selection_rewrite.db")
    candidate = repo.save(SelectionRewriteCandidate(
        rewrite_id="srw_old_001",
        chapter_id="chapter_001",
        work_id="work_001",
        rewrite_mode=SelectionRewriteMode.REWRITE,
        source_text="月落窗前",
        source_hash=sha256("月落窗前".encode("utf-8")).hexdigest(),
        source_start_pos=3,
        source_end_pos=7,
        status="pending",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        created_at=(datetime.now(UTC) - timedelta(hours=25)).isoformat(),
    ))

    items = asyncio.run(service.list_candidates_by_chapter("chapter_001"))

    assert len(items) == 1
    assert items[0].rewrite_id == candidate.rewrite_id
    assert items[0].status.value == "expired"


def test_selection_rewrite_service_clears_history_for_chapter(tmp_path) -> None:
    service = _build_service(tmp_path)
    repo = SQLiteSelectionRewriteRepository(tmp_path / "selection_rewrite.db")
    repo.save(SelectionRewriteCandidate(
        rewrite_id="srw_keep_001",
        chapter_id="chapter_002",
        work_id="work_001",
        rewrite_mode=SelectionRewriteMode.REWRITE,
        source_text="他走进房间",
        source_hash=sha256("他走进房间".encode("utf-8")).hexdigest(),
        source_start_pos=3,
        source_end_pos=8,
        status="pending",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        created_at=datetime.now(UTC).isoformat(),
    ))
    repo.save(SelectionRewriteCandidate(
        rewrite_id="srw_clear_001",
        chapter_id="chapter_001",
        work_id="work_001",
        rewrite_mode=SelectionRewriteMode.REWRITE,
        source_text="他走进房间",
        source_hash=sha256("他走进房间".encode("utf-8")).hexdigest(),
        source_start_pos=3,
        source_end_pos=8,
        status="failed",
        chapter_revision=3,
        draft_revision=12,
        draft_text_hash="hash_draft",
        draft_length=120,
        created_at=datetime.now(UTC).isoformat(),
    ))

    result = asyncio.run(service.clear_chapter_history("chapter_001"))
    remaining = asyncio.run(service.list_candidates_by_chapter("chapter_002"))

    assert result["chapter_id"] == "chapter_001"
    assert result["cleared_count"] == 1
    assert len(remaining) == 1
    assert remaining[0].rewrite_id == "srw_keep_001"
