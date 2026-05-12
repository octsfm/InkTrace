from __future__ import annotations

import os
from pathlib import Path


DB_PATH = os.getenv("INKTRACE_DB_PATH", str(Path("data") / "inktrace.db"))
CHROMA_DIR = os.getenv("INKTRACE_CHROMA_DIR", str(Path("data") / "chroma"))


def warmup_singletons_for_startup() -> None:
    return None

from functools import lru_cache

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.ai_review_service import AIReviewApplicationService
from application.services.ai.ai_settings_service import AISettingsService
from application.services.ai.candidate_review_service import CandidateReviewService
from application.services.ai.continuation_workflow import MinimalContinuationWorkflow
from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.ai.model_router import ModelRouter
from application.services.ai.provider_registry import ProviderRegistry
from application.services.ai.quick_trial_service import QuickTrialApplicationService
from application.services.ai.security import SettingsCipher
from infrastructure.ai.providers.fake_provider import FakeLLMProvider
from infrastructure.ai.providers.fake_reviewer import FakeReviewer
from infrastructure.ai.providers.fake_writer import FakeWriter
from infrastructure.database.repositories.ai.file_ai_review_store import FileAIReviewStore
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_ai_settings_store import FileAISettingsStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo


@lru_cache(maxsize=1)
def get_ai_settings_repository() -> FileAISettingsStore:
    return FileAISettingsStore()


@lru_cache(maxsize=1)
def get_ai_job_store() -> FileAIJobStore:
    return FileAIJobStore()


@lru_cache(maxsize=1)
def get_initialization_repository() -> FileInitializationStore:
    return FileInitializationStore()


@lru_cache(maxsize=1)
def get_story_memory_repository() -> FileStoryMemoryStore:
    return FileStoryMemoryStore()


@lru_cache(maxsize=1)
def get_story_state_repository() -> FileStoryStateStore:
    return FileStoryStateStore()


@lru_cache(maxsize=1)
def get_context_pack_repository() -> FileContextPackStore:
    return FileContextPackStore()


@lru_cache(maxsize=1)
def get_candidate_draft_repository() -> FileCandidateDraftStore:
    return FileCandidateDraftStore()


@lru_cache(maxsize=1)
def get_ai_review_repository() -> FileAIReviewStore:
    return FileAIReviewStore()


@lru_cache(maxsize=1)
def get_llm_call_log_repository() -> FileLLMCallLogStore:
    return FileLLMCallLogStore()


@lru_cache(maxsize=1)
def get_settings_cipher() -> SettingsCipher:
    return SettingsCipher()


@lru_cache(maxsize=1)
def get_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(FakeLLMProvider())
    return registry


@lru_cache(maxsize=1)
def get_work_service() -> WorkService:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    return WorkService(work_repo=work_repo, chapter_repo=chapter_repo)


@lru_cache(maxsize=1)
def get_chapter_service() -> ChapterService:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    return ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)


@lru_cache(maxsize=1)
def get_model_router() -> ModelRouter:
    return ModelRouter(
        settings_repository=get_ai_settings_repository(),
        provider_registry=get_provider_registry(),
    )


@lru_cache(maxsize=1)
def get_ai_settings_service() -> AISettingsService:
    return AISettingsService(
        settings_repository=get_ai_settings_repository(),
        model_router=get_model_router(),
        settings_cipher=get_settings_cipher(),
    )


@lru_cache(maxsize=1)
def get_ai_job_service() -> AIJobService:
    store = get_ai_job_store()
    return AIJobService(
        job_repository=store,
        step_repository=store,
        attempt_repository=store,
    )


@lru_cache(maxsize=1)
def get_initialization_service() -> InitializationApplicationService:
    store = get_ai_job_store()
    return InitializationApplicationService(
        work_service=get_work_service(),
        chapter_service=get_chapter_service(),
        job_repository=store,
        step_repository=store,
        attempt_repository=store,
        initialization_repository=get_initialization_repository(),
        story_memory_repository=get_story_memory_repository(),
        story_state_repository=get_story_state_repository(),
    )


@lru_cache(maxsize=1)
def get_context_pack_service() -> ContextPackService:
    return ContextPackService(
        chapter_service=get_chapter_service(),
        initialization_repository=get_initialization_repository(),
        story_memory_repository=get_story_memory_repository(),
        story_state_repository=get_story_state_repository(),
        context_pack_repository=get_context_pack_repository(),
    )


@lru_cache(maxsize=1)
def get_quick_trial_service() -> QuickTrialApplicationService:
    return QuickTrialApplicationService(
        settings_repository=get_ai_settings_repository(),
        model_router=get_model_router(),
        provider_registry=get_provider_registry(),
        llm_call_log_repository=get_llm_call_log_repository(),
    )


@lru_cache(maxsize=1)
def get_continuation_workflow() -> MinimalContinuationWorkflow:
    store = get_ai_job_store()
    return MinimalContinuationWorkflow(
        work_service=get_work_service(),
        chapter_service=get_chapter_service(),
        context_pack_service=get_context_pack_service(),
        candidate_draft_repository=get_candidate_draft_repository(),
        writer=FakeWriter(),
        job_repository=store,
        step_repository=store,
        attempt_repository=store,
    )


@lru_cache(maxsize=1)
def get_candidate_review_service() -> CandidateReviewService:
    return CandidateReviewService(
        candidate_draft_repository=get_candidate_draft_repository(),
        chapter_service=get_chapter_service(),
        initialization_service=get_initialization_service(),
    )


@lru_cache(maxsize=1)
def get_ai_review_service() -> AIReviewApplicationService:
    return AIReviewApplicationService(
        work_service=get_work_service(),
        chapter_service=get_chapter_service(),
        candidate_draft_repository=get_candidate_draft_repository(),
        ai_review_repository=get_ai_review_repository(),
        reviewer=FakeReviewer(),
        initialization_repository=get_initialization_repository(),
        story_memory_repository=get_story_memory_repository(),
        story_state_repository=get_story_state_repository(),
    )
