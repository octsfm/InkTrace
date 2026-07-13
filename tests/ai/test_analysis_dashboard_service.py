from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from application.services.ai.analysis_dashboard_query_service import AnalysisDashboardQueryService


@dataclass
class _Chapter:
    id: str
    title: str
    content: str
    order_index: int
    created_at: datetime
    updated_at: datetime


@dataclass
class _Candidate:
    status: str
    applied_at: str = ""
    revision_count: int = 0
    content: str = "候选稿正文绝不能进入分析"


class _ChapterRepo:
    def __init__(self, chapters):
        self._chapters = chapters

    def list_by_work(self, _work_id):
        return list(self._chapters)


class _CandidateRepo:
    def __init__(self, candidates):
        self._candidates = candidates

    def list_by_work(self, _work_id, chapter_id=""):
        return list(self._candidates)


def test_analysis_uses_persisted_chapters_and_candidate_metadata_only() -> None:
    now = datetime.now(UTC)
    service = AnalysisDashboardQueryService(
        chapter_repository=_ChapterRepo([
            _Chapter("c1", "第一章", "她说：“我们走。”\n\n门外突然响起脚步声。", 1, now - timedelta(days=2), now),
            _Chapter("c2", "第二章", "他没有回答。\n\n难道秘密已经暴露？", 2, now - timedelta(days=1), now),
        ]),
        candidate_draft_repository=_CandidateRepo([
            _Candidate("applied", applied_at=now.isoformat(), revision_count=2),
            _Candidate("pending_review", revision_count=1),
        ]),
        style_profile_repository=None,
    )

    stats = asyncio.run(service.get_writing_stats("work-1"))
    usage = asyncio.run(service.get_ai_usage_analysis("work-1"))
    rhythm = asyncio.run(service.get_rhythm_analysis("work-1"))

    assert stats["total_chapters"] == 2
    assert stats["total_word_count"] > 0
    assert stats["ai_adoption_rate"] == 0.5
    assert usage["total_candidates"] == 2
    assert usage["total_adopted"] == 1
    assert usage["avg_revision_rounds"] == 1.5
    assert "候选稿正文" not in str(asyncio.run(service.get_word_frequency("work-1")))
    assert rhythm["cliffhanger_stats"]["per_chapter"][1]["question_count"] == 1


def test_analysis_returns_plain_safe_empty_results() -> None:
    service = AnalysisDashboardQueryService(
        chapter_repository=_ChapterRepo([]),
        candidate_draft_repository=_CandidateRepo([]),
        style_profile_repository=None,
    )

    assert asyncio.run(service.get_writing_stats("work-empty"))["total_word_count"] == 0
    style = asyncio.run(service.get_style_consistency("work-empty"))
    assert style["warning"] == "no_confirmed_chapters"
