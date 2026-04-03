"""
导出服务模块
"""

from pathlib import Path
import os
import re

from application.services.logging_service import build_log_context, get_logger
from domain.types import NovelId
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from infrastructure.file.markdown_exporter import MarkdownExporter
from infrastructure.file.txt_exporter import TxtExporter
from application.dto.request_dto import ExportNovelRequest
from application.dto.response_dto import ExportResponse


EXPORTS_ROOT = Path("exports")


class ExportService:
    """
    导出服务。

    负责将整本小说导出到 exports 目录，并返回可下载的相对路径。
    """

    def __init__(
        self,
        novel_repo: INovelRepository,
        chapter_repo: IChapterRepository,
    ):
        self.novel_repo = novel_repo
        self.chapter_repo = chapter_repo
        self.markdown_exporter = MarkdownExporter()
        self.txt_exporter = TxtExporter()
        self.logger = get_logger(__name__)

    def export_novel(self, request: ExportNovelRequest) -> ExportResponse:
        self.logger.info(
            "导出开始",
            extra=build_log_context(
                event="export_started",
                novel_id=request.novel_id,
                scope=request.scope,
                format=request.format,
                output_path=request.output_path,
            ),
        )
        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            self.logger.error(
                "导出失败",
                extra=build_log_context(
                    event="export_failed",
                    novel_id=request.novel_id,
                    scope=request.scope,
                    format=request.format,
                    output_path=request.output_path,
                    error="novel_not_found",
                ),
            )
            raise ValueError(f"小说不存在: {request.novel_id}")
        if not str(novel.author or "").strip():
            novel.author = "未知"

        chapters = self.chapter_repo.find_by_novel(novel.id)
        export_scope = str(request.scope or "full").strip().lower()
        export_format = str(request.format or "markdown").strip().lower()
        options = request.options if isinstance(request.options, dict) else {}
        if export_scope not in {"full", "by_chapter"}:
            self.logger.error(
                "导出失败",
                extra=build_log_context(
                    event="export_failed",
                    novel_id=request.novel_id,
                    scope=export_scope,
                    format=export_format,
                    output_path=request.output_path,
                    error="invalid_scope",
                ),
            )
            raise ValueError("不支持的导出范围，仅支持 full / by_chapter")
        if export_format not in {"markdown", "txt"}:
            self.logger.error(
                "导出失败",
                extra=build_log_context(
                    event="export_failed",
                    novel_id=request.novel_id,
                    scope=export_scope,
                    format=export_format,
                    output_path=request.output_path,
                    error="invalid_format",
                ),
            )
            raise ValueError(f"不支持的导出格式: {request.format}")
        word_count = sum(chapter.word_count for chapter in chapters)
        novel.current_word_count = word_count
        if export_scope == "full":
            output_path, response_path = self._resolve_output_path(request.output_path, novel.title, export_format)
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            if os.path.exists(output_path):
                os.remove(output_path)
            if export_format == "markdown":
                self.export_full_markdown(novel, chapters, output_path)
            else:
                self.export_full_txt(novel, chapters, output_path)
            response = ExportResponse(
                mode="file",
                scope="full",
                file_path=response_path,
                directory_path="",
                file_count=1,
                format=export_format,
                word_count=word_count,
                chapter_count=len(chapters),
            )
            self.logger.info(
                "导出完成",
                extra=build_log_context(
                    event="export_finished",
                    novel_id=request.novel_id,
                    scope="full",
                    format=export_format,
                    output_path=response_path,
                    chapter_count=len(chapters),
                    file_count=1,
                ),
            )
            return response

        chapter_export_mode = str(options.get("chapter_export_mode") or "single").strip().lower()
        if chapter_export_mode not in {"single", "every_10"}:
            raise ValueError("按章节导出模式仅支持 single / every_10")
        directory_path, response_dir = self._resolve_output_directory(request.output_path, novel.title)
        os.makedirs(directory_path, exist_ok=True)
        if export_format == "markdown":
            file_count = self.export_chapters_markdown(chapters, directory_path, chapter_export_mode)
        else:
            file_count = self.export_chapters_txt(chapters, directory_path, chapter_export_mode)
        response = ExportResponse(
            mode="directory",
            scope="by_chapter",
            file_path="",
            directory_path=response_dir,
            file_count=file_count,
            format=export_format,
            word_count=word_count,
            chapter_count=len(chapters),
        )
        self.logger.info(
            "导出完成",
            extra=build_log_context(
                event="export_finished",
                novel_id=request.novel_id,
                scope="by_chapter",
                format=export_format,
                output_path=response_dir,
                chapter_count=len(chapters),
                file_count=file_count,
            ),
        )
        return response

    def export_full_markdown(self, novel, chapters, output_path: str) -> None:
        self.markdown_exporter.export_novel(novel, chapters, output_path)

    def export_full_txt(self, novel, chapters, output_path: str) -> None:
        self.txt_exporter.export_novel(novel, chapters, output_path)

    def export_chapters_markdown(self, chapters, output_dir: str, mode: str = "single") -> int:
        if mode == "every_10":
            return self._export_chapter_batches_markdown(chapters, output_dir, 10)
        for chapter in chapters:
            filename = f"{chapter.number:04d}_{self._sanitize_filename(self._chapter_filename_title(chapter), 'chapter')}.md"
            self.markdown_exporter.export_chapter(chapter, str(Path(output_dir) / filename))
        return len(chapters)

    def export_chapters_txt(self, chapters, output_dir: str, mode: str = "single") -> int:
        if mode == "every_10":
            return self._export_chapter_batches_txt(chapters, output_dir, 10)
        for chapter in chapters:
            filename = f"{chapter.number:04d}_{self._sanitize_filename(self._chapter_filename_title(chapter), 'chapter')}.txt"
            self.txt_exporter.export_chapter(chapter, str(Path(output_dir) / filename))
        return len(chapters)

    def _export_chapter_batches_markdown(self, chapters, output_dir: str, batch_size: int) -> int:
        if not chapters:
            return 0
        count = 0
        for start in range(0, len(chapters), batch_size):
            chunk = chapters[start:start + batch_size]
            first_no = int(chunk[0].number)
            last_no = int(chunk[-1].number)
            filename = f"{first_no:04d}_{last_no:04d}_chapters.md"
            self.markdown_exporter.export_chapter_batch(chunk, str(Path(output_dir) / filename))
            count += 1
        return count

    def _export_chapter_batches_txt(self, chapters, output_dir: str, batch_size: int) -> int:
        if not chapters:
            return 0
        count = 0
        for start in range(0, len(chapters), batch_size):
            chunk = chapters[start:start + batch_size]
            first_no = int(chunk[0].number)
            last_no = int(chunk[-1].number)
            filename = f"{first_no:04d}_{last_no:04d}_chapters.txt"
            self.txt_exporter.export_chapter_batch(chunk, str(Path(output_dir) / filename))
            count += 1
        return count

    def _chapter_filename_title(self, chapter) -> str:
        raw_title = str(getattr(chapter, "title", "") or "").strip()
        normalized = re.sub(r"^第[一二三四五六七八九十百千万零\d]+章\s*", "", raw_title).strip()
        return normalized or raw_title or f"章节{getattr(chapter, 'number', 0)}"

    def _resolve_output_path(self, requested_path: str, novel_title: str, export_format: str) -> tuple[str, str]:
        suffix = ".md" if export_format == "markdown" else f".{export_format}"
        target = Path(requested_path or "").expanduser()

        if target.is_absolute():
            final_path = target if target.suffix else target.with_suffix(suffix)
            return str(final_path), str(final_path)

        parts = [part for part in target.parts if part not in ("", ".")]
        if parts and parts[0].lower() == "exports":
            parts = parts[1:]

        safe_dirs = [self._sanitize_filename(part, "export") for part in parts[:-1]]
        requested_name = parts[-1] if parts else ""
        requested_target = Path(requested_name) if requested_name else Path()

        if requested_target.name:
            stem = self._sanitize_filename(requested_target.stem, self._sanitize_filename(novel_title))
            ext = requested_target.suffix or suffix
        else:
            stem = self._sanitize_filename(novel_title)
            ext = suffix

        filename = f"{stem}{ext}"
        relative_path = Path(*safe_dirs, filename) if safe_dirs else Path(filename)
        absolute_path = EXPORTS_ROOT / relative_path
        return str(absolute_path), relative_path.as_posix()

    def _resolve_output_directory(self, requested_path: str, novel_title: str) -> tuple[str, str]:
        target = Path(requested_path or "").expanduser()
        if target.is_absolute():
            final_dir = target
            return str(final_dir), str(final_dir)
        parts = [part for part in target.parts if part not in ("", ".")]
        if parts and parts[0].lower() == "exports":
            parts = parts[1:]
        safe_parts = [self._sanitize_filename(part, "export") for part in parts]
        if not safe_parts:
            safe_parts = [self._sanitize_filename(novel_title)]
        relative_path = Path(*safe_parts)
        absolute_path = EXPORTS_ROOT / relative_path
        return str(absolute_path), relative_path.as_posix()

    def _sanitize_filename(self, name: str, fallback: str = "novel_export") -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (name or "").strip())
        cleaned = cleaned.strip(" .")
        return cleaned or fallback
