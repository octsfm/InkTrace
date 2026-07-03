from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from application.services.ai.auto_queue_service import AutoContinuationQueueService
from application.services.ai.stop_condition_evaluator import StopConditionEvaluator
from domain.entities.ai.models import (
    AutoQueueConfig,
    AutoQueueMode,
    AutoQueueRun,
    AutoQueueStatus,
    ChapterAdvanceDecision,
    ChapterStatusEntry,
    MultiChapterSession,
    MultiChapterStatus,
    PerChapterStatus,
    StopCondition,
)
from domain.repositories.ai.auto_queue_config_repository import AutoQueueConfigRepository
from domain.repositories.ai.auto_queue_run_repository import AutoQueueRunRepository
from presentation.api import dependencies
from presentation.api.app import app
from presentation.api.routers.v2.ai import auto_queues


def _now() -> str:
    return datetime.now(UTC).isoformat()


class _InMemoryAutoQueueConfigRepository(AutoQueueConfigRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, AutoQueueConfig] = {}
        self._by_work: dict[str, AutoQueueConfig] = {}

    def save(self, config: AutoQueueConfig) -> AutoQueueConfig:
        self._by_id[config.config_id] = config
        self._by_work[config.work_id] = config
        return config

    def get_by_work(self, work_id: str) -> AutoQueueConfig | None:
        return self._by_work.get(work_id)

    def get_by_id(self, config_id: str) -> AutoQueueConfig | None:
        return self._by_id.get(config_id)

    def update(self, config: AutoQueueConfig) -> AutoQueueConfig:
        return self.save(config)


class _InMemoryAutoQueueRunRepository(AutoQueueRunRepository):
    def __init__(self) -> None:
        self._items: dict[str, AutoQueueRun] = {}

    def save(self, run: AutoQueueRun) -> AutoQueueRun:
        self._items[run.run_id] = run
        return run

    def get_by_id(self, run_id: str) -> AutoQueueRun | None:
        return self._items.get(run_id)

    def get_active(self, work_id: str) -> AutoQueueRun | None:
        for run in self._items.values():
            if run.work_id == work_id and run.status not in {
                AutoQueueStatus.STOPPED,
                AutoQueueStatus.COMPLETED,
                AutoQueueStatus.FAILED,
                AutoQueueStatus.CANCELLED,
            }:
                return run
        return None

    def get_history(self, work_id: str, limit: int = 20) -> list[AutoQueueRun]:
        return [item for item in self._items.values() if item.work_id == work_id][:limit]

    def update(self, run: AutoQueueRun) -> AutoQueueRun:
        return self.save(run)


class _StubMultiChapterService:
    def __init__(self, *, session: MultiChapterSession) -> None:
        self.get_session_result = session
        self.resume_result = session
        self.advance_result = session
        self.get_session_calls: list[str] = []
        self.resume_calls: list[str] = []
        self.advance_calls: list[tuple[str, ChapterAdvanceDecision]] = []

    def get_session(self, session_id: str) -> MultiChapterSession:
        self.get_session_calls.append(session_id)
        return self.get_session_result

    def resume(self, session_id: str) -> MultiChapterSession:
        self.resume_calls.append(session_id)
        return self.resume_result

    def advance_to_next_chapter(
        self,
        session_id: str,
        *,
        decision: ChapterAdvanceDecision,
    ) -> MultiChapterSession:
        self.advance_calls.append((session_id, decision))
        return self.advance_result


class _StubJobService:
    def create_job(self, **kwargs):
        _ = kwargs
        return type("_Job", (), {"job_id": "job_aq_001"})()


class _StubTraceService:
    def __init__(self) -> None:
        self.audit_events: list[dict[str, object]] = []

    def record_audit_event(
        self,
        *,
        trace_id: str,
        session_id: str,
        step_id: str,
        event_type: str,
        summary: str,
        payload_digest: dict[str, object] | None = None,
        high_risk_user_action: bool = False,
    ):
        event = {
            "trace_id": trace_id,
            "session_id": session_id,
            "step_id": step_id,
            "event_type": event_type,
            "summary": summary,
            "payload_digest": dict(payload_digest or {}),
            "high_risk_user_action": high_risk_user_action,
        }
        self.audit_events.append(event)
        return event


class _StubPlotArcRepository:
    def get_active_sequence_arc(self, work_id: str, current_index: int):
        _ = work_id, current_index
        return None


class _StubBudgetService:
    def __init__(self, *, exceeded: bool, suggested_action: str = "adjust_budget") -> None:
        self.exceeded = exceeded
        self.suggested_action = suggested_action
        self.calls: list[str] = []

    def check_auto_queue_budget(self, run_id: str):
        self.calls.append(run_id)

        class _Result:
            def __init__(self, exceeded: bool, suggested_action: str) -> None:
                self.exceeded = exceeded
                self.suggested_action = suggested_action

        return _Result(self.exceeded, self.suggested_action)


class _FakeAutoQueueService:
    def __init__(self) -> None:
        self.configs: dict[str, AutoQueueConfig] = {}
        self.runs: dict[str, AutoQueueRun] = {}
        self.recover_results: dict[str, AutoQueueRun | None] = {}
        self.recover_calls: list[str] = []
        self.background_step_calls: list[str] = []

    def get_config(self, work_id: str) -> AutoQueueConfig | None:
        return self.configs.get(work_id)

    def start(self, config_id: str, work_id: str, start_chapter_id: str) -> AutoQueueRun:
        _ = config_id, start_chapter_id
        return self.runs[work_id]

    def user_confirm_continue(self, run_id: str) -> AutoQueueRun:
        return self.runs[run_id].model_copy(update={"status": AutoQueueStatus.RUNNING, "updated_at": _now()})

    def recover_after_restart(self, work_id: str) -> AutoQueueRun | None:
        self.recover_calls.append(work_id)
        return self.recover_results.get(work_id)

    def run_background_step(self, run_id: str) -> AutoQueueRun:
        self.background_step_calls.append(run_id)
        return self.runs[run_id]


class _FakeJobStep:
    def __init__(self, step_id: str = "step_aq_001") -> None:
        self.step_id = step_id


class _FakeAIJob:
    def __init__(self, status: str) -> None:
        self.status = status


class _FakeAIJobService:
    def __init__(self) -> None:
        self.job_statuses: dict[str, str] = {}
        self.completed_jobs: list[tuple[str, dict[str, object], str]] = []

    def start_job(self, job_id: str):
        self.job_statuses[job_id] = "running"
        return None

    def get_job(self, job_id: str):
        return _FakeAIJob(self.job_statuses.get(job_id, "paused"))

    def get_job_steps(self, job_id: str):
        _ = job_id
        return [_FakeJobStep()]

    def mark_step_running(self, job_id: str, step_id: str):
        _ = job_id, step_id
        return None

    def mark_step_completed(self, job_id: str, step_id: str, summary: str = "", *, warning_count: int = 0, status_reason: str = ""):
        _ = job_id, step_id, summary, warning_count, status_reason
        return None

    def pause_job(self, job_id: str, *, reason: str):
        _ = job_id, reason
        return None

    def cancel_job(self, job_id: str, *, reason: str):
        _ = job_id, reason
        self.job_statuses[job_id] = "cancelled"
        return None

    def mark_job_completed(self, job_id: str, *, result_summary: dict[str, object], result_ref: str = ""):
        self.completed_jobs.append((job_id, dict(result_summary), result_ref))
        self.job_statuses[job_id] = "completed"
        return None

    def mark_step_failed(self, job_id: str, step_id: str, *, error_code: str, error_message: str, warning_count: int = 0):
        _ = job_id, step_id, error_code, error_message, warning_count
        return None

    def mark_job_failed(self, job_id: str, *, error_code: str, error_message: str):
        _ = job_id, error_code, error_message
        self.job_statuses[job_id] = "failed"
        return None


class _FakeWork:
    def __init__(self, work_id: str) -> None:
        self.id = work_id


class _FakeWorkService:
    def __init__(self, work_ids: list[str]) -> None:
        self._items = [_FakeWork(work_id) for work_id in work_ids]

    def list_works(self):
        return list(self._items)


def _build_stop_evaluator(*, budget_service=None) -> StopConditionEvaluator:
    return StopConditionEvaluator(
        plot_arc_repository=_StubPlotArcRepository(),
        budget_service=budget_service,
    )


def _build_config(**updates) -> AutoQueueConfig:
    payload = {
        "config_id": "aqc_001",
        "work_id": "work_001",
        "queue_mode": AutoQueueMode.SAFE,
        "target_chapters": 3,
        "target_word_count": 0,
        "stop_at_sequence_end": True,
        "stop_on_blocking_review": True,
        "max_consecutive_blocking": 2,
        "stop_on_budget_exceeded": True,
        "max_consecutive_revision_failures": 3,
        "stop_on_foreshadow_premature": True,
        "budget_limit_tokens": 200000,
        "enabled": True,
        "created_at": "2026-06-24T12:00:00Z",
        "updated_at": "2026-06-24T12:00:00Z",
    }
    payload.update(updates)
    return AutoQueueConfig(**payload)


def _build_session(
    *,
    status: MultiChapterStatus,
    current_index: int,
    target_chapters: int = 3,
) -> MultiChapterSession:
    per_chapter_status = []
    for chapter_index in range(1, target_chapters + 1):
        chapter_status = PerChapterStatus.READY if chapter_index <= current_index else PerChapterStatus.PENDING
        per_chapter_status.append(
            ChapterStatusEntry(
                chapter_index=chapter_index,
                chapter_id=f"chapter_{chapter_index:03d}",
                status=chapter_status,
            )
        )
    return MultiChapterSession(
        session_id="mcs_001",
        work_id="work_001",
        start_chapter_id="chapter_start",
        target_chapters=target_chapters,
        current_index=current_index,
        status=status,
        per_chapter_status=per_chapter_status,
        request_id="job_mc_001",
        trace_id="trace_mc_001",
        created_by="user_action",
        created_at="2026-06-24T12:00:00Z",
        updated_at="2026-06-24T12:00:00Z",
        started_at="2026-06-24T12:01:00Z",
        metadata={"job_id": "job_mc_001"},
    )


def _build_run(**updates) -> AutoQueueRun:
    payload = {
        "run_id": "aqr_001",
        "job_id": "job_aq_001",
        "config_id": "aqc_001",
        "work_id": "work_001",
        "multi_chapter_session_id": "mcs_001",
        "status": AutoQueueStatus.RUNNING,
        "queue_mode": AutoQueueMode.SAFE,
        "generated_count": 1,
        "total_word_count": 3200,
        "consumed_tokens": 60000,
        "current_stop_evaluation": {},
        "stop_record": None,
        "current_candidate_story_state": {},
        "queue_state_snapshots": [],
        "consecutive_blocking_count": 0,
        "consecutive_revision_failure_count": 0,
        "error_code": "",
        "error_message": "",
        "request_id": "req_001",
        "trace_id": "trace_001",
        "created_at": "2026-06-24T12:00:00Z",
        "updated_at": "2026-06-24T12:00:00Z",
        "started_at": "2026-06-24T12:01:00Z",
        "stopped_at": "",
        "finished_at": "",
    }
    payload.update(updates)
    return AutoQueueRun(**payload)


def test_p2_auto_queue_gate_confirm_continue_rejects_non_user_action_caller(monkeypatch) -> None:
    fake_service = _FakeAutoQueueService()
    fake_service.runs["aqr_001"] = _build_run(run_id="aqr_001", status=AutoQueueStatus.WAITING_USER_DECISION)
    monkeypatch.setenv("INKTRACE_P2_ENABLE_AUTO_QUEUE", "1")
    monkeypatch.setattr(dependencies, "get_auto_queue_service", lambda: fake_service, raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/auto-queues/aqr_001/confirm-continue",
        json={"caller_type": "agent", "user_action": True, "idempotency_key": "aq-gate-confirm-001"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "P2_CALLER_FORBIDDEN"


def test_p2_auto_queue_gate_start_rejects_zero_target_chapters_with_422(monkeypatch) -> None:
    fake_service = _FakeAutoQueueService()
    fake_service.configs["work_001"] = _build_config(
        work_id="work_001",
        target_chapters=0,
        target_word_count=5000,
        stop_at_sequence_end=True,
        budget_limit_tokens=200000,
    )
    fake_service.runs["work_001"] = _build_run(work_id="work_001")
    monkeypatch.setenv("INKTRACE_P2_ENABLE_AUTO_QUEUE", "1")
    monkeypatch.setattr(dependencies, "get_auto_queue_service", lambda: fake_service, raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/auto-queues/start",
        json={"work_id": "work_001", "start_chapter_id": "chapter_001"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["error_code"] == "auto_queue_target_chapters_required"


def test_p2_auto_queue_gate_recover_after_restart_auto_advances_continuous_waiting_run() -> None:
    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=3, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.CONTINUOUS, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(
        session=_build_session(status=MultiChapterStatus.WAITING_USER_DECISION, current_index=1, target_chapters=3)
    )
    multi_chapter_service.advance_result = _build_session(
        status=MultiChapterStatus.RUNNING,
        current_index=2,
        target_chapters=3,
    )
    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    recovered = service.recover_after_restart("work_001")

    assert recovered is not None
    assert recovered.status == AutoQueueStatus.RUNNING
    assert recovered.generated_count == 2
    assert multi_chapter_service.get_session_calls == ["mcs_001"]
    assert multi_chapter_service.advance_calls == [("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY)]


def test_p2_auto_queue_gate_blocking_stop_syncs_count_and_error_details() -> None:
    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, max_consecutive_blocking=2))
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING, queue_mode=AutoQueueMode.CONTINUOUS))
    multi_chapter_service = _StubMultiChapterService(
        session=_build_session(status=MultiChapterStatus.BLOCKED, current_index=1, target_chapters=3).model_copy(
            update={
                "blocked_reason_code": "blocking_review_consecutive",
                "error_code": "blocking_review_consecutive",
                "error_message": "review blocked by consecutive conflicts",
            }
        )
    )
    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    refreshed = service.get_status("aqr_001")

    assert refreshed.status == AutoQueueStatus.STOPPED
    assert refreshed.stop_record is not None
    assert refreshed.stop_record.stop_reason == StopCondition.BLOCKING_REVIEW_CONSECUTIVE
    assert refreshed.consecutive_blocking_count == 2
    assert refreshed.error_code == "blocking_review_consecutive"
    assert refreshed.error_message == "review blocked by consecutive conflicts"


def test_p2_auto_queue_gate_recover_after_restart_skips_terminal_reconvergence_when_ai_job_already_terminal(monkeypatch) -> None:
    fake_service = _FakeAutoQueueService()
    completed_run = _build_run(
        run_id="aqr_010",
        job_id="job_aq_010",
        work_id="work_010",
        status=AutoQueueStatus.COMPLETED,
        queue_mode=AutoQueueMode.CONTINUOUS,
    )
    fake_service.recover_results["work_010"] = completed_run
    fake_service.runs["aqr_010"] = completed_run
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_auto_queue_service", lambda: fake_service, raising=False)
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    monkeypatch.setattr(dependencies, "get_work_service", lambda: _FakeWorkService(["work_010"]), raising=False)
    auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS.clear()

    class _FakeThread:
        def __init__(self, *, target, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            self.target(*self.args, **self.kwargs)

    monkeypatch.setattr(auto_queues.threading, "Thread", _FakeThread)

    first_recovered = auto_queues.recover_auto_queue_runs_after_restart()
    second_recovered = auto_queues.recover_auto_queue_runs_after_restart()

    assert first_recovered == ["aqr_010"]
    assert second_recovered == ["aqr_010"]
    assert fake_job_service.completed_jobs == [
        (
            "job_aq_010",
            {
                "run_id": "aqr_010",
                "status": "completed",
                "queue_mode": "continuous",
            },
            "auto_queue_run:aqr_010",
        )
    ]


def test_p2_auto_queue_gate_budget_audit_only_records_safe_digest_fields() -> None:
    budget_service = _StubBudgetService(exceeded=True, suggested_action="adjust_budget")
    trace_service = _StubTraceService()
    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(
        _build_config(
            queue_mode=AutoQueueMode.CONTINUOUS,
            target_chapters=4,
            stop_at_sequence_end=False,
            stop_on_budget_exceeded=True,
        )
    )
    run_repo.save(
        _build_run(
            status=AutoQueueStatus.PAUSED,
            queue_mode=AutoQueueMode.CONTINUOUS,
            generated_count=1,
            error_message="FULL_PROVIDER_ERROR: secret quota details",
            current_candidate_story_state={
                "chapter_text": "FULL OFFICIAL BODY CONTENT",
                "context_pack": "FULL CONTEXTPACK CONTENT",
                "candidate_draft": "FULL CANDIDATE DRAFT",
                "prompt": "FULL PROMPT CONTENT",
            },
        )
    )
    multi_chapter_service = _StubMultiChapterService(
        session=_build_session(status=MultiChapterStatus.RUNNING, current_index=2, target_chapters=4)
    )
    multi_chapter_service.resume_result = _build_session(
        status=MultiChapterStatus.RUNNING,
        current_index=2,
        target_chapters=4,
    )
    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(budget_service=budget_service),
        job_service=_StubJobService(),
        trace_service=trace_service,
    )

    service.resume("aqr_001")

    assert len(trace_service.audit_events) == 1
    event = trace_service.audit_events[0]
    assert event["event_type"] == "budget_stop_recorded"
    assert event["summary"] == "auto_queue_stopped_due_to_budget_exceeded"
    assert event["payload_digest"] == {
        "run_id": "aqr_001",
        "condition": StopCondition.BUDGET_EXCEEDED.value,
        "generated_count": 2,
    }
    assert "FULL OFFICIAL BODY CONTENT" not in str(event)
    assert "FULL CONTEXTPACK CONTENT" not in str(event)
    assert "FULL CANDIDATE DRAFT" not in str(event)
    assert "FULL PROMPT CONTENT" not in str(event)
    assert "FULL_PROVIDER_ERROR: secret quota details" not in str(event)
