from __future__ import annotations

import hashlib
from pathlib import Path

from application.services.ai.citation_link_service import CitationLinkService
from application.services.v1.chapter_service import ChapterService
from application.services.v1.work_service import WorkService
from application.services.v1.writing_asset_service import WritingAssetService
from domain.entities.ai.models import (
    CandidateDraft,
    CandidateDraftStatus,
    CandidateDraftValidationStatus,
    CandidateDraftVersion,
    CandidateDraftVersionStatus,
    CitationVerificationStatus,
    StoryStateSnapshot,
)
from infrastructure.database.repositories import (
    ChapterOutlineRepo,
    ChapterRepo,
    CharacterRepo,
    ForeshadowRepo,
    TimelineEventRepo,
    WorkOutlineRepo,
    WorkRepo,
)
from infrastructure.database.repositories.ai.file_candidate_draft_store import FileCandidateDraftStore
from infrastructure.database.repositories.ai.file_story_state_store import FileStoryStateStore
from infrastructure.persistence.sqlite_citation_link_repo import SQLiteCitationLinkRepository


def _build_candidate_context(tmp_path: Path):
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    writing_asset_service = WritingAssetService(
        work_repo=work_repo,
        chapter_repo=chapter_repo,
        work_outline_repo=WorkOutlineRepo(),
        chapter_outline_repo=ChapterOutlineRepo(),
        timeline_event_repo=TimelineEventRepo(),
        foreshadow_repo=ForeshadowRepo(),
        character_repo=CharacterRepo(),
    )
    work_service = WorkService(work_repo=work_repo, chapter_repo=chapter_repo)
    chapter_service = ChapterService(chapter_repo=chapter_repo, work_repo=work_repo)
    work = work_service.create_work("Citation Link 作品", "作者")
    chapter = chapter_service.list_chapters(work.id)[0]
    chapter = chapter_service.update_chapter(
        chapter.id.value,
        title="第一章",
        content="顾迟在海边灯塔醒来，发现父亲留下的海图坐标藏在夹层里。",
        expected_version=1,
    )
    candidate_store = FileCandidateDraftStore(tmp_path / "candidate_drafts.json")
    story_state_store = FileStoryStateStore(tmp_path / "story_state_snapshots.json")
    draft = candidate_store.save(
        CandidateDraft(
            candidate_draft_id="cd_citation_1",
            work_id=work.id,
            chapter_id=chapter.id.value,
            source_context_pack_id="cp_1",
            source_job_id="job_1",
            status=CandidateDraftStatus.PENDING_REVIEW,
            selected_version_id="ver_citation_1",
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
            candidate_version_id="ver_citation_1",
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
    story_state_store.save_analysis_baseline(
        StoryStateSnapshot(
            story_state_id="state_citation_1",
            work_id=work.id,
            source_initialization_id="init_1",
            source_job_id="job_1",
            latest_chapter_id=chapter.id.value,
            latest_chapter_version=chapter.version,
            current_position_summary="顾迟仍在灯塔附近追查海图。",
            active_characters=["顾迟"],
            active_locations=["灯塔", "旧码头"],
            unresolved_threads=["海图坐标指向何处"],
            continuity_notes=["潮汐祭坛只能在月蚀夜开启。", "海图缺失北侧航线。"],
            source_snapshot_id="memory_citation_1",
            created_at="2026-06-09T00:00:00+00:00",
        )
    )
    service = CitationLinkService(
        citation_repository=SQLiteCitationLinkRepository(tmp_path / "runtime.db"),
        candidate_draft_repository=candidate_store,
        work_service=work_service,
        chapter_service=chapter_service,
        writing_asset_service=writing_asset_service,
        story_state_repository=story_state_store,
    )
    return service, writing_asset_service, candidate_store, work.id, chapter.id.value, version.candidate_version_id, draft.candidate_draft_id


class _SpyVectorRecallService:
    def __init__(self, results: list[dict[str, object]]) -> None:
        self.results = results
        self.calls = 0

    def recall(self, query):  # noqa: ANN001
        self.calls += 1
        return list(self.results)


def test_citation_link_service_processes_candidate_citations_and_groups_by_version(tmp_path: Path) -> None:
    service, _, _, _, chapter_id, candidate_version_id, candidate_draft_id = _build_candidate_context(tmp_path)

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "chapter",
                "source_name": "第一章",
                "source_id_hint": chapter_id,
                "context_in_draft": "父亲留下的海图",
                "confidence": 0.91,
            },
            {
                "source_type": "chapter",
                "source_name": "不存在的章节",
                "source_id_hint": "chapter_missing",
                "context_in_draft": "未知线索",
                "confidence": 0.4,
            },
        ],
    )

    assert batch.candidate_version_id == candidate_version_id
    assert batch.candidate_draft_id == candidate_draft_id
    assert batch.total_count == 2
    assert batch.unknown_count == 1
    assert batch.citations[0].source_id == chapter_id
    assert batch.citations[0].verification_status == CitationVerificationStatus.LOW_CONFIDENCE
    assert "vector_unavailable" in batch.citations[0].verification_detail
    assert batch.citations[1].verification_status == CitationVerificationStatus.UNKNOWN_SOURCE

    stored = service.get_by_candidate_version(candidate_version_id)
    assert stored.total_count == 2
    assert stored.citations[0].candidate_draft_id == candidate_draft_id


def test_citation_link_service_supports_query_by_source_and_source_detail(tmp_path: Path) -> None:
    service, _, _, work_id, chapter_id, candidate_version_id, _ = _build_candidate_context(tmp_path)
    service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "chapter",
                "source_name": "第一章",
                "source_id_hint": chapter_id,
                "context_in_draft": "灯塔夹层",
                "confidence": 0.88,
            }
        ],
    )

    citations = service.get_by_source("chapter", chapter_id)
    source_detail = service.get_source_detail("chapter", chapter_id)

    assert len(citations) == 1
    assert citations[0].work_id == work_id
    assert source_detail["source_id"] == chapter_id
    assert source_detail["is_active"] is True
    assert source_detail["source_full_summary"]


def test_citation_link_service_marks_chapter_citation_verified_when_vector_recall_matches(tmp_path: Path) -> None:
    service, _, _, _, chapter_id, candidate_version_id, _ = _build_candidate_context(tmp_path)
    service._vector_recall_service = _SpyVectorRecallService(  # type: ignore[attr-defined]
        [
            {
                "source_id": chapter_id,
                "content_text": "顾迟发现父亲留下的海图坐标。",
                "score": 0.92,
            }
        ]
    )

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "chapter",
                "source_name": "第一章",
                "source_id_hint": chapter_id,
                "context_in_draft": "父亲留下的海图",
                "confidence": 0.91,
            }
        ],
    )

    assert batch.citations[0].verification_status == CitationVerificationStatus.VERIFIED
    assert "vector_matched" in batch.citations[0].verification_detail
    assert batch.citations[0].source_excerpt == "顾迟发现父亲留下的海图坐标。"


def test_citation_link_service_marks_chapter_citation_low_confidence_when_vector_score_is_low(tmp_path: Path) -> None:
    service, _, _, _, chapter_id, candidate_version_id, _ = _build_candidate_context(tmp_path)
    service._vector_recall_service = _SpyVectorRecallService(  # type: ignore[attr-defined]
        [
            {
                "source_id": chapter_id,
                "content_text": "顾迟发现父亲留下的海图坐标。",
                "score": 0.42,
            }
        ]
    )

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "chapter",
                "source_name": "第一章",
                "source_id_hint": chapter_id,
                "context_in_draft": "父亲留下的海图",
                "confidence": 0.91,
            }
        ],
    )

    assert batch.citations[0].verification_status == CitationVerificationStatus.LOW_CONFIDENCE
    assert "vector_score_low" in batch.citations[0].verification_detail


def test_citation_link_service_marks_event_citation_verified_when_vector_recall_matches(tmp_path: Path) -> None:
    service, writing_asset_service, _, work_id, _, candidate_version_id, _ = _build_candidate_context(tmp_path)
    event = writing_asset_service.create_timeline_event(
        work_id,
        {
            "title": "灯塔发现海图",
            "description": "顾迟在灯塔夹层发现父亲留下的海图坐标。",
        },
    )
    service._vector_recall_service = _SpyVectorRecallService(  # type: ignore[attr-defined]
        [
            {
                "source_id": event.id,
                "content_text": "顾迟在灯塔夹层发现父亲留下的海图坐标。",
                "score": 0.94,
            }
        ]
    )

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "event",
                "source_name": event.title,
                "source_id_hint": event.id,
                "context_in_draft": "灯塔夹层里的海图坐标",
                "confidence": 0.9,
            }
        ],
    )

    assert batch.citations[0].verification_status == CitationVerificationStatus.VERIFIED
    assert "vector_matched" in batch.citations[0].verification_detail


def test_citation_link_service_marks_character_citation_existence_only_when_vector_unavailable(tmp_path: Path) -> None:
    service, writing_asset_service, _, work_id, _, candidate_version_id, _ = _build_candidate_context(tmp_path)
    character = writing_asset_service.create_character(
        work_id,
        {
            "name": "顾迟",
            "description": "年轻船匠，执着追查父亲留下的海图。",
        },
    )

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "character",
                "source_name": character.name,
                "source_id_hint": character.id,
                "context_in_draft": "顾迟想起父亲留下的嘱托",
                "confidence": 0.86,
            }
        ],
    )

    assert batch.citations[0].verification_status == CitationVerificationStatus.LOW_CONFIDENCE
    assert batch.citations[0].verification_detail == "existence_only"
    assert batch.citations[0].source_excerpt == "年轻船匠，执着追查父亲留下的海图。"


def test_citation_link_service_marks_foreshadow_citation_existence_only_when_vector_unavailable(tmp_path: Path) -> None:
    service, writing_asset_service, _, work_id, chapter_id, candidate_version_id, _ = _build_candidate_context(tmp_path)
    foreshadow = writing_asset_service.create_foreshadow(
        work_id,
        {
            "title": "灯塔海图",
            "description": "海图坐标将指向更大的家族秘密。",
            "introduced_chapter_id": chapter_id,
        },
    )

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "foreshadow",
                "source_name": foreshadow.title,
                "source_id_hint": foreshadow.id,
                "context_in_draft": "海图坐标隐藏着后续秘密",
                "confidence": 0.83,
            }
        ],
    )

    assert batch.citations[0].verification_status == CitationVerificationStatus.LOW_CONFIDENCE
    assert batch.citations[0].verification_detail == "existence_only"
    assert batch.citations[0].source_excerpt == "海图坐标将指向更大的家族秘密。"


def test_citation_link_service_marks_location_citation_existence_only_from_story_state(tmp_path: Path) -> None:
    service, _, _, _, _, candidate_version_id, _ = _build_candidate_context(tmp_path)

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "location",
                "source_name": "灯塔",
                "context_in_draft": "顾迟再次回到灯塔寻找夹层",
                "confidence": 0.72,
            }
        ],
    )

    assert batch.citations[0].verification_status == CitationVerificationStatus.LOW_CONFIDENCE
    assert batch.citations[0].verification_detail == "existence_only"
    assert batch.citations[0].source_name_snapshot == "灯塔"
    assert batch.citations[0].source_excerpt == "灯塔"


def test_citation_link_service_marks_setting_citation_existence_only_from_story_state(tmp_path: Path) -> None:
    service, _, _, _, _, candidate_version_id, _ = _build_candidate_context(tmp_path)

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "setting",
                "source_name": "潮汐祭坛只能在月蚀夜开启。",
                "context_in_draft": "月蚀夜才能打开潮汐祭坛",
                "confidence": 0.68,
            }
        ],
    )

    assert batch.citations[0].verification_status == CitationVerificationStatus.LOW_CONFIDENCE
    assert batch.citations[0].verification_detail == "existence_only"
    assert batch.citations[0].source_name_snapshot == "潮汐祭坛只能在月蚀夜开启。"
    assert batch.citations[0].source_excerpt == "潮汐祭坛只能在月蚀夜开启。"


def test_citation_link_service_marks_setting_citation_unknown_when_story_state_has_no_match(tmp_path: Path) -> None:
    service, _, _, _, _, candidate_version_id, _ = _build_candidate_context(tmp_path)

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "setting",
                "source_name": "并不存在的远古契约",
                "context_in_draft": "远古契约被再次提起",
                "confidence": 0.4,
            }
        ],
    )

    assert batch.citations[0].verification_status == CitationVerificationStatus.UNKNOWN_SOURCE
    assert batch.citations[0].verification_detail == "source_not_found"


def test_citation_link_service_rejects_citation_when_source_hash_mismatches(tmp_path: Path) -> None:
    service, _, _, _, chapter_id, candidate_version_id, _ = _build_candidate_context(tmp_path)

    try:
        service.process_candidate_citations(
            candidate_version_id=candidate_version_id,
            raw_citations=[
                {
                    "source_type": "chapter",
                    "source_name": "第一章",
                    "source_id_hint": chapter_id,
                    "source_hash": "sha256:not-the-real-hash",
                    "context_in_draft": "父亲留下的海图",
                    "confidence": 0.91,
                }
            ],
        )
    except ValueError as exc:
        assert str(exc) == "P2_CITATION_SOURCE_HASH_MISMATCH"
    else:
        raise AssertionError("expected source hash mismatch to raise ValueError")


def test_citation_link_service_accepts_matching_source_hash(tmp_path: Path) -> None:
    service, _, _, _, chapter_id, candidate_version_id, _ = _build_candidate_context(tmp_path)
    expected_hash = f"sha256:{hashlib.sha256('顾迟在海边灯塔醒来，发现父亲留下的海图坐标藏在夹层里。'.encode('utf-8')).hexdigest()}"

    batch = service.process_candidate_citations(
        candidate_version_id=candidate_version_id,
        raw_citations=[
            {
                "source_type": "chapter",
                "source_name": "第一章",
                "source_id_hint": chapter_id,
                "source_hash": expected_hash,
                "context_in_draft": "父亲留下的海图",
                "confidence": 0.91,
            }
        ],
    )

    assert batch.total_count == 1
    assert batch.citations[0].source_id == chapter_id
