"""
响应数据传输对象模块

作者：孔利群
"""

# 文件路径：application/dto/response_dto.py


from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class GlobalConstraints(BaseModel):
    main_plot: str = ""
    hidden_plot: str = ""
    core_selling_points: List[str] = Field(default_factory=list)
    protagonist_core_traits: List[str] = Field(default_factory=list)
    must_keep_threads: List[str] = Field(default_factory=list)
    genre_guardrails: List[str] = Field(default_factory=list)


class ChapterAnalysisMemory(BaseModel):
    chapter_id: str = ""
    chapter_number: int = 0
    chapter_title: str = ""
    summary: str = ""
    events: List[str] = Field(default_factory=list)
    plot_role: str = ""
    conflict: str = ""
    foreshadowing: List[str] = Field(default_factory=list)
    hook: str = ""
    problems: List[str] = Field(default_factory=list)


class ChapterContinuationMemory(BaseModel):
    chapter_id: str = ""
    chapter_number: int = 0
    chapter_title: str = ""
    scene_summary: str = ""
    scene_state: Dict[str, str] = Field(default_factory=lambda: {"time": "", "location": "", "environment": ""})
    protagonist_state: Dict[str, str] = Field(default_factory=lambda: {"name": "", "physical_state": "", "emotion_state": "", "current_goal": "", "internal_tension": ""})
    active_characters: List[Dict[str, str]] = Field(default_factory=list)
    active_conflicts: List[str] = Field(default_factory=list)
    immediate_threads: List[str] = Field(default_factory=list)
    long_term_threads: List[str] = Field(default_factory=list)
    recent_reveals: List[str] = Field(default_factory=list)
    must_continue_points: List[str] = Field(default_factory=list)
    forbidden_jumps: List[str] = Field(default_factory=list)
    tone_and_pacing: Dict[str, str] = Field(default_factory=lambda: {"tone": "", "pace": ""})
    last_hook: str = ""


class ChapterTask(BaseModel):
    chapter_id: str = ""
    chapter_number: int = 0
    chapter_function: str = ""
    goals: List[str] = Field(default_factory=list)
    must_continue_points: List[str] = Field(default_factory=list)
    forbidden_jumps: List[str] = Field(default_factory=list)
    required_foreshadowing_action: str = "推进"
    required_hook_strength: str = "中"
    pace_target: str = ""
    opening_continuation: str = ""
    chapter_payoff: str = ""
    style_bias: str = ""


class StructuralDraft(BaseModel):
    chapter_id: str = ""
    chapter_number: int = 0
    title: str = ""
    content: str = ""
    source_task_id: str = ""
    generation_notes: List[str] = Field(default_factory=list)


class DetemplatedDraft(BaseModel):
    chapter_id: str = ""
    chapter_number: int = 0
    title: str = ""
    content: str = ""
    based_on_structural_draft_id: str = ""
    style_requirements_snapshot: Dict[str, Any] = Field(default_factory=dict)


class DraftIntegrityCheck(BaseModel):
    event_integrity_ok: bool = True
    motivation_integrity_ok: bool = True
    foreshadowing_integrity_ok: bool = True
    hook_integrity_ok: bool = True
    continuity_ok: bool = True
    risk_notes: List[str] = Field(default_factory=list)


class StyleRequirements(BaseModel):
    author_voice_keywords: List[str] = Field(default_factory=list)
    avoid_patterns: List[str] = Field(default_factory=list)
    preferred_rhythm: str = ""
    narrative_distance: str = ""
    dialogue_density: str = ""


class ProjectMemoryResponse(BaseModel):
    characters: List[Dict[str, Any]] = Field(default_factory=list)
    world_facts: Dict[str, Any] = Field(default_factory=dict)
    plot_arcs: List[Dict[str, Any]] = Field(default_factory=list)
    chapter_summaries: List[str] = Field(default_factory=list)
    current_state: Dict[str, Any] = Field(default_factory=dict)
    continuity_flags: List[Dict[str, Any]] = Field(default_factory=list)
    global_constraints: GlobalConstraints = Field(default_factory=GlobalConstraints)
    chapter_analysis_memories: List[ChapterAnalysisMemory] = Field(default_factory=list)
    chapter_continuation_memories: List[ChapterContinuationMemory] = Field(default_factory=list)
    chapter_tasks: List[ChapterTask] = Field(default_factory=list)
    structural_drafts: List[StructuralDraft] = Field(default_factory=list)
    detemplated_drafts: List[DetemplatedDraft] = Field(default_factory=list)
    draft_integrity_checks: List[DraftIntegrityCheck] = Field(default_factory=list)
    style_requirements: StyleRequirements = Field(default_factory=StyleRequirements)


class ProjectMemoryEnvelope(BaseModel):
    project_id: str
    memory: ProjectMemoryResponse = Field(default_factory=ProjectMemoryResponse)


class MemoryViewResponse(BaseModel):
    id: str = ""
    project_id: str = ""
    memory_id: str = ""
    main_characters: List[Dict[str, Any]] = Field(default_factory=list)
    world_summary: List[str] = Field(default_factory=list)
    main_plot_lines: List[str] = Field(default_factory=list)
    style_tags: List[str] = Field(default_factory=list)
    current_progress: str = ""
    outline_summary: List[str] = Field(default_factory=list)


class ProjectMemoryViewEnvelope(BaseModel):
    project_id: str
    memory_view: MemoryViewResponse = Field(default_factory=MemoryViewResponse)


class ChapterTaskResponse(BaseModel):
    id: str = ""
    project_id: str = ""
    branch_id: str = ""
    chapter_id: str = ""
    chapter_number: int = 0
    title: str = ""
    goal: str = ""
    conflict: str = ""
    progression: str = ""
    ending_hook: str = ""
    target_words: int = 2500
    related_arc_ids: List[str] = Field(default_factory=list)
    status: str = "ready"
    chapter_function: str = ""
    goals: List[str] = Field(default_factory=list)
    must_continue_points: List[str] = Field(default_factory=list)
    forbidden_jumps: List[str] = Field(default_factory=list)
    required_foreshadowing_action: str = "推进"
    required_hook_strength: str = "中"
    pace_target: str = ""
    opening_continuation: str = ""
    chapter_payoff: str = ""
    style_bias: str = ""


class ChapterPlanEnvelope(BaseModel):
    project_id: str
    branch_id: str
    plans: List[ChapterTaskResponse] = Field(default_factory=list)


class WriteResultResponse(BaseModel):
    project_id: str
    generated_chapter_ids: List[str] = Field(default_factory=list)
    latest_content: str = ""
    latest_title: str = ""
    latest_chapter_number: int = 0
    latest_chapter: Dict[str, Any] = Field(default_factory=dict)
    latest_structural_draft: Dict[str, Any] = Field(default_factory=dict)
    latest_detemplated_draft: Dict[str, Any] = Field(default_factory=dict)
    latest_draft_integrity_check: Dict[str, Any] = Field(default_factory=dict)
    used_structural_fallback: bool = False
    memory_view: MemoryViewResponse = Field(default_factory=MemoryViewResponse)


class StyleRequirementsEnvelope(BaseModel):
    project_id: str
    style_requirements: StyleRequirements = Field(default_factory=StyleRequirements)


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
