"""
请求数据传输对象模块

作者：孔利群
"""

# 文件路径：application/dto/request_dto.py


from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class BaseRequest(BaseModel):
    """基础请求DTO，包含上下文信息"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None


class CreateNovelRequest(BaseRequest):
    """创建小说请求"""
    title: str = Field(..., min_length=1, max_length=100)
    author: str = Field(..., min_length=1, max_length=50)
    genre: str = Field(..., min_length=1)
    target_word_count: int = Field(..., gt=0, le=50000000)
    options: Optional[Dict[str, Any]] = None


class ImportNovelRequest(BaseRequest):
    """导入小说请求"""
    novel_id: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    options: Optional[Dict[str, Any]] = None


class AnalyzeNovelRequest(BaseRequest):
    """分析小说请求"""
    novel_id: str = Field(..., min_length=1)
    analyze_style: bool = True
    analyze_plot: bool = True
    options: Optional[Dict[str, Any]] = None


class GenerateChapterRequest(BaseRequest):
    """生成章节请求 - Agent友好"""
    novel_id: str = Field(..., min_length=1)
    goal: str = Field(..., min_length=1)
    constraints: Optional[List[str]] = None
    context_summary: Optional[str] = None
    chapter_count: int = Field(1, ge=1, le=100)
    target_word_count: int = Field(2100, gt=0, le=50000)
    options: Optional[Dict[str, Any]] = None


class ContinueWritingRequest(BaseRequest):
    """续写下一章请求"""
    novel_id: str = Field(..., min_length=1)
    goal: str = Field(..., min_length=1)
    target_word_count: int = Field(2100, gt=0, le=50000)
    options: Optional[Dict[str, Any]] = None


class GenerateBranchesRequest(BaseRequest):
    """生成剧情分支请求"""
    novel_id: str = Field(..., min_length=1)
    branch_count: int = Field(3, ge=3, le=5)
    current_chapter_content: Optional[str] = None
    direction_hint: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class PlanPlotRequest(BaseRequest):
    """规划剧情请求 - Agent友好"""
    novel_id: str = Field(..., min_length=1)
    goal: str = Field(..., min_length=1)
    constraints: Optional[List[str]] = None
    chapter_count: int = Field(..., ge=1, le=100)
    options: Optional[Dict[str, Any]] = None


class ExportNovelRequest(BaseRequest):
    """导出小说请求"""
    novel_id: str = Field(..., min_length=1)
    output_path: str = Field(..., min_length=1)
    format: str = Field("markdown", min_length=1)
    options: Optional[Dict[str, Any]] = None


class UpdateChapterRequest(BaseRequest):
    """更新章节请求"""
    chapter_id: str = Field(..., min_length=1)
    content: Optional[str] = None
    title: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class CreateCharacterRequest(BaseRequest):
    """创建人物请求"""
    novel_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=50)
    role: str = Field(..., min_length=1)
    background: str = ""
    personality: str = ""
    options: Optional[Dict[str, Any]] = None
