from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from application.services.ai.candidate_review_service import CandidateReviewService
from application.services.ai.continuation_workflow import MinimalContinuationWorkflow
from application.services.ai.context_pack_service import ContextPackService
from application.services.ai.initialization_service import InitializationApplicationService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from domain.entities.ai.models import CandidateDraft, CandidateDraftStatus, CandidateDraftValidationStatus
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.repositories.ai.file_ai_job_store import FileAIJobStore
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_context_pack_store import FileContextPackStore
from infrastructure.database.repositories.ai.file_initialization_store import FileInitializationStore
from infrastructure.database.repositories.ai.file_story_memory_store import FileStoryMemoryStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore
from presentation.api.app import app


def _stores(tmp_path: Path):
    job_store = FileAIJobStore(tmp_path / "jobs.json")
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    init_store = FileInitializationStore(tmp_path / "initializations.json")
    memory_store = FileStoryMemoryStore(tmp_path / "memory.json")
    state_store = FileStoryStateStore(tmp_path / "state.json")
    context_store = FileContextPackStore(tmp_path / "context_packs.json")
    return job_store, candidate_store, init_store, memory_store, state_store, context_store


def _build_services(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    job_store, candidate_store, init_store, memory_store, state_store, _ = _stores(tmp_path)
    init_service = InitializationApplicationService(
        work_service=work_service,
        chapter_service=chapter_service,
        job_repository=job_store,
        step_repository=job_store,
        attempt_repository=job_store,
        initialization_repository=init_store,
        story_memory_repository=memory_store,
        story_state_repository=state_store,
    )
    review_service = CandidateReviewService(
        candidate_draft_repository=candidate_store,
        chapter_service=chapter_service,
        initialization_service=init_service,
    )
    return work_service, chapter_service, init_service, review_service, candidate_store


def _create_initialized_work(tmp_path: Path):
    work_service, chapter_service, init_service, review_service, candidate_store = _build_services(tmp_path)
    work = work_service.create_work("S6 Work", "Author")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="Chapter One",
        content="Original chapter text.",
        expected_version=1,
    )
    init_service.start_initialization(work.id, created_by="user_action")
    return work_service, chapter_service, init_service, review_service, candidate_store, work, chapter


def _save_candidate(candidate_store: FileCandidateDraftStore, *, work_id: str, chapter_id: str, content: str = "Candidate continuation.") -> CandidateDraft:
    draft = CandidateDraft(
        candidate_draft_id="cd_s6_test",
        work_id=work_id,
        chapter_id=chapter_id,
        source_context_pack_id="cp_s6",
        source_job_id="job_s6",
        status=CandidateDraftStatus.PENDING_REVIEW,
        content=content,
        content_preview=content[:120],
        word_count=2,
        char_count=len(content),
        validation_status=CandidateDraftValidationStatus.PASSED,
        writer_model_role="writer",
        provider_name="fake",
        model_name="fake-writer",
        created_by="workflow",
        created_at="2026-05-11T00:00:00+00:00",
        updated_at="2026-05-11T00:00:00+00:00",
        metadata={"chapter_version": 2},
    )
    return candidate_store.save(draft)


def test_accept_candidate_requires_user_action_and_does_not_write_chapter(tmp_path: Path) -> None:
    _, chapter_service, _, review_service, candidate_store, work, chapter = _create_initialized_work(tmp_path)
    draft = _save_candidate(candidate_store, work_id=work.id, chapter_id=chapter.id.value)

    try:
        review_service.accept_candidate(draft.candidate_draft_id, user_id="u1", user_action=False)
    except ValueError as exc:
        assert str(exc) == "user_confirmation_required"
    else:
        raise AssertionError("accept without user_action should fail")

    accepted = review_service.accept_candidate(draft.candidate_draft_id, user_id="u1", user_action=True)
    chapter_after = chapter_service.list_chapters(work.id)[0]

    assert accepted.status == CandidateDraftStatus.ACCEPTED
    assert chapter_after.content == chapter.content


def test_reject_candidate_requires_user_action_and_cannot_apply(tmp_path: Path) -> None:
    _, chapter_service, _, review_service, candidate_store, work, chapter = _create_initialized_work(tmp_path)
    draft = _save_candidate(candidate_store, work_id=work.id, chapter_id=chapter.id.value)

    rejected = review_service.reject_candidate(draft.candidate_draft_id, user_id="u1", reason="not now", user_action=True)
    chapter_after = chapter_service.list_chapters(work.id)[0]

    assert rejected.status == CandidateDraftStatus.REJECTED
    assert chapter_after.content == chapter.content

    try:
        review_service.apply_candidate_to_draft(
            draft.candidate_draft_id,
            user_id="u1",
            expected_chapter_version=chapter.version,
            user_action=True,
            idempotency_key="apply-rejected-1",
        )
    except ValueError as exc:
        assert str(exc) == "candidate_already_rejected"
    else:
        raise AssertionError("rejected candidate should not apply")


def test_apply_candidate_updates_chapter_marks_applied_and_marks_stale(tmp_path: Path) -> None:
    _, chapter_service, init_service, review_service, candidate_store, work, chapter = _create_initialized_work(tmp_path)
    draft = _save_candidate(candidate_store, work_id=work.id, chapter_id=chapter.id.value, content="The new continuation arrives.")
    review_service.accept_candidate(draft.candidate_draft_id, user_id="u1", user_action=True)

    result = review_service.apply_candidate_to_draft(
        draft.candidate_draft_id,
        user_id="u1",
        expected_chapter_version=chapter.version,
        user_action=True,
        idempotency_key="apply-success-1",
    )
    applied = review_service.get_candidate_draft(draft.candidate_draft_id)
    chapter_after = chapter_service.list_chapters(work.id)[0]

    assert result["status"] == "applied"
    assert applied.status == CandidateDraftStatus.APPLIED
    assert "The new continuation arrives." in chapter_after.content
    assert chapter_after.version == chapter.version + 1
    assert init_service.is_stale(work.id) is True
    assert init_service.get_latest_story_memory(work.id).stale_status == "stale"
    assert init_service.get_latest_story_state(work.id).stale_status == "stale"


def test_apply_generated_candidate_is_allowed_as_user_action(tmp_path: Path) -> None:
    _, chapter_service, _, review_service, candidate_store, work, chapter = _create_initialized_work(tmp_path)
    draft = _save_candidate(candidate_store, work_id=work.id, chapter_id=chapter.id.value)

    result = review_service.apply_candidate_to_draft(
        draft.candidate_draft_id,
        user_id="u1",
        expected_chapter_version=chapter.version,
        user_action=True,
        idempotency_key="apply-generated-1",
    )

    assert result["status"] == "applied"
    assert chapter_service.list_chapters(work.id)[0].content.endswith("Candidate continuation.")


def test_apply_version_conflict_does_not_write_chapter_or_mark_applied(tmp_path: Path) -> None:
    _, chapter_service, init_service, review_service, candidate_store, work, chapter = _create_initialized_work(tmp_path)
    draft = _save_candidate(candidate_store, work_id=work.id, chapter_id=chapter.id.value)
    original_content = chapter.content

    try:
        review_service.apply_candidate_to_draft(
            draft.candidate_draft_id,
            user_id="u1",
            expected_chapter_version=chapter.version + 1,
            user_action=True,
            idempotency_key="apply-conflict-1",
        )
    except ValueError as exc:
        assert str(exc) == "chapter_version_conflict"
    else:
        raise AssertionError("version conflict should fail")

    assert chapter_service.list_chapters(work.id)[0].content == original_content
    assert review_service.get_candidate_draft(draft.candidate_draft_id).status == CandidateDraftStatus.PENDING_REVIEW
    assert init_service.is_stale(work.id) is False


def test_apply_rejects_repeated_apply_missing_user_action_and_missing_candidate(tmp_path: Path) -> None:
    _, _, _, review_service, candidate_store, work, chapter = _create_initialized_work(tmp_path)
    draft = _save_candidate(candidate_store, work_id=work.id, chapter_id=chapter.id.value)

    try:
        review_service.apply_candidate_to_draft(
            draft.candidate_draft_id,
            user_id="u1",
            expected_chapter_version=chapter.version,
            user_action=False,
            idempotency_key="apply-no-user-1",
        )
    except ValueError as exc:
        assert str(exc) == "user_confirmation_required"
    else:
        raise AssertionError("apply without user_action should fail")

    review_service.apply_candidate_to_draft(
        draft.candidate_draft_id,
        user_id="u1",
        expected_chapter_version=chapter.version,
        user_action=True,
        idempotency_key="apply-repeat-1",
    )
    try:
        review_service.apply_candidate_to_draft(
            draft.candidate_draft_id,
            user_id="u1",
            expected_chapter_version=chapter.version + 1,
            user_action=True,
            idempotency_key="apply-repeat-2",
        )
    except ValueError as exc:
        assert str(exc) == "candidate_already_applied"
    else:
        raise AssertionError("applied candidate should not apply again")

    try:
        review_service.get_candidate_draft("cd_missing")
    except ValueError as exc:
        assert str(exc) == "candidate_draft_not_found"
    else:
        raise AssertionError("missing candidate should fail")


def test_apply_modes_reject_whole_chapter_replace_and_validate_targets(tmp_path: Path) -> None:
    _, _, _, review_service, candidate_store, work, chapter = _create_initialized_work(tmp_path)
    draft = _save_candidate(candidate_store, work_id=work.id, chapter_id=chapter.id.value)

    for mode in ("replace_chapter_draft", "whole_chapter_replace"):
        try:
            review_service.apply_candidate_to_draft(
                draft.candidate_draft_id,
                user_id="u1",
                expected_chapter_version=chapter.version,
                user_action=True,
                apply_mode=mode,
                idempotency_key=f"apply-mode-{mode}",
            )
        except ValueError as exc:
            assert str(exc) == "apply_mode_not_supported"
        else:
            raise AssertionError(f"{mode} should not be supported")

    try:
        review_service.apply_candidate_to_draft(
            draft.candidate_draft_id,
            user_id="u1",
            expected_chapter_version=chapter.version,
            user_action=True,
            apply_mode="replace_selection",
            idempotency_key="apply-selection-missing",
        )
    except ValueError as exc:
        assert str(exc) == "apply_target_missing"
    else:
        raise AssertionError("replace_selection without selection_range should fail")


def _api_seed_candidate() -> tuple[str, int]:
    client = TestClient(app)
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("S6 API Work", "Author")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(chapter.id.value, title="Chapter", content="API original.", expected_version=1)
    from presentation.api import dependencies

    dependencies.get_initialization_service().start_initialization(work.id, created_by="user_action")
    response = client.post(
        "/api/v2/ai/continuations",
        json={"work_id": work.id, "chapter_id": chapter.id.value, "user_instruction": "continue"},
    )
    assert response.status_code == 200
    return response.json()["data"]["candidate_draft_id"], chapter.version


def test_candidate_review_apis_accept_reject_apply_and_require_version() -> None:
    client = TestClient(app)
    candidate_draft_id, chapter_version = _api_seed_candidate()

    accept_denied = client.post(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/accept", json={"user_action": False})
    assert accept_denied.status_code == 403
    assert accept_denied.json()["error"]["error_code"] == "user_confirmation_required"

    accept_response = client.post(f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/accept", json={"user_action": True, "user_id": "u1"})
    assert accept_response.status_code == 200
    assert accept_response.json()["data"]["status"] == "accepted"

    missing_version = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/apply",
        json={"user_action": True, "idempotency_key": "apply-missing-version"},
    )
    assert missing_version.status_code == 400
    assert missing_version.json()["error"]["error_code"] == "expected_chapter_version_required"

    conflict = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/apply",
        json={"user_action": True, "expected_chapter_version": chapter_version + 99, "idempotency_key": "apply-conflict-api"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["error_code"] == "chapter_version_conflict"

    apply_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/apply",
        json={"user_action": True, "user_id": "u1", "expected_chapter_version": chapter_version, "idempotency_key": "apply-api-success"},
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["data"]["status"] == "applied"


def test_apply_candidate_api_requires_idempotency_key() -> None:
    client = TestClient(app)
    candidate_draft_id, chapter_version = _api_seed_candidate()

    response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/apply",
        json={"user_action": True, "user_id": "u1", "expected_chapter_version": chapter_version, "idempotency_key": ""},
    )
    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "idempotency_key_missing"


def test_legacy_generated_candidate_status_is_normalized_to_pending_review() -> None:
    legacy = CandidateDraft.model_validate(
        {
            "candidate_draft_id": "cd_legacy",
            "work_id": "w1",
            "chapter_id": "c1",
            "source_context_pack_id": "cp1",
            "source_job_id": "job1",
            "status": "generated",
        }
    )

    assert legacy.status == CandidateDraftStatus.PENDING_REVIEW


def test_reject_api_does_not_write_and_no_ai_review_api_exists() -> None:
    client = TestClient(app)
    candidate_draft_id, _ = _api_seed_candidate()

    reject_response = client.post(
        f"/api/v2/ai/candidate-drafts/{candidate_draft_id}/reject",
        json={"user_action": True, "user_id": "u1", "reason": "reject"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["status"] == "rejected"

    routes = {route.path for route in app.routes}
    assert "/api/v2/ai/review" not in routes
    assert "/api/v2/ai/candidate-drafts/{candidate_draft_id}/whole_chapter_replace" not in routes
