from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from domain.entities.work import Work
from domain.repositories.workbench import ChapterRepository, WorkRepository
from infrastructure.database.session import get_connection
from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.file.txt_exporter import TxtExporter
from infrastructure.file.txt_parser import TxtParser

from application.services.v1.work_service import WorkService


class IOService:
    MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024

    def __init__(
        self,
        work_service: Optional[WorkService] = None,
        work_repo: Optional[WorkRepository] = None,
        chapter_repo: Optional[ChapterRepository] = None,
        txt_parser: Optional[TxtParser] = None,
        txt_exporter: Optional[TxtExporter] = None,
    ):
        self.work_repo = work_repo or WorkRepo()
        self.chapter_repo = chapter_repo or ChapterRepo()
        self.work_service = work_service or WorkService(work_repo=self.work_repo, chapter_repo=self.chapter_repo)
        self.txt_parser = txt_parser or TxtParser()
        self.txt_exporter = txt_exporter or TxtExporter()

    def import_txt_upload(self, filename: str, raw_bytes: bytes, *, title: str = "", author: str = ""):
        if len(raw_bytes) > self.MAX_UPLOAD_SIZE_BYTES:
            raise ValueError("txt_file_too_large")
        payload = self.txt_parser.parse_uploaded_novel_file(raw_bytes)
        work_title = str(title or "").strip() or Path(str(filename or "未命名作品.txt")).stem or "未命名作品"
        return self._import_from_payload(payload, title=work_title, author=author)

    def _import_from_payload(self, payload: dict, *, title: str, author: str):
        imported = self._build_import_chapters(payload)
        now = datetime.now(timezone.utc)
        work = Work(
            id=str(uuid.uuid4()),
            title=str(title or "").strip(),
            author=str(author or "").strip(),
            word_count=0,
            created_at=now,
            updated_at=now,
        )
        chapters = []
        with get_connection() as conn:
            self.work_repo._save_with_connection(conn, work)
            for index, item in enumerate(imported, start=1):
                chapter = self.work_service._build_first_chapter(work.id, now)
                chapter.order_index = index
                chapter.title = str(item.get("title") or "")
                chapter.content = str(item.get("content") or "")
                self.chapter_repo._save_with_connection(conn, chapter)
                chapters.append(chapter)
            work.update_word_count(sum(item.word_count for item in chapters), now)
            self.work_repo._save_with_connection(conn, work)
        return work

    def _build_import_chapters(self, payload: dict) -> list[dict]:
        intro = str(payload.get("intro") or "").strip()
        chapters = payload.get("chapters") or []
        items: list[dict] = []
        if intro:
            items.append({"title": "前言", "content": intro})
        for item in chapters:
            if not isinstance(item, dict):
                continue
            items.append(
                {
                    "title": str(item.get("title") or "").strip(),
                    "content": str(item.get("content") or ""),
                }
            )
        if not items:
            items.append({"title": "全本导入", "content": ""})
        return items

    def export_txt(
        self,
        work_id: str,
        *,
        include_titles: bool = True,
        gap_lines: int = 1,
    ) -> tuple[str, bytes]:
        work = self.work_repo.find_by_id(work_id)
        if not work:
            raise ValueError("work_not_found")
        if gap_lines not in {0, 1, 2}:
            raise ValueError("invalid_input")

        chapters = sorted(
            self.chapter_repo.list_by_work(work_id),
            key=lambda item: (item.order_index, item.created_at),
        )
        content = self.txt_exporter.build_novel_text(
            chapters,
            include_titles=include_titles,
            gap_lines=gap_lines,
        )
        return self._build_export_filename(work.title), content.encode("utf-8")

    def _build_export_filename(self, work_title: str) -> str:
        safe_title = "".join("_" if ch in '<>:"/\\|?*' else ch for ch in str(work_title or "未命名作品")).strip()
        safe_title = safe_title.rstrip(". ") or "未命名作品"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{safe_title}-{stamp}.txt"
