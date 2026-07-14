from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from threading import RLock

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
    WorkflowStageName,
    WritingTask,
    WritingTaskStatus,
)
from domain.repositories.ai.chapter_plan_repository import ChapterPlanRepository
from domain.repositories.ai.direction_plan_repository import DirectionPlanRepository
from domain.value_objects.outline_snapshot import outline_content_hash


_P2_WRITING_TASK_CONFIRM_LOCK = RLock()


def _normalize_decision_note(value: str) -> str:
    return str(value or "").strip()


def _user_decision_request_hash(*, resource_id: str, user_id: str, decision_note: str) -> str:
    canonical = json.dumps(
        {
            "resource_id": str(resource_id),
            "user_id": str(user_id),
            "decision_note": _normalize_decision_note(decision_note),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
        planning_generator=None,
        writing_asset_service=None,
        trace_service=None,
    ) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._context_pack_service = context_pack_service
        self._tool_facade = tool_facade
        self._orchestrator = orchestrator
        self._direction_plan_repository = direction_plan_repository
        self._chapter_plan_repository = chapter_plan_repository
        self._planning_generator = planning_generator
        self._writing_asset_service = writing_asset_service
        self._trace_service = trace_service

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
        if not user_action:
            raise ValueError("action_not_allowed")
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
        run = self._orchestrator.prepare_memory_context(run.session_id)
        if run.current_stage == WorkflowStageName.FAILED:
            raise ValueError(run.error_code or "memory_context_prepare_failed")
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
        if run.current_stage == WorkflowStageName.FAILED:
            raise ValueError(run.error_code or "chapter_plan_generation_failed")
        generated_plan = next(
            (
                item
                for item in self._chapter_plan_repository.list_by_work(proposal.work_id, chapter_id=proposal.chapter_id)
                if item.agent_session_id == run.session_id
                and item.direction_proposal_id == proposal.direction_proposal_id
                and item.status == DirectionPlanStatus.WAITING_FOR_CONFIRMATION
                and item.stale_status == "fresh"
            ),
            None,
        )
        return {
            "selection": self._direction_plan_repository.get_direction_selection(f"ds_{run.session_id}_{proposal.direction_proposal_id}"),
            "proposal": self.get_direction_proposal(proposal_id),
            "workflow_stage": run.current_stage,
            "chapter_plan": generated_plan,
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
        existing_plan = next(
            (
                item
                for item in self._chapter_plan_repository.list_by_work(work_id, chapter_id=chapter_id)
                if item.direction_proposal_id == direction_proposal_id
                and item.status == DirectionPlanStatus.WAITING_FOR_CONFIRMATION
                and item.stale_status == "fresh"
            ),
            None,
        )
        if existing_plan is not None:
            return existing_plan
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
        if not user_action:
            raise ValueError("action_not_allowed")
        plan = self.get_chapter_plan(plan_id)
        run = self._require_plan_confirmation_workflow(plan)
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
        if not user_action:
            raise ValueError("action_not_allowed")
        plan = self.get_chapter_plan(plan_id)
        run = self._require_plan_confirmation_workflow(plan)
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

    def _require_plan_confirmation_workflow(self, plan: ChapterPlan):  # noqa: ANN202
        if not str(plan.agent_session_id or "").strip():
            raise ValueError("chapter_plan_workflow_not_found")
        run = self._orchestrator.get_workflow_run(plan.agent_session_id)
        if run.current_stage != WorkflowStageName.CHAPTER_PLAN_CONFIRM_WAITING:
            raise ValueError("chapter_plan_workflow_not_waiting")
        if not any(item.ref_type == "chapter_plan" and item.ref_id == plan.chapter_plan_id for item in run.result_refs):
            raise ValueError("chapter_plan_workflow_mismatch")
        return run

    def list_writing_tasks(self, work_id: str, *, chapter_id: str = "") -> list[WritingTask]:
        return self._direction_plan_repository.list_writing_tasks(work_id, chapter_id=chapter_id)

    def get_writing_task(self, writing_task_id: str) -> WritingTask:
        return self._direction_plan_repository.get_writing_task(writing_task_id)

    def is_outline_assist_writing_task(self, writing_task_id: str) -> bool:
        try:
            task = self._direction_plan_repository.get_writing_task(writing_task_id)
        except ValueError:
            return False
        return (task.metadata or {}).get("source") == "p2_outline_assist"

    def confirm_writing_task(
        self,
        *,
        writing_task_id: str,
        user_id: str,
        request_id: str,
        trace_id: str,
        user_action: bool,
        decision_note: str = "",
        idempotency_key: str = "",
    ) -> WritingTask:
        if not user_action:
            raise ValueError("action_not_allowed")
        task = self.get_writing_task(writing_task_id)
        if (task.metadata or {}).get("source") == "p2_outline_assist":
            with _P2_WRITING_TASK_CONFIRM_LOCK:
                return self._confirm_writing_task_loaded(
                    self.get_writing_task(writing_task_id),
                    user_id=user_id,
                    request_id=request_id,
                    trace_id=trace_id,
                    decision_note=decision_note,
                    idempotency_key=idempotency_key,
                )
        return self._confirm_writing_task_loaded(
            task,
            user_id=user_id,
            request_id=request_id,
            trace_id=trace_id,
            decision_note=decision_note,
            idempotency_key=idempotency_key,
        )

    def _confirm_writing_task_loaded(
        self,
        task: WritingTask,
        *,
        user_id: str,
        request_id: str,
        trace_id: str,
        decision_note: str,
        idempotency_key: str,
    ) -> WritingTask:
        metadata = dict(task.metadata or {})
        is_p2_task = metadata.get("source") == "p2_outline_assist"
        normalized_note = _normalize_decision_note(decision_note) if is_p2_task else decision_note or ""
        if is_p2_task:
            if not str(idempotency_key or "").strip():
                raise ValueError("P2_IDEMPOTENCY_KEY_REQUIRED")
            key_hash = hashlib.sha256(idempotency_key.strip().encode("utf-8")).hexdigest()
            request_hash = _user_decision_request_hash(
                resource_id=task.writing_task_id,
                user_id=user_id,
                decision_note=normalized_note,
            )
            self._require_confirmation_request_matches_key_scope(
                task,
                key_hash=key_hash,
                request_hash=request_hash,
            )
            if metadata.get("confirmation_key_hash"):
                if (
                    metadata.get("confirmation_key_hash") != key_hash
                    or metadata.get("confirmation_request_hash") != request_hash
                ):
                    raise ValueError("P2_IDEMPOTENCY_CONFLICT")
                if task.status == WritingTaskStatus.READY and metadata.get("user_confirmed"):
                    return task
        elif (
            task.status == WritingTaskStatus.READY
            and metadata.get("user_confirmed")
            and str(metadata.get("confirmed_by", "") or "") == user_id
        ):
            return task
        if is_p2_task:
            if task.status != WritingTaskStatus.PENDING:
                raise ValueError("writing_task_not_ready")
            try:
                plan = self._chapter_plan_repository.get(task.chapter_plan_id)
            except ValueError as exc:
                raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING") from exc
            if (
                plan.work_id != task.work_id
                or plan.chapter_id != task.chapter_id
                or plan.status not in {DirectionPlanStatus.CONFIRMED, DirectionPlanStatus.EDITED}
                or plan.stale_status != "fresh"
                or int(plan.version) != int(metadata.get("chapter_plan_version") or 0)
            ):
                raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING")
            current_plan = next(
                (
                    candidate
                    for candidate in self._chapter_plan_repository.list_by_work(task.work_id, chapter_id=task.chapter_id)
                    if candidate.status in {DirectionPlanStatus.CONFIRMED, DirectionPlanStatus.EDITED}
                    and candidate.stale_status == "fresh"
                ),
                None,
            )
            if current_plan is None or current_plan.chapter_plan_id != plan.chapter_plan_id:
                raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING")
            if self._writing_asset_service is None:
                raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING")
            try:
                current_outline = self._writing_asset_service.get_chapter_outline(task.chapter_id)
            except ValueError as exc:
                raise ValueError("P2_WRITING_TASK_PREREQUISITE_MISSING") from exc
            if (
                int(current_outline.version) != int(metadata.get("target_revision") or 0)
                or outline_content_hash(current_outline.content_text, current_outline.content_tree_json)
                != str(metadata.get("target_content_hash") or "")
            ):
                raise ValueError("P2_OUTLINE_TARGET_CONFLICT")
            self._record_outline_task_confirmation_before_write(task, user_id=user_id)
            metadata["confirmation_key_hash"] = key_hash
            metadata["confirmation_request_hash"] = request_hash
        elif task.status != WritingTaskStatus.READY:
            raise ValueError("writing_task_not_ready")

        metadata.update(
            {
                "user_confirmed": True,
                "confirmed_by": user_id,
                "confirmed_via": "writing_task_confirm_api",
                "confirmed_request_id": request_id,
                "confirmed_trace_id": task.trace_id if is_p2_task else trace_id,
                "confirmation_note": normalized_note,
            }
        )
        updated = task.model_copy(
            update={
                "status": WritingTaskStatus.READY if is_p2_task else task.status,
                "metadata": metadata,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "request_id": task.request_id if is_p2_task else request_id or task.request_id,
                "trace_id": task.trace_id if is_p2_task else trace_id or task.trace_id,
            }
        )
        self._direction_plan_repository.save_writing_task(updated)
        return self.get_writing_task(task.writing_task_id)

    def _require_confirmation_request_matches_key_scope(
        self,
        task: WritingTask,
        *,
        key_hash: str,
        request_hash: str,
    ) -> None:
        for candidate in self._direction_plan_repository.list_writing_tasks(task.work_id):
            metadata = candidate.metadata or {}
            if (
                metadata.get("confirmation_key_hash") == key_hash
                and metadata.get("confirmation_request_hash") != request_hash
            ):
                raise ValueError("P2_IDEMPOTENCY_CONFLICT")

    def _record_outline_task_confirmation_before_write(self, task: WritingTask, *, user_id: str) -> None:
        if self._trace_service is None or not str(task.trace_id or "").strip():
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED")
        try:
            trace = self._trace_service.ensure_operation_trace(
                trace_id=task.trace_id,
                work_id=task.work_id,
                chapter_id=task.chapter_id,
                operation_ref=task.writing_task_id,
                workflow_type="outline_assist",
            )
            event = self._trace_service.record_audit_event(
                trace_id=task.trace_id,
                session_id=task.writing_task_id,
                step_id="writing_task_confirm",
                event_type="user_decision_recorded",
                summary="writing_task_confirm",
                payload_digest={
                    "writing_task_id": task.writing_task_id,
                    "suggestion_id": str((task.metadata or {}).get("suggestion_id") or ""),
                    "decision_type": "confirm_writing_task",
                    "user_id": user_id,
                },
                high_risk_user_action=True,
            )
            if trace is None or event is None:
                raise ValueError("audit_record_not_persisted")
        except Exception as exc:
            raise ValueError("P2_OUTLINE_AUDIT_WRITE_FAILED") from exc

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
        if self._planning_generator is None:
            raise ValueError("planner_not_configured")
        generated = self._planning_generator.generate_direction_options(
            work_id=work_id,
            chapter_id=chapter_id,
            chapter_title=str(getattr(chapter, "title", "") or ""),
            user_instruction=str(user_instruction or ""),
            context_pack=snapshot,
        )
        options = []
        for index, generated_option in enumerate(list(generated.get("options", []) or []), start=1):
            option = dict(generated_option)
            option.update(
                {
                    "option_id": f"do_{chapter_id}_{index}",
                    "base_arc_refs": [],
                    "base_memory_refs": ["memory_latest"],
                    "created_at": getattr(snapshot, "created_at", ""),
                }
            )
            options.append(option)
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
            "generation_metadata": {
                "prompt_key": "direction_generation_p1",
                "readiness_status": readiness.get("status", "unknown"),
                "provider_name": str(generated.get("provider_name", "") or ""),
                "model_name": str(generated.get("model_name", "") or ""),
            },
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
        if not proposal.options:
            raise ValueError("direction_options_missing")
        selected_option = next((item for item in proposal.options if item.option_id == proposal.selected_option_id), proposal.options[0])
        if self._planning_generator is None:
            raise ValueError("planner_not_configured")
        generated = self._planning_generator.generate_chapter_plan(
            work_id=work_id,
            chapter_id=chapter_id,
            selected_option=selected_option.model_dump(mode="json"),
            context_pack=snapshot,
        )
        plan_items = []
        for index, generated_item in enumerate(list(generated.get("plan_items", []) or []), start=1):
            plan_item = dict(generated_item)
            plan_item.update(
                {
                    "item_id": f"cpi_{chapter_id}_{index}",
                    "arc_alignment": [],
                    "source_sequence_event_refs": [],
                    "created_at": getattr(snapshot, "created_at", ""),
                }
            )
            plan_items.append(plan_item)
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
            "plan_summary": str(generated.get("plan_summary", "") or ""),
            "constraints": list(generated.get("constraints", []) or []),
            "total_estimated_chapters": len(plan_items),
            "total_estimated_words": sum(int(item.get("estimated_word_count", 0) or 0) for item in plan_items),
            "generation_metadata": {
                "prompt_key": "chapter_plan_generation_p1",
                "readiness_status": readiness.get("status", "unknown"),
                "provider_name": str(generated.get("provider_name", "") or ""),
                "model_name": str(generated.get("model_name", "") or ""),
            },
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
