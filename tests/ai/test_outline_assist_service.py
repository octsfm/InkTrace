from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Lock, Thread
from types import SimpleNamespace

import pytest

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.conflict_guard_service import ConflictGuardService
from application.services.ai.outline_application_service import OutlineApplicationService, OutlineConflictReviewRequired
from application.services.ai.outline_assist_service import OutlineAssistService
from application.services.ai.outline_assist_service import OutlinePlannerService
from application.services.ai.output_validation_service import OutputValidationService
from application.services.ai.agent_trace_service import AgentTraceService
from application.services.v1.service_factory import build_writing_asset_service
from application.services.v1.work_service import WorkService
from application.services.v1.writing_asset_service import WritingAssetService
from domain.entities.ai.models import (
    AISuggestion,
    AISuggestionAction,
    AISuggestionActionType,
    AISuggestionPriority,
    AISuggestionSeverity,
    AISuggestionSource,
    AISuggestionStatus,
    AISuggestionTarget,
    AISuggestionType,
    AIJobStepStatus,
    AIJobStatus,
    ConflictRecordStatus,
    ConflictGuardRecord,
    ConflictSeverity,
    ConflictType,
    DirectionPlanStatus,
    LLMCallStatus,
    LLMUsage,
)
from domain.entities.writing_assets import ChapterOutline, WorkOutline
from domain.value_objects.outline_snapshot import outline_content_hash, preserves_outline_node_contract
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_ai_suggestion_store import FileAISuggestionStore
from infrastructure.database.repositories.ai.file_conflict_guard_store import FileConflictGuardStore
from infrastructure.database.repositories.ai.file_agent_trace_store import FileAgentTraceStore
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import initialize_database


class _Assets:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.work_outline = WorkOutline("wo-1", "work-1", "旧的作品大纲", [], 3, now, now)
        self.chapter_outline = ChapterOutline("co-1", "chapter-1", "旧的章节大纲", [], 5, now, now)
        self.saved: list[tuple[str, str, int]] = []
        self.expected_content_hashes: list[str | None] = []

    def get_work_outline(self, work_id: str) -> WorkOutline:
        if work_id != "work-1":
            raise ValueError("work_not_found")
        return self.work_outline

    def get_chapter_outline(self, chapter_id: str) -> ChapterOutline:
        if chapter_id != "chapter-1":
            raise ValueError("chapter_not_found")
        return self.chapter_outline

    def chapter_belongs_to_work(self, chapter_id: str, work_id: str) -> bool:
        return chapter_id == "chapter-1" and work_id == "work-1"

    def is_outline_persisted(self, *, target_kind: str, target_id: str) -> bool:
        return (target_kind, target_id) in {
            ("work_outline", "work-1"),
            ("chapter_outline", "chapter-1"),
        }

    def save_work_outline(
        self,
        work_id: str,
        *,
        content_text: str,
        content_tree_json,
        expected_version: int,
        expected_content_hash: str | None = None,
        force_override: bool = False,
    ):
        assert force_override is False
        if expected_version != self.work_outline.version:
            raise ValueError("asset_version_conflict")
        self.expected_content_hashes.append(expected_content_hash)
        self.saved.append(("work_outline", content_text, expected_version))
        self.work_outline = WorkOutline(
            self.work_outline.id,
            work_id,
            content_text,
            content_tree_json,
            expected_version + 1,
            self.work_outline.created_at,
            datetime.now(UTC),
        )
        return self.work_outline

    def save_chapter_outline(
        self,
        chapter_id: str,
        *,
        content_text: str,
        content_tree_json,
        expected_version: int,
        expected_content_hash: str | None = None,
        force_override: bool = False,
    ):
        assert force_override is False
        if expected_version != self.chapter_outline.version:
            raise ValueError("asset_version_conflict")
        self.expected_content_hashes.append(expected_content_hash)
        self.saved.append(("chapter_outline", content_text, expected_version))
        self.chapter_outline = ChapterOutline(
            self.chapter_outline.id,
            chapter_id,
            content_text,
            content_tree_json,
            expected_version + 1,
            self.chapter_outline.created_at,
            datetime.now(UTC),
        )
        return self.chapter_outline


class _Planner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(
        self,
        *,
        suggestion_type: AISuggestionType,
        source_text: str,
        target_content_tree_json,
        options: dict[str, object],
        **audit_scope,
    ):
        self.calls.append(
            {
                "suggestion_type": suggestion_type,
                "source_text": source_text,
                "target_content_tree_json": target_content_tree_json,
                "options": options,
                "audit_scope": audit_scope,
            }
        )
        result = {
            "proposed_content_text": "新的作品大纲",
            "proposed_content_tree_json": target_content_tree_json,
            "diff_summary": ["理顺开篇目标"],
        }
        if suggestion_type == AISuggestionType.OUTLINE_POLISH:
            result["polish_notes"] = ["没有新增剧情事实"]
        elif suggestion_type == AISuggestionType.OUTLINE_EXPAND:
            result.update({"expansion_points": ["补足动机"], "expand_focus": options.get("expand_focus")})
        elif suggestion_type == AISuggestionType.CHAPTER_OUTLINE_DETAIL:
            result.update(
                {
                    "chapter_goal": str(options.get("chapter_goal") or "推进本章目标"),
                    "scene_beats": [],
                    "conflict_points": ["本章冲突"],
                    "ending_hook": "留下选择",
                }
            )
        elif suggestion_type == AISuggestionType.WRITING_TASK_SUGGESTION:
            return {
                "task_title": "本章写作要点",
                "writing_goal": "推进本章目标",
                "must_include": ["关键线索"],
                "must_not_include": ["提前揭晓"],
                "target_word_count": 2200,
                "tone_guidance": "克制",
                "required_beats": ["发现线索"],
                "context_summary": "依据已确认计划整理",
            }
        return result


class _RequiredTrace:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def ensure_operation_trace(self, **kwargs):
        return SimpleNamespace(**kwargs)

    def record_audit_event(self, **kwargs):
        self.events.append(dict(kwargs))
        return SimpleNamespace(**kwargs)

    def finish_operation_trace(self, *args, **kwargs):
        return SimpleNamespace(trace_id=args[0], **kwargs)


class _CheckpointFailsOnceTrace(_RequiredTrace):
    def __init__(self) -> None:
        super().__init__()
        self._remaining_checkpoint_failures = 1

    def record_audit_event(self, **kwargs):
        if kwargs.get("event_type") == "checkpoint_saved" and self._remaining_checkpoint_failures:
            self._remaining_checkpoint_failures -= 1
            raise OSError("checkpoint trace temporarily unavailable")
        return super().record_audit_event(**kwargs)


def _job_service(tmp_path: Path) -> AIJobService:
    store = FileAIJobStore(tmp_path / "outline_jobs.json")
    return AIJobService(store, store, store)


def _conflict_guard(store: FileConflictGuardStore) -> ConflictGuardService:
    return ConflictGuardService(
        conflict_guard_repository=store,
        candidate_draft_repository=object(),
        chapter_service=object(),
    )


class _ResolveFailingGuard:
    def __init__(self, delegate: ConflictGuardService) -> None:
        self._delegate = delegate

    def record_outline_apply_check(self, **kwargs):
        return self._delegate.record_outline_apply_check(**kwargs)

    def acknowledge_outline_apply(self, *args, **kwargs):
        return self._delegate.acknowledge_outline_apply(*args, **kwargs)

    def list_unresolved_outline_blocking(self, **kwargs):
        return self._delegate.list_unresolved_outline_blocking(**kwargs)

    def resolve_outline_apply(self, *args, **kwargs):
        raise RuntimeError("audit store temporarily unavailable")


class _FailCompletedSuggestionStore:
    def __init__(self, delegate: FileAISuggestionStore, failures: int) -> None:
        self._delegate = delegate
        self.remaining_failures = failures

    def save(self, suggestion):
        if suggestion.status == AISuggestionStatus.CONVERTED and self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise OSError("temporary suggestion store failure")
        return self._delegate.save(suggestion)

    def get(self, suggestion_id: str):
        return self._delegate.get(suggestion_id)

    def list_suggestions(self, **kwargs):
        return self._delegate.list_suggestions(**kwargs)


class _FailFirstFormalSaveAssets(_Assets):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_work_save = True

    def save_work_outline(self, *args, **kwargs):
        if self.fail_next_work_save:
            self.fail_next_work_save = False
            raise OSError("formal asset save did not happen")
        return super().save_work_outline(*args, **kwargs)


class _EntityRepo:
    def __init__(self, entity) -> None:
        self.entity = entity

    def find_by_id(self, entity_id: str):
        return self.entity


class _SlowAbsentOutlineRepo:
    def __init__(self) -> None:
        self.item = None
        self._lock = Lock()

    def _observe(self):
        with self._lock:
            observed = self.item
        if observed is None:
            time.sleep(0.08)
        return observed

    def find_by_work(self, work_id: str):
        return self._observe()

    def find_by_chapter(self, chapter_id: str):
        return self._observe()

    def save(self, outline) -> None:
        with self._lock:
            self.item = outline


def test_outline_generation_uses_formal_asset_hash_not_editable_selected_text(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "outline_suggestions.json")
    queued: list[callable] = []
    service = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )

    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text="作者在输入框里改过的参考文字",
        caller_type="user_action",
        idempotency_key="polish-1",
    )

    pending = suggestions.get(launch.suggestion_id)
    assert launch.status == "pending"
    assert pending.status == AISuggestionStatus.PENDING
    assert pending.payload["target_content_text"] == "旧的作品大纲"
    assert pending.payload["target_content_hash"] != pending.payload.get("selected_text_hash")
    assert assets.saved == []

    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    assert generated.status == AISuggestionStatus.GENERATED
    assert generated.payload["proposed_content_text"] == "新的作品大纲"
    assert assets.saved == []
    job_audit_text = (tmp_path / "outline_jobs.json").read_text(encoding="utf-8")
    assert "旧的作品大纲" not in job_audit_text
    assert "作者在输入框里改过的参考文字" not in job_audit_text
    assert "新的作品大纲" not in job_audit_text
    assert "api_key" not in job_audit_text.lower()


@pytest.mark.parametrize(
    ("suggestion_type", "schema_key", "output"),
    [
        (AISuggestionType.OUTLINE_POLISH, "outline_polish_schema", {"proposed_content_text": "润色后", "proposed_content_tree_json": [], "diff_summary": [], "polish_notes": []}),
        (AISuggestionType.OUTLINE_EXPAND, "outline_expand_schema", {"proposed_content_text": "扩写后", "proposed_content_tree_json": [], "diff_summary": [], "expansion_points": [], "expand_focus": None}),
        (AISuggestionType.CHAPTER_OUTLINE_DETAIL, "chapter_outline_detail_schema", {"proposed_content_text": "细纲", "proposed_content_tree_json": [], "diff_summary": [], "chapter_goal": "目标", "scene_beats": [], "conflict_points": [], "ending_hook": "钩子"}),
        (AISuggestionType.WRITING_TASK_SUGGESTION, "writing_task_suggestion_schema", {"task_title": "要点", "writing_goal": "推进目标", "must_include": [], "must_not_include": [], "target_word_count": 2000, "tone_guidance": "", "required_beats": [], "context_summary": ""}),
    ],
)
def test_outline_planner_maps_each_mode_to_structured_contract(suggestion_type, schema_key, output) -> None:
    class _Router:
        def __init__(self) -> None:
            self.requests = []

        def generate(self, request):
            self.requests.append(request)
            return SimpleNamespace(content=json.dumps(output, ensure_ascii=False))

    router = _Router()
    planner = _tested_outline_planner(router)
    result = _generate_with_audit_scope(
        planner,
        suggestion_type=suggestion_type,
        source_text="原大纲",
        target_content_tree_json=[],
        options={},
    )

    assert result
    assert router.requests[0].model_role == "planner"
    assert router.requests[0].output_schema_key == schema_key


def test_outline_planner_retries_structural_validation_twice() -> None:
    valid = {"proposed_content_text": "有效结果", "proposed_content_tree_json": [], "diff_summary": [], "polish_notes": []}

    class _Router:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, request):
            self.calls += 1
            content = "not-json" if self.calls < 3 else json.dumps(valid, ensure_ascii=False)
            return SimpleNamespace(content=content)

    router = _Router()
    planner = _tested_outline_planner(router)
    result = _generate_with_audit_scope(
        planner,
        suggestion_type=AISuggestionType.OUTLINE_POLISH,
        source_text="原大纲",
        target_content_tree_json=[],
        options={},
    )
    assert router.calls == 3
    assert result["proposed_content_text"] == "有效结果"


class _PromptRegistry:
    def __init__(self, *, missing: bool = False) -> None:
        self.missing = missing
        self.calls: list[dict[str, object]] = []

    def render(self, **kwargs) -> str:
        self.calls.append(dict(kwargs))
        if self.missing:
            raise ValueError("prompt_template_missing")
        return "SAFE_REGISTERED_PROMPT"


class _LLMLogger:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def record(self, **kwargs) -> None:
        if self.fail:
            raise OSError("audit store unavailable")
        self.calls.append(dict(kwargs))


def _tested_outline_planner(router) -> OutlinePlannerService:
    class _RouterAdapter:
        def resolve_model(self, model_role):
            return SimpleNamespace(provider_name="fake", model_name="fake-planner")

        def generate(self, request):
            response = router.generate(request)
            if not hasattr(response, "provider_name"):
                response.provider_name = "fake"
            if not hasattr(response, "model_name"):
                response.model_name = "fake-planner"
            if not hasattr(response, "token_usage"):
                response.token_usage = LLMUsage(total_tokens=0)
            return response

    return OutlinePlannerService(
        model_router=_RouterAdapter(),
        output_validator=OutputValidationService(),
        prompt_registry=_PromptRegistry(),
        llm_call_logger=_LLMLogger(),
    )


def _generate_with_audit_scope(planner: OutlinePlannerService, **kwargs):
    return planner.generate(
        **kwargs,
        work_id="work-1",
        trace_id="trace-shared",
        session_id="suggestion-1",
        step_id="step-1",
    )


def test_outline_planner_requires_registered_prompt_without_hardcoded_fallback() -> None:
    class _Router:
        def __init__(self) -> None:
            self.calls = 0

        def resolve_model(self, model_role):
            return SimpleNamespace(provider_name="fake", model_name="fake-planner")

        def generate(self, request):
            self.calls += 1
            raise AssertionError("model must not run without a registered prompt")

    router = _Router()
    planner = OutlinePlannerService(
        model_router=router,
        output_validator=OutputValidationService(),
        prompt_registry=_PromptRegistry(missing=True),
        llm_call_logger=_LLMLogger(),
    )

    with pytest.raises(ValueError, match="prompt_template_missing"):
        planner.generate(
            suggestion_type=AISuggestionType.OUTLINE_POLISH,
            source_text="SENSITIVE_OUTLINE",
            target_content_tree_json=[],
            options={},
            work_id="work-1",
            trace_id="trace-shared",
            session_id="suggestion-1",
            step_id="step-1",
        )

    assert router.calls == 0


def test_outline_planner_logs_every_attempt_with_shared_trace_and_safe_content_hash() -> None:
    valid = {
        "proposed_content_text": "SENSITIVE_RESULT",
        "proposed_content_tree_json": [],
        "diff_summary": [],
        "polish_notes": [],
    }

    class _Router:
        def __init__(self) -> None:
            self.requests = []

        def resolve_model(self, model_role):
            return SimpleNamespace(provider_name="fake", model_name="fake-planner")

        def generate(self, request):
            self.requests.append(request)
            content = "not-json" if len(self.requests) < 3 else json.dumps(valid, ensure_ascii=False)
            return SimpleNamespace(
                content=content,
                provider_name="fake",
                model_name="fake-planner",
                token_usage=LLMUsage(input_tokens=11, output_tokens=7, total_tokens=18),
            )

    router = _Router()
    logger = _LLMLogger()
    registry = _PromptRegistry()
    planner = OutlinePlannerService(
        model_router=router,
        output_validator=OutputValidationService(),
        prompt_registry=registry,
        llm_call_logger=logger,
    )

    result = planner.generate(
        suggestion_type=AISuggestionType.OUTLINE_POLISH,
        source_text="SENSITIVE_OUTLINE",
        target_content_tree_json=[],
        options={},
        work_id="work-1",
        trace_id="trace-shared",
        session_id="suggestion-1",
        step_id="step-1",
    )

    assert result["proposed_content_text"] == "SENSITIVE_RESULT"
    assert [call["attempt_no"] for call in logger.calls] == [1, 2, 3]
    assert [call["status"] for call in logger.calls] == [
        LLMCallStatus.FAILED,
        LLMCallStatus.FAILED,
        LLMCallStatus.SUCCEEDED,
    ]
    assert {call["trace_id"] for call in logger.calls} == {"trace-shared"}
    assert len({call["request_id"] for call in logger.calls}) == 3
    assert {call["provider_name"] for call in logger.calls} == {"fake"}
    assert {call["model_name"] for call in logger.calls} == {"fake-planner"}
    assert {call["output_schema_key"] for call in logger.calls} == {"outline_polish_schema"}
    assert all(call["usage"].total_tokens == 18 for call in logger.calls)
    serialized_log_arguments = repr(logger.calls)
    assert "SENSITIVE_OUTLINE" not in serialized_log_arguments
    assert "SENSITIVE_RESULT" not in serialized_log_arguments
    assert all(len(str(call["content_hash"])) == 64 for call in logger.calls)


def test_outline_planner_logger_failure_is_audit_failure() -> None:
    class _Router:
        def resolve_model(self, model_role):
            return SimpleNamespace(provider_name="fake", model_name="fake-planner")

        def generate(self, request):
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "proposed_content_text": "结果",
                        "proposed_content_tree_json": [],
                        "diff_summary": [],
                        "polish_notes": [],
                    },
                    ensure_ascii=False,
                ),
                provider_name="fake",
                model_name="fake-planner",
                token_usage=LLMUsage(total_tokens=1),
            )

    planner = OutlinePlannerService(
        model_router=_Router(),
        output_validator=OutputValidationService(),
        prompt_registry=_PromptRegistry(),
        llm_call_logger=_LLMLogger(fail=True),
    )

    with pytest.raises(ValueError, match="P2_OUTLINE_AUDIT_WRITE_FAILED"):
        planner.generate(
            suggestion_type=AISuggestionType.OUTLINE_POLISH,
            source_text="原大纲",
            target_content_tree_json=[],
            options={},
            work_id="work-1",
            trace_id="trace-shared",
            session_id="suggestion-1",
            step_id="step-1",
        )


@pytest.mark.parametrize("failure_stage", ["resolve", "generate"])
def test_outline_planner_provider_failure_always_writes_safe_failed_call_log(failure_stage: str) -> None:
    class _Router:
        def resolve_model(self, model_role):
            if failure_stage == "resolve":
                raise OSError("SENSITIVE_PROVIDER_CONFIGURATION")
            return SimpleNamespace(provider_name="fake", model_name="fake-planner")

        def generate(self, request):
            raise OSError("SENSITIVE_API_KEY_OR_PROMPT")

    logger = _LLMLogger()
    planner = OutlinePlannerService(
        model_router=_Router(),
        output_validator=OutputValidationService(),
        prompt_registry=_PromptRegistry(),
        llm_call_logger=logger,
    )

    with pytest.raises(ValueError, match="provider_call_failed"):
        _generate_with_audit_scope(
            planner,
            suggestion_type=AISuggestionType.OUTLINE_POLISH,
            source_text="SENSITIVE_OUTLINE",
            target_content_tree_json=[],
            options={},
        )

    assert len(logger.calls) == 1
    assert logger.calls[0]["status"] == LLMCallStatus.FAILED
    assert logger.calls[0]["error_code"] == "provider_call_failed"
    assert logger.calls[0]["attempt_no"] == 1
    assert str(logger.calls[0]["request_id"]).startswith("req_oa_")
    expected_provider = "unresolved" if failure_stage == "resolve" else "fake"
    expected_model = "unresolved" if failure_stage == "resolve" else "fake-planner"
    assert logger.calls[0]["provider_name"] == expected_provider
    assert logger.calls[0]["model_name"] == expected_model
    assert logger.calls[0]["usage"] == LLMUsage()
    assert "SENSITIVE" not in repr(logger.calls)


def test_outline_planner_normalizes_missing_response_observability_fields() -> None:
    class _Router:
        def resolve_model(self, model_role):
            return SimpleNamespace(provider_name="", model_name="")

        def generate(self, request):
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "proposed_content_text": "结果",
                        "proposed_content_tree_json": [],
                        "diff_summary": [],
                        "polish_notes": [],
                    },
                    ensure_ascii=False,
                )
            )

    logger = _LLMLogger()
    planner = OutlinePlannerService(
        model_router=_Router(),
        output_validator=OutputValidationService(),
        prompt_registry=_PromptRegistry(),
        llm_call_logger=logger,
    )

    result = _generate_with_audit_scope(
        planner,
        suggestion_type=AISuggestionType.OUTLINE_POLISH,
        source_text="原大纲",
        target_content_tree_json=[],
        options={},
    )

    assert result["proposed_content_text"] == "结果"
    assert len(logger.calls) == 1
    assert logger.calls[0]["provider_name"] == "unresolved"
    assert logger.calls[0]["model_name"] == "unresolved"
    assert logger.calls[0]["usage"] == LLMUsage()


def test_outline_planner_validator_exception_is_logged_for_all_attempts() -> None:
    class _Router:
        def resolve_model(self, model_role):
            return SimpleNamespace(provider_name="fake", model_name="fake-planner")

        def generate(self, request):
            return SimpleNamespace(
                content='{"proposed_content_text":"SENSITIVE_RESULT"}',
                provider_name="fake",
                model_name="fake-planner",
                token_usage=LLMUsage(total_tokens=3),
            )

    class _ExplodingValidator:
        def validate(self, schema_key, content):
            raise RuntimeError("SENSITIVE_VALIDATOR_DETAIL")

    logger = _LLMLogger()
    planner = OutlinePlannerService(
        model_router=_Router(),
        output_validator=_ExplodingValidator(),
        prompt_registry=_PromptRegistry(),
        llm_call_logger=logger,
    )

    with pytest.raises(ValueError, match="output_schema_invalid"):
        _generate_with_audit_scope(
            planner,
            suggestion_type=AISuggestionType.OUTLINE_POLISH,
            source_text="SENSITIVE_OUTLINE",
            target_content_tree_json=[],
            options={},
        )

    assert [call["attempt_no"] for call in logger.calls] == [1, 2, 3]
    assert all(call["status"] == LLMCallStatus.FAILED for call in logger.calls)
    assert all(call["error_code"] == "output_schema_invalid" for call in logger.calls)
    assert "SENSITIVE" not in repr(logger.calls)


def test_outline_assist_uses_only_controlled_writing_asset_read_facade(tmp_path: Path) -> None:
    class _FacadeOnlyAssets(_Assets):
        @property
        def work_outline_repo(self):
            raise AssertionError("application service must not inspect repository attributes")

        @property
        def chapter_outline_repo(self):
            raise AssertionError("application service must not inspect repository attributes")

        @property
        def chapter_repo(self):
            raise AssertionError("application service must not inspect repository attributes")

    queued: list[callable] = []
    service = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=FileAISuggestionStore(tmp_path / "facade-suggestions.json"),
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=_FacadeOnlyAssets(),
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )

    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="facade-only",
    )

    assert launch.status == "pending"
    assert len(queued) == 1


def test_missing_generation_trace_fails_suggestion_and_job_without_enqueue(tmp_path: Path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "missing-trace-suggestions.json")
    jobs = _job_service(tmp_path)
    queued: list[callable] = []
    service = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=jobs,
        writing_asset_service=_Assets(),
        trace_service=None,
        background_submitter=queued.append,
    )

    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="missing-trace",
    )

    suggestion = suggestions.get(launch.suggestion_id)
    assert suggestion.status == AISuggestionStatus.FAILED
    assert suggestion.metadata["generation_error_code"] == "P2_OUTLINE_AUDIT_WRITE_FAILED"
    assert "P2_OUTLINE_AUDIT_WRITE_FAILED" not in suggestion.warning_codes
    assert jobs.get_job(launch.job_id).status == AIJobStatus.FAILED
    assert queued == []


def test_cancelled_outline_job_callback_does_not_call_planner_or_generate_suggestion(tmp_path: Path) -> None:
    planner = _Planner()
    suggestions = FileAISuggestionStore(tmp_path / "cancelled-entry-suggestions.json")
    jobs = _job_service(tmp_path)
    trace = _RequiredTrace()
    queued: list[callable] = []
    service = OutlineAssistService(
        planner_service=planner,
        ai_suggestion_repository=suggestions,
        ai_job_service=jobs,
        writing_asset_service=_Assets(),
        trace_service=trace,
        background_submitter=queued.append,
    )
    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="cancel-before-callback",
    )
    jobs.cancel_job(launch.job_id, reason="user_cancelled")

    queued.pop()()

    assert planner.calls == []
    assert suggestions.get(launch.suggestion_id).status == AISuggestionStatus.PENDING
    assert jobs.get_job(launch.job_id).status == AIJobStatus.CANCELLED
    assert [event["event_type"] for event in trace.events] == ["step_started"]


def test_outline_job_cancelled_during_planner_call_does_not_write_success_terminal_state(tmp_path: Path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "cancelled-terminal-suggestions.json")
    jobs = _job_service(tmp_path)
    trace = _RequiredTrace()
    queued: list[callable] = []

    class _CancellingPlanner(_Planner):
        job_id = ""

        def generate(self, **kwargs):
            result = super().generate(**kwargs)
            jobs.cancel_job(self.job_id, reason="user_cancelled")
            return result

    planner = _CancellingPlanner()
    service = OutlineAssistService(
        planner_service=planner,
        ai_suggestion_repository=suggestions,
        ai_job_service=jobs,
        writing_asset_service=_Assets(),
        trace_service=trace,
        background_submitter=queued.append,
    )
    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="cancel-during-generation",
    )
    planner.job_id = launch.job_id

    queued.pop()()

    assert len(planner.calls) == 1
    assert suggestions.get(launch.suggestion_id).status == AISuggestionStatus.PENDING
    assert jobs.get_job(launch.job_id).status == AIJobStatus.CANCELLED
    assert [event["event_type"] for event in trace.events] == ["step_started"]


def test_outline_job_cancelled_by_success_trace_does_not_commit_generated_or_leave_step_running(tmp_path: Path) -> None:
    suggestions = FileAISuggestionStore(tmp_path / "cancelled-by-success-trace-suggestions.json")
    jobs = _job_service(tmp_path)
    queued: list[callable] = []

    class _CancellingSuccessTrace(_RequiredTrace):
        job_id = ""

        def record_audit_event(self, **kwargs):
            event = super().record_audit_event(**kwargs)
            if kwargs.get("event_type") == "step_succeeded":
                jobs.cancel_job(self.job_id, reason="user_cancelled")
            return event

    trace = _CancellingSuccessTrace()
    service = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=jobs,
        writing_asset_service=_Assets(),
        trace_service=trace,
        background_submitter=queued.append,
    )
    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="cancel-from-success-trace",
    )
    trace.job_id = launch.job_id

    queued.pop()()

    assert suggestions.get(launch.suggestion_id).status == AISuggestionStatus.PENDING
    assert jobs.get_job(launch.job_id).status == AIJobStatus.CANCELLED
    step = jobs.get_job_steps(launch.job_id)[0]
    assert step.status == AIJobStepStatus.SKIPPED
    assert step.finished_at


def test_terminal_generation_trace_failure_never_completes_business_state(tmp_path: Path) -> None:
    class _TerminalTraceFailure(_RequiredTrace):
        def record_audit_event(self, **kwargs):
            if kwargs.get("event_type") == "step_succeeded":
                if kwargs.get("high_risk_user_action") is True:
                    raise OSError("critical trace write unavailable")
                return SimpleNamespace(fallback=True)
            return super().record_audit_event(**kwargs)

    suggestions = FileAISuggestionStore(tmp_path / "terminal-trace-suggestions.json")
    jobs = _job_service(tmp_path)
    queued: list[callable] = []
    service = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=jobs,
        writing_asset_service=_Assets(),
        trace_service=_TerminalTraceFailure(),
        background_submitter=queued.append,
    )
    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="terminal-trace-failure",
    )
    queued.pop()()

    suggestion = suggestions.get(launch.suggestion_id)
    assert suggestion.status == AISuggestionStatus.FAILED
    assert suggestion.metadata["generation_error_code"] == "P2_OUTLINE_AUDIT_WRITE_FAILED"
    assert suggestion.warning_codes == []
    assert jobs.get_job(launch.job_id).status == AIJobStatus.FAILED


def test_new_outline_node_cannot_inject_chapter_reference_in_validator_or_apply(tmp_path: Path) -> None:
    malicious_tree = [
        {
            "node_id": "11111111-1111-4111-8111-111111111111",
            "text": "伪造章节引用",
            "children": [],
            "chapter_ref": "chapter-evil",
        }
    ]
    output = {
        "proposed_content_text": "恶意结果",
        "proposed_content_tree_json": malicious_tree,
        "diff_summary": [],
        "polish_notes": [],
    }

    class _Router:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, request):
            self.calls += 1
            return SimpleNamespace(content=json.dumps(output, ensure_ascii=False))

    router = _Router()
    planner = _tested_outline_planner(router)
    with pytest.raises(ValueError, match="output_schema_invalid"):
        _generate_with_audit_scope(
            planner,
            suggestion_type=AISuggestionType.OUTLINE_POLISH,
            source_text="原大纲",
            target_content_tree_json=[],
            options={},
        )
    assert router.calls == 3

    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "conflicts.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="malicious-tree",
    )
    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    payload = dict(generated.payload)
    payload["proposed_content_tree_json"] = malicious_tree
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED, "payload": payload}))
    application = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=_RequiredTrace(),
    )
    with pytest.raises(ValueError, match="P2_OUTLINE_SUGGESTION_TYPE_UNSUPPORTED"):
        application.apply_suggestion(
            suggestion_id=launch.suggestion_id,
            caller_type="user_action",
            user_action=True,
            user_id="writer-1",
            idempotency_key="malicious-tree-apply",
            confirm_apply=True,
            target_revision=3,
        )
    assert assets.saved == []


def test_outline_node_contract_rejects_deleting_existing_unbound_node() -> None:
    target_tree = [
        {
            "node_id": "22222222-2222-4222-8222-222222222222",
            "text": "必须保留的节点",
            "children": [],
            "chapter_ref": None,
        }
    ]
    assert preserves_outline_node_contract(target_tree, []) is False


def test_writing_asset_expected_version_is_serialized_for_concurrent_outline_writes() -> None:
    initialize_database()
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("并发大纲", "作者")
    initial_service = build_writing_asset_service()
    initial_service.save_work_outline(work.id, content_text="初始大纲", content_tree_json=[], expected_version=1)
    services = [build_writing_asset_service(), build_writing_asset_service()]
    barrier = Barrier(2)
    result_lock = Lock()
    successes: list[int] = []
    errors: list[str] = []

    def save(index: int) -> None:
        barrier.wait()
        try:
            saved = services[index].save_work_outline(
                work.id,
                content_text=f"并发版本 {index}",
                content_tree_json=[],
                expected_version=1,
            )
            with result_lock:
                successes.append(saved.version)
        except ValueError as exc:
            with result_lock:
                errors.append(str(exc))

    threads = [Thread(target=save, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert successes == [2]
    assert errors == ["asset_version_conflict"]


@pytest.mark.parametrize("target_kind", ["work_outline", "chapter_outline"])
def test_first_outline_creation_allows_only_one_concurrent_absent_snapshot(target_kind: str) -> None:
    outline_repo = _SlowAbsentOutlineRepo()
    entity_repo = _EntityRepo(SimpleNamespace(id="entity-1", work_id="work-1"))
    service = WritingAssetService(
        work_repo=entity_repo,
        chapter_repo=entity_repo,
        work_outline_repo=outline_repo,
        chapter_outline_repo=outline_repo,
    )
    start = Barrier(2)
    result_lock = Lock()
    successes: list[int] = []
    errors: list[str] = []

    def save(index: int) -> None:
        start.wait()
        try:
            if target_kind == "work_outline":
                saved = service.save_work_outline(
                    "work-1",
                    content_text=f"首次作品大纲 {index}",
                    content_tree_json=[],
                    expected_version=1,
                )
            else:
                saved = service.save_chapter_outline(
                    "chapter-1",
                    content_text=f"首次章节大纲 {index}",
                    content_tree_json=[],
                    expected_version=1,
                )
            with result_lock:
                successes.append(saved.version)
        except ValueError as exc:
            with result_lock:
                errors.append(str(exc))

    threads = [Thread(target=save, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert successes == [1]
    assert errors == ["asset_version_conflict"]
    assert outline_repo.item.version == 1


@pytest.mark.parametrize("target_kind", ["work_outline", "chapter_outline"])
def test_first_outline_creation_without_expected_version_preserves_existing_save_semantics(
    target_kind: str,
) -> None:
    outline_repo = _SlowAbsentOutlineRepo()
    entity_repo = _EntityRepo(SimpleNamespace(id="entity-1", work_id="work-1"))
    service = WritingAssetService(
        work_repo=entity_repo,
        chapter_repo=entity_repo,
        work_outline_repo=outline_repo,
        chapter_outline_repo=outline_repo,
    )
    start = Barrier(2)
    result_lock = Lock()
    successes: list[int] = []
    errors: list[str] = []

    def save(index: int) -> None:
        start.wait()
        try:
            if target_kind == "work_outline":
                saved = service.save_work_outline(
                    "work-1",
                    content_text=f"无版本条件的作品大纲 {index}",
                    content_tree_json=[],
                )
            else:
                saved = service.save_chapter_outline(
                    "chapter-1",
                    content_text=f"无版本条件的章节大纲 {index}",
                    content_tree_json=[],
                )
            with result_lock:
                successes.append(saved.version)
        except ValueError as exc:
            with result_lock:
                errors.append(str(exc))

    threads = [Thread(target=save, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert sorted(successes) == [1, 2]
    assert errors == []
    assert outline_repo.item.version == 2


def test_final_generation_validation_failure_marks_suggestion_and_job_failed(tmp_path: Path) -> None:
    class _FailingPlanner:
        def generate(self, **kwargs):
            raise ValueError("output_schema_invalid")

    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    jobs = _job_service(tmp_path)
    queued: list[callable] = []
    service = OutlineAssistService(
        planner_service=_FailingPlanner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=jobs,
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text="作者可编辑的参考",
        caller_type="user_action",
        idempotency_key="generation-fails",
    )
    queued.pop()()

    assert suggestions.get(launch.suggestion_id).status == AISuggestionStatus.FAILED
    assert jobs.get_job(launch.job_id).status == AIJobStatus.FAILED
    assert assets.saved == []


def test_required_terminal_trace_failure_prevents_business_terminal_state(tmp_path: Path) -> None:
    class _TraceFailsOnSuccess(_RequiredTrace):
        def record_audit_event(self, **kwargs):
            if kwargs.get("event_type") == "step_succeeded":
                assert kwargs.get("high_risk_user_action") is True
                raise OSError("trace unavailable")
            return super().record_audit_event(**kwargs)

    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    jobs = _job_service(tmp_path)
    queued: list[callable] = []
    service = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=jobs,
        writing_asset_service=assets,
        trace_service=_TraceFailsOnSuccess(),
        background_submitter=queued.append,
    )
    launch = service.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="trace-failure",
    )
    queued.pop()()

    suggestion = suggestions.get(launch.suggestion_id)
    assert suggestion.status == AISuggestionStatus.FAILED
    assert suggestion.metadata["generation_error_code"] == "P2_OUTLINE_AUDIT_WRITE_FAILED"
    assert suggestion.warning_codes == []
    assert jobs.get_job(launch.job_id).status == AIJobStatus.FAILED
    assert assets.saved == []


def test_writing_task_suggestion_store_excludes_full_outline_prompt_and_context(tmp_path: Path) -> None:
    assets = _Assets()
    assets.chapter_outline = ChapterOutline(
        assets.chapter_outline.id,
        assets.chapter_outline.chapter_id,
        "SENSITIVE_FULL_CHAPTER_OUTLINE",
        [],
        5,
        assets.chapter_outline.created_at,
        assets.chapter_outline.updated_at,
    )
    plan = SimpleNamespace(
        chapter_plan_id="plan-safe-1",
        work_id="work-1",
        chapter_id="chapter-1",
        status=DirectionPlanStatus.CONFIRMED,
        stale_status="fresh",
        plan_summary="PROMPT_ONLY_PLAN_SUMMARY",
        plan_items=[],
        direction_proposal_id="direction-safe-ref",
        selected_option_id="option-safe-ref",
    )

    class _Plans:
        def list_by_work(self, work_id: str, chapter_id: str = ""):
            return [plan]

    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    queued: list[callable] = []
    planner = _Planner()
    service = OutlineAssistService(
        planner_service=planner,
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        chapter_plan_repository=_Plans(),
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = service.start_writing_task_suggestion(
        work_id="work-1",
        chapter_id="chapter-1",
        target_revision=5,
        caller_type="user_action",
        idempotency_key="writing-task-safe-store",
    )
    queued.pop()()

    stored_text = (tmp_path / "suggestions.json").read_text(encoding="utf-8")
    assert "SENSITIVE_FULL_CHAPTER_OUTLINE" not in stored_text
    assert "PROMPT_ONLY_PLAN_SUMMARY" not in stored_text
    assert "ContextPack" not in stored_text
    payload = suggestions.get(launch.suggestion_id).payload
    assert "target_content_text" not in payload
    assert "target_content_tree_json" not in payload
    assert payload["chapter_plan_id"] == "plan-safe-1"
    assert planner.calls[0]["options"]["confirmed_plan_summary"] == "PROMPT_ONLY_PLAN_SUMMARY"

    leaked_text = "SENSITIVE_FULL_CHAPTER_OUTLINE" * 100

    class _LeakingRouter:
        def generate(self, request):
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "task_title": "本章要点",
                        "writing_goal": "推进目标",
                        "must_include": [],
                        "must_not_include": [],
                        "target_word_count": 2000,
                        "tone_guidance": "",
                        "required_beats": [],
                        "context_summary": leaked_text,
                    },
                    ensure_ascii=False,
                )
            )

    leak_store = FileAISuggestionStore(tmp_path / "leak-suggestions.json")
    leak_queue: list[callable] = []
    leak_service = OutlineAssistService(
        planner_service=_tested_outline_planner(_LeakingRouter()),
        ai_suggestion_repository=leak_store,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        chapter_plan_repository=_Plans(),
        trace_service=_RequiredTrace(),
        background_submitter=leak_queue.append,
    )
    leak_launch = leak_service.start_writing_task_suggestion(
        work_id="work-1",
        chapter_id="chapter-1",
        target_revision=5,
        caller_type="user_action",
        idempotency_key="writing-task-leak-blocked",
    )
    leak_queue.pop()()
    assert leak_store.get(leak_launch.suggestion_id).status == AISuggestionStatus.FAILED
    assert leaked_text not in (tmp_path / "leak-suggestions.json").read_text(encoding="utf-8")


def test_outline_apply_requires_accept_and_rejects_changed_target_tree(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "outline_suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "outline_conflicts.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="polish-apply",
    )
    queued.pop()()
    application = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=_RequiredTrace(),
    )

    with pytest.raises(ValueError, match="P2_OUTLINE_SUGGESTION_NOT_ACCEPTED"):
        application.apply_suggestion(
            suggestion_id=launch.suggestion_id,
            caller_type="user_action",
            user_action=True,
            user_id="writer-1",
            idempotency_key="apply-1",
            confirm_apply=True,
            target_revision=3,
        )
    assert assets.saved == []

    generated = suggestions.get(launch.suggestion_id)
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    assets.work_outline = WorkOutline(
        assets.work_outline.id,
        assets.work_outline.work_id,
        assets.work_outline.content_text,
        {},
        3,
        assets.work_outline.created_at,
        datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="P2_OUTLINE_TARGET_CONFLICT"):
        application.apply_suggestion(
            suggestion_id=launch.suggestion_id,
            caller_type="user_action",
            user_action=True,
            user_id="writer-1",
            idempotency_key="apply-2",
            confirm_apply=True,
            target_revision=3,
        )
    assert assets.saved == []
    records = conflicts.list_records(work_id="work-1")
    assert records[0].status == ConflictRecordStatus.DETECTED
    assert records[0].severity.value == "blocking"


def test_outline_apply_without_required_trace_is_fail_safe_before_formal_write(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "apply-audit-suggestions.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="apply-audit-generation",
    )
    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    application = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(FileConflictGuardStore(tmp_path / "apply-audit-conflicts.json")),
        trace_service=None,
    )

    with pytest.raises(ValueError, match="P2_OUTLINE_AUDIT_WRITE_FAILED"):
        application.apply_suggestion(
            suggestion_id=launch.suggestion_id,
            caller_type="user_action",
            user_action=True,
            user_id="writer-1",
            idempotency_key="apply-audit-key",
            confirm_apply=True,
            target_revision=3,
        )

    assert assets.saved == []
    assert assets.work_outline.version == 3


def test_outline_apply_writes_once_and_resolves_guard_record(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "outline_suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "outline_conflicts.json")
    trace_store = FileAgentTraceStore(tmp_path / "outline_traces.json")
    trace_service = AgentTraceService(repository=trace_store)
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=trace_service,
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="polish-ok",
    )
    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    application = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=trace_service,
    )

    gate_request = {
        "suggestion_id": launch.suggestion_id,
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "apply-ok",
        "confirm_apply": True,
        "target_revision": 3,
    }
    for update, code in [
        ({"caller_type": "agent"}, "P2_CALLER_FORBIDDEN"),
        ({"user_action": False}, "P2_USER_ACTION_REQUIRED"),
        ({"idempotency_key": ""}, "P2_IDEMPOTENCY_KEY_REQUIRED"),
        ({"confirm_apply": False}, "P2_OUTLINE_APPLY_CONFIRMATION_REQUIRED"),
    ]:
        with pytest.raises(ValueError, match=code):
            application.apply_suggestion(**{**gate_request, **update})
    assert assets.saved == []

    first = application.apply_suggestion(
        suggestion_id=launch.suggestion_id,
        caller_type="user_action",
        user_action=True,
        user_id="writer-1",
        idempotency_key="apply-ok",
        confirm_apply=True,
        target_revision=3,
    )
    second = application.apply_suggestion(
        suggestion_id=launch.suggestion_id,
        caller_type="user_action",
        user_action=True,
        user_id="writer-1",
        idempotency_key="apply-ok",
        confirm_apply=True,
        target_revision=3,
    )

    assert first == second
    assert first.new_version == 4
    assert assets.saved == [("work_outline", "新的作品大纲", 3)]
    assert assets.expected_content_hashes == [outline_content_hash("旧的作品大纲", [])]
    trace_audit_text = (tmp_path / "outline_traces.json").read_text(encoding="utf-8")
    assert "旧的作品大纲" not in trace_audit_text
    assert "新的作品大纲" not in trace_audit_text
    trace_events = trace_store.list_events(generated.trace_id)
    assert {event.event_type.value for event in trace_events} >= {
        "step_started",
        "step_succeeded",
        "user_decision_recorded",
        "checkpoint_saved",
    }
    assert suggestions.get(launch.suggestion_id).status == AISuggestionStatus.CONVERTED
    assert conflicts.list_records(work_id="work-1")[0].status == ConflictRecordStatus.RESOLVED

    duplicate = generated.model_copy(
        update={
            "suggestion_id": "ais-other-request",
            "status": AISuggestionStatus.ACCEPTED,
            "metadata": {
                key: value
                for key, value in generated.metadata.items()
                if key not in {"apply_idempotency_key_hash", "apply_request_hash", "apply_result"}
            },
        }
    )
    suggestions.save(duplicate)
    with pytest.raises(ValueError, match="P2_IDEMPOTENCY_CONFLICT"):
        application.apply_suggestion(
            suggestion_id=duplicate.suggestion_id,
            caller_type="user_action",
            user_action=True,
            user_id="writer-1",
            idempotency_key="apply-ok",
            confirm_apply=True,
            target_revision=3,
        )
    assert assets.saved == [("work_outline", "新的作品大纲", 3)]


def test_selection_suggestion_cannot_apply_to_formal_outline(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "conflicts.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="selection",
        target_id=None,
        target_revision=None,
        selected_text="自由选择的一段大纲",
        caller_type="user_action",
        idempotency_key="selection-1",
    )
    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    application = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=_RequiredTrace(),
    )

    with pytest.raises(ValueError, match="P2_OUTLINE_SUGGESTION_TYPE_UNSUPPORTED"):
        application.apply_suggestion(
            suggestion_id=launch.suggestion_id,
            caller_type="user_action",
            user_action=True,
            user_id="writer-1",
            idempotency_key="selection-apply",
            confirm_apply=True,
            target_revision=0,
        )
    assert assets.saved == []


def test_existing_blocking_outline_conflict_requires_review_before_write(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "conflicts.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="blocking-conflict",
    )
    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    conflicts.save_record(
        ConflictGuardRecord(
            record_id="cgr-existing-blocking",
            work_id="work-1",
            chapter_id="",
            candidate_draft_id="",
            candidate_version_id="",
            source_type="outline_consistency_check",
            source_ref_id="external-check",
            target_type="work_outline",
            target_ref_id="work-1",
            conflict_type=ConflictType.CHARACTER_CONFLICT,
            severity=ConflictSeverity.BLOCKING,
            status=ConflictRecordStatus.DETECTED,
            title="人物设定冲突",
        )
    )
    application = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=_RequiredTrace(),
    )
    with pytest.raises(OutlineConflictReviewRequired, match="P2_OUTLINE_CONFLICT_REVIEW_REQUIRED") as exc_info:
        application.apply_suggestion(
            suggestion_id=launch.suggestion_id,
            caller_type="user_action",
            user_action=True,
            user_id="writer-1",
            idempotency_key="blocking-conflict-apply",
            confirm_apply=True,
            target_revision=3,
        )
    assert exc_info.value.record_refs == ["cgr-existing-blocking"]
    assert assets.saved == []


def test_chapter_outline_apply_uses_chapter_version_and_guard(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "conflicts.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_chapter_outline(
        work_id="work-1",
        target_kind="chapter_outline",
        target_id="chapter-1",
        target_revision=5,
        chapter_goal="找到父亲留下的线索",
        caller_type="user_action",
        idempotency_key="chapter-outline-1",
    )
    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    application = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=_RequiredTrace(),
    )
    result = application.apply_suggestion(
        suggestion_id=launch.suggestion_id,
        caller_type="user_action",
        user_action=True,
        user_id="writer-1",
        idempotency_key="chapter-apply-1",
        confirm_apply=True,
        target_revision=5,
    )

    assert result.target_kind == "chapter_outline"
    assert result.new_version == 6
    assert assets.saved == [("chapter_outline", "新的作品大纲", 5)]
    assert assets.expected_content_hashes == [outline_content_hash("旧的章节大纲", [])]
    assert conflicts.list_records(work_id="work-1")[0].status == ConflictRecordStatus.RESOLVED


def test_post_write_guard_resolution_failure_reports_real_saved_result(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "conflicts.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="polish-resolution-failure",
    )
    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    service = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_ResolveFailingGuard(_conflict_guard(conflicts)),
        trace_service=_RequiredTrace(),
    )

    result = service.apply_suggestion(
        suggestion_id=launch.suggestion_id,
        caller_type="user_action",
        user_action=True,
        user_id="writer-1",
        idempotency_key="apply-resolution-failure",
        confirm_apply=True,
        target_revision=3,
    )

    stored = suggestions.get(launch.suggestion_id)
    assert result.success is True
    assert result.new_version == 4
    assert assets.work_outline.version == 4
    assert stored.status == AISuggestionStatus.CONVERTED
    assert stored.metadata["apply_result"]["new_version"] == 4
    assert stored.metadata["conflict_guard_resolution_pending"] is True
    assert conflicts.list_records(work_id="work-1")[0].status == ConflictRecordStatus.ACKNOWLEDGED


def test_checkpoint_trace_failure_keeps_guard_pending_until_same_key_replay(tmp_path: Path) -> None:
    assets = _Assets()
    suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "conflicts.json")
    trace = _CheckpointFailsOnceTrace()
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=trace,
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="polish-checkpoint-failure",
    )
    queued.pop()()
    generated = suggestions.get(launch.suggestion_id)
    suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    service = OutlineApplicationService(
        ai_suggestion_repository=suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=trace,
    )
    request = {
        "suggestion_id": launch.suggestion_id,
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "apply-checkpoint-failure",
        "confirm_apply": True,
        "target_revision": 3,
    }

    first = service.apply_suggestion(**request)
    pending = suggestions.get(launch.suggestion_id)

    assert first.success is True
    assert first.new_version == 4
    assert pending.metadata["apply_result"]["new_version"] == 4
    assert pending.metadata["conflict_guard_resolution_pending"] is True
    assert conflicts.list_records(work_id="work-1")[0].status == ConflictRecordStatus.ACKNOWLEDGED
    assert [event["event_type"] for event in trace.events].count("checkpoint_saved") == 0
    assert len(assets.saved) == 1

    proposed_hash = outline_content_hash(
        str(pending.payload["proposed_content_text"]),
        pending.payload["proposed_content_tree_json"],
    )
    assets.save_work_outline(
        "work-1",
        content_text="later independent outline update",
        content_tree_json=[],
        expected_version=4,
    )
    writes_before_replay = len(assets.saved)

    replay = service.apply_suggestion(**request)
    resolved = suggestions.get(launch.suggestion_id)
    checkpoint_event = next(event for event in trace.events if event["event_type"] == "checkpoint_saved")

    assert replay == first
    assert resolved.metadata["conflict_guard_resolution_pending"] is False
    assert conflicts.list_records(work_id="work-1")[0].status == ConflictRecordStatus.RESOLVED
    assert [event["event_type"] for event in trace.events].count("checkpoint_saved") == 1
    assert checkpoint_event["payload_digest"]["target_content_hash"] == proposed_hash
    assert checkpoint_event["payload_digest"]["target_revision"] == first.new_version
    assert checkpoint_event["payload_digest"]["result_ref"] == first.result_ref
    assert len(assets.saved) == writes_before_replay
    assert assets.work_outline.version == 5


def test_post_write_suggestion_failure_is_recovered_by_same_key_replay(tmp_path: Path) -> None:
    assets = _Assets()
    stored_suggestions = FileAISuggestionStore(tmp_path / "suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "conflicts.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=stored_suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="recoverable-generation",
    )
    queued.pop()()
    generated = stored_suggestions.get(launch.suggestion_id)
    stored_suggestions.save(generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED}))
    failing_store = _FailCompletedSuggestionStore(stored_suggestions, failures=2)
    service = OutlineApplicationService(
        ai_suggestion_repository=failing_store,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=_RequiredTrace(),
    )
    request = {
        "suggestion_id": launch.suggestion_id,
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "recoverable-apply",
        "confirm_apply": True,
        "target_revision": 3,
    }

    first = service.apply_suggestion(**request)
    intermediate = stored_suggestions.get(launch.suggestion_id)
    assert first.new_version == 4
    assert intermediate.status == AISuggestionStatus.ACCEPTED
    assert intermediate.metadata["apply_state"] == "writing"
    assert conflicts.list_records(work_id="work-1")[0].status == ConflictRecordStatus.ACKNOWLEDGED

    replay = service.apply_suggestion(**request)
    recovered = stored_suggestions.get(launch.suggestion_id)
    assert replay == first
    assert recovered.status == AISuggestionStatus.CONVERTED
    assert recovered.metadata["apply_result"]["new_version"] == 4
    assert recovered.metadata["conflict_guard_resolution_pending"] is False
    assert conflicts.list_records(work_id="work-1")[0].status == ConflictRecordStatus.RESOLVED
    assert assets.saved == [("work_outline", "新的作品大纲", 3)]


def test_first_v1_outline_save_failure_is_recovered_without_incrementing_initial_version(tmp_path: Path) -> None:
    initialize_database()
    work = WorkService(work_repo=WorkRepo(), chapter_repo=ChapterRepo()).create_work("首次大纲恢复", "作者")
    assets = build_writing_asset_service()
    stored_suggestions = FileAISuggestionStore(tmp_path / "first-save-suggestions.json")
    target_hash = outline_content_hash("", [])
    suggestion = stored_suggestions.save(
        AISuggestion(
            suggestion_id="ais-first-outline-save",
            work_id=work.id,
            chapter_id="",
            source=AISuggestionSource(source_type="outline_assist", source_ref_id="ais-first-outline-save"),
            target=AISuggestionTarget(
                target_type="work_outline",
                target_ref_id=work.id,
                target_scope="formal_asset",
                target_snapshot_ref="1",
            ),
            suggestion_type=AISuggestionType.OUTLINE_POLISH,
            severity=AISuggestionSeverity.MEDIUM,
            priority=AISuggestionPriority.MEDIUM,
            title="把这段写顺",
            status=AISuggestionStatus.ACCEPTED,
            action=AISuggestionAction(
                action_type=AISuggestionActionType.APPLY_OUTLINE,
                requires_user_action=True,
                action_status="pending",
            ),
            payload={
                "target_kind": "work_outline",
                "target_id": work.id,
                "target_revision": 1,
                "target_content_hash": target_hash,
                "target_content_text": "",
                "target_content_tree_json": [],
                "proposed_content_text": "首次正式大纲",
                "proposed_content_tree_json": [],
                "diff_summary": ["建立作品主线"],
                "polish_notes": [],
            },
            metadata={"target_content_hash": target_hash},
            created_at="2026-07-11T00:00:00+00:00",
            updated_at="2026-07-11T00:00:00+00:00",
        )
    )
    conflicts = FileConflictGuardStore(tmp_path / "first-save-conflicts.json")
    failing_store = _FailCompletedSuggestionStore(stored_suggestions, failures=2)
    service = OutlineApplicationService(
        ai_suggestion_repository=failing_store,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=_RequiredTrace(),
    )
    request = {
        "suggestion_id": suggestion.suggestion_id,
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "first-outline-apply",
        "confirm_apply": True,
        "target_revision": 1,
    }

    first = service.apply_suggestion(**request)
    assert first.previous_version == 1
    assert first.new_version == 1
    assert assets.get_work_outline(work.id).version == 1
    checkpoint = stored_suggestions.get(suggestion.suggestion_id).metadata
    assert checkpoint["apply_state"] == "writing"
    assert checkpoint["target_was_persisted"] is False
    assert checkpoint["expected_post_write_version"] == 1

    replay = service.apply_suggestion(**request)
    recovered = stored_suggestions.get(suggestion.suggestion_id)
    assert replay == first
    assert recovered.status == AISuggestionStatus.CONVERTED
    assert recovered.metadata["apply_result"]["new_version"] == 1
    assert assets.get_work_outline(work.id).content_text == "首次正式大纲"
    assert assets.get_work_outline(work.id).version == 1


def test_same_version_noop_writing_replay_performs_the_missing_formal_save(tmp_path: Path) -> None:
    assets = _FailFirstFormalSaveAssets()
    stored_suggestions = FileAISuggestionStore(tmp_path / "noop-replay-suggestions.json")
    conflicts = FileConflictGuardStore(tmp_path / "noop-replay-conflicts.json")
    queued: list[callable] = []
    assist = OutlineAssistService(
        planner_service=_Planner(),
        ai_suggestion_repository=stored_suggestions,
        ai_job_service=_job_service(tmp_path),
        writing_asset_service=assets,
        trace_service=_RequiredTrace(),
        background_submitter=queued.append,
    )
    launch = assist.start_polish(
        work_id="work-1",
        target_kind="work_outline",
        target_id="work-1",
        target_revision=3,
        selected_text=None,
        caller_type="user_action",
        idempotency_key="noop-generation",
    )
    queued.pop()()
    generated = stored_suggestions.get(launch.suggestion_id)
    payload = dict(generated.payload)
    payload["proposed_content_text"] = payload["target_content_text"]
    payload["proposed_content_tree_json"] = payload["target_content_tree_json"]
    stored_suggestions.save(
        generated.model_copy(update={"status": AISuggestionStatus.ACCEPTED, "payload": payload})
    )
    service = OutlineApplicationService(
        ai_suggestion_repository=stored_suggestions,
        writing_asset_service=assets,
        conflict_guard_service=_conflict_guard(conflicts),
        trace_service=_RequiredTrace(),
    )
    request = {
        "suggestion_id": launch.suggestion_id,
        "caller_type": "user_action",
        "user_action": True,
        "user_id": "writer-1",
        "idempotency_key": "noop-apply",
        "confirm_apply": True,
        "target_revision": 3,
    }

    with pytest.raises(OSError, match="formal asset save did not happen"):
        service.apply_suggestion(**request)
    interrupted = stored_suggestions.get(launch.suggestion_id)
    assert interrupted.status == AISuggestionStatus.ACCEPTED
    assert interrupted.metadata["apply_state"] == "writing"
    assert interrupted.metadata["target_was_persisted"] is True
    assert interrupted.metadata["expected_post_write_version"] == 4
    assert assets.work_outline.version == 3
    assert assets.saved == []

    replay = service.apply_suggestion(**request)
    recovered = stored_suggestions.get(launch.suggestion_id)
    assert replay.previous_version == 3
    assert replay.new_version == 4
    assert assets.saved == [("work_outline", "旧的作品大纲", 3)]
    assert assets.work_outline.version == 4
    assert recovered.status == AISuggestionStatus.CONVERTED
