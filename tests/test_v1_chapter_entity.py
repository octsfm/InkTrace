from datetime import datetime, timedelta

from domain.entities.chapter import Chapter
from domain.types import ChapterId, ChapterStatus, NovelId


def test_chapter_entity_tracks_version_and_order_index():
    created_at = datetime(2026, 4, 28, 10, 0, 0)
    updated_at = created_at + timedelta(minutes=2)
    chapter = Chapter(
        id=ChapterId("chapter-1"),
        novel_id=NovelId("work-1"),
        number=1,
        title="第一章",
        content="原始内容",
        status=ChapterStatus.DRAFT,
        created_at=created_at,
        updated_at=created_at,
    )

    chapter.update_content("新的正文", updated_at)
    chapter.update_title("第一章 重写", updated_at)
    chapter.move_to(3, updated_at)

    assert chapter.version == 3
    assert chapter.order_index == 3
    assert chapter.title == "第一章 重写"
    assert chapter.content == "新的正文"
