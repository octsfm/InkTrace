from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from domain.entities.ai.models import VectorIndexBuildResult
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from presentation.api import dependencies
from presentation.api.app import app


def _publish_chapter(chapter_service: ChapterService, chapter_id: str) -> None:
    chapter = chapter_service.chapter_repo.find_by_id(chapter_id)
    assert chapter is not None
    chapter.publish(datetime.now(timezone.utc))
    chapter_service.chapter_repo.save(chapter)


def _seed_work_with_published_chapters(*, chapter_count: int = 1) -> tuple[str, list[str]]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("Reindex API 作品", "作者")
    chapter_ids: list[str] = []
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在旧灯塔里发现父亲留下的海图残页。" * 30,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)
    chapter_ids.append(chapter.id.value)
    for index in range(2, chapter_count + 1):
        created = chapter_service.create_chapter(work.id, f"第{index}章")
        chapter_service.update_chapter(
            created.id.value,
            title=f"第{index}章",
            content=(f"第{index}章的潮汐图指向更远的海域。" * 30),
            expected_version=1,
        )
        _publish_chapter(chapter_service, created.id.value)
        chapter_ids.append(created.id.value)
    return work.id, chapter_ids


def test_reindex_api_full_work_creates_job() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "user_action",
            "idempotency_key": "idem_full_work_create_job",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data"]["job_type"] == "vector_indexing"
    assert payload["data"]["operation"] == "reindex"
    assert payload["data"]["work_id"] == work_id
    assert payload["data"]["index_scope"] == "full_work"
    assert payload["data"]["target_chapter_ids"] == []
    assert payload["data"]["status"] == "queued"
    assert payload["data"]["reused_existing_job"] is False
    assert "payload" not in payload["data"]


def test_reindex_api_single_chapter_creates_job() -> None:
    work_id, chapter_ids = _seed_work_with_published_chapters(chapter_count=2)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "chapter",
            "target_chapter_ids": [chapter_ids[0]],
            "caller_type": "user_action",
            "idempotency_key": "idem_single_chapter_job",
        },
    )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["index_scope"] == "chapter"
    assert data["target_chapter_ids"] == [chapter_ids[0]]
    assert data["status"] == "queued"


def test_reindex_api_multi_chapter_creates_job() -> None:
    work_id, chapter_ids = _seed_work_with_published_chapters(chapter_count=3)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "chapter",
            "target_chapter_ids": chapter_ids,
            "caller_type": "user_action",
            "idempotency_key": "idem_multi_chapter_job",
        },
    )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["index_scope"] == "chapter"
    assert data["target_chapter_ids"] == chapter_ids
    assert data["status"] == "queued"


def test_reindex_api_idempotency_returns_existing_job() -> None:
    work_id, chapter_ids = _seed_work_with_published_chapters(chapter_count=2)
    client = TestClient(app)
    payload = {
        "work_id": work_id,
        "index_scope": "chapter",
        "target_chapter_ids": chapter_ids,
        "caller_type": "user_action",
        "idempotency_key": "idem_reuse_existing_job",
    }

    first = client.post("/api/v2/ai/vector-index/reindex", json=payload)
    second = client.post("/api/v2/ai/vector-index/reindex", json=payload)

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["data"]["job_id"] == first.json()["data"]["job_id"]
    assert second.json()["data"]["reused_existing_job"] is True


def test_reindex_api_job_completed_index_status_updated() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    service = dependencies.get_vector_reindex_service()
    job = service.start_reindex(
        work_id=work_id,
        index_scope="full_work",
        created_by="user_action",
    )

    assert job.status.value == "completed"
    assert job.result_summary["index_status"] in {"ready", "degraded"}


def test_reindex_api_status_query_via_job_api() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "user_action",
            "idempotency_key": "idem_status_query",
        },
    )
    job_id = response.json()["data"]["job_id"]
    status_response = client.get(f"/api/v2/ai/jobs/{job_id}")

    assert response.status_code == 202
    assert status_response.status_code == 200
    data = status_response.json()["data"]
    assert data["job_id"] == job_id
    assert data["status"] in {"queued", "running", "completed", "failed"}
    assert "payload" not in data


def test_reindex_api_cancel_via_job_api() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    service = dependencies.get_vector_reindex_service()
    job = service.start_reindex(
        work_id=work_id,
        index_scope="full_work",
        created_by="user_action",
        auto_run=False,
    )
    client = TestClient(app)

    response = client.post(
        f"/api/v2/ai/jobs/{job.job_id}/cancel",
        json={"reason": "user_cancelled"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cancelled"


def test_reindex_api_retry_failed_job() -> None:
    class _FailOnceService:
        def __init__(self) -> None:
            self.call_count = 0

        def reindex_work(self, work_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
            self.call_count += 1
            if self.call_count == 1:
                return VectorIndexBuildResult(
                    index_status="failed",
                    failed_chunk_count=1,
                    degraded_reason="index_build_failed",
                )
            return VectorIndexBuildResult(
                index_status="ready",
                indexed_chapter_count=1,
                indexed_chunk_count=2,
            )

        def reindex_chapter(self, work_id: str, chapter_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
            return self.reindex_work(work_id, should_continue=should_continue)

    work_id, _chapter_ids = _seed_work_with_published_chapters()
    original_service = dependencies.get_vector_reindex_service()
    failing_service = _FailOnceService()
    dependencies.get_vector_reindex_service()._vector_index_service = failing_service
    try:
        job = dependencies.get_vector_reindex_service().start_reindex(
            work_id=work_id,
            index_scope="full_work",
            created_by="user_action",
        )
        retried = dependencies.get_vector_reindex_service().retry_and_run(job.job_id)
    finally:
        dependencies.get_vector_reindex_service()._vector_index_service = original_service._vector_index_service

    assert job.status.value == "failed"
    assert retried.status.value == "completed"
    assert retried.result_summary["index_status"] == "ready"


def test_reindex_api_force_rebuild_creates_new_job() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    service = dependencies.get_vector_reindex_service()
    first = service.start_reindex(
        work_id=work_id,
        index_scope="full_work",
        created_by="user_action",
    )
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "user_action",
            "force_rebuild": True,
            "idempotency_key": "idem_force_rebuild_new_job",
        },
    )

    assert first.status.value == "completed"
    assert response.status_code == 202
    assert response.json()["data"]["job_id"] != first.job_id
    assert response.json()["data"]["reused_existing_job"] is False


def test_reindex_api_invalid_scope_rejected() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "invalid",
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "P2_VECTOR_INVALID_INDEX_SCOPE"


def test_reindex_api_chapter_missing_target_ids_rejected() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "chapter",
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED"


def test_reindex_api_full_work_with_target_ids_rejected() -> None:
    work_id, chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "target_chapter_ids": chapter_ids,
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "P2_VECTOR_TARGET_CHAPTER_IDS_NOT_ALLOWED"


def test_reindex_api_work_not_found() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": "work_missing",
            "index_scope": "full_work",
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["error_code"] == "P2_VECTOR_WORK_NOT_FOUND"


def test_reindex_api_chapter_not_in_work_rejected() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    other_work_id, other_chapter_ids = _seed_work_with_published_chapters()
    assert work_id != other_work_id
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "chapter",
            "target_chapter_ids": [other_chapter_ids[0]],
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "P2_VECTOR_CHAPTER_NOT_IN_WORK"


def test_reindex_api_agent_caller_rejected() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "workflow",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "P2_VECTOR_CALLER_FORBIDDEN"


def test_reindex_api_system_caller_rejected() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "system",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["error_code"] == "P2_VECTOR_CALLER_FORBIDDEN"


def test_reindex_api_concurrent_rejected() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    service = dependencies.get_vector_reindex_service()
    service.start_reindex(
        work_id=work_id,
        index_scope="full_work",
        created_by="user_action",
        auto_run=False,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["error_code"] == "P2_VECTOR_INDEXING_IN_PROGRESS"


def test_reindex_api_vector_store_unavailable(monkeypatch) -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    monkeypatch.setattr(dependencies, "get_vector_store", lambda: (_ for _ in ()).throw(RuntimeError("vector store down")))

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["error_code"] == "P2_VECTOR_STORE_UNAVAILABLE"


def test_reindex_api_embedding_unavailable(monkeypatch) -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    monkeypatch.setattr(dependencies, "get_embedding_provider", lambda: (_ for _ in ()).throw(RuntimeError("provider down")))

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["error_code"] == "P2_VECTOR_EMBEDDING_UNAVAILABLE"


def test_reindex_api_idempotency_key_mismatch_conflict() -> None:
    work_id, chapter_ids = _seed_work_with_published_chapters(chapter_count=3)
    client = TestClient(app)
    idempotency_key = "idem_conflict_key"

    first = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "chapter",
            "target_chapter_ids": chapter_ids[:2],
            "caller_type": "user_action",
            "idempotency_key": idempotency_key,
        },
    )
    second = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "chapter",
            "target_chapter_ids": [chapter_ids[2]],
            "caller_type": "user_action",
            "idempotency_key": idempotency_key,
        },
    )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error"]["error_code"] == "P2_VECTOR_IDEMPOTENCY_CONFLICT"


def test_reindex_api_response_excludes_internal_data() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters()
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "full_work",
            "caller_type": "user_action",
            "idempotency_key": "idem_response_excludes_internal_data",
        },
    )

    assert response.status_code == 202
    data = response.json()["data"]
    assert "payload" not in data
    assert "input_snapshot" not in data
    assert "params" not in data
    assert "metadata" not in data


def test_reindex_api_too_many_chapters_rejected() -> None:
    work_id, _chapter_ids = _seed_work_with_published_chapters(chapter_count=1)
    client = TestClient(app)

    response = client.post(
        "/api/v2/ai/vector-index/reindex",
        json={
            "work_id": work_id,
            "index_scope": "chapter",
            "target_chapter_ids": [f"chapter_{index}" for index in range(51)],
            "caller_type": "user_action",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "P2_VECTOR_TOO_MANY_CHAPTERS"


def test_reindex_api_log_excludes_full_text(caplog, monkeypatch) -> None:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("日志脱敏作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    secret_content = "API_KEY_SHOULD_NOT_LEAK chunk_text_should_not_leak 完整正文禁止入日志 " * 20
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content=secret_content,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)

    caplog.set_level(logging.INFO, logger="application.services.ai.vector_reindex_service")
    job = dependencies.get_vector_reindex_service().start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
        idempotency_key="idem_log_redaction",
    )

    logged_text = "\n".join(record.getMessage() for record in caplog.records)
    assert job.status.value == "completed"
    assert logged_text
    assert "API_KEY_SHOULD_NOT_LEAK" not in logged_text
    assert "chunk_text_should_not_leak" not in logged_text
    assert "完整正文禁止入日志" not in logged_text
    assert "text_excerpt" not in logged_text
    assert "embedding" not in logged_text


def test_reindex_api_log_excludes_chunk_text() -> None:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("结果脱敏作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    leaked_excerpt = "RESULT_SUMMARY_CHUNK_TEXT_SHOULD_NOT_LEAK " * 20
    chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content=leaked_excerpt,
        expected_version=1,
    )
    _publish_chapter(chapter_service, chapter.id.value)

    job = dependencies.get_vector_reindex_service().start_reindex(
        work_id=work.id,
        index_scope="full_work",
        created_by="user_action",
    )

    serialized = json.dumps(job.result_summary, ensure_ascii=False)
    assert job.status.value == "completed"
    assert "RESULT_SUMMARY_CHUNK_TEXT_SHOULD_NOT_LEAK" not in serialized
    assert "text_excerpt" not in serialized
    assert "chunk_text" not in serialized
