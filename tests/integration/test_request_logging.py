from __future__ import annotations

import logging
import importlib

from fastapi.testclient import TestClient

from application.services import logging_service
from presentation.api.app import app

app_module = importlib.import_module("presentation.api.app")


def test_request_id_header_is_returned():
    client = TestClient(app)
    response = client.get("/api/novels/")
    assert response.status_code == 200
    assert response.headers.get("x-request-id")


def test_request_id_preserves_custom_header_on_error_response():
    client = TestClient(app)
    custom_id = "req_test_custom_001"
    response = client.get("/api/export/download/not_exist.md", headers={"X-Request-Id": custom_id})
    assert response.status_code in {400, 404}
    assert response.headers.get("x-request-id") == custom_id


def test_runtime_metrics_endpoint_returns_request_and_sqlite_stats():
    client = TestClient(app)
    response = client.get("/metrics/runtime")
    assert response.status_code == 200
    payload = response.json()
    assert "runtime" in payload
    assert "sqlite" in payload
    assert "requests" in payload["runtime"]
    assert "organize" in payload["runtime"]
    assert "token_limit_error_rate" in payload["runtime"]["organize"]
    assert "budget_block_rate" in payload["runtime"]["organize"]
    assert "batch_resume_success_rate" in payload["runtime"]["organize"]
    assert "global_analysis_p95_ms" in payload["runtime"]["organize"]
    assert "connections_total" in payload["sqlite"]


def test_progress_poll_matcher_only_matches_progress_endpoint():
    assert app_module._is_progress_poll_request("GET", "/api/content/organize/progress/novel_1") is True
    assert app_module._is_progress_poll_request("POST", "/api/content/organize/progress/novel_1") is False
    assert app_module._is_progress_poll_request("GET", "/api/novels/novel_1") is False


def test_uvicorn_access_noise_filter_only_suppresses_progress_poll_2xx(monkeypatch):
    monkeypatch.setattr(logging_service, "_SUPPRESS_PROGRESS_POLL", True)
    noise_filter = logging_service._UvicornAccessNoiseFilter()
    progress_record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1", "GET", "/api/content/organize/progress/novel_1", "1.1", 200),
        exc_info=None,
    )
    normal_record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1", "GET", "/api/novels/", "1.1", 200),
        exc_info=None,
    )
    progress_error_record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1", "GET", "/api/content/organize/progress/novel_1", "1.1", 500),
        exc_info=None,
    )
    assert noise_filter.filter(progress_record) is False
    assert noise_filter.filter(normal_record) is True
    assert noise_filter.filter(progress_error_record) is True
