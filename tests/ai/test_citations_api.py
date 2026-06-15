from __future__ import annotations

from fastapi.testclient import TestClient

from application.services.ai.citation_link_service import CitationLinkService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import (
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
    CandidateDraftVersion,
    CandidateDraftVersionStatus,
)
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_database_path
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.persistence.sqlite_citation_link_repo import SQLiteCitationLinkRepository
from presentation.api import dependencies
from presentation.api.app import app


def _reset_dependencies() -> None:
    get_database_path.cache_clear()
    dependencies.get_candidate_draft_repository.cache_clear()
    if hasattr(dependencies, "get_citation_link_repository"):
        dependencies.get_citation_link_repository.cache_clear()
    if hasattr(dependencies, "get_citation_link_service"):
        dependencies.get_citation_link_service.cache_clear()


def _seed_citation_data(tmp_path) -> tuple[str, str, str]:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("Citation API 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在灯塔夹层发现父亲留下的海图坐标。",
        expected_version=1,
    )
    candidate_store = dependencies.get_candidate_draft_repository()
    draft = candidate_store.save(
        CandidateDraft(
            candidate_draft_id="cd_api_citation_1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            source_context_pack_id="cp_1",
            source_job_id="job_1",
            status=CandidateDraftStatus.PENDING_REVIEW,
            selected_version_id="ver_api_citation_1",
            latest_version_no=1,
            content="候选稿正文",
            content_preview="候选稿正文",
            word_count=4,
            char_count=4,
            validation_status=CandidateDraftValidationStatus.PASSED,
            created_at="2026-06-09T00:00:00+00:00",
            updated_at="2026-06-09T00:00:00+00:00",
        )
    )
    version = candidate_store.save_version(
        CandidateDraftVersion(
            candidate_version_id="ver_api_citation_1",
            candidate_draft_id=draft.candidate_draft_id,
            work_id=work.id,
            chapter_id=chapter.id.value,
            version_no=1,
            status=CandidateDraftVersionStatus.GENERATED,
            content="候选稿正文",
            content_summary="候选稿正文摘要",
            word_count=4,
            source_context_pack_id="cp_1",
            created_at="2026-06-09T00:00:00+00:00",
            updated_at="2026-06-09T00:00:00+00:00",
        )
    )
    service = dependencies.get_citation_link_service()
    service.process_candidate_citations(
        candidate_version_id=version.candidate_version_id,
        raw_citations=[
            {
                "source_type": "chapter",
                "source_name": "第一章",
                "source_id_hint": chapter.id.value,
                "context_in_draft": "父亲留下的海图",
                "confidence": 0.95,
            }
        ],
    )
    return draft.candidate_draft_id, version.candidate_version_id, chapter.id.value


def test_citations_api_exposes_candidate_version_draft_source_and_detail(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    monkeypatch.setenv("INKTRACE_P2_ENABLE_CITATION_LINK", "1")
    _reset_dependencies()
    candidate_draft_id, candidate_version_id, chapter_id = _seed_citation_data(tmp_path)
    client = TestClient(app)

    version_response = client.get(f"/api/v2/ai/citations/candidate-version/{candidate_version_id}")
    draft_response = client.get(f"/api/v2/ai/citations/candidate-draft/{candidate_draft_id}")
    source_response = client.get("/api/v2/ai/citations/source", params={"source_type": "chapter", "source_id": chapter_id})
    detail_response = client.get(f"/api/v2/ai/citations/{draft_response.json()['data']['batches'][0]['citations'][0]['citation_id']}/source-detail")

    assert version_response.status_code == 200
    assert version_response.json()["data"]["batch"]["candidate_version_id"] == candidate_version_id
    assert version_response.json()["data"]["batch"]["citations"][0]["source_type"] == "chapter"
    assert draft_response.status_code == 200
    assert draft_response.json()["data"]["batches"][0]["candidate_draft_id"] == candidate_draft_id
    assert source_response.status_code == 200
    assert source_response.json()["data"]["citations"][0]["source_id"] == chapter_id
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["source_id"] == chapter_id
    assert detail_response.json()["data"]["is_active"] is True

