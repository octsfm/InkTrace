"""
响应数据传输对象模块

作者：孔利群
"""

# 文件路径：application/dto/response_dto.py


from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class BaseResponse(BaseModel):
    """基础响应DTO"""
    success: bool = True
    message: Optional[str] = None
    trace_id: Optional[str] = None


class NovelResponse(BaseResponse):
    """小说响应"""
    id: str
    title: str
    author: str = ""
    genre: str
    word_count: int = 0
    target_word_count: int
    current_word_count: int = 0
    chapter_count: int = 0
    chapters: Optional[List[Dict[str, Any]]] = None
    memory: Optional[Dict[str, Any]] = None
    status: str
    created_at: str
    updated_at: str


class ChapterResponse(BaseResponse):
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


class CharacterResponse(BaseResponse):
    """人物响应"""
    id: str
    novel_id: str
    name: str
    role: str
    background: str
    personality: str
    current_state: str
    appearance_count: int


class StyleAnalysisResponse(BaseResponse):
    """文风分析响应"""
    vocabulary_stats: Dict[str, Any]
    sentence_patterns: List[str]
    rhetoric_stats: Dict[str, int]
    dialogue_style: str
    narrative_voice: str
    pacing: str
    sample_sentences: List[str]


class PlotAnalysisResponse(BaseResponse):
    """剧情分析响应"""
    characters: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    foreshadowings: List[Dict[str, Any]]


class ConsistencyCheckResponse(BaseResponse):
    """连贯性检查响应"""
    is_valid: bool
    inconsistencies: List[Dict[str, str]]
    warnings: List[str]


class GenerateChapterResponse(BaseResponse):
    """生成章节响应"""
    chapter_id: str
    content: str
    word_count: int
    metadata: Optional[Dict[str, Any]] = None


class ContinueWritingResponse(BaseResponse):
    """续写章节响应"""
    content: str
    word_count: int
    metadata: Optional[Dict[str, Any]] = None


class ChapterAIActionResponse(BaseResponse):
    chapter_id: str
    action: str
    result_text: str
    analysis: Optional[Dict[str, Any]] = None
    outline_draft: Optional[Dict[str, Any]] = None
    used_fallback: bool = False


class ExportResponse(BaseResponse):
    """导出响应"""
    mode: str = "file"
    scope: str = "full"
    file_path: str = ""
    directory_path: str = ""
    file_count: int = 0
    format: str
    word_count: int
    chapter_count: int


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[str] = None
    trace_id: Optional[str] = None


class PagedResponse(BaseResponse):
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
