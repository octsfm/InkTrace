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

        session = self.session_repo.find_by_work_id(work_id)
        if session:
            return session

        first_chapter = next(iter(self.chapter_repo.list_by_work(work_id)), None)
        return EditSession(
            work_id=work_id,
            last_open_chapter_id=first_chapter.id.value if first_chapter else "",
            cursor_position=0,
            scroll_top=0,
            updated_at=datetime.now(timezone.utc),
        )

    def save_session(
        self,
        work_id: str,
        *,
        chapter_id: str = "",
        cursor_position: int = 0,
        scroll_top: int = 0,
    ) -> EditSession:
        session = self.get_session(work_id)
        now = datetime.now(timezone.utc)
        if chapter_id:
            session.open_chapter(chapter_id, now)
        session.update_viewport(cursor_position, scroll_top, now)
        self.session_repo.save(session)
        return self.session_repo.find_by_work_id(work_id)
