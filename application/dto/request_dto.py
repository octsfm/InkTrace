"""
请求数据传输对象模块

作者：孔利群
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class CreateNovelRequest:
    """创建小说请求"""
    title: str
    author: str
    genre: str
    target_word_count: int


@dataclass
class ImportNovelRequest:
    """导入小说请求"""
    novel_id: str
    file_path: str


@dataclass
class AnalyzeNovelRequest:
    """分析小说请求"""
    novel_id: str
    analyze_style: bool = True
    analyze_plot: bool = True


@dataclass
class GenerateChapterRequest:
    """生成章节请求"""
    novel_id: str
    plot_direction: str
    chapter_count: int = 1
    target_word_count: int = 2100
    enable_style_mimicry: bool = True
    enable_consistency_check: bool = True


@dataclass
class PlanPlotRequest:
    """规划剧情请求"""
    novel_id: str
    direction: str
    chapter_count: int


@dataclass
class ExportNovelRequest:
    """导出小说请求"""
    novel_id: str
    output_path: str
    format: str = "markdown"


@dataclass
class UpdateChapterRequest:
    """更新章节请求"""
    chapter_id: str
    content: Optional[str] = None
    title: Optional[str] = None


@dataclass
class CreateCharacterRequest:
    """创建人物请求"""
    novel_id: str
    name: str
    role: str
    background: str = ""
    personality: str = ""
