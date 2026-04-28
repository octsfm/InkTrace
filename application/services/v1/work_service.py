from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from domain.entities.chapter import Chapter
from domain.entities.work import Work
from domain.types import ChapterId, ChapterStatus, NovelId
from infrastructure.database.repositories import ChapterRepo, WorkRepo


class WorkService:
    def __init__(self, work_repo: Optional[WorkRepo] = None, chapter_repo: Optional[ChapterRepo] = None):
        self.work_repo = work_repo or WorkRepo()
        self.chapter_repo = chapter_repo or ChapterRepo()

    def list_works(self) -> List[Work]:
        return self.work_repo.list_all()

    def create_work(self, title: str, author: str = "") -> Work:
        now = datetime.now(timezone.utc)
        work = Work(
            id=str(uuid.uuid4()),
            title=str(title or "").strip(),
            author=str(author or "").strip(),
            current_word_count=0,
            created_at=now,
            updated_at=now,
        )
        self.work_repo.save(work)
        self.chapter_repo.save(self._build_first_chapter(work.id, now))
        return work

    def delete_work(self, work_id: str) -> None:
        self.work_repo.delete(work_id)

    @staticmethod
    def _build_first_chapter(work_id: str, created_at: datetime) -> Chapter:
        return Chapter(
            id=ChapterId(str(uuid.uuid4())),
            novel_id=NovelId(str(work_id)),
            number=1,
            title="第1章",
            content="",
            status=ChapterStatus.DRAFT,
            created_at=created_at,
            updated_at=created_at,
            order_index=1,
            version=1,
        )
