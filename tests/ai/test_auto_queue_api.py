from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from starlette.requests import Request

from domain.entities.ai.models import AutoQueueConfig, AutoQueueRun, AutoQueueStatus, AutoQueueStopRecord, StopCondition, StopSeverity
from presentation.api import dependencies
from presentation.api.app import app
from presentation.api.routers.v2.ai import auto_queues
from presentation.api.routers.v2.ai.schemas import SessionActionRequest


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _build_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v2/ai/auto-queues/test",
        "headers": [],
    }
    request = Request(scope)
    request.state.request_id = "req_test"
    return request


def _build_config(
    *,
    work_id: str = "work_001",
    config_id: str = "aqc_001",
) -> AutoQueueConfig:
    now = _now()
    return AutoQueueConfig(
        config_id=config_id,
        work_id=work_id,
        target_chapters=3,
        target_word_count=0,
        stop_at_sequence_end=True,
        stop_on_blocking_review=True,
        max_consecutive_blocking=2,
        stop_on_budget_exceeded=True,
        max_consecutive_revision_failures=3,
        stop_on_foreshadow_premature=True,
        budget_limit_tokens=200000,
        enabled=True,
        created_at=now,
        updated_at=now,
    )


def _build_run(
    *,
    run_id: str = "aqr_001",
    config_id: str = "aqc_001",
    work_id: str = "work_001",
    status: AutoQueueStatus = AutoQueueStatus.RUNNING,
    stop_record: AutoQueueStopRecord | None = None,
) -> AutoQueueRun:
    now = _now()
    return AutoQueueRun(
        run_id=run_id,
        job_id="job_aq_001",
        config_id=config_id,
        work_id=work_id,
        multi_chapter_session_id="mcs_001",
        status=status,
        generated_count=1,
        total_word_count=3200,
        consumed_tokens=60000,
        current_stop_evaluation={},
        stop_record=stop_record,
        current_candidate_story_state={},
        queue_state_snapshots=[],
        consecutive_blocking_count=0,
        consecutive_revision_failure_count=0,
        error_code="",
        error_message="",
        request_id="req_001",
        trace_id="trace_001",
        created_at=now,
        updated_at=now,
        started_at=now,
        stopped_at="",
        finished_at="",
    )


class _FakeAutoQueueService:
    def __init__(self) -> None:
        self.configs: dict[str, AutoQueueConfig] = {}
        self.runs: dict[str, AutoQueueRun] = {}
        self.status_sequences: dict[str, list[AutoQueueRun]] = {}
        self.recover_results: dict[str, AutoQueueRun | None] = {}
        self.start_calls: list[tuple[str, str, str, str]] = []
        self.confirm_calls: list[str] = []
        self.status_calls: list[str] = []
        self.background_step_calls: list[str] = []
        self.recover_calls: list[str] = []

    def upsert_config(self, *, work_id: str, payload: dict[str, object]) -> AutoQueueConfig:
        current = self.configs.get(work_id)
        config = _build_config(work_id=work_id, config_id=current.config_id if current else "aqc_001")
        for key, value in payload.items():
            if value is not None and hasattr(config, key):
                config = config.model_copy(update={key: value, "updated_at": _now()})
        self.configs[work_id] = config
        return config

    def get_config(self, work_id: str) -> AutoQueueConfig | None:
        return self.configs.get(work_id)

    def start(
        self,
        config_id: str,
        work_id: str,
        start_chapter_id: str,
        user_instruction: str = "",
    ) -> AutoQueueRun:
        self.start_calls.append((config_id, work_id, start_chapter_id, user_instruction))
        run = _build_run(run_id=f"aqr_{len(self.runs) + 1:03d}", config_id=config_id, work_id=work_id)
        self.runs[run.run_id] = run
        return run

    def get_status(self, run_id: str) -> AutoQueueRun:
        self.status_calls.append(run_id)
        if self.status_sequences.get(run_id):
            run = self.status_sequences[run_id].pop(0)
            self.runs[run_id] = run
            return run
        run = self.runs.get(run_id)
        if run is None:
            raise ValueError("auto_queue_run_not_found")
        return run

    def run_background_step(self, run_id: str) -> AutoQueueRun:
        self.background_step_calls.append(run_id)
        return self.get_status(run_id)

    def pause(self, run_id: str) -> AutoQueueRun:
        run = self.get_status(run_id).model_copy(update={"status": AutoQueueStatus.PAUSED, "updated_at": _now()})
        self.runs[run_id] = run
        return run

    def resume(self, run_id: str) -> AutoQueueRun:
        run = self.get_status(run_id).model_copy(update={"status": AutoQueueStatus.RUNNING, "updated_at": _now()})
        self.runs[run_id] = run
        return run

    def stop(self, run_id: str, *, reason=None) -> AutoQueueRun:
        _ = reason
        run = self.get_status(run_id).model_copy(update={"status": AutoQueueStatus.STOPPED, "updated_at": _now()})
        self.runs[run_id] = run
        return run

    def cancel(self, run_id: str) -> AutoQueueRun:
        run = self.get_status(run_id).model_copy(
            update={"status": AutoQueueStatus.CANCELLED, "resume_allowed": False, "updated_at": _now()}
        )
        self.runs[run_id] = run
        return run

    def user_confirm_continue(self, run_id: str, **_context) -> AutoQueueRun:
        self.confirm_calls.append(run_id)
        run = self.get_status(run_id).model_copy(update={"status": AutoQueueStatus.RUNNING, "updated_at": _now()})
        self.runs[run_id] = run
        return run

    def get_history(self, work_id: str) -> list[AutoQueueRun]:
        return [item for item in self.runs.values() if item.work_id == work_id]

    def recover_after_restart(self, work_id: str) -> AutoQueueRun | None:
        self.recover_calls.append(work_id)
        return self.recover_results.get(work_id)


def _install_test_dependencies(monkeypatch):
    fake_service = _FakeAutoQueueService()
    monkeypatch.setenv("INKTRACE_P2_ENABLE_AUTO_QUEUE", "1")
    monkeypatch.setattr(dependencies, "get_auto_queue_service", lambda: fake_service, raising=False)
    return fake_service


class _FakeJobStep:
    def __init__(self, step_id: str = "step_aq_001") -> None:
        self.step_id = step_id


class _FakeAIJob:
    def __init__(self, status: str = "paused") -> None:
        self.status = status


class _FakeAIJobService:
    def __init__(self) -> None:
        self.started_jobs: list[str] = []
        self.paused_jobs: list[tuple[str, str]] = []
        self.cancelled_jobs: list[tuple[str, str]] = []
        self.running_steps: list[tuple[str, str]] = []
        self.completed_steps: list[tuple[str, str, str]] = []
        self.completed_jobs: list[tuple[str, dict[str, object], str]] = []
        self.failed_steps: list[tuple[str, str, str, str]] = []
        self.failed_jobs: list[tuple[str, str, str]] = []
        self.job_statuses: dict[str, str] = {}

    def start_job(self, job_id: str):
        self.started_jobs.append(job_id)
        self.job_statuses[job_id] = "running"
        return None

    def get_job(self, job_id: str):
        return _FakeAIJob(self.job_statuses.get(job_id, "paused"))

    def get_job_steps(self, job_id: str):
        _ = job_id
        return [_FakeJobStep()]

    def mark_step_running(self, job_id: str, step_id: str):
        self.running_steps.append((job_id, step_id))
        return None

    def pause_job(self, job_id: str, *, reason: str):
        self.paused_jobs.append((job_id, reason))
        self.job_statuses[job_id] = "paused"
        return None

    def cancel_job(self, job_id: str, *, reason: str):
        self.cancelled_jobs.append((job_id, reason))
        self.job_statuses[job_id] = "cancelled"
        return None

    def mark_step_completed(self, job_id: str, step_id: str, summary: str = "", *, warning_count: int = 0, status_reason: str = ""):
        _ = warning_count, status_reason
        self.completed_steps.append((job_id, step_id, summary))
        return None

    def mark_job_completed(self, job_id: str, *, result_summary: dict[str, object], result_ref: str = ""):
        self.completed_jobs.append((job_id, dict(result_summary), result_ref))
        self.job_statuses[job_id] = "completed"
        return None

    def mark_step_failed(self, job_id: str, step_id: str, *, error_code: str, error_message: str, warning_count: int = 0):
        _ = warning_count
        self.failed_steps.append((job_id, step_id, error_code, error_message))
        return None

    def mark_job_failed(self, job_id: str, *, error_code: str, error_message: str):
        self.failed_jobs.append((job_id, error_code, error_message))
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


def test_auto_queue_config_api_upserts_and_reads_config(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    client = TestClient(app)

    put_response = client.put(
        "/api/v2/ai/auto-queues/config",
        json={
            "work_id": "work_001",
            "target_chapters": 5,
            "budget_limit_tokens": 500000,
        },
    )
    get_response = client.get("/api/v2/ai/auto-queues/config/work_001")

    assert put_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["data"]["config"]["target_chapters"] == 5
    assert fake_service.get_config("work_001") is not None


def test_auto_queue_start_and_status_api_return_run_payload(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.configs["work_001"] = _build_config(work_id="work_001", config_id="aqc_work_001")
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/auto-queues/start",
        json={
            "work_id": "work_001",
            "start_chapter_id": "chapter_001",
            "user_instruction": "让冲突更紧张",
        },
    )

    assert start_response.status_code == 202
    run_id = start_response.json()["data"]["run_id"]
    assert start_response.json()["data"]["job_id"] == "job_aq_001"
    status_response = client.get(f"/api/v2/ai/auto-queues/{run_id}/status")

    assert status_response.status_code == 200
    assert status_response.json()["data"]["run"]["run_id"] == run_id
    assert status_response.json()["data"]["run"]["job_id"] == "job_aq_001"
    assert fake_service.start_calls == [("aqc_work_001", "work_001", "chapter_001", "让冲突更紧张")]


def test_auto_queue_start_rejects_writing_intent_over_sixty_characters(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.configs["work_001"] = _build_config(work_id="work_001", config_id="aqc_work_001")
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/auto-queues/start",
        json={
            "work_id": "work_001",
            "start_chapter_id": "chapter_001",
            "user_instruction": "想" * 61,
        },
    )

    assert response.status_code == 422
    assert fake_service.start_calls == []


def test_auto_queue_start_api_returns_422_when_target_chapters_is_zero(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.configs["work_001"] = _build_config(
        work_id="work_001",
        config_id="aqc_work_001",
    ).model_copy(
        update={
            "target_chapters": 0,
            "target_word_count": 5000,
            "stop_at_sequence_end": True,
            "budget_limit_tokens": 200000,
        }
    )
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/auto-queues/start",
        json={"work_id": "work_001", "start_chapter_id": "chapter_001"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["error_code"] == "auto_queue_target_chapters_required"


def test_auto_queue_start_api_spawns_background_runner(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.configs["work_001"] = _build_config(work_id="work_001", config_id="aqc_work_001")
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    started_threads: list[dict[str, object]] = []
    auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS.clear()

    class _FakeThread:
        def __init__(self, *, target, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            started_threads.append(
                {
                    "target": self.target,
                    "args": self.args,
                    "kwargs": dict(self.kwargs),
                    "daemon": self.daemon,
                }
            )

    monkeypatch.setattr(auto_queues.threading, "Thread", _FakeThread)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/auto-queues/start",
        json={"work_id": "work_001", "start_chapter_id": "chapter_001"},
    )

    assert response.status_code == 202
    assert started_threads == [
        {
            "target": auto_queues._run_auto_queue_async,
            "args": ("job_aq_001", response.json()["data"]["run_id"]),
            "kwargs": {},
            "daemon": True,
        }
    ]


def test_spawn_auto_queue_runner_skips_duplicate_run_id(monkeypatch) -> None:
    started_threads: list[dict[str, object]] = []

    class _FakeThread:
        def __init__(self, *, target, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            started_threads.append(
                {
                    "target": self.target,
                    "args": self.args,
                    "kwargs": dict(self.kwargs),
                    "daemon": self.daemon,
                }
            )

    monkeypatch.setattr(auto_queues.threading, "Thread", _FakeThread)
    auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS.clear()
    run = _build_run(run_id="aqr_001", status=AutoQueueStatus.RUNNING)

    auto_queues._spawn_auto_queue_runner(run)
    auto_queues._spawn_auto_queue_runner(run)

    assert started_threads == [
        {
            "target": auto_queues._run_auto_queue_async,
            "args": ("job_aq_001", "aqr_001"),
            "kwargs": {},
            "daemon": True,
        }
    ]


def test_run_auto_queue_async_releases_runner_slot_after_exit(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.runs["aqr_001"] = _build_run(run_id="aqr_001", status=AutoQueueStatus.COMPLETED)
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS.clear()
    auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS.add("aqr_001")

    auto_queues._run_auto_queue_async("job_aq_001", "aqr_001")

    assert "aqr_001" not in auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS


def test_auto_queue_resume_api_spawns_background_runner_for_non_terminal_run(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.runs["aqr_001"] = _build_run(run_id="aqr_001", status=AutoQueueStatus.PAUSED)
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    started_threads: list[dict[str, object]] = []
    auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS.clear()

    class _FakeThread:
        def __init__(self, *, target, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            started_threads.append(
                {
                    "target": self.target,
                    "args": self.args,
                    "kwargs": dict(self.kwargs),
                    "daemon": self.daemon,
                }
            )

    monkeypatch.setattr(auto_queues.threading, "Thread", _FakeThread)
    response = auto_queues.resume_auto_queue(
        "aqr_001",
        SessionActionRequest(caller_type="user_action", user_action=True, idempotency_key="aq-resume-002"),
        _build_request(),
    )

    assert response["data"]["run"]["status"] == "running"
    assert started_threads == [
        {
            "target": auto_queues._run_auto_queue_async,
            "args": ("job_aq_001", "aqr_001"),
            "kwargs": {},
            "daemon": True,
        }
    ]


def test_auto_queue_confirm_continue_api_spawns_background_runner_for_non_terminal_run(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.runs["aqr_001"] = _build_run(run_id="aqr_001", status=AutoQueueStatus.WAITING_USER_DECISION)
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    started_threads: list[dict[str, object]] = []
    auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS.clear()

    class _FakeThread:
        def __init__(self, *, target, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            started_threads.append(
                {
                    "target": self.target,
                    "args": self.args,
                    "kwargs": dict(self.kwargs),
                    "daemon": self.daemon,
                }
            )

    monkeypatch.setattr(auto_queues.threading, "Thread", _FakeThread)
    response = auto_queues.confirm_continue_auto_queue(
        "aqr_001",
        SessionActionRequest(caller_type="user_action", user_action=True, idempotency_key="aq-confirm-002"),
        _build_request(),
    )

    assert response["data"]["run"]["status"] == "running"
    assert started_threads == [
        {
            "target": auto_queues._run_auto_queue_async,
            "args": ("job_aq_001", "aqr_001"),
            "kwargs": {},
            "daemon": True,
        }
    ]


def test_recover_auto_queue_runs_after_restart_spawns_only_running_runs(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.recover_results["work_001"] = _build_run(run_id="aqr_001", work_id="work_001", status=AutoQueueStatus.RUNNING)
    fake_service.recover_results["work_002"] = _build_run(run_id="aqr_002", work_id="work_002", status=AutoQueueStatus.WAITING_USER_DECISION)
    fake_service.recover_results["work_003"] = _build_run(run_id="aqr_003", work_id="work_003", status=AutoQueueStatus.WAITING_USER_DECISION)
    monkeypatch.setattr(dependencies, "get_work_service", lambda: _FakeWorkService(["work_001", "work_002", "work_003"]), raising=False)
    started_threads: list[dict[str, object]] = []
    auto_queues._ACTIVE_AUTO_QUEUE_RUNNERS.clear()

    class _FakeThread:
        def __init__(self, *, target, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            started_threads.append(
                {
                    "target": self.target,
                    "args": self.args,
                    "kwargs": dict(self.kwargs),
                    "daemon": self.daemon,
                }
            )

    monkeypatch.setattr(auto_queues.threading, "Thread", _FakeThread)

    recovered_run_ids = auto_queues.recover_auto_queue_runs_after_restart()

    assert recovered_run_ids == ["aqr_001", "aqr_002", "aqr_003"]
    assert fake_service.recover_calls == ["work_001", "work_002", "work_003"]
    assert started_threads == [
        {
            "target": auto_queues._run_auto_queue_async,
            "args": ("job_aq_001", "aqr_001"),
            "kwargs": {},
            "daemon": True,
        }
    ]


def test_recover_auto_queue_runs_after_restart_converges_completed_run_to_completed_ai_job(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    completed_run = _build_run(run_id="aqr_004", work_id="work_004", status=AutoQueueStatus.COMPLETED)
    fake_service.recover_results["work_004"] = completed_run
    fake_service.runs["aqr_004"] = completed_run
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    monkeypatch.setattr(dependencies, "get_work_service", lambda: _FakeWorkService(["work_004"]), raising=False)
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

    recovered_run_ids = auto_queues.recover_auto_queue_runs_after_restart()

    assert recovered_run_ids == ["aqr_004"]
    assert fake_job_service.completed_jobs == [
        (
            "job_aq_001",
            {
                "run_id": "aqr_004",
                "status": "completed",
            },
            "auto_queue_run:aqr_004",
        )
    ]


def test_recover_auto_queue_runs_after_restart_preserves_failed_run_error_details(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    failed_run = _build_run(
        run_id="aqr_005",
        work_id="work_005",
        status=AutoQueueStatus.FAILED,
    ).model_copy(
        update={
            "error_code": "provider_unrecoverable",
            "error_message": "quota exceeded",
        }
    )
    fake_service.recover_results["work_005"] = failed_run
    fake_service.runs["aqr_005"] = failed_run
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    monkeypatch.setattr(dependencies, "get_work_service", lambda: _FakeWorkService(["work_005"]), raising=False)
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

    recovered_run_ids = auto_queues.recover_auto_queue_runs_after_restart()

    assert recovered_run_ids == ["aqr_005"]
    assert fake_job_service.failed_jobs == [
        (
            "job_aq_001",
            "provider_unrecoverable",
            "quota exceeded",
        )
    ]
    assert fake_job_service.failed_steps == [
        (
            "job_aq_001",
            "step_aq_001",
            "provider_unrecoverable",
            "quota exceeded",
        )
    ]


def test_recover_auto_queue_runs_after_restart_cancels_cancelled_run_without_restarting_job(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    cancelled_run = _build_run(
        run_id="aqr_006",
        work_id="work_006",
        status=AutoQueueStatus.CANCELLED,
    )
    fake_service.recover_results["work_006"] = cancelled_run
    fake_service.runs["aqr_006"] = cancelled_run
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    monkeypatch.setattr(dependencies, "get_work_service", lambda: _FakeWorkService(["work_006"]), raising=False)
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

    recovered_run_ids = auto_queues.recover_auto_queue_runs_after_restart()

    assert recovered_run_ids == ["aqr_006"]
    assert fake_job_service.started_jobs == []
    assert fake_job_service.running_steps == []
    assert fake_job_service.cancelled_jobs == [("job_aq_001", "auto_queue_cancelled")]


def test_recover_auto_queue_runs_after_restart_completes_terminal_runs_without_restarting_job(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    completed_run = _build_run(
        run_id="aqr_007",
        work_id="work_007",
        status=AutoQueueStatus.COMPLETED,
    ).model_copy(
        update={
            "job_id": "job_aq_007",
        }
    )
    stopped_run = _build_run(
        run_id="aqr_008",
        work_id="work_008",
        status=AutoQueueStatus.STOPPED,
        stop_record=AutoQueueStopRecord(
            stop_reason=StopCondition.USER_MANUAL_STOP,
            stop_severity=StopSeverity.USER,
            stop_context={"source": "test"},
            stopped_at=_now(),
            user_action_required=False,
            suggested_action="",
        ),
    ).model_copy(
        update={
            "job_id": "job_aq_008",
        }
    )
    failed_run = _build_run(
        run_id="aqr_009",
        work_id="work_009",
        status=AutoQueueStatus.FAILED,
    ).model_copy(
        update={
            "job_id": "job_aq_009",
            "error_code": "provider_unrecoverable",
            "error_message": "quota exceeded",
        }
    )
    fake_service.recover_results["work_007"] = completed_run
    fake_service.recover_results["work_008"] = stopped_run
    fake_service.recover_results["work_009"] = failed_run
    fake_service.runs["aqr_007"] = completed_run
    fake_service.runs["aqr_008"] = stopped_run
    fake_service.runs["aqr_009"] = failed_run
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    monkeypatch.setattr(dependencies, "get_work_service", lambda: _FakeWorkService(["work_007", "work_008", "work_009"]), raising=False)
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

    recovered_run_ids = auto_queues.recover_auto_queue_runs_after_restart()

    assert recovered_run_ids == ["aqr_007", "aqr_008", "aqr_009"]
    assert fake_job_service.started_jobs == []
    assert fake_job_service.running_steps == []
    assert fake_job_service.completed_jobs == [
        (
            "job_aq_007",
            {
                "run_id": "aqr_007",
                "status": "completed",
            },
            "auto_queue_run:aqr_007",
        ),
        (
            "job_aq_008",
            {
                "run_id": "aqr_008",
                "status": "stopped",
                "stop_reason": "user_manual_stop",
            },
            "auto_queue_run:aqr_008",
        ),
    ]
    assert fake_job_service.failed_jobs == [
        (
            "job_aq_009",
            "provider_unrecoverable",
            "quota exceeded",
        )
    ]


def test_recover_auto_queue_runs_after_restart_skips_terminal_reconvergence_when_ai_job_already_terminal(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    completed_run = _build_run(
        run_id="aqr_010",
        work_id="work_010",
        status=AutoQueueStatus.COMPLETED,
    ).model_copy(
        update={
            "job_id": "job_aq_010",
        }
    )
    fake_service.recover_results["work_010"] = completed_run
    fake_service.runs["aqr_010"] = completed_run
    fake_job_service = _FakeAIJobService()
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
            },
            "auto_queue_run:aqr_010",
        )
    ]


def test_recover_auto_queue_runs_after_restart_skips_failed_and_cancelled_reconvergence_when_ai_job_already_terminal(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    failed_run = _build_run(
        run_id="aqr_011",
        work_id="work_011",
        status=AutoQueueStatus.FAILED,
    ).model_copy(
        update={
            "job_id": "job_aq_011",
            "error_code": "provider_unrecoverable",
            "error_message": "quota exceeded",
        }
    )
    cancelled_run = _build_run(
        run_id="aqr_012",
        work_id="work_012",
        status=AutoQueueStatus.CANCELLED,
    ).model_copy(
        update={
            "job_id": "job_aq_012",
        }
    )
    fake_service.recover_results["work_011"] = failed_run
    fake_service.recover_results["work_012"] = cancelled_run
    fake_service.runs["aqr_011"] = failed_run
    fake_service.runs["aqr_012"] = cancelled_run
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)
    monkeypatch.setattr(dependencies, "get_work_service", lambda: _FakeWorkService(["work_011", "work_012"]), raising=False)
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

    assert first_recovered == ["aqr_011", "aqr_012"]
    assert second_recovered == ["aqr_011", "aqr_012"]
    assert fake_job_service.failed_jobs == [
        (
            "job_aq_011",
            "provider_unrecoverable",
            "quota exceeded",
        )
    ]
    assert fake_job_service.cancelled_jobs == [("job_aq_012", "auto_queue_cancelled")]


def test_run_auto_queue_async_completes_ai_job_from_background_step(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.runs["aqr_001"] = _build_run(run_id="aqr_001", status=AutoQueueStatus.COMPLETED)
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)

    auto_queues._run_auto_queue_async("job_aq_001", "aqr_001")

    assert fake_service.background_step_calls == ["aqr_001"]
    assert fake_service.status_calls == ["aqr_001"]
    assert fake_job_service.started_jobs == ["job_aq_001"]
    assert fake_job_service.running_steps == [("job_aq_001", "step_aq_001")]
    assert fake_job_service.completed_steps == [("job_aq_001", "step_aq_001", "run:aqr_001:completed")]
    assert fake_job_service.completed_jobs == [
        (
            "job_aq_001",
            {
                "run_id": "aqr_001",
                "status": "completed",
            },
            "auto_queue_run:aqr_001",
        )
    ]


def test_run_auto_queue_async_loops_running_steps_until_completed(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.status_sequences["aqr_001"] = [
        _build_run(run_id="aqr_001", status=AutoQueueStatus.RUNNING),
        _build_run(run_id="aqr_001", status=AutoQueueStatus.RUNNING),
        _build_run(run_id="aqr_001", status=AutoQueueStatus.COMPLETED),
    ]
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)

    auto_queues._run_auto_queue_async("job_aq_001", "aqr_001")

    assert fake_service.background_step_calls == ["aqr_001", "aqr_001", "aqr_001"]
    assert fake_service.status_calls == ["aqr_001", "aqr_001", "aqr_001"]
    assert fake_job_service.completed_steps == [("job_aq_001", "step_aq_001", "run:aqr_001:completed")]
    assert fake_job_service.completed_jobs == [
        (
            "job_aq_001",
            {
                "run_id": "aqr_001",
                "status": "completed",
            },
            "auto_queue_run:aqr_001",
        )
    ]


def test_run_auto_queue_async_pauses_job_on_waiting_user_decision(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.status_sequences["aqr_001"] = [
        _build_run(run_id="aqr_001", status=AutoQueueStatus.WAITING_USER_DECISION),
    ]
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)

    auto_queues._run_auto_queue_async("job_aq_001", "aqr_001")

    assert fake_service.background_step_calls == ["aqr_001"]
    assert fake_service.status_calls == ["aqr_001"]
    assert fake_job_service.paused_jobs == [("job_aq_001", "waiting_user_decision")]
    assert fake_job_service.completed_steps == [("job_aq_001", "step_aq_001", "run:aqr_001:waiting_user_decision")]
    assert fake_job_service.completed_jobs == []
    assert fake_job_service.failed_jobs == []


def test_run_auto_queue_async_cancelled_mode_cancels_job_instead_of_completing(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.status_sequences["aqr_001"] = [
        _build_run(run_id="aqr_001", status=AutoQueueStatus.CANCELLED),
    ]
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)

    auto_queues._run_auto_queue_async("job_aq_001", "aqr_001")

    assert fake_job_service.completed_steps == []
    assert fake_job_service.cancelled_jobs == [("job_aq_001", "auto_queue_cancelled")]
    assert fake_job_service.completed_jobs == []
    assert fake_job_service.failed_jobs == []


def test_run_auto_queue_async_running_then_cancelled_exits_without_extra_completion(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.status_sequences["aqr_001"] = [
        _build_run(run_id="aqr_001", status=AutoQueueStatus.RUNNING),
        _build_run(run_id="aqr_001", status=AutoQueueStatus.CANCELLED),
        _build_run(run_id="aqr_001", status=AutoQueueStatus.COMPLETED),
    ]
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)

    auto_queues._run_auto_queue_async("job_aq_001", "aqr_001")

    assert fake_service.background_step_calls == ["aqr_001", "aqr_001"]
    assert fake_service.status_calls == ["aqr_001", "aqr_001"]
    assert fake_job_service.completed_steps == []
    assert fake_job_service.cancelled_jobs == [("job_aq_001", "auto_queue_cancelled")]
    assert fake_job_service.completed_jobs == []


def test_run_auto_queue_async_stopped_mode_preserves_stop_reason_in_result_summary(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.status_sequences["aqr_001"] = [
        _build_run(
            run_id="aqr_001",
            status=AutoQueueStatus.STOPPED,
            stop_record=AutoQueueStopRecord(
                stop_reason=StopCondition.USER_MANUAL_STOP,
                stop_severity=StopSeverity.USER,
                stop_context={"source": "test"},
                stopped_at=_now(),
                user_action_required=False,
                suggested_action="",
            ),
        ),
    ]
    fake_job_service = _FakeAIJobService()
    monkeypatch.setattr(dependencies, "get_ai_job_service", lambda: fake_job_service, raising=False)

    auto_queues._run_auto_queue_async("job_aq_001", "aqr_001")

    assert fake_job_service.completed_jobs == [
        (
            "job_aq_001",
            {
                "run_id": "aqr_001",
                "status": "stopped",
                "stop_reason": "user_manual_stop",
            },
            "auto_queue_run:aqr_001",
        )
    ]


def test_auto_queue_confirm_continue_api_rejects_non_user_action_caller(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.runs["aqr_001"] = _build_run(run_id="aqr_001", status=AutoQueueStatus.WAITING_USER_DECISION)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/auto-queues/aqr_001/confirm-continue",
        json={"caller_type": "agent", "user_action": True, "idempotency_key": "aq-confirm-001"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "P2_CALLER_FORBIDDEN"


def test_auto_queue_control_and_history_api_use_service_results(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    fake_service.runs["aqr_001"] = _build_run(run_id="aqr_001", status=AutoQueueStatus.WAITING_USER_DECISION)
    fake_service.runs["aqr_002"] = _build_run(run_id="aqr_002", status=AutoQueueStatus.STOPPED)
    client = TestClient(app)

    confirm_response = client.post(
        "/api/v2/ai/auto-queues/aqr_001/confirm-continue",
        json={"caller_type": "user_action", "user_action": True, "idempotency_key": "aq-confirm-allow-001"},
    )
    pause_response = client.post(
        "/api/v2/ai/auto-queues/aqr_001/pause",
        json={"caller_type": "user_action", "user_action": True, "idempotency_key": "aq-pause-001"},
    )
    resume_response = client.post(
        "/api/v2/ai/auto-queues/aqr_001/resume",
        json={"caller_type": "user_action", "user_action": True, "idempotency_key": "aq-resume-001"},
    )
    stop_response = client.post(
        "/api/v2/ai/auto-queues/aqr_001/stop",
        json={"caller_type": "user_action", "user_action": True, "idempotency_key": "aq-stop-001"},
    )
    history_response = client.get("/api/v2/ai/auto-queues/work_001/history")

    assert confirm_response.status_code == 200
    assert confirm_response.json()["data"]["run"]["status"] == "running"
    assert pause_response.status_code == 200
    assert pause_response.json()["data"]["run"]["status"] == "paused"
    assert resume_response.status_code == 200
    assert resume_response.json()["data"]["run"]["status"] == "running"
    assert stop_response.status_code == 200
    assert stop_response.json()["data"]["run"]["status"] == "stopped"
    assert history_response.status_code == 200
    assert {item["run_id"] for item in history_response.json()["data"]["runs"]} == {"aqr_001", "aqr_002"}
    assert fake_service.confirm_calls == ["aqr_001"]
