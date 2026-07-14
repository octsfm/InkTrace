from __future__ import annotations

from fastapi import APIRouter, Request

from domain.entities.ai.models import (
    ArcRef,
    ChapterBeat,
    ChapterPlan,
    ChapterPlanItem,
    DirectionOption,
    DirectionProposal,
    ForeshadowArrangementItem,
    PlanConfirmation,
    WorkflowType,
    WritingTask,
)
from presentation.api import dependencies
from presentation.api.middleware.p2_feature_flag import (
    is_outline_assist_enabled,
    outline_assist_feature_disabled_response,
)
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

_AUDIT_FAILURE_SAFE_MESSAGE = "安全记录暂时失败，本次操作没有生效，请稍后重试。"


def _ensure_gate_request(
    request: Request,
    *,
    caller_type: str,
    user_action: bool,
    idempotency_key: str,
    is_outline_assist: bool = False,
):
    if caller_type != "user_action":
        error_code = "P2_CALLER_FORBIDDEN" if is_outline_assist else "caller_type_forbidden"
        return error_response(request, error_code=error_code, status_code=403)
    if not user_action:
        error_code = "P2_USER_ACTION_REQUIRED" if is_outline_assist else "action_not_allowed"
        return error_response(request, error_code=error_code, status_code=403)
    if not str(idempotency_key or "").strip():
        error_code = "P2_IDEMPOTENCY_KEY_REQUIRED" if is_outline_assist else "idempotency_key_required"
        return error_response(request, error_code=error_code, status_code=400)
    return None


def _ensure_write_request(request: Request, *, caller_type: str, idempotency_key: str):
    if caller_type != "user_action":
        return error_response(request, error_code="caller_type_forbidden", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


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
            "chapter_plan": _serialize_chapter_plan(result["chapter_plan"]) if result.get("chapter_plan") is not None else {},
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
    except ValueError as exc:
        error_code = str(exc)
        return error_response(
            request,
            error_code=error_code,
            status_code=404 if error_code in {"chapter_plan_not_found", "chapter_plan_workflow_not_found"} else 409,
        )
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
    except ValueError as exc:
        error_code = str(exc)
        return error_response(
            request,
            error_code=error_code,
            status_code=404 if error_code in {"chapter_plan_not_found", "chapter_plan_workflow_not_found"} else 409,
        )
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
    service = dependencies.get_planning_api_service()
    try:
        is_outline_task = service.is_outline_assist_writing_task(writing_task_id)
    except ValueError as exc:
        if str(exc) != "writing_task_not_found":
            raise
        is_outline_task = False
    if is_outline_task and not is_outline_assist_enabled():
        return outline_assist_feature_disabled_response(request)
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
        is_outline_assist=is_outline_task,
    )
    if denied is not None:
        return denied
    try:
        task = service.confirm_writing_task(
            writing_task_id=writing_task_id,
            user_id=payload.user_id,
            decision_note=payload.decision_note,
            request_id=getattr(request.state, "request_id", ""),
            trace_id=request.headers.get("X-Trace-Id", "").strip(),
            user_action=payload.user_action,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        error_code = str(exc)
        if error_code == "writing_task_not_found":
            status_code = 404
        elif error_code in {"P2_IDEMPOTENCY_CONFLICT", "P2_WRITING_TASK_PREREQUISITE_MISSING", "P2_OUTLINE_TARGET_CONFLICT"}:
            status_code = 409
        elif error_code == "P2_OUTLINE_AUDIT_WRITE_FAILED":
            status_code = 503
        else:
            status_code = 400
        audit_failed = error_code == "P2_OUTLINE_AUDIT_WRITE_FAILED"
        return error_response(
            request,
            error_code=error_code,
            status_code=status_code,
            retryable=audit_failed,
            safe_message=_AUDIT_FAILURE_SAFE_MESSAGE if audit_failed else None,
        )
    return success_response(request, data=_serialize_writing_task(task))
