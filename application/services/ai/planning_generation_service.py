from __future__ import annotations

from application.services.ai.context_pack_service import ContextPackService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import ContextPackBuildRequest, DirectionPlanStatus
from domain.repositories.ai.direction_plan_repository import DirectionPlanRepository


class PlanningGenerationService:
    """Build model-generated Planner assets without bypassing ToolFacade persistence."""

    def __init__(
        self,
        *,
        work_service: WorkService,
        chapter_service: ChapterService,
        context_pack_service: ContextPackService,
        direction_plan_repository: DirectionPlanRepository,
        planning_generator,
    ) -> None:
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._context_pack_service = context_pack_service
        self._direction_plan_repository = direction_plan_repository
        self._planning_generator = planning_generator

    def build_direction_proposal_payload(
        self,
        *,
        work_id: str,
        chapter_id: str,
        user_instruction: str,
        request_id: str,
        trace_id: str,
        agent_session_id: str,
    ) -> dict[str, object]:
        self._work_service.get_work(work_id)
        chapter = self._get_chapter(work_id, chapter_id)
        readiness, snapshot = self._build_context(work_id, chapter_id)
        if self._planning_generator is None:
            raise ValueError("planner_not_configured")
        generated = self._planning_generator.generate_direction_options(
            work_id=work_id,
            chapter_id=chapter_id,
            chapter_title=str(getattr(chapter, "title", "") or ""),
            user_instruction=str(user_instruction or ""),
            context_pack=snapshot,
        )
        options: list[dict[str, object]] = []
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
        if not options:
            raise ValueError("direction_options_missing")
        return {
            "work_id": work_id,
            "chapter_id": chapter_id,
            "chapter_order": int(getattr(chapter, "order_index", 0) or 0),
            "agent_session_id": agent_session_id,
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
            "warning_codes": list(readiness.get("warnings", []) or []),
            "created_at": getattr(snapshot, "created_at", ""),
            "updated_at": getattr(snapshot, "created_at", ""),
            "request_id": request_id,
            "trace_id": trace_id,
            "direction_proposal_id": "",
        }

    def build_chapter_plan_payload(
        self,
        *,
        work_id: str,
        chapter_id: str,
        direction_proposal_id: str,
        request_id: str,
        trace_id: str,
        agent_session_id: str,
    ) -> dict[str, object]:
        self._work_service.get_work(work_id)
        self._get_chapter(work_id, chapter_id)
        proposal = self._direction_plan_repository.get_direction_proposal(direction_proposal_id)
        if proposal.work_id != work_id or proposal.chapter_id != chapter_id:
            raise ValueError("direction_proposal_scope_mismatch")
        if proposal.status not in {DirectionPlanStatus.SELECTED, DirectionPlanStatus.EDITED}:
            raise ValueError("direction_proposal_not_ready")
        if not proposal.options:
            raise ValueError("direction_options_missing")
        selected_option = next(
            (item for item in proposal.options if item.option_id == proposal.selected_option_id),
            proposal.options[0],
        )
        readiness, snapshot = self._build_context(work_id, chapter_id)
        if self._planning_generator is None:
            raise ValueError("planner_not_configured")
        generated = self._planning_generator.generate_chapter_plan(
            work_id=work_id,
            chapter_id=chapter_id,
            selected_option=selected_option.model_dump(mode="json"),
            context_pack=snapshot,
        )
        plan_items: list[dict[str, object]] = []
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
        if not plan_items:
            raise ValueError("chapter_plan_items_missing")
        return {
            "work_id": work_id,
            "chapter_id": chapter_id,
            "direction_proposal_id": proposal.direction_proposal_id,
            "selected_option_id": proposal.selected_option_id or selected_option.option_id,
            "selection_id": f"ds_{agent_session_id}_{proposal.direction_proposal_id}",
            "agent_session_id": agent_session_id,
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

    def _get_chapter(self, work_id: str, chapter_id: str):  # noqa: ANN202
        chapter = next(
            (item for item in self._chapter_service.list_chapters(work_id) if item.id.value == chapter_id),
            None,
        )
        if chapter is None:
            raise ValueError("chapter_not_found")
        return chapter

    def _build_context(self, work_id: str, chapter_id: str):  # noqa: ANN202
        readiness = self._context_pack_service.evaluate_readiness(work_id, chapter_id=chapter_id)
        if readiness.get("status") == "blocked":
            raise ValueError(str(readiness.get("blocked_reason") or "context_pack_blocked"))
        snapshot = self._context_pack_service.build_and_save(
            ContextPackBuildRequest(
                work_id=work_id,
                chapter_id=chapter_id,
                continuation_mode="continue_chapter",
                user_instruction="",
            )
        )
        return readiness, snapshot
