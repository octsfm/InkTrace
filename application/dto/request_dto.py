"""
请求数据传输对象模块

作者：孔利群
"""

# 文件路径：application/dto/request_dto.py


from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

from domain.constants.story_constants import (
    DEFAULT_BRANCH_COUNT,
    DEFAULT_GENERATE_CHAPTER_COUNT,
    DEFAULT_TARGET_WORDS_PER_CHAPTER,
)


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
    summary: str = ""
    tags: List[str] = Field(default_factory=list)
    target_word_count: int = Field(..., gt=0, le=50000000)
    options: Optional[Dict[str, Any]] = None


class ImportNovelRequest(BaseRequest):
    """导入小说请求"""
    novel_id: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    author: Optional[str] = ""
    import_mode: str = "full"
    chapter_items: List[Dict[str, Any]] = Field(default_factory=list)
    outline_path: Optional[str] = None
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
    format: Literal["markdown", "txt"] = "markdown"
    scope: Literal["full", "by_chapter"] = "full"
    options: Optional[Dict[str, Any]] = None


class UpdateChapterRequest(BaseRequest):
    """更新章节请求"""
    chapter_id: str = Field(..., min_length=1)
    content: Optional[str] = None
    title: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class ChapterOutlineRequest(BaseRequest):
    chapter_id: str = Field(..., min_length=1)
    goal: str = ""
    conflict: str = ""
    events: List[str] = Field(default_factory=list)
    character_progress: str = ""
    ending_hook: str = ""
    opening_continuation: str = ""
    notes: str = ""


class ChapterAIActionRequest(BaseRequest):
    chapter_id: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    content: str = ""
    outline: Optional[Dict[str, Any]] = None
    style: str = ""
    global_memory_summary: str = ""
    global_outline_summary: str = ""
    recent_chapter_summaries: List[str] = Field(default_factory=list)
    last_chapter_tail: str = ""
    relevant_characters: List[Dict[str, Any]] = Field(default_factory=list)
    relevant_foreshadowing: List[str] = Field(default_factory=list)
    chapter_task: Optional[Dict[str, Any]] = None
    style_requirements: Optional[Dict[str, Any]] = None
    target_word_count: int = Field(2000, ge=200, le=10000)
    mode: str = ""
    selection_context: Optional[Dict[str, Any]] = None
    selected_text: str = ""
    highlight_range: Optional[Dict[str, Any]] = None


class ContinuationContextRequest(BaseRequest):
    project_id: str = Field(..., min_length=1)
    chapter_id: str = Field(..., min_length=1)
    branch_id: str = ""
    chapter_plan_id: str = ""


class ChapterTaskRequest(BaseRequest):
    chapter_id: str = Field(..., min_length=1)
    continuation_context: Dict[str, Any] = Field(default_factory=dict)
    plan_id: str = ""


class DetemplatingRewriteRequest(BaseRequest):
    chapter_id: str = Field(..., min_length=1)
    structural_draft_id: str = Field(..., min_length=1)
    chapter_task: Dict[str, Any] = Field(default_factory=dict)
    global_constraints: Dict[str, Any] = Field(default_factory=dict)
    style_requirements: Dict[str, Any] = Field(default_factory=dict)


class ImportProjectRequest(BaseRequest):
    project_name: str = Field(..., min_length=1)
    author: str = ""
    genre: str = ""
    target_word_count: int = Field(default=8000000, ge=10000, le=50000000)
    novel_file_path: str = Field(..., min_length=1)
    import_mode: str = "full"
    chapter_items: List[Dict[str, Any]] = Field(default_factory=list)
    outline_file_path: str = ""
    auto_organize: bool = True


class OrganizeRequest(BaseRequest):
    mode: str = "full_reanalyze"
    rebuild_memory: bool = True
    batch_size_chapters: Optional[int] = Field(default=None, ge=2, le=20)


class ChapterDetailOutlineSceneRequest(BaseModel):
    scene_no: int = Field(default=0, ge=0)
    goal: str = ""
    conflict: str = ""
    turning_point: str = ""
    hook: str = ""
    foreshadow: str = ""
    target_words: int = Field(default=0, ge=0)


class ChapterDetailOutlineRequest(BaseRequest):
    chapter_id: str = Field(..., min_length=1)
    scenes: List[ChapterDetailOutlineSceneRequest] = Field(default_factory=list)
    notes: str = ""


class BranchesRequest(BaseRequest):
    direction_hint: str = ""
    branch_count: int = Field(default=DEFAULT_BRANCH_COUNT, ge=3, le=5)


class ChapterPlanRequest(BaseRequest):
    branch_id: str = Field(..., min_length=1)
    chapter_count: int = Field(default=DEFAULT_GENERATE_CHAPTER_COUNT, ge=1, le=10)
    target_words_per_chapter: int = Field(default=DEFAULT_TARGET_WORDS_PER_CHAPTER, ge=500, le=10000)
    planning_mode: str = "light_planning"
    target_arc_id: str = ""
    allow_deep_planning: bool = False


class WriteRequest(BaseRequest):
    plan_ids: List[str] = Field(default_factory=list)
    auto_commit: bool = True
    planning_mode: str = "light_planning"
    target_arc_id: str = ""


class WritePreviewRequest(BaseRequest):
    plan_id: str = Field(..., min_length=1)
    target_word_count: int = Field(default=DEFAULT_TARGET_WORDS_PER_CHAPTER, ge=500, le=10000)
    style_requirements: Dict[str, Any] = Field(default_factory=dict)
    planning_mode: str = "light_planning"
    target_arc_id: str = ""


class WriteCommitRequest(BaseRequest):
    plan_ids: List[str] = Field(default_factory=list)
    chapter_count: int = Field(default=DEFAULT_GENERATE_CHAPTER_COUNT, ge=1, le=10)
    auto_commit: bool = True
    planning_mode: str = "light_planning"
    target_arc_id: str = ""


class RefreshMemoryRequest(BaseRequest):
    from_chapter_number: int = Field(..., ge=1)
    to_chapter_number: int = Field(..., ge=1)


class StyleRequirementsRequest(BaseRequest):
    author_voice_keywords: List[str] = Field(default_factory=list)
    avoid_patterns: List[str] = Field(default_factory=list)
    preferred_rhythm: str = ""
    narrative_distance: str = ""
    dialogue_density: str = ""
    source_type: str = "manual"
    version: int = Field(default=1, ge=1)


class ExtractStyleRequirementsRequest(BaseRequest):
    sample_chapter_count: int = Field(default=3, ge=1, le=10)


class CreateCharacterRequest(BaseRequest):
    """创建人物请求"""
    novel_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=50)
    role: str = Field(..., min_length=1)
    background: str = ""
    personality: str = ""
    options: Optional[Dict[str, Any]] = None
