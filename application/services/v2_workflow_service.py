"""
v2主流程服务。
负责导入、整理、分支、计划、写作、刷新memory全链路。
"""

from __future__ import annotations

from datetime import datetime, UTC
import json
import os
import re
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from application.agent_mvp import AnalysisTool, ContinueWritingTool, StoryBranchTool, TaskContext
from application.config.story_defaults import (
    DEFAULT_DIALOGUE_DENSITY,
    DEFAULT_NARRATIVE_DISTANCE,
    DEFAULT_PREFERRED_RHYTHM,
)
from application.dto.request_dto import ImportNovelRequest
from application.prompts.prompt_labels import FORESHADOWING_ACTION_LABELS, HOOK_STRENGTH_LABELS
from application.services.content_service import ContentService
from application.services.continuation_context_builder import ContinuationContextBuilder
from application.services.chapter_task_generator import ChapterTaskGenerator
from application.services.continuation_writer import ContinuationWriter
from application.services.detemplating_rewriter import DetemplatingRewriter
from application.services.draft_integrity_checker import DraftIntegrityChecker
from application.services.chapter_allocation_service import ChapterAllocationService
from application.services.chapter_ai_service import ChapterAIService
from application.services.chapter_memory_service import ChapterMemoryService
from application.services.chapter_planning_service import ChapterPlanningService
from application.services.global_analysis_service import GlobalAnalysisService
from application.services.logging_service import build_log_context, get_logger
from application.services.memory_writeback_service import MemoryWritebackService
from application.services.arc_planning_service import ArcPlanningService
from application.services.arc_writeback_service import ArcWritebackService
from application.services.plot_arc_service import PlotArcService
from application.services.project_service import ProjectService
from application.services.validation_service_v2 import ValidationServiceV2
from application.services.write_batch_result_builder import WriteBatchResultBuilder
from application.services.writing_service_v2 import WritingServiceV2
from application.prompts.prompt_constants import ARC_STAGE_ORDER
from application.prompts.prompt_constants import PLANNING_MODE_LIGHT
from domain.entities.chapter import Chapter
from domain.entities.chapter_analysis_memory import ChapterAnalysisMemory
from domain.entities.chapter_arc_binding import ChapterArcBinding
from domain.entities.chapter_continuation_memory import ChapterContinuationMemory
from domain.entities.chapter_outline import ChapterOutline
from domain.entities.chapter_task import ChapterTask
from domain.entities.model_role import ModelRole
from domain.entities.continuation_context_snapshot import ContinuationContextSnapshot
from domain.entities.continuation_context import ContinuationContext
from domain.entities.detemplated_draft import DetemplatedDraft
from domain.entities.draft_integrity_check import DraftIntegrityCheck
from domain.entities.global_constraints import GlobalConstraints
from domain.entities.structural_draft import StructuralDraft
from domain.entities.style_requirements import StyleRequirements
from domain.repositories.chapter_analysis_memory_repository import IChapterAnalysisMemoryRepository
from domain.repositories.chapter_arc_binding_repository import IChapterArcBindingRepository
from domain.repositories.chapter_continuation_memory_repository import IChapterContinuationMemoryRepository
from domain.repositories.chapter_outline_repository import IChapterOutlineRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.chapter_task_repository import IChapterTaskRepository
from domain.repositories.continuation_context_snapshot_repository import IContinuationContextSnapshotRepository
from domain.repositories.arc_progress_snapshot_repository import IArcProgressSnapshotRepository
from domain.repositories.detemplated_draft_repository import IDetemplatedDraftRepository
from domain.repositories.draft_integrity_check_repository import IDraftIntegrityCheckRepository
from domain.repositories.global_constraints_repository import IGlobalConstraintsRepository
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.outline_repository import IOutlineRepository
from domain.repositories.structural_draft_repository import IStructuralDraftRepository
from domain.repositories.style_requirements_repository import IStyleRequirementsRepository
from domain.constants.story_constants import (
    CHAPTER_TITLE_FALLBACK_TEMPLATE,
    CONTINUATION_CONTEXT_RECENT_CHAPTER_LIMIT,
    DEFAULT_BRANCH_COUNT,
    DEFAULT_FORESHADOWING_ACTION,
    DEFAULT_GENERATE_CHAPTER_COUNT,
    DEFAULT_HOOK_STRENGTH,
    DEFAULT_LAST_CHAPTER_TAIL_CHARS,
    DEFAULT_PACE_TARGET,
    DEFAULT_TARGET_WORDS_PER_CHAPTER,
    LAST_CHAPTER_TAIL_MAX_CHARS,
    LAST_CHAPTER_TAIL_MIN_CHARS,
)
from domain.constants.story_enums import (
    FORESHADOWING_ACTION_ADVANCE,
    FORESHADOWING_ACTION_BURY,
    FORESHADOWING_ACTION_RETRIEVE,
    GENERATION_STAGE_DETEMPLATED,
    GENERATION_STAGE_STRUCTURAL,
    HOOK_STRENGTH_STRONG,
    STYLE_SOURCE_MANUAL,
    STYLE_SOURCE_SAMPLE,
    WRITING_STATUS_READY,
)
from domain.types import ChapterId, ChapterStatus, NovelId, ProjectId
from domain.types import GenreType
from domain.utils import looks_garbled_text, repair_mojibake, sanitize_display_text
from infrastructure.llm.llm_factory import LLMFactory
from infrastructure.persistence.sqlite_v2_repo import SQLiteV2Repository


class V2WorkflowService:
    def __init__(
        self,
        project_service: ProjectService,
        content_service: ContentService,
        chapter_repo: IChapterRepository,
        novel_repo: INovelRepository,
        outline_repo: IOutlineRepository,
        llm_factory: LLMFactory,
        v2_repo: SQLiteV2Repository,
        global_constraints_repo: IGlobalConstraintsRepository,
        chapter_analysis_memory_repo: IChapterAnalysisMemoryRepository,
        chapter_continuation_memory_repo: IChapterContinuationMemoryRepository,
        chapter_outline_repo: IChapterOutlineRepository,
        chapter_task_repo: IChapterTaskRepository,
        structural_draft_repo: IStructuralDraftRepository,
        detemplated_draft_repo: IDetemplatedDraftRepository,
        draft_integrity_check_repo: IDraftIntegrityCheckRepository,
        style_requirements_repo: IStyleRequirementsRepository,
        continuation_context_snapshot_repo: Optional[IContinuationContextSnapshotRepository] = None,
        arc_progress_snapshot_repo: Optional[IArcProgressSnapshotRepository] = None,
        plot_arc_service: Optional[PlotArcService] = None,
        chapter_arc_binding_repo: Optional[IChapterArcBindingRepository] = None,
        arc_planning_service: Optional[ArcPlanningService] = None,
        arc_writeback_service: Optional[ArcWritebackService] = None,
    ):
        self.project_service = project_service
        self.content_service = content_service
        self.chapter_repo = chapter_repo
        self.novel_repo = novel_repo
        self.outline_repo = outline_repo
        self.llm_factory = llm_factory
        self.v2_repo = v2_repo
        self.global_constraints_repo = global_constraints_repo
        self.chapter_analysis_memory_repo = chapter_analysis_memory_repo
        self.chapter_continuation_memory_repo = chapter_continuation_memory_repo
        self.chapter_outline_repo = chapter_outline_repo
        self.chapter_task_repo = chapter_task_repo
        self.structural_draft_repo = structural_draft_repo
        self.detemplated_draft_repo = detemplated_draft_repo
        self.draft_integrity_check_repo = draft_integrity_check_repo
        self.style_requirements_repo = style_requirements_repo
        self.plot_arc_service = plot_arc_service
        self.arc_planning_service = arc_planning_service
        self.arc_writeback_service = arc_writeback_service or type(
            "_NullArcWritebackService",
            (),
            {"writeback_chapter_arc": lambda *_args, **_kwargs: None},
        )()
        self.arc_progress_snapshot_repo = arc_progress_snapshot_repo or type(
            "_NullArcProgressSnapshotRepo",
            (),
            {"list_by_arc": lambda *_args, **_kwargs: [], "save": lambda *_args, **_kwargs: None},
        )()
        self.chapter_arc_binding_repo = chapter_arc_binding_repo or type(
            "_NullChapterArcBindingRepo",
            (),
            {"list_by_project": lambda *_args, **_kwargs: [], "list_by_chapter": lambda *_args, **_kwargs: [], "save": lambda *_args, **_kwargs: None},
        )()
        self.continuation_context_snapshot_repo = continuation_context_snapshot_repo or type(
            "_NullContinuationContextSnapshotRepo",
            (),
            {
                "save": lambda *_args, **_kwargs: None,
                "find_latest": lambda *_args, **_kwargs: None,
                "list_by_project_id": lambda *_args, **_kwargs: [],
            },
        )()
        self.logger = get_logger(__name__)
        self.continuation_context_builder = ContinuationContextBuilder(self)
        self.chapter_task_generator = ChapterTaskGenerator(self)
        self.continuation_writer = ContinuationWriter(self)
        self.detemplating_rewriter = DetemplatingRewriter(self)
        self.draft_integrity_checker = DraftIntegrityChecker(self)
        self.chapter_allocation_service = ChapterAllocationService(self)
        self.write_batch_result_builder = WriteBatchResultBuilder()
        self.memory_writeback_service = MemoryWritebackService(self)
        self.continue_writing_tool_cls = ContinueWritingTool
        self.analysis_tool_cls = AnalysisTool
        self.prompt_ai_service = ChapterAIService(llm_factory)
        self.global_analysis_service = GlobalAnalysisService(self.prompt_ai_service)
        self.chapter_memory_service = ChapterMemoryService(self.prompt_ai_service)
        self.validation_service_v2 = ValidationServiceV2(self)
        self.writing_service_v2 = WritingServiceV2(self, self.validation_service_v2)
        self.chapter_planning_service = ChapterPlanningService(self)

    def _is_kimi_role(self, role: ModelRole) -> bool:
        return role in {
            ModelRole.GLOBAL_ANALYSIS,
            ModelRole.CHAPTER_ANALYSIS,
            ModelRole.CONTINUATION_MEMORY_EXTRACTION,
            ModelRole.PLOT_ARC_EXTRACTION,
            ModelRole.ARC_STATE_UPDATE,
            ModelRole.ARC_SELECTION,
            ModelRole.CHAPTER_PLANNING,
            ModelRole.CONSISTENCY_VALIDATION,
        }

    def _get_role_clients(self, role: ModelRole, project_id: str = "", chapter_id: str = "", chapter_number: int = 0, planning_mode: str = ""):
        mode = str(os.getenv("INKTRACE_MODEL_ROLE_MODE", "strict") or "strict").strip().lower()
        kimi_role = self._is_kimi_role(role)
        provider = "kimi" if kimi_role else "deepseek"
        primary = self.llm_factory.get_client_for_provider(provider)
        backup = None if mode == "strict" else self.llm_factory.get_fallback_client_for_provider(provider)
        self.logger.info(
            "模型职责路由完成",
            extra=build_log_context(
                event="model_role_dispatched",
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=chapter_number,
                task_role=role.value,
                model_name=provider,
                planning_mode=planning_mode,
                used_fallback=bool(backup),
            ),
        )
        if mode == "degraded":
            self.logger.warning(
                "模型职责进入降级模式",
                extra=build_log_context(
                    event="model_role_degraded",
                    project_id=project_id,
                    chapter_id=chapter_id,
                    chapter_number=chapter_number,
                    task_role=role.value,
                    model_name=provider,
                    planning_mode=planning_mode,
                    used_fallback=bool(backup),
                ),
            )
        return primary, backup

    def _should_use_legacy_analysis_tool(self) -> bool:
        return all(
            getattr(self.llm_factory, attr, None) is None
            for attr in ("deepseek_client", "kimi_client")
        )

    def clean_text(self, value: str) -> str:
        cleaned = sanitize_display_text(value)
        if not cleaned:
            return ""
        cleaned = repair_mojibake(cleaned).strip()
        cleaned = re.sub(r"chunk\s*=?\s*\d+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\?{2,}", "", cleaned)
        cleaned = cleaned.replace("分析完成", "").replace("组织完成", "")
        cleaned = cleaned.replace(";", "；")
        cleaned = cleaned.replace(",", "、")
        cleaned = re.sub(r"[|/\\\\]+", "；", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip("；、-:： ")
        return cleaned

    def _normalize_foreshadowing_action(self, value: str) -> str:
        text = self.clean_text(str(value or ""))
        mapping = {
            "advance": FORESHADOWING_ACTION_ADVANCE,
            "bury": FORESHADOWING_ACTION_BURY,
            "retrieve": FORESHADOWING_ACTION_RETRIEVE,
            "埋": FORESHADOWING_ACTION_BURY,
            "推进": FORESHADOWING_ACTION_ADVANCE,
            "回收": FORESHADOWING_ACTION_RETRIEVE,
        }
        return mapping.get(text, DEFAULT_FORESHADOWING_ACTION)

    def _normalize_hook_strength(self, value: str) -> str:
        text = self.clean_text(str(value or ""))
        mapping = {
            "weak": "weak",
            "medium": "medium",
            "strong": "strong",
            "弱": "weak",
            "中": "medium",
            "强": "strong",
        }
        return mapping.get(text, DEFAULT_HOOK_STRENGTH)

    def _foreshadowing_action_label(self, value: str) -> str:
        normalized = self._normalize_foreshadowing_action(value)
        return FORESHADOWING_ACTION_LABELS.get(normalized, "推进伏笔")

    def _hook_strength_label(self, value: str) -> str:
        normalized = self._normalize_hook_strength(value)
        return HOOK_STRENGTH_LABELS.get(normalized, "中钩子")

    def looks_garbled_text(self, value: str) -> bool:
        if looks_garbled_text(value):
            return True
        if not isinstance(value, str):
            return False
        text = value.strip()
        if not text:
            return False
        if text.count("?") >= max(3, len(text) // 4):
            return True
        return False

    def normalize_text_list(self, items: List[str], limit: int) -> List[str]:
        unique: List[str] = []
        for item in items:
            cleaned = self.clean_text(str(item or ""))
            if not cleaned:
                continue
            if self.looks_garbled_text(cleaned):
                continue
            if cleaned not in unique:
                unique.append(cleaned)
            if len(unique) >= limit:
                break
        return unique[:limit]

    async def import_project(
        self,
        project_name: str,
        genre: str,
        novel_file_path: str,
        target_word_count: int = 8000000,
        author: str = "",
        import_mode: str = "full",
        chapter_items: Optional[List[Dict[str, Any]]] = None,
        outline_file_path: str = "",
        auto_organize: bool = True,
    ) -> Dict[str, Any]:
        self.logger.info(
            "导入项目开始",
            extra=build_log_context(
                event="workflow_import_started",
                project_name=project_name,
                import_mode=import_mode,
                file_path=novel_file_path,
                outline_present=bool(outline_file_path),
            ),
        )
        try:
            genre_enum = GenreType(genre) if genre else GenreType.XUANHUAN
        except ValueError:
            genre_enum = GenreType.XUANHUAN
        project = self.project_service.create_project(
            name=project_name,
            genre=genre_enum,
            target_words=max(10000, int(target_word_count or 8000000)),
            author=author,
        )
        request = ImportNovelRequest(
            novel_id=str(project.novel_id),
            file_path=novel_file_path,
            author=author,
            import_mode=import_mode,
            chapter_items=chapter_items or [],
            outline_path=outline_file_path or None,
        )
        self.content_service.import_novel(request)
        memory_view = {}
        if auto_organize:
            organized = await self.organize_project(project.id.value, mode="chapter_first", rebuild_memory=True)
            memory_view = organized.get("memory_view") or {}
        self.logger.info(
            "导入项目完成",
            extra=build_log_context(
                event="workflow_import_finished",
                project_id=project.id.value,
                novel_id=str(project.novel_id),
                status="organized" if auto_organize else "imported",
            ),
        )
        return {
            "project_id": project.id.value,
            "novel_id": str(project.novel_id),
            "outline_id": f"outline_{project.id.value}",
            "status": "organized" if auto_organize else "imported",
            "memory_view": memory_view,
        }

    async def organize_project(
        self,
        project_id: str,
        mode: str,
        rebuild_memory: bool,
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        resume_from: int = 0,
        checkpoint_memory: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "整理开始",
            extra=build_log_context(
                event="organize_started",
                project_id=project_id,
                novel_id=str(project.novel_id),
                mode=mode,
                rebuild_memory=bool(rebuild_memory),
            ),
        )
        async def _emit_progress(
            stage: str,
            current: int,
            total: int,
            message: str,
            current_chapter_title: str = "",
            status: str = "running",
            resumable: bool = False,
            memory_snapshot: Optional[Dict[str, Any]] = None,
        ) -> None:
            if progress_callback is None:
                return
            safe_total = max(int(total), 0)
            safe_current = max(0, min(int(current), safe_total)) if safe_total else 0
            percent = 100 if safe_total and safe_current >= safe_total else int((safe_current / safe_total) * 100) if safe_total else 0
            payload = {
                "status": status,
                "stage": stage,
                "current": safe_current,
                "total": safe_total,
                "percent": percent,
                "message": self.clean_text(message) or message,
                "current_chapter_title": self.clean_text(current_chapter_title),
                "resumable": resumable,
            }
            if isinstance(memory_snapshot, dict):
                payload["memory_snapshot"] = memory_snapshot
            await progress_callback(payload)
        job_id = self.v2_repo.start_workflow_job(
            project_id=project_id,
            workflow_type="organize_novel",
            input_payload={"mode": mode, "rebuild_memory": rebuild_memory},
        )
        novel_id = str(project.novel_id)
        outline = self.outline_repo.find_by_novel(project.novel_id)
        outline_context = {
            "premise": outline.premise if outline else "",
            "story_background": outline.story_background if outline else "",
            "world_setting": outline.world_setting if outline else "",
            "summary": [outline.premise, outline.story_background] if outline else [],
        }
        chapters = self._build_chapter_units(project.novel_id, mode)
        total_chapters = len(chapters)
        self.logger.info(
            "整理准备完成",
            extra=build_log_context(event="organize_prepare_done", project_id=project_id, total_chapters=total_chapters),
        )
        resume_cursor = 0 if rebuild_memory else max(0, min(int(resume_from or 0), total_chapters))
        merged_memory: Dict[str, Any] = self._empty_structured_memory(outline_context)
        if not rebuild_memory and resume_cursor > 0 and isinstance(checkpoint_memory, dict) and checkpoint_memory:
            merged_memory = checkpoint_memory
            merged_memory["outline_context"] = outline_context
        global_analysis_service = GlobalAnalysisService(self.prompt_ai_service)
        chapter_memory_service = ChapterMemoryService(self.prompt_ai_service)
        project_name = str(getattr(project, "name", "") or project_id)
        global_analysis = await global_analysis_service.analyze_story(
            project_id=project_id,
            project_name=project_name,
            outline_context=outline_context,
            chapters=chapters,
        )
        merged_memory = self._merge_structured_memory(merged_memory, global_analysis, "global_analysis")
        legacy_analysis_tool = None
        if self._should_use_legacy_analysis_tool():
            legacy_analysis_tool = self.analysis_tool_cls(None, None)
        await _emit_progress(
            stage="prepare",
            current=resume_cursor,
            total=total_chapters,
            message=f"准备整理章节（{resume_cursor}/{total_chapters}）",
        )
        chapter_artifacts: List[Dict[str, Any]] = []
        for index, chapter in enumerate(chapters, 1):
            if index <= resume_cursor:
                continue
            self.logger.info(
                "章节分析开始",
                extra=build_log_context(
                    event="chapter_analysis_started",
                    project_id=project_id,
                    chapter_number=index,
                    chapter_title=chapter.get("title") or f"第{index}章",
                    current=index,
                    total=total_chapters,
                ),
            )
            try:
                if legacy_analysis_tool is not None:
                    legacy_result = await legacy_analysis_tool.execute_async(
                        TaskContext(novel_id=novel_id, goal="organize_incremental"),
                        {"mode": "incremental_mode", "chapter": chapter},
                    )
                    if getattr(legacy_result, "status", "") != "success":
                        raise ValueError(f"Chapter analysis failed at {chapter.get('title') or index}")
                bundle = await chapter_memory_service.build_memories(
                    chapter_title=str(chapter.get("title") or ""),
                    chapter_content=str(chapter.get("content") or ""),
                    constraints=merged_memory.get("global_constraints") or {},
                    global_memory_summary=self._build_outline_memory_summary(merged_memory),
                    global_outline_summary=self._build_outline_summary_text(outline_context, merged_memory),
                    recent_chapter_summaries=self._build_recent_outline_summaries(merged_memory),
                )
            except Exception as error:
                self.logger.error(
                    "绔犺妭鍒嗘瀽澶辫触",
                    extra=build_log_context(
                        event="chapter_analysis_failed",
                        project_id=project_id,
                        chapter_number=index,
                        chapter_title=self.clean_text(str(chapter.get("title") or f"Chapter {index}")) or f"Chapter {index}",
                        error=str(error),
                    ),
                )
                raise
            analysis_payload = self._chapter_bundle_to_analysis_payload(bundle, chapter, index)
            merged_memory = self._merge_structured_memory(
                merged_memory,
                analysis_payload,
                chapter.get("title") or "",
                chapter_number=int(chapter.get("index") or index),
                chapter_id=str(chapter.get("id") or ""),
                chapter_content=str(chapter.get("content") or ""),
            )
            self._save_chapter_memory_bundle(project_id, chapter, index, bundle, merged_memory)
            chapter_artifacts.append(
                {
                    "chapter_id": str(chapter.get("id") or ""),
                    "chapter_number": int(chapter.get("index") or index),
                    "chapter_title": str(chapter.get("title") or ""),
                    "analysis_summary": str((bundle.get("analysis_summary") or {}).get("summary") or ""),
                    "scene_summary": str((bundle.get("continuation_memory") or {}).get("scene_summary") or ""),
                    "goal": str((bundle.get("outline_draft") or {}).get("goal") or ""),
                    "conflict": str((bundle.get("outline_draft") or {}).get("conflict") or ""),
                    "ending_hook": str((bundle.get("outline_draft") or {}).get("ending_hook") or ""),
                    "must_continue_points": list((bundle.get("continuation_memory") or {}).get("must_continue_points") or []),
                }
            )
            self.logger.info(
                "绔犺妭鍒嗘瀽瀹屾垚",
                extra=build_log_context(
                    event="chapter_analysis_finished",
                    project_id=project_id,
                    chapter_number=index,
                    chapter_title=self.clean_text(str(chapter.get("title") or f"Chapter {index}")) or f"Chapter {index}",
                ),
            )
            await _emit_progress(
                stage="chapter_analysis",
                current=index,
                total=total_chapters,
                message=f"Analyzed chapter {index}/{total_chapters}: {self.clean_text(str(chapter.get('title') or f'Chapter {index}')) or f'Chapter {index}'}",
                current_chapter_title=self.clean_text(str(chapter.get("title") or f"Chapter {index}")) or f"Chapter {index}",
                resumable=index < total_chapters,
                memory_snapshot=merged_memory,
            )
        if self.plot_arc_service:
            if hasattr(self.prompt_ai_service, "extract_plot_arcs"):
                plot_arc_payload = await self.prompt_ai_service.extract_plot_arcs(
                    {
                        "project_id": project_id,
                        "global_analysis": global_analysis,
                        "chapter_artifacts": chapter_artifacts,
                    }
                )
            else:
                plot_arc_payload = {"plot_arcs": [], "chapter_arc_bindings": [], "active_arc_ids": []}
            merged_memory["plot_arcs"] = list(plot_arc_payload.get("plot_arcs") or [])
            current_state = merged_memory.get("current_state") if isinstance(merged_memory.get("current_state"), dict) else {}
            current_state["active_arc_ids"] = [str(x) for x in (plot_arc_payload.get("active_arc_ids") or []) if str(x).strip()][:5]
            merged_memory["current_state"] = current_state
            self.plot_arc_service.clear_project_arcs(project_id)
            if hasattr(self.chapter_arc_binding_repo, "delete_by_project"):
                self.chapter_arc_binding_repo.delete_by_project(project_id)
            self._save_arc_bindings(project_id, plot_arc_payload.get("chapter_arc_bindings") or [])
        await _emit_progress(
            stage="memory_merge",
            current=total_chapters,
            total=total_chapters,
            message="正在合并章节记忆",
            resumable=False,
        )
        self.logger.info("开始合并记忆", extra=build_log_context(event="memory_merge_started", project_id=project_id))
        memory = dict(merged_memory)
        if self.plot_arc_service:
            chapter_ids = [str(item.get("id") or "") for item in chapters if str(item.get("id") or "").strip()]
            arcs = self.plot_arc_service.extract_initial_arcs(project_id, memory, chapter_ids)
            self.plot_arc_service.enforce_active_arc_limit(project_id, limit=5)
            memory["plot_arcs"] = [self._to_plot_arc_dict(arc) for arc in arcs]
            current_state = memory.get("current_state") if isinstance(memory.get("current_state"), dict) else {}
            current_state["active_arc_ids"] = [arc.arc_id for arc in arcs if arc.status == "active"][:5]
            memory["current_state"] = current_state
        self.logger.info("记忆合并完成", extra=build_log_context(event="memory_merge_finished", project_id=project_id))
        await _emit_progress(
            stage="memory_view_build",
            current=total_chapters,
            total=total_chapters,
            message="正在生成结构摘要",
            resumable=False,
        )
        self.logger.info("开始构建摘要视图", extra=build_log_context(event="memory_view_build_started", project_id=project_id))
        self.project_service.bind_memory_to_novel(NovelId(novel_id), memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        self._sync_primary_repositories(project_id, memory_payload)
        view_payload = self._to_memory_view_payload(project_id, memory_payload)
        self.v2_repo.save_memory_view(view_payload)
        self.logger.info("摘要视图构建完成", extra=build_log_context(event="memory_view_build_finished", project_id=project_id))
        self.v2_repo.finish_workflow_job(
            job_id,
            "success",
            result_payload={"organized_chapter_count": len(chapters), "memory_id": memory_payload["id"]},
        )
        self.logger.info(
            "整理完成",
            extra=build_log_context(
                event="organize_finished",
                project_id=project_id,
                organized_chapter_count=len(chapters),
                memory_id=memory_payload["id"],
            ),
        )
        await _emit_progress(
            stage="done",
            current=total_chapters,
            total=total_chapters,
            message=f"整理完成（{total_chapters}/{total_chapters}）",
            status="done",
            resumable=False,
        )
        return {
            "project_id": project_id,
            "organized_chapter_count": len(chapters),
            "memory_id": memory_payload["id"],
            "memory_view": view_payload,
        }

    def get_memory(self, project_id: str) -> Dict[str, Any]:
        payload = self.v2_repo.find_active_project_memory(project_id) or {}
        return self._hydrate_memory_from_primary_sources(project_id, payload)

    def get_memory_view(self, project_id: str) -> Dict[str, Any]:
        cached = self.v2_repo.find_memory_view(project_id) or {}
        if cached:
            return cached
        memory = self.get_memory(project_id) or {}
        if not memory:
            return {}
        payload = {"id": str(memory.get("id") or f"memory_view_fallback_{uuid.uuid4().hex[:8]}"), **memory}
        view = self._to_memory_view_payload(project_id, payload)
        self.v2_repo.save_memory_view(view)
        return view

    def get_style_requirements(self, project_id: str) -> Dict[str, Any]:
        style_entity = self.style_requirements_repo.find_by_project_id(project_id)
        style_requirements = {
            "author_voice_keywords": list(style_entity.author_voice_keywords or []) if style_entity else [],
            "avoid_patterns": list(style_entity.avoid_patterns or []) if style_entity else [],
            "preferred_rhythm": style_entity.preferred_rhythm if style_entity else "",
            "narrative_distance": style_entity.narrative_distance if style_entity else "",
            "dialogue_density": style_entity.dialogue_density if style_entity else "",
            "source_type": style_entity.source_type if style_entity else STYLE_SOURCE_MANUAL,
            "version": style_entity.version if style_entity else 1,
        }
        return {
            "project_id": project_id,
            "style_requirements": {
                "author_voice_keywords": [str(x) for x in (style_requirements.get("author_voice_keywords") or []) if str(x).strip()],
                "avoid_patterns": [str(x) for x in (style_requirements.get("avoid_patterns") or []) if str(x).strip()],
                "preferred_rhythm": self.clean_text(str(style_requirements.get("preferred_rhythm") or "")),
                "narrative_distance": self.clean_text(str(style_requirements.get("narrative_distance") or "")),
                "dialogue_density": self.clean_text(str(style_requirements.get("dialogue_density") or "")),
                "source_type": self.clean_text(str(style_requirements.get("source_type") or STYLE_SOURCE_MANUAL)),
                "version": int(style_requirements.get("version") or 1),
            },
        }

    def update_style_requirements(self, project_id: str, style_requirements: Dict[str, Any]) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        outline_context = self._get_outline_context(project.novel_id)
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        incoming = style_requirements if isinstance(style_requirements, dict) else {}
        current = memory.get("style_requirements") if isinstance(memory.get("style_requirements"), dict) else {}
        merged = {
            "author_voice_keywords": self.normalize_text_list(
                [str(x) for x in ((incoming.get("author_voice_keywords") if "author_voice_keywords" in incoming else current.get("author_voice_keywords")) or [])],
                20,
            ),
            "avoid_patterns": self.normalize_text_list(
                [str(x) for x in ((incoming.get("avoid_patterns") if "avoid_patterns" in incoming else current.get("avoid_patterns")) or [])],
                20,
            ),
            "preferred_rhythm": self.clean_text(str(incoming.get("preferred_rhythm") if "preferred_rhythm" in incoming else current.get("preferred_rhythm") or "")),
            "narrative_distance": self.clean_text(str(incoming.get("narrative_distance") if "narrative_distance" in incoming else current.get("narrative_distance") or "")),
            "dialogue_density": self.clean_text(str(incoming.get("dialogue_density") if "dialogue_density" in incoming else current.get("dialogue_density") or "")),
            "source_type": self.clean_text(str(incoming.get("source_type") if "source_type" in incoming else current.get("source_type") or STYLE_SOURCE_MANUAL)),
            "version": max(1, int(incoming.get("version") if "version" in incoming else current.get("version") or 1)),
        }
        memory["style_requirements"] = merged
        self.project_service.bind_memory_to_novel(project.novel_id, memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        self._sync_primary_repositories(project_id, memory_payload)
        self.v2_repo.save_memory_view(self._to_memory_view_payload(project_id, memory_payload))
        if self.plot_arc_service:
            self.plot_arc_service.enforce_active_arc_limit(project_id, limit=5)
        return {"project_id": project_id, "style_requirements": merged}

    def extract_style_requirements_from_samples(self, project_id: str, sample_chapter_count: int = 3) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        chapters = sorted(self.chapter_repo.find_by_novel(project.novel_id), key=lambda x: x.number)
        sample_size = max(1, min(int(sample_chapter_count or 3), 10))
        picked = chapters[-sample_size:]
        texts = [str(item.content or "") for item in picked if str(item.content or "").strip()]
        if not texts:
            raise ValueError("样章内容为空，无法提取风格要求")
        inferred = self._infer_style_requirements_from_samples(texts)
        return self.update_style_requirements(project_id, inferred)

    def list_chapter_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        return [self._chapter_task_to_dict(item) for item in (self.chapter_task_repo.find_by_project_id(project_id) or [])]

    def get_chapter_editor_context(self, project_id: str, chapter_number: int = 0, recent_limit: int = 5) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "加载章节编辑上下文",
            extra=build_log_context(
                event="chapter_context_loaded",
                project_id=project_id,
                chapter_number=chapter_number,
                recent_limit=recent_limit,
            ),
        )
        memory_view = self.get_memory_view(project_id) or {}
        memory_payload = self.get_memory(project_id) or {}
        chapters = sorted(self.chapter_repo.find_by_novel(project.novel_id), key=lambda x: x.number)
        if chapter_number > 0:
            history = [ch for ch in chapters if ch.number < chapter_number]
        else:
            history = chapters
        recent = history[-max(1, int(recent_limit)) :]
        recent_summaries = []
        for item in recent:
            summary = self.clean_text((item.content or "").strip().replace("\n", " ")[:120])
            if summary:
                recent_summaries.append(f"第{item.number}章 {item.title}：{summary}")
        outline_summary = memory_view.get("outline_summary") or []
        if not outline_summary:
            outline_ctx = memory_payload.get("outline_context") or {}
            outline_summary = [
                str(x).strip()
                for x in (outline_ctx.get("summary") or [])
                if str(x).strip()
            ]
        global_memory_summary = "；".join([str(x).strip() for x in (memory_view.get("main_plot_lines") or []) if str(x).strip()])
        if not global_memory_summary:
            global_memory_summary = self.clean_text(str(memory_view.get("current_progress") or ""))
        current_chapter = next((ch for ch in chapters if int(ch.number or 0) == int(chapter_number or 0)), None)
        chapter_outline = {}
        chapter_task_seed = {}
        continuation_summary = {}
        chapter_arcs: List[Dict[str, Any]] = []
        if current_chapter:
            outline_entity = self.chapter_outline_repo.find_by_chapter_id(current_chapter.id)
            chapter_outline = self._chapter_outline_to_dict(outline_entity) if outline_entity else {}
            task_entity = next((item for item in (self.chapter_task_repo.find_by_project_id(project_id) or []) if int(getattr(item, "chapter_number", 0) or 0) == int(chapter_number or 0)), None)
            chapter_task_seed = self._chapter_task_to_dict(task_entity) if task_entity else {}
            continuation_entity = next((item for item in (self.chapter_continuation_memory_repo.find_by_chapter_id(current_chapter.id.value) or [])), None)
            continuation_summary = self._chapter_continuation_memory_to_dict(continuation_entity) if continuation_entity else {}
            chapter_arcs = [self._to_chapter_arc_binding_dict(item) for item in (self.chapter_arc_binding_repo.list_by_chapter(current_chapter.id.value) or [])]
        return {
            "project_id": project_id,
            "memory_view": memory_view,
            "outline_summary": outline_summary[:6],
            "recent_chapter_summaries": recent_summaries,
            "current_progress": self.clean_text(str(memory_view.get("current_progress") or "")),
            "global_memory_summary": global_memory_summary,
            "global_outline_summary": "；".join([str(x).strip() for x in outline_summary[:6] if str(x).strip()]),
            "chapter_outline": chapter_outline,
            "chapter_task_seed": chapter_task_seed,
            "continuation_summary": continuation_summary,
            "chapter_arcs": chapter_arcs,
        }

    def upsert_imported_chapter_artifacts(
        self,
        project_id: str,
        chapter: Chapter,
        outline_draft: Dict[str, Any],
        continuation_memory: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = datetime.now()
        continuation = continuation_memory if isinstance(continuation_memory, dict) else {}
        continuation_entity = ChapterContinuationMemory(
            id=str(continuation.get("id") or f"ccm_{uuid.uuid4().hex[:10]}"),
            chapter_id=chapter.id.value,
            chapter_number=int(chapter.number or 0),
            chapter_title=str(chapter.title or ""),
            scene_summary=str(continuation.get("scene_summary") or ""),
            scene_state=continuation.get("scene_state") or {},
            protagonist_state=continuation.get("protagonist_state") or {},
            active_characters=continuation.get("active_characters") or [],
            active_conflicts=[str(x) for x in (continuation.get("active_conflicts") or [])],
            immediate_threads=[str(x) for x in (continuation.get("immediate_threads") or [])],
            long_term_threads=[str(x) for x in (continuation.get("long_term_threads") or [])],
            recent_reveals=[str(x) for x in (continuation.get("recent_reveals") or [])],
            must_continue_points=[str(x) for x in (continuation.get("must_continue_points") or [])],
            forbidden_jumps=[str(x) for x in (continuation.get("forbidden_jumps") or [])],
            tone_and_pacing=continuation.get("tone_and_pacing") or {},
            last_hook=str(continuation.get("last_hook") or ""),
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.chapter_continuation_memory_repo.save(continuation_entity)
        arc_target_id = ""
        arc_stage_before = ""
        arc_stage_after_expected = ""
        if self.arc_planning_service:
            arc_pick = self.arc_planning_service.select_arcs(
                project_id=project_id,
                planning_mode=PLANNING_MODE_LIGHT,
                preferred_arc_id="",
                allow_deep_planning=False,
                trigger_context={},
            )
            arc_target = arc_pick.get("target_arc")
            arc_target_id = str(getattr(arc_target, "arc_id", "") or "")
            arc_stage_before = str(getattr(arc_target, "current_stage", "") or "")
            arc_stage_after_expected = self._predict_next_arc_stage(arc_stage_before) if arc_stage_before else ""
        task_entity = ChapterTask(
            id=f"task_{uuid.uuid4().hex[:10]}",
            chapter_id=chapter.id.value,
            project_id=project_id,
            branch_id="",
            chapter_number=int(chapter.number or 0),
            chapter_function="advance_investigation",
            goals=[str(outline_draft.get("goal") or "")] if str(outline_draft.get("goal") or "").strip() else [],
            must_continue_points=[str(x) for x in (continuation.get("must_continue_points") or [])],
            forbidden_jumps=[str(x) for x in (continuation.get("forbidden_jumps") or [])],
            opening_continuation=str(outline_draft.get("opening_continuation") or ""),
            chapter_payoff=str(outline_draft.get("ending_hook") or ""),
            target_arc_id=arc_target_id,
            arc_stage_before=arc_stage_before,
            arc_stage_after_expected=arc_stage_after_expected,
            arc_push_goal=str(outline_draft.get("goal") or ""),
            arc_conflict_focus=str(outline_draft.get("conflict") or ""),
            arc_payoff_expectation=str(outline_draft.get("ending_hook") or ""),
            planning_mode=PLANNING_MODE_LIGHT,
            created_at=now,
            updated_at=now,
        )
        self.chapter_task_repo.save(task_entity)
        analysis_entity = ChapterAnalysisMemory(
            id=f"cam_{uuid.uuid4().hex[:10]}",
            chapter_id=chapter.id.value,
            chapter_number=int(chapter.number or 0),
            chapter_title=str(chapter.title or ""),
            summary=str(continuation.get("scene_summary") or outline_draft.get("goal") or ""),
            events=[str(x) for x in (outline_draft.get("events") or [])],
            plot_role=str(outline_draft.get("goal") or ""),
            conflict=str(outline_draft.get("conflict") or ""),
            hook=str(outline_draft.get("ending_hook") or ""),
            primary_arc_id=arc_target_id,
            arc_push_summary=str(outline_draft.get("goal") or ""),
            arc_stage_impact=f"{arc_stage_before}->{arc_stage_after_expected}" if arc_stage_before or arc_stage_after_expected else "",
            created_at=now,
            updated_at=now,
        )
        self.chapter_analysis_memory_repo.save(analysis_entity)
        if arc_target_id:
            self.arc_writeback_service.writeback_chapter_arc(
                project_id=project_id,
                chapter_id=chapter.id.value,
                chapter_number=int(chapter.number or 0),
                target_arc_id=arc_target_id,
                progress_summary="",
                binding_role="primary",
                push_type="stabilize",
            )
        return {
            "chapter_task_seed": self._chapter_task_to_dict(task_entity),
            "chapter_analysis_summary": self._chapter_analysis_memory_to_dict(analysis_entity),
            "continuation_summary": self._chapter_continuation_memory_to_dict(continuation_entity),
        }

    def build_continuation_context(self, project_id: str, chapter_id: str, chapter_number: int = 0) -> ContinuationContext:
        memory = self.get_memory(project_id) or {}
        chapters = []
        project = self.project_service.get_project(ProjectId(project_id))
        if project:
            chapters = sorted(self.chapter_repo.find_by_novel(project.novel_id), key=lambda x: x.number)
        recent_limit = max(2, int(CONTINUATION_CONTEXT_RECENT_CHAPTER_LIMIT or 3))
        history = [ch for ch in chapters if not chapter_number or int(ch.number or 0) < int(chapter_number or 0)]
        recent_real_chapters = history[-recent_limit:]
        recent_memories = []
        for recent_chapter in recent_real_chapters:
            chapter_memories = self.chapter_continuation_memory_repo.find_by_chapter_id(recent_chapter.id.value) or []
            if chapter_memories:
                recent_memories.append(self._chapter_continuation_memory_to_dict(chapter_memories[0]))
        chapter_outline = {}
        if chapter_id:
            try:
                chapter_outline_entity = self._get_chapter_outline_entity(chapter_id)
                chapter_outline = self._chapter_outline_to_dict(chapter_outline_entity) if chapter_outline_entity else {}
            except Exception:
                chapter_outline = {}
        tail_chars = max(LAST_CHAPTER_TAIL_MIN_CHARS, min(DEFAULT_LAST_CHAPTER_TAIL_CHARS, LAST_CHAPTER_TAIL_MAX_CHARS))
        last_tail_source = recent_real_chapters[-1].content if recent_real_chapters else (chapters[-1].content if chapters else "")
        last_tail = str(last_tail_source or "")[-tail_chars:]
        relevant_characters = []
        recent_text = " ".join([str(item.get("scene_summary") or "") for item in recent_memories if isinstance(item, dict)])
        for character in (memory.get("characters") or []):
            if isinstance(character, dict):
                name = str(character.get("name") or character.get("character_name") or "").strip()
                if not name or name in recent_text or len(relevant_characters) < 3:
                    relevant_characters.append(character)
            if len(relevant_characters) >= 6:
                break
        relevant_foreshadowing = []
        recent_numbers = {int(item.get("chapter_number") or 0) for item in recent_memories if isinstance(item, dict)}
        for item in memory.get("chapter_analysis_memories") or []:
            if isinstance(item, dict):
                if not recent_numbers or int(item.get("chapter_number") or 0) in recent_numbers:
                    relevant_foreshadowing.extend([str(x) for x in (item.get("foreshadowing") or []) if str(x).strip()])
        relevant_foreshadowing.extend([str(x) for x in ((memory.get("global_constraints") or {}).get("must_keep_threads") or []) if str(x).strip()])
        task_seed = {}
        task_items = self.chapter_task_repo.find_by_project_id(project_id) or []
        if chapter_number > 0:
            matched = [item for item in task_items if int(getattr(item, "chapter_number", 0) or 0) == int(chapter_number)]
            if matched:
                task_seed = self._chapter_task_to_dict(matched[-1])
        if not task_seed and (memory.get("chapter_tasks") or []):
            task_seed = (memory.get("chapter_tasks") or [])[-1]
        active_arcs = [self._to_plot_arc_dict(arc) for arc in (self.plot_arc_service.list_active_arcs(project_id) if self.plot_arc_service else [])]
        target_arc = {}
        if isinstance(task_seed, dict):
            target_arc_id = str(task_seed.get("target_arc_id") or "").strip()
            if target_arc_id:
                target_arc = next((item for item in active_arcs if str(item.get("arc_id") or "") == target_arc_id), {})
        recent_arc_progress: List[Dict[str, Any]] = []
        arc_bindings = [self._to_chapter_arc_binding_dict(item) for item in self.chapter_arc_binding_repo.list_by_chapter(chapter_id)] if chapter_id else []
        arc_ids_for_progress = [str(item.get("arc_id") or "") for item in arc_bindings if str(item.get("arc_id") or "").strip()]
        if not arc_ids_for_progress and target_arc:
            arc_ids_for_progress = [str(target_arc.get("arc_id") or "")]
        if not arc_ids_for_progress:
            arc_ids_for_progress = [str(item.get("arc_id") or "") for item in active_arcs[:3] if str(item.get("arc_id") or "").strip()]
        recent_arc_progress = self._load_recent_arc_progress(arc_ids_for_progress, limit=10)
        return ContinuationContext(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            recent_chapter_memories=recent_memories,
            last_chapter_tail=last_tail,
            relevant_characters=relevant_characters,
            relevant_foreshadowing=self.normalize_text_list(relevant_foreshadowing, 12),
            global_constraints=memory.get("global_constraints") or {},
            chapter_outline=chapter_outline,
            chapter_task_seed=task_seed if isinstance(task_seed, dict) else {},
            active_arcs=active_arcs,
            target_arc=target_arc,
            recent_arc_progress=recent_arc_progress,
            arc_bindings=arc_bindings,
            style_requirements=memory.get("style_requirements") or {},
        )

    def _load_recent_arc_progress(self, arc_ids: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        snapshots: List[Dict[str, Any]] = []
        for arc_id in [str(x).strip() for x in (arc_ids or []) if str(x).strip()]:
            for item in (self.arc_progress_snapshot_repo.list_by_arc(arc_id) or [])[:3]:
                snapshots.append(
                    {
                        "snapshot_id": str(getattr(item, "snapshot_id", "") or ""),
                        "arc_id": str(getattr(item, "arc_id", "") or ""),
                        "chapter_id": str(getattr(item, "chapter_id", "") or ""),
                        "chapter_number": int(getattr(item, "chapter_number", 0) or 0),
                        "stage_before": str(getattr(item, "stage_before", "") or ""),
                        "stage_after": str(getattr(item, "stage_after", "") or ""),
                        "progress_summary": str(getattr(item, "progress_summary", "") or ""),
                        "change_reason": str(getattr(item, "change_reason", "") or ""),
                        "new_conflicts": list(getattr(item, "new_conflicts", []) or []),
                        "new_payoffs": list(getattr(item, "new_payoffs", []) or []),
                        "created_at": str((getattr(item, "created_at", None) or datetime.now()).isoformat()),
                    }
                )
        snapshots.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return snapshots[: max(1, int(limit or 10))]

    def list_workflow_jobs(self, project_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        return self.v2_repo.list_workflow_jobs(project_id, limit)

    def list_writing_sessions(self, project_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        return self.v2_repo.list_writing_sessions(project_id, limit)

    def get_project_trace(self, project_id: str) -> Dict[str, Any]:
        memory = self.get_memory(project_id)
        view = self.get_memory_view(project_id)
        jobs = self.list_workflow_jobs(project_id, 10)
        sessions = self.list_writing_sessions(project_id, 10)
        latest_job = jobs[0] if jobs else {}
        latest_session = sessions[0] if sessions else {}
        return {
            "project_id": project_id,
            "memory_version": int(memory.get("version") or 0),
            "latest_progress": str(view.get("current_progress") or ""),
            "latest_workflow_job": latest_job,
            "latest_writing_session": latest_session,
        }

    async def generate_branches(self, project_id: str, direction_hint: str, branch_count: int) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "分支生成开始",
            extra=build_log_context(event="branches_started", project_id=project_id, branch_count=branch_count),
        )
        outline_context = self._get_outline_context(project.novel_id)
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        chapters = self.chapter_repo.find_by_novel(project.novel_id)
        latest = chapters[-1].content if chapters else ""
        branch_primary, branch_backup = self._get_role_clients(ModelRole.CHAPTER_PLANNING, project_id=project_id)
        tool = StoryBranchTool(branch_primary, branch_backup)
        result = await tool.execute_async(
            TaskContext(novel_id=str(project.novel_id), goal=direction_hint, target_word_count=0),
            {
                "memory": self._to_tool_memory_context(memory),
                "current_chapter_content": latest,
                "direction_hint": direction_hint,
                "branch_count": branch_count,
            },
        )
        if result.status != "success":
            self.logger.error("分支生成失败", extra=build_log_context(event="branches_failed", project_id=project_id, branch_count=branch_count))
            self.logger.error(
                "模型职责执行失败",
                extra=build_log_context(
                    event="model_role_failed",
                    project_id=project_id,
                    task_role=ModelRole.CHAPTER_PLANNING.value,
                    model_name="kimi",
                    used_fallback=bool(str(os.getenv("INKTRACE_MODEL_ROLE_MODE", "strict")).lower() == "degraded"),
                    error="branch_generation_failed",
                ),
            )
            raise ValueError("分支生成失败")
        branches = []
        for idx, item in enumerate((result.payload or {}).get("branches") or [], 1):
            generated_id = str(item.get("id") or "").strip()
            if not generated_id:
                generated_id = f"branch_{uuid.uuid4().hex[:8]}"
            else:
                generated_id = f"{project_id[:8]}_{generated_id}_{idx}"
            branches.append(
                {
                    "id": generated_id,
                    "project_id": project_id,
                    "title": item.get("title") or "",
                    "summary": item.get("summary") or "",
                    "core_conflict": item.get("impact") or "",
                    "key_progressions": [item.get("next_goal") or ""],
                    "related_characters": [c.get("name") for c in (memory.get("characters") or []) if isinstance(c, dict)][:3],
                    "style_tags": [item.get("tone") or ""],
                    "consistency_note": self._build_outline_consistency_note(item, outline_context),
                    "risk_note": self._build_outline_risk_note(item, outline_context),
                    "status": "candidate",
                }
            )
        self.v2_repo.replace_branches(project_id, branches)
        self.logger.info("分支生成完成", extra=build_log_context(event="branches_finished", project_id=project_id, branch_count=len(branches)))
        return {"project_id": project_id, "branches": branches}

    async def create_chapter_plan(
        self,
        project_id: str,
        branch_id: str,
        chapter_count: int,
        target_words_per_chapter: int,
        planning_mode: str = "light_planning",
        target_arc_id: str = "",
        allow_deep_planning: bool = False,
    ) -> Dict[str, Any]:
        return await self.chapter_planning_service.create_chapter_plan(
            project_id=project_id,
            branch_id=branch_id,
            chapter_count=chapter_count,
            target_words_per_chapter=target_words_per_chapter,
            planning_mode=planning_mode,
            target_arc_id=target_arc_id,
            allow_deep_planning=allow_deep_planning,
        )

    async def execute_write_preview(
        self,
        project_id: str,
        plan_id: str,
        target_word_count: int = 0,
        style_requirements: Optional[Dict[str, Any]] = None,
        planning_mode: str = "light_planning",
        target_arc_id: str = "",
    ) -> Dict[str, Any]:
        return await self.writing_service_v2.execute_write_preview(
            project_id=project_id,
            plan_id=plan_id,
            target_word_count=target_word_count,
            style_requirements=style_requirements,
            planning_mode=planning_mode,
            target_arc_id=target_arc_id,
        )

    async def execute_write_commit(
        self,
        project_id: str,
        plan_ids: List[str],
        chapter_count: int,
        auto_commit: bool = True,
        planning_mode: str = "light_planning",
        target_arc_id: str = "",
    ) -> Dict[str, Any]:
        return await self.writing_service_v2.execute_write_commit(
            project_id=project_id,
            plan_ids=plan_ids,
            chapter_count=chapter_count,
            auto_commit=auto_commit,
            planning_mode=planning_mode,
            target_arc_id=target_arc_id,
        )

    async def execute_writing(self, project_id: str, plan_ids: List[str], auto_commit: bool) -> Dict[str, Any]:
        return await self.writing_service_v2.execute_writing(
            project_id=project_id,
            plan_ids=plan_ids,
            auto_commit=auto_commit,
        )

    def _build_generated_continuation_memory(self, chapter_task: Dict[str, Any], chapter_plan: Dict[str, Any], structural_draft: Dict[str, Any], detemplated_draft: Dict[str, Any]) -> Dict[str, Any]:
        display_content = str(structural_draft.get("content") or "") if detemplated_draft.get("display_fallback_to_structural") else str(detemplated_draft.get("content") or "")
        return {
            "id": f"runtime_ccm_{uuid.uuid4().hex[:8]}",
            "chapter_id": str(detemplated_draft.get("chapter_id") or chapter_task.get("chapter_id") or ""),
            "chapter_number": int(detemplated_draft.get("chapter_number") or chapter_task.get("chapter_number") or 0),
            "chapter_title": str(detemplated_draft.get("title") or structural_draft.get("title") or ""),
            "scene_summary": display_content[:150],
            "scene_state": {"ending_scene": display_content[-120:]},
            "protagonist_state": {"current_goal": str(chapter_plan.get("goal") or "")},
            "active_characters": [],
            "active_conflicts": [str(chapter_plan.get("conflict") or "")] if str(chapter_plan.get("conflict") or "").strip() else [],
            "immediate_threads": [str(chapter_plan.get("progression") or "")] if str(chapter_plan.get("progression") or "").strip() else [],
            "long_term_threads": [str(x) for x in (chapter_task.get("must_continue_points") or [])[:3]],
            "recent_reveals": [str(chapter_plan.get("goal") or "")] if str(chapter_plan.get("goal") or "").strip() else [],
            "must_continue_points": [str(x) for x in (chapter_task.get("must_continue_points") or [])],
            "forbidden_jumps": [str(x) for x in (chapter_task.get("forbidden_jumps") or [])],
            "tone_and_pacing": {"pace_target": str(chapter_task.get("pace_target") or "")},
            "last_hook": str(chapter_plan.get("ending_hook") or chapter_task.get("chapter_payoff") or ""),
            "active_arc_ids": [str(x) for x in (chapter_plan.get("related_arc_ids") or []) if str(x).strip()][:5],
            "target_arc_id": str(chapter_task.get("target_arc_id") or chapter_plan.get("target_arc_id") or ""),
            "target_arc_stage": str(chapter_task.get("arc_stage_before") or chapter_plan.get("arc_stage_before") or ""),
            "arc_must_continue_points": [str(x) for x in (chapter_task.get("must_continue_points") or [])[:3]],
        }

    async def refresh_memory(self, project_id: str, from_chapter_number: int, to_chapter_number: int) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "刷新记忆开始",
            extra=build_log_context(
                event="refresh_memory_started",
                project_id=project_id,
                from_chapter_number=from_chapter_number,
                to_chapter_number=to_chapter_number,
            ),
        )
        chapters = self.chapter_repo.find_by_novel(project.novel_id)
        selected = [c for c in chapters if from_chapter_number <= c.number <= to_chapter_number]
        outline_context = self._get_outline_context(project.novel_id)
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        memory["outline_context"] = outline_context
        chapter_memory_service = ChapterMemoryService(self.prompt_ai_service)
        chapter_artifacts: List[Dict[str, Any]] = []
        for chapter in selected:
            bundle = await chapter_memory_service.build_memories(
                chapter_title=str(chapter.title or ""),
                chapter_content=str(chapter.content or ""),
                constraints=memory.get("global_constraints") or {},
                global_memory_summary=self._build_outline_memory_summary(memory),
                global_outline_summary=self._build_outline_summary_text(outline_context, memory),
                recent_chapter_summaries=self._build_recent_outline_summaries(memory),
            )
            analysis_payload = self._chapter_bundle_to_analysis_payload(
                bundle,
                {"id": chapter.id.value, "index": chapter.number, "title": chapter.title, "content": chapter.content},
                chapter.number,
            )
            memory = self._merge_structured_memory(
                memory,
                analysis_payload,
                chapter.title or f"Chapter {chapter.number}",
                chapter_number=chapter.number,
                chapter_id=chapter.id.value,
                chapter_content=chapter.content or "",
            )
            self._save_chapter_memory_bundle(
                project_id,
                {"id": chapter.id.value, "index": chapter.number, "title": chapter.title, "content": chapter.content},
                chapter.number,
                bundle,
                memory,
            )
            chapter_artifacts.append(
                {
                    "chapter_id": chapter.id.value,
                    "chapter_number": chapter.number,
                    "chapter_title": chapter.title,
                    "analysis_summary": str((bundle.get("analysis_summary") or {}).get("summary") or ""),
                    "scene_summary": str((bundle.get("continuation_memory") or {}).get("scene_summary") or ""),
                    "goal": str((bundle.get("outline_draft") or {}).get("goal") or ""),
                    "conflict": str((bundle.get("outline_draft") or {}).get("conflict") or ""),
                    "ending_hook": str((bundle.get("outline_draft") or {}).get("ending_hook") or ""),
                    "must_continue_points": list((bundle.get("continuation_memory") or {}).get("must_continue_points") or []),
                }
            )
        if self.plot_arc_service and selected:
            if hasattr(self.prompt_ai_service, "extract_plot_arcs"):
                plot_arc_payload = await self.prompt_ai_service.extract_plot_arcs(
                    {
                        "project_id": project_id,
                        "global_analysis": {
                            "main_plot_lines": self._build_plot_lines(memory),
                            "characters": memory.get("characters") or [],
                            "world_facts": memory.get("world_facts") or {},
                        },
                        "chapter_artifacts": chapter_artifacts,
                    }
                )
            else:
                plot_arc_payload = {"plot_arcs": memory.get("plot_arcs") or [], "chapter_arc_bindings": [], "active_arc_ids": []}
            memory["plot_arcs"] = list(plot_arc_payload.get("plot_arcs") or memory.get("plot_arcs") or [])
            current_state = memory.get("current_state") if isinstance(memory.get("current_state"), dict) else {}
            current_state["active_arc_ids"] = [str(x) for x in (plot_arc_payload.get("active_arc_ids") or []) if str(x).strip()][:5]
            memory["current_state"] = current_state
            self._save_arc_bindings(project_id, plot_arc_payload.get("chapter_arc_bindings") or [])
        self.project_service.bind_memory_to_novel(project.novel_id, memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        self._sync_primary_repositories(project_id, memory_payload)
        view_payload = self._to_memory_view_payload(project_id, memory_payload)
        self.v2_repo.save_memory_view(view_payload)
        self.logger.info(
            "刷新记忆完成",
            extra=build_log_context(
                event="refresh_memory_finished",
                project_id=project_id,
                from_chapter_number=from_chapter_number,
                to_chapter_number=to_chapter_number,
            ),
        )
        return {"project_id": project_id, "memory_view": view_payload}

    def _ensure_chapter_title(self, title: str, chapter_number: int) -> str:
        text = self.clean_text(str(title or "")).strip()
        return text or f"第{chapter_number}章"

    def _normalize_generated_chapter_output(self, chapter_text: str, plan_title: str, chapter_number: int) -> Dict[str, Any]:
        raw = str(chapter_text or "").strip()
        title = self.clean_text(str(plan_title or "")).strip()
        content = raw
        if raw.startswith("{") and raw.endswith("}"):
            try:
                payload = json.loads(raw)
            except Exception:
                payload = None
            if isinstance(payload, dict):
                title = self.clean_text(str(payload.get("title") or payload.get("chapter_title") or title)).strip()
                extracted = payload.get("content") or payload.get("chapter_text") or payload.get("result_text") or ""
                content = str(extracted or "").strip()
        if not content:
            content = raw
        safe_no = int(chapter_number or 0)
        if not title and safe_no > 0:
            title = CHAPTER_TITLE_FALLBACK_TEMPLATE.format(chapter_number=safe_no)
        return {"chapter_number": safe_no, "title": title, "content": content}

    def _build_global_constraints(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        chapter_summaries = [self.clean_text(str(x)) for x in (memory.get("chapter_summaries") or []) if str(x).strip()]
        plot_lines = self._build_plot_lines(memory)
        protagonist_traits: List[str] = []
        for char in (memory.get("characters") or []):
            if isinstance(char, dict):
                protagonist_traits.extend([str(x) for x in (char.get("traits") or []) if str(x).strip()])
        return {
            "main_plot": plot_lines[0] if plot_lines else "",
            "hidden_plot": plot_lines[1] if len(plot_lines) > 1 else "",
            "core_selling_points": self.normalize_text_list(plot_lines[:5], 8),
            "protagonist_core_traits": self.normalize_text_list(protagonist_traits, 12),
            "must_keep_threads": self.normalize_text_list(chapter_summaries[-10:], 12),
            "genre_guardrails": self.normalize_text_list([str(memory.get("outline_context", {}).get("premise") or "")], 6),
        }

    def _build_style_requirements(self, style_profile: Dict[str, Any]) -> Dict[str, Any]:
        style = style_profile if isinstance(style_profile, dict) else {}
        return {
            "author_voice_keywords": self.normalize_text_list([str(x) for x in (style.get("tone_tags") or [])], 10),
            "avoid_patterns": [],
            "preferred_rhythm": self.clean_text(str("、".join([str(x) for x in (style.get("rhythm_tags") or []) if str(x).strip()]))),
            "narrative_distance": self.clean_text(str(style.get("narrative_pov") or "")),
            "dialogue_density": DEFAULT_DIALOGUE_DENSITY,
            "source_type": STYLE_SOURCE_MANUAL,
            "version": 1,
        }

    def _infer_style_requirements_from_samples(self, sample_texts: List[str]) -> Dict[str, Any]:
        full_text = "\n".join([str(x) for x in sample_texts if str(x).strip()])
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        dialogue_lines = [line for line in lines if any(token in line for token in ["“", "”", "\""])]
        dialogue_ratio = (len(dialogue_lines) / len(lines)) if lines else 0
        if dialogue_ratio >= 0.45:
            dialogue_density = "high"
        elif dialogue_ratio >= 0.2:
            dialogue_density = "medium"
        else:
            dialogue_density = "low"
        question_marks = full_text.count("？") + full_text.count("?")
        exclamations = full_text.count("！") + full_text.count("!")
        ellipsis = full_text.count("……") + full_text.count("...")
        if exclamations + question_marks >= 12:
            preferred_rhythm = "fast"
        elif ellipsis >= 4:
            preferred_rhythm = "slow_pressure"
        else:
            preferred_rhythm = DEFAULT_PREFERRED_RHYTHM
        narrative_distance = DEFAULT_NARRATIVE_DISTANCE
        if full_text.count("我") >= 18 and full_text.count("他") < full_text.count("我"):
            narrative_distance = "first_person"
        keyword_candidates = ["紧张", "压迫", "悬疑", "克制", "冷峻", "热血", "细腻", "肃杀", "诙谐", "悲怆"]
        voice_keywords = [item for item in keyword_candidates if item in full_text][:5]
        if not voice_keywords:
            voice_keywords = ["紧凑", "画面感"]
        avoid_patterns = []
        if "与此同时" in full_text:
            avoid_patterns.append("与此同时")
        if "下一刻" in full_text:
            avoid_patterns.append("下一刻")
        if "不由得" in full_text:
            avoid_patterns.append("不由得")
        return {
            "author_voice_keywords": voice_keywords,
            "avoid_patterns": avoid_patterns,
            "preferred_rhythm": preferred_rhythm,
            "narrative_distance": narrative_distance,
            "dialogue_density": dialogue_density,
            "source_type": STYLE_SOURCE_SAMPLE,
            "version": 1,
        }

    def _detemplate_content(self, content: str, style_requirements: Dict[str, Any], chapter_task: Dict[str, Any]) -> str:
        text = str(content or "").strip()
        if not text:
            return ""
        avoid_patterns = [str(x).strip() for x in ((style_requirements or {}).get("avoid_patterns") or []) if str(x).strip()]
        defaults = ["与此同时", "下一刻", "不由得", "仿佛", "毫无疑问"]
        for phrase in [*defaults, *avoid_patterns]:
            text = text.replace(phrase, "")
        style_bias = self.clean_text(str((chapter_task or {}).get("style_bias") or ""))
        if style_bias and style_bias not in text[:100]:
            text = f"{style_bias}。{text}"
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    def _check_draft_integrity(self, structural_draft: Dict[str, Any], detemplated_draft: Dict[str, Any], chapter_task: Dict[str, Any]) -> Dict[str, Any]:
        source = str(structural_draft.get("content") or "")
        target = str(detemplated_draft.get("content") or "")
        must_continue = [str(x) for x in ((chapter_task or {}).get("must_continue_points") or []) if str(x).strip()]
        forbidden = [str(x) for x in ((chapter_task or {}).get("forbidden_jumps") or []) if str(x).strip()]
        risk_notes: List[str] = []
        if not target:
            risk_notes.append("去模板化后正文为空")
        event_integrity_ok = len(target) >= max(200, int(len(source) * 0.5)) if source else bool(target)
        if not event_integrity_ok:
            risk_notes.append("事件信息疑似丢失")
        motivation_integrity_ok = True
        if must_continue:
            missing = [item for item in must_continue if item not in target]
            motivation_integrity_ok = len(missing) <= max(1, len(must_continue) // 2)
            if not motivation_integrity_ok:
                risk_notes.append("关键承接点缺失过多")
        foreshadowing_integrity_ok = True
        if self._normalize_foreshadowing_action(str(chapter_task.get("required_foreshadowing_action") or "")) == FORESHADOWING_ACTION_RETRIEVE and "伏笔" not in target:
            foreshadowing_integrity_ok = False
            risk_notes.append("要求回收伏笔但正文未体现")
        hook_integrity_ok = self._normalize_hook_strength(str(chapter_task.get("required_hook_strength") or DEFAULT_HOOK_STRENGTH)) != HOOK_STRENGTH_STRONG or any(x in target[-60:] for x in ["？", "！", "……"])
        if not hook_integrity_ok:
            risk_notes.append("章节结尾钩子强度不足")
        continuity_ok = True
        violated = [item for item in forbidden if item and item in target]
        if violated:
            continuity_ok = False
            risk_notes.append(f"触发禁跳项: {'、'.join(violated[:3])}")
        arc_consistency_ok = True
        target_arc_id = str(chapter_task.get("target_arc_id") or "").strip()
        arc_push_goal = str(chapter_task.get("arc_push_goal") or "").strip()
        arc_conflict_focus = str(chapter_task.get("arc_conflict_focus") or "").strip()
        arc_payoff_expectation = str(chapter_task.get("arc_payoff_expectation") or "").strip()
        if target_arc_id:
            arc_signals = [item for item in [arc_push_goal, arc_conflict_focus, arc_payoff_expectation] if item]
            if arc_signals:
                matched = sum(1 for item in arc_signals if item in target)
                arc_consistency_ok = matched >= 1
                if not arc_consistency_ok:
                    risk_notes.append("目标剧情弧推进信号不足")
        return {
            "chapter_number": int(structural_draft.get("chapter_number") or 0),
            "event_integrity_ok": event_integrity_ok,
            "motivation_integrity_ok": motivation_integrity_ok,
            "foreshadowing_integrity_ok": foreshadowing_integrity_ok,
            "hook_integrity_ok": hook_integrity_ok,
            "continuity_ok": continuity_ok,
            "arc_consistency_ok": arc_consistency_ok,
            "risk_notes": risk_notes,
        }

    def _is_integrity_ok(self, check: Dict[str, Any]) -> bool:
        return bool(
            check.get("event_integrity_ok")
            and check.get("motivation_integrity_ok")
            and check.get("foreshadowing_integrity_ok")
            and check.get("hook_integrity_ok")
            and check.get("continuity_ok")
            and check.get("arc_consistency_ok", True)
        )

    def _to_project_memory_payload(self, project_id: str, memory: Dict[str, Any]) -> Dict[str, Any]:
        active_memory = self.v2_repo.find_active_project_memory(project_id) or {}
        version = int(active_memory.get("version") or 0) + 1
        return {
            "id": f"memory_{uuid.uuid4().hex[:12]}",
            "project_id": project_id,
            "version": max(version, 1),
            "characters": memory.get("characters") or [],
            "world_facts": memory.get("world_facts") or {},
            "plot_arcs": memory.get("plot_arcs") or [],
            "events": memory.get("events") or [],
            "style_profile": memory.get("style_profile") or {},
            "outline_context": memory.get("outline_context") or {},
            "current_state": memory.get("current_state") or {},
            "chapter_summaries": memory.get("chapter_summaries") or [],
            "continuity_flags": memory.get("continuity_flags") or [],
            "global_constraints": memory.get("global_constraints") or {},
            "chapter_analysis_memory_refs": [str(x) for x in (memory.get("chapter_analysis_memory_refs") or [str(item.get("id") or "") for item in (memory.get("chapter_analysis_memories") or []) if isinstance(item, dict)]) if str(x).strip()],
            "chapter_continuation_memory_refs": [str(x) for x in (memory.get("chapter_continuation_memory_refs") or [str(item.get("id") or "") for item in (memory.get("chapter_continuation_memories") or []) if isinstance(item, dict)]) if str(x).strip()],
            "chapter_task_refs": [str(x) for x in (memory.get("chapter_task_refs") or [str(item.get("id") or "") for item in (memory.get("chapter_tasks") or []) if isinstance(item, dict)]) if str(x).strip()],
            "chapter_analysis_memories": [],
            "chapter_continuation_memories": [],
            "chapter_tasks": [],
            "structural_drafts": [],
            "detemplated_drafts": [],
            "draft_integrity_checks": [],
            "style_requirements": memory.get("style_requirements") or {},
            "structured_story_migrated": int(active_memory.get("structured_story_migrated") or 0),
        }

    def _to_memory_view_payload(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        chars = payload.get("characters") or payload.get("main_characters") or []
        main_characters = []
        for item in chars[:5]:
            if isinstance(item, dict):
                name = self.clean_text(str(item.get("name") or ""))
                role = self.clean_text(str(item.get("role") or "角色")) or "角色"
                if not name or self.looks_garbled_text(name):
                    continue
                trait_items = self.normalize_text_list([str(x) for x in (item.get("traits") or [])], 3)
                main_characters.append(
                    {
                        "name": name,
                        "role": role,
                        "traits": "、".join(trait_items),
                    }
                )
        if not main_characters and isinstance(payload.get("main_characters"), list):
            main_characters = [
                {"name": self.clean_text(str(item.get("name") or "")), "role": self.clean_text(str(item.get("role") or "角色")) or "角色", "traits": self.clean_text(str(item.get("traits") or ""))}
                for item in (payload.get("main_characters") or [])
                if isinstance(item, dict) and self.clean_text(str(item.get("name") or ""))
            ][:5]
        world_summary = self.normalize_text_list(self._build_world_summary(payload.get("world_facts") or {}), 8)
        if not world_summary:
            world_summary = self.normalize_text_list([str(x) for x in (payload.get("world_summary") or []) if str(x).strip()], 8)
        style = payload.get("style_profile") or {}
        style_tags: List[str] = []
        if isinstance(style, dict):
            style_tags = [
                *[str(x) for x in (style.get("tone_tags") or [])],
                *[str(x) for x in (style.get("rhythm_tags") or [])],
                str(style.get("narrative_pov") or ""),
            ]
        elif isinstance(style, str):
            style_tags = [x for x in re.split(r"[；;]", style) if x]
        style_tags = self.normalize_text_list(style_tags, 6)
        outline_context = payload.get("outline_context") or {}
        outline_summary = [str(x) for x in (outline_context.get("summary") or []) if str(x)]
        if not outline_summary:
            outline_summary = [
                str(outline_context.get("premise") or ""),
                str(outline_context.get("story_background") or ""),
                str(outline_context.get("world_setting") or ""),
            ]
            outline_summary = [x for x in outline_summary if x]
        outline_summary = self.normalize_text_list(outline_summary, 5)
        current_progress = self.clean_text(str((payload.get("current_state") or {}).get("latest_summary") or payload.get("current_progress") or ""))
        main_plot_lines = self._build_plot_lines(payload)
        if not main_plot_lines:
            main_plot_lines = self.normalize_text_list([str(x) for x in (payload.get("main_plot_lines") or []) if str(x).strip()], 12)
        return {
            "id": f"view_{uuid.uuid4().hex[:12]}",
            "project_id": project_id,
            "memory_id": payload["id"],
            "main_characters": main_characters,
            "world_summary": world_summary,
            "main_plot_lines": main_plot_lines,
            "style_tags": style_tags,
            "current_progress": current_progress,
            "outline_summary": outline_summary,
            "plot_arcs": payload.get("plot_arcs") or [],
            "active_arc_ids": list(((payload.get("current_state") or {}).get("active_arc_ids") or [])),
            "chapter_arc_bindings": [self._to_chapter_arc_binding_dict(item) for item in self.chapter_arc_binding_repo.list_by_project(project_id)],
            "recent_arc_progress": self._load_recent_arc_progress(list(((payload.get("current_state") or {}).get("active_arc_ids") or [])), limit=12),
        }

    def _to_plot_arc_dict(self, arc: Any) -> Dict[str, Any]:
        return {
            "arc_id": str(getattr(arc, "arc_id", "") or ""),
            "title": str(getattr(arc, "title", "") or ""),
            "arc_type": str(getattr(arc, "arc_type", "") or "supporting_arc"),
            "priority": str(getattr(arc, "priority", "") or "minor"),
            "status": str(getattr(arc, "status", "") or "active"),
            "goal": str(getattr(arc, "goal", "") or ""),
            "core_conflict": str(getattr(arc, "core_conflict", "") or ""),
            "current_stage": str(getattr(arc, "current_stage", "") or "setup"),
            "latest_progress_summary": str(getattr(arc, "latest_progress_summary", "") or ""),
            "next_push_suggestion": str(getattr(arc, "next_push_suggestion", "") or ""),
            "covered_chapter_ids": list(getattr(arc, "covered_chapter_ids", []) or []),
        }

    def _to_chapter_arc_binding_dict(self, binding: Any) -> Dict[str, Any]:
        return {
            "binding_id": str(getattr(binding, "binding_id", "") or ""),
            "project_id": str(getattr(binding, "project_id", "") or ""),
            "chapter_id": str(getattr(binding, "chapter_id", "") or ""),
            "arc_id": str(getattr(binding, "arc_id", "") or ""),
            "binding_role": str(getattr(binding, "binding_role", "") or "background"),
            "push_type": str(getattr(binding, "push_type", "") or "advance"),
            "confidence": float(getattr(binding, "confidence", 0.0) or 0.0),
        }

    def _select_preview_target_arc(self, project_id: str, plan: Dict[str, Any], request_target_arc_id: str) -> Dict[str, Any]:
        selected_arc_id = str(request_target_arc_id or plan.get("target_arc_id") or "").strip()
        if not selected_arc_id:
            related = [str(x) for x in (plan.get("related_arc_ids") or []) if str(x).strip()]
            selected_arc_id = related[0] if related else ""
        if not selected_arc_id or not self.plot_arc_service:
            return {}
        arcs = self.plot_arc_service.list_arcs(project_id)
        target = next((arc for arc in arcs if arc.arc_id == selected_arc_id), None)
        return self._to_plot_arc_dict(target) if target else {}

    def _predict_next_arc_stage(self, current_stage: str) -> str:
        stage = str(current_stage or "")
        if stage not in ARC_STAGE_ORDER:
            return ARC_STAGE_ORDER[0]
        index = ARC_STAGE_ORDER.index(stage)
        if index >= len(ARC_STAGE_ORDER) - 1:
            return ARC_STAGE_ORDER[-1]
        return ARC_STAGE_ORDER[index + 1]

    def _build_world_summary(self, world_facts: Dict[str, Any]) -> List[str]:
        if not isinstance(world_facts, dict):
            return []
        ordered: List[str] = []
        for key in ("background", "power_system", "organizations", "locations", "rules", "artifacts"):
            ordered.extend([self.clean_text(str(x)) for x in (world_facts.get(key) or [])])
        return self.normalize_text_list(ordered, 8)

    def _build_plot_lines(self, payload: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        for arc in (payload.get("plot_arcs") or []):
            if not isinstance(arc, dict):
                continue
            title = self.clean_text(str(arc.get("title") or ""))
            summary = self.clean_text(str(arc.get("summary") or ""))
            stage = self.clean_text(str(arc.get("current_stage") or ""))
            candidate = summary or (f"{title}：{stage}" if title and stage else title)
            if candidate:
                lines.append(candidate)
        chapter_summaries = [self.clean_text(str(x)) for x in (payload.get("chapter_summaries") or []) if str(x).strip()]
        lines.extend(chapter_summaries[-6:])
        current_state = payload.get("current_state") or {}
        latest_summary = self.clean_text(str(current_state.get("latest_summary") or "")) if isinstance(current_state, dict) else ""
        if latest_summary:
            lines.append(latest_summary)
        filtered = [line for line in lines if line and "chunk=" not in line and "分析完成" not in line]
        return self.normalize_text_list(filtered, 8)

    def _global_constraints_to_dict(self, item: GlobalConstraints) -> Dict[str, Any]:
        return {
            "id": item.id,
            "main_plot": item.main_plot,
            "hidden_plot": item.hidden_plot,
            "core_selling_points": list(item.core_selling_points or []),
            "protagonist_core_traits": list(item.protagonist_core_traits or []),
            "must_keep_threads": list(item.must_keep_threads or []),
            "genre_guardrails": list(item.genre_guardrails or []),
            "source_type": item.source_type,
            "version": item.version,
        }

    def _style_requirements_to_dict(self, item: StyleRequirements) -> Dict[str, Any]:
        return {
            "id": item.id,
            "author_voice_keywords": list(item.author_voice_keywords or []),
            "avoid_patterns": list(item.avoid_patterns or []),
            "preferred_rhythm": item.preferred_rhythm,
            "narrative_distance": item.narrative_distance,
            "dialogue_density": item.dialogue_density,
            "source_type": item.source_type,
            "version": item.version,
        }

    def _chapter_analysis_memory_to_dict(self, item: ChapterAnalysisMemory) -> Dict[str, Any]:
        return {"id": item.id, "chapter_id": item.chapter_id, "chapter_number": item.chapter_number, "chapter_title": item.chapter_title, "summary": item.summary, "events": list(item.events or []), "plot_role": item.plot_role, "conflict": item.conflict, "foreshadowing": list(item.foreshadowing or []), "hook": item.hook, "problems": list(item.problems or []), "primary_arc_id": item.primary_arc_id, "secondary_arc_ids": list(item.secondary_arc_ids or []), "arc_push_summary": item.arc_push_summary, "arc_stage_impact": item.arc_stage_impact, "version": item.version}

    def _chapter_continuation_memory_to_dict(self, item: ChapterContinuationMemory) -> Dict[str, Any]:
        return {"id": item.id, "chapter_id": item.chapter_id, "chapter_number": item.chapter_number, "chapter_title": item.chapter_title, "scene_summary": item.scene_summary, "scene_state": dict(item.scene_state or {}), "protagonist_state": dict(item.protagonist_state or {}), "active_characters": list(item.active_characters or []), "active_conflicts": list(item.active_conflicts or []), "immediate_threads": list(item.immediate_threads or []), "long_term_threads": list(item.long_term_threads or []), "recent_reveals": list(item.recent_reveals or []), "must_continue_points": list(item.must_continue_points or []), "forbidden_jumps": list(item.forbidden_jumps or []), "tone_and_pacing": dict(item.tone_and_pacing or {}), "last_hook": item.last_hook, "active_arc_ids": list(item.active_arc_ids or []), "target_arc_id": item.target_arc_id, "target_arc_stage": item.target_arc_stage, "arc_must_continue_points": list(item.arc_must_continue_points or []), "version": item.version}

    def _chapter_task_to_dict(self, item: ChapterTask) -> Dict[str, Any]:
        return {"id": item.id, "chapter_id": item.chapter_id, "project_id": item.project_id, "branch_id": item.branch_id, "chapter_number": item.chapter_number, "chapter_function": item.chapter_function, "goals": list(item.goals or []), "must_continue_points": list(item.must_continue_points or []), "forbidden_jumps": list(item.forbidden_jumps or []), "required_foreshadowing_action": self._normalize_foreshadowing_action(item.required_foreshadowing_action), "required_hook_strength": self._normalize_hook_strength(item.required_hook_strength), "pace_target": item.pace_target, "opening_continuation": item.opening_continuation, "chapter_payoff": item.chapter_payoff, "style_bias": item.style_bias, "target_arc_id": item.target_arc_id, "secondary_arc_ids": list(item.secondary_arc_ids or []), "arc_stage_before": item.arc_stage_before, "arc_stage_after_expected": item.arc_stage_after_expected, "arc_push_goal": item.arc_push_goal, "arc_conflict_focus": item.arc_conflict_focus, "arc_payoff_expectation": item.arc_payoff_expectation, "planning_mode": item.planning_mode, "status": item.status, "version": item.version}

    def _structural_draft_to_dict(self, item: StructuralDraft) -> Dict[str, Any]:
        return {"id": item.id, "chapter_id": item.chapter_id, "project_id": item.project_id, "chapter_number": item.chapter_number, "title": item.title, "content": item.content, "source_task_id": item.source_task_id, "model_name": item.model_name, "used_fallback": item.used_fallback, "generation_stage": item.generation_stage, "version": item.version}

    def _detemplated_draft_to_dict(self, item: DetemplatedDraft) -> Dict[str, Any]:
        return {"id": item.id, "chapter_id": item.chapter_id, "project_id": item.project_id, "chapter_number": item.chapter_number, "title": item.title, "content": item.content, "based_on_structural_draft_id": item.based_on_structural_draft_id, "style_requirements_snapshot": dict(item.style_requirements_snapshot or {}), "model_name": item.model_name, "used_fallback": item.used_fallback, "generation_stage": item.generation_stage, "version": item.version}

    def _draft_integrity_check_to_dict(self, item: DraftIntegrityCheck) -> Dict[str, Any]:
        return {
            "id": item.id,
            "chapter_id": item.chapter_id,
            "project_id": item.project_id,
            "structural_draft_id": item.structural_draft_id,
            "detemplated_draft_id": item.detemplated_draft_id,
            "event_integrity_ok": item.event_integrity_ok,
            "motivation_integrity_ok": item.motivation_integrity_ok,
            "foreshadowing_integrity_ok": item.foreshadowing_integrity_ok,
            "hook_integrity_ok": item.hook_integrity_ok,
            "continuity_ok": item.continuity_ok,
            "arc_consistency_ok": item.arc_consistency_ok,
            "title_alignment_ok": item.title_alignment_ok,
            "progression_integrity_ok": item.progression_integrity_ok,
            "risk_notes": list(item.risk_notes or []),
            "issue_list": list(item.issue_list or []),
            "revision_suggestion": item.revision_suggestion,
            "revision_attempted": item.revision_attempted,
            "revision_succeeded": item.revision_succeeded,
        }

    def _get_chapter_outline_entity(self, chapter_id: str):
        return self.chapter_outline_repo.find_by_chapter_id(ChapterId(chapter_id))

    def _chapter_outline_to_dict(self, outline) -> Dict[str, Any]:
        if not outline:
            return {}
        return {
            "goal": getattr(outline, "goal", "") or "",
            "conflict": getattr(outline, "conflict", "") or "",
            "events": list(getattr(outline, "events", []) or []),
            "character_progress": getattr(outline, "character_progress", "") or "",
            "ending_hook": getattr(outline, "ending_hook", "") or "",
            "opening_continuation": getattr(outline, "opening_continuation", "") or "",
            "notes": getattr(outline, "notes", "") or "",
        }

    def _get_outline_context(self, novel_id: NovelId) -> Dict[str, Any]:
        outline = self.outline_repo.find_by_novel(novel_id)
        summary = []
        if outline:
            summary = [str(outline.premise or ""), str(outline.story_background or ""), str(outline.world_setting or "")]
            summary = [x for x in summary if x]
        return {
            "premise": outline.premise if outline else "",
            "story_background": outline.story_background if outline else "",
            "world_setting": outline.world_setting if outline else "",
            "summary": summary,
        }

    def _load_structured_memory(
        self,
        project_id: str,
        novel_id: NovelId,
        outline_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        memory = self.v2_repo.find_active_project_memory(project_id) or {}
        memory = self._hydrate_memory_from_primary_sources(project_id, memory)
        if isinstance(memory, dict) and memory.get("world_facts"):
            memory["outline_context"] = outline_context or (memory.get("outline_context") or {})
            if self._needs_primary_repo_migration(memory):
                self._sync_primary_repositories(project_id, memory)
            return memory
        legacy = self.project_service.get_memory_by_novel(novel_id)
        if self._is_legacy_memory(legacy):
            normalized = self._normalize_legacy_memory(legacy if isinstance(legacy, dict) else {}, outline_context or {})
            normalized["outline_context"] = outline_context or {}
            self._sync_primary_repositories(project_id, normalized)
            return normalized
        return self._empty_structured_memory(outline_context or {})

    def _needs_primary_repo_migration(self, memory: Dict[str, Any]) -> bool:
        if int(memory.get("structured_story_migrated") or 0) == 1:
            return False
        return bool(
            memory.get("global_constraints")
            or memory.get("chapter_analysis_memories")
            or memory.get("chapter_analysis_memories_legacy")
            or memory.get("chapter_continuation_memories")
            or memory.get("chapter_continuation_memories_legacy")
            or memory.get("chapter_tasks")
            or memory.get("chapter_tasks_legacy")
            or memory.get("structural_drafts")
            or memory.get("structural_drafts_legacy")
            or memory.get("detemplated_drafts")
            or memory.get("detemplated_drafts_legacy")
            or memory.get("draft_integrity_checks")
            or memory.get("draft_integrity_checks_legacy")
            or memory.get("style_requirements")
            or memory.get("style_requirements_legacy")
        )

    def _hydrate_memory_from_primary_sources(self, project_id: str, memory: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(memory or {})
        payload["project_id"] = project_id
        constraints = self.global_constraints_repo.find_by_project_id(project_id)
        if constraints:
            payload["global_constraints"] = self._global_constraints_to_dict(constraints)
        style = self.style_requirements_repo.find_by_project_id(project_id)
        if style:
            payload["style_requirements"] = self._style_requirements_to_dict(style)
        payload["chapter_tasks"] = [self._chapter_task_to_dict(item) for item in self.chapter_task_repo.find_by_project_id(project_id)] or (payload.get("chapter_tasks") or [])
        payload["structural_drafts"] = [self._structural_draft_to_dict(item) for item in self.structural_draft_repo.find_by_project_id(project_id)] or (payload.get("structural_drafts") or [])
        payload["detemplated_drafts"] = [self._detemplated_draft_to_dict(item) for item in self.detemplated_draft_repo.find_by_project_id(project_id)] or (payload.get("detemplated_drafts") or [])
        payload["draft_integrity_checks"] = [self._draft_integrity_check_to_dict(item) for item in self.draft_integrity_check_repo.find_by_project_id(project_id)] or (payload.get("draft_integrity_checks") or [])
        payload["chapter_task_refs"] = [str(item.get("id") or "") for item in (payload.get("chapter_tasks") or []) if isinstance(item, dict)]
        analysis_refs = [str(x) for x in (payload.get("chapter_analysis_memory_refs") or []) if str(x).strip()]
        if not analysis_refs:
            analysis_refs = [str(item.get("id") or "") for item in (payload.get("chapter_analysis_memories") or []) if isinstance(item, dict) and str(item.get("id") or "").strip()]
        hydrated_analysis = []
        for item_id in analysis_refs:
            item = self.chapter_analysis_memory_repo.find_by_id(item_id)
            if item:
                hydrated_analysis.append(self._chapter_analysis_memory_to_dict(item))
        if hydrated_analysis:
            payload["chapter_analysis_memories"] = hydrated_analysis
        payload["chapter_analysis_memory_refs"] = [str(item.get("id") or "") for item in (payload.get("chapter_analysis_memories") or []) if isinstance(item, dict)]
        continuation_refs = [str(x) for x in (payload.get("chapter_continuation_memory_refs") or []) if str(x).strip()]
        if not continuation_refs:
            continuation_refs = [str(item.get("id") or "") for item in (payload.get("chapter_continuation_memories") or []) if isinstance(item, dict) and str(item.get("id") or "").strip()]
        hydrated_continuation = []
        for item_id in continuation_refs:
            item = self.chapter_continuation_memory_repo.find_by_id(item_id)
            if item:
                hydrated_continuation.append(self._chapter_continuation_memory_to_dict(item))
        if hydrated_continuation:
            payload["chapter_continuation_memories"] = hydrated_continuation
        payload["chapter_continuation_memory_refs"] = [str(item.get("id") or "") for item in (payload.get("chapter_continuation_memories") or []) if isinstance(item, dict)]
        return payload

    def _sync_primary_repositories(self, project_id: str, memory: Dict[str, Any]) -> None:
        now = datetime.now()
        global_constraints = memory.get("global_constraints") or {}
        if isinstance(global_constraints, dict) and any(global_constraints.values()):
            self.global_constraints_repo.save(
                GlobalConstraints(
                    id=str(global_constraints.get("id") or f"gc_{project_id}"),
                    project_id=project_id,
                    main_plot=str(global_constraints.get("main_plot") or ""),
                    hidden_plot=str(global_constraints.get("hidden_plot") or ""),
                    core_selling_points=[str(x) for x in (global_constraints.get("core_selling_points") or [])],
                    protagonist_core_traits=[str(x) for x in (global_constraints.get("protagonist_core_traits") or [])],
                    must_keep_threads=[str(x) for x in (global_constraints.get("must_keep_threads") or [])],
                    genre_guardrails=[str(x) for x in (global_constraints.get("genre_guardrails") or [])],
                    source_type=str(global_constraints.get("source_type") or STYLE_SOURCE_MANUAL),
                    version=int(global_constraints.get("version") or 1),
                    created_at=now,
                    updated_at=now,
                )
            )
        style_requirements = memory.get("style_requirements") or memory.get("style_requirements_legacy") or {}
        if isinstance(style_requirements, dict):
            self.style_requirements_repo.save(
                StyleRequirements(
                    id=str(style_requirements.get("id") or f"style_{project_id}"),
                    project_id=project_id,
                    author_voice_keywords=[str(x) for x in (style_requirements.get("author_voice_keywords") or [])],
                    avoid_patterns=[str(x) for x in (style_requirements.get("avoid_patterns") or [])],
                    preferred_rhythm=str(style_requirements.get("preferred_rhythm") or ""),
                    narrative_distance=str(style_requirements.get("narrative_distance") or ""),
                    dialogue_density=str(style_requirements.get("dialogue_density") or ""),
                    source_type=str(style_requirements.get("source_type") or STYLE_SOURCE_MANUAL),
                    version=int(style_requirements.get("version") or 1),
                    created_at=now,
                    updated_at=now,
                )
            )
        for item in ((memory.get("chapter_analysis_memories") or []) or (memory.get("chapter_analysis_memories_legacy") or [])):
            if isinstance(item, dict):
                self.chapter_analysis_memory_repo.save(ChapterAnalysisMemory(id=str(item.get("id") or f"cam_{uuid.uuid4().hex[:10]}"), chapter_id=str(item.get("chapter_id") or ""), chapter_number=int(item.get("chapter_number") or 0), chapter_title=str(item.get("chapter_title") or ""), summary=str(item.get("summary") or ""), events=[str(x) for x in (item.get("events") or [])], plot_role=str(item.get("plot_role") or ""), conflict=str(item.get("conflict") or ""), foreshadowing=[str(x) for x in (item.get("foreshadowing") or [])], hook=str(item.get("hook") or ""), problems=[str(x) for x in (item.get("problems") or [])], version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in ((memory.get("chapter_continuation_memories") or []) or (memory.get("chapter_continuation_memories_legacy") or [])):
            if isinstance(item, dict):
                self.chapter_continuation_memory_repo.save(ChapterContinuationMemory(id=str(item.get("id") or f"ccm_{uuid.uuid4().hex[:10]}"), chapter_id=str(item.get("chapter_id") or ""), chapter_number=int(item.get("chapter_number") or 0), chapter_title=str(item.get("chapter_title") or ""), scene_summary=str(item.get("scene_summary") or ""), scene_state=item.get("scene_state") or {}, protagonist_state=item.get("protagonist_state") or {}, active_characters=item.get("active_characters") or [], active_conflicts=[str(x) for x in (item.get("active_conflicts") or [])], immediate_threads=[str(x) for x in (item.get("immediate_threads") or [])], long_term_threads=[str(x) for x in (item.get("long_term_threads") or [])], recent_reveals=[str(x) for x in (item.get("recent_reveals") or [])], must_continue_points=[str(x) for x in (item.get("must_continue_points") or [])], forbidden_jumps=[str(x) for x in (item.get("forbidden_jumps") or [])], tone_and_pacing=item.get("tone_and_pacing") or {}, last_hook=str(item.get("last_hook") or ""), version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in ((memory.get("chapter_tasks") or []) or (memory.get("chapter_tasks_legacy") or [])):
            if isinstance(item, dict):
                self.chapter_task_repo.save(ChapterTask(id=str(item.get("id") or f"task_{uuid.uuid4().hex[:10]}"), chapter_id=str(item.get("chapter_id") or ""), project_id=project_id, branch_id=str(item.get("branch_id") or ""), chapter_number=int(item.get("chapter_number") or 0), chapter_function=str(item.get("chapter_function") or ""), goals=[str(x) for x in (item.get("goals") or [])], must_continue_points=[str(x) for x in (item.get("must_continue_points") or [])], forbidden_jumps=[str(x) for x in (item.get("forbidden_jumps") or [])], required_foreshadowing_action=self._normalize_foreshadowing_action(str(item.get("required_foreshadowing_action") or DEFAULT_FORESHADOWING_ACTION)), required_hook_strength=self._normalize_hook_strength(str(item.get("required_hook_strength") or DEFAULT_HOOK_STRENGTH)), pace_target=str(item.get("pace_target") or ""), opening_continuation=str(item.get("opening_continuation") or ""), chapter_payoff=str(item.get("chapter_payoff") or ""), style_bias=str(item.get("style_bias") or ""), status=str(item.get("status") or WRITING_STATUS_READY), version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in ((memory.get("structural_drafts") or []) or (memory.get("structural_drafts_legacy") or [])):
            if isinstance(item, dict):
                self.structural_draft_repo.save(StructuralDraft(id=str(item.get("id") or f"struct_{uuid.uuid4().hex[:10]}"), chapter_id=str(item.get("chapter_id") or ""), project_id=project_id, chapter_number=int(item.get("chapter_number") or 0), title=str(item.get("title") or ""), content=str(item.get("content") or ""), source_task_id=str(item.get("source_task_id") or ""), model_name=str(item.get("model_name") or "continue-writing"), used_fallback=bool(item.get("used_fallback")), generation_stage=str(item.get("generation_stage") or "structural"), version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in ((memory.get("detemplated_drafts") or []) or (memory.get("detemplated_drafts_legacy") or [])):
            if isinstance(item, dict):
                self.detemplated_draft_repo.save(DetemplatedDraft(id=str(item.get("id") or f"det_{uuid.uuid4().hex[:10]}"), chapter_id=str(item.get("chapter_id") or ""), project_id=project_id, chapter_number=int(item.get("chapter_number") or 0), title=str(item.get("title") or ""), content=str(item.get("content") or ""), based_on_structural_draft_id=str(item.get("based_on_structural_draft_id") or ""), style_requirements_snapshot=item.get("style_requirements_snapshot") or {}, model_name=str(item.get("model_name") or "detemplating-rewrite"), used_fallback=bool(item.get("used_fallback")), generation_stage=str(item.get("generation_stage") or "detemplated"), version=int(item.get("version") or 1), created_at=now, updated_at=now))
        for item in ((memory.get("draft_integrity_checks") or []) or (memory.get("draft_integrity_checks_legacy") or [])):
            if isinstance(item, dict):
                self.draft_integrity_check_repo.save(DraftIntegrityCheck(id=str(item.get("id") or f"check_{uuid.uuid4().hex[:10]}"), chapter_id=str(item.get("chapter_id") or ""), project_id=project_id, structural_draft_id=str(item.get("structural_draft_id") or ""), detemplated_draft_id=str(item.get("detemplated_draft_id") or ""), event_integrity_ok=bool(item.get("event_integrity_ok")), motivation_integrity_ok=bool(item.get("motivation_integrity_ok")), foreshadowing_integrity_ok=bool(item.get("foreshadowing_integrity_ok")), hook_integrity_ok=bool(item.get("hook_integrity_ok")), continuity_ok=bool(item.get("continuity_ok")), arc_consistency_ok=bool(item.get("arc_consistency_ok", True)), title_alignment_ok=bool(item.get("title_alignment_ok", True)), progression_integrity_ok=bool(item.get("progression_integrity_ok", True)), risk_notes=[str(x) for x in (item.get("risk_notes") or [])], issue_list=[issue for issue in (item.get("issue_list") or []) if isinstance(issue, dict)], revision_suggestion=str(item.get("revision_suggestion") or ""), revision_attempted=bool(item.get("revision_attempted")), revision_succeeded=bool(item.get("revision_succeeded")), created_at=now))
        if hasattr(self.v2_repo, "mark_structured_story_migrated"):
            self.v2_repo.mark_structured_story_migrated(project_id)

    def _is_legacy_memory(self, memory: Any) -> bool:
        if not isinstance(memory, dict):
            return False
        for key in ("world_settings", "plot_outline", "writing_style", "current_progress"):
            value = memory.get(key)
            if isinstance(value, str) and value.strip():
                return True
            if isinstance(value, dict) and value:
                return True
            if isinstance(value, list) and value:
                return True
        return False

    def _build_outline_consistency_note(self, branch: Dict[str, Any], outline_context: Dict[str, Any]) -> str:
        premise = self.clean_text(str(outline_context.get("premise") or ""))
        summary = self.clean_text(str(branch.get("summary") or ""))
        if not premise:
            return "暂无大纲约束"
        if premise and premise[:10] in summary:
            return "与当前大纲方向基本一致"
        return f"与当前大纲存在偏移风险，需留意设定：{premise[:48]}"

    def _build_outline_risk_note(self, branch: Dict[str, Any], outline_context: Dict[str, Any]) -> str:
        premise = self.clean_text(str(outline_context.get("premise") or ""))
        summary = self.clean_text(str(branch.get("summary") or ""))
        if not premise:
            return ""
        if premise and premise[:10] in summary:
            return ""
        return f"与当前大纲存在偏移风险，需留意设定：{premise[:48]}"

    def _build_chapter_units(self, novel_id: NovelId, mode: str) -> List[Dict[str, Any]]:
        chapters = self.chapter_repo.find_by_novel(novel_id)
        if mode == "chapter_first" and chapters:
            return [
                {
                    "id": chapter.id.value,
                    "title": self.clean_text(chapter.title) or f"第{chapter.number}章",
                    "content": chapter.content or "",
                    "index": chapter.number,
                }
                for chapter in chapters
                if (chapter.content or "").strip()
            ]
        novel_text = self.content_service.get_novel_text(str(novel_id))
        units = []
        if novel_text.strip():
            for idx, part in enumerate([x for x in novel_text.split("\n\n") if x.strip()], 1):
                units.append({"title": f"单元{idx}", "content": part, "index": idx})
        return units

    def _build_outline_memory_summary(self, memory: Dict[str, Any]) -> str:
        lines: List[str] = []
        current_state = memory.get("current_state") or {}
        global_constraints = memory.get("global_constraints") or {}
        main_plot = self.clean_text(str(global_constraints.get("main_plot") or ""))
        next_focus = self.clean_text(str(current_state.get("next_writing_focus") or ""))
        latest_summary = self.clean_text(str(current_state.get("latest_summary") or ""))
        if main_plot:
            lines.append(main_plot)
        lines.extend(self._build_plot_lines(memory))
        lines.extend([str(x) for x in (global_constraints.get("must_keep_threads") or []) if str(x).strip()])
        if next_focus:
            lines.append(next_focus)
        if latest_summary:
            lines.append(latest_summary)
        return "；".join(self.normalize_text_list(lines, 8))

    def _build_outline_summary_text(self, outline_context: Dict[str, Any], memory: Dict[str, Any]) -> str:
        lines = [str(x) for x in ((outline_context or {}).get("summary") or []) if str(x).strip()]
        global_constraints = memory.get("global_constraints") or {}
        lines.extend([str(x) for x in (global_constraints.get("genre_guardrails") or []) if str(x).strip()])
        return "；".join(self.normalize_text_list(lines, 6))

    def _build_recent_outline_summaries(self, memory: Dict[str, Any]) -> List[str]:
        return self._build_plot_lines(memory)[-3:]

    async def _generate_and_save_chapter_outline(
        self,
        project_id: str,
        chapter: Dict[str, Any],
        memory: Dict[str, Any],
        outline_context: Dict[str, Any],
        current: int,
        total: int,
    ) -> None:
        chapter_id = str(chapter.get("id") or "").strip()
        if not chapter_id:
            return
        chapter_title = self.clean_text(str(chapter.get("title") or f"第{current}章")) or f"第{current}章"
        result = await self.prompt_ai_service.analyze_to_outline(
            chapter_title=chapter_title,
            chapter_content=str(chapter.get("content") or ""),
            global_memory_summary=self._build_outline_memory_summary(memory),
            global_outline_summary=self._build_outline_summary_text(outline_context, memory),
            recent_chapter_summaries=self._build_recent_outline_summaries(memory),
        )
        draft = result.get("outline_draft") if isinstance(result, dict) else {}
        draft = draft if isinstance(draft, dict) else {}
        existing = self.chapter_outline_repo.find_by_chapter_id(ChapterId(chapter_id))
        now = datetime.now()
        self.chapter_outline_repo.save(
            ChapterOutline(
                chapter_id=ChapterId(chapter_id),
                goal=self.clean_text(str(draft.get("goal") or "")),
                conflict=self.clean_text(str(draft.get("conflict") or "")),
                events=self.normalize_text_list([str(x) for x in (draft.get("events") or [])], 12),
                character_progress=self.clean_text(str(draft.get("character_progress") or "")),
                ending_hook=self.clean_text(str(draft.get("ending_hook") or "")),
                opening_continuation=self.clean_text(str(draft.get("opening_continuation") or "")),
                notes=self.clean_text(str(draft.get("notes") or "")),
                created_at=existing.created_at if existing else now,
                updated_at=now,
            )
        )
        self.logger.info(
            "章节大纲生成完成",
            extra=build_log_context(
                event="chapter_outline_generation_finished",
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=int(chapter.get("index") or current),
                chapter_title=chapter_title,
                used_fallback=bool((result or {}).get("used_fallback")),
                current=current,
                total=total,
            ),
        )

    def _chapter_bundle_to_analysis_payload(self, bundle: Dict[str, Any], chapter: Dict[str, Any], chapter_number: int) -> Dict[str, Any]:
        outline_draft = bundle.get("outline_draft") if isinstance(bundle.get("outline_draft"), dict) else {}
        continuation = bundle.get("continuation_memory") if isinstance(bundle.get("continuation_memory"), dict) else {}
        analysis_summary = bundle.get("analysis_summary") if isinstance(bundle.get("analysis_summary"), dict) else {}
        summary = self.clean_text(str(analysis_summary.get("summary") or continuation.get("scene_summary") or chapter.get("title") or ""))
        current_state = {
            "latest_chapter_number": int(chapter_number or 0),
            "latest_summary": summary,
            "next_writing_focus": self.clean_text(str(outline_draft.get("goal") or outline_draft.get("ending_hook") or "")),
            "active_arc_ids": list(continuation.get("active_arc_ids") or []),
            "recent_conflicts": [str(x) for x in (continuation.get("active_conflicts") or []) if str(x).strip()][:5],
        }
        return {
            "chapter_summary": summary,
            "chapter_summaries": [summary] if summary else [],
            "events": [
                {
                    "chapter_id": str(chapter.get("id") or ""),
                    "chapter_number": int(chapter_number or 0),
                    "summary": str(item),
                }
                for item in (analysis_summary.get("events") or outline_draft.get("events") or [])[:6]
                if str(item).strip()
            ],
            "continuity_flags": [
                {"severity": "medium", "message": str(item)}
                for item in (analysis_summary.get("problems") or [])[:4]
                if str(item).strip()
            ],
            "current_state": current_state,
        }

    def _save_chapter_memory_bundle(
        self,
        project_id: str,
        chapter: Dict[str, Any],
        chapter_number: int,
        bundle: Dict[str, Any],
        memory: Dict[str, Any],
    ) -> None:
        chapter_id = str(chapter.get("id") or "").strip()
        if not chapter_id:
            return
        chapter_title = self.clean_text(str(chapter.get("title") or f"第{chapter_number}章")) or f"第{chapter_number}章"
        outline_draft = bundle.get("outline_draft") if isinstance(bundle.get("outline_draft"), dict) else {}
        analysis_summary = bundle.get("analysis_summary") if isinstance(bundle.get("analysis_summary"), dict) else {}
        continuation = bundle.get("continuation_memory") if isinstance(bundle.get("continuation_memory"), dict) else {}
        now = datetime.now()
        existing_outline = self.chapter_outline_repo.find_by_chapter_id(ChapterId(chapter_id))
        self.chapter_outline_repo.save(
            ChapterOutline(
                chapter_id=ChapterId(chapter_id),
                goal=self.clean_text(str(outline_draft.get("goal") or "")),
                conflict=self.clean_text(str(outline_draft.get("conflict") or "")),
                events=self.normalize_text_list([str(x) for x in (outline_draft.get("events") or [])], 12),
                character_progress=self.clean_text(str(outline_draft.get("character_progress") or "")),
                ending_hook=self.clean_text(str(outline_draft.get("ending_hook") or "")),
                opening_continuation=self.clean_text(str(outline_draft.get("opening_continuation") or "")),
                notes=self.clean_text(str(outline_draft.get("notes") or "")),
                created_at=existing_outline.created_at if existing_outline else now,
                updated_at=now,
            )
        )
        self.chapter_analysis_memory_repo.save(
            ChapterAnalysisMemory(
                id=f"cam_{project_id}_{chapter_id}",
                chapter_id=chapter_id,
                chapter_number=int(chapter_number or 0),
                chapter_title=chapter_title,
                summary=self.clean_text(str(analysis_summary.get("summary") or continuation.get("scene_summary") or "")),
                events=self.normalize_text_list([str(x) for x in (analysis_summary.get("events") or outline_draft.get("events") or [])], 8),
                plot_role=self.clean_text(str(analysis_summary.get("plot_role") or outline_draft.get("goal") or "")),
                conflict=self.clean_text(str(analysis_summary.get("conflict") or outline_draft.get("conflict") or "")),
                foreshadowing=self.normalize_text_list([str(x) for x in (analysis_summary.get("foreshadowing") or continuation.get("must_continue_points") or [])], 6),
                hook=self.clean_text(str(analysis_summary.get("hook") or outline_draft.get("ending_hook") or continuation.get("last_hook") or "")),
                problems=self.normalize_text_list([str(x) for x in (analysis_summary.get("problems") or [])], 6),
                primary_arc_id=str(continuation.get("target_arc_id") or ""),
                secondary_arc_ids=[str(x) for x in (continuation.get("active_arc_ids") or []) if str(x).strip()][:3],
                arc_push_summary=self.clean_text(str(outline_draft.get("goal") or "")),
                arc_stage_impact=self.clean_text(str(continuation.get("target_arc_stage") or "")),
                created_at=now,
                updated_at=now,
            )
        )
        self.chapter_continuation_memory_repo.save(
            ChapterContinuationMemory(
                id=f"ccm_{project_id}_{chapter_id}",
                chapter_id=chapter_id,
                chapter_number=int(chapter_number or 0),
                chapter_title=chapter_title,
                scene_summary=self.clean_text(str(continuation.get("scene_summary") or "")),
                scene_state=continuation.get("scene_state") if isinstance(continuation.get("scene_state"), dict) else {},
                protagonist_state=continuation.get("protagonist_state") if isinstance(continuation.get("protagonist_state"), dict) else {},
                active_characters=[item for item in (continuation.get("active_characters") or []) if isinstance(item, dict)],
                active_conflicts=[str(x) for x in (continuation.get("active_conflicts") or []) if str(x).strip()],
                immediate_threads=[str(x) for x in (continuation.get("immediate_threads") or []) if str(x).strip()],
                long_term_threads=[str(x) for x in (continuation.get("long_term_threads") or []) if str(x).strip()],
                recent_reveals=[str(x) for x in (continuation.get("recent_reveals") or []) if str(x).strip()],
                must_continue_points=[str(x) for x in (continuation.get("must_continue_points") or []) if str(x).strip()],
                forbidden_jumps=[str(x) for x in (continuation.get("forbidden_jumps") or []) if str(x).strip()],
                tone_and_pacing=continuation.get("tone_and_pacing") if isinstance(continuation.get("tone_and_pacing"), dict) else {},
                last_hook=self.clean_text(str(continuation.get("last_hook") or "")),
                active_arc_ids=[str(x) for x in (continuation.get("active_arc_ids") or []) if str(x).strip()][:5],
                target_arc_id=str(continuation.get("target_arc_id") or ""),
                target_arc_stage=str(continuation.get("target_arc_stage") or ""),
                arc_must_continue_points=[str(x) for x in (continuation.get("arc_must_continue_points") or continuation.get("must_continue_points") or []) if str(x).strip()][:6],
                created_at=now,
                updated_at=now,
            )
        )
        memory["chapter_analysis_memory_refs"] = [*(memory.get("chapter_analysis_memory_refs") or []), f"cam_{project_id}_{chapter_id}"][-300:]
        memory["chapter_continuation_memory_refs"] = [*(memory.get("chapter_continuation_memory_refs") or []), f"ccm_{project_id}_{chapter_id}"][-300:]

    def _save_arc_bindings(self, project_id: str, bindings: List[Dict[str, Any]]) -> None:
        now = datetime.now()
        for item in bindings:
            if not isinstance(item, dict):
                continue
            chapter_id = str(item.get("chapter_id") or "").strip()
            arc_id = str(item.get("arc_id") or "").strip()
            if not chapter_id or not arc_id:
                continue
            binding_id = str(item.get("binding_id") or f"bind_{project_id}_{chapter_id}_{arc_id}").strip()
            self.chapter_arc_binding_repo.save(
                ChapterArcBinding(
                    binding_id=binding_id,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    arc_id=arc_id,
                    binding_role=str(item.get("binding_role") or "background"),
                    push_type=str(item.get("push_type") or "advance"),
                    confidence=float(item.get("confidence") or 0.6),
                    created_at=now,
                )
            )

    def _empty_structured_memory(self, outline_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "characters": [],
            "world_facts": {"background": [], "power_system": [], "organizations": [], "locations": [], "rules": [], "artifacts": []},
            "plot_arcs": [],
            "events": [],
            "style_profile": {"narrative_pov": "第三人称有限视角", "tone_tags": [], "rhythm_tags": []},
            "outline_context": outline_context or {},
            "current_state": {"latest_chapter_number": 0, "latest_summary": "", "active_arc_ids": [], "recent_conflicts": [], "next_writing_focus": ""},
            "chapter_summaries": [],
            "continuity_flags": [],
            "global_constraints": {
                "main_plot": "",
                "hidden_plot": "",
                "core_selling_points": [],
                "protagonist_core_traits": [],
                "must_keep_threads": [],
                "genre_guardrails": [],
            },
            "chapter_analysis_memory_refs": [],
            "chapter_continuation_memory_refs": [],
            "chapter_task_refs": [],
            "chapter_analysis_memories": [],
            "chapter_continuation_memories": [],
            "chapter_tasks": [],
            "structural_drafts": [],
            "detemplated_drafts": [],
            "draft_integrity_checks": [],
            "style_requirements": {
                "author_voice_keywords": [],
                "avoid_patterns": [],
                "preferred_rhythm": "",
                "narrative_distance": "",
                "dialogue_density": "",
            },
        }

    def _normalize_legacy_memory(self, memory: Dict[str, Any], outline_context: Dict[str, Any]) -> Dict[str, Any]:
        base = self._empty_structured_memory(outline_context)
        chars = memory.get("characters") or []
        base["characters"] = [x for x in chars if isinstance(x, dict)]
        world_settings = self.clean_text(str(memory.get("world_settings") or ""))
        segments = [x.strip() for x in re.split(r"[；;]", world_settings) if x.strip()]
        base["world_facts"]["background"] = segments[:4]
        base["events"] = [x for x in (memory.get("events") or []) if isinstance(x, dict)]
        writing_style = self.clean_text(str(memory.get("writing_style") or ""))
        style_parts = [x.strip() for x in re.split(r"[；;]", writing_style) if x.strip()]
        if style_parts:
            base["style_profile"]["narrative_pov"] = style_parts[0]
            base["style_profile"]["tone_tags"] = style_parts[1:3]
            base["style_profile"]["rhythm_tags"] = style_parts[3:5]
        current = memory.get("current_progress")
        if isinstance(current, dict):
            base["current_state"] = {
                "latest_chapter_number": int(current.get("latest_chapter_number") or 0),
                "latest_summary": str(current.get("last_summary") or ""),
                "active_arc_ids": [],
                "recent_conflicts": [],
                "next_writing_focus": str(current.get("latest_goal") or ""),
            }
        elif isinstance(current, str):
            base["current_state"]["latest_summary"] = self.clean_text(current)
        outline = memory.get("plot_outline")
        if outline:
            base["chapter_summaries"] = self.normalize_text_list([x.strip() for x in re.split(r"[；;]", str(outline)) if x.strip()], 20)
        return base

    def _to_tool_memory_context(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        structured = {
            "characters": memory.get("characters") or [],
            "world_facts": memory.get("world_facts") or {},
            "plot_arcs": memory.get("plot_arcs") or [],
            "style_profile": memory.get("style_profile") or {},
            "chapter_summaries": memory.get("chapter_summaries") or [],
            "current_state": memory.get("current_state") or {},
            "events": memory.get("events") or [],
            "continuity_flags": memory.get("continuity_flags") or [],
            "outline_context": memory.get("outline_context") or {},
            "global_constraints": memory.get("global_constraints") or {},
            "style_requirements": memory.get("style_requirements") or {},
            "chapter_analysis_memories": memory.get("chapter_analysis_memories") or [],
            "chapter_continuation_memories": memory.get("chapter_continuation_memories") or [],
            "chapter_tasks": memory.get("chapter_tasks") or [],
        }
        if self._is_legacy_memory(memory):
            world_parts: List[str] = []
            for key in ("background", "power_system", "organizations", "locations", "rules", "artifacts"):
                world_parts.extend([self.clean_text(str(x)) for x in ((memory.get("world_facts") or {}).get(key) or []) if str(x)])
            style = memory.get("style_profile") or {}
            style_text = "；".join(
                [
                    self.clean_text(str(style.get("narrative_pov") or "")),
                    "、".join(self.normalize_text_list([str(x) for x in (style.get("tone_tags") or []) if str(x)], 6)),
                    "、".join(self.normalize_text_list([str(x) for x in (style.get("rhythm_tags") or []) if str(x)], 6)),
                ]
            ).strip("；")
            current = memory.get("current_state") or {}
            structured.update(
                {
                    "world_settings": "；".join([x for x in world_parts if x]),
                    "plot_outline": "；".join(self.normalize_text_list([str(x) for x in (memory.get("chapter_summaries") or [])], 20)),
                    "writing_style": style_text,
                    "current_progress": {
                        "latest_chapter_number": int(current.get("latest_chapter_number") or 0),
                        "latest_goal": str(current.get("next_writing_focus") or ""),
                        "last_summary": str(current.get("latest_summary") or ""),
                    },
                }
            )
        return structured

    def _merge_structured_memory(
        self,
        base: Dict[str, Any],
        analysis_payload: Dict[str, Any],
        chapter_title: str,
        chapter_number: int = 0,
        chapter_id: str = "",
        chapter_content: str = "",
    ) -> Dict[str, Any]:
        merged = dict(base or {})
        characters = merged.get("characters") or []
        new_chars = analysis_payload.get("characters") or []
        by_name = {str(x.get("name") or ""): x for x in characters if isinstance(x, dict)}
        for item in new_chars:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            if name not in by_name:
                by_name[name] = {"name": name, "traits": [], "relationships": {}}
            traits = [str(x).strip() for x in (item.get("traits") or []) if str(x).strip()]
            by_name[name]["traits"] = list(dict.fromkeys([*(by_name[name].get("traits") or []), *traits]))
            relations = item.get("relationships") or {}
            if isinstance(relations, dict):
                by_name[name]["relationships"] = {**(by_name[name].get("relationships") or {}), **relations}
        merged["characters"] = list(by_name.values())
        world_facts = merged.get("world_facts") or {"background": [], "power_system": [], "organizations": [], "locations": [], "rules": [], "artifacts": []}
        incoming_world = analysis_payload.get("world_facts") if isinstance(analysis_payload.get("world_facts"), dict) else {}
        for key in ("background", "power_system", "organizations", "locations", "rules", "artifacts"):
            items = self.normalize_text_list([str(x).strip() for x in (incoming_world.get(key) or []) if str(x).strip()], 40)
            world_facts[key] = list(dict.fromkeys([*(world_facts.get(key) or []), *items]))[:40]
        merged["world_facts"] = world_facts
        events = merged.get("events") or []
        incoming_events = [x for x in (analysis_payload.get("events") or []) if isinstance(x, dict)]
        merged["events"] = [*events, *incoming_events][-160:]
        style = merged.get("style_profile") or {"narrative_pov": "第三人称有限视角", "tone_tags": [], "rhythm_tags": []}
        style_profile_payload = analysis_payload.get("style_profile") if isinstance(analysis_payload.get("style_profile"), dict) else {}
        if style_profile_payload:
            tone_tags = [str(x).strip() for x in (style_profile_payload.get("tone_tags") or []) if str(x).strip()]
            rhythm_tags = [str(x).strip() for x in (style_profile_payload.get("rhythm_tags") or []) if str(x).strip()]
            if tone_tags:
                style["tone_tags"] = list(dict.fromkeys([*(style.get("tone_tags") or []), *tone_tags[:3]]))
            if rhythm_tags:
                style["rhythm_tags"] = list(dict.fromkeys([*(style.get("rhythm_tags") or []), *rhythm_tags[:3]]))
            narrative_pov = str(style_profile_payload.get("narrative_pov") or "").strip()
            if narrative_pov:
                style["narrative_pov"] = narrative_pov
        style_tags = [str(x).strip() for x in (analysis_payload.get("style_tags") or []) if str(x).strip()]
        if style_tags:
            style["tone_tags"] = list(dict.fromkeys([*(style.get("tone_tags") or []), *style_tags[:3]]))
        merged["style_profile"] = style
        incoming_summaries = self.normalize_text_list(
            [str(x).strip() for x in (analysis_payload.get("chapter_summaries") or []) if str(x).strip()],
            20,
        )
        summary = self.clean_text(str(analysis_payload.get("chapter_summary") or chapter_title or ""))
        if not incoming_summaries and summary:
            incoming_summaries = [summary]
        if incoming_summaries:
            merged["chapter_summaries"] = [*(merged.get("chapter_summaries") or []), *incoming_summaries][-300:]
        flags = [x for x in (analysis_payload.get("continuity_flags") or []) if isinstance(x, dict)]
        merged["continuity_flags"] = [*(merged.get("continuity_flags") or []), *flags][-80:]
        current_state = merged.get("current_state") or {}
        incoming_state = analysis_payload.get("current_state") if isinstance(analysis_payload.get("current_state"), dict) else {}
        current_state.update(
            {
                "latest_chapter_number": int(
                    incoming_state.get("latest_chapter_number")
                    or current_state.get("latest_chapter_number")
                    or 0
                ),
                "latest_summary": str(
                    incoming_state.get("latest_summary")
                    or summary
                    or current_state.get("latest_summary")
                    or ""
                ),
                "active_arc_ids": incoming_state.get("active_arc_ids") or current_state.get("active_arc_ids") or [],
                "recent_conflicts": incoming_state.get("recent_conflicts") or current_state.get("recent_conflicts") or [],
                "next_writing_focus": str(
                    incoming_state.get("next_writing_focus")
                    or current_state.get("next_writing_focus")
                    or ""
                ),
            }
        )
        merged["current_state"] = current_state
        merged["outline_context"] = merged.get("outline_context") or {}
        merged["plot_arcs"] = merged.get("plot_arcs") or []
        global_constraints = merged.get("global_constraints") if isinstance(merged.get("global_constraints"), dict) else {}
        if not global_constraints:
            global_constraints = self._build_global_constraints(merged)
        merged["global_constraints"] = {
            "main_plot": self.clean_text(str(global_constraints.get("main_plot") or "")),
            "hidden_plot": self.clean_text(str(global_constraints.get("hidden_plot") or "")),
            "core_selling_points": self.normalize_text_list([str(x) for x in (global_constraints.get("core_selling_points") or [])], 12),
            "protagonist_core_traits": self.normalize_text_list([str(x) for x in (global_constraints.get("protagonist_core_traits") or [])], 12),
            "must_keep_threads": self.normalize_text_list([str(x) for x in (global_constraints.get("must_keep_threads") or [])], 20),
            "genre_guardrails": self.normalize_text_list([str(x) for x in (global_constraints.get("genre_guardrails") or [])], 12),
        }
        style_requirements = merged.get("style_requirements") if isinstance(merged.get("style_requirements"), dict) else {}
        if not style_requirements:
            style_requirements = self._build_style_requirements(merged.get("style_profile") or {})
        merged["style_requirements"] = {
            "author_voice_keywords": self.normalize_text_list([str(x) for x in (style_requirements.get("author_voice_keywords") or [])], 12),
            "avoid_patterns": self.normalize_text_list([str(x) for x in (style_requirements.get("avoid_patterns") or [])], 12),
            "preferred_rhythm": self.clean_text(str(style_requirements.get("preferred_rhythm") or "")),
            "narrative_distance": self.clean_text(str(style_requirements.get("narrative_distance") or "")),
            "dialogue_density": self.clean_text(str(style_requirements.get("dialogue_density") or "")),
        }
        if chapter_number > 0:
            analysis_memory = {
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "chapter_title": self.clean_text(chapter_title),
                "summary": summary,
                "events": self.normalize_text_list([str(x) for x in incoming_summaries], 12),
                "plot_role": self.clean_text(str(analysis_payload.get("plot_role") or "推进主线")),
                "conflict": self.clean_text(str(analysis_payload.get("conflict") or "")),
                "foreshadowing": self.normalize_text_list([str(x) for x in (analysis_payload.get("foreshadowing") or [])], 12),
                "hook": self.clean_text(str(analysis_payload.get("hook") or "")),
                "problems": self.normalize_text_list([str(x) for x in (analysis_payload.get("problems") or [])], 12),
            }
            continuation_memory = {
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "chapter_title": self.clean_text(chapter_title),
                "scene_summary": summary,
                "scene_state": {"time": "", "location": "", "environment": ""},
                "protagonist_state": {"name": "", "physical_state": "", "emotion_state": "", "current_goal": "", "internal_tension": ""},
                "active_characters": [],
                "active_conflicts": self.normalize_text_list([str(x) for x in (current_state.get("recent_conflicts") or [])], 12),
                "immediate_threads": self.normalize_text_list([str(x) for x in incoming_summaries], 8),
                "long_term_threads": self.normalize_text_list([str(x) for x in (merged.get("chapter_summaries") or [])[-8:]], 8),
                "recent_reveals": self.normalize_text_list([str(x) for x in (analysis_payload.get("reveals") or [])], 8),
                "must_continue_points": self.normalize_text_list([str(x) for x in incoming_summaries], 8),
                "forbidden_jumps": self.normalize_text_list([str(x) for x in (analysis_payload.get("forbidden_jumps") or [])], 8),
                "tone_and_pacing": {"tone": "、".join(style.get("tone_tags") or []), "pace": "、".join(style.get("rhythm_tags") or [])},
                "last_hook": self.clean_text(str(analysis_payload.get("hook") or current_state.get("next_writing_focus") or "")),
            }
            merged["chapter_analysis_memories"] = [
                *(merged.get("chapter_analysis_memories") or []),
                analysis_memory,
            ][-300:]
            merged["chapter_continuation_memories"] = [
                *(merged.get("chapter_continuation_memories") or []),
                continuation_memory,
            ][-300:]
        return merged
