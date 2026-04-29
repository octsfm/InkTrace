from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from domain.entities.chapter import Chapter
from domain.types import ChapterId, ChapterStatus, NovelId
from infrastructure.database.repositories import ChapterRepo, WorkRepo


class ChapterService:
    def __init__(self, chapter_repo: Optional[ChapterRepo] = None, work_repo: Optional[WorkRepo] = None):
        self.chapter_repo = chapter_repo or ChapterRepo()
        self.work_repo = work_repo or WorkRepo()

    def list_chapters(self, work_id: str) -> List[Chapter]:
        return self.chapter_repo.list_by_work(work_id)

    def create_chapter(self, work_id: str, title: str = "", after_chapter_id: str = "") -> Chapter:
        work = self.work_repo.find_by_id(work_id)
        if not work:
            raise ValueError("work_not_found")

        now = datetime.now(timezone.utc)
        chapters = self.chapter_repo.list_by_work(work_id)
        insert_after = next((item for item in chapters if item.id.value == str(after_chapter_id)), None)
        insert_index = insert_after.order_index if insert_after else len(chapters)

        for item in chapters:
            if item.order_index > insert_index:
                item.order_index += 1
                item.number = item.order_index
                item.updated_at = now
                self.chapter_repo.save(item)

        chapter = Chapter(
            id=ChapterId(str(uuid.uuid4())),
            novel_id=NovelId(str(work_id)),
            number=insert_index + 1,
            title=str(title or "").strip() or f"第{insert_index + 1}章",
            content="",
            status=ChapterStatus.DRAFT,
            created_at=now,
            updated_at=now,
            order_index=insert_index + 1,
            version=1,
        )
        self.chapter_repo.save(chapter)
        self._normalize_orders(work_id, updated_at=now)
        return self.chapter_repo.find_by_id(chapter.id.value)

    def update_chapter(
        self,
        chapter_id: str,
        *,
        title: Optional[str] = None,
        content: Optional[str] = None,
        expected_version: Optional[int] = None,
        force_override: bool = False,
    ) -> Chapter:
        chapter = self.chapter_repo.find_by_id(chapter_id)
        if not chapter:
            raise ValueError("chapter_not_found")
        if expected_version is not None and chapter.version != int(expected_version) and not force_override:
            raise ValueError("chapter_version_conflict")

        now = datetime.now(timezone.utc)
        if title is not None:
            chapter.title = str(title)
        if content is not None:
            chapter.content = str(content)
        chapter.updated_at = now
        chapter.version += 1
        self.chapter_repo.save(chapter)
        self._sync_work_word_count(chapter.novel_id.value)
        return self.chapter_repo.find_by_id(chapter.id.value)

    def delete_chapter(self, chapter_id: str) -> str:
        chapter = self.chapter_repo.find_by_id(chapter_id)
        if not chapter:
            raise ValueError("chapter_not_found")

        work_id = chapter.novel_id.value
        chapters = self.chapter_repo.list_by_work(work_id)
        current_index = next((index for index, item in enumerate(chapters) if item.id.value == chapter_id), -1)
        next_focus = ""
        if current_index >= 0:
            if current_index + 1 < len(chapters):
                next_focus = chapters[current_index + 1].id.value
            elif current_index - 1 >= 0:
                next_focus = chapters[current_index - 1].id.value

        self.chapter_repo.delete(chapter_id)
        self._normalize_orders(work_id, updated_at=datetime.now(timezone.utc))
        self._sync_work_word_count(work_id)
        return next_focus

    def reorder_chapters(self, work_id: str, ordered_chapter_ids: List[str]) -> List[Chapter]:
        existing = {item.id.value: item for item in self.chapter_repo.list_by_work(work_id)}
        ordered = [existing[item_id] for item_id in ordered_chapter_ids if item_id in existing]
        remaining = [item for item_id, item in existing.items() if item_id not in ordered_chapter_ids]
        final_list = [*ordered, *remaining]
        now = datetime.now(timezone.utc)

        for index, chapter in enumerate(final_list, start=1):
            chapter.order_index = index
            chapter.number = index
            chapter.updated_at = now
        self.chapter_repo.save_many(final_list)
        return self.chapter_repo.list_by_work(work_id)

    def _normalize_orders(self, work_id: str, *, updated_at: datetime) -> None:
        chapters = self.chapter_repo.list_by_work(work_id)
        for index, chapter in enumerate(chapters, start=1):
            if chapter.order_index != index or chapter.number != index:
                chapter.order_index = index
                chapter.number = index
                chapter.updated_at = updated_at
                self.chapter_repo.save(chapter)

    def _sync_work_word_count(self, work_id: str) -> None:
        work = self.work_repo.find_by_id(work_id)
        if not work:
            return
        chapters = self.chapter_repo.list_by_work(work_id)
        total = sum(item.word_count for item in chapters)
        work.update_word_count(total, datetime.now(timezone.utc))
        self.work_repo.save(work)
