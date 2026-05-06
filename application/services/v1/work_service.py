from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from domain.entities.chapter import Chapter
from domain.repositories.workbench import ChapterRepository, WorkRepository
from domain.entities.work import Work
from domain.types import ChapterId, ChapterStatus, NovelId
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_connection


class WorkService:
    def __init__(
        self,
        work_repo: Optional[WorkRepository] = None,
        chapter_repo: Optional[ChapterRepository] = None,
    ):
        self.work_repo = work_repo or WorkRepo()
        self.chapter_repo = chapter_repo or ChapterRepo()

    def list_works(self) -> List[Work]:
        return self.work_repo.list_all()

    def get_work(self, work_id: str) -> Work:
        work = self.work_repo.find_by_id(work_id)
        if not work:
            raise ValueError("work_not_found")
        return work

    def create_work(self, title: str, author: str = "") -> Work:
        now = datetime.now(timezone.utc)
        work = Work(
            id=str(uuid.uuid4()),
            title=str(title or "").strip(),
            author=str(author or "").strip(),
            word_count=0,
            created_at=now,
            updated_at=now,
        )
        first_chapter = self._build_first_chapter(work.id, now)
        with get_connection() as conn:
            self.work_repo._save_with_connection(conn, work)
            self.chapter_repo._save_with_connection(conn, first_chapter)
        return work

    def update_work(self, work_id: str, title: str | None = None, author: str | None = None) -> Work:
        work = self.get_work(work_id)
        if title is not None:
            work.title = str(title or "").strip()
        if author is not None:
            work.author = str(author or "").strip()
        work.updated_at = datetime.now(timezone.utc)
        self.work_repo.save(work)
        return self.get_work(work_id)

    def delete_work(self, work_id: str) -> None:
        if not self.work_repo.find_by_id(work_id):
            raise ValueError("work_not_found")
        self.work_repo.delete(work_id)

    @staticmethod
    def _build_first_chapter(work_id: str, created_at: datetime) -> Chapter:
        return Chapter(
            id=ChapterId(str(uuid.uuid4())),
            work_id=NovelId(str(work_id)),
            title="",
            content="",
            status=ChapterStatus.DRAFT,
            created_at=created_at,
            updated_at=created_at,
            order_index=1,
            version=1,
        )
