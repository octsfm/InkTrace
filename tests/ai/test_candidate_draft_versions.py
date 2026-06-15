from __future__ import annotations

from pathlib import Path

from application.services.ai.candidate_review_service import CandidateReviewService
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
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.v1 import connect


def _build_services(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts_versions.json")
    review_service = CandidateReviewService(
        candidate_draft_repository=candidate_store,
        chapter_service=chapter_service,
    )
    return work_service, chapter_service, candidate_store, review_service


def _seed_draft_with_versions(tmp_path: Path):
    work_service, chapter_service, candidate_store, review_service = _build_services(tmp_path)
    work = work_service.create_work("P1-S6 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="原始章节内容。",
        expected_version=1,
    )
    draft = candidate_store.save(
        CandidateDraft(
            candidate_draft_id="cd_versions",
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="agent_session_1",
            writing_task_id="wt_1",
            direction_plan_snapshot_id="snap_1",
            source_context_pack_id="cp_1",
            source_job_id="job_1",
            status=CandidateDraftStatus.GENERATED,
            content="v1 候选稿",
            content_preview="v1 候选稿",
            word_count=2,
            char_count=6,
            validation_status=CandidateDraftValidationStatus.PASSED,
            latest_version_no=2,
            selected_version_id="ver_1",
            created_by="workflow",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    version_1 = candidate_store.save_version(
        CandidateDraftVersion(
            candidate_version_id="ver_1",
            candidate_draft_id=draft.candidate_draft_id,
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="agent_session_1",
            version_no=1,
            status=CandidateDraftVersionStatus.GENERATED,
            content="v1 候选稿",
            content_summary="v1 摘要",
            word_count=2,
            writing_task_id="wt_1",
            direction_plan_snapshot_id="snap_1",
            source_context_pack_id="cp_1",
            created_by="writer_agent",
            created_at="2026-05-21T00:00:00+00:00",
            updated_at="2026-05-21T00:00:00+00:00",
        )
    )
    version_2 = candidate_store.save_version(
        CandidateDraftVersion(
            candidate_version_id="ver_2",
            candidate_draft_id=draft.candidate_draft_id,
            work_id=work.id,
            chapter_id=chapter.id.value,
            agent_session_id="agent_session_2",
            source_candidate_draft_id=draft.candidate_draft_id,
            source_version_id="ver_1",
            parent_version_id="ver_1",
            version_no=2,
            status=CandidateDraftVersionStatus.GENERATED,
            content="v2 修订稿",
            content_summary="v2 摘要",
            word_count=2,
            writing_task_id="wt_1",
            direction_plan_snapshot_id="snap_1",
            source_context_pack_id="cp_1",
            created_by="rewriter_agent",
            created_at="2026-05-21T00:10:00+00:00",
            updated_at="2026-05-21T00:10:00+00:00",
        )
    )
    return work, chapter, candidate_store, review_service, version_1, version_2


def test_candidate_draft_store_persists_versions_and_lists_chain(tmp_path: Path) -> None:
    work, chapter, candidate_store, _, _, version_2 = _seed_draft_with_versions(tmp_path)

    draft = candidate_store.get("cd_versions")
    versions = candidate_store.list_versions("cd_versions")
    stored_v2 = candidate_store.get_version(version_2.candidate_version_id)

    assert draft.selected_version_id == "ver_1"
    assert draft.latest_version_no == 2
    assert draft.revision_count == 0
    assert draft.applied_at == ""
    assert [item.candidate_version_id for item in versions] == ["ver_1", "ver_2"]
    assert stored_v2.parent_version_id == "ver_1"
    assert stored_v2.status == CandidateDraftVersionStatus.GENERATED
    assert stored_v2.work_id == work.id
    assert stored_v2.chapter_id == chapter.id.value


def test_candidate_review_service_select_accept_apply_specific_version_preserves_three_pointers(tmp_path: Path) -> None:
    work, chapter, candidate_store, review_service, _, _ = _seed_draft_with_versions(tmp_path)

    selected = review_service.select_candidate_version(
        "cd_versions",
        candidate_version_id="ver_2",
        user_id="user_1",
        user_action=True,
    )
    accepted = review_service.accept_candidate(
        "cd_versions",
        candidate_version_id="ver_2",
        user_id="user_1",
        user_action=True,
    )
    result = review_service.apply_candidate_to_draft(
        "cd_versions",
        candidate_version_id="ver_2",
        user_id="user_1",
        expected_chapter_version=chapter.version,
        user_action=True,
        idempotency_key="apply-ver-2",
    )

    draft = review_service.get_candidate_draft("cd_versions")
    applied_version = candidate_store.get_version("ver_2")
    chapter_after = [item for item in review_service._chapter_service.list_chapters(work.id) if item.id.value == chapter.id.value][0]  # noqa: SLF001

    assert selected.selected_version_id == "ver_2"
    assert accepted.accepted_version_id == "ver_2"
    assert accepted.applied_version_id == ""
    assert result["status"] == "applied"
    assert draft.selected_version_id == "ver_2"
    assert draft.accepted_version_id == "ver_2"
    assert draft.applied_version_id == "ver_2"
    assert draft.applied_at
    assert applied_version.status == CandidateDraftVersionStatus.APPLIED
    assert chapter_after.content.endswith("v2 修订稿")


def test_candidate_draft_store_projects_latest_snapshot_to_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "runtime.db"
    store = FileCandidateDraftStore(
        tmp_path / "candidate_drafts_versions.json",
        database_path=db_path,
    )
    draft = CandidateDraft(
        candidate_draft_id="cd_sqlite",
        work_id="work-1",
        chapter_id="chapter-1",
        agent_session_id="agent-session-1",
        writing_task_id="wt-1",
        direction_plan_snapshot_id="snap-1",
        source_context_pack_id="cp-1",
        source_job_id="job-1",
        status=CandidateDraftStatus.GENERATED,
        content="初稿",
        content_preview="初稿",
        word_count=2,
        char_count=2,
        validation_status=CandidateDraftValidationStatus.PASSED,
        latest_version_no=1,
        revision_count=0,
        created_by="workflow",
        created_at="2026-06-09T00:00:00+00:00",
        updated_at="2026-06-09T00:00:00+00:00",
    )
    store.save(draft)
    store.save(
        draft.model_copy(
            update={
                "status": CandidateDraftStatus.APPLIED,
                "revision_count": 2,
                "applied_at": "2026-06-09T01:00:00+00:00",
                "updated_at": "2026-06-09T01:00:00+00:00",
            }
        )
    )

    conn = connect(db_path)
    row = conn.execute(
        "SELECT candidate_draft_id, work_id, chapter_id, status, applied_at, revision_count, updated_at "
        "FROM candidate_drafts WHERE candidate_draft_id = ?",
        ("cd_sqlite",),
    ).fetchone()
    count_row = conn.execute("SELECT COUNT(*) AS total FROM candidate_drafts WHERE candidate_draft_id = ?", ("cd_sqlite",)).fetchone()
    conn.close()

    assert row is not None
    assert row["candidate_draft_id"] == "cd_sqlite"
    assert row["work_id"] == "work-1"
    assert row["chapter_id"] == "chapter-1"
    assert row["status"] == CandidateDraftStatus.APPLIED.value
    assert row["applied_at"] == "2026-06-09T01:00:00+00:00"
    assert row["revision_count"] == 2
    assert row["updated_at"] == "2026-06-09T01:00:00+00:00"
    assert count_row["total"] == 1
