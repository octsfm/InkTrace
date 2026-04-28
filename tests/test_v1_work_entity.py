from datetime import datetime, timedelta

from domain.entities.work import Work


def test_work_entity_updates_title_and_word_count():
    created_at = datetime(2026, 4, 28, 10, 0, 0)
    updated_at = created_at + timedelta(minutes=5)
    work = Work(
        id="work-1",
        title="旧标题",
        author="作者A",
        created_at=created_at,
        updated_at=created_at,
    )

    work.rename("新标题", updated_at)
    work.update_word_count(1234, updated_at)

    assert work.title == "新标题"
    assert work.current_word_count == 1234
    assert work.updated_at == updated_at
