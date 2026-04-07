from __future__ import annotations

import uuid
from typing import Any, Dict, List

from application.services.logging_service import build_log_context
from domain.constants.story_constants import (
    DEFAULT_FORESHADOWING_ACTION,
    DEFAULT_GENERATE_CHAPTER_COUNT,
    DEFAULT_HOOK_STRENGTH,
    DEFAULT_PACE_TARGET,
    DEFAULT_TARGET_WORDS_PER_CHAPTER,
)
from domain.constants.story_enums import WRITING_STATUS_READY
from domain.entities.chapter_task import ChapterTask
from domain.types import ProjectId


class ChapterPlanningService:
    def __init__(self, workflow_service):
        self.workflow_service = workflow_service
        self.logger = workflow_service.logger

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
        workflow = self.workflow_service
        project = workflow.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "章节计划开始",
            extra=build_log_context(
                event="chapter_plan_started",
                project_id=project_id,
                branch_id=branch_id,
                chapter_count=chapter_count,
            ),
        )
        chapters = workflow.chapter_repo.find_by_novel(project.novel_id)
        start_no = max([int(ch.number) for ch in chapters], default=0) + 1
        branches = workflow.v2_repo.list_branches(project_id)
        branch = next((b for b in branches if b["id"] == branch_id), None)
        if not branch:
            raise ValueError("分支不存在")

        outline_context = workflow._get_outline_context(project.novel_id)
        outline_summary = "；".join(
            [
                str(outline_context.get("premise") or ""),
                str(outline_context.get("story_background") or ""),
                str(outline_context.get("world_setting") or ""),
            ]
        ).strip("；")
        memory = workflow._load_structured_memory(project_id, project.novel_id, outline_context)
        plans: List[Dict[str, Any]] = []

        continuation_memories = memory.get("chapter_continuation_memories") if isinstance(memory.get("chapter_continuation_memories"), list) else []
        latest_continuation = continuation_memories[-1] if continuation_memories else {}
        must_continue_points = latest_continuation.get("must_continue_points") if isinstance(latest_continuation, dict) else []
        forbidden_jumps = latest_continuation.get("forbidden_jumps") if isinstance(latest_continuation, dict) else []
        opening_continuation = str((latest_continuation or {}).get("last_hook") or memory.get("current_state", {}).get("latest_summary") or "")
        tone_tags = [str(x).strip() for x in ((memory.get("style_profile") or {}).get("tone_tags") or []) if str(x).strip()]
        safe_chapter_count = max(1, int(chapter_count or DEFAULT_GENERATE_CHAPTER_COUNT))
        safe_target_words = max(500, int(target_words_per_chapter or DEFAULT_TARGET_WORDS_PER_CHAPTER))
        effective_planning_mode = "deep_planning" if allow_deep_planning and planning_mode == "deep_planning" else "light_planning"
        planning_reason = "default_light_planning"
        selected_arc = None
        secondary_arc_ids: List[str] = []

        if workflow.arc_planning_service:
            all_active_arcs = workflow.plot_arc_service.list_active_arcs(project_id) if workflow.plot_arc_service else []
            preferred_arc = next((arc for arc in all_active_arcs if arc.arc_id == target_arc_id), None) if target_arc_id else None
            recent_tasks = workflow.chapter_task_repo.find_by_project_id(project_id) or []
            chapters_since_target_arc_progress = 0
            if target_arc_id:
                for item in reversed(recent_tasks):
                    if str(getattr(item, "target_arc_id", "") or "") == str(target_arc_id):
                        break
                    chapters_since_target_arc_progress += 1
            continuity_flags = memory.get("continuity_flags") if isinstance(memory.get("continuity_flags"), list) else []
            latest_flags = continuity_flags[-5:]
            consistency_warning = any(
                str((flag or {}).get("severity") or "").lower() in {"high", "critical"}
                for flag in latest_flags
                if isinstance(flag, dict)
            )
            arc_pick = workflow.arc_planning_service.select_arcs(
                project_id=project_id,
                planning_mode=planning_mode,
                preferred_arc_id=target_arc_id,
                allow_deep_planning=allow_deep_planning,
                trigger_context={
                    "target_arc_stage": getattr(preferred_arc, "current_stage", ""),
                    "chapters_since_target_arc_progress": chapters_since_target_arc_progress,
                    "consistency_warning": consistency_warning,
                },
            )
            selected_arc = arc_pick.get("target_arc")
            secondary_arc_ids = [arc.arc_id for arc in (arc_pick.get("secondary_arcs") or []) if getattr(arc, "arc_id", "")]
            effective_planning_mode = str(arc_pick.get("planning_mode") or effective_planning_mode)
            planning_reason = str(arc_pick.get("planning_reason") or planning_reason)

        phase_templates = [
            {"function": "advance_investigation", "goal_focus": "锁定新线索", "hook": "新证据出现"},
            {"function": "reveal_abnormal", "goal_focus": "暴露异常真相", "hook": "异常范围扩大"},
            {"function": "recover_foreshadow", "goal_focus": "回收关键伏笔", "hook": "旧伏笔反噬"},
            {"function": "continue_crisis", "goal_focus": "推进危机对抗", "hook": "危机失控升级"},
            {"function": "transition", "goal_focus": "切换战场与目标", "hook": "新阶段代价显现"},
            {"function": "explosion", "goal_focus": "触发高强度爆点", "hook": "爆点后遗症开启"},
        ]
        hook_strength_cycle = ["medium", "high", "high", "high", "medium", "high"]

        for i in range(safe_chapter_count):
            no = start_no + i
            phase = phase_templates[i % len(phase_templates)]
            chapter_function = phase["function"]
            hook_text = phase["hook"]
            must_continue_anchor = str((must_continue_points[i % len(must_continue_points)] if must_continue_points else branch["summary"]) or "").strip()
            must_continue_anchor = workflow.clean_text(must_continue_anchor)[:60]
            previous_title = plans[-1]["title"] if plans else "上一章"
            outline_clause = f"并参考大纲约束：{outline_summary[:120]}" if outline_summary else "并保持与当前大纲和设定一致"
            base_plan = {
                "id": f"plan_{uuid.uuid4().hex[:10]}",
                "project_id": project_id,
                "branch_id": branch_id,
                "chapter_number": no,
                "title": f"第{no}章 {branch['title']}·{phase['goal_focus']}",
                "goal": f"围绕“{branch['title']}”执行“{phase['goal_focus']}”，优先承接“{must_continue_anchor or branch['summary']}”，{outline_clause}",
                "conflict": f"{branch['core_conflict'] or '制造新的关键冲突'}，并要求本章在人际关系上产生不可逆变化",
                "progression": f"承接{previous_title}与分支摘要：{branch['summary']}，本章聚焦{chapter_function}，并把冲突推进到下一层级。",
                "ending_hook": f"围绕“{branch['title']}”触发“{hook_text}”，并把“{must_continue_anchor or '主线压力'}”升级为下一章必须回应的问题",
                "target_words": safe_target_words,
                "related_arc_ids": [x for x in ([getattr(selected_arc, 'arc_id', '')] + secondary_arc_ids) if x],
                "target_arc_id": getattr(selected_arc, "arc_id", ""),
                "planning_mode": effective_planning_mode,
                "planning_reason": planning_reason,
                "arc_stage_before": getattr(selected_arc, "current_stage", ""),
                "arc_stage_after_expected": workflow._predict_next_arc_stage(getattr(selected_arc, "current_stage", "")),
                "status": WRITING_STATUS_READY,
                "chapter_task_seed": {
                    "chapter_id": f"planned_{project_id}_{no}",
                    "chapter_function": chapter_function,
                    "goals": [f"推进“{branch['title']}”分支主线", f"第{no}章完成“{phase['goal_focus']}”并触发“{hook_text}”"],
                    "must_continue_points": [str(x) for x in (must_continue_points or []) if str(x).strip()],
                    "forbidden_jumps": [str(x) for x in (forbidden_jumps or []) if str(x).strip()],
                    "required_foreshadowing_action": DEFAULT_FORESHADOWING_ACTION,
                    "required_hook_strength": hook_strength_cycle[i % len(hook_strength_cycle)],
                    "pace_target": DEFAULT_PACE_TARGET,
                    "opening_continuation": workflow.clean_text(opening_continuation),
                    "chapter_payoff": f"完成分支“{branch['title']}”的阶段性收益",
                    "style_bias": "、".join(tone_tags[:3]),
                    "target_arc_id": getattr(selected_arc, "arc_id", ""),
                    "secondary_arc_ids": secondary_arc_ids,
                    "arc_stage_before": getattr(selected_arc, "current_stage", ""),
                    "arc_stage_after_expected": workflow._predict_next_arc_stage(getattr(selected_arc, "current_stage", "")),
                    "arc_push_goal": getattr(selected_arc, "goal", ""),
                    "arc_conflict_focus": getattr(selected_arc, "core_conflict", ""),
                    "arc_payoff_expectation": hook_text,
                    "planning_mode": effective_planning_mode,
                },
            }
            context = workflow.continuation_context_builder.build(project_id, "", no, memory)
            generated_task = await workflow.chapter_task_generator.generate(context, base_plan)
            task_goals = [str(x).strip() for x in (generated_task.get("goals") or []) if str(x).strip()]
            payoff = workflow.clean_text(str(generated_task.get("chapter_payoff") or base_plan["ending_hook"]))
            continuation = workflow.clean_text(str(generated_task.get("opening_continuation") or base_plan["progression"]))
            generated_function = workflow.clean_text(str(generated_task.get("chapter_function") or chapter_function))
            previous_function = str((plans[-1].get("chapter_task_seed") or {}).get("chapter_function") or "") if plans else ""
            if previous_function and generated_function == previous_function and chapter_function != generated_function:
                generated_function = chapter_function
            task_goal_text = "；".join(task_goals[:2])
            if task_goal_text:
                base_plan["goal"] = f"{base_plan['goal']}；任务要求：{task_goal_text}"
            if continuation:
                base_plan["progression"] = f"{base_plan['progression']}；承接动作：{continuation}"
            if payoff and payoff not in base_plan["ending_hook"]:
                base_plan["ending_hook"] = f"{base_plan['ending_hook']}；阶段收益：{payoff}"
            base_plan["chapter_task_seed"] = {
                **base_plan["chapter_task_seed"],
                "chapter_function": generated_function or chapter_function,
                "goals": task_goals or base_plan["chapter_task_seed"]["goals"],
                "must_continue_points": [str(x) for x in (generated_task.get("must_continue_points") or base_plan["chapter_task_seed"]["must_continue_points"]) if str(x).strip()],
                "forbidden_jumps": [str(x) for x in (generated_task.get("forbidden_jumps") or base_plan["chapter_task_seed"]["forbidden_jumps"]) if str(x).strip()],
                "required_foreshadowing_action": workflow._normalize_foreshadowing_action(str(generated_task.get("required_foreshadowing_action") or base_plan["chapter_task_seed"]["required_foreshadowing_action"])),
                "required_hook_strength": workflow._normalize_hook_strength(str(generated_task.get("required_hook_strength") or base_plan["chapter_task_seed"]["required_hook_strength"])),
                "pace_target": str(generated_task.get("pace_target") or base_plan["chapter_task_seed"]["pace_target"] or DEFAULT_PACE_TARGET),
                "opening_continuation": continuation,
                "chapter_payoff": payoff,
                "style_bias": workflow.clean_text(str(generated_task.get("style_bias") or base_plan["chapter_task_seed"]["style_bias"])),
            }
            plans.append(base_plan)

        workflow.v2_repo.replace_plans(project_id, plans)
        workflow.chapter_task_repo.replace_by_project(
            project_id,
            [
                ChapterTask(
                    id=str(item.get("id") or ""),
                    chapter_id=str((item.get("chapter_task_seed") or {}).get("chapter_id") or ""),
                    project_id=project_id,
                    branch_id=branch_id,
                    chapter_number=int(item.get("chapter_number") or 0),
                    chapter_function=str((item.get("chapter_task_seed") or {}).get("chapter_function") or ""),
                    goals=[str(x) for x in ((item.get("chapter_task_seed") or {}).get("goals") or [])],
                    must_continue_points=[str(x) for x in ((item.get("chapter_task_seed") or {}).get("must_continue_points") or [])],
                    forbidden_jumps=[str(x) for x in ((item.get("chapter_task_seed") or {}).get("forbidden_jumps") or [])],
                    required_foreshadowing_action=workflow._normalize_foreshadowing_action(str((item.get("chapter_task_seed") or {}).get("required_foreshadowing_action") or DEFAULT_FORESHADOWING_ACTION)),
                    required_hook_strength=workflow._normalize_hook_strength(str((item.get("chapter_task_seed") or {}).get("required_hook_strength") or DEFAULT_HOOK_STRENGTH)),
                    pace_target=str((item.get("chapter_task_seed") or {}).get("pace_target") or ""),
                    opening_continuation=str((item.get("chapter_task_seed") or {}).get("opening_continuation") or ""),
                    chapter_payoff=str((item.get("chapter_task_seed") or {}).get("chapter_payoff") or ""),
                    style_bias=str((item.get("chapter_task_seed") or {}).get("style_bias") or ""),
                    target_arc_id=str((item.get("chapter_task_seed") or {}).get("target_arc_id") or ""),
                    secondary_arc_ids=[str(x) for x in ((item.get("chapter_task_seed") or {}).get("secondary_arc_ids") or [])],
                    arc_stage_before=str((item.get("chapter_task_seed") or {}).get("arc_stage_before") or ""),
                    arc_stage_after_expected=str((item.get("chapter_task_seed") or {}).get("arc_stage_after_expected") or ""),
                    arc_push_goal=str((item.get("chapter_task_seed") or {}).get("arc_push_goal") or ""),
                    arc_conflict_focus=str((item.get("chapter_task_seed") or {}).get("arc_conflict_focus") or ""),
                    arc_payoff_expectation=str((item.get("chapter_task_seed") or {}).get("arc_payoff_expectation") or ""),
                    planning_mode=str((item.get("chapter_task_seed") or {}).get("planning_mode") or effective_planning_mode),
                    status=str(item.get("status") or WRITING_STATUS_READY),
                )
                for item in plans
            ],
        )

        memory["chapter_tasks"] = [*(memory.get("chapter_tasks") or []), *plans][-300:]
        workflow.project_service.bind_memory_to_novel(project.novel_id, memory)
        memory_payload = workflow._to_project_memory_payload(project_id, memory)
        workflow.v2_repo.save_project_memory(memory_payload)
        workflow._sync_primary_repositories(project_id, memory_payload)
        workflow.v2_repo.save_memory_view(workflow._to_memory_view_payload(project_id, memory_payload))
        self.logger.info(
            "章节计划完成",
            extra=build_log_context(
                event="chapter_plan_finished",
                project_id=project_id,
                branch_id=branch_id,
                chapter_count=len(plans),
            ),
        )
        return {
            "project_id": project_id,
            "branch_id": branch_id,
            "plans": plans,
            "target_arc": workflow._to_plot_arc_dict(selected_arc) if selected_arc else {},
            "planning_mode": effective_planning_mode,
            "planning_reason": planning_reason,
            "arc_stage_before": getattr(selected_arc, "current_stage", "") if selected_arc else "",
            "arc_stage_after_expected": workflow._predict_next_arc_stage(getattr(selected_arc, "current_stage", "")) if selected_arc else "",
        }
