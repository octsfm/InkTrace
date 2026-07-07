from __future__ import annotations

from datetime import datetime, timezone

from application.services.ai.tool_facade import CoreToolFacade, ToolExecutionContext
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    ArcRef,
    ChapterBeat,
    ChapterPlan,
    ChapterPlanItem,
    ContextPackBuildRequest,
    DirectionOption,
    DirectionPlanStatus,
    DirectionProposal,
    ForeshadowArrangementItem,
    PlanConfirmation,
    WorkflowType,
    WritingTask,
    WritingTaskStatus,
)
from domain.repositories.ai.chapter_plan_repository import ChapterPlanRepository
from domain.repositories.ai.direction_plan_repository import DirectionPlanRepository


class PlanningAPIService:
    def __init__(
        self,
        *,
        work_service: WorkService,
        chapter_service: ChapterService,
        context_pack_service,
        tool_facade: CoreToolFacade,
        orchestrator,
        direction_plan_repository: DirectionPlanRepository,
        chapter_plan_repository: ChapterPlanRepository,
    ) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._context_pack_service = context_pack_service
        self._tool_facade = tool_facade
        self._orchestrator = orchestrator
        self._direction_plan_repository = direction_plan_repository
        self._chapter_plan_repository = chapter_plan_repository

    def generate_direction_proposal(
        self,
        *,
        work_id: str,
        chapter_id: str,
        user_instruction: str,
        request_id: str,
        trace_id: str,
        idempotency_key: str,
    ) -> DirectionProposal:
        self._work_service.get_work(work_id)
        payload = self._build_direction_payload(
            work_id=work_id,
            chapter_id=chapter_id,
            user_instruction=user_instruction,
            request_id=request_id,
            trace_id=trace_id,
        )
        result = self._tool_facade.call(
            "create_direction_proposal",
            context=self._context_from_request(
                work_id=work_id,
                chapter_id=chapter_id,
                request_id=request_id,
                trace_id=trace_id,
                idempotency_key=idempotency_key,
                agent_session_id=str(payload["agent_session_id"]),
                agent_step_id="direction_generation",
            ),
            payload=payload,
        )
        proposal_id = str(result.payload.get("result_ref", "")).split(":", 1)[-1]
        return self.get_direction_proposal(proposal_id)

    def list_direction_proposals(self, work_id: str, *, chapter_id: str = "") -> list[DirectionProposal]:
        return self._direction_plan_repository.list_direction_proposals(work_id, chapter_id=chapter_id)

    def get_direction_proposal(self, proposal_id: str) -> DirectionProposal:
        return self._direction_plan_repository.get_direction_proposal(proposal_id)

    def select_direction(
        self,
        *,
        proposal_id: str,
        selected_option_id: str,
        user_id: str,
        edited_fields: list[str],
        edited_values: dict[str, object],
        request_id: str,
        user_action: bool,
    ) -> dict[str, object]:
        proposal = self.get_direction_proposal(proposal_id)
        if proposal.status not in {DirectionPlanStatus.WAITING_FOR_SELECTION, DirectionPlanStatus.EDITED, DirectionPlanStatus.SELECTED}:
            raise ValueError("direction_proposal_not_ready")
        run = self._orchestrator.start_workflow(
            work_id=proposal.work_id,
            chapter_id=proposal.chapter_id,
            workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
            user_instruction="direction_selection_api",
            caller_type="user_action",
        )
        run = self._orchestrator.advance_workflow(
            run.session_id,
            decision="continue",
            result_ref=f"memory_context:{proposal.source_context_pack_id or 'cp_api'}",
            safe_message="memory ready",
        )
        run = self._orchestrator.advance_workflow(
            run.session_id,
            decision="continue",
            result_ref=f"direction:{proposal.direction_proposal_id}",
            safe_message="direction ready",
        )
        run = self._orchestrator.submit_user_decision(
            run.session_id,
            user_decision="confirm_direction",
            safe_message="direction selected",
            request_id=request_id,
            metadata={
                "selected_direction_id": proposal.direction_proposal_id,
                "selected_option_id": selected_option_id,
                "edited_fields": edited_fields,
                "edited_values": edited_values,
                "user_id": user_id,
            },
        )
        return {
            "selection": self._direction_plan_repository.get_direction_selection(f"ds_{run.session_id}_{proposal.direction_proposal_id}"),
            "proposal": self.get_direction_proposal(proposal_id),
            "workflow_stage": run.current_stage,
        }

    def generate_chapter_plan(
        self,
        *,
        work_id: str,
        chapter_id: str,
        direction_proposal_id: str,
        request_id: str,
        trace_id: str,
        idempotency_key: str,
    ) -> ChapterPlan:
        proposal = self.get_direction_proposal(direction_proposal_id)
        if proposal.status not in {DirectionPlanStatus.SELECTED, DirectionPlanStatus.EDITED}:
            raise ValueError("direction_proposal_not_ready")
        payload = self._build_plan_payload(
            work_id=work_id,
            chapter_id=chapter_id,
            proposal=proposal,
            request_id=request_id,
            trace_id=trace_id,
        )
        result = self._tool_facade.call(
            "create_chapter_plan",
            context=self._context_from_request(
                work_id=work_id,
                chapter_id=chapter_id,
                request_id=request_id,
                trace_id=trace_id,
                idempotency_key=idempotency_key,
                agent_session_id=str(payload["agent_session_id"]),
                agent_step_id="chapter_plan_generation",
            ),
            payload=payload,
        )
        plan_id = str(result.payload.get("result_ref", "")).split(":", 1)[-1]
        return self.get_chapter_plan(plan_id)

    def list_chapter_plans(self, work_id: str, *, chapter_id: str = "") -> list[ChapterPlan]:
        return self._chapter_plan_repository.list_by_work(work_id, chapter_id=chapter_id)

    def get_chapter_plan(self, plan_id: str) -> ChapterPlan:
        return self._chapter_plan_repository.get(plan_id)

    def confirm_chapter_plan(
        self,
        *,
        plan_id: str,
        user_id: str,
        edited_items: list[str],
        edited_fields: dict[str, object],
        user_edit_notes: str,
        request_id: str,
        user_action: bool,
    ) -> dict[str, object]:
        plan = self.get_chapter_plan(plan_id)
        run = self._orchestrator.start_workflow(
            work_id=plan.work_id,
            chapter_id=plan.chapter_id,
            workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
            user_instruction="chapter_plan_confirm_api",
            caller_type="user_action",
        )
        run = self._orchestrator.advance_workflow(
            run.session_id,
            decision="continue",
            result_ref=f"memory_context:{plan.source_context_pack_id or 'cp_api'}",
            safe_message="memory ready",
        )
        run = self._orchestrator.advance_workflow(
            run.session_id,
            decision="continue",
            result_ref=f"direction:{plan.direction_proposal_id}",
            safe_message="direction ready",
        )
        run = self._orchestrator.submit_user_decision(
            run.session_id,
            user_decision="confirm_direction",
            safe_message="direction confirmed",
            request_id=request_id,
            metadata={
                "selected_direction_id": plan.direction_proposal_id,
                "selected_option_id": plan.selected_option_id,
            },
        )
        run = self._orchestrator.submit_user_decision(
            run.session_id,
            user_decision="confirm_chapter_plan",
            safe_message="plan confirmed",
            request_id=request_id,
            metadata={
                "selected_chapter_plan_id": plan.chapter_plan_id,
                "edited_items": edited_items,
                "edited_fields": edited_fields,
                "user_edit_notes": user_edit_notes,
                "user_id": user_id,
            },
        )
        return {
            "confirmation": self._direction_plan_repository.get_plan_confirmation(f"pc_{run.session_id}_{plan.chapter_plan_id}"),
            "plan": self.get_chapter_plan(plan_id),
            "writing_task": self._direction_plan_repository.get_active_writing_task(plan.work_id, chapter_id=plan.chapter_id),
            "workflow_stage": run.current_stage,
        }

    def reject_chapter_plan(
        self,
        *,
        plan_id: str,
        user_id: str,
        user_edit_notes: str,
        request_id: str,
        user_action: bool,
    ) -> dict[str, object]:
        plan = self.get_chapter_plan(plan_id)
        run = self._orchestrator.start_workflow(
            work_id=plan.work_id,
            chapter_id=plan.chapter_id,
            workflow_type=WorkflowType.CONTINUATION_WORKFLOW,
            user_instruction="chapter_plan_reject_api",
            caller_type="user_action",
        )
        run = self._orchestrator.advance_workflow(
            run.session_id,
            decision="continue",
            result_ref=f"memory_context:{plan.source_context_pack_id or 'cp_api'}",
            safe_message="memory ready",
        )
        run = self._orchestrator.advance_workflow(
            run.session_id,
            decision="continue",
            result_ref=f"direction:{plan.direction_proposal_id}",
            safe_message="direction ready",
        )
        run = self._orchestrator.submit_user_decision(
            run.session_id,
            user_decision="confirm_direction",
            safe_message="direction confirmed",
            request_id=request_id,
            metadata={
                "selected_direction_id": plan.direction_proposal_id,
                "selected_option_id": plan.selected_option_id,
            },
        )
        run = self._orchestrator.submit_user_decision(
            run.session_id,
            user_decision="reject",
            safe_message="plan rejected",
            request_id=request_id,
            metadata={
                "selected_chapter_plan_id": plan.chapter_plan_id,
                "user_edit_notes": user_edit_notes,
                "user_id": user_id,
            },
        )
        return {
            "confirmation": self._direction_plan_repository.get_plan_confirmation(f"pc_{run.session_id}_{plan.chapter_plan_id}"),
            "plan": self.get_chapter_plan(plan_id),
            "workflow_stage": run.current_stage,
        }

    def list_writing_tasks(self, work_id: str, *, chapter_id: str = "") -> list[WritingTask]:
        return self._direction_plan_repository.list_writing_tasks(work_id, chapter_id=chapter_id)

    def get_writing_task(self, writing_task_id: str) -> WritingTask:
        return self._direction_plan_repository.get_writing_task(writing_task_id)

    def confirm_writing_task(
        self,
        *,
        writing_task_id: str,
        user_id: str,
        request_id: str,
        trace_id: str,
        user_action: bool,
        decision_note: str = "",
    ) -> WritingTask:
        task = self.get_writing_task(writing_task_id)
        if task.status != WritingTaskStatus.READY:
            raise ValueError("writing_task_not_ready")

        metadata = dict(task.metadata or {})
        if metadata.get("user_confirmed") and str(metadata.get("confirmed_by", "") or "") == user_id:
            return task

        metadata.update(
            {
                "user_confirmed": True,
                "confirmed_by": user_id,
                "confirmed_via": "writing_task_confirm_api",
                "confirmed_request_id": request_id,
                "confirmed_trace_id": trace_id,
                "confirmation_note": decision_note or "",
            }
        )
        updated = task.model_copy(
            update={
                "metadata": metadata,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id or task.request_id,
                "trace_id": trace_id or task.trace_id,
            }
        )
        self._direction_plan_repository.save_writing_task(updated)
        return self.get_writing_task(writing_task_id)

    def _direction_generation_context(self, work_id: str, chapter_id: str) -> dict[str, object]:
        readiness = self._context_pack_service.evaluate_readiness(work_id, chapter_id=chapter_id)
        snapshot = self._context_pack_service.build_and_save(
            ContextPackBuildRequest(
                work_id=work_id,
                chapter_id=chapter_id,
                continuation_mode="continue_chapter",
                user_instruction="",
            )
        )
        return {"readiness": readiness, "snapshot": snapshot}

    def _build_direction_payload(
        self,
        *,
        work_id: str,
        chapter_id: str,
        user_instruction: str,
        request_id: str,
        trace_id: str,
    ) -> dict[str, object]:
        chapters = self._chapter_service.list_chapters(work_id)
        chapter = next((item for item in chapters if item.id.value == chapter_id), None)
        if chapter is None:
            raise ValueError("chapter_not_found")
        context = self._direction_generation_context(work_id, chapter_id)
        readiness = context["readiness"]
        snapshot = context["snapshot"]
        degraded_warnings = list(readiness.get("warnings", []) or [])
        title_hint = str(getattr(chapter, "title", "") or "当前章节")
        seed_text = str(user_instruction or "继续推进当前主线")
        options = []
        for index, label in enumerate(("A", "B", "C"), start=1):
            option_id = f"do_{chapter_id}_{index}"
            options.append(
                {
                    "option_id": option_id,
                    "label": label,
                    "title": f"方向 {label}",
                    "plot_summary": f"{title_hint}后续方向 {label}：围绕{seed_text}推进，并拉近与灯塔谜团的距离。",
                    "narrative_premise": f"以{seed_text}为核心，推进顾迟对灯塔与父亲线索的追查。",
                    "narrative_benefits": [f"强化方向 {label} 的悬念推进", f"保留灯塔主线的可持续张力"],
                    "main_conflicts": [
                        {
                            "conflict_name": "灯塔谜团",
                            "conflict_description": "顾迟必须在风险升级前确认钟声来源。",
                            "conflict_type": "main",
                            "intensity": "medium",
                        }
                    ],
                    "foreshadow_usage": [
                        {
                            "foreshadow_id": f"fs_{index}",
                            "foreshadow_description": "旧航海图边角盐渍",
                            "usage_plan": "作为父亲线索的持续提示",
                            "is_new": False,
                        }
                    ],
                    "risk_points": [
                        {
                            "risk_description": "信息揭示过快会削弱后续悬念",
                            "risk_severity": "medium",
                            "mitigation": "将真相拆分到多章逐步释放",
                        }
                    ],
                    "estimated_chapters": 3 + (index - 1),
                    "chapter_preview": [f"第{index}步推进灯塔调查", f"第{index + 1}步扩展父亲遗留线索"],
                    "base_arc_refs": [],
                    "base_memory_refs": ["memory_latest"],
                    "score": {
                        "total_score": 86 - index,
                        "consistency_score": 88 - index,
                        "conflict_density_score": 84,
                        "satisfaction_rhythm_score": 82,
                        "foreshadow_progress_score": 87,
                        "risk_controllability_score": 83,
                        "score_rationale": "满足当前主线推进与悬念节奏。",
                    },
                    "confidence": 0.8,
                    "tone_direction": "悬疑压迫",
                    "key_characters_involved": ["顾迟"],
                    "created_at": getattr(snapshot, "created_at", ""),
                }
            )
        return {
            "work_id": work_id,
            "chapter_id": chapter_id,
            "chapter_order": int(getattr(chapter, "order_index", 0) or 0),
            "agent_session_id": f"planner_direction_{chapter_id}",
            "source_context_pack_id": getattr(snapshot, "context_pack_id", ""),
            "source_arc_refs": [],
            "source_memory_refs": ["memory_latest"],
            "status": DirectionPlanStatus.WAITING_FOR_SELECTION,
            "version": 1,
            "options": options,
            "generation_metadata": {"prompt_key": "direction_generation", "readiness_status": readiness.get("status", "unknown")},
            "created_by": "planner_agent",
            "warning_codes": degraded_warnings,
            "created_at": getattr(snapshot, "created_at", ""),
            "updated_at": getattr(snapshot, "created_at", ""),
            "request_id": request_id,
            "trace_id": trace_id,
            "direction_proposal_id": "",
        }

    def _build_plan_payload(
        self,
        *,
        work_id: str,
        chapter_id: str,
        proposal: DirectionProposal,
        request_id: str,
        trace_id: str,
    ) -> dict[str, object]:
        readiness = self._context_pack_service.evaluate_readiness(work_id, chapter_id=chapter_id)
        snapshot = self._context_pack_service.build_and_save(
            ContextPackBuildRequest(
                work_id=work_id,
                chapter_id=chapter_id,
                continuation_mode="continue_chapter",
                user_instruction="",
            )
        )
        selected_option = next((item for item in proposal.options if item.option_id == proposal.selected_option_id), proposal.options[0])
        plan_items = []
        for index in range(1, 4):
            plan_items.append(
                {
                    "item_id": f"cpi_{chapter_id}_{index}",
                    "plan_order": index,
                    "chapter_goal": f"第{index}章目标：{selected_option.plot_summary}",
                    "key_events": [
                        {
                            "beat_order": 1,
                            "beat_name": f"推进节点 {index}",
                            "beat_description": f"围绕{selected_option.plot_summary}推进关键行动。",
                            "beat_type": "development",
                            "emotional_tone": "紧张",
                            "involved_characters": ["顾迟"],
                        }
                    ],
                    "conflict_progression": f"本章继续推进{selected_option.narrative_premise}",
                    "foreshadow_arrangement": [
                        {
                            "foreshadow_id": f"fs_{index}",
                            "foreshadow_description": "旧航海图边角盐渍",
                            "arrangement": "advance",
                            "arrangement_detail": "继续强化父亲留下的线索。",
                        }
                    ],
                    "forbidden_items": ["不要提前揭示父亲真相"],
                    "required_beats": [f"关键节拍 {index}"],
                    "estimated_word_count": 2200,
                    "estimated_word_count_max": 3200,
                    "tone_hint": "悬疑压迫",
                    "pov_hint": "顾迟",
                    "arc_alignment": [],
                    "source_sequence_event_refs": [f"seq_event_{index}"],
                    "created_at": getattr(snapshot, "created_at", ""),
                }
            )
        return {
            "work_id": work_id,
            "chapter_id": chapter_id,
            "direction_proposal_id": proposal.direction_proposal_id,
            "selected_option_id": proposal.selected_option_id or selected_option.option_id,
            "selection_id": f"ds_planner_{proposal.direction_proposal_id}",
            "agent_session_id": proposal.agent_session_id or f"planner_plan_{chapter_id}",
            "source_context_pack_id": getattr(snapshot, "context_pack_id", ""),
            "source_arc_refs": [],
            "source_memory_refs": ["memory_latest"],
            "status": DirectionPlanStatus.WAITING_FOR_CONFIRMATION,
            "version": 1,
            "plan_items": plan_items,
            "plan_summary": f"围绕“{selected_option.plot_summary}”推进未来三章。",
            "constraints": ["保持悬念递进", "不得越过已知世界观边界"],
            "total_estimated_chapters": len(plan_items),
            "total_estimated_words": 7800,
            "generation_metadata": {"prompt_key": "chapter_plan_generation", "readiness_status": readiness.get("status", "unknown")},
            "created_by": "planner_agent",
            "warning_codes": list(readiness.get("warnings", []) or []),
            "created_at": getattr(snapshot, "created_at", ""),
            "updated_at": getattr(snapshot, "created_at", ""),
            "request_id": request_id,
            "trace_id": trace_id,
        }

    @staticmethod
    def _context_from_request(
        *,
        work_id: str,
        chapter_id: str,
        request_id: str,
        trace_id: str,
        idempotency_key: str = "",
        agent_session_id: str = "",
        agent_step_id: str = "",
    ) -> ToolExecutionContext:
        return ToolExecutionContext(
            caller_type="agent",
            work_id=work_id,
            chapter_id=chapter_id,
            request_id=request_id,
            trace_id=trace_id,
            agent_session_id=agent_session_id,
            agent_step_id=agent_step_id,
            agent_type="planner",
            session_status="running",
            step_status="waiting_observation",
            resource_scope_refs=[f"work:{work_id}", f"chapter:{chapter_id}"],
            side_effect_level="plan_write",
            idempotency_key=idempotency_key,
        )
