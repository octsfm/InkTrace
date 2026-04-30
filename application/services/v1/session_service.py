from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from domain.entities.edit_session import EditSession
from infrastructure.database.repositories import ChapterRepo, EditSessionRepo, WorkRepo


class SessionService:
    def __init__(
        self,
        session_repo: Optional[EditSessionRepo] = None,
        chapter_repo: Optional[ChapterRepo] = None,
        work_repo: Optional[WorkRepo] = None,
    ):
        self.session_repo = session_repo or EditSessionRepo()
        self.chapter_repo = chapter_repo or ChapterRepo()
        self.work_repo = work_repo or WorkRepo()

    def get_session(self, work_id: str) -> EditSession:
        work = self.work_repo.find_by_id(work_id)
        if not work:
            raise ValueError("work_not_found")

        chapters = self.chapter_repo.list_by_work(work_id)
        first_chapter_id = chapters[0].id.value if chapters else ""
        chapter_ids = {chapter.id.value for chapter in chapters}
        session = self.session_repo.find_by_work_id(work_id)
        if session:
            if session.last_open_chapter_id and session.last_open_chapter_id not in chapter_ids:
                session.last_open_chapter_id = first_chapter_id
                session.cursor_position = 0
                session.scroll_top = 0
            return session

        return EditSession(
            work_id=work_id,
            last_open_chapter_id=first_chapter_id,
            cursor_position=0,
            scroll_top=0,
            updated_at=datetime.now(timezone.utc),
        )

    def save_session(
        self,
        work_id: str,
        *,
        chapter_id: str = "",
        active_chapter_id: str = "",
        cursor_position: int = 0,
        scroll_top: int = 0,
    ) -> EditSession:
        session = self.get_session(work_id)
        now = datetime.now(timezone.utc)
        next_chapter_id = str(active_chapter_id or chapter_id or session.last_open_chapter_id or "")
        if next_chapter_id:
            chapter_ids = {chapter.id.value for chapter in self.chapter_repo.list_by_work(work_id)}
            if next_chapter_id not in chapter_ids:
                raise ValueError("chapter_not_found")
            session.open_chapter(next_chapter_id, now)
        session.update_viewport(cursor_position, scroll_top, now)
        self.session_repo.save(session)
        return self.session_repo.find_by_work_id(work_id)
