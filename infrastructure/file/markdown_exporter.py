"""
Markdown导出器模块

作者：孔利群
"""

# 文件路径：infrastructure/file/markdown_exporter.py


import os
import re
from typing import List

from domain.entities.chapter import Chapter
from domain.entities.novel import Novel


class MarkdownExporter:
    """
    Markdown导出器
    
    用于将章节和小说导出为Markdown格式。
    """

    def _display_title(self, chapter: Chapter) -> str:
        raw_title = (chapter.title or "").strip()
        normalized = re.sub(r"^第[一二三四五六七八九十百千万零\d]+章\s*", "", raw_title).strip()
        return f"第{chapter.number}章 {normalized or raw_title or f'章节{chapter.number}'}"

    def export_chapter(self, chapter: Chapter, output_path: str) -> None:
        """
        导出单个章节
        
        Args:
            chapter: 章节实体
            output_path: 输出文件路径
        """
# 文件：模块：markdown_exporter

        content = self.export_chapter_content(chapter)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def export_chapter_content(self, chapter: Chapter) -> str:
        """
        导出章节内容
        
        Args:
            chapter: 章节实体
            
        Returns:
            Markdown格式的章节内容
        """
# 文件：模块：markdown_exporter

        lines = [
            f"# {self._display_title(chapter)}",
            "",
            chapter.content,
            ""
        ]
        
        return '\n'.join(lines)

    def export_novel(
        self, 
        novel: Novel, 
        chapters: List[Chapter], 
        output_path: str
    ) -> None:
        """
        导出整部小说
        
        Args:
            novel: 小说实体
            chapters: 章节列表
            output_path: 输出文件路径
        """
# 文件：模块：markdown_exporter

        lines = [
            self.format_metadata(novel),
            "",
            "---",
            "",
            "## 目录",
            ""
        ]
        
        for chapter in chapters:
            title = self._display_title(chapter)
            lines.append(f"- [{title}](#{title})")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        for chapter in chapters:
            lines.append(self.export_chapter_content(chapter))
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def format_metadata(self, novel: Novel) -> str:
        """
        格式化小说元数据
        
        Args:
            novel: 小说实体
            
        Returns:
            Markdown格式的元数据
        """
# 文件：模块：markdown_exporter

        lines = [
            f"# {novel.title}",
            "",
            f"**作者**: {novel.author}",
            "",
            f"**题材**: {novel.genre}",
            "",
            f"**字数**: {novel.current_word_count:,} / {novel.target_word_count:,}",
            ""
        ]
        
        return '\n'.join(lines)
