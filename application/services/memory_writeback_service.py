from __future__ import annotations

import uuid
from datetime import datetime

from application.services.logging_service import build_log_context, get_logger
from domain.entities.chapter_analysis_memory import ChapterAnalysisMemory
from domain.entities.chapter import Chapter, ChapterStatus
from domain.entities.chapter_continuation_memory import ChapterContinuationMemory
from domain.entities.chapter_task import ChapterTask
from domain.entities.detemplated_draft import DetemplatedDraft
from domain.entities.draft_integrity_check import DraftIntegrityCheck
from domain.entities.structural_draft import StructuralDraft
from domain.types import ChapterId


class MemoryWritebackService:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = get_logger(__name__)

    async def write_batch(self, project, memory: dict, generated_items: list[dict], auto_commit: bool) -> dict:
        saved_chapter_ids: list[str] = []
        chapter_saved = False
        latest_chapter_id = ""
        latest_chapter_number = 0
        latest_plan_id = ""
        latest_branch_id = ""
        if auto_commit:
            for item in generated_items:
                allocation = item["allocation"]
                structural_draft = item["structural_draft"]
                detemplated_draft = item["detemplated_draft"]
                integrity_check = item["integrity_check"]
                chapter_task = item["chapter_task"]
                item["global_constraints"] = memory.get("global_constraints") or {}
                latest_plan_id = str(item["chapter_plan"].get("id") or "")
                latest_branch_id = str(item["chapter_plan"].get("branch_id") or "")
                now = datetime.now()
                accepted_content = str(structural_draft.get("content") or "") if detemplated_draft.get("display_fallback_to_structural") else str(detemplated_draft.get("content") or "")
                chapter = Chapter(
                    id=ChapterId(str(uuid.uuid4())),
                    novel_id=project.novel_id,
                    number=int(allocation["chapter_number"]),
                    title=str(allocation["final_title"]),
                    content=accepted_content,
                    status=ChapterStatus.DRAFT,
                    created_at=now,
                    updated_at=now,
                )
                self.workflow_service.chapter_repo.save(chapter)
                saved_chapter_ids.append(chapter.id.value)
                latest_chapter_id = chapter.id.value
                latest_chapter_number = chapter.number
                chapter_saved = True
                structural_draft["chapter_id"] = chapter.id.value
                structural_draft["chapter_number"] = chapter.number
                structural_draft["title"] = chapter.title
                detemplated_draft["chapter_id"] = chapter.id.value
                detemplated_draft["chapter_number"] = chapter.number
                detemplated_draft["title"] = chapter.title
                integrity_check["chapter_id"] = chapter.id.value
                self.workflow_service.structural_draft_repo.save(
                    StructuralDraft(
                        id=str(structural_draft.get("id") or ""),
                        chapter_id=chapter.id.value,
                        project_id=str(structural_draft.get("project_id") or ""),
                        chapter_number=chapter.number,
                        title=chapter.title,
                        content=str(structural_draft.get("content") or ""),
                        source_task_id=str(structural_draft.get("source_task_id") or ""),
                        model_name=str(structural_draft.get("model_name") or ""),
                        used_fallback=bool(structural_draft.get("used_fallback")),
                        generation_stage=str(structural_draft.get("generation_stage") or ""),
                        version=int(structural_draft.get("version") or 1),
                    )
                )
                self.workflow_service.detemplated_draft_repo.save(
                    DetemplatedDraft(
                        id=str(detemplated_draft.get("id") or ""),
                        chapter_id=chapter.id.value,
                        project_id=str(detemplated_draft.get("project_id") or ""),
                        chapter_number=chapter.number,
                        title=chapter.title,
                        content=str(detemplated_draft.get("content") or ""),
                        based_on_structural_draft_id=str(detemplated_draft.get("based_on_structural_draft_id") or ""),
                        style_requirements_snapshot=detemplated_draft.get("style_requirements_snapshot") or {},
                        model_name=str(detemplated_draft.get("model_name") or ""),
                        used_fallback=bool(detemplated_draft.get("used_fallback")),
                        integrity_failed=bool(detemplated_draft.get("integrity_failed")),
                        display_fallback_to_structural=bool(detemplated_draft.get("display_fallback_to_structural")),
                        generation_stage=str(detemplated_draft.get("generation_stage") or ""),
                        version=int(detemplated_draft.get("version") or 1),
                    )
                )
                self.workflow_service.draft_integrity_check_repo.save(
                    DraftIntegrityCheck(
                        id=str(integrity_check.get("id") or ""),
                        chapter_id=chapter.id.value,
                        project_id=str(detemplated_draft.get("project_id") or ""),
                        structural_draft_id=str(structural_draft.get("id") or ""),
                        detemplated_draft_id=str(detemplated_draft.get("id") or ""),
                        event_integrity_ok=bool(integrity_check.get("event_integrity_ok")),
                        motivation_integrity_ok=bool(integrity_check.get("motivation_integrity_ok")),
                        foreshadowing_integrity_ok=bool(integrity_check.get("foreshadowing_integrity_ok")),
                        hook_integrity_ok=bool(integrity_check.get("hook_integrity_ok")),
                        continuity_ok=bool(integrity_check.get("continuity_ok")),
                        risk_notes=[str(x) for x in (integrity_check.get("risk_notes") or [])],
                        arc_consistency_ok=bool(integrity_check.get("arc_consistency_ok", True)),
                        title_alignment_ok=bool(integrity_check.get("title_alignment_ok", True)),
                        progression_integrity_ok=bool(integrity_check.get("progression_integrity_ok", True)),
                        issue_list=[item for item in (integrity_check.get("issue_list") or []) if isinstance(item, dict)],
                        revision_suggestion=str(integrity_check.get("revision_suggestion") or ""),
                        revision_attempted=bool(integrity_check.get("revision_attempted")),
                        revision_succeeded=bool(integrity_check.get("revision_succeeded")),
                    )
                )
                self.workflow_service.chapter_task_repo.save(
                    ChapterTask(
                        id=str(chapter_task.get("id") or ""),
                        chapter_id=chapter.id.value,
                        project_id=str(chapter_task.get("project_id") or ""),
                        branch_id=str(chapter_task.get("branch_id") or ""),
                        chapter_number=chapter.number,
                        chapter_function=str(chapter_task.get("chapter_function") or ""),
                        goals=[str(x) for x in (chapter_task.get("goals") or [])],
                        must_continue_points=[str(x) for x in (chapter_task.get("must_continue_points") or [])],
                        forbidden_jumps=[str(x) for x in (chapter_task.get("forbidden_jumps") or [])],
                        required_foreshadowing_action=str(chapter_task.get("required_foreshadowing_action") or ""),
                        required_hook_strength=str(chapter_task.get("required_hook_strength") or ""),
                        pace_target=str(chapter_task.get("pace_target") or ""),
                        opening_continuation=str(chapter_task.get("opening_continuation") or ""),
                        chapter_payoff=str(chapter_task.get("chapter_payoff") or ""),
                        style_bias=str(chapter_task.get("style_bias") or ""),
                        status="done",
                        version=int(chapter_task.get("version") or 1),
                    )
                )
                analysis_memory = self._build_analysis_memory(project.id.value, chapter.id.value, chapter.number, chapter.title, item)
                continuation_memory = await self._build_continuation_memory(project.id.value, chapter.id.value, chapter.number, chapter.title, item, accepted_content)
                self.workflow_service.chapter_analysis_memory_repo.save(analysis_memory)
                self.workflow_service.chapter_continuation_memory_repo.save(continuation_memory)
                memory["chapter_analysis_memories"] = [*(memory.get("chapter_analysis_memories") or []), self._analysis_to_dict(analysis_memory)][-50:]
                memory["chapter_continuation_memories"] = [*(memory.get("chapter_continuation_memories") or []), self._continuation_to_dict(continuation_memory)][-50:]
                memory["chapter_summaries"] = [*(memory.get("chapter_summaries") or []), accepted_content[:120]][-300:]
                current_state = memory.get("current_state") or {}
                current_state.update(
                    {
                        "latest_chapter_number": chapter.number,
                        "latest_summary": accepted_content[:120],
                        "next_writing_focus": str(item["chapter_plan"].get("ending_hook") or ""),
                    }
                )
                memory["current_state"] = current_state
        project_id = str(project.id.value)
        memory_refreshed = False
        if auto_commit:
            memory_payload = self.workflow_service._to_project_memory_payload(project_id, memory)
            self.workflow_service.v2_repo.save_project_memory(memory_payload)
            self.workflow_service._sync_primary_repositories(project_id, memory_payload)
            view_payload = self.workflow_service._to_memory_view_payload(project_id, memory_payload)
            self.workflow_service.v2_repo.save_memory_view(view_payload)
            memory_refreshed = True
        else:
            view_payload = self.workflow_service.get_memory_view(project_id)
        self.logger.info(
            "记忆回写完成",
            extra=build_log_context(
                event="memory_writeback_finished",
                project_id=project_id,
                chapter_id=latest_chapter_id,
                chapter_number=latest_chapter_number,
                plan_id=latest_plan_id,
                branch_id=latest_branch_id,
                chapter_saved=chapter_saved,
                memory_refreshed=memory_refreshed,
                used_structural_fallback=any(bool((item.get("detemplated_draft") or {}).get("used_fallback") or (item.get("detemplated_draft") or {}).get("display_fallback_to_structural")) for item in generated_items),
            ),
        )
        return {
            "chapter_saved": chapter_saved,
            "memory_refreshed": memory_refreshed,
            "updated_memory_view": view_payload,
            "saved_chapter_ids": saved_chapter_ids,
        }

    def _build_analysis_memory(self, project_id: str, chapter_id: str, chapter_number: int, chapter_title: str, item: dict) -> ChapterAnalysisMemory:
        chapter_plan = item["chapter_plan"]
        chapter_task = item["chapter_task"]
        detemplated_draft = item["detemplated_draft"]
        accepted_content = str(item["structural_draft"].get("content") or "") if detemplated_draft.get("display_fallback_to_structural") else str(detemplated_draft.get("content") or "")
        return ChapterAnalysisMemory(
            id=f"cam_{uuid.uuid4().hex[:10]}",
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            summary=accepted_content[:180],
            events=[str(chapter_plan.get("goal") or ""), str(chapter_plan.get("progression") or "")],
            plot_role=str(chapter_task.get("chapter_function") or ""),
            conflict=str(chapter_plan.get("conflict") or ""),
            foreshadowing=[str(x) for x in (chapter_task.get("must_continue_points") or [])[:4]],
            hook=str(chapter_plan.get("ending_hook") or chapter_task.get("chapter_payoff") or ""),
            problems=[str(x) for x in ((item["integrity_check"].get("risk_notes") or []))],
            version=1,
        )

    async def _build_continuation_memory(self, project_id: str, chapter_id: str, chapter_number: int, chapter_title: str, item: dict, accepted_content: str) -> ChapterContinuationMemory:
        chapter_plan = item["chapter_plan"]
        chapter_task = item["chapter_task"]
        extracted = await self.workflow_service.prompt_ai_service.extract_continuation_memory(
            chapter_title=chapter_title,
            chapter_content=accepted_content,
            relevant_characters=[],
            global_constraints=item.get("global_constraints") or {},
        )
        return ChapterContinuationMemory(
            id=f"ccm_{uuid.uuid4().hex[:10]}",
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            scene_summary=str(extracted.get("scene_summary") or accepted_content[:180]),
            scene_state=extracted.get("scene_state") if isinstance(extracted.get("scene_state"), dict) else {"ending_scene": accepted_content[-120:]},
            protagonist_state=extracted.get("protagonist_state") if isinstance(extracted.get("protagonist_state"), dict) else {"current_goal": str(chapter_plan.get("goal") or "")},
            active_characters=[item for item in (extracted.get("active_characters") or []) if isinstance(item, dict)],
            active_conflicts=[str(x) for x in (extracted.get("active_conflicts") or [str(chapter_plan.get("conflict") or "")]) if str(x).strip()],
            immediate_threads=[str(x) for x in (extracted.get("immediate_threads") or [str(chapter_plan.get("progression") or "")]) if str(x).strip()],
            long_term_threads=[str(x) for x in (extracted.get("long_term_threads") or list(chapter_task.get("must_continue_points") or [])) if str(x).strip()],
            recent_reveals=[str(x) for x in (extracted.get("recent_reveals") or [str(chapter_plan.get("goal") or "")]) if str(x).strip()],
            must_continue_points=[str(x) for x in (extracted.get("must_continue_points") or list(chapter_task.get("must_continue_points") or [])) if str(x).strip()],
            forbidden_jumps=[str(x) for x in (extracted.get("forbidden_jumps") or list(chapter_task.get("forbidden_jumps") or [])) if str(x).strip()],
            tone_and_pacing=extracted.get("tone_and_pacing") if isinstance(extracted.get("tone_and_pacing"), dict) else {"pace": str(chapter_task.get("pace_target") or "")},
            last_hook=str(extracted.get("last_hook") or chapter_plan.get("ending_hook") or chapter_task.get("chapter_payoff") or ""),
            version=1,
        )

    def _analysis_to_dict(self, item: ChapterAnalysisMemory) -> dict:
        return {
            "id": item.id,
            "chapter_id": item.chapter_id,
            "chapter_number": item.chapter_number,
            "chapter_title": item.chapter_title,
            "summary": item.summary,
            "events": list(item.events or []),
            "plot_role": item.plot_role,
            "conflict": item.conflict,
            "foreshadowing": list(item.foreshadowing or []),
            "hook": item.hook,
            "problems": list(item.problems or []),
            "version": item.version,
        }

    def _continuation_to_dict(self, item: ChapterContinuationMemory) -> dict:
        return {
            "id": item.id,
            "chapter_id": item.chapter_id,
            "chapter_number": item.chapter_number,
            "chapter_title": item.chapter_title,
            "scene_summary": item.scene_summary,
            "scene_state": item.scene_state,
            "protagonist_state": item.protagonist_state,
            "active_characters": list(item.active_characters or []),
            "active_conflicts": list(item.active_conflicts or []),
            "immediate_threads": list(item.immediate_threads or []),
            "long_term_threads": list(item.long_term_threads or []),
            "recent_reveals": list(item.recent_reveals or []),
            "must_continue_points": list(item.must_continue_points or []),
            "forbidden_jumps": list(item.forbidden_jumps or []),
            "tone_and_pacing": item.tone_and_pacing,
            "last_hook": item.last_hook,
            "version": item.version,
        }
