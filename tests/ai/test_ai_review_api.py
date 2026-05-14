from __future__ import annotations

from fastapi.testclient import TestClient

from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _clear_singletons() -> None:
    dependencies.get_ai_settings_repository.cache_clear()
    dependencies.get_provider_registry.cache_clear()
    dependencies.get_model_router.cache_clear()
    dependencies.get_llm_call_log_repository.cache_clear()
    dependencies.get_candidate_draft_repository.cache_clear()
    dependencies.get_ai_review_repository.cache_clear()
    dependencies.get_ai_review_service.cache_clear()


def test_ai_review_api_review_get_list(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    get_database_path.cache_clear()
    _clear_singletons()
    client = TestClient(app)

    # create candidate draft via continuation API (already uses FakeWriter, no external calls)
    work_id, chapter_id = _seed_initialized_work(client)
    start = client.post("/api/v2/ai/continuations", json={"work_id": work_id, "chapter_id": chapter_id, "user_instruction": "继续"})
    assert start.status_code == 200
    candidate_id = start.json()["data"]["candidate_draft_id"]

    review = client.post(f"/api/v2/ai/reviews/candidate-drafts/{candidate_id}", json={"user_instruction": "关注一致性"})
    assert review.status_code == 200
    payload = review.json()
    review_id = payload["data"]["review_id"]
    assert review_id.startswith("rv_")
    assert payload["data"]["status"] in {"completed", "completed_with_warnings", "failed", "skipped", "blocked"}
    assert "api_key" not in str(payload)

    get_resp = client.get(f"/api/v2/ai/reviews/{review_id}")
    assert get_resp.status_code == 200
    get_payload = get_resp.json()
    assert get_payload["data"]["review_id"] == review_id
    assert "issues" in get_payload["data"]

    list_resp = client.get("/api/v2/ai/reviews", params={"work_id": work_id, "candidate_draft_id": candidate_id})
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload["data"]["items"][0]["review_id"] == review_id


def _seed_initialized_work(client: TestClient) -> tuple[str, str]:
    # Create work/chapter with v1 services is too coupled to container here; reuse existing initialization API
    work_service = dependencies.get_work_service()
    chapter_service = dependencies.get_chapter_service()
    work = work_service.create_work("S8 API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(chapter.id.value, title="第一章", content="测试正文。", expected_version=1)
    init = client.post("/api/v2/ai/initializations", json={"work_id": work.id})
    assert init.status_code == 200
    return work.id, chapter.id.value


def test_ai_review_api_requires_work_id_for_list(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    get_database_path.cache_clear()
    _clear_singletons()
    client = TestClient(app)

    resp = client.get("/api/v2/ai/reviews")
    assert resp.status_code == 422


def test_ai_review_api_rejects_non_user_action_caller_type(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    get_database_path.cache_clear()
    _clear_singletons()
    client = TestClient(app)

    work_id, chapter_id = _seed_initialized_work(client)
    start = client.post("/api/v2/ai/continuations", json={"work_id": work_id, "chapter_id": chapter_id, "user_instruction": "继续"})
    assert start.status_code == 200
    candidate_id = start.json()["data"]["candidate_draft_id"]

    review = client.post(
        f"/api/v2/ai/reviews/candidate-drafts/{candidate_id}",
        json={"user_instruction": "关注一致性", "caller_type": "workflow"},
    )
    assert review.status_code == 403
    assert review.json()["error"]["error_code"] == "caller_type_not_allowed"


def test_ai_review_api_rejects_invalid_caller_type_before_service_invocation(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    get_database_path.cache_clear()
    _clear_singletons()
    client = TestClient(app)
    work_id, chapter_id = _seed_initialized_work(client)
    start = client.post("/api/v2/ai/continuations", json={"work_id": work_id, "chapter_id": chapter_id, "user_instruction": "继续"})
    assert start.status_code == 200
    candidate_id = start.json()["data"]["candidate_draft_id"]

    class _ExplodingReviewService:
        def review_candidate_draft(self, *args, **kwargs):
            raise AssertionError("service_should_not_be_called")

    monkeypatch.setattr(dependencies, "get_ai_review_service", lambda: _ExplodingReviewService())

    review = client.post(
        f"/api/v2/ai/reviews/candidate-drafts/{candidate_id}",
        json={"user_instruction": "关注一致性", "caller_type": "workflow"},
    )

    assert review.status_code == 403
    assert review.json()["error"]["error_code"] == "caller_type_not_allowed"
