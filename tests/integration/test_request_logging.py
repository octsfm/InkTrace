from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api.app import app


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
