from __future__ import annotations

import threading

from fastapi import APIRouter, Request
from pydantic import Field

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import SessionActionRequest, V2AIBaseModel

router = APIRouter(prefix="/api/v2/ai/auto-queues", tags=["v2-ai-auto-queues"])
_ACTIVE_AUTO_QUEUE_RUNNERS: set[str] = set()
_ACTIVE_AUTO_QUEUE_RUNNERS_LOCK = threading.Lock()
_TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled"}


class AutoQueueConfigUpsertRequest(V2AIBaseModel):
    work_id: str
    target_chapters: int | None = None
    target_word_count: int | None = None
    stop_at_sequence_end: bool | None = None
    stop_on_blocking_review: bool | None = None
    max_consecutive_blocking: int | None = None
    stop_on_budget_exceeded: bool | None = None
    stop_on_foreshadow_premature: bool | None = None
    max_consecutive_revision_failures: int | None = None
    budget_limit_tokens: int | None = None
    enabled: bool | None = None


class AutoQueueStartRequest(V2AIBaseModel):
    work_id: str
    start_chapter_id: str
    user_instruction: str = Field(default="", max_length=60)


def _ensure_gate_request(request: Request, *, caller_type: str, user_action: bool, idempotency_key: str):
    if caller_type != "user_action":
        return error_response(request, error_code="P2_CALLER_FORBIDDEN", status_code=403)
    if not user_action:
        return error_response(request, error_code="action_not_allowed", status_code=403)
    if not str(idempotency_key or "").strip():
        return error_response(request, error_code="idempotency_key_required", status_code=400)
    return None


def _serialize_config(config) -> dict[str, object]:
    return {
        "config_id": config.config_id,
        "work_id": config.work_id,
        "target_chapters": config.target_chapters,
        "target_word_count": config.target_word_count,
        "stop_at_sequence_end": config.stop_at_sequence_end,
        "stop_on_blocking_review": config.stop_on_blocking_review,
        "max_consecutive_blocking": config.max_consecutive_blocking,
        "stop_on_budget_exceeded": config.stop_on_budget_exceeded,
        "stop_on_foreshadow_premature": config.stop_on_foreshadow_premature,
        "max_consecutive_revision_failures": config.max_consecutive_revision_failures,
        "budget_limit_tokens": config.budget_limit_tokens,
        "enabled": config.enabled,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


def _serialize_stop_record(stop_record) -> dict[str, object] | None:
    if stop_record is None:
        return None
    return {
        "stop_reason": getattr(stop_record.stop_reason, "value", stop_record.stop_reason),
        "stop_severity": getattr(stop_record.stop_severity, "value", stop_record.stop_severity),
        "stop_context": dict(stop_record.stop_context or {}),
        "stopped_at": stop_record.stopped_at,
        "user_action_required": stop_record.user_action_required,
        "suggested_action": stop_record.suggested_action,
    }


def _serialize_run(run) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "job_id": getattr(run, "job_id", ""),
        "config_id": run.config_id,
        "work_id": run.work_id,
        "multi_chapter_session_id": run.multi_chapter_session_id,
        "status": getattr(run.status, "value", run.status),
        "generated_count": run.generated_count,
        "total_word_count": run.total_word_count,
        "consumed_tokens": run.consumed_tokens,
        "current_stop_evaluation": dict(run.current_stop_evaluation or {}),
        "stop_record": _serialize_stop_record(run.stop_record),
        "current_candidate_story_state": dict(run.current_candidate_story_state or {}),
        "queue_state_snapshots": list(run.queue_state_snapshots or []),
        "consecutive_blocking_count": run.consecutive_blocking_count,
        "consecutive_revision_failure_count": run.consecutive_revision_failure_count,
        "error_code": run.error_code,
        "error_message": run.error_message,
        "request_id": run.request_id,
        "trace_id": run.trace_id,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "started_at": run.started_at,
        "stopped_at": run.stopped_at,
        "finished_at": run.finished_at,
    }


def _validate_start_config(config) -> str | None:
    if int(getattr(config, "target_chapters", 0) or 0) <= 0:
        return "auto_queue_target_chapters_required"
    return None


def _spawn_auto_queue_runner(run, *, allow_terminal: bool = False) -> None:
    job_id = str(getattr(run, "job_id", "") or "")
    run_id = str(getattr(run, "run_id", "") or "")
    status = str(getattr(getattr(run, "status", ""), "value", getattr(run, "status", "")) or "")
    skip_job_start = allow_terminal and status in {"completed", "stopped", "cancelled", "failed"}
    should_spawn = status == "running" or (allow_terminal and status in {"completed", "stopped", "cancelled", "failed"})
    if not job_id or not run_id or not should_spawn:
        return
    if skip_job_start:
        try:
            job_service = dependencies.get_ai_job_service()
            current_job = getattr(job_service, "get_job", lambda _job_id: None)(job_id)
            current_status = str(getattr(getattr(current_job, "status", ""), "value", getattr(current_job, "status", "")) or "")
            if current_status in _TERMINAL_JOB_STATUSES:
                return
        except Exception:
            pass
    with _ACTIVE_AUTO_QUEUE_RUNNERS_LOCK:
        if run_id in _ACTIVE_AUTO_QUEUE_RUNNERS:
            return
        _ACTIVE_AUTO_QUEUE_RUNNERS.add(run_id)
    thread_kwargs = {"skip_job_start": True} if skip_job_start else {}
    threading.Thread(
        target=_run_auto_queue_async,
        args=(job_id, run_id),
        kwargs=thread_kwargs,
        daemon=True,
    ).start()


def recover_auto_queue_runs_after_restart() -> list[str]:
    work_service = dependencies.get_work_service()
    service = dependencies.get_auto_queue_service()
    recovered_run_ids: list[str] = []
    for work in work_service.list_works():
        run = service.recover_after_restart(str(getattr(work, "id", "") or ""))
        if run is None:
            continue
        recovered_run_ids.append(str(getattr(run, "run_id", "") or ""))
        _spawn_auto_queue_runner(run, allow_terminal=True)
    return recovered_run_ids


def _run_auto_queue_async(job_id: str, run_id: str, *, skip_job_start: bool = False) -> None:
    job_service = dependencies.get_ai_job_service()
    service = dependencies.get_auto_queue_service()
    try:
        if not skip_job_start:
            job_service.start_job(job_id)
        step = job_service.get_job_steps(job_id)[0]
        if not skip_job_start:
            job_service.mark_step_running(job_id, step.step_id)
        last_run = None
        for _ in range(20):
            run = service.run_background_step(run_id)
            last_run = run
            status = getattr(run.status, "value", run.status)
            if status == "waiting_user_decision":
                job_service.mark_step_completed(job_id, step.step_id, summary=f"run:{run.run_id}:{status}")
                job_service.pause_job(job_id, reason="waiting_user_decision")
                return
            if status in {"paused"}:
                job_service.mark_step_completed(job_id, step.step_id, summary=f"run:{run.run_id}:{status}")
                job_service.pause_job(job_id, reason="user_paused")
                return
            if status == "cancelled":
                job_service.cancel_job(job_id, reason="auto_queue_cancelled")
                return
            if status in {"completed", "stopped"}:
                result_summary = {
                    "run_id": run.run_id,
                    "status": status,
                }
                stop_record = getattr(run, "stop_record", None)
                stop_reason = getattr(getattr(stop_record, "stop_reason", None), "value", getattr(stop_record, "stop_reason", None))
                if stop_reason:
                    result_summary["stop_reason"] = stop_reason
                job_service.mark_step_completed(job_id, step.step_id, summary=f"run:{run.run_id}:{status}")
                job_service.mark_job_completed(
                    job_id,
                    result_summary=result_summary,
                    result_ref=f"auto_queue_run:{run.run_id}",
                )
                return
            if status in {"failed"}:
                error_code = str(getattr(run, "error_code", "") or "auto_queue_run_failed")
                error_message = str(
                    getattr(run, "error_message", "") or f"auto_queue_terminal_failed:{run.run_id}:{status}"
                )
                job_service.mark_step_failed(
                    job_id,
                    step.step_id,
                    error_code=error_code,
                    error_message=error_message,
                )
                job_service.mark_job_failed(
                    job_id,
                    error_code=error_code,
                    error_message=error_message,
                )
                return
        raise RuntimeError(f"auto_queue_runner_iteration_exhausted:{getattr(last_run, 'run_id', run_id)}")
    except Exception as exc:
        try:
            steps = job_service.get_job_steps(job_id)
            if steps:
                job_service.mark_step_failed(
                    job_id,
                    steps[0].step_id,
                    error_code="auto_queue_run_failed",
                    error_message=str(exc),
                )
        except Exception:
            pass
        try:
            job_service.mark_job_failed(
                job_id,
                error_code="auto_queue_run_failed",
                error_message=str(exc),
            )
        except Exception:
            pass
    finally:
        with _ACTIVE_AUTO_QUEUE_RUNNERS_LOCK:
            _ACTIVE_AUTO_QUEUE_RUNNERS.discard(run_id)


@router.put("/config")
def upsert_auto_queue_config(payload: AutoQueueConfigUpsertRequest, request: Request):
    service = dependencies.get_auto_queue_service()
    config = service.upsert_config(work_id=payload.work_id, payload=payload.model_dump(exclude={"work_id"}, exclude_none=True))
    return success_response(request, data={"config": _serialize_config(config)})


@router.get("/config/{work_id}")
def get_auto_queue_config(work_id: str, request: Request):
    service = dependencies.get_auto_queue_service()
    config = service.get_config(work_id)
    return success_response(request, data={"config": _serialize_config(config) if config is not None else None})


@router.post("/start", status_code=202)
def start_auto_queue(payload: AutoQueueStartRequest, request: Request):
    service = dependencies.get_auto_queue_service()
    config = service.get_config(payload.work_id)
    if config is None:
        return error_response(request, error_code="auto_queue_config_not_found", status_code=404)
    invalid_error = _validate_start_config(config)
    if invalid_error is not None:
        return error_response(request, error_code=invalid_error, status_code=422)
    try:
        run = service.start(
            config.config_id,
            payload.work_id,
            payload.start_chapter_id,
            user_instruction=payload.user_instruction.strip(),
        )
    except ValueError as exc:
        error_code = str(exc)
        if error_code == "auto_queue_config_not_found":
            status_code = 404
        elif error_code == "auto_queue_already_running":
            status_code = 409
        elif error_code == "auto_queue_target_chapters_required":
            status_code = 422
        else:
            status_code = 400
        return error_response(request, error_code=error_code, status_code=status_code)
    _spawn_auto_queue_runner(run)
    return success_response(
        request,
        data={
            "run_id": run.run_id,
            "job_id": getattr(run, "job_id", ""),
            "status": getattr(run.status, "value", run.status),
        },
    )


@router.get("/{run_id}/status")
def get_auto_queue_status(run_id: str, request: Request):
    service = dependencies.get_auto_queue_service()
    try:
        run = service.get_status(run_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"run": _serialize_run(run)})


@router.post("/{run_id}/pause")
def pause_auto_queue(run_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_auto_queue_service()
    try:
        run = service.pause(run_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"run": _serialize_run(run)})


@router.post("/{run_id}/resume")
def resume_auto_queue(run_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_auto_queue_service()
    try:
        run = service.resume(run_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    _spawn_auto_queue_runner(run)
    return success_response(request, data={"run": _serialize_run(run)})


@router.post("/{run_id}/stop")
def stop_auto_queue(run_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_auto_queue_service()
    try:
        run = service.stop(run_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data={"run": _serialize_run(run)})


@router.post("/{run_id}/confirm-continue")
def confirm_continue_auto_queue(run_id: str, payload: SessionActionRequest, request: Request):
    denied = _ensure_gate_request(
        request,
        caller_type=payload.caller_type,
        user_action=payload.user_action,
        idempotency_key=payload.idempotency_key,
    )
    if denied is not None:
        return denied
    service = dependencies.get_auto_queue_service()
    try:
        run = service.user_confirm_continue(
            run_id,
            caller_type=payload.caller_type,
            user_action=payload.user_action,
        )
    except ValueError as exc:
        error_code = str(exc)
        status_code = 409 if error_code == "auto_queue_not_waiting_user_decision" else 404
        return error_response(request, error_code=error_code, status_code=status_code)
    _spawn_auto_queue_runner(run)
    return success_response(request, data={"run": _serialize_run(run)})


@router.get("/{work_id}/history")
def get_auto_queue_history(work_id: str, request: Request):
    service = dependencies.get_auto_queue_service()
    return success_response(request, data={"runs": [_serialize_run(item) for item in service.get_history(work_id)]})
