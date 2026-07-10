from __future__ import annotations

from pathlib import Path

import pytest

from application.services.ai.opening_agent_service import OpeningAgentService
from infrastructure.persistence.sqlite_opening_repo import SQLiteOpeningRepository
from infrastructure.security.temporary_sensitive_text_store import EncryptedTemporarySensitiveTextStore


class FakeDirectionGenerator:
    def generate(self, *, brief, reference_summaries):
        return [
            {
                "name": name,
                "summary": f"{name}的开篇说明",
                "chapter_goals": ["主角出现", "冲突升级", "留下期待"],
                "advantages": ["容易理解"],
                "risks": [],
            }
            for name in ("先给危机", "先立人物", "先抛谜团")
        ]


class FakeDraftGenerator:
    def __init__(self, fail_on: int | None = None) -> None:
        self.fail_on = fail_on

    def generate(self, *, brief, direction, chapter_no, previous_drafts):
        if chapter_no == self.fail_on:
            raise RuntimeError("writer_failed")
        return f"第{chapter_no}章候选稿：{direction.name}"


class HighStrategyRiskChecker:
    def check_strategy(self, **kwargs):
        return {"risk_level": "high", "evidence_summary": "关键场景顺序过于接近", "revision_suggestions": ["更换开场地点"]}

    def check_draft(self, **kwargs):
        return {"risk_level": "low", "evidence_summary": "", "revision_suggestions": []}


@pytest.fixture()
def opening_service(tmp_path: Path):
    repository = SQLiteOpeningRepository(tmp_path / "opening.db")
    secret_store = EncryptedTemporarySensitiveTextStore(
        tmp_path / "opening-secrets",
        secret="test-opening-secret",
        ttl_seconds=1800,
    )
    return OpeningAgentService(
        repository=repository,
        temporary_text_store=secret_store,
        direction_generator=FakeDirectionGenerator(),
        draft_generator=FakeDraftGenerator(),
    ), repository, secret_store


def test_no_reference_path_creates_three_directions_and_keeps_history(opening_service):
    service, repository, _ = opening_service
    brief = service.prepare_brief(
        work_id="work-1",
        story_premise="一个普通人发现自己能看见谎言",
        protagonist_desire="保护家人",
        third_chapter_expectation="想知道能力的来源",
        idempotency_key="brief-1",
    )

    first = service.generate_directions(brief_id=brief.brief_id, idempotency_key="directions-1")
    second = service.generate_directions(brief_id=brief.brief_id, idempotency_key="directions-2")

    assert len(first.directions) == 3
    assert len(second.directions) == 3
    assert first.batch_id != second.batch_id
    assert repository.get_direction_batch(first.batch_id) is not None
    assert repository.get_direction_batch(second.batch_id) is not None


def test_direction_confirmation_requires_real_user_action(opening_service):
    service, _, _ = opening_service
    brief = service.prepare_brief(
        work_id="work-1",
        story_premise="悬疑故事",
        protagonist_desire="找出真相",
        third_chapter_expectation="想知道凶手是谁",
        idempotency_key="brief-2",
    )
    batch = service.generate_directions(brief_id=brief.brief_id, idempotency_key="directions-3")

    with pytest.raises(ValueError, match="P2_CALLER_FORBIDDEN"):
        service.confirm_direction(
            direction_id=batch.directions[0].direction_id,
            caller_type="agent",
            user_action=False,
            user_id="agent",
            idempotency_key="confirm-bad",
        )

    confirmed = service.confirm_direction(
        direction_id=batch.directions[0].direction_id,
        caller_type="user_action",
        user_action=True,
        user_id="author-1",
        idempotency_key="confirm-ok",
    )
    assert confirmed.status == "confirmed"


def test_revise_direction_creates_a_new_unconfirmed_version_without_overwriting(opening_service):
    service, repository, _ = opening_service
    brief = service.prepare_brief(
        work_id="work-1", story_premise="悬疑故事", protagonist_desire="找到真相",
        third_chapter_expectation="发现第一个关键线索", idempotency_key="brief-revise",
    )
    batch = service.generate_directions(brief_id=brief.brief_id, idempotency_key="directions-revise")
    original = batch.directions[0]

    revised = service.revise_direction(
        direction_id=original.direction_id,
        name="我自己的开场",
        summary="主角先在日常生活里发现一处说不通的细节。",
        chapter_goals=["发现异常", "主动调查", "线索指向熟人"],
        advantages=["人物更自然"], risks=["开场节奏需要控制"],
        idempotency_key="revise-1",
    )

    assert revised.direction_id != original.direction_id
    assert revised.parent_direction_id == original.direction_id
    assert revised.revision_no == 2
    assert revised.status == "proposed"
    stored = repository.get_direction_batch(batch.batch_id)
    assert stored is not None
    assert len(stored.directions) == 4
    assert repository.get_direction(original.direction_id).summary == original.summary

    with pytest.raises(ValueError, match="P2_OPENING_DIRECTION_NOT_CONFIRMED"):
        service.generate_drafts(direction_id=revised.direction_id, idempotency_key="draft-before-confirm")


def test_reference_text_is_encrypted_limited_and_deleted_after_analysis(opening_service):
    service, repository, secret_store = opening_service
    brief = service.prepare_brief(
        work_id="work-1",
        story_premise="成长故事",
        protagonist_desire="离开故乡",
        third_chapter_expectation="想知道远方有什么",
        idempotency_key="brief-3",
    )
    raw_text = "这是一段只用于测试的参考原文"

    session = service.import_references(
        brief_id=brief.brief_id,
        references=[{"title": "参考一", "chapters_text": [raw_text]}],
        rights_confirmed=True,
        rights_text_version="v1",
        idempotency_key="reference-1",
    )

    stored = repository.get_reference_session(session.reference_session_id)
    assert stored is not None
    assert raw_text not in str(stored.model_dump())
    assert not secret_store.exists(session.reference_session_id)

    with pytest.raises(ValueError, match="P2_OPENING_REFERENCE_LIMIT_EXCEEDED"):
        service.import_references(
            brief_id=brief.brief_id,
            references=[{"title": "过长", "chapters_text": ["字" * 30001]}],
            rights_confirmed=True,
            rights_text_version="v1",
            idempotency_key="reference-too-long",
        )


def test_partial_draft_generation_keeps_completed_candidate_result(tmp_path: Path):
    repository = SQLiteOpeningRepository(tmp_path / "opening.db")
    service = OpeningAgentService(
        repository=repository,
        temporary_text_store=EncryptedTemporarySensitiveTextStore(
            tmp_path / "secrets", secret="test", ttl_seconds=1800
        ),
        direction_generator=FakeDirectionGenerator(),
        draft_generator=FakeDraftGenerator(fail_on=2),
    )
    brief = service.prepare_brief(
        work_id="work-1",
        story_premise="冒险故事",
        protagonist_desire="寻找失踪的父亲",
        third_chapter_expectation="想知道地图的秘密",
        idempotency_key="brief-4",
    )
    directions = service.generate_directions(brief_id=brief.brief_id, idempotency_key="directions-4")
    direction = service.confirm_direction(
        direction_id=directions.directions[0].direction_id,
        caller_type="user_action",
        user_action=True,
        user_id="author-1",
        idempotency_key="confirm-4",
    )

    batch = service.generate_drafts(direction_id=direction.direction_id, idempotency_key="drafts-1")

    assert batch.status == "partial_success"
    assert batch.result_refs
    assert batch.chapter_results[0].candidate_draft_id
    assert batch.chapter_results[1].status == "failed"


def test_high_strategy_similarity_is_blocked_before_draft_generation(tmp_path: Path):
    repository = SQLiteOpeningRepository(tmp_path / "opening.db")
    service = OpeningAgentService(
        repository=repository,
        temporary_text_store=EncryptedTemporarySensitiveTextStore(tmp_path / "secrets", secret="test", ttl_seconds=1800),
        direction_generator=FakeDirectionGenerator(),
        draft_generator=FakeDraftGenerator(),
        originality_checker=HighStrategyRiskChecker(),
    )
    brief = service.prepare_brief(work_id="work-1", story_premise="故事", protagonist_desire="目标", third_chapter_expectation="期待", idempotency_key="b-high")
    service.import_references(
        brief_id=brief.brief_id,
        references=[{"title": "参考", "chapters_text": ["参考文本"]}],
        rights_confirmed=True,
        rights_text_version="v1",
        idempotency_key="r-high",
    )
    batch = service.generate_directions(brief_id=brief.brief_id, idempotency_key="d-high")
    direction = service.confirm_direction(direction_id=batch.directions[0].direction_id, caller_type="user_action", user_action=True, user_id="author", idempotency_key="c-high")

    with pytest.raises(ValueError, match="P2_OPENING_STRATEGY_SIMILARITY_BLOCKED"):
        service.generate_drafts(direction_id=direction.direction_id, idempotency_key="draft-high")
