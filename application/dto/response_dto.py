"""
响应数据传输对象模块

作者：孔利群
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class NovelResponse:
    """小说响应"""
    id: str
    title: str
    author: str
    genre: str
    target_word_count: int
    current_word_count: int
    chapter_count: int
    created_at: str
    updated_at: str


@dataclass
class ChapterResponse:
    """章节响应"""
    id: str
    novel_id: str
    number: int
    title: str
    content: str
    word_count: int
    status: str
    created_at: str
    updated_at: str


@dataclass
class CharacterResponse:
    """人物响应"""
    id: str
    novel_id: str
    name: str
    role: str
    background: str
    personality: str
    current_state: str
    appearance_count: int


@dataclass
class StyleAnalysisResponse:
    """文风分析响应"""
    vocabulary_stats: Dict[str, Any]
    sentence_patterns: List[str]
    rhetoric_stats: Dict[str, int]
    dialogue_style: str
    narrative_voice: str
    pacing: str
    sample_sentences: List[str]


@dataclass
class PlotAnalysisResponse:
    """剧情分析响应"""
    characters: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    foreshadowings: List[Dict[str, Any]]


@dataclass
class ConsistencyCheckResponse:
    """连贯性检查响应"""
    is_valid: bool
    inconsistencies: List[Dict[str, str]]
    warnings: List[str]


@dataclass
class GenerateChapterResponse:
    """生成章节响应"""
    chapter_id: str
    content: str
    word_count: int
    consistency_report: Optional[ConsistencyCheckResponse] = None


@dataclass
class ExportResponse:
    """导出响应"""
    file_path: str
    format: str
    word_count: int
    chapter_count: int


@dataclass
class ErrorResponse:
    """错误响应"""
    error_code: str
    message: str
    details: Optional[str] = None


@dataclass
class PagedResponse:
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
