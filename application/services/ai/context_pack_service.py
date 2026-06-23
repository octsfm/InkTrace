from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from application.services.v1.chapter_service import ChapterService
from domain.entities.ai.models import (
    ArcQualityLevel,
    ArcStatus,
    ChapterContextItem,
    CharacterMoment,
    ContextItem,
    ContextPackBuildRequest,
    ContextPackSnapshot,
    ContextPackStatus,
    CurrentChapterContext,
    ImmediateWindow,
    MasterArc,
    SceneMoment,
    SequenceArc,
    SequenceEvent,
    VolumeArc,
)
from domain.repositories.ai.context_pack_repository import ContextPackRepository
from domain.repositories.ai.initialization_repository import InitializationRepository
from domain.repositories.ai.plot_arc_repository import PlotArcRepository
from domain.repositories.ai.story_memory_repository import StoryMemoryRepository
from domain.repositories.ai.story_state_repository import StoryStateRepository
from domain.repositories.ai.vector_index_repository import VectorIndexRepositoryPort


class ContextPackService:
    PRIORITY_PLOT_ARC_IMMEDIATE = 1
    PRIORITY_PLOT_ARC_SEQUENCE = 2
    PRIORITY_PLOT_ARC_VOLUME = 3
    PRIORITY_PLOT_ARC_MASTER = 4
    PRIORITY_USER_INSTRUCTION = 5
    PRIORITY_STORY_STATE = 6
    PRIORITY_CURRENT_CHAPTER = 7
    PRIORITY_STORY_MEMORY = 8
    PRIORITY_RECENT_CHAPTER_SUMMARY = 9
    PRIORITY_CHARACTER = 10
    PRIORITY_LOCATION = 11
    PRIORITY_PLOT_THREAD = 12
    PRIORITY_CONTINUITY_NOTE = 13
    PRIORITY_VECTOR_RECALL = 14

    def __init__(
        self,
        *,
        chapter_service: ChapterService,
        initialization_repository: InitializationRepository,
        story_memory_repository: StoryMemoryRepository,
        story_state_repository: StoryStateRepository,
        context_pack_repository: ContextPackRepository,
        plot_arc_repository: PlotArcRepository | None = None,
        vector_recall_service=None,
        vector_index_repository: VectorIndexRepositoryPort | None = None,
    ) -> None:
        self._chapter_service = chapter_service
        self._initialization_repository = initialization_repository
        self._story_memory_repository = story_memory_repository
        self._story_state_repository = story_state_repository
        self._context_pack_repository = context_pack_repository
        self._plot_arc_repository = plot_arc_repository
        self._vector_recall_service = vector_recall_service
        self._vector_index_repository = vector_index_repository

    def build(self, request: ContextPackBuildRequest) -> ContextPackSnapshot:
        now = self._now()
        pack_id = f"cp_{uuid.uuid4().hex[:12]}"

        initialization = self._initialization_repository.get_latest_by_work(request.work_id)

        # ---------- blocked checks ----------
        if initialization is None or initialization.status.value in ("not_started", "failed", "cancelled"):
            return ContextPackSnapshot(
                context_pack_id=pack_id,
                work_id=request.work_id,
                chapter_id=request.chapter_id,
                status=ContextPackStatus.BLOCKED,
                blocked_reason="initialization_not_completed",
                warnings=["initialization_not_completed"],
                token_budget=request.max_context_tokens,
                created_at=now,
            )

        story_memory = self._story_memory_repository.get_latest_snapshot_by_work(request.work_id)
        story_state = self._story_state_repository.get_latest_analysis_baseline_by_work(request.work_id)

        if story_memory is None:
            return ContextPackSnapshot(
                context_pack_id=pack_id,
                work_id=request.work_id,
                chapter_id=request.chapter_id,
                status=ContextPackStatus.BLOCKED,
                blocked_reason="story_memory_missing",
                warnings=["story_memory_missing"],
                token_budget=request.max_context_tokens,
                created_at=now,
            )
        if story_state is None:
            return ContextPackSnapshot(
                context_pack_id=pack_id,
                work_id=request.work_id,
                chapter_id=request.chapter_id,
                status=ContextPackStatus.BLOCKED,
                blocked_reason="story_state_missing",
                warnings=["story_state_missing"],
                token_budget=request.max_context_tokens,
                created_at=now,
            )

        # ---------- stale checks ----------
        stale = False
        stale_reason_parts: list[str] = []
        if initialization and (initialization.stale or initialization.status.value == "stale"):
            stale = True
            stale_reason_parts.append(initialization.stale_reason or "initialization_stale")
            if story_memory and story_memory.stale_status == "stale":
                stale_reason_parts.append("story_memory_stale")
            if story_state and story_state.stale_status == "stale":
                stale_reason_parts.append("story_state_stale")

        # ---------- assemble items ----------
        items: list[ContextItem] = []
        degraded_reason_parts: list[str] = []
        source_chapter_versions: dict[str, int] = {}

        if initialization:
            source_chapter_versions = dict(initialization.source_chapter_versions)

        chapters = self._chapter_service.list_chapters(request.work_id)
        vector_index_status = self._get_vector_index_status(request.work_id)
        current_chapter = next(
            (
                ch
                for ch in chapters
                if getattr(ch, "id", None) and getattr(getattr(ch, "id", None), "value", "") == request.chapter_id
            ),
            None,
        )
        current_chapter_no = int(getattr(current_chapter, "order_index", 0) or 0)

        master_arc = self._resolve_master_arc(
            work_id=request.work_id,
            initialization=initialization,
            story_memory=story_memory,
            story_state=story_state,
            stale=stale,
        )
        if master_arc is None or master_arc.status in {ArcStatus.PENDING, ArcStatus.FAILED, ArcStatus.EMPTY}:
            return ContextPackSnapshot(
                context_pack_id=pack_id,
                work_id=request.work_id,
                chapter_id=request.chapter_id,
                source_initialization_id=initialization.initialization_id if initialization else "",
                source_story_memory_snapshot_id=story_memory.snapshot_id if story_memory else "",
                source_story_state_id=story_state.story_state_id if story_state else "",
                status=ContextPackStatus.BLOCKED,
                blocked_reason="master_arc_missing",
                warnings=["master_arc_missing"],
                stale=stale,
                stale_reason="; ".join(stale_reason_parts) if stale else "",
                token_budget=request.max_context_tokens,
                created_at=now,
            )

        volume_arc = self._resolve_volume_arc(
            work_id=request.work_id,
            master_arc=master_arc,
            story_state=story_state,
            stale=stale,
            chapter_no=current_chapter_no,
        )
        sequence_arc = self._resolve_sequence_arc(
            work_id=request.work_id,
            master_arc=master_arc,
            volume_arc=volume_arc,
            story_memory=story_memory,
            stale=stale,
            chapter_no=current_chapter_no,
        )
        immediate_window = self._build_immediate_window(
            pack_id=pack_id,
            work_id=request.work_id,
            chapter_id=request.chapter_id,
            chapters=chapters,
            current_chapter=current_chapter,
            story_memory=story_memory,
            story_state=story_state,
            stale=stale,
        )
        plot_arc_statuses = self._build_plot_arc_statuses(master_arc, volume_arc, sequence_arc, immediate_window)
        plot_arc_summary = self._build_plot_arc_summary(master_arc, volume_arc, sequence_arc, immediate_window)
        degraded_reason_parts.extend(
            self._collect_plot_arc_warnings(master_arc, volume_arc, sequence_arc, immediate_window)
        )
        items.extend(
            self._build_plot_arc_items(
                pack_id=pack_id,
                master_arc=master_arc,
                volume_arc=volume_arc,
                sequence_arc=sequence_arc,
                immediate_window=immediate_window,
            )
        )

        # user_instruction
        if request.user_instruction:
            instruction_text = self._summarize_user_instruction(request.user_instruction)
            items.append(ContextItem(
                item_id=f"{pack_id}_instruction",
                source_type="user_instruction",
                priority=self.PRIORITY_USER_INSTRUCTION,
                content_text=instruction_text,
                token_estimate=self._estimate_tokens(instruction_text),
                required=True,
            ))

        # story_state
        if story_state:
            state_text = f"当前故事位置: {story_state.current_position_summary}\n活跃角色: {', '.join(story_state.active_characters)}\n活跃地点: {', '.join(story_state.active_locations)}\n未解决线索: {', '.join(story_state.unresolved_threads)}"
            items.append(ContextItem(
                item_id=f"{pack_id}_state",
                source_type="story_state",
                source_id=story_state.story_state_id,
                priority=self.PRIORITY_STORY_STATE,
                content_text=state_text,
                token_estimate=self._estimate_tokens(state_text),
                required=True,
                stale_status=story_state.stale_status,
            ))

        chapter_text = ""

        # current_chapter
        if current_chapter:
            content = getattr(current_chapter, "content", "")
            title = str(getattr(current_chapter, "title", "") or "")
            chapter_text = self._build_current_chapter_context(title=title, content=content)
            items.append(ContextItem(
                item_id=f"{pack_id}_chapter",
                source_type="current_chapter",
                source_id=request.chapter_id,
                priority=self.PRIORITY_CURRENT_CHAPTER,
                content_text=chapter_text,
                token_estimate=self._estimate_tokens(chapter_text),
                required=(request.continuation_mode in ("continue_chapter",)),
            ))
        elif request.chapter_id:
            chapters_list = self._chapter_service.list_chapters(request.work_id)
            if not chapters_list:
                return ContextPackSnapshot(
                    context_pack_id=pack_id,
                    work_id=request.work_id,
                    chapter_id=request.chapter_id,
                    status=ContextPackStatus.BLOCKED,
                    blocked_reason="no_confirmed_chapters",
                    warnings=["no_confirmed_chapters"],
                    token_budget=request.max_context_tokens,
                    created_at=now,
                )

        # story_memory
        if story_memory:
            memory_text = f"全书进度摘要: {story_memory.global_summary}\n角色: {', '.join(story_memory.characters)}\n地点: {', '.join(story_memory.locations)}\n剧情线索: {', '.join(story_memory.plot_threads)}"
            items.append(ContextItem(
                item_id=f"{pack_id}_memory",
                source_type="story_memory",
                source_id=story_memory.snapshot_id,
                priority=self.PRIORITY_STORY_MEMORY,
                content_text=memory_text,
                token_estimate=self._estimate_tokens(memory_text),
                required=False,
                stale_status=story_memory.stale_status,
            ))

        # recent chapter summaries from story_memory
        if story_memory and story_memory.chapter_summaries:
            for summary_item in story_memory.chapter_summaries[-3:]:
                ch_text = f"章节 {summary_item.get('chapter_id', '')}: {summary_item.get('summary', '')}"
                items.append(ContextItem(
                    item_id=f"{pack_id}_recap_{summary_item.get('chapter_id', '')}",
                    source_type="recent_chapter_summary",
                    source_id=summary_item.get("chapter_id", ""),
                    priority=self.PRIORITY_RECENT_CHAPTER_SUMMARY,
                    content_text=ch_text,
                    token_estimate=self._estimate_tokens(ch_text),
                    required=False,
                ))

        # characters / locations / plot threads from story_memory and story_state
        combined_chars = list(dict.fromkeys((story_memory.characters if story_memory else []) + (story_state.active_characters if story_state else [])))
        for char in combined_chars[:5]:
            items.append(ContextItem(
                item_id=f"{pack_id}_char_{char}",
                source_type="character",
                source_id=char,
                priority=self.PRIORITY_CHARACTER,
                content_text=f"角色: {char}",
                token_estimate=self._estimate_tokens(char) + 2,
                required=False,
            ))

        combined_locs = list(dict.fromkeys((story_memory.locations if story_memory else []) + (story_state.active_locations if story_state else [])))
        for loc in combined_locs[:3]:
            items.append(ContextItem(
                item_id=f"{pack_id}_loc_{loc}",
                source_type="location",
                source_id=loc,
                priority=self.PRIORITY_LOCATION,
                content_text=f"地点: {loc}",
                token_estimate=self._estimate_tokens(loc) + 2,
                required=False,
            ))

        for thread in (story_memory.plot_threads if story_memory else [])[:5]:
            items.append(ContextItem(
                item_id=f"{pack_id}_plot_{thread}",
                source_type="plot_thread",
                source_id=thread,
                priority=self.PRIORITY_PLOT_THREAD,
                content_text=f"剧情线索: {thread}",
                token_estimate=self._estimate_tokens(thread) + 3,
                required=False,
            ))

        if story_state and story_state.continuity_notes:
            for idx, note in enumerate(story_state.continuity_notes[:3]):
                items.append(ContextItem(
                    item_id=f"{pack_id}_note_{idx}",
                    source_type="continuity_note",
                    source_id=story_state.story_state_id,
                    priority=self.PRIORITY_CONTINUITY_NOTE,
                    content_text=note,
                    token_estimate=self._estimate_tokens(note),
                    required=False,
                ))

        vector_recall_items, vector_recall_status, vector_recall_warnings = self._build_vector_recall_items(
            request=request,
            pack_id=pack_id,
            chapter_text=chapter_text,
            story_memory=story_memory,
            story_state=story_state,
            vector_index_status=vector_index_status,
        )
        items.extend(vector_recall_items)
        degraded_reason_parts.extend(vector_recall_warnings)

        # ---------- Priority sort ----------
        items.sort(key=lambda item: item.priority)
        items, _required_trimmed, required_trim_warnings, required_overflow = self._fit_required_items_with_budget(
            items,
            max_context_tokens=request.max_context_tokens,
        )
        degraded_reason_parts.extend(required_trim_warnings)

        # ---------- Token budget ----------
        total_tokens = 0
        included: list[ContextItem] = []
        trimmed: list[ContextItem] = []
        required_tokens = sum(item.token_estimate for item in items if item.required and item.included)

        if required_overflow > 0 or required_tokens > request.max_context_tokens:
            return ContextPackSnapshot(
                context_pack_id=pack_id,
                work_id=request.work_id,
                chapter_id=request.chapter_id,
                source_initialization_id=initialization.initialization_id if initialization else "",
                source_story_memory_snapshot_id=story_memory.snapshot_id if story_memory else "",
                source_story_state_id=story_state.story_state_id if story_state else "",
                status=ContextPackStatus.BLOCKED,
                blocked_reason="required_context_over_budget",
                warnings=degraded_reason_parts + ["required_context_over_budget"],
                vector_recall_status=vector_recall_status,
                context_items=[item.model_copy(update={"included": False, "trim_reason": "required_over_budget"}) for item in items],
                token_budget=request.max_context_tokens,
                estimated_token_count=required_tokens,
                trimmed_items=[],
                stale=stale,
                stale_reason="; ".join(stale_reason_parts) if stale else "",
                source_chapter_versions=source_chapter_versions,
                plot_arc_statuses=plot_arc_statuses,
                plot_arc_summary=plot_arc_summary,
                created_at=now,
            )

        for item in items:
            if not item.included:
                trimmed.append(item)
                included.append(item)
                continue
            if total_tokens + item.token_estimate <= request.max_context_tokens:
                total_tokens += item.token_estimate
                included.append(item.model_copy(update={"included": True, "trim_reason": ""}))
            else:
                trimmed_item = item.model_copy(update={"included": False, "trim_reason": "token_budget_exceeded"})
                trimmed.append(trimmed_item)
                included.append(trimmed_item)

        # ---------- Determine status ----------
        if trimmed and request.allow_degraded:
            status = ContextPackStatus.DEGRADED
            degraded_reason_parts.append("optional_trimmed")
        elif degraded_reason_parts:
            status = ContextPackStatus.DEGRADED
        elif stale:
            status = ContextPackStatus.DEGRADED
        else:
            status = ContextPackStatus.READY

        summary_parts = [item.content_text[:100] for item in included if item.included and item.content_text]
        return ContextPackSnapshot(
            context_pack_id=pack_id,
            work_id=request.work_id,
            chapter_id=request.chapter_id,
            source_initialization_id=initialization.initialization_id if initialization else "",
            source_story_memory_snapshot_id=story_memory.snapshot_id if story_memory else "",
            source_story_state_id=story_state.story_state_id if story_state else "",
            status=status,
            blocked_reason="",
            degraded_reason="; ".join(degraded_reason_parts) if degraded_reason_parts and status == ContextPackStatus.DEGRADED else "",
            warnings=degraded_reason_parts,
            vector_recall_status=vector_recall_status,
            context_items=included,
            token_budget=request.max_context_tokens,
            estimated_token_count=total_tokens,
            trimmed_items=trimmed,
            stale=stale,
            stale_reason="; ".join(stale_reason_parts) if stale else "",
            source_chapter_versions=source_chapter_versions,
            plot_arc_statuses=plot_arc_statuses,
            plot_arc_summary=plot_arc_summary,
            summary="; ".join(part for part in summary_parts if part)[:500],
            created_at=now,
        )

    def build_and_save(self, request: ContextPackBuildRequest) -> ContextPackSnapshot:
        snapshot = self.build(request)
        return self._context_pack_repository.save(snapshot)

    def get(self, context_pack_id: str) -> ContextPackSnapshot:
        return self._context_pack_repository.get(context_pack_id)

    def get_latest(self, work_id: str, chapter_id: str = "") -> ContextPackSnapshot | None:
        return self._context_pack_repository.get_latest_by_work(work_id, chapter_id=chapter_id)

    def list_by_work(self, work_id: str) -> list[ContextPackSnapshot]:
        return self._context_pack_repository.list_by_work(work_id)

    def evaluate_readiness(self, work_id: str, chapter_id: str = "") -> dict[str, object]:
        request = ContextPackBuildRequest(work_id=work_id, chapter_id=chapter_id)
        snapshot = self.build(request)
        return {
            "context_pack_id": snapshot.context_pack_id,
            "status": snapshot.status.value,
            "blocked_reason": snapshot.blocked_reason,
            "degraded_reason": snapshot.degraded_reason,
            "warnings": snapshot.warnings,
            "estimated_token_count": snapshot.estimated_token_count,
            "stale": snapshot.stale,
            "stale_reason": snapshot.stale_reason,
            "plot_arc_statuses": snapshot.plot_arc_statuses,
            "plot_arc_summary": snapshot.plot_arc_summary,
        }

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(re.sub(r"\s+", "", text)) // 2)

    def _summarize_user_instruction(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        return f"用户续写意图已记录（长度 {len(cleaned)} 字）"

    def _build_current_chapter_context(self, *, title: str, content: str) -> str:
        cleaned = re.sub(r"\s+", " ", content or "").strip()
        return f"章节标题: {title}\n正文概况: 已省略原文，仅保留章节定位与长度（{len(cleaned)}字）"

    def _resolve_master_arc(self, *, work_id: str, initialization, story_memory, story_state, stale: bool) -> MasterArc | None:
        if self._plot_arc_repository is not None:
            stored_arc = self._plot_arc_repository.get_master_arc(work_id)
            if stored_arc is not None:
                return self._apply_stale_to_arc(stored_arc, stale=stale, stale_code="master_arc_stale")
        return self._build_master_arc(
            work_id=work_id,
            initialization=initialization,
            story_memory=story_memory,
            story_state=story_state,
            stale=stale,
        )

    def _resolve_volume_arc(self, *, work_id: str, master_arc: MasterArc, story_state, stale: bool, chapter_no: int) -> VolumeArc:
        if self._plot_arc_repository is not None:
            stored_arc = self._plot_arc_repository.get_active_volume_arc(work_id, chapter_no=chapter_no)
            if stored_arc is not None:
                return self._apply_stale_to_arc(stored_arc, stale=stale, stale_code="volume_arc_stale")
        return self._build_volume_arc(
            work_id=work_id,
            master_arc=master_arc,
            story_state=story_state,
            stale=stale,
        )

    def _resolve_sequence_arc(
        self,
        *,
        work_id: str,
        master_arc: MasterArc,
        volume_arc: VolumeArc,
        story_memory,
        stale: bool,
        chapter_no: int,
    ) -> SequenceArc:
        if self._plot_arc_repository is not None:
            stored_arc = self._plot_arc_repository.get_active_sequence_arc(work_id, chapter_no=chapter_no)
            if stored_arc is not None:
                return self._apply_stale_to_arc(stored_arc, stale=stale, stale_code="sequence_arc_stale")
        return self._build_sequence_arc(
            work_id=work_id,
            master_arc=master_arc,
            volume_arc=volume_arc,
            story_memory=story_memory,
            stale=stale,
        )

    def _apply_stale_to_arc(self, arc, *, stale: bool, stale_code: str):
        if not stale:
            return arc
        warning_codes = self._dedupe_warnings(list(getattr(arc, "warning_codes", [])) + [stale_code])
        return arc.model_copy(
            update={
                "status": ArcStatus.STALE,
                "stale_status": "stale",
                "warning_codes": warning_codes,
            }
        )

    def _build_master_arc(self, *, work_id: str, initialization, story_memory, story_state, stale: bool) -> MasterArc | None:
        if initialization is None or story_memory is None or story_state is None:
            return None
        outline = initialization.outline_analysis
        inferred_without_outline = bool(outline is None or outline.outline_empty)
        warning_codes: list[str] = []
        status = ArcStatus.READY
        quality_level = ArcQualityLevel.MINIMAL
        now = self._now()
        if inferred_without_outline:
            status = ArcStatus.DEGRADED
            warning_codes.append("master_arc_inferred_without_outline")
        if stale:
            status = ArcStatus.STALE
            warning_codes.append("master_arc_stale")

        arc_title = str((outline.title if outline else "") or "主线轨道").strip() or "主线轨道"
        arc_logline = str((outline.global_summary if outline else "") or story_memory.global_summary or "").strip()
        ultimate_goal = arc_logline or "待补充主线目标"
        current_stage = str(story_state.current_position_summary or "待补充当前阶段").strip()
        core_theme = str((outline.tone if outline else "") or "延续既有叙事基调").strip()
        final_conflict = str(
            (story_memory.plot_threads[0] if story_memory.plot_threads else "")
            or (story_state.unresolved_threads[0] if story_state.unresolved_threads else "")
            or "待补充终局冲突"
        ).strip()
        protagonist_motivation = final_conflict or ultimate_goal
        if not ultimate_goal or not current_stage:
            quality_level = ArcQualityLevel.PLACEHOLDER
            warning_codes.append("arc_placeholder_only")
            if status == ArcStatus.READY:
                status = ArcStatus.DEGRADED

        return MasterArc(
            master_arc_id=f"ma_{work_id}",
            work_id=work_id,
            arc_title=arc_title,
            version=1,
            arc_logline=arc_logline,
            status=status,
            quality_level=quality_level,
            ultimate_goal=ultimate_goal,
            protagonist_motivation=protagonist_motivation,
            current_stage=current_stage,
            stage_position=current_stage,
            core_theme=core_theme,
            final_conflict=final_conflict,
            main_antagonist="待补充",
            key_milestones=story_memory.plot_threads[:3],
            endgame_foreshadows=story_memory.plot_threads[:2],
            source_initialization_id=initialization.initialization_id,
            source_outline_ref=arc_title,
            source_refs=[story_memory.snapshot_id, story_state.story_state_id],
            warning_codes=warning_codes,
            stale_status="stale" if stale else "fresh",
            built_from_text_inference=inferred_without_outline,
            built_by="memory_agent",
            last_updated_by="memory_agent",
            created_at=now,
            updated_at=now,
        )

    def _build_volume_arc(self, *, work_id: str, master_arc: MasterArc, story_state, stale: bool) -> VolumeArc:
        status = ArcStatus.STALE if stale else ArcStatus.PENDING
        warning_codes = ["arc_placeholder_only"]
        now = self._now()
        if stale:
            warning_codes.append("volume_arc_stale")
        return VolumeArc(
            volume_arc_id=f"va_{work_id}_1",
            work_id=work_id,
            master_arc_id=master_arc.master_arc_id,
            version=1,
            volume_no=1,
            status=status,
            quality_level=ArcQualityLevel.PLACEHOLDER,
            stage_goal=str(story_state.current_position_summary or "等待方向确认后生成当前卷目标。").strip(),
            core_conflict=str(story_state.unresolved_threads[0] if story_state.unresolved_threads else "等待方向确认后补充当前卷冲突。").strip(),
            climax_description="等待方向选择与阶段目标确认后补充卷高潮。",
            resolution_condition="等待方向确认后定义本卷收束条件。",
            stage_open_loops=list(story_state.unresolved_threads[:5]),
            key_characters=list(story_state.active_characters[:5]),
            chapter_range={"from_chapter": 1, "to_chapter_estimate": 0},
            source_refs=[master_arc.master_arc_id],
            warning_codes=warning_codes,
            stale_status="stale" if stale else "fresh",
            built_by="planner_agent",
            last_updated_by="planner_agent",
            created_at=now,
            updated_at=now,
        )

    def _build_sequence_arc(self, *, work_id: str, master_arc: MasterArc, volume_arc: VolumeArc, story_memory, stale: bool) -> SequenceArc:
        events: list[SequenceEvent] = []
        now = self._now()
        for index, summary_item in enumerate(story_memory.chapter_summaries[-3:], start=1):
            summary = str(summary_item.get("summary", "") or "").strip()
            events.append(
                SequenceEvent(
                    event_id=f"seq_{index}",
                    event_order=index,
                    event_name=f"近期事件 {index}",
                    description=summary[:120],
                    event_type="development",
                )
            )
        warning_codes = ["arc_placeholder_only"]
        if stale:
            warning_codes.append("sequence_arc_stale")
        return SequenceArc(
            sequence_arc_id=f"sa_{work_id}_1",
            work_id=work_id,
            volume_arc_id=volume_arc.volume_arc_id,
            master_arc_id=master_arc.master_arc_id,
            version=1,
            seq_no=1,
            status=ArcStatus.STALE if stale else ArcStatus.PENDING,
            quality_level=ArcQualityLevel.PLACEHOLDER,
            sequence_goal="等待章节计划确认后生成当前序列目标。",
            key_events=events,
            turning_points=list(story_memory.plot_threads[:2]),
            required_beats=list(story_memory.plot_threads[:3]),
            chapter_range={"from_chapter": 1, "to_chapter_estimate": 0},
            source_refs=[master_arc.master_arc_id, volume_arc.volume_arc_id],
            warning_codes=warning_codes,
            stale_status="stale" if stale else "fresh",
            built_by="planner_agent",
            last_updated_by="planner_agent",
            created_at=now,
            updated_at=now,
        )

    def _build_immediate_window(self, *, pack_id: str, work_id: str, chapter_id: str, chapters: list[object], current_chapter, story_memory, story_state, stale: bool) -> ImmediateWindow:
        recent_chapters_summary: list[ChapterContextItem] = []
        recent_3_chapters_detail: list[ChapterContextItem] = []
        chapter_lookup = {
            getattr(getattr(chapter, "id", None), "value", ""): chapter
            for chapter in chapters
            if getattr(chapter, "id", None) is not None
        }
        for index, summary_item in enumerate(story_memory.chapter_summaries[-10:], start=1):
            chapter_id_value = str(summary_item.get("chapter_id", "") or "")
            chapter = chapter_lookup.get(chapter_id_value)
            chapter_no = int(getattr(chapter, "order_index", index) or index)
            title = str(getattr(chapter, "title", "") or f"第{chapter_no}章")
            item = ChapterContextItem(
                chapter_id=chapter_id_value,
                chapter_no=chapter_no,
                title=title,
                summary=str(summary_item.get("summary", "") or "")[:200],
                key_event=str(summary_item.get("summary", "") or "")[:100],
            )
            recent_chapters_summary.append(item)
        recent_3_chapters_detail = recent_chapters_summary[-3:]

        current_context = None
        if current_chapter is not None:
            content = str(getattr(current_chapter, "content", "") or "")
            title = str(getattr(current_chapter, "title", "") or "")
            current_context = CurrentChapterContext(
                chapter_id=chapter_id,
                chapter_no=int(getattr(current_chapter, "order_index", 0) or 0),
                title=title,
                content_summary=self._build_current_chapter_context(title=title, content=content),
                writing_position=str(story_state.current_position_summary or "章节推进中").strip(),
                unresolved_in_chapter=list(story_state.unresolved_threads[:3]),
            )

        character_states = [
            CharacterMoment(
                character_name=character,
                current_status=str(story_state.current_position_summary or "处于当前剧情推进中").strip(),
                location=str(story_state.active_locations[0] if story_state.active_locations else ""),
                last_action=str(story_state.unresolved_threads[0] if story_state.unresolved_threads else ""),
            )
            for character in story_state.active_characters[:5]
        ]
        scene_details = self._select_scene_details(story_memory=story_memory, chapter_id=chapter_id)

        warning_codes: list[str] = []
        if stale:
            warning_codes.append("immediate_window_stale")
        if not recent_chapters_summary:
            warning_codes.append("immediate_window_empty")
            status = ArcStatus.DEGRADED
            quality_level = ArcQualityLevel.MINIMAL
        elif len(recent_chapters_summary) < 3:
            warning_codes.append("immediate_window_partial")
            status = ArcStatus.DEGRADED
            quality_level = ArcQualityLevel.MINIMAL
        else:
            status = ArcStatus.READY
            quality_level = ArcQualityLevel.COMPLETE
        if stale:
            status = ArcStatus.STALE

        previous_hook = recent_chapters_summary[-1].summary if recent_chapters_summary else ""
        return ImmediateWindow(
            window_id=f"iw_{pack_id}",
            work_id=work_id,
            context_pack_id=pack_id,
            status=status,
            quality_level=quality_level,
            recent_chapters_summary=recent_chapters_summary,
            recent_3_chapters_detail=recent_3_chapters_detail,
            current_chapter_context=current_context,
            previous_chapter_hook=previous_hook[:300],
            character_current_states=character_states,
            active_plot_threads=list(story_memory.plot_threads[:5]),
            scene_details=scene_details,
            warning_codes=warning_codes,
            stale_status="stale" if stale else "fresh",
            assembled_at=self._now(),
        )

    def _build_plot_arc_items(self, *, pack_id: str, master_arc: MasterArc, volume_arc: VolumeArc, sequence_arc: SequenceArc, immediate_window: ImmediateWindow) -> list[ContextItem]:
        sequence_events = [event.description or event.event_name for event in sequence_arc.key_events[:3]]
        immediate_recap = [item.summary for item in immediate_window.recent_3_chapters_detail]
        return [
            ContextItem(
                item_id=f"{pack_id}_plot_master",
                source_type="plot_arc_master",
                source_id=master_arc.master_arc_id,
                priority=self.PRIORITY_PLOT_ARC_MASTER,
                content_text=f"全文弧目标: {master_arc.ultimate_goal}\n当前阶段: {master_arc.current_stage}\n主题: {master_arc.core_theme}",
                summary=f"{master_arc.ultimate_goal} / {master_arc.current_stage}",
                token_estimate=self._estimate_tokens(f"{master_arc.ultimate_goal} {master_arc.current_stage} {master_arc.core_theme}"),
                required=True,
                stale_status=master_arc.stale_status,
                warning="; ".join(master_arc.warning_codes),
                metadata={"status": master_arc.status.value, "quality_level": master_arc.quality_level.value},
            ),
            ContextItem(
                item_id=f"{pack_id}_plot_volume",
                source_type="plot_arc_volume",
                source_id=volume_arc.volume_arc_id,
                priority=self.PRIORITY_PLOT_ARC_VOLUME,
                content_text=f"当前卷目标: {volume_arc.stage_goal}\n当前卷冲突: {volume_arc.core_conflict}",
                summary=volume_arc.stage_goal,
                token_estimate=self._estimate_tokens(f"{volume_arc.stage_goal} {volume_arc.core_conflict}"),
                required=True,
                stale_status=volume_arc.stale_status,
                warning="; ".join(volume_arc.warning_codes),
                metadata={"status": volume_arc.status.value, "quality_level": volume_arc.quality_level.value},
            ),
            ContextItem(
                item_id=f"{pack_id}_plot_sequence",
                source_type="plot_arc_sequence",
                source_id=sequence_arc.sequence_arc_id,
                priority=self.PRIORITY_PLOT_ARC_SEQUENCE,
                content_text=f"当前序列目标: {sequence_arc.sequence_goal}\n关键事件: {'; '.join(sequence_events)}",
                summary=sequence_arc.sequence_goal,
                token_estimate=self._estimate_tokens(f"{sequence_arc.sequence_goal} {' '.join(sequence_events)}"),
                required=True,
                stale_status=sequence_arc.stale_status,
                warning="; ".join(sequence_arc.warning_codes),
                metadata={"status": sequence_arc.status.value, "quality_level": sequence_arc.quality_level.value},
            ),
            ContextItem(
                item_id=f"{pack_id}_plot_immediate",
                source_type="plot_arc_immediate",
                source_id=immediate_window.window_id,
                priority=self.PRIORITY_PLOT_ARC_IMMEDIATE,
                content_text=f"近期摘要: {'; '.join(immediate_recap)}\n活跃线索: {', '.join(immediate_window.active_plot_threads)}",
                summary=immediate_window.current_chapter_context.content_summary if immediate_window.current_chapter_context else "; ".join(immediate_recap),
                token_estimate=self._estimate_tokens(f"{' '.join(immediate_recap)} {' '.join(immediate_window.active_plot_threads)}"),
                required=True,
                stale_status=immediate_window.stale_status,
                warning="; ".join(immediate_window.warning_codes),
                metadata={"status": immediate_window.status.value, "quality_level": immediate_window.quality_level.value},
            ),
        ]

    def _build_plot_arc_statuses(self, master_arc: MasterArc, volume_arc: VolumeArc, sequence_arc: SequenceArc, immediate_window: ImmediateWindow) -> dict[str, dict[str, object]]:
        return {
            "master_arc": self._arc_status_payload(master_arc.status, master_arc.quality_level, master_arc.warning_codes),
            "volume_arc": self._arc_status_payload(volume_arc.status, volume_arc.quality_level, volume_arc.warning_codes),
            "sequence_arc": self._arc_status_payload(sequence_arc.status, sequence_arc.quality_level, sequence_arc.warning_codes),
            "immediate_window": self._arc_status_payload(immediate_window.status, immediate_window.quality_level, immediate_window.warning_codes),
        }

    def _arc_status_payload(self, status: ArcStatus, quality_level: ArcQualityLevel, warning_codes: list[str]) -> dict[str, object]:
        return {
            "status": status.value,
            "quality_level": quality_level.value,
            "warning_codes": list(warning_codes),
        }

    def _build_plot_arc_summary(self, master_arc: MasterArc, volume_arc: VolumeArc, sequence_arc: SequenceArc, immediate_window: ImmediateWindow) -> dict[str, dict[str, object]]:
        return {
            "master_arc": {
                "arc_title": master_arc.arc_title,
                "ultimate_goal": master_arc.ultimate_goal,
                "current_stage": master_arc.current_stage,
                "core_theme": master_arc.core_theme,
            },
            "volume_arc": {
                "stage_goal": volume_arc.stage_goal,
                "core_conflict": volume_arc.core_conflict,
                "stage_open_loops": list(volume_arc.stage_open_loops),
                "key_characters": list(volume_arc.key_characters),
                "foreshadow_planted": list(volume_arc.foreshadow_planted),
                "foreshadow_resolved": list(volume_arc.foreshadow_resolved),
            },
            "sequence_arc": {
                "sequence_goal": sequence_arc.sequence_goal,
                "key_events": [event.description or event.event_name for event in sequence_arc.key_events[:5]],
                "turning_points": list(sequence_arc.turning_points),
                "required_beats": list(sequence_arc.required_beats),
            },
            "immediate_window": {
                "recent_chapters_summary": [item.summary for item in immediate_window.recent_chapters_summary],
                "previous_chapter_hook": immediate_window.previous_chapter_hook,
                "active_plot_threads": list(immediate_window.active_plot_threads),
                "scene_details": [item.model_dump(mode="json") for item in immediate_window.scene_details],
                "character_current_states": [
                    {
                        "character_name": item.character_name,
                        "current_status": item.current_status,
                        "location": item.location,
                    }
                    for item in immediate_window.character_current_states
                ],
                "current_chapter_context": immediate_window.current_chapter_context.model_dump(mode="json")
                if immediate_window.current_chapter_context is not None
                else {},
            },
        }

    def _select_scene_details(self, *, story_memory, chapter_id: str) -> list[SceneMoment]:
        details = list(getattr(story_memory, "scene_details", []))
        current_chapter_items = [item for item in details if str(getattr(item, "chapter_id", "")) == chapter_id]
        selected = current_chapter_items or details[-3:]
        scenes: list[SceneMoment] = []
        for item in selected[:5]:
            scenes.append(
                SceneMoment(
                    location=str(getattr(item, "location", "") or ""),
                    time_of_day=str(getattr(item, "time_of_day", "") or ""),
                    atmosphere=str(getattr(item, "atmosphere", "") or ""),
                    characters_present=list(getattr(item, "characters_present", []) or []),
                    emotional_tone=str(getattr(item, "emotional_tone", "") or ""),
                    pov_hint=str(getattr(item, "pov_hint", "") or ""),
                    reveal_points=list(getattr(item, "reveal_points", []) or []),
                )
            )
        return scenes

    def _collect_plot_arc_warnings(self, master_arc: MasterArc, volume_arc: VolumeArc, sequence_arc: SequenceArc, immediate_window: ImmediateWindow) -> list[str]:
        warnings: list[str] = []
        warnings.extend(master_arc.warning_codes)
        warnings.extend(self._map_non_master_arc_warnings(volume_arc.status, volume_arc.warning_codes, missing_code="volume_arc_missing", degraded_code="volume_arc_degraded", stale_code="volume_arc_stale"))
        warnings.extend(self._map_non_master_arc_warnings(sequence_arc.status, sequence_arc.warning_codes, missing_code="sequence_arc_missing", degraded_code="sequence_arc_degraded", stale_code="sequence_arc_stale"))
        warnings.extend(immediate_window.warning_codes)
        return self._dedupe_warnings(warnings)

    def _map_non_master_arc_warnings(self, status: ArcStatus, warning_codes: list[str], *, missing_code: str, degraded_code: str, stale_code: str) -> list[str]:
        warnings = list(warning_codes)
        if status in {ArcStatus.PENDING, ArcStatus.EMPTY, ArcStatus.FAILED}:
            warnings.append(missing_code)
        elif status == ArcStatus.DEGRADED:
            warnings.append(degraded_code)
        elif status == ArcStatus.STALE:
            warnings.append(stale_code)
        return warnings

    def _dedupe_warnings(self, warnings: list[str]) -> list[str]:
        return list(dict.fromkeys(item for item in warnings if item))

    def _fit_required_items_with_budget(
        self,
        items: list[ContextItem],
        *,
        max_context_tokens: int,
    ) -> tuple[list[ContextItem], list[ContextItem], list[str], int]:
        fitted_items = [item.model_copy() for item in items]
        required_tokens = sum(item.token_estimate for item in fitted_items if item.required and item.included)
        if required_tokens <= max_context_tokens:
            return fitted_items, [], [], 0
        overflow = required_tokens - max_context_tokens
        trimmed_items: list[ContextItem] = []
        warnings: list[str] = []
        trim_candidates = [
            item
            for item in fitted_items
            if item.required
            and item.source_type in {"plot_arc_sequence", "plot_arc_volume"}
            and item.included
        ]
        trim_candidates.sort(key=lambda item: item.priority)
        for item in trim_candidates:
            overflow -= item.token_estimate
            item.included = False
            item.trim_reason = "arc_trimmed"
            item.token_estimate = 0
            trimmed_items.append(item.model_copy())
        if trimmed_items:
            warnings.append("arc_trimmed")
        return fitted_items, trimmed_items, warnings, max(overflow, 0)

    def _build_vector_recall_items(
        self,
        *,
        request: ContextPackBuildRequest,
        pack_id: str,
        chapter_text: str,
        story_memory,
        story_state,
        vector_index_status: dict[str, object] | None,
    ) -> tuple[list[ContextItem], str, list[str]]:
        warnings: list[str] = []
        index_status = str((vector_index_status or {}).get("index_status", "") or "").strip()
        index_stale_status = str((vector_index_status or {}).get("stale_status", "fresh") or "fresh").strip()
        if index_status in {"missing", "not_built", "failed", "degraded"}:
            return [], "degraded", ["vector_index_unavailable"]
        if index_status == "stale" or index_stale_status in {"stale", "partial_stale"}:
            warnings.append("vector_index_stale_warning")
            if not request.allow_stale_vector:
                return [], "degraded", warnings

        if self._vector_recall_service is None:
            return [], "degraded", self._dedupe_warnings(warnings + ["vector_recall_unavailable"])

        try:
            query_text = self._build_vector_query_text(request, chapter_text, story_memory, story_state)
        except Exception:
            return [], "skipped", self._dedupe_warnings(warnings + ["query_text_build_failed", "rag_skipped"])

        recall_query = _RecallQuery(
            work_id=request.work_id,
            target_chapter_id=request.chapter_id,
            target_chapter_order=0,
            query_text=query_text,
            top_k=3,
            score_threshold=0.6,
            recall_scope="confirmed_chapters",
            allow_stale=request.allow_stale_vector,
            request_id=request.request_id,
            trace_id=request.trace_id,
        )
        try:
            raw_items = self._vector_recall_service.recall(recall_query)
        except Exception:
            return [], "failed", self._dedupe_warnings(warnings + ["vector_recall_failed"])

        recall_items, filter_warnings = self._normalize_vector_recall_items(
            pack_id,
            raw_items,
            allow_stale=request.allow_stale_vector,
        )
        warnings.extend(filter_warnings)
        if not recall_items:
            empty_reason = "recall_result_empty_after_filter" if filter_warnings else "vector_recall_empty"
            return [], "degraded", self._dedupe_warnings(warnings + [empty_reason])
        recall_status = "degraded" if warnings else "ready"
        return recall_items, recall_status, self._dedupe_warnings(warnings)

    def _build_vector_query_text(self, request: ContextPackBuildRequest, chapter_text: str, story_memory, story_state) -> str:
        parts = [
            str(request.user_instruction or "").strip(),
            str(story_state.current_position_summary if story_state else "").strip(),
            str(story_memory.global_summary if story_memory else "").strip(),
            str(chapter_text or "").strip(),
        ]
        query_text = " ".join(part for part in parts if part).strip()
        if not query_text:
            raise ValueError("query_text_build_failed")
        return query_text[:500]

    def _normalize_vector_recall_items(
        self,
        pack_id: str,
        raw_items: object,
        *,
        allow_stale: bool,
    ) -> tuple[list[ContextItem], list[str]]:
        normalized: list[ContextItem] = []
        warnings: list[str] = []
        for index, raw_item in enumerate(raw_items or []):
            if isinstance(raw_item, ContextItem):
                if raw_item.stale_status in {"stale", "partial_stale"} and not allow_stale:
                    warnings.append("stale_content")
                    continue
                normalized.append(raw_item.model_copy(update={"priority": self.PRIORITY_VECTOR_RECALL}))
                continue
            if not isinstance(raw_item, dict):
                continue
            content_text = str(raw_item.get("content_text", "") or "").strip()
            if not content_text:
                continue
            metadata = dict(raw_item.get("metadata", {}) or {})
            source_value = str(
                metadata.get("source", metadata.get("source_type", raw_item.get("source", raw_item.get("source_type", "")))) or ""
            ).strip()
            if source_value and source_value != "confirmed_chapter":
                warnings.append("illegal_recall_source")
                continue
            stale_status = str(raw_item.get("stale_status", "fresh") or "fresh")
            chunk_status = str(metadata.get("status", metadata.get("index_status", "")) or "").strip()
            if chunk_status in {"deleted", "invalid"}:
                warnings.append("deleted_content")
                continue
            if chunk_status == "failed":
                warnings.append("failed_chunk")
                continue
            if chunk_status == "skipped":
                warnings.append("skipped_chunk")
                continue
            if stale_status in {"stale", "partial_stale"} and not allow_stale:
                warnings.append("stale_content")
                continue
            normalized.append(
                ContextItem(
                    item_id=str(raw_item.get("item_id", f"{pack_id}_recall_{index}")),
                    source_type="vector_recall",
                    source_id=str(raw_item.get("source_id", "")),
                    priority=self.PRIORITY_VECTOR_RECALL,
                    content_text=content_text[:200],
                    token_estimate=int(raw_item.get("token_estimate", self._estimate_tokens(content_text))),
                    required=False,
                    included=True,
                    stale_status=stale_status,
                    warning=str(raw_item.get("warning", "")),
                    filter_reason=str(raw_item.get("filter_reason", "")),
                    metadata=metadata,
                )
            )
        return normalized, self._dedupe_warnings(warnings)

    def _get_vector_index_status(self, work_id: str) -> dict[str, object] | None:
        if self._vector_index_repository is None:
            return None
        try:
            return self._vector_index_repository.get_index_status_by_work(work_id)
        except Exception:
            return None

    def _truncate_text(self, text: str, max_chars: int) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        return cleaned[:max_chars] + ("..." if len(cleaned) > max_chars else "")

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class _RecallQuery:
    query_text: str
    work_id: str = ""
    target_chapter_id: str = ""
    target_chapter_order: int = 0
    top_k: int = 3
    score_threshold: float = 0.6
    recall_scope: str = "confirmed_chapters"
    allow_stale: bool = False
    request_id: str = ""
    trace_id: str = ""
