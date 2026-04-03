from __future__ import annotations

from typing import Any, Dict, List, Optional

from application.services.logging_service import build_log_context, get_logger
from domain.types import ProjectId


class WritingServiceV2:
    def __init__(self, workflow_service, validation_service):
        self.workflow_service = workflow_service
        self.validation_service = validation_service
        self.logger = get_logger(__name__)

    async def execute_write_preview(
        self,
        project_id: str,
        plan_id: str,
        target_word_count: int = 0,
        style_requirements: Optional[Dict[str, Any]] = None,
        planning_mode: str = "light_planning",
        target_arc_id: str = "",
    ) -> Dict[str, Any]:
        workflow = self.workflow_service
        project = workflow.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        plans = workflow.v2_repo.find_plans(project_id, [plan_id])
        if not plans:
            raise ValueError("未找到可执行的章节计划")
        plan = dict(plans[0])
        self.logger.info(
            "续写预览开始",
            extra=build_log_context(
                event="write_preview_started",
                project_id=project_id,
                chapter_id="",
                chapter_number=int(plan.get("chapter_number") or 0),
                plan_id=plan_id,
                branch_id=str(plan.get("branch_id") or ""),
                used_structural_fallback=False,
            ),
        )
        if target_word_count > 0:
            plan["target_words"] = int(target_word_count)
        outline_context = workflow._get_outline_context(project.novel_id)
        memory = workflow._load_structured_memory(project_id, project.novel_id, outline_context)
        if style_requirements:
            memory["style_requirements"] = style_requirements
        chapters = workflow.chapter_repo.find_by_novel(project.novel_id)
        recent_chapter_id = str(chapters[-1].id.value) if chapters else ""
        context = workflow.continuation_context_builder.build(
            project_id,
            chapter_id=recent_chapter_id,
            chapter_number=int(plan.get("chapter_number") or 0),
            plan_id=plan_id,
            branch_id=str(plan.get("branch_id") or ""),
        )
        chapter_task = await workflow.chapter_task_generator.generate(context, plan)
        write_result = await workflow.continuation_writer.write(project, plan, chapter_task, context, memory, chapters)
        structural_draft = write_result["structural_draft"]
        detemplated_draft = await workflow.detemplating_rewriter.rewrite(
            structural_draft,
            chapter_task,
            memory.get("global_constraints") or {},
            memory.get("style_requirements") or {},
        )
        validated = await self.validation_service.validate_and_revise(
            structural_draft=structural_draft,
            detemplated_draft=detemplated_draft,
            chapter_task=chapter_task,
            global_constraints=memory.get("global_constraints") or {},
            style_requirements=memory.get("style_requirements") or {},
        )
        detemplated_draft = validated["detemplated_draft"]
        integrity_check = validated["integrity_check"]
        if not workflow._is_integrity_ok(integrity_check):
            detemplated_draft["integrity_failed"] = True
            detemplated_draft["display_fallback_to_structural"] = True
        arc_stage_before = str(chapter_task.get("arc_stage_before") or plan.get("arc_stage_before") or "")
        arc_stage_after_expected = str(
            chapter_task.get("arc_stage_after_expected")
            or plan.get("arc_stage_after_expected")
            or workflow._predict_next_arc_stage(arc_stage_before)
        )
        result = {
            "project_id": project_id,
            "chapter_task": chapter_task,
            "structural_draft": structural_draft,
            "detemplated_draft": detemplated_draft,
            "integrity_check": integrity_check,
            "revision_attempts": validated.get("revision_attempts") or [],
            "used_structural_fallback": bool(detemplated_draft.get("used_fallback") or detemplated_draft.get("display_fallback_to_structural")),
            "target_arc": workflow._select_preview_target_arc(project_id, plan, target_arc_id),
            "planning_mode": planning_mode or str(plan.get("planning_mode") or "light_planning"),
            "planning_reason": str(plan.get("planning_reason") or ""),
            "arc_stage_before": arc_stage_before,
            "arc_stage_after_expected": arc_stage_after_expected,
        }
        self.logger.info(
            "续写预览完成",
            extra=build_log_context(
                event="write_preview_finished",
                project_id=project_id,
                chapter_id=str(chapter_task.get("chapter_id") or ""),
                chapter_number=int(structural_draft.get("chapter_number") or 0),
                plan_id=plan_id,
                branch_id=str(plan.get("branch_id") or ""),
                used_structural_fallback=bool(result.get("used_structural_fallback")),
            ),
        )
        return result

    async def execute_write_commit(
        self,
        project_id: str,
        plan_ids: List[str],
        chapter_count: int,
        auto_commit: bool = True,
        planning_mode: str = "light_planning",
        target_arc_id: str = "",
    ) -> Dict[str, Any]:
        workflow = self.workflow_service
        project = workflow.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "续写开始",
            extra=build_log_context(
                event="write_started",
                project_id=project_id,
                chapter_id="",
                chapter_number=0,
                plan_id=",".join(plan_ids),
                branch_id="",
                used_structural_fallback=False,
                plan_ids=plan_ids,
            ),
        )
        plans = workflow.v2_repo.find_plans(project_id, plan_ids)
        if not plans:
            raise ValueError("未找到可执行的章节计划")
        plans = plans[: max(1, int(chapter_count or len(plan_ids) or 1))]
        outline_context = workflow._get_outline_context(project.novel_id)
        memory = workflow._load_structured_memory(project_id, project.novel_id, outline_context)
        chapters = list(workflow.chapter_repo.find_by_novel(project.novel_id))
        generated_items: List[Dict[str, Any]] = []
        for plan in plans:
            recent_chapter_id = str(chapters[-1].id.value) if chapters else ""
            context = workflow.continuation_context_builder.build(
                project_id,
                chapter_id=recent_chapter_id,
                chapter_number=int(plan.get("chapter_number") or 0),
                plan_id=str(plan.get("id") or ""),
                branch_id=str(plan.get("branch_id") or ""),
            )
            chapter_task = await workflow.chapter_task_generator.generate(context, plan)
            write_result = await workflow.continuation_writer.write(project, plan, chapter_task, context, memory, chapters)
            structural_draft = write_result["structural_draft"]
            detemplated_draft = await workflow.detemplating_rewriter.rewrite(
                structural_draft,
                chapter_task,
                memory.get("global_constraints") or {},
                memory.get("style_requirements") or {},
            )
            validated = await self.validation_service.validate_and_revise(
                structural_draft=structural_draft,
                detemplated_draft=detemplated_draft,
                chapter_task=chapter_task,
                global_constraints=memory.get("global_constraints") or {},
                style_requirements=memory.get("style_requirements") or {},
            )
            detemplated_draft = validated["detemplated_draft"]
            integrity_check = validated["integrity_check"]
            if not workflow._is_integrity_ok(integrity_check):
                detemplated_draft["integrity_failed"] = True
                detemplated_draft["display_fallback_to_structural"] = True
            generated_items.append(
                {
                    "chapter_plan": plan,
                    "chapter_task": chapter_task,
                    "structural_draft": structural_draft,
                    "detemplated_draft": detemplated_draft,
                    "integrity_check": integrity_check,
                    "revision_attempts": validated.get("revision_attempts") or [],
                }
            )
            display_content = str(structural_draft.get("content") or "") if detemplated_draft.get("display_fallback_to_structural") else str(detemplated_draft.get("content") or "")
            chapters.append(
                type(
                    "GeneratedChapter",
                    (),
                    {
                        "id": type("GeneratedId", (), {"value": str(chapter_task.get("chapter_id") or "")})(),
                        "number": int(plan.get("chapter_number") or 0),
                        "title": str(detemplated_draft.get("title") or structural_draft.get("title") or ""),
                        "content": display_content,
                    },
                )()
            )
            continuation_memory = workflow._build_generated_continuation_memory(
                chapter_task=chapter_task,
                chapter_plan=plan,
                structural_draft=structural_draft,
                detemplated_draft=detemplated_draft,
            )
            memory["chapter_continuation_memories"] = [*(memory.get("chapter_continuation_memories") or []), continuation_memory][-20:]
        allocations = workflow.chapter_allocation_service.allocate(
            project_id,
            len(generated_items),
            [str(item["chapter_plan"].get("title") or "") for item in generated_items],
            [str(item["detemplated_draft"].get("title") or "") for item in generated_items],
            [str(item["chapter_task"].get("chapter_payoff") or item["chapter_task"].get("chapter_function") or "") for item in generated_items],
            branch_id=str(generated_items[0]["chapter_plan"].get("branch_id") or "") if generated_items else "",
            plan_ids=[str(item["chapter_plan"].get("id") or "") for item in generated_items],
        )
        for index, allocation in enumerate(allocations):
            generated_items[index]["allocation"] = allocation
        writeback = await workflow.memory_writeback_service.write_batch(project, memory, generated_items, auto_commit=auto_commit)
        generated_chapters = []
        for item in generated_items:
            allocation = item["allocation"]
            detemplated_draft = item["detemplated_draft"]
            structural_draft = item["structural_draft"]
            integrity_check = item["integrity_check"]
            generated_chapters.append(
                {
                    "chapter_id": str(detemplated_draft.get("chapter_id") or ""),
                    "chapter_number": int(allocation["chapter_number"]),
                    "number": int(allocation["chapter_number"]),
                    "title": str(allocation["final_title"]),
                    "content": str(detemplated_draft.get("content") or ""),
                    "structural_draft_id": str(structural_draft.get("id") or ""),
                    "detemplated_draft_id": str(detemplated_draft.get("id") or ""),
                    "integrity_check_id": str(integrity_check.get("id") or ""),
                    "used_structural_fallback": bool(detemplated_draft.get("used_fallback") or detemplated_draft.get("display_fallback_to_structural")),
                    "saved": str(detemplated_draft.get("chapter_id") or "") in (writeback.get("saved_chapter_ids") or []),
                    "structural_draft": dict(structural_draft),
                    "detemplated_draft": dict(detemplated_draft),
                    "integrity_check": dict(integrity_check),
                    "revision_attempts": list(item.get("revision_attempts") or []),
                }
            )
        if auto_commit and generated_chapters:
            for index, generated in enumerate(generated_chapters):
                if not generated.get("saved"):
                    continue
                source = generated_items[index] if index < len(generated_items) else {}
                chapter_task = source.get("chapter_task") or {}
                chapter_plan = source.get("chapter_plan") or {}
                selected_arc_id = str(
                    chapter_task.get("target_arc_id")
                    or chapter_plan.get("target_arc_id")
                    or target_arc_id
                    or ""
                ).strip()
                workflow.arc_writeback_service.writeback_chapter_arc(
                    project_id=project_id,
                    chapter_id=str(generated.get("chapter_id") or ""),
                    chapter_number=int(generated.get("chapter_number") or 0),
                    target_arc_id=selected_arc_id,
                    progress_summary=str(generated.get("title") or ""),
                    binding_role="primary",
                    push_type="advance",
                )
            if workflow.plot_arc_service:
                workflow.plot_arc_service.enforce_active_arc_limit(project_id, limit=5)
        latest_generated = generated_chapters[-1] if generated_chapters else {}
        latest_structural_draft = generated_items[-1]["structural_draft"] if generated_items else {}
        latest_detemplated_draft = generated_items[-1]["detemplated_draft"] if generated_items else {}
        latest_integrity_check = generated_items[-1]["integrity_check"] if generated_items else {}
        result = workflow.write_batch_result_builder.build(
            project_id=project_id,
            generated_chapters=generated_chapters,
            latest_chapter=latest_generated,
            latest_structural_draft=latest_structural_draft,
            latest_detemplated_draft=latest_detemplated_draft,
            latest_draft_integrity_check=latest_integrity_check,
            memory_view=writeback["updated_memory_view"],
            used_structural_fallback=any(bool(item["detemplated_draft"].get("used_fallback") or item["detemplated_draft"].get("display_fallback_to_structural")) for item in generated_items),
            chapter_saved=bool(writeback["chapter_saved"]),
            memory_refreshed=bool(writeback["memory_refreshed"]),
            saved_chapter_ids=list(writeback["saved_chapter_ids"]),
        )
        first_plan = generated_items[0]["chapter_plan"] if generated_items else {}
        result["target_arc"] = workflow._select_preview_target_arc(project_id, first_plan, target_arc_id)
        result["planning_mode"] = planning_mode or str(first_plan.get("planning_mode") or "light_planning")
        result["planning_reason"] = str(first_plan.get("planning_reason") or "")
        result["arc_stage_before"] = str(first_plan.get("arc_stage_before") or "")
        result["arc_stage_after_expected"] = str(first_plan.get("arc_stage_after_expected") or workflow._predict_next_arc_stage(result["arc_stage_before"]))
        target_arc_actual = result.get("target_arc") or {}
        result["arc_stage_after_actual"] = str(target_arc_actual.get("current_stage") or result["arc_stage_before"])
        result["arc_stage_advanced"] = bool(
            result["arc_stage_after_actual"]
            and result["arc_stage_before"]
            and result["arc_stage_after_actual"] != result["arc_stage_before"]
        )
        self.logger.info(
            "续写完成",
            extra=build_log_context(
                event="write_finished",
                project_id=project_id,
                chapter_id=str((latest_generated or {}).get("chapter_id") or ""),
                chapter_number=int((latest_generated or {}).get("chapter_number") or 0),
                plan_id=",".join(plan_ids),
                branch_id=str(generated_items[0]["chapter_plan"].get("branch_id") or "") if generated_items else "",
                used_structural_fallback=bool(result.get("used_structural_fallback")),
                generated_count=len(generated_chapters),
            ),
        )
        return result

    async def execute_writing(self, project_id: str, plan_ids: List[str], auto_commit: bool) -> Dict[str, Any]:
        batch_result = await self.execute_write_commit(project_id, plan_ids, len(plan_ids), auto_commit=auto_commit)
        latest_chapter = batch_result.get("latest_chapter") or {}
        return {
            "project_id": project_id,
            "generated_chapter_ids": list(batch_result.get("saved_chapter_ids") or []),
            "latest_content": str(latest_chapter.get("content") or ""),
            "latest_title": str(latest_chapter.get("title") or ""),
            "latest_chapter_number": int(latest_chapter.get("chapter_number") or 0),
            "latest_chapter": latest_chapter,
            "latest_structural_draft": batch_result.get("latest_structural_draft") or {},
            "latest_detemplated_draft": batch_result.get("latest_detemplated_draft") or {},
            "latest_draft_integrity_check": batch_result.get("latest_draft_integrity_check") or {},
            "used_structural_fallback": bool(batch_result.get("used_structural_fallback")),
            "memory_view": batch_result.get("memory_view") or {},
        }
