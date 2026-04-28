from datetime import datetime, timedelta

from domain.entities.edit_session import EditSession


def test_edit_session_tracks_chapter_and_viewport():
    created_at = datetime(2026, 4, 28, 11, 0, 0)
    updated_at = created_at + timedelta(minutes=3)
    session = EditSession(
        work_id="work-1",
        last_open_chapter_id="chapter-1",
        cursor_position=10,
        scroll_top=20,
        updated_at=created_at,
    )

    session.open_chapter("chapter-2", updated_at)
    session.update_viewport(88, 144, updated_at)

    assert session.last_open_chapter_id == "chapter-2"
    assert session.cursor_position == 88
    assert session.scroll_top == 144
    assert session.updated_at == updated_at
