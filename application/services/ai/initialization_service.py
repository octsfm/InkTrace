from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.story_memory_service import StoryMemoryService
from application.services.ai.story_state_service import StoryStateService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    AIJob,
    ChapterAnalysisResult,
    ChapterAnalysisStatus,
    InitializationCompletionStatus,
    InitializationRecord,
    InitializationStatus,
    OutlineAnalysisResult,
)
from domain.repositories.ai.ai_job_attempt_repository import AIJobAttemptRepository
from domain.repositories.ai.ai_job_repository import AIJobRepository
from domain.repositories.ai.ai_job_step_repository import AIJobStepRepository
from domain.repositories.ai.initialization_repository import InitializationRepository
from domain.repositories.ai.story_memory_repository import StoryMemoryRepository
from domain.repositories.ai.story_state_repository import StoryStateRepository


class InitializationApplicationService:
    def __init__(
        self,
        *,
        work_service: WorkService,
        chapter_service: ChapterService,
        job_repository: AIJobRepository,
        step_repository: AIJobStepRepository,
        attempt_repository: AIJobAttemptRepository,
        initialization_repository: InitializationRepository,
        story_memory_repository: StoryMemoryRepository,
        story_state_repository: StoryStateRepository,
    ) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._job_service = AIJobService(
            job_repository=job_repository,
            step_repository=step_repository,
            attempt_repository=attempt_repository,
        )
        self._initialization_repository = initialization_repository
        self._story_memory_service = StoryMemoryService(story_memory_repository)
        self._story_state_service = StoryStateService(story_state_repository)

    def start_initialization(self, work_id: str, *, created_by: str, auto_run: bool = True) -> InitializationRecord:
        self._work_service.get_work(work_id)
        latest = self._initialization_repository.get_latest_by_work(work_id)
        if latest and latest.status in {
            InitializationStatus.OUTLINE_ANALYZING,
            InitializationStatus.MANUSCRIPT_ANALYZING,
            InitializationStatus.MEMORY_BUILDING,
            InitializationStatus.STATE_BUILDING,
        }:
            raise ValueError("initialization_in_progress")

        chapters = self._chapter_service.list_chapters(work_id)
        now = self._now()
        job = self._job_service.create_job(
            job_type="ai_initialization",
            work_id=work_id,
            steps=[
                {"step_type": "outline_analysis", "step_name": "Outline Analysis"},
                {"step_type": "manuscript_analysis", "step_name": "Manuscript Analysis"},
                {"step_type": "build_story_memory", "step_name": "Build Story Memory"},
                {"step_type": "build_story_state", "step_name": "Build Story State"},
                {"step_type": "finalize_initialization", "step_name": "Finalize Initialization"},
            ],
            created_by=created_by,
            payload={"work_id": work_id, "purpose": "initialization"},
        )
        initialization = InitializationRecord(
            initialization_id=f"init_{uuid.uuid4().hex[:12]}",
            work_id=work_id,
            job_id=job.job_id,
            status=InitializationStatus.NOT_STARTED if not auto_run else InitializationStatus.OUTLINE_ANALYZING,
            completion_status=InitializationCompletionStatus.FAILED,
            total_confirmed_chapter_count=len(chapters),
            source_chapter_versions={chapter.id.value: chapter.version for chapter in chapters},
            created_at=now,
            updated_at=now,
        )
        self._initialization_repository.save(initialization)
        return self.run_initialization(initialization.initialization_id) if auto_run else initialization

    def run_initialization(self, initialization_id: str) -> InitializationRecord:
        initialization = self._initialization_repository.get(initialization_id)
        job = self._job_service.get_job(initialization.job_id)
        if job.status.value == "cancelled":
            return self._save_initialization(
                initialization.model_copy(
                    update={
                        "status": InitializationStatus.CANCELLED,
                        "completion_status": InitializationCompletionStatus.IGNORED,
                        "updated_at": self._now(),
                    }
                )
            )

        self._job_service.start_job(initialization.job_id)
        work = self._work_service.get_work(initialization.work_id)
        chapters = self._chapter_service.list_chapters(initialization.work_id)
        step_ids = self._get_step_ids(initialization.job_id)

        self._job_service.mark_step_running(initialization.job_id, step_ids["outline_analysis"])
        outline_analysis = self._analyze_outline(work.id, work.title, chapters)
        self._job_service.mark_step_completed(initialization.job_id, step_ids["outline_analysis"], summary="outline analyzed")

        self._save_initialization(
            initialization.model_copy(
                update={
                    "status": InitializationStatus.MANUSCRIPT_ANALYZING,
                    "outline_analysis": outline_analysis,
                    "updated_at": self._now(),
                }
            )
        )

        self._job_service.mark_step_running(initialization.job_id, step_ids["manuscript_analysis"])
        chapter_results = [self._analyze_chapter(chapter.id.value, chapter.title, chapter.content, chapter.version) for chapter in chapters]
        self._job_service.mark_step_completed(initialization.job_id, step_ids["manuscript_analysis"], summary="chapters analyzed")

        return self.finalize_initialization(initialization_id, chapter_results=chapter_results)

    def finalize_initialization(
        self,
        initialization_id: str,
        *,
        chapter_results: list[ChapterAnalysisResult] | None = None,
    ) -> InitializationRecord:
        initialization = self._initialization_repository.get(initialization_id)
        job = self._job_service.get_job(initialization.job_id)
        if job.status.value == "cancelled":
            return self._save_initialization(
                initialization.model_copy(
                    update={
                        "status": InitializationStatus.CANCELLED,
                        "completion_status": InitializationCompletionStatus.IGNORED,
                        "updated_at": self._now(),
                    }
                )
            )

        step_ids = self._get_step_ids(initialization.job_id)
        self._job_service.mark_step_running(initialization.job_id, step_ids["finalize_initialization"])
        results = chapter_results if chapter_results is not None else initialization.chapter_results
        successful = [item for item in results if item.status == ChapterAnalysisStatus.SUCCEEDED and not item.is_empty]
        empty_count = sum(1 for item in results if item.status == ChapterAnalysisStatus.EMPTY or item.is_empty)
        failed_count = sum(1 for item in results if item.status == ChapterAnalysisStatus.FAILED)

        update_base = {
            "chapter_results": results,
            "analyzed_chapter_count": len(successful),
            "empty_chapter_count": empty_count,
            "failed_chapter_count": failed_count,
            "updated_at": self._now(),
        }

        if len(successful) == 0:
            self._job_service.mark_step_failed(
                initialization.job_id,
                step_ids["finalize_initialization"],
                error_code="work_empty",
                error_message="no effective confirmed chapters",
            )
            self._job_service.mark_job_failed(initialization.job_id, error_code="work_empty", error_message="no effective confirmed chapters")
            return self._save_initialization(
                initialization.model_copy(
                    update={
                        **update_base,
                        "status": InitializationStatus.FAILED,
                        "completion_status": InitializationCompletionStatus.FAILED,
                        "error_code": "work_empty",
                        "error_message": "no effective confirmed chapters",
                        "finalized_at": self._now(),
                    }
                )
            )

        self._job_service.mark_step_running(initialization.job_id, step_ids["build_story_memory"])
        story_memory = self._story_memory_service.build_snapshot(
            initialization=initialization.model_copy(update=update_base),
            outline_analysis=initialization.outline_analysis or OutlineAnalysisResult(work_id=initialization.work_id),
            chapter_results=results,
        )
        self._job_service.mark_step_completed(initialization.job_id, step_ids["build_story_memory"], summary="story memory built")

        self._job_service.mark_step_running(initialization.job_id, step_ids["build_story_state"])
        story_state = self._story_state_service.build_analysis_baseline(
            initialization=initialization.model_copy(update=update_base),
            story_memory_snapshot=story_memory,
            chapter_results=results,
        )
        self._job_service.mark_step_completed(initialization.job_id, step_ids["build_story_state"], summary="story state built")

        if empty_count > 0 or failed_count > 0:
            self._job_service.mark_job_partial_success(
                initialization.job_id,
                result_summary={"analyzed_chapter_count": len(successful), "empty_chapter_count": empty_count, "failed_chapter_count": failed_count},
            )
            completion_status = InitializationCompletionStatus.PARTIAL_SUCCESS
            partial_reason = "chapter_empty_or_failed_detected"
        else:
            self._job_service.mark_job_completed(
                initialization.job_id,
                result_summary={"analyzed_chapter_count": len(successful)},
                result_ref=story_memory.snapshot_id,
            )
            completion_status = InitializationCompletionStatus.SUCCEEDED
            partial_reason = ""

        self._job_service.mark_step_completed(initialization.job_id, step_ids["finalize_initialization"], summary="initialization finalized")
        return self._save_initialization(
            initialization.model_copy(
                update={
                    **update_base,
                    "status": InitializationStatus.COMPLETED,
                    "completion_status": completion_status,
                    "partial_success_reason": partial_reason,
                    "story_memory_snapshot_id": story_memory.snapshot_id,
                    "story_state_snapshot_id": story_state.story_state_id,
                    "finalized_at": self._now(),
                    "error_code": "",
                    "error_message": "",
                }
            )
        )

    def get_initialization(self, initialization_id: str) -> InitializationRecord:
        return self._initialization_repository.get(initialization_id)

    def get_latest_initialization(self, work_id: str) -> InitializationRecord | None:
        return self._initialization_repository.get_latest_by_work(work_id)

    def get_latest_story_memory(self, work_id: str):
        return self._story_memory_service.get_latest_snapshot_by_work(work_id)

    def get_latest_story_state(self, work_id: str):
        return self._story_state_service.get_latest_analysis_baseline_by_work(work_id)

    def get_job(self, job_id: str) -> AIJob:
        return self._job_service.get_job(job_id)

    def cancel_job(self, job_id: str, *, reason: str) -> AIJob:
        job = self._job_service.cancel_job(job_id, reason=reason)
        initialization = self._initialization_repository.get_by_job_id(job_id)
        if initialization is not None:
            self._save_initialization(
                initialization.model_copy(
                    update={
                        "status": InitializationStatus.CANCELLED,
                        "completion_status": InitializationCompletionStatus.IGNORED,
                        "updated_at": self._now(),
                    }
                )
            )
        return job

    def mark_stale(self, work_id: str, *, reason: str) -> InitializationRecord:
        latest = self._initialization_repository.get_latest_by_work(work_id)
        if latest is None:
            raise ValueError("initialization_not_found")
        if latest.story_memory_snapshot_id:
            self._story_memory_service.mark_snapshot_stale(latest.story_memory_snapshot_id, reason)
        if latest.story_state_snapshot_id:
            self._story_state_service.mark_story_state_stale(latest.story_state_snapshot_id, reason)
        return self._save_initialization(
            latest.model_copy(
                update={
                    "status": InitializationStatus.STALE,
                    "stale": True,
                    "stale_reason": reason,
                    "updated_at": self._now(),
                }
            )
        )

    def is_stale(self, work_id: str) -> bool:
        latest = self._initialization_repository.get_latest_by_work(work_id)
        return bool(latest and (latest.stale or latest.status == InitializationStatus.STALE))

    def _analyze_outline(self, work_id: str, work_title: str, chapters: list[object]) -> OutlineAnalysisResult:
        titles = [str(getattr(chapter, "title", "") or f"第{index}章").strip() or f"第{index}章" for index, chapter in enumerate(chapters, start=1)]
        return OutlineAnalysisResult(
            work_id=work_id,
            title=work_title,
            chapter_order=[getattr(chapter, "id").value for chapter in chapters],
            chapter_titles=titles,
            global_summary=f"{work_title} 当前已确认 {len(chapters)} 章，初始化基于已持久化章节生成最小分析结果。",
            issues=["outline_empty"],
            outline_empty=True,
        )

    def _analyze_chapter(self, chapter_id: str, title: str, content: str, version: int) -> ChapterAnalysisResult:
        normalized = str(content or "").strip()
        if not normalized:
            return ChapterAnalysisResult(
                chapter_id=chapter_id,
                chapter_title=title,
                chapter_version=version,
                status=ChapterAnalysisStatus.EMPTY,
                summary="chapter_empty",
                error_code="chapter_empty",
                is_empty=True,
                analyzed_at=self._now(),
            )
        characters = self._extract_named_tokens(normalized, suffixes=("林", "顾", "沈", "陆", "温", "顾迟", "林舟", "沈砚"))
        locations = self._extract_location_tokens(normalized)
        unresolved = ["pending_follow_up"] if "?" in normalized or "？" in normalized else []
        summary = self._build_chapter_summary(
            title=title,
            normalized=normalized,
            characters=characters,
            locations=locations,
            unresolved=unresolved,
        )
        plot_points = [summary]
        return ChapterAnalysisResult(
            chapter_id=chapter_id,
            chapter_title=title,
            chapter_version=version,
            status=ChapterAnalysisStatus.SUCCEEDED,
            summary=summary,
            characters=characters,
            locations=locations,
            plot_points=plot_points,
            unresolved_threads=unresolved,
            analyzed_at=self._now(),
        )

    def _build_chapter_summary(
        self,
        *,
        title: str,
        normalized: str,
        characters: list[str],
        locations: list[str],
        unresolved: list[str],
    ) -> str:
        parts = [f"{title or '本章'}已完成最小分析"]
        if characters:
            parts.append(f"角色:{', '.join(characters[:3])}")
        if locations:
            parts.append(f"地点:{', '.join(locations[:2])}")
        if unresolved:
            parts.append("存在待跟进线索")
        parts.append(f"原文长度:{len(normalized)}字")
        return "；".join(parts)[:120]

    def _extract_named_tokens(self, text: str, *, suffixes: tuple[str, ...]) -> list[str]:
        results: list[str] = []
        for token in re.findall(r"[\u4e00-\u9fff]{2,4}", text):
            if token in results:
                continue
            if token in suffixes or token.endswith(("城", "馆", "塔", "港", "岛")):
                continue
            results.append(token)
            if len(results) >= 5:
                break
        return results

    def _extract_location_tokens(self, text: str) -> list[str]:
        results: list[str] = []
        for token in re.findall(r"[\u4e00-\u9fff]{2,8}", text):
            if token.endswith(("城", "馆", "塔", "港", "岛", "镇", "山", "海")) and token not in results:
                results.append(token)
            if len(results) >= 5:
                break
        return results

    def _get_step_ids(self, job_id: str) -> dict[str, str]:
        return {step.step_type: step.step_id for step in self._job_service.get_job_steps(job_id)}

    def _save_initialization(self, initialization: InitializationRecord) -> InitializationRecord:
        return self._initialization_repository.save(initialization)

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
