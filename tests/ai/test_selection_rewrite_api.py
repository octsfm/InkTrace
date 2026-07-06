from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api import dependencies
from presentation.api.app import app


class _FakeSelectionRewriteService:
    def __init__(self) -> None:
        self.rewrite_payload: dict[str, object] | None = None
        self.apply_payload: dict[str, object] | None = None
        self.list_payload: dict[str, object] | None = None
        self.clear_payload: dict[str, object] | None = None

    async def rewrite(self, **kwargs):
        self.rewrite_payload = kwargs
        return {
            "rewrite_id": "srw_001",
            "status": "generating",
            "request_id": "job_001",
            "rewritten_text": "",
            "word_count_before": 5,
            "word_count_after": 0,
            "diff_summary": "",
        }

    async def get_candidate(self, rewrite_id: str):
        return {
            "rewrite_id": rewrite_id,
            "status": "pending",
            "rewritten_text": "他缓步走进房间",
            "word_count_before": 5,
            "word_count_after": 8,
            "diff_summary": "补充动作细节",
            "source_start_pos": 3,
            "source_end_pos": 8,
        }

    async def list_candidates_by_chapter(self, chapter_id: str):
        self.list_payload = {"chapter_id": chapter_id}
        return [{
            "rewrite_id": "srw_hist_001",
            "chapter_id": chapter_id,
            "status": "expired",
            "rewrite_mode": "rewrite",
            "source_text": "他走进房间",
            "rewritten_text": "他缓步走进房间",
        }]

    async def apply(self, rewrite_id: str, **kwargs):
        self.apply_payload = {"rewrite_id": rewrite_id, **kwargs}
        return {
            "rewrite_id": rewrite_id,
            "status": "applied",
            "patch": {
                "range": [3, 8],
                "replacement": kwargs.get("final_text") or "他缓步走进房间",
            },
        }

    async def reject(self, rewrite_id: str):
        return {
            "rewrite_id": rewrite_id,
            "status": "rejected",
        }

    async def clear_chapter_history(self, chapter_id: str):
        self.clear_payload = {"chapter_id": chapter_id}
        return {
            "chapter_id": chapter_id,
            "cleared_count": 2,
        }


def _install_test_dependencies(monkeypatch):
    fake_service = _FakeSelectionRewriteService()
    monkeypatch.setenv("INKTRACE_P2_ENABLE_SELECTION_REWRITE", "1")
    monkeypatch.setattr(dependencies, "get_selection_rewrite_service", lambda: fake_service)
    return fake_service


def test_selection_rewrite_api_supports_create_get_apply_and_reject(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    client = TestClient(app)

    create_response = client.post(
        "/api/v2/ai/selection-rewrite",
        json={
            "work_id": "work_001",
            "chapter_id": "chapter_001",
            "chapter_revision": 3,
            "draft_revision": 12,
            "draft_text_hash": "hash_draft",
            "draft_length": 120,
            "source_text": "他走进房间",
            "source_hash": "hash_source",
            "start_pos": 3,
            "end_pos": 8,
            "context_before": "前文片段",
            "context_after": "后文片段",
            "mode": "rewrite",
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()["data"]["rewrite_id"] == "srw_001"
    assert create_response.json()["data"]["status"] == "generating"
    assert create_response.json()["data"]["request_id"] == "job_001"
    assert fake_service.rewrite_payload["draft_text_hash"] == "hash_draft"
    assert fake_service.rewrite_payload["draft_length"] == 120
    assert fake_service.rewrite_payload["context_before"] == "前文片段"
    assert fake_service.rewrite_payload["context_after"] == "后文片段"

    get_response = client.get("/api/v2/ai/selection-rewrite/srw_001")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["status"] == "pending"

    history_response = client.get("/api/v2/ai/selection-rewrite/chapters/chapter_001/history")
    assert history_response.status_code == 200
    assert history_response.json()["data"]["items"][0]["rewrite_id"] == "srw_hist_001"
    assert fake_service.list_payload == {"chapter_id": "chapter_001"}

    apply_response = client.post(
        "/api/v2/ai/selection-rewrite/srw_001/apply",
        json={
            "final_text": "他缓步走进房间",
            "chapter_revision": 3,
            "draft_revision": 12,
            "draft_text_hash": "hash_draft",
            "draft_length": 120,
            "range_text": "他走进房间",
            "caller_type": "user_action",
        },
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["data"]["patch"]["replacement"] == "他缓步走进房间"
    assert fake_service.apply_payload["draft_text_hash"] == "hash_draft"
    assert fake_service.apply_payload["range_text"] == "他走进房间"

    reject_response = client.post("/api/v2/ai/selection-rewrite/srw_001/reject")
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["status"] == "rejected"

    clear_response = client.delete("/api/v2/ai/selection-rewrite/chapters/chapter_001/history")
    assert clear_response.status_code == 200
    assert clear_response.json()["data"]["cleared_count"] == 2
    assert fake_service.clear_payload == {"chapter_id": "chapter_001"}


def test_selection_rewrite_api_rejects_non_user_apply(monkeypatch) -> None:
    _install_test_dependencies(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/selection-rewrite/srw_001/apply",
        json={
            "final_text": "他缓步走进房间",
            "chapter_revision": 3,
            "draft_revision": 12,
            "draft_text_hash": "hash_draft",
            "draft_length": 120,
            "range_text": "他走进房间",
            "caller_type": "agent",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "caller_type_forbidden"
