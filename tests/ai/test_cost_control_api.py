from fastapi.testclient import TestClient

from presentation.api import dependencies
from presentation.api.app import app


class _Service:
    def summary(self, work_id, month): return {"work_id": work_id, "estimated_cost": "2.500000", "currency": "CNY", "cost_completeness": "known"}
    def details(self, work_id, month, limit, offset): return {"items": [], "limit": limit, "offset": offset}
    def budgets(self, work_id): return {"policies": []}
    def check(self, work_id): return {"allowed": True, "control": "allow"}
    def save_budget(self, **kwargs): return {"budget_type": kwargs["budget_type"], "enabled": kwargs["enabled"], "limit": kwargs["limit"]}
    def prices(self, work_id, provider_name="", model_name=""): return {"policies": []}
    def save_price(self, **kwargs): return {"provider_name": kwargs["provider_name"], "model_name": kwargs["model_name"]}


def test_cost_queries_and_user_gated_budget_write(monkeypatch):
    monkeypatch.setenv("INKTRACE_P2_ENABLE_COST_DASHBOARD", "1")
    monkeypatch.setattr(dependencies, "get_cost_control_service", lambda: _Service())
    client = TestClient(app)
    summary = client.get("/api/v2/ai/cost-dashboard/summary", params={"work_id": "work-1"})
    forbidden = client.put("/api/v2/ai/cost-budget", json={"budget_type": "monthly", "enabled": True, "limit": "10", "currency": "CNY"})
    saved = client.put("/api/v2/ai/cost-budget", json={
        "work_id": "work-1", "budget_type": "monthly", "enabled": True, "limit": "10", "currency": "CNY",
        "caller_type": "user_action", "user_action": True, "user_id": "local-author", "idempotency_key": "budget-1", "confirm_budget_change": True
    })
    assert summary.status_code == 200
    assert summary.json()["data"]["estimated_cost"] == "2.500000"
    assert forbidden.status_code == 403
    assert saved.status_code == 200


def test_disabling_budget_needs_second_confirmation(monkeypatch):
    monkeypatch.setattr(dependencies, "get_cost_control_service", lambda: _Service())
    client = TestClient(app)
    response = client.put("/api/v2/ai/cost-budget", json={
        "budget_type": "monthly", "enabled": False, "limit": "10", "currency": "CNY",
        "user_action": True, "user_id": "local-author", "idempotency_key": "budget-2", "confirm_budget_change": True
    })
    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "P2_BUDGET_DISABLE_CONFIRMATION_REQUIRED"


def test_manual_price_requires_source_confirmation(monkeypatch):
    monkeypatch.setattr(dependencies, "get_cost_control_service", lambda: _Service())
    response = TestClient(app).put("/api/v2/ai/cost-prices", json={
        "provider_name":"provider","model_name":"model","input_price_per_1m":"1","output_price_per_1m":"2","currency":"CNY",
        "user_action":True,"user_id":"local-author","idempotency_key":"price-1","confirm_price_change":True
    })
    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "P2_PRICE_SOURCE_CONFIRMATION_REQUIRED"
