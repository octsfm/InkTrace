from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from application.services.v1.chapter_service import ChapterService
from domain.entities.ai.models import (
    ContextItem,
    ContextPackBuildRequest,
    ContextPackSnapshot,
    ContextPackStatus,
)
from domain.repositories.ai.context_pack_repository import ContextPackRepository
from domain.repositories.ai.initialization_repository import InitializationRepository
from domain.repositories.ai.story_memory_repository import StoryMemoryRepository
from domain.repositories.ai.story_state_repository import StoryStateRepository


class ContextPackService:
    PRIORITY_SYSTEM_POLICY = 1
    PRIORITY_USER_INSTRUCTION = 2
    PRIORITY_STORY_STATE = 3
    PRIORITY_CURRENT_CHAPTER = 4
    PRIORITY_STORY_MEMORY = 5
    PRIORITY_RECENT_CHAPTER_SUMMARY = 6
    PRIORITY_CHARACTER = 7
    PRIORITY_LOCATION = 8
    PRIORITY_PLOT_THREAD = 9
    PRIORITY_CONTINUITY_NOTE = 10
    PRIORITY_VECTOR_RECALL = 11

    def __init__(
        self,
        *,
        chapter_service: ChapterService,
        initialization_repository: InitializationRepository,
        story_memory_repository: StoryMemoryRepository,
        story_state_repository: StoryStateRepository,
        context_pack_repository: ContextPackRepository,
    ) -> None:
        self._chapter_service = chapter_service
        self._initialization_repository = initialization_repository
        self._story_memory_repository = story_memory_repository
        self._story_state_repository = story_state_repository
        self._context_pack_repository = context_pack_repository

    def build(self, request: ContextPackBuildRequest) -> ContextPackSnapshot:
        now = self._now()
        pack_id = f"cp_{uuid.uuid4().hex[:12]}"

        initialization = self._initialization_repository.get_latest_by_work(request.work_id)

        # ---------- blocked checks ----------
        if not request.is_quick_trial:
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

        if not request.is_quick_trial:
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
        if request.is_quick_trial:
            stale = bool(initialization and (initialization.stale or initialization.status.value == "stale"))
            if stale:
                stale_reason_parts.append("stale_initialization")
        else:
            if initialization and (initialization.stale or initialization.status.value == "stale"):
                stale = True
                stale_reason_parts.append(initialization.stale_reason or "initialization_stale")
                if story_memory and story_memory.stale_status == "stale":
                    stale_reason_parts.append("story_memory_stale")
                if story_state and story_state.stale_status == "stale":
                    stale_reason_parts.append("story_state_stale")

        if stale and not request.is_quick_trial:
            return ContextPackSnapshot(
                context_pack_id=pack_id,
                work_id=request.work_id,
                chapter_id=request.chapter_id,
                source_initialization_id=initialization.initialization_id if initialization else "",
                source_story_memory_snapshot_id=story_memory.snapshot_id if story_memory else "",
                source_story_state_id=story_state.story_state_id if story_state else "",
                status=ContextPackStatus.BLOCKED,
                blocked_reason="state_or_memory_stale",
                warnings=stale_reason_parts,
                stale=True,
                stale_reason="; ".join(stale_reason_parts),
                token_budget=request.max_context_tokens,
                created_at=now,
            )

        # ---------- assemble items ----------
        items: list[ContextItem] = []
        degraded_reason_parts: list[str] = []
        source_chapter_versions: dict[str, int] = {}

        if initialization:
            source_chapter_versions = dict(initialization.source_chapter_versions)

        # system_policy
        items.append(ContextItem(
            item_id=f"{pack_id}_policy",
            source_type="system_policy",
            priority=self.PRIORITY_SYSTEM_POLICY,
            content_text="你是一位专业的小说写作助手。请根据提供的上下文和用户指令，生成高质量的小说正文续写内容。",
            token_estimate=self._estimate_tokens("你是一位专业的小说写作助手。请根据提供的上下文和用户指令，生成高质量的小说正文续写内容。"),
            required=True,
        ))

        # user_instruction
        if request.user_instruction:
            items.append(ContextItem(
                item_id=f"{pack_id}_instruction",
                source_type="user_instruction",
                priority=self.PRIORITY_USER_INSTRUCTION,
                content_text=request.user_instruction,
                token_estimate=self._estimate_tokens(request.user_instruction),
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

        # current_chapter
        chapters = self._chapter_service.list_chapters(request.work_id)
        current_chapter = next((ch for ch in chapters if getattr(ch, "id", None) and getattr(ch.id, "value", "") == request.chapter_id), None)
        if current_chapter:
            content = getattr(current_chapter, "content", "")
            title = str(getattr(current_chapter, "title", "") or "")
            chapter_text = f"章节标题: {title}\n正文片段: {self._truncate_text(content, 600)}"
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
                if request.is_quick_trial:
                    degraded_reason_parts.append("no_confirmed_chapters")
                else:
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

        # ---------- VectorRecall stub ----------
        items.append(ContextItem(
            item_id=f"{pack_id}_recall_stub",
            source_type="vector_recall",
            priority=self.PRIORITY_VECTOR_RECALL,
            content_text="",
            token_estimate=0,
            required=False,
            included=False,
            trim_reason="vector_recall_unavailable",
        ))
        degraded_reason_parts.append("vector_recall_unavailable")

        # ---------- Priority sort ----------
        items.sort(key=lambda item: item.priority)

        # ---------- Token budget ----------
        total_tokens = 0
        included: list[ContextItem] = []
        trimmed: list[ContextItem] = []
        required_tokens = sum(item.token_estimate for item in items if item.required)

        if required_tokens > request.max_context_tokens:
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
                vector_recall_status="skipped",
                context_items=[item.model_copy(update={"included": False, "trim_reason": "required_over_budget"}) for item in items],
                token_budget=request.max_context_tokens,
                estimated_token_count=required_tokens,
                trimmed_items=items,
                stale=stale,
                stale_reason="; ".join(stale_reason_parts) if stale else "",
                source_chapter_versions=source_chapter_versions,
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

        if request.is_quick_trial:
            degraded_reason_parts.append("quick_trial_context")
            status = ContextPackStatus.DEGRADED

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
            vector_recall_status="skipped",
            context_items=included,
            token_budget=request.max_context_tokens,
            estimated_token_count=total_tokens,
            trimmed_items=trimmed,
            stale=stale,
            stale_reason="; ".join(stale_reason_parts) if stale else "",
            source_chapter_versions=source_chapter_versions,
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
        saved = self._context_pack_repository.save(snapshot)
        return {
            "context_pack_id": saved.context_pack_id,
            "status": saved.status.value,
            "blocked_reason": saved.blocked_reason,
            "degraded_reason": saved.degraded_reason,
            "warnings": saved.warnings,
            "estimated_token_count": saved.estimated_token_count,
            "stale": saved.stale,
            "stale_reason": saved.stale_reason,
        }

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(re.sub(r"\s+", "", text)) // 2)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        return cleaned[:max_chars] + ("..." if len(cleaned) > max_chars else "")

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
