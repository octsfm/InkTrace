from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.entities.ai.models import (
    AutoQueueConfig,
    AutoQueueRun,
    AutoQueueStatus,
    AutoQueueStopRecord,
    ChapterAdvanceDecision,
    MultiChapterStatus,
    PerChapterStatus,
    StopCondition,
    StopSeverity,
)


class AutoContinuationQueueService:
    """Minimal P2-04 queue orchestration on top of P2-01 multi-chapter service."""

    TERMINAL_STATUSES = {
        AutoQueueStatus.STOPPED,
        AutoQueueStatus.COMPLETED,
        AutoQueueStatus.FAILED,
        AutoQueueStatus.CANCELLED,
    }

    def __init__(
        self,
        *,
        config_repository,
        run_repository,
        multi_chapter_service,
        stop_evaluator,
        job_service,
        trace_service=None,
    ) -> None:
        self._config_repository = config_repository
        self._run_repository = run_repository
        self._multi_chapter_service = multi_chapter_service
        self._stop_evaluator = stop_evaluator
        self._job_service = job_service
        self._trace_service = trace_service

    def upsert_config(self, *, work_id: str, payload: dict[str, object]) -> AutoQueueConfig:
        current = self._config_repository.get_by_work(work_id)
        now = self._now()
        if current is None:
            base = AutoQueueConfig(
                config_id=f"aqc_{uuid.uuid4().hex[:12]}",
                work_id=work_id,
                created_at=now,
                updated_at=now,
            )
            updated = AutoQueueConfig.model_validate({**base.model_dump(), **payload, "updated_at": now})
            return self._config_repository.save(updated)
        updated = AutoQueueConfig.model_validate({**current.model_dump(), **payload, "updated_at": now})
        return self._config_repository.update(updated)

    def get_config(self, work_id: str) -> AutoQueueConfig | None:
        return self._config_repository.get_by_work(work_id)

    def start(
        self,
        config_id: str,
        work_id: str,
        start_chapter_id: str,
        user_instruction: str = "",
    ) -> AutoQueueRun:
        config = self._load_config(config_id)
        if config.work_id != work_id:
            raise ValueError("auto_queue_work_id_mismatch")
        if not bool(config.enabled):
            raise ValueError("auto_queue_disabled")
        if int(config.target_chapters or 0) <= 0:
            raise ValueError("auto_queue_target_chapters_required")
        active = self._run_repository.get_active(work_id)
        if active is not None:
            raise ValueError("auto_queue_already_running")

        run_id = f"aqr_{uuid.uuid4().hex[:12]}"
        job = self._job_service.create_job(
            job_type="auto_queue",
            work_id=work_id,
            chapter_id=start_chapter_id,
            created_by="user_action",
            idempotency_key="",
            payload={
                "run_id": run_id,
                "config_id": config.config_id,
                "work_id": work_id,
                "start_chapter_id": start_chapter_id,
            },
            steps=[
                {
                    "step_type": "run_auto_queue",
                    "step_name": "Run Auto Queue",
                }
            ],
        )
        session = self._multi_chapter_service.start(
            work_id=work_id,
            start_chapter_id=start_chapter_id,
            target_chapters=int(config.target_chapters),
            user_instruction=str(user_instruction or "").strip(),
            caller_type="user_action",
        )
        now = self._now()
        run = AutoQueueRun(
            run_id=run_id,
            job_id=str(job.job_id or ""),
            config_id=config.config_id,
            work_id=work_id,
            multi_chapter_session_id=session.session_id,
            status=self._map_session_status(session.status),
            generated_count=self._count_generated(session),
            total_word_count=0,
            consumed_tokens=0,
            current_stop_evaluation={},
            stop_record=None,
            current_candidate_story_state=dict(session.candidate_story_state or {}),
            queue_state_snapshots=list(session.queue_state_snapshots or []),
            consecutive_blocking_count=0,
            consecutive_revision_failure_count=0,
            error_code="",
            error_message="",
            request_id=str(session.request_id or ""),
            trace_id=str(session.trace_id or ""),
            created_at=now,
            updated_at=now,
            started_at=now if self._map_session_status(session.status) == AutoQueueStatus.RUNNING else "",
            stopped_at="",
            finished_at="",
        )
        saved = self._run_repository.save(run)
        return self._sync_from_session(saved, session, config=config)

    def pause(self, run_id: str) -> AutoQueueRun:
        run = self._load_run(run_id)
        session = self._multi_chapter_service.pause(run.multi_chapter_session_id)
        return self._save_from_session(run, session, forced_status=AutoQueueStatus.PAUSED)

    def resume(self, run_id: str) -> AutoQueueRun:
        run = self._load_run(run_id)
        config = self._load_config(run.config_id)
        session = self._multi_chapter_service.resume(run.multi_chapter_session_id)
        return self._sync_from_session(run, session, config=config)

    def stop(self, run_id: str, *, reason: StopCondition = StopCondition.USER_MANUAL_STOP) -> AutoQueueRun:
        run = self._load_run(run_id)
        self._multi_chapter_service.cancel(run.multi_chapter_session_id)
        now = self._now()
        stop_record = AutoQueueStopRecord(
            stop_reason=reason,
            stop_severity=StopSeverity.USER if reason == StopCondition.USER_MANUAL_STOP else StopSeverity.ABNORMAL,
            stop_context={
                "generated_count": run.generated_count,
                "multi_chapter_session_id": run.multi_chapter_session_id,
            },
            stopped_at=now,
            user_action_required=False,
            suggested_action="resume_queue" if reason == StopCondition.USER_MANUAL_STOP else "review_stop_reason",
        )
        updated = run.model_copy(
            update={
                "status": AutoQueueStatus.STOPPED,
                "stop_record": stop_record,
                "updated_at": now,
                "stopped_at": now,
                "finished_at": now,
            }
        )
        return self._run_repository.update(updated)

    def get_status(self, run_id: str) -> AutoQueueRun:
        run = self._load_run(run_id)
        if run.status in self.TERMINAL_STATUSES:
            return run
        session = self._multi_chapter_service.get_session(run.multi_chapter_session_id)
        config = self._load_config(run.config_id)
        return self._sync_from_session(run, session, config=config)

    def get_history(self, work_id: str) -> list[AutoQueueRun]:
        return self._run_repository.get_history(work_id)

    def get_active(self, work_id: str) -> AutoQueueRun | None:
        return self._run_repository.get_active(work_id)

    def recover_after_restart(self, work_id: str) -> AutoQueueRun | None:
        run = self._run_repository.get_active(work_id)
        if run is None:
            return None
        if run.status == AutoQueueStatus.PAUSED:
            return run
        if run.status == AutoQueueStatus.RUNNING:
            return self.resume(run.run_id)
        if run.status == AutoQueueStatus.WAITING_USER_DECISION:
            return run
        return run

    def run_background_step(self, run_id: str) -> AutoQueueRun:
        run = self._load_run(run_id)
        if run.status in self.TERMINAL_STATUSES or run.status == AutoQueueStatus.PAUSED:
            return run
        config = self._load_config(run.config_id)
        if run.status == AutoQueueStatus.WAITING_USER_DECISION:
            return run
        session = self._multi_chapter_service.get_session(run.multi_chapter_session_id)
        return self._sync_from_session(run, session, config=config)

    def user_confirm_continue(
        self,
        run_id: str,
        *,
        caller_type: str,
        user_action: bool,
    ) -> AutoQueueRun:
        if caller_type != "user_action" or not user_action:
            raise ValueError("P2_CALLER_FORBIDDEN")
        run = self._load_run(run_id)
        if run.status != AutoQueueStatus.WAITING_USER_DECISION:
            raise ValueError("auto_queue_not_waiting_user_decision")
        config = self._load_config(run.config_id)
        session = self._multi_chapter_service.advance_to_next_chapter(
            run.multi_chapter_session_id,
            decision=ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY,
        )
        return self._sync_from_session(run, session, config=config)

    def _load_config(self, config_id: str):
        config = self._config_repository.get_by_id(config_id)
        if config is None:
            raise ValueError("auto_queue_config_not_found")
        return config

    def _load_run(self, run_id: str) -> AutoQueueRun:
        run = self._run_repository.get_by_id(run_id)
        if run is None:
            raise ValueError("auto_queue_run_not_found")
        return run

    def _save_from_session(
        self,
        run: AutoQueueRun,
        session,
        *,
        config: AutoQueueConfig | None = None,
        forced_status: AutoQueueStatus | None = None,
    ) -> AutoQueueRun:
        status = forced_status or self._map_session_status(session.status)
        now = self._now()
        updates = {
            "status": status,
            "generated_count": self._count_generated(session),
            "total_word_count": self._derive_total_word_count(session, current_value=run.total_word_count),
            "consumed_tokens": self._derive_consumed_tokens(session, current_value=run.consumed_tokens),
            "consecutive_blocking_count": self._derive_consecutive_blocking_count(
                session,
                current_value=run.consecutive_blocking_count,
                config=config,
            ),
            "error_code": self._derive_error_code(session, current_value=run.error_code),
            "error_message": self._derive_error_message(session, current_value=run.error_message),
            "current_candidate_story_state": dict(session.candidate_story_state or {}),
            "queue_state_snapshots": list(session.queue_state_snapshots or []),
            "request_id": str(session.request_id or run.request_id),
            "trace_id": str(session.trace_id or run.trace_id),
            "updated_at": now,
        }
        if status == AutoQueueStatus.RUNNING and not run.started_at:
            updates["started_at"] = now
        if status == AutoQueueStatus.COMPLETED:
            updates["finished_at"] = now
        updated = run.model_copy(update=updates)
        return self._run_repository.update(updated)

    def _sync_from_session(
        self,
        run: AutoQueueRun,
        session,
        *,
        config: AutoQueueConfig | None = None,
    ) -> AutoQueueRun:
        status = self._map_session_status(session.status)
        if config is None:
            config = self._load_config(run.config_id)
        synced_run = self._save_from_session(run, session, config=config, forced_status=status)
        if status == AutoQueueStatus.STOPPED:
            evaluation = self._build_session_stop_evaluation(session)
            return self._mark_stopped(synced_run, evaluation, session=session)
        if status in self.TERMINAL_STATUSES:
            return synced_run
        evaluation = self._evaluate_stop_conditions(synced_run, config)
        if bool(evaluation.should_stop):
            if evaluation.severity == StopSeverity.NORMAL:
                return self._mark_completed(synced_run, evaluation)
            return self._mark_stopped(synced_run, evaluation, session=session)

        synced_run = synced_run.model_copy(
            update={
                "current_stop_evaluation": self._serialize_stop_evaluation(evaluation),
                "updated_at": self._now(),
            }
        )
        return self._run_repository.update(synced_run)

    def _evaluate_stop_conditions(self, run: AutoQueueRun, config: AutoQueueConfig):
        return self._stop_evaluator.evaluate(run, config, last_review_result=None)

    def _mark_completed(self, run: AutoQueueRun, evaluation) -> AutoQueueRun:
        now = self._now()
        stop_record = AutoQueueStopRecord(
            stop_reason=evaluation.condition,
            stop_severity=evaluation.severity,
            stop_context={
                "generated_count": run.generated_count,
                "multi_chapter_session_id": run.multi_chapter_session_id,
            },
            stopped_at=now,
            user_action_required=bool(evaluation.user_action_required),
            suggested_action=str(evaluation.suggested_action or "none"),
        )
        updated = run.model_copy(
            update={
                "status": AutoQueueStatus.COMPLETED,
                "stop_record": stop_record,
                "current_stop_evaluation": self._serialize_stop_evaluation(evaluation),
                "updated_at": now,
                "finished_at": run.finished_at or now,
            }
        )
        return self._run_repository.update(updated)

    def _mark_stopped(self, run: AutoQueueRun, evaluation, *, session=None) -> AutoQueueRun:
        now = self._now()
        stop_record = run.stop_record or AutoQueueStopRecord(
            stop_reason=evaluation.condition or StopCondition.BLOCKING_REVIEW_CONSECUTIVE,
            stop_severity=evaluation.severity or StopSeverity.ABNORMAL,
            stop_context={
                "generated_count": run.generated_count,
                "multi_chapter_session_id": run.multi_chapter_session_id,
                "blocked_reason_code": str(getattr(session, "blocked_reason_code", "") or ""),
            },
            stopped_at=now,
            user_action_required=bool(evaluation.user_action_required),
            suggested_action=str(evaluation.suggested_action or "review_stop_reason"),
        )
        updated = run.model_copy(
            update={
                "status": AutoQueueStatus.STOPPED,
                "stop_record": stop_record,
                "current_stop_evaluation": self._serialize_stop_evaluation(evaluation),
                "updated_at": now,
                "stopped_at": run.stopped_at or now,
                "finished_at": run.finished_at or now,
            }
        )
        saved = self._run_repository.update(updated)
        self._record_budget_stop_audit(saved, evaluation)
        return saved

    def _build_session_stop_evaluation(self, session):
        reason_code = str(getattr(session, "blocked_reason_code", "") or "")
        mapping = {
            "blocking_review_consecutive": (StopCondition.BLOCKING_REVIEW_CONSECUTIVE, StopSeverity.ABNORMAL, "review_conflicts"),
            "budget_exceeded": (StopCondition.BUDGET_EXCEEDED, StopSeverity.BUDGET, "adjust_budget"),
            "provider_unrecoverable": (StopCondition.PROVIDER_UNRECOVERABLE, StopSeverity.PROVIDER, "check_provider"),
            "foreshadow_premature_reveal": (StopCondition.FORESHADOW_PREMATURE_REVEAL, StopSeverity.ABNORMAL, "review_conflicts"),
            "user_manual_stop": (StopCondition.USER_MANUAL_STOP, StopSeverity.USER, "resume_queue"),
        }
        condition, severity, suggested_action = mapping.get(
            reason_code,
            (StopCondition.BLOCKING_REVIEW_CONSECUTIVE, StopSeverity.ABNORMAL, "review_conflicts"),
        )
        return type(
            "SessionStopEvaluation",
            (),
            {
                "should_stop": True,
                "condition": condition,
                "severity": severity,
                "reason": reason_code or getattr(condition, "value", str(condition)),
                "user_action_required": severity != StopSeverity.NORMAL,
                "suggested_action": suggested_action,
            },
        )()

    def _record_budget_stop_audit(self, run: AutoQueueRun, evaluation) -> None:
        if self._trace_service is None or not str(run.trace_id or "").strip():
            return
        condition = getattr(evaluation, "condition", None)
        if condition != StopCondition.BUDGET_EXCEEDED:
            return
        self._trace_service.record_audit_event(
            trace_id=str(run.trace_id or ""),
            session_id=str(run.multi_chapter_session_id or ""),
            step_id="",
            event_type="budget_stop_recorded",
            summary="auto_queue_stopped_due_to_budget_exceeded",
            payload_digest={
                "run_id": run.run_id,
                "condition": getattr(condition, "value", str(condition)),
                "generated_count": int(run.generated_count or 0),
            },
            high_risk_user_action=False,
        )

    @staticmethod
    def _map_session_status(status: MultiChapterStatus) -> AutoQueueStatus:
        mapping = {
            MultiChapterStatus.PENDING: AutoQueueStatus.PENDING,
            MultiChapterStatus.RUNNING: AutoQueueStatus.RUNNING,
            MultiChapterStatus.PAUSED: AutoQueueStatus.PAUSED,
            MultiChapterStatus.WAITING_USER_DECISION: AutoQueueStatus.WAITING_USER_DECISION,
            MultiChapterStatus.BLOCKED: AutoQueueStatus.STOPPED,
            MultiChapterStatus.COMPLETED: AutoQueueStatus.COMPLETED,
            MultiChapterStatus.PARTIAL_SUCCESS: AutoQueueStatus.STOPPED,
            MultiChapterStatus.FAILED: AutoQueueStatus.FAILED,
            MultiChapterStatus.CANCELLED: AutoQueueStatus.CANCELLED,
        }
        return mapping[MultiChapterStatus(status)]

    @staticmethod
    def _count_generated(session) -> int:
        generated_statuses = {
            PerChapterStatus.READY,
            PerChapterStatus.BLOCKED,
            PerChapterStatus.APPLIED,
            PerChapterStatus.SKIPPED,
        }
        count = 0
        for item in list(getattr(session, "per_chapter_status", []) or []):
            if PerChapterStatus(item.status) in generated_statuses:
                count += 1
        return count

    @staticmethod
    def _derive_total_word_count(session, *, current_value: int = 0) -> int:
        total = 0
        seen_keys: set[str] = set()
        for snapshot in list(getattr(session, "queue_state_snapshots", []) or []):
            if not isinstance(snapshot, dict):
                continue
            word_count = int(snapshot.get("word_count", 0) or 0)
            if word_count <= 0:
                continue
            key = str(
                snapshot.get("chapter_id")
                or snapshot.get("candidate_draft_id")
                or snapshot.get("chapter_index")
                or f"snapshot:{len(seen_keys)}"
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            total += word_count

        candidate_story_state = getattr(session, "candidate_story_state", {}) or {}
        if isinstance(candidate_story_state, dict):
            latest_word_count = int(candidate_story_state.get("word_count", 0) or 0)
            latest_key = str(
                candidate_story_state.get("latest_chapter_id")
                or candidate_story_state.get("latest_candidate_draft_id")
                or ""
            )
            if latest_word_count > 0 and latest_key and latest_key not in seen_keys:
                total += latest_word_count

        if total > 0:
            return total
        return int(current_value or 0)

    @staticmethod
    def _derive_consumed_tokens(session, *, current_value: int = 0) -> int:
        metadata = getattr(session, "metadata", {}) or {}
        if isinstance(metadata, dict):
            direct = int(metadata.get("consumed_tokens", 0) or 0)
            if direct > 0:
                return direct
            token_usage = metadata.get("token_usage", {}) or {}
            if isinstance(token_usage, dict):
                total_tokens = int(token_usage.get("total_tokens", 0) or 0)
                if total_tokens > 0:
                    return total_tokens
        return int(current_value or 0)

    @staticmethod
    def _derive_consecutive_blocking_count(session, *, current_value: int = 0, config: AutoQueueConfig | None = None) -> int:
        reason_code = str(getattr(session, "blocked_reason_code", "") or "")
        session_status = MultiChapterStatus(getattr(session, "status"))
        if session_status == MultiChapterStatus.BLOCKED and reason_code == "blocking_review_consecutive":
            threshold = 1
            if config is not None:
                threshold = max(int(getattr(config, "max_consecutive_blocking", 2) or 2), 1)
            return max(int(current_value or 0), threshold)
        return 0

    @staticmethod
    def _derive_error_code(session, *, current_value: str = "") -> str:
        error_code = str(getattr(session, "error_code", "") or "")
        if error_code:
            return error_code
        blocked_reason_code = str(getattr(session, "blocked_reason_code", "") or "")
        if blocked_reason_code:
            return blocked_reason_code
        return str(current_value or "")

    @staticmethod
    def _derive_error_message(session, *, current_value: str = "") -> str:
        error_message = str(getattr(session, "error_message", "") or "")
        if error_message:
            return error_message
        return str(current_value or "")

    @staticmethod
    def _serialize_stop_evaluation(evaluation) -> dict[str, object]:
        return {
            "should_stop": bool(getattr(evaluation, "should_stop", False)),
            "condition": getattr(getattr(evaluation, "condition", None), "value", getattr(evaluation, "condition", None)),
            "severity": getattr(getattr(evaluation, "severity", None), "value", getattr(evaluation, "severity", None)),
            "reason": str(getattr(evaluation, "reason", "") or ""),
            "user_action_required": bool(getattr(evaluation, "user_action_required", False)),
            "suggested_action": str(getattr(evaluation, "suggested_action", "") or ""),
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
