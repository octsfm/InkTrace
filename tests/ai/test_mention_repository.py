from domain.entities.ai.models import (
    ChapterMention,
    MentionEntityType,
    MentionSource,
    MentionStatus,
)
from infrastructure.persistence.sqlite_chapter_mention_repo import SQLiteChapterMentionRepository


def test_chapter_mention_model_and_repository_replace_preserve_and_break_omitted(tmp_path) -> None:
    repo = SQLiteChapterMentionRepository(tmp_path / "mentions.db")
    first = ChapterMention(
        mention_id="m_001",
        chapter_id="chapter_001",
        work_id="work_001",
        entity_type=MentionEntityType.CHARACTER,
        entity_id="char_001",
        entity_name_snapshot="张三",
        start_pos=0,
        end_pos=3,
        source=MentionSource.USER_INPUT,
        ai_suggestion_id="",
        status=MentionStatus.ACTIVE,
        is_active=True,
        validation_detail="",
        created_at="2026-07-03T10:00:00Z",
        updated_at="2026-07-03T10:00:00Z",
    )
    second = first.model_copy(
        update={
            "mention_id": "m_002",
            "entity_id": "event_001",
            "entity_type": MentionEntityType.EVENT,
            "entity_name_snapshot": "雨夜决战",
            "start_pos": 8,
            "end_pos": 12,
            "created_at": "2026-07-03T10:05:00Z",
            "updated_at": "2026-07-03T10:05:00Z",
        }
    )

    saved = repo.replace_by_chapter("chapter_001", [first, second])
    assert [item.mention_id for item in saved] == ["m_001", "m_002"]

    updated_first = first.model_copy(
        update={
            "start_pos": 2,
            "end_pos": 5,
            "updated_at": "2026-07-03T10:10:00Z",
        }
    )
    replaced = repo.replace_by_chapter("chapter_001", [updated_first])

    assert [item.mention_id for item in replaced] == ["m_001", "m_002"]
    assert replaced[0].start_pos == 2
    assert replaced[0].status == MentionStatus.ACTIVE
    assert replaced[1].status == MentionStatus.BROKEN
    assert replaced[1].is_active is False

    by_chapter = repo.get_by_chapter("chapter_001")
    assert [item.mention_id for item in by_chapter] == ["m_001", "m_002"]

    by_entity = repo.get_by_entity(MentionEntityType.CHARACTER, "char_001")
    assert [item.mention_id for item in by_entity] == ["m_001"]

    repo.mark_entity_deleted(MentionEntityType.CHARACTER, "char_001")
    deleted_items = repo.get_by_entity(MentionEntityType.CHARACTER, "char_001")
    assert deleted_items[0].status == MentionStatus.INACTIVE_ENTITY
    assert deleted_items[0].is_active is False
