from __future__ import annotations

import uuid
from datetime import UTC, datetime

from application.services.ai.ai_job_service import AIJobService
from application.services.ai.initialization_analysis_service import ManuscriptAnalysisService, OutlineAnalysisService
from application.services.ai.story_memory_service import StoryMemoryService
from application.services.ai.story_state_service import StoryStateService
from application.services.ai.vector_index_service import VectorIndexService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    ArcQualityLevel,
    ArcStatus,
    AIJob,
    ChapterAnalysisResult,
    ChapterAnalysisStatus,
    HierarchicalStorySummary,
    InitializationCompletionStatus,
    InitializationRecord,
    InitializationStatus,
    MasterArc,
    OutlineAnalysisResult,
    VectorIndexBuildResult,
    VolumeArc,
)
from domain.repositories.ai.ai_job_attempt_repository import AIJobAttemptRepository
from domain.repositories.ai.ai_job_repository import AIJobRepository
from domain.repositories.ai.ai_job_step_repository import AIJobStepRepository
from domain.repositories.ai.initialization_repository import InitializationRepository
from domain.repositories.ai.plot_arc_repository import PlotArcRepository
from domain.repositories.ai.story_memory_repository import StoryMemoryRepository
from domain.repositories.ai.story_state_repository import StoryStateRepository


RECENT_CHAPTER_SUMMARY_LIMIT = 10


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
        plot_arc_repository: PlotArcRepository | None = None,
        vector_index_service: VectorIndexService | None = None,
        writing_asset_service=None,
        outline_analysis_service: OutlineAnalysisService | None = None,
        manuscript_analysis_service: ManuscriptAnalysisService | None = None,
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
        self._plot_arc_repository = plot_arc_repository
        self._vector_index_service = vector_index_service
        self._writing_asset_service = writing_asset_service
        self._outline_analysis_service = outline_analysis_service
        self._manuscript_analysis_service = manuscript_analysis_service

    def start_initialization(self, work_id: str, *, created_by: str, auto_run: bool = True) -> InitializationRecord:
        self._work_service.get_work(work_id)
        latest = self._initialization_repository.get_latest_by_work(work_id)
        if latest and latest.status in {
            InitializationStatus.OUTLINE_ANALYZING,
            InitializationStatus.MANUSCRIPT_ANALYZING,
            InitializationStatus.MEMORY_BUILDING,
            InitializationStatus.STATE_BUILDING,
            InitializationStatus.VECTOR_INDEXING,
        }:
            raise ValueError("initialization_in_progress")

        chapters = self._chapter_service.list_chapters(work_id)
        now = self._now()
        job = self._job_service.create_job(
            job_type="ai_initialization",
            work_id=work_id,
            steps=[
                {"step_type": "outline_analysis", "step_name": "Outline Analysis"},
                {"step_type": "manuscript_chapter_analysis", "step_name": "Manuscript Analysis"},
                {"step_type": "build_story_memory", "step_name": "Build Story Memory"},
                {"step_type": "build_story_state", "step_name": "Build Story State"},
                {"step_type": "build_vector_index", "step_name": "Build Vector Index"},
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
        try:
            return self._run_initialization(initialization_id)
        except Exception as exc:
            initialization = self._initialization_repository.get(initialization_id)
            error_code = str(getattr(exc, "error_code", "") or "initialization_analysis_failed")
            safe_error_code = error_code if error_code.replace("_", "").isalnum() else "initialization_analysis_failed"
            step_type = {
                InitializationStatus.OUTLINE_ANALYZING: "outline_analysis",
                InitializationStatus.MANUSCRIPT_ANALYZING: "manuscript_chapter_analysis",
                InitializationStatus.MEMORY_BUILDING: "build_story_memory",
                InitializationStatus.STATE_BUILDING: "build_story_state",
                InitializationStatus.VECTOR_INDEXING: "build_vector_index",
            }.get(initialization.status, "outline_analysis")
            step_ids = self._get_step_ids(initialization.job_id)
            step_id = step_ids.get(step_type, "")
            if step_id:
                try:
                    self._job_service.mark_step_failed(
                        initialization.job_id,
                        step_id,
                        error_code=safe_error_code,
                        error_message=safe_error_code,
                    )
                except Exception:
                    pass
            try:
                self._job_service.mark_job_failed(
                    initialization.job_id,
                    error_code=safe_error_code,
                    error_message=safe_error_code,
                )
            except Exception:
                pass
            return self._save_initialization(
                initialization.model_copy(
                    update={
                        "status": InitializationStatus.FAILED,
                        "completion_status": InitializationCompletionStatus.FAILED,
                        "error_code": safe_error_code,
                        "error_message": safe_error_code,
                        "finalized_at": self._now(),
                        "updated_at": self._now(),
                    }
                )
            )

    def _run_initialization(self, initialization_id: str) -> InitializationRecord:
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
        outline_analysis = self._analyze_outline(
            work.id,
            work.title,
            chapters,
            job_id=initialization.job_id,
        )
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

        self._job_service.mark_step_running(initialization.job_id, step_ids["manuscript_chapter_analysis"])
        chapter_results: list[ChapterAnalysisResult] = []
        previous_summaries: list[str] = []
        for chapter_order, chapter in enumerate(chapters, start=1):
            result = self._analyze_chapter(
                work_id=initialization.work_id,
                chapter_id=chapter.id.value,
                title=chapter.title,
                content=chapter.content,
                version=chapter.version,
                chapter_order=chapter_order,
                outline_analysis=outline_analysis,
                previous_chapter_summaries=previous_summaries[-RECENT_CHAPTER_SUMMARY_LIMIT:],
                job_id=initialization.job_id,
            )
            chapter_results.append(result)
            if result.status == ChapterAnalysisStatus.SUCCEEDED and result.summary:
                previous_summaries.append(result.summary)
        hierarchical_story_summary = None
        if previous_summaries:
            hierarchical_story_summary = self._manuscript_analysis_service.analyze_story_hierarchy(
                work_id=initialization.work_id,
                outline_analysis=outline_analysis,
                chapter_results=chapter_results,
                job_id=initialization.job_id,
            )
        self._job_service.mark_step_completed(initialization.job_id, step_ids["manuscript_chapter_analysis"], summary="chapters analyzed")

        return self.finalize_initialization(
            initialization_id,
            chapter_results=chapter_results,
            hierarchical_story_summary=hierarchical_story_summary,
        )

    def finalize_initialization(
        self,
        initialization_id: str,
        *,
        chapter_results: list[ChapterAnalysisResult] | None = None,
        hierarchical_story_summary: HierarchicalStorySummary | None = None,
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
        hierarchy = hierarchical_story_summary or initialization.hierarchical_story_summary
        successful = [item for item in results if item.status == ChapterAnalysisStatus.SUCCEEDED and not item.is_empty]
        empty_count = sum(1 for item in results if item.status == ChapterAnalysisStatus.EMPTY or item.is_empty)
        failed_count = sum(1 for item in results if item.status == ChapterAnalysisStatus.FAILED)

        update_base = {
            "chapter_results": results,
            "hierarchical_story_summary": hierarchy,
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

        initialization = self._save_initialization(
            initialization.model_copy(update={**update_base, "status": InitializationStatus.MEMORY_BUILDING, "updated_at": self._now()})
        )
        self._job_service.mark_step_running(initialization.job_id, step_ids["build_story_memory"])
        if hierarchy is None:
            raise ValueError("missing_input")
        story_memory = self._story_memory_service.build_snapshot(
            initialization=initialization.model_copy(update=update_base),
            outline_analysis=initialization.outline_analysis or OutlineAnalysisResult(work_id=initialization.work_id),
            chapter_results=results,
            hierarchical_story_summary=hierarchy,
        )
        self._job_service.mark_step_completed(initialization.job_id, step_ids["build_story_memory"], summary="story memory built")

        initialization = self._save_initialization(
            initialization.model_copy(update={**update_base, "status": InitializationStatus.STATE_BUILDING, "updated_at": self._now()})
        )
        self._job_service.mark_step_running(initialization.job_id, step_ids["build_story_state"])
        story_state = self._story_state_service.build_analysis_baseline(
            initialization=initialization.model_copy(update=update_base),
            story_memory_snapshot=story_memory,
            chapter_results=results,
        )
        self._job_service.mark_step_completed(initialization.job_id, step_ids["build_story_state"], summary="story state built")
        self._persist_initial_plot_arcs(
            initialization=initialization.model_copy(update=update_base),
            story_memory=story_memory,
            story_state=story_state,
            chapter_results=results,
        )
        vector_index_result = self._build_vector_index(
            initialization=initialization.model_copy(update={**update_base, "status": InitializationStatus.VECTOR_INDEXING, "updated_at": self._now()}),
            step_id=step_ids["build_vector_index"],
        )
        if self._job_service.get_job(initialization.job_id).status.value == "cancelled":
            return self._save_initialization(
                initialization.model_copy(
                    update={
                        **update_base,
                        "status": InitializationStatus.CANCELLED,
                        "completion_status": InitializationCompletionStatus.IGNORED,
                        "updated_at": self._now(),
                    }
                )
            )

        result_summary = {
            "analyzed_chapter_count": len(successful),
            "vector_index_status": vector_index_result.index_status,
        }
        if empty_count > 0 or failed_count > 0:
            self._job_service.mark_job_partial_success(
                initialization.job_id,
                result_summary={
                    **result_summary,
                    "empty_chapter_count": empty_count,
                    "failed_chapter_count": failed_count,
                    **self._vector_index_summary_payload(vector_index_result),
                },
            )
            completion_status = InitializationCompletionStatus.PARTIAL_SUCCESS
            partial_reason = "chapter_empty_or_failed_detected"
        else:
            self._job_service.mark_job_completed(
                initialization.job_id,
                result_summary={**result_summary, **self._vector_index_summary_payload(vector_index_result)},
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
        self._work_service.get_work(work_id)
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

    def _analyze_outline(
        self,
        work_id: str,
        work_title: str,
        chapters: list[object],
        *,
        job_id: str,
    ) -> OutlineAnalysisResult:
        if self._writing_asset_service is None or self._outline_analysis_service is None:
            raise RuntimeError("initialization_analysis_dependencies_missing")
        work_outline = self._writing_asset_service.get_work_outline(work_id)
        existing_chapters = [
            {
                "chapter_id": getattr(chapter, "id").value,
                "title": str(getattr(chapter, "title", "") or ""),
                "order_index": int(getattr(chapter, "order_index", index) or index),
            }
            for index, chapter in enumerate(chapters, start=1)
        ]
        return self._outline_analysis_service.analyze(
            work_id=work_id,
            work_title=work_title,
            user_outline=str(work_outline.content_text or ""),
            existing_chapters=existing_chapters,
            job_id=job_id,
        )

    def _analyze_chapter(
        self,
        *,
        work_id: str,
        chapter_id: str,
        title: str,
        content: str,
        version: int,
        chapter_order: int,
        outline_analysis: OutlineAnalysisResult,
        previous_chapter_summaries: list[str],
        job_id: str,
    ) -> ChapterAnalysisResult:
        if self._manuscript_analysis_service is None:
            raise RuntimeError("initialization_analysis_dependencies_missing")
        return self._manuscript_analysis_service.analyze_chapter(
            work_id=work_id,
            chapter_id=chapter_id,
            chapter_title=title,
            chapter_content=content,
            chapter_version=version,
            chapter_order=chapter_order,
            outline_analysis=outline_analysis,
            previous_chapter_summaries=previous_chapter_summaries,
            job_id=job_id,
            analyzed_at=self._now(),
        )

    def _get_step_ids(self, job_id: str) -> dict[str, str]:
        return {step.step_type: step.step_id for step in self._job_service.get_job_steps(job_id)}

    def _build_vector_index(self, *, initialization: InitializationRecord, step_id: str) -> VectorIndexBuildResult:
        if self._vector_index_service is None:
            result = VectorIndexBuildResult(
                index_status="degraded",
                warning_count=1,
                degraded_reason="vector_index_service_missing",
                warnings=["vector_index_service_missing"],
            )
            self._job_service.mark_step_completed(
                initialization.job_id,
                step_id,
                summary="vector index skipped",
                warning_count=result.warning_count,
                status_reason="vector_index_degraded",
            )
            return result

        self._save_initialization(
            initialization.model_copy(update={"status": InitializationStatus.VECTOR_INDEXING, "updated_at": self._now()})
        )
        self._job_service.mark_step_running(initialization.job_id, step_id)
        try:
            should_continue = lambda: self._job_service.get_job(initialization.job_id).status.value != "cancelled"
            build_initialization_index = getattr(self._vector_index_service, "build_initialization_index", None)
            if callable(build_initialization_index):
                result = build_initialization_index(
                    initialization.work_id,
                    should_continue=should_continue,
                )
            else:
                result = self._vector_index_service.build_initial_index(
                    initialization.work_id,
                    should_continue=should_continue,
                )
        except Exception as exc:
            self._job_service.mark_step_failed(
                initialization.job_id,
                step_id,
                error_code="vector_index_build_failed",
                error_message=str(exc),
                warning_count=1,
            )
            return VectorIndexBuildResult(
                index_status="failed",
                warning_count=1,
                degraded_reason=str(exc),
                warnings=[str(exc)],
            )

        summary = f"indexed_chapters={result.indexed_chapter_count}; indexed_chunks={result.indexed_chunk_count}"
        if result.index_status in {"degraded", "failed"} or result.warning_count > 0:
            self._job_service.mark_step_completed(
                initialization.job_id,
                step_id,
                summary=summary,
                warning_count=max(int(result.warning_count or 0), 1 if result.index_status in {"degraded", "failed"} else 0),
                status_reason="vector_index_degraded",
            )
        else:
            self._job_service.mark_step_completed(initialization.job_id, step_id, summary=summary)
        return result

    def _vector_index_summary_payload(self, result: VectorIndexBuildResult) -> dict[str, object]:
        payload: dict[str, object] = {
            "vector_index_status": result.index_status,
            "vector_index_warning_count": int(result.warning_count or 0),
        }
        warning_value = result.degraded_reason or (result.warnings[0] if result.warnings else "")
        if warning_value:
            payload["vector_index_warning"] = warning_value
        return payload

    def _persist_initial_plot_arcs(self, *, initialization: InitializationRecord, story_memory, story_state, chapter_results: list[ChapterAnalysisResult]) -> None:
        if self._plot_arc_repository is None:
            return
        now = self._now()
        source_refs = [story_memory.snapshot_id, story_state.story_state_id]
        outline_title = str(initialization.outline_analysis.title if initialization.outline_analysis else "").strip()
        protagonist_motivation = (
            (story_memory.plot_threads[0] if story_memory.plot_threads else "")
            or (story_state.unresolved_threads[0] if story_state.unresolved_threads else "")
            or "延续当前主线并查明核心真相"
        )
        master_arc = MasterArc(
            master_arc_id=f"ma_{initialization.work_id}",
            work_id=initialization.work_id,
            arc_title=outline_title or "主线轨道",
            version=1,
            arc_logline=str(story_memory.global_summary or "").strip(),
            status=ArcStatus.DEGRADED if initialization.outline_analysis is None or initialization.outline_analysis.outline_empty else ArcStatus.READY,
            quality_level=ArcQualityLevel.MINIMAL,
            ultimate_goal=str(story_memory.global_summary or protagonist_motivation).strip() or "待补充主线目标",
            protagonist_motivation=protagonist_motivation,
            current_stage=str(story_state.current_position_summary or "初始化完成").strip(),
            stage_position=str(story_state.current_position_summary or "初始化完成").strip(),
            core_theme="延续既有叙事基调",
            final_conflict=str(story_state.unresolved_threads[0] if story_state.unresolved_threads else protagonist_motivation).strip(),
            main_antagonist="待补充",
            key_milestones=list(story_memory.plot_threads[:3]),
            endgame_foreshadows=list(story_memory.plot_threads[:2]),
            source_initialization_id=initialization.initialization_id,
            source_outline_ref=outline_title,
            source_refs=source_refs,
            warning_codes=["master_arc_inferred_without_outline"] if initialization.outline_analysis is None or initialization.outline_analysis.outline_empty else [],
            built_from_text_inference=bool(initialization.outline_analysis is None or initialization.outline_analysis.outline_empty),
            built_by="memory_agent",
            last_updated_by="memory_agent",
            created_at=now,
            updated_at=now,
        )
        chapter_count = max(len(chapter_results), 1)
        volume_arc = VolumeArc(
            volume_arc_id=f"va_{initialization.work_id}_1",
            work_id=initialization.work_id,
            master_arc_id=master_arc.master_arc_id,
            version=1,
            volume_no=1,
            status=ArcStatus.PENDING,
            quality_level=ArcQualityLevel.PLACEHOLDER,
            stage_goal=str(story_state.current_position_summary or "等待方向确认后生成当前卷目标。").strip(),
            core_conflict=str(story_state.unresolved_threads[0] if story_state.unresolved_threads else "等待方向确认后补充当前卷冲突。").strip(),
            climax_description="等待方向选择与阶段目标确认后补充卷高潮。",
            resolution_condition="等待方向确认后定义本卷收束条件。",
            stage_open_loops=list(story_state.unresolved_threads[:5]),
            key_characters=list(story_state.active_characters[:5]),
            chapter_range={"from_chapter": 1, "to_chapter_estimate": chapter_count},
            source_initialization_id=initialization.initialization_id,
            source_outline_ref=outline_title,
            source_refs=source_refs,
            warning_codes=["arc_placeholder_only"],
            built_by="planner_agent",
            last_updated_by="planner_agent",
            created_at=now,
            updated_at=now,
        )
        self._plot_arc_repository.save_master_arc(master_arc)
        self._plot_arc_repository.save_volume_arc(volume_arc)

    def _save_initialization(self, initialization: InitializationRecord) -> InitializationRecord:
        return self._initialization_repository.save(initialization)

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
