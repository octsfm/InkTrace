from __future__ import annotations

from application.services.ai.ai_job_service import AIJobService
from domain.entities.ai.models import (
    AIJobStatus,
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
    StopSeverity,
)
from application.services.ai.stop_condition_evaluator import StopConditionEvaluator
from domain.repositories.ai.auto_queue_config_repository import AutoQueueConfigRepository
from domain.repositories.ai.auto_queue_run_repository import AutoQueueRunRepository


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
    TERMINAL = {
        AutoQueueStatus.STOPPED,
        AutoQueueStatus.COMPLETED,
        AutoQueueStatus.FAILED,
        AutoQueueStatus.CANCELLED,
    }

    def __init__(self) -> None:
        self._items: dict[str, AutoQueueRun] = {}

    def save(self, run: AutoQueueRun) -> AutoQueueRun:
        self._items[run.run_id] = run
        return run

    def get_by_id(self, run_id: str) -> AutoQueueRun | None:
        return self._items.get(run_id)

    def get_active(self, work_id: str) -> AutoQueueRun | None:
        for run in sorted(self._items.values(), key=lambda item: item.updated_at, reverse=True):
            if run.work_id == work_id and run.status not in self.TERMINAL:
                return run
        return None

    def get_history(self, work_id: str, limit: int = 20) -> list[AutoQueueRun]:
        return [item for item in self._items.values() if item.work_id == work_id][:limit]

    def update(self, run: AutoQueueRun) -> AutoQueueRun:
        return self.save(run)


class _StubMultiChapterService:
    def __init__(self, *, start_result: MultiChapterSession) -> None:
        self.start_result = start_result
        self.pause_result = start_result
        self.resume_result = start_result
        self.cancel_result = start_result
        self.advance_result = start_result
        self.advance_results: list[MultiChapterSession] = []
        self.get_session_result = start_result
        self.start_calls: list[dict[str, object]] = []
        self.pause_calls: list[str] = []
        self.resume_calls: list[str] = []
        self.cancel_calls: list[str] = []
        self.advance_calls: list[tuple[str, ChapterAdvanceDecision]] = []
        self.get_session_calls: list[str] = []

    def start(
        self,
        *,
        work_id: str,
        start_chapter_id: str,
        target_chapters: int,
        user_instruction: str = "",
        caller_type: str = "user_action",
    ) -> MultiChapterSession:
        self.start_calls.append(
            {
                "work_id": work_id,
                "start_chapter_id": start_chapter_id,
                "target_chapters": target_chapters,
                "user_instruction": user_instruction,
                "caller_type": caller_type,
            }
        )
        return self.start_result

    def pause(self, session_id: str) -> MultiChapterSession:
        self.pause_calls.append(session_id)
        return self.pause_result

    def resume(self, session_id: str) -> MultiChapterSession:
        self.resume_calls.append(session_id)
        return self.resume_result

    def cancel(self, session_id: str) -> MultiChapterSession:
        self.cancel_calls.append(session_id)
        return self.cancel_result

    def get_session(self, session_id: str) -> MultiChapterSession:
        self.get_session_calls.append(session_id)
        return self.get_session_result

    def advance_to_next_chapter(
        self,
        session_id: str,
        *,
        decision: ChapterAdvanceDecision,
    ) -> MultiChapterSession:
        self.advance_calls.append((session_id, decision))
        if self.advance_results:
            return self.advance_results.pop(0)
        return self.advance_result


class _StubJobService:
    def __init__(self) -> None:
        self.created_jobs: list[dict[str, object]] = []

    def create_job(
        self,
        *,
        job_type: str,
        work_id: str,
        chapter_id: str | None = None,
        steps: list[dict[str, object]] | None = None,
        created_by: str = "user_action",
        idempotency_key: str = "",
        payload: dict[str, object] | None = None,
    ):
        job_id = f"job_aq_{len(self.created_jobs) + 1:03d}"
        job_payload = {
            "job_id": job_id,
            "job_type": job_type,
            "work_id": work_id,
            "chapter_id": chapter_id,
            "steps": list(steps or []),
            "created_by": created_by,
            "idempotency_key": idempotency_key,
            "payload": dict(payload or {}),
        }
        self.created_jobs.append(job_payload)
        return type(
            "_Job",
            (),
            {
                "job_id": job_id,
                "job_type": job_type,
                "work_id": work_id,
                "chapter_id": chapter_id,
                "status": AIJobStatus.QUEUED,
                "payload": dict(payload or {}),
            },
        )()


class _StubPlotArcRepository:
    def __init__(self, *, active_sequence_arc=None) -> None:
        self.active_sequence_arc = active_sequence_arc

    def get_active_sequence_arc(self, work_id: str, current_index: int):
        _ = work_id, current_index
        return self.active_sequence_arc


class _StubBudgetService:
    def __init__(self, *, exceeded: bool = False, suggested_action: str = "adjust_budget") -> None:
        self.exceeded = exceeded
        self.suggested_action = suggested_action
        self.calls: list[str] = []

    def check_auto_queue_budget(self, run_id: str):
        self.calls.append(run_id)
        class _Result:
            def __init__(self, exceeded: bool, suggested_action: str) -> None:
                self.exceeded = exceeded
                self.suggested_action = suggested_action

        return _Result(
            exceeded=self.exceeded,
            suggested_action=self.suggested_action,
        )


def _build_stop_evaluator(*, budget_service=None, active_sequence_arc=None) -> StopConditionEvaluator:
    return StopConditionEvaluator(
        plot_arc_repository=_StubPlotArcRepository(active_sequence_arc=active_sequence_arc),
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
    status: MultiChapterStatus = MultiChapterStatus.RUNNING,
    current_index: int = 1,
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


def test_auto_queue_service_start_creates_run_and_delegates_to_multi_chapter_start() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(target_chapters=3))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session(status=MultiChapterStatus.RUNNING))

    job_service = _StubJobService()
    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=job_service,
    )

    run = service.start(config_id="aqc_001", work_id="work_001", start_chapter_id="chapter_start")

    assert run.status == AutoQueueStatus.RUNNING
    assert run.job_id == "job_aq_001"
    assert run.queue_mode == AutoQueueMode.SAFE
    assert run.multi_chapter_session_id == "mcs_001"
    assert run_repo.get_by_id(run.run_id) is not None
    assert job_service.created_jobs == [
        {
            "job_id": "job_aq_001",
            "job_type": "auto_queue",
            "work_id": "work_001",
            "chapter_id": "chapter_start",
            "steps": [{"step_type": "run_auto_queue", "step_name": "Run Auto Queue"}],
            "created_by": "user_action",
            "idempotency_key": "",
            "payload": {
                "run_id": run.run_id,
                "config_id": "aqc_001",
                "work_id": "work_001",
                "start_chapter_id": "chapter_start",
                "queue_mode": "safe",
            },
        }
    ]
    assert multi_chapter_service.start_calls == [
        {
            "work_id": "work_001",
            "start_chapter_id": "chapter_start",
            "target_chapters": 3,
            "user_instruction": "",
            "caller_type": "user_action",
        }
    ]


def test_auto_queue_service_start_auto_advances_one_hop_in_continuous_mode() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=3, stop_at_sequence_end=False))
    multi_chapter_service = _StubMultiChapterService(
        start_result=_build_session(
            status=MultiChapterStatus.WAITING_USER_DECISION,
            current_index=1,
            target_chapters=3,
        )
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

    run = service.start(config_id="aqc_001", work_id="work_001", start_chapter_id="chapter_start")

    assert run.status == AutoQueueStatus.RUNNING
    assert run.queue_mode == AutoQueueMode.CONTINUOUS
    assert multi_chapter_service.advance_calls == [("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY)]


def test_auto_queue_service_start_completes_instead_of_auto_advance_when_target_reached() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=1, stop_at_sequence_end=False))
    multi_chapter_service = _StubMultiChapterService(
        start_result=_build_session(
            status=MultiChapterStatus.WAITING_USER_DECISION,
            current_index=1,
            target_chapters=1,
        )
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    run = service.start(config_id="aqc_001", work_id="work_001", start_chapter_id="chapter_start")

    assert run.status == AutoQueueStatus.COMPLETED
    assert run.stop_record is not None
    assert run.stop_record.stop_reason == StopCondition.TARGET_CHAPTERS_REACHED
    assert multi_chapter_service.advance_calls == []


def test_auto_queue_service_pause_updates_run_and_delegates_to_multi_chapter_pause() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config())
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.pause_result = _build_session(status=MultiChapterStatus.PAUSED)

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    paused = service.pause("aqr_001")

    assert paused.status == AutoQueueStatus.PAUSED
    assert multi_chapter_service.pause_calls == ["mcs_001"]


def test_auto_queue_service_resume_maps_waiting_state_from_multi_chapter_service() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config())
    run_repo.save(_build_run(status=AutoQueueStatus.PAUSED))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.resume_result = _build_session(status=MultiChapterStatus.WAITING_USER_DECISION)

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    resumed = service.resume("aqr_001")

    assert resumed.status == AutoQueueStatus.WAITING_USER_DECISION
    assert multi_chapter_service.resume_calls == ["mcs_001"]


def test_auto_queue_service_resume_marks_completed_when_target_reached() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.SAFE, target_chapters=2, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.PAUSED, queue_mode=AutoQueueMode.SAFE, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.resume_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=2,
        target_chapters=2,
    ).model_copy(
        update={
            "per_chapter_status": [
                ChapterStatusEntry(chapter_index=1, chapter_id="chapter_001", status=PerChapterStatus.READY),
                ChapterStatusEntry(chapter_index=2, chapter_id="chapter_002", status=PerChapterStatus.READY),
            ]
        }
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    resumed = service.resume("aqr_001")

    assert resumed.status == AutoQueueStatus.COMPLETED
    assert resumed.stop_record is not None
    assert resumed.stop_record.stop_reason == StopCondition.TARGET_CHAPTERS_REACHED
    assert resumed.current_stop_evaluation["reason"] == "target_chapters_reached"
    assert multi_chapter_service.resume_calls == ["mcs_001"]


def test_auto_queue_service_resume_stops_when_budget_exceeded() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    budget_service = _StubBudgetService(exceeded=True, suggested_action="adjust_budget")
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
    run_repo.save(_build_run(status=AutoQueueStatus.PAUSED, queue_mode=AutoQueueMode.CONTINUOUS, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
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
    )

    resumed = service.resume("aqr_001")

    assert resumed.status == AutoQueueStatus.STOPPED
    assert resumed.stop_record is not None
    assert resumed.stop_record.stop_reason == StopCondition.BUDGET_EXCEEDED
    assert resumed.current_stop_evaluation["reason"] == "budget_exceeded"
    assert budget_service.calls == ["aqr_001"]


def test_auto_queue_service_user_confirm_continue_advances_without_apply() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.SAFE))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.SAFE))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.advance_result = _build_session(status=MultiChapterStatus.RUNNING, current_index=2)

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    updated = service.user_confirm_continue("aqr_001")

    assert updated.status == AutoQueueStatus.RUNNING
    assert multi_chapter_service.advance_calls == [("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY)]


def test_auto_queue_service_user_confirm_continue_marks_completed_when_target_reached() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.SAFE, target_chapters=2, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.SAFE, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.advance_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=2,
        target_chapters=2,
    ).model_copy(
        update={
            "per_chapter_status": [
                ChapterStatusEntry(chapter_index=1, chapter_id="chapter_001", status=PerChapterStatus.READY),
                ChapterStatusEntry(chapter_index=2, chapter_id="chapter_002", status=PerChapterStatus.READY),
            ]
        }
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    updated = service.user_confirm_continue("aqr_001")

    assert updated.status == AutoQueueStatus.COMPLETED
    assert updated.stop_record is not None
    assert updated.stop_record.stop_reason == StopCondition.TARGET_CHAPTERS_REACHED
    assert updated.current_stop_evaluation["reason"] == "target_chapters_reached"
    assert multi_chapter_service.advance_calls == [("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY)]


def test_auto_queue_service_user_confirm_continue_stops_when_budget_exceeded() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    budget_service = _StubBudgetService(exceeded=True, suggested_action="adjust_budget")
    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(
        _build_config(
            queue_mode=AutoQueueMode.SAFE,
            target_chapters=3,
            stop_at_sequence_end=False,
            stop_on_budget_exceeded=True,
        )
    )
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.SAFE, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.advance_result = _build_session(
        status=MultiChapterStatus.RUNNING,
        current_index=2,
        target_chapters=3,
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(budget_service=budget_service),
        job_service=_StubJobService(),
    )

    updated = service.user_confirm_continue("aqr_001")

    assert updated.status == AutoQueueStatus.STOPPED
    assert updated.stop_record is not None
    assert updated.stop_record.stop_reason == StopCondition.BUDGET_EXCEEDED
    assert updated.current_stop_evaluation["reason"] == "budget_exceeded"
    assert budget_service.calls == ["aqr_001"]


def test_auto_queue_service_run_background_step_returns_waiting_in_safe_mode() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.SAFE))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.SAFE))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    stepped = service.run_background_step("aqr_001")

    assert stepped.status == AutoQueueStatus.WAITING_USER_DECISION
    assert multi_chapter_service.get_session_calls == []
    assert multi_chapter_service.advance_calls == []


def test_auto_queue_service_run_background_step_advances_waiting_continuous_mode() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=3, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.CONTINUOUS, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
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

    stepped = service.run_background_step("aqr_001")

    assert stepped.status == AutoQueueStatus.RUNNING
    assert multi_chapter_service.get_session_calls == ["mcs_001"]
    assert multi_chapter_service.advance_calls == [("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY)]


def test_auto_queue_service_run_background_step_advances_multiple_chapters_until_completed() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=3, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.CONTINUOUS, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.advance_results = [
        _build_session(
            status=MultiChapterStatus.WAITING_USER_DECISION,
            current_index=2,
            target_chapters=3,
        ),
        _build_session(
            status=MultiChapterStatus.WAITING_USER_DECISION,
            current_index=3,
            target_chapters=3,
        ),
    ]

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    stepped = service.run_background_step("aqr_001")

    assert stepped.status == AutoQueueStatus.COMPLETED
    assert stepped.generated_count == 3
    assert multi_chapter_service.advance_calls == [
        ("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY),
        ("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY),
    ]


def test_auto_queue_service_run_background_step_stops_at_waiting_when_continuous_advances_to_non_terminal_state() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=4, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.CONTINUOUS, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.advance_results = [
        _build_session(
            status=MultiChapterStatus.RUNNING,
            current_index=2,
            target_chapters=4,
        ),
    ]
    multi_chapter_service.get_session_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=2,
        target_chapters=4,
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    stepped = service.run_background_step("aqr_001")

    assert stepped.status == AutoQueueStatus.WAITING_USER_DECISION
    assert stepped.generated_count == 2
    assert multi_chapter_service.advance_calls == [("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY)]
    assert multi_chapter_service.get_session_calls == ["mcs_001"]


def test_auto_queue_service_get_status_refreshes_waiting_state_from_multi_chapter_session() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.SAFE))
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING, queue_mode=AutoQueueMode.SAFE))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.get_session_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=1,
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    refreshed = service.get_status("aqr_001")

    assert refreshed.status == AutoQueueStatus.WAITING_USER_DECISION
    assert refreshed.generated_count == 1
    assert multi_chapter_service.get_session_calls == ["mcs_001"]


def test_auto_queue_service_get_status_auto_advances_one_hop_in_continuous_mode() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=3, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING, queue_mode=AutoQueueMode.CONTINUOUS, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.get_session_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=1,
        target_chapters=3,
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

    refreshed = service.get_status("aqr_001")

    assert refreshed.status == AutoQueueStatus.RUNNING
    assert refreshed.generated_count == 2
    assert multi_chapter_service.get_session_calls == ["mcs_001"]
    assert multi_chapter_service.advance_calls == [("mcs_001", ChapterAdvanceDecision.CONTINUE_WITHOUT_APPLY)]


def test_auto_queue_service_get_status_continuous_mode_completes_instead_of_auto_advance_when_target_reached() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=1, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING, queue_mode=AutoQueueMode.CONTINUOUS, generated_count=0))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.get_session_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=1,
        target_chapters=1,
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    refreshed = service.get_status("aqr_001")

    assert refreshed.status == AutoQueueStatus.COMPLETED
    assert refreshed.stop_record is not None
    assert refreshed.stop_record.stop_reason == StopCondition.TARGET_CHAPTERS_REACHED
    assert multi_chapter_service.advance_calls == []


def test_auto_queue_service_get_status_maps_blocked_session_to_stopped_with_stop_record() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS))
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING, queue_mode=AutoQueueMode.CONTINUOUS))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.get_session_result = _build_session(status=MultiChapterStatus.BLOCKED).model_copy(
        update={"blocked_reason_code": "blocking_review_consecutive"}
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
    assert refreshed.stop_record.stop_severity == StopSeverity.ABNORMAL


def test_auto_queue_service_get_status_marks_completed_when_target_chapters_reached() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.SAFE, target_chapters=1, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING, queue_mode=AutoQueueMode.SAFE, generated_count=0))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.get_session_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=1,
        target_chapters=1,
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    refreshed = service.get_status("aqr_001")

    assert refreshed.status == AutoQueueStatus.COMPLETED
    assert refreshed.stop_record is not None
    assert refreshed.stop_record.stop_reason == StopCondition.TARGET_CHAPTERS_REACHED
    assert refreshed.stop_record.stop_severity == StopSeverity.NORMAL
    assert refreshed.current_stop_evaluation["reason"] == "target_chapters_reached"
    assert refreshed.current_stop_evaluation["should_stop"] is True


def test_auto_queue_service_get_status_stops_when_budget_exceeded() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    budget_service = _StubBudgetService(exceeded=True, suggested_action="adjust_budget")
    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(
        _build_config(
            queue_mode=AutoQueueMode.CONTINUOUS,
            target_chapters=5,
            stop_at_sequence_end=False,
            stop_on_budget_exceeded=True,
        )
    )
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING, queue_mode=AutoQueueMode.CONTINUOUS))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.get_session_result = _build_session(
        status=MultiChapterStatus.RUNNING,
        current_index=1,
        target_chapters=5,
    )

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(budget_service=budget_service),
        job_service=_StubJobService(),
    )

    refreshed = service.get_status("aqr_001")

    assert refreshed.status == AutoQueueStatus.STOPPED
    assert refreshed.stop_record is not None
    assert refreshed.stop_record.stop_reason == StopCondition.BUDGET_EXCEEDED
    assert refreshed.stop_record.stop_severity == StopSeverity.BUDGET
    assert refreshed.current_stop_evaluation["reason"] == "budget_exceeded"
    assert budget_service.calls == ["aqr_001"]


def test_auto_queue_service_stop_records_user_manual_stop() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config())
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.cancel_result = _build_session(status=MultiChapterStatus.CANCELLED)

    service = AutoContinuationQueueService(
        config_repository=config_repo,
        run_repository=run_repo,
        multi_chapter_service=multi_chapter_service,
        stop_evaluator=_build_stop_evaluator(),
        job_service=_StubJobService(),
    )

    stopped = service.stop("aqr_001")

    assert stopped.status == AutoQueueStatus.STOPPED
    assert stopped.stop_record is not None
    assert stopped.stop_record.stop_reason == StopCondition.USER_MANUAL_STOP
    assert stopped.stop_record.stop_severity == StopSeverity.USER
    assert multi_chapter_service.cancel_calls == ["mcs_001"]


def test_auto_queue_service_recover_after_restart_resumes_running_active_run() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=3, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.RUNNING, queue_mode=AutoQueueMode.CONTINUOUS))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.resume_result = _build_session(
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
    assert multi_chapter_service.resume_calls == ["mcs_001"]


def test_auto_queue_service_recover_after_restart_keeps_safe_waiting_run_waiting() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.SAFE, target_chapters=3))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.SAFE))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.get_session_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=1,
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
    assert recovered.status == AutoQueueStatus.WAITING_USER_DECISION
    assert multi_chapter_service.resume_calls == []
    assert multi_chapter_service.get_session_calls == ["mcs_001"]
    assert multi_chapter_service.advance_calls == []


def test_auto_queue_service_recover_after_restart_auto_advances_continuous_waiting_run() -> None:
    from application.services.ai.auto_queue_service import AutoContinuationQueueService

    config_repo = _InMemoryAutoQueueConfigRepository()
    run_repo = _InMemoryAutoQueueRunRepository()
    config_repo.save(_build_config(queue_mode=AutoQueueMode.CONTINUOUS, target_chapters=3, stop_at_sequence_end=False))
    run_repo.save(_build_run(status=AutoQueueStatus.WAITING_USER_DECISION, queue_mode=AutoQueueMode.CONTINUOUS, generated_count=1))
    multi_chapter_service = _StubMultiChapterService(start_result=_build_session())
    multi_chapter_service.get_session_result = _build_session(
        status=MultiChapterStatus.WAITING_USER_DECISION,
        current_index=1,
        target_chapters=3,
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
