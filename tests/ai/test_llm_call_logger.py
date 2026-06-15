from __future__ import annotations

import json
from datetime import UTC, datetime

from application.services.ai.llm_call_logger import LLMCallLogger
from domain.entities.ai.models import LLMCallLog, LLMCallStatus, LLMUsage
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore
from infrastructure.database.v1 import connect


def test_llm_call_logger_records_success_without_prompt_or_api_key(tmp_path) -> None:
    store = FileLLMCallLogStore(tmp_path / "llm_calls.jsonl")
    logger = LLMCallLogger(repository=store)

    logger.record(
        prompt_key="provider_connection_test_p0",
        prompt_version="v1",
        model_role="writer",
        provider_name="fake",
        model_name="fake-writer",
        request_id="req-1",
        trace_id="trace-1",
        status=LLMCallStatus.SUCCEEDED,
        started_at=datetime(2026, 5, 11, tzinfo=UTC),
        finished_at=datetime(2026, 5, 11, tzinfo=UTC),
        usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
    )

    payload = json.loads((tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert payload["provider_name"] == "fake"
    assert payload["model_name"] == "fake-writer"
    assert payload["status"] == "succeeded"
    assert "prompt_text" not in payload
    assert "api_key" not in payload


def test_llm_call_logger_records_failure_error_code(tmp_path) -> None:
    store = FileLLMCallLogStore(tmp_path / "llm_calls.jsonl")
    logger = LLMCallLogger(repository=store)

    logger.record(
        prompt_key="provider_connection_test_p0",
        prompt_version="v1",
        model_role="writer",
        provider_name="fake",
        model_name="fake-writer",
        request_id="req-2",
        trace_id="trace-2",
        status=LLMCallStatus.FAILED,
        started_at=datetime(2026, 5, 11, tzinfo=UTC),
        finished_at=datetime(2026, 5, 11, tzinfo=UTC),
        error_code="provider_timeout",
        error_message="request timed out",
    )

    payload = json.loads((tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert payload["status"] == "failed"
    assert payload["error_code"] == "provider_timeout"


def test_llm_call_logger_ignores_missing_trace_when_persisting_observability_view(tmp_path) -> None:
    store = FileLLMCallLogStore(tmp_path / "llm_calls.jsonl")

    class _TraceService:
        def record_llm_call(self, *args, **kwargs) -> None:
            raise ValueError("trace_not_found")

    logger = LLMCallLogger(repository=store, trace_service=_TraceService())

    logger.record(
        prompt_key="quick_trial",
        prompt_version="p0",
        model_role="quick_trial_writer",
        provider_name="fake",
        model_name="fake-chat",
        request_id="req-3",
        trace_id="trace-missing",
        status=LLMCallStatus.SUCCEEDED,
        started_at=datetime(2026, 5, 11, tzinfo=UTC),
        finished_at=datetime(2026, 5, 11, tzinfo=UTC),
        usage=LLMUsage(input_tokens=1, output_tokens=2, total_tokens=3),
    )

    payload = json.loads((tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert payload["request_id"] == "req-3"
    assert payload["trace_id"] == "trace-missing"


def test_llm_call_logger_records_cost_snapshot_and_scope_fields(tmp_path) -> None:
    store = FileLLMCallLogStore(tmp_path / "llm_calls.jsonl")
    logger = LLMCallLogger(
        repository=store,
        pricing_resolver=lambda provider_name, model_name, model_role: {
            "input_price_per_1k": 0.002,
            "output_price_per_1k": 0.008,
            "currency": "CNY",
            "pricing_source": "test_fixture",
            "captured_at": "2026-06-09T10:00:00+08:00",
        },
    )

    logger.record(
        prompt_key="quick_trial",
        prompt_version="p0",
        model_role="writer",
        provider_name="fake",
        model_name="fake-writer",
        request_id="req-4",
        trace_id="trace-4",
        work_id="work-1",
        session_id="session-1",
        step_id="step-1",
        status=LLMCallStatus.SUCCEEDED,
        started_at=datetime(2026, 6, 9, tzinfo=UTC),
        finished_at=datetime(2026, 6, 9, tzinfo=UTC),
        usage=LLMUsage(input_tokens=1500, output_tokens=500, total_tokens=2000),
    )

    payload = json.loads((tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert payload["work_id"] == "work-1"
    assert payload["session_id"] == "session-1"
    assert payload["step_id"] == "step-1"
    assert payload["estimated_cost"] == 0.007
    assert payload["price_snapshot_json"] == {
        "input_price_per_1k": 0.002,
        "output_price_per_1k": 0.008,
        "currency": "CNY",
        "pricing_source": "test_fixture",
        "captured_at": "2026-06-09T10:00:00+08:00",
    }


def test_file_llm_call_log_store_projects_entry_to_sqlite(tmp_path) -> None:
    db_path = tmp_path / "runtime.db"
    store = FileLLMCallLogStore(
        tmp_path / "llm_calls.jsonl",
        database_path=db_path,
    )

    store.append(
        LLMCallLog(
            prompt_key="quick_trial",
            prompt_version="p0",
            work_id="work-1",
            model_role="writer",
            provider_name="fake",
            model_name="fake-writer",
            request_id="req-sqlite-1",
            trace_id="trace-sqlite-1",
            session_id="session-1",
            step_id="step-1",
            status=LLMCallStatus.SUCCEEDED,
            started_at=datetime(2026, 6, 9, tzinfo=UTC),
            finished_at=datetime(2026, 6, 9, tzinfo=UTC),
            usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            estimated_cost=0.123,
            price_snapshot_json={"currency": "CNY", "input_price_per_1k": 0.002},
        )
    )

    conn = connect(db_path)
    row = conn.execute(
        "SELECT request_id, work_id, session_id, step_id, estimated_cost, price_snapshot_json "
        "FROM llm_call_logs WHERE request_id = ?",
        ("req-sqlite-1",),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["request_id"] == "req-sqlite-1"
    assert row["work_id"] == "work-1"
    assert row["session_id"] == "session-1"
    assert row["step_id"] == "step-1"
    assert row["estimated_cost"] == 0.123
    assert json.loads(row["price_snapshot_json"]) == {"currency": "CNY", "input_price_per_1k": 0.002}
