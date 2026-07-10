from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api import dependencies
from presentation.api.app import app


class FakeOpeningService:
    def __init__(self) -> None:
        self.confirm_payload = None

    def prepare_brief(self, **kwargs):
        return type("Brief", (), {"model_dump": lambda self, mode="json": {"brief_id": "ob_1", "work_id": kwargs["work_id"], "status": "ready"}})()

    def generate_directions(self, **kwargs):
        return type("Batch", (), {"model_dump": lambda self, mode="json": {"batch_id": "odb_1", "status": "waiting_direction_choice", "directions": []}})()

    def confirm_direction(self, **kwargs):
        self.confirm_payload = kwargs
        return type("Direction", (), {"model_dump": lambda self, mode="json": {"direction_id": "od_1", "status": "confirmed"}})()

    def revise_direction(self, **kwargs):
        return type("Direction", (), {"model_dump": lambda self, mode="json": {
            "direction_id": "od_2", "parent_direction_id": kwargs["direction_id"],
            "revision_no": 2, "status": "proposed", "name": kwargs["name"],
        }})()

    def generate_drafts(self, **kwargs):
        return type("Batch", (), {"model_dump": lambda self, mode="json": {"draft_batch_id": "odraft_1", "status": "partial_success", "result_refs": ["candidate_draft:cd_1"]}})()

    def get_direction_batch(self, batch_id):
        return type("Batch", (), {"model_dump": lambda self, mode="json": {"batch_id": batch_id, "status": "waiting_direction_choice", "directions": []}})()

    def get_draft_batch(self, batch_id):
        return type("Batch", (), {"model_dump": lambda self, mode="json": {"draft_batch_id": batch_id, "status": "partial_success", "result_refs": ["candidate_draft:cd_1"]}})()

    def get_latest(self, work_id):
        return {"work_id": work_id}


def test_opening_v2_api_uses_human_routes_and_user_action_gate(monkeypatch):
    fake = FakeOpeningService()
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OPENING_AGENT", "1")
    monkeypatch.setattr(dependencies, "get_opening_agent_service", lambda: fake)
    client = TestClient(app)

    brief = client.post("/api/v2/ai/opening/briefs", json={
        "work_id": "work-1", "story_premise": "悬疑故事", "protagonist_desire": "找出真相",
        "third_chapter_expectation": "想知道幕后的人", "idempotency_key": "brief-1",
    })
    assert brief.status_code == 200
    assert brief.json()["data"]["brief_id"] == "ob_1"

    directions = client.post("/api/v2/ai/opening/briefs/ob_1/directions:generate", json={"idempotency_key": "dir-1"})
    assert directions.status_code == 200

    denied = client.post("/api/v2/ai/opening/directions/od_1:confirm", json={
        "caller_type": "agent", "user_action": False, "user_id": "agent", "idempotency_key": "bad",
    })
    assert denied.status_code == 403

    confirmed = client.post("/api/v2/ai/opening/directions/od_1:confirm", json={
        "caller_type": "user_action", "user_action": True, "user_id": "author", "idempotency_key": "ok",
    })
    assert confirmed.status_code == 200
    assert fake.confirm_payload["caller_type"] == "user_action"

    revised = client.post("/api/v2/ai/opening/directions/od_1:revise", json={
        "name": "我自己的方向", "summary": "从一个反常细节开始",
        "chapter_goals": ["异常", "追查", "反转"], "advantages": [], "risks": [],
        "idempotency_key": "revise-1",
    })
    assert revised.status_code == 200
    assert revised.json()["data"]["parent_direction_id"] == "od_1"

    generated = client.post("/api/v2/ai/opening/directions/od_1/drafts:generate", json={"idempotency_key": "draft-1"})
    assert generated.status_code == 200
    assert generated.json()["data"]["result_refs"] == ["candidate_draft:cd_1"]


def test_legacy_opening_routes_are_not_registered(monkeypatch):
    monkeypatch.setenv("INKTRACE_P2_ENABLE_OPENING_AGENT", "1")
    client = TestClient(app)
    assert client.post("/api/v2/ai/opening/import-reference", json={}).status_code == 404
    assert client.post("/api/v2/ai/opening/analyze", json={}).status_code == 404
