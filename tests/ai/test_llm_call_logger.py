from __future__ import annotations

import json
from datetime import UTC, datetime

from application.services.ai.llm_call_logger import LLMCallLogger
from domain.entities.ai.models import LLMCallStatus, LLMUsage
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore


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
