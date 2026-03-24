"""
导出服务模块
"""

from pathlib import Path
import os
import re

from domain.types import NovelId
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from infrastructure.file.markdown_exporter import MarkdownExporter
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

    def export_novel(self, request: ExportNovelRequest) -> ExportResponse:
        novel = self.novel_repo.find_by_id(NovelId(request.novel_id))
        if not novel:
            raise ValueError(f"小说不存在: {request.novel_id}")

        chapters = self.chapter_repo.find_by_novel(novel.id)
        output_path, response_path = self._resolve_output_path(request.output_path, novel.title, request.format)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if request.format == "markdown":
            self.markdown_exporter.export_novel(novel, chapters, output_path)
        else:
            raise ValueError(f"不支持的导出格式: {request.format}")

        return ExportResponse(
            file_path=response_path,
            format=request.format,
            word_count=novel.current_word_count,
            chapter_count=len(chapters),
        )

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

    def _sanitize_filename(self, name: str, fallback: str = "novel_export") -> str:
        cleaned = re.sub(r'[<>:"/\\\\|?*\\x00-\\x1f]', "_", (name or "").strip())
        cleaned = cleaned.strip(" .")
        return cleaned or fallback
