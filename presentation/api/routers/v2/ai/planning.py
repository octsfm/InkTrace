from __future__ import annotations

from fastapi import APIRouter, Request

from application.services.ai.tool_facade import ToolExecutionContext
from domain.entities.ai.models import ContextPackBuildRequest
from domain.entities.ai.models import (
    ArcRef,
    ChapterBeat,
    ChapterPlan,
    ChapterPlanItem,
    DirectionOption,
    DirectionPlanStatus,
    DirectionProposal,
    ForeshadowArrangementItem,
    PlanConfirmation,
    WorkflowType,
    WritingTask,
)
from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import (
    ConfirmWritingTaskRequest,
    ConfirmChapterPlanRequest,
    GenerateChapterPlanRequest,
    GenerateDirectionProposalRequest,
    RejectChapterPlanRequest,
    SelectDirectionRequest,
)

router = APIRouter(tags=["v2-ai-planning"])


def _ensure_gate_request(request: Request, *, caller_type: str, user_action: bool, idempotency_key: str):
    if caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    if not user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


def _ensure_write_request(request: Request, *, caller_type: str, idempotency_key: str):
    if caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


def _context_from_request(
    request: Request,
    *,
    work_id: str,
    chapter_id: str,
    idempotency_key: str = "",
    agent_session_id: str = "",
    agent_step_id: str = "",
) -> ToolExecutionContext:
    return ToolExecutionContext(
        caller_type="agent",
        work_id=work_id,
        chapter_id=chapter_id,
        request_id=getattr(request.state, "request_id", ""),
        trace_id=request.headers.get("X-Trace-Id", "").strip(),
        agent_session_id=agent_session_id,
        agent_step_id=agent_step_id,
        agent_type="planner",
        session_status="running",
        step_status="waiting_observation",
        resource_scope_refs=[f"work:{work_id}", f"chapter:{chapter_id}"],
        side_effect_level="plan_write",
        idempotency_key=idempotency_key,
    )


def _direction_generation_context(work_id: str, chapter_id: str) -> dict[str, object]:
    context_service = dependencies.get_context_pack_service()
    readiness = context_service.evaluate_readiness(work_id, chapter_id=chapter_id)
    snapshot = context_service.build_and_save(
        request=ContextPackBuildRequest(
            work_id=work_id,
            chapter_id=chapter_id,
            continuation_mode="continue_chapter",
            user_instruction="",
        )
    )
    return {"readiness": readiness, "snapshot": snapshot}


def _build_direction_payload(*, work_id: str, chapter_id: str, request: Request, user_instruction: str) -> dict[str, object]:
    chapter_service = dependencies.get_chapter_service()
    chapters = chapter_service.list_chapters(work_id)
    chapter = next((item for item in chapters if item.id.value == chapter_id), None)
    if chapter is None:
        raise ValueError("chapter_not_found")
    context = _direction_generation_context(work_id, chapter_id)
    readiness = context["readiness"]
    snapshot = context["snapshot"]
    degraded_warnings = list(readiness.get("warnings", []) or [])
    title_hint = str(getattr(chapter, "title", "") or "当前章节")
    seed_text = str(user_instruction or "继续推进当前主线")
    proposal_id = ""
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
                "chapter_preview": [
                    f"第{index}步推进灯塔调查",
                    f"第{index + 1}步扩展父亲遗留线索",
                ],
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
        "generation_metadata": {
            "prompt_key": "direction_generation",
            "readiness_status": readiness.get("status", "unknown"),
        },
        "created_by": "planner_agent",
        "warning_codes": degraded_warnings,
        "created_at": getattr(snapshot, "created_at", ""),
        "updated_at": getattr(snapshot, "created_at", ""),
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": request.headers.get("X-Trace-Id", "").strip(),
        "direction_proposal_id": proposal_id,
    }


def _build_plan_payload(*, work_id: str, chapter_id: str, proposal: DirectionProposal, request: Request) -> dict[str, object]:
    context_service = dependencies.get_context_pack_service()
    readiness = context_service.evaluate_readiness(work_id, chapter_id=chapter_id)
    snapshot = context_service.build_and_save(
        request=ContextPackBuildRequest(
            work_id=work_id,
            chapter_id=chapter_id,
            continuation_mode="continue_chapter",
            user_instruction="",
        )
    )
    selected_option = next(
        (item for item in proposal.options if item.option_id == proposal.selected_option_id),
        proposal.options[0],
    )
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
        "generation_metadata": {
            "prompt_key": "chapter_plan_generation",
            "readiness_status": readiness.get("status", "unknown"),
        },
        "created_by": "planner_agent",
        "warning_codes": list(readiness.get("warnings", []) or []),
        "created_at": getattr(snapshot, "created_at", ""),
        "updated_at": getattr(snapshot, "created_at", ""),
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": request.headers.get("X-Trace-Id", "").strip(),
    }


def _serialize_arc_ref(ref: ArcRef) -> dict[str, object]:
    return ref.model_dump(mode="json")


def _serialize_direction_option(option: DirectionOption) -> dict[str, object]:
    return option.model_dump(mode="json")


def _serialize_direction_proposal(proposal: DirectionProposal) -> dict[str, object]:
    return {
        **proposal.model_dump(mode="json"),
        "options": [_serialize_direction_option(item) for item in proposal.options],
    }


def _serialize_chapter_beat(beat: ChapterBeat) -> dict[str, object]:
    return beat.model_dump(mode="json")


def _serialize_chapter_plan_item(item: ChapterPlanItem) -> dict[str, object]:
    return {
        **item.model_dump(mode="json"),
        "key_events": [_serialize_chapter_beat(beat) for beat in item.key_events],
        "foreshadow_arrangement": [entry.model_dump(mode="json") for entry in item.foreshadow_arrangement],
        "arc_alignment": [_serialize_arc_ref(ref) for ref in item.arc_alignment],
    }


def _serialize_chapter_plan(plan: ChapterPlan) -> dict[str, object]:
    return {
        **plan.model_dump(mode="json"),
        "plan_items": [_serialize_chapter_plan_item(item) for item in plan.plan_items],
        "source_arc_refs": [_serialize_arc_ref(ref) for ref in plan.source_arc_refs],
    }


def _serialize_plan_confirmation(confirmation: PlanConfirmation) -> dict[str, object]:
    return confirmation.model_dump(mode="json")


def _serialize_writing_task(task: WritingTask) -> dict[str, object]:
    return task.model_dump(mode="json")


@router.post("/api/v2/ai/directions")
def generate_direction_proposal(payload: GenerateDirectionProposalRequest, request: Request):
    denied = _ensure_write_request(request, caller_type=payload.caller_type, idempotency_key=payload.idempotency_key)
    if denied is not None:
        return denied
    service = dependencies.get_planning_api_service()
    try:
        proposal = service.generate_direction_proposal(
            work_id=payload.work_id,
            chapter_id=payload.chapter_id,
            user_instruction=payload.user_instruction,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        error_code = str(exc)
        return error_response(request, error_code=error_code, status_code=404 if error_code in {"work_not_found", "chapter_not_found"} else 400)
    return success_response(request, data=_serialize_direction_proposal(proposal))


@router.get("/api/v2/ai/directions")
def list_direction_proposals(work_id: str, request: Request, chapter_id: str = ""):
    try:
        items = dependencies.get_planning_api_service().list_direction_proposals(work_id, chapter_id=chapter_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=400)
    return success_response(request, data={"items": [_serialize_direction_proposal(item) for item in items]})


@router.get("/api/v2/ai/directions/{proposal_id}")
def get_direction_proposal(proposal_id: str, request: Request):
    try:
        proposal = dependencies.get_planning_api_service().get_direction_proposal(proposal_id)
    except ValueError:
        return error_response(request, error_code="direction_proposal_not_found", status_code=404)
    return success_response(request, data=_serialize_direction_proposal(proposal))


@router.post("/api/v2/ai/directions/{proposal_id}/select")
def select_direction(proposal_id: str, payload: SelectDirectionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_planning_api_service()
    try:
        result = service.select_direction(
            proposal_id=proposal_id,
            selected_option_id=payload.selected_option_id,
            user_id=payload.user_id,
            edited_fields=payload.edited_fields,
            edited_values=payload.edited_values,
            request_id=getattr(request.state, "request_id", ""),
            user_action=payload.user_action,
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code == "direction_proposal_not_found" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(
        request,
        data={
            "selection": result["selection"].model_dump(mode="json"),
            "proposal": _serialize_direction_proposal(result["proposal"]),
            "workflow_stage": result["workflow_stage"],
        },
    )


@router.post("/api/v2/ai/chapter-plans")
def generate_chapter_plan(payload: GenerateChapterPlanRequest, request: Request):
    denied = _ensure_write_request(request, caller_type=payload.caller_type, idempotency_key=payload.idempotency_key)
    if denied is not None:
        return denied
    service = dependencies.get_planning_api_service()
    try:
        plan = service.generate_chapter_plan(
            work_id=payload.work_id,
            chapter_id=payload.chapter_id,
            direction_proposal_id=payload.direction_proposal_id,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code == "direction_proposal_not_found" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(request, data=_serialize_chapter_plan(plan))


@router.get("/api/v2/ai/chapter-plans")
def list_chapter_plans(work_id: str, request: Request, chapter_id: str = ""):
    items = dependencies.get_planning_api_service().list_chapter_plans(work_id, chapter_id=chapter_id)
    return success_response(request, data={"items": [_serialize_chapter_plan(item) for item in items]})


@router.get("/api/v2/ai/chapter-plans/{plan_id}")
def get_chapter_plan(plan_id: str, request: Request):
    try:
        plan = dependencies.get_planning_api_service().get_chapter_plan(plan_id)
    except ValueError:
        return error_response(request, error_code="chapter_plan_not_found", status_code=404)
    return success_response(request, data=_serialize_chapter_plan(plan))


@router.post("/api/v2/ai/chapter-plans/{plan_id}/confirm")
def confirm_chapter_plan(plan_id: str, payload: ConfirmChapterPlanRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    try:
        result = dependencies.get_planning_api_service().confirm_chapter_plan(
            plan_id=plan_id,
            user_id=payload.user_id,
            edited_items=payload.edited_items,
            edited_fields=payload.edited_fields,
            user_edit_notes=payload.user_edit_notes,
            request_id=getattr(request.state, "request_id", ""),
            user_action=payload.user_action,
        )
    except ValueError:
        return error_response(request, error_code="chapter_plan_not_found", status_code=404)
    return success_response(
        request,
        data={
            "confirmation": _serialize_plan_confirmation(result["confirmation"]),
            "plan": _serialize_chapter_plan(result["plan"]),
            "writing_task": _serialize_writing_task(result["writing_task"]) if result["writing_task"] is not None else {},
            "workflow_stage": result["workflow_stage"],
        },
    )


@router.post("/api/v2/ai/chapter-plans/{plan_id}/reject")
def reject_chapter_plan(plan_id: str, payload: RejectChapterPlanRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    try:
        result = dependencies.get_planning_api_service().reject_chapter_plan(
            plan_id=plan_id,
            user_id=payload.user_id,
            user_edit_notes=payload.user_edit_notes,
            request_id=getattr(request.state, "request_id", ""),
            user_action=payload.user_action,
        )
    except ValueError:
        return error_response(request, error_code="chapter_plan_not_found", status_code=404)
    return success_response(
        request,
        data={
            "confirmation": _serialize_plan_confirmation(result["confirmation"]),
            "plan": _serialize_chapter_plan(result["plan"]),
            "workflow_stage": result["workflow_stage"],
        },
    )


@router.get("/api/v2/ai/writing-tasks")
def list_writing_tasks(work_id: str, request: Request, chapter_id: str = ""):
    items = dependencies.get_planning_api_service().list_writing_tasks(work_id, chapter_id=chapter_id)
    return success_response(request, data={"items": [_serialize_writing_task(item) for item in items]})


@router.get("/api/v2/ai/writing-tasks/{writing_task_id}")
def get_writing_task(writing_task_id: str, request: Request):
    try:
        task = dependencies.get_planning_api_service().get_writing_task(writing_task_id)
    except ValueError:
        return error_response(request, error_code="writing_task_not_found", status_code=404)
    return success_response(request, data=_serialize_writing_task(task))


@router.post("/api/v2/ai/writing-tasks/{writing_task_id}/confirm")
def confirm_writing_task(writing_task_id: str, payload: ConfirmWritingTaskRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    try:
        task = dependencies.get_planning_api_service().confirm_writing_task(
            writing_task_id=writing_task_id,
            user_id=payload.user_id,
            decision_note=payload.decision_note,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
            user_action=payload.user_action,
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code == "writing_task_not_found" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(request, data=_serialize_writing_task(task))
