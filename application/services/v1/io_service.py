from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from infrastructure.database.repositories import ChapterRepo, WorkRepo
from infrastructure.file.txt_exporter import TxtExporter
from infrastructure.file.txt_parser import TxtParser

from application.services.v1.work_service import WorkService


class IOService:
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

    def import_txt(self, file_path: str, *, title: str = "", author: str = ""):
        payload = self.txt_parser.parse_novel_file(file_path)
        work_title = str(title or "").strip() or Path(file_path).stem or "未命名作品"
        return self._import_from_payload(payload, title=work_title, author=author)

    def import_txt_upload(self, filename: str, raw_bytes: bytes, *, title: str = "", author: str = ""):
        payload = self.txt_parser.parse_uploaded_novel_file(raw_bytes)
        work_title = str(title or "").strip() or Path(str(filename or "未命名作品.txt")).stem or "未命名作品"
        return self._import_from_payload(payload, title=work_title, author=author)

    def path_import_allowed(self) -> bool:
        return str(os.getenv("INKTRACE_ALLOW_PATH_IMPORT", "")).strip().lower() in {"1", "true", "yes", "on"}

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
        first.number = 1
        first.order_index = 1
        first.title = str(first_item.get("title") or first.title)
        first.content = str(first_item.get("content") or "")
        self.chapter_repo.save(first)

        for index, item in enumerate(imported[1:], start=2):
            chapter = self.work_service._build_first_chapter(work.id, first.created_at)
            chapter.number = index
            chapter.order_index = index
            chapter.title = str(item.get("title") or f"第{index}章")
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
        return items

    def export_txt(self, work_id: str, output_path: str = "") -> str:
        work = self.work_repo.find_by_id(work_id)
        if not work:
            raise ValueError("work_not_found")

        chapters = sorted(
            self.chapter_repo.list_by_work(work_id),
            key=lambda item: (item.order_index, item.created_at),
        )
        final_path = Path(output_path) if output_path else Path("exports") / f"{work.title}.txt"
        if not chapters:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_path.write_text("", encoding="utf-8")
            return str(final_path)
        novel_view = SimpleNamespace(
            title=work.title,
            author=work.author,
            genre="",
            current_word_count=sum(item.word_count for item in chapters),
            target_word_count=sum(item.word_count for item in chapters),
        )
        self.txt_exporter.export_novel(novel_view, chapters, str(final_path))
        return str(final_path)
