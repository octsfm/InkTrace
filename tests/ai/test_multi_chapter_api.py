from __future__ import annotations

import hashlib
import time

from fastapi.testclient import TestClient

from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import AIProviderConfig, AISettings, ModelSelection
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_database_path
from presentation.api import dependencies
from presentation.api.app import app


def _reset_dependencies() -> None:
    get_database_path.cache_clear()
    dependencies.get_ai_job_store.cache_clear()
    dependencies.get_initialization_repository.cache_clear()
    dependencies.get_story_memory_repository.cache_clear()
    dependencies.get_story_state_repository.cache_clear()
    dependencies.get_context_pack_repository.cache_clear()
    dependencies.get_candidate_draft_repository.cache_clear()
    dependencies.get_settings_cipher.cache_clear()
    dependencies.get_provider_registry.cache_clear()
    dependencies.get_work_service.cache_clear()
    dependencies.get_chapter_service.cache_clear()
    dependencies.get_ai_job_service.cache_clear()
    dependencies.get_core_tool_facade.cache_clear()
    dependencies.get_continuation_workflow.cache_clear()
    if hasattr(dependencies, "get_multi_chapter_repository"):
        dependencies.get_multi_chapter_repository.cache_clear()
    if hasattr(dependencies, "get_multi_chapter_service"):
        dependencies.get_multi_chapter_service.cache_clear()
    if hasattr(dependencies, "get_citation_link_repository"):
        dependencies.get_citation_link_repository.cache_clear()
    if hasattr(dependencies, "get_citation_link_service"):
        dependencies.get_citation_link_service.cache_clear()
    if hasattr(dependencies, "get_citation_vector_recall_service"):
        dependencies.get_citation_vector_recall_service.cache_clear()


def _seed_writer_model_settings() -> None:
    cipher = dependencies.get_settings_cipher()
    dependencies.get_ai_settings_repository().save(
        AISettings(
            provider_configs={
                "fake": AIProviderConfig(
                    provider_name="fake",
                    enabled=True,
                    encrypted_api_key=cipher.encrypt("fake-api-key"),
                    default_model="fake-chat",
                )
            },
            model_role_mappings={
                "writer": ModelSelection(provider_name="fake", model_name="fake-chat"),
            },
        )
    )


def _seed_initialized_work() -> tuple[str, str]:
    _seed_writer_model_settings()
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("P2-S1 API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在灯塔里找到被海风侵蚀的航海图残页。",
        expected_version=1,
    )
    dependencies.get_initialization_service().start_initialization(work.id, created_by="user_action")
    return work.id, chapter.id.value


def _wait_until_ready(client: TestClient, session_id: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/v2/ai/multi-chapter/{session_id}/progress")
        if response.status_code == 200 and response.json()["data"]["status"] == "waiting_user_decision":
            return response.json()["data"]
        time.sleep(0.05)
    raise AssertionError("multi chapter session did not become ready in time")


def test_multi_chapter_api_starts_and_reports_progress(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_MULTI_CHAPTER", "1")
    _reset_dependencies()
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/multi-chapter/start",
        json={
            "work_id": work_id,
            "start_chapter_id": chapter_id,
            "target_chapters": 2,
            "user_instruction": "继续推进灯塔谜团。",
            "caller_type": "user_action",
            "idempotency_key": "mc-start-1",
        },
    )

    assert start_response.status_code == 202
    session_id = start_response.json()["data"]["session_id"]
    progress = _wait_until_ready(client, session_id)

    assert progress["session_id"] == session_id
    assert progress["current_index"] == 1
    assert progress["target_chapters"] == 2
    assert progress["per_chapter"][0]["candidate_draft_id"].startswith("cd_")


def test_multi_chapter_advance_api_rejects_non_user_action_caller(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_MULTI_CHAPTER", "1")
    _reset_dependencies()
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/multi-chapter/start",
        json={
            "work_id": work_id,
            "start_chapter_id": chapter_id,
            "target_chapters": 2,
            "caller_type": "user_action",
            "idempotency_key": "mc-start-2",
        },
    )
    session_id = start_response.json()["data"]["session_id"]
    _wait_until_ready(client, session_id)

    response = client.post(
        f"/api/v2/ai/multi-chapter/{session_id}/advance",
        json={
            "decision": "continue_without_apply",
            "caller_type": "agent",
            "user_action": True,
            "idempotency_key": "mc-advance-forbidden-1",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "P2_CALLER_FORBIDDEN"


def test_multi_chapter_advance_api_accepts_user_action_and_moves_to_next_chapter(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_MULTI_CHAPTER", "1")
    _reset_dependencies()
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/multi-chapter/start",
        json={
            "work_id": work_id,
            "start_chapter_id": chapter_id,
            "target_chapters": 2,
            "caller_type": "user_action",
            "idempotency_key": "mc-start-advance-allow-1",
        },
    )
    session_id = start_response.json()["data"]["session_id"]
    _wait_until_ready(client, session_id)

    response = client.post(
        f"/api/v2/ai/multi-chapter/{session_id}/advance",
        json={
            "decision": "continue_without_apply",
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "mc-advance-allow-1",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["session_id"] == session_id
    assert response.json()["data"]["current_index"] == 2
    assert response.json()["data"]["next_chapter_available"] is False


def test_multi_chapter_cancel_api_cancels_session_for_user_action(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_MULTI_CHAPTER", "1")
    _reset_dependencies()
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/multi-chapter/start",
        json={
            "work_id": work_id,
            "start_chapter_id": chapter_id,
            "target_chapters": 2,
            "caller_type": "user_action",
            "idempotency_key": "mc-start-cancel-allow-1",
        },
    )
    session_id = start_response.json()["data"]["session_id"]

    response = client.post(
        f"/api/v2/ai/multi-chapter/{session_id}/cancel",
        json={
            "caller_type": "user_action",
            "user_action": True,
            "idempotency_key": "mc-cancel-allow-1",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["session_id"] == session_id
    assert response.json()["data"]["status"] == "cancelled"
    assert response.json()["data"]["cancelled_at"]


def test_multi_chapter_generated_citations_can_be_verified_without_monkeypatch_service(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_MULTI_CHAPTER", "1")
    monkeypatch.setenv("INKTRACE_P2_ENABLE_CITATION_LINK", "1")
    _reset_dependencies()
    work_id, chapter_id = _seed_initialized_work()
    client = TestClient(app)

    start_response = client.post(
        "/api/v2/ai/multi-chapter/start",
        json={
            "work_id": work_id,
            "start_chapter_id": chapter_id,
            "target_chapters": 1,
            "user_instruction": "请引用第一章前文线索继续推进灯塔谜团。",
            "caller_type": "user_action",
            "idempotency_key": "mc-start-citation-verify-1",
        },
    )

    assert start_response.status_code == 202
    session_id = start_response.json()["data"]["session_id"]
    progress = _wait_until_ready(client, session_id)
    candidate_draft_id = progress["per_chapter"][0]["candidate_draft_id"]

    draft_response = client.get(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}")
    assert draft_response.status_code == 200
    selected_version_id = draft_response.json()["data"]["selected_version_id"]
    assert draft_response.json()["data"]["metadata"]["citation_status"] == "ready"
    assert draft_response.json()["data"]["metadata"]["citation_count"] >= 1

    citation_response = client.get(f"/api/v2/ai/citations/candidate-version/{selected_version_id}")
    assert citation_response.status_code == 200
    assert citation_response.json()["data"]["batch"]["total_count"] >= 1

    source_hash = f"sha256:{hashlib.sha256('顾迟在灯塔里找到被海风侵蚀的航海图残页。'.encode('utf-8')).hexdigest()}"
    verify_response = client.post(
        "/api/v2/ai/citations/verify",
        json={
            "candidate_version_id": selected_version_id,
            "citations": [
                {
                    "source_type": "chapter",
                    "source_name": "第一章",
                    "source_hash": source_hash,
                    "context_in_draft": "顾迟发现海图的线索",
                    "confidence": 0.88,
                }
            ],
        },
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["data"]["batch"]["citations"][0]["verification_status"] == "verified"
