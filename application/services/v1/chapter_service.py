from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from application.services.v1.text_metrics import count_effective_characters
from domain.entities.chapter import Chapter
from domain.repositories.workbench import ChapterRepository, WorkRepository
from domain.types import ChapterId, ChapterStatus, NovelId
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.database.session import get_connection


class ChapterService:
    def __init__(
        self,
        chapter_repo: Optional[ChapterRepository] = None,
        work_repo: Optional[WorkRepository] = None,
    ):
        self.chapter_repo = chapter_repo or ChapterRepo()
        self.work_repo = work_repo or WorkRepo()

    def list_chapters(self, work_id: str) -> List[Chapter]:
        if not self.work_repo.find_by_id(str(work_id)):
            raise ValueError("work_not_found")
        return self.chapter_repo.list_by_work(work_id)

    def create_chapter(self, work_id: str, title: str = "", after_chapter_id: str = "") -> Chapter:
        work = self.work_repo.find_by_id(work_id)
        if not work:
            raise ValueError("work_not_found")

        now = datetime.now(timezone.utc)
        chapters = self.chapter_repo.list_by_work(work_id)
        next_order = len(chapters) + 1
        chapter = Chapter(
            id=ChapterId(str(uuid.uuid4())),
            work_id=NovelId(str(work_id)),
            title=str(title or "").strip(),
            content="",
            status=ChapterStatus.DRAFT,
            created_at=now,
            updated_at=now,
            order_index=next_order,
            version=1,
        )
        self.chapter_repo.save(chapter)
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
            raise ValueError("version_conflict")

        now = datetime.now(timezone.utc)
        if title is not None:
            chapter.title = str(title or "")
        if content is not None:
            chapter.content = str(content or "")
        # word_count is derived from content through the Chapter entity and persisted by ChapterRepo.
        count_effective_characters(chapter.content)
        chapter.updated_at = now
        chapter.version += 1
        self.chapter_repo.save(chapter)
        self._sync_work_word_count(chapter.work_id.value)
        return self.chapter_repo.find_by_id(chapter.id.value)

    def delete_chapter(self, chapter_id: str) -> str:
        chapter = self.chapter_repo.find_by_id(chapter_id)
        if not chapter:
            raise ValueError("chapter_not_found")

        work_id = chapter.work_id.value
        chapters = self.chapter_repo.list_by_work(work_id)
        current_index = next((index for index, item in enumerate(chapters) if item.id.value == chapter_id), -1)
        next_focus = ""
        if current_index >= 0:
            if current_index + 1 < len(chapters):
                next_focus = chapters[current_index + 1].id.value
            elif current_index - 1 >= 0:
                next_focus = chapters[current_index - 1].id.value

        self._delete_chapter_with_asset_cleanup(work_id, chapter_id)
        return next_focus

    def _delete_chapter_with_asset_cleanup(self, work_id: str, chapter_id: str) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            conn.execute("DELETE FROM chapter_outlines WHERE chapter_id = ?", (str(chapter_id),))
            conn.execute(
                "UPDATE timeline_events SET chapter_id = NULL, updated_at = ? WHERE chapter_id = ?",
                (updated_at, str(chapter_id)),
            )
            conn.execute(
                """
                UPDATE foreshadows
                SET introduced_chapter_id = CASE WHEN introduced_chapter_id = ? THEN NULL ELSE introduced_chapter_id END,
                    resolved_chapter_id = CASE WHEN resolved_chapter_id = ? THEN NULL ELSE resolved_chapter_id END,
                    updated_at = ?
                WHERE introduced_chapter_id = ? OR resolved_chapter_id = ?
                """,
                (str(chapter_id), str(chapter_id), updated_at, str(chapter_id), str(chapter_id)),
            )
            rows = conn.execute(
                "SELECT id, content_tree_json FROM work_outlines WHERE work_id = ?",
                (str(work_id),),
            ).fetchall()
            for row in rows:
                try:
                    tree = json.loads(str(row["content_tree_json"] or "[]"))
                except json.JSONDecodeError:
                    tree = []
                cleared_tree = self._clear_chapter_refs_in_tree(tree, str(chapter_id))
                conn.execute(
                    "UPDATE work_outlines SET content_tree_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(cleared_tree, ensure_ascii=False, separators=(",", ":")), updated_at, row["id"]),
                )

            conn.execute("DELETE FROM chapters WHERE id = ?", (str(chapter_id),))
            remaining = conn.execute(
                """
                SELECT id
                FROM chapters
                WHERE work_id = ?
                ORDER BY order_index ASC
                """,
                (str(work_id),),
            ).fetchall()
            chapter_columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(chapters)").fetchall()}
            for index, row in enumerate(remaining, start=1):
                conn.execute(
                    "UPDATE chapters SET order_index = ?, updated_at = ? WHERE id = ?",
                    (index, updated_at, row["id"]),
                )
                if "number" in chapter_columns:
                    conn.execute("UPDATE chapters SET number = ? WHERE id = ?", (index, row["id"]))
                if "chapter_number" in chapter_columns:
                    conn.execute("UPDATE chapters SET chapter_number = ? WHERE id = ?", (index, row["id"]))
            total = conn.execute(
                "SELECT COALESCE(SUM(word_count), 0) FROM chapters WHERE work_id = ?",
                (str(work_id),),
            ).fetchone()[0]
            conn.execute(
                "UPDATE works SET word_count = ?, updated_at = ? WHERE id = ?",
                (int(total or 0), updated_at, str(work_id)),
            )

    def _clear_chapter_refs_in_tree(self, value, chapter_id: str):
        if isinstance(value, list):
            return [self._clear_chapter_refs_in_tree(item, chapter_id) for item in value]
        if not isinstance(value, dict):
            return value
        next_value = dict(value)
        if next_value.get("chapter_ref") == chapter_id:
            next_value["chapter_ref"] = None
        if isinstance(next_value.get("children"), list):
            next_value["children"] = [
                self._clear_chapter_refs_in_tree(item, chapter_id)
                for item in next_value["children"]
            ]
        return next_value

    def reorder_chapters(self, work_id: str, mappings: List[dict]) -> List[Chapter]:
        if not self.work_repo.find_by_id(str(work_id)):
            raise ValueError("work_not_found")
        chapters = self.chapter_repo.list_by_work(work_id)
        existing_ids = [item.id.value for item in chapters]
        if len(mappings) != len(chapters):
            raise ValueError("invalid_input")

        submitted_ids = [str(item.get("id", "")) for item in mappings]
        submitted_orders = [int(item.get("order_index", 0)) for item in mappings]
        if len(set(submitted_ids)) != len(submitted_ids):
            raise ValueError("invalid_input")
        if set(submitted_ids) != set(existing_ids):
            raise ValueError("invalid_input")
        if sorted(submitted_orders) != list(range(1, len(chapters) + 1)):
            raise ValueError("invalid_input")

        chapter_by_id = {item.id.value: item for item in chapters}
        now = datetime.now(timezone.utc)
        for item in mappings:
            chapter = chapter_by_id[str(item["id"])]
            order_index = int(item["order_index"])
            chapter.order_index = order_index
            chapter.updated_at = now
        self.chapter_repo.save_many(list(chapter_by_id.values()))
        return self.chapter_repo.list_by_work(work_id)

    def _normalize_orders(self, work_id: str, *, updated_at: datetime) -> None:
        chapters = self.chapter_repo.list_by_work(work_id)
        for index, chapter in enumerate(chapters, start=1):
            if chapter.order_index != index:
                chapter.order_index = index
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
