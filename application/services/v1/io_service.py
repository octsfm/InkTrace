from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.file.txt_exporter import TxtExporter
from infrastructure.file.txt_parser import TxtParser

from application.services.v1.work_service import WorkService


class IOService:
    MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024

    def __init__(
        self,
        work_service: Optional[WorkService] = None,
        work_repo: Optional[WorkRepo] = None,
        chapter_repo: Optional[ChapterRepo] = None,
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
        work = self.work_service.create_work(title, author)
        imported = self._build_import_chapters(payload)
        existing = self.chapter_repo.list_by_work(work.id)
        if not existing:
            return work

        first = existing[0]
        if not imported:
            return work

        first_item = imported[0]
        first.order_index = 1
        first.title = str(first_item.get("title") or "")
        first.content = str(first_item.get("content") or "")
        self.chapter_repo.save(first)

        for index, item in enumerate(imported[1:], start=2):
            chapter = self.work_service._build_first_chapter(work.id, first.created_at)
            chapter.order_index = index
            chapter.title = str(item.get("title") or "")
            chapter.content = str(item.get("content") or "")
            self.chapter_repo.save(chapter)

        chapters = self.chapter_repo.list_by_work(work.id)
        total_words = sum(item.word_count for item in chapters)
        work.update_word_count(total_words, work.updated_at)
        self.work_repo.save(work)
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
