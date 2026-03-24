"""
DDD重构版核心领域模型定义。

本文件集中声明跨模块共享的数据结构，覆盖：
- Project / Novel / Chapter / Outline
- ProjectMemory及其子结构
- StoryBranch / ChapterPlan / WritingSession
- MemoryView / WorkflowJob / LLMConfig
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal, Optional


ProjectStatus = Literal["active", "archived", "draft"]
ChapterSourceType = Literal["imported", "generated", "edited"]
ChapterStatus = Literal["draft", "confirmed"]
BranchStatus = Literal["candidate", "selected", "rejected"]
SessionStatus = Literal["running", "finished", "failed"]
WorkflowStatus = Literal["pending", "running", "success", "failed"]


@dataclass
class Project:
    id: str
    name: str
    genre: str
    status: ProjectStatus
    novel_id: str
    outline_id: str
    memory_id: str
    current_phase: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Novel:
    id: str
    project_id: str
    title: str
    total_chapters: int = 0
    latest_chapter_number: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Chapter:
    id: str
    novel_id: str
    chapter_number: int
    title: str
    content: str
    summary: str
    source_type: ChapterSourceType
    status: ChapterStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PlannedArc:
    id: str
    title: str
    stage: Literal["early", "middle", "late"]


@dataclass
class Outline:
    id: str
    project_id: str
    raw_text: str
    summary: List[str]
    major_goals: List[str]
    planned_arcs: List[PlannedArc]
    constraints: List[str]
    main_characters: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CharacterRelation:
    target_character_id: str
    relation: str
    note: str


@dataclass
class CharacterState:
    location: str = ""
    power_level: str = ""
    emotion: str = ""
    injury: str = ""


@dataclass
class CharacterProfile:
    id: str
    name: str
    aliases: List[str]
    role: str
    importance: Literal["core", "major", "minor"]
    traits: List[str]
    goals: List[str]
    relationships: List[CharacterRelation]
    state: CharacterState


@dataclass
class PlotArc:
    id: str
    title: str
    type: Literal["main", "side"]
    status: Literal["ongoing", "resolved", "paused"]
    summary: str
    current_stage: str
    open_conflicts: List[str]
    related_character_ids: List[str]


@dataclass
class StoryEvent:
    id: str
    chapter_number: int
    summary: str
    impact: str
    related_arc_ids: List[str]


@dataclass
class StyleProfile:
    narrative_pov: str
    tone_tags: List[str]
    rhythm_tags: List[str]


@dataclass
class CurrentState:
    latest_chapter_number: int
    latest_summary: str
    active_arc_ids: List[str]
    recent_conflicts: List[str]
    next_writing_focus: str


@dataclass
class ContinuityFlag:
    id: str
    type: str
    severity: Literal["low", "medium", "high"]
    message: str
    related_chapter_numbers: List[int]


@dataclass
class ProjectMemory:
    id: str
    project_id: str
    characters: List[CharacterProfile]
    world_facts: Dict[str, List[str]]
    plot_arcs: List[PlotArc]
    events: List[StoryEvent]
    style_profile: StyleProfile
    outline_context: Dict[str, List[str]]
    current_state: CurrentState
    chapter_summaries: List[str]
    continuity_flags: List[ContinuityFlag]
    version: int = 1
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StoryBranch:
    id: str
    project_id: str
    title: str
    summary: str
    core_conflict: str
    key_progressions: List[str]
    related_characters: List[str]
    style_tags: List[str]
    consistency_note: str
    risk_note: str
    status: BranchStatus = "candidate"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChapterPlan:
    id: str
    project_id: str
    branch_id: str
    chapter_number: int
    title: str
    goal: str
    conflict: str
    progression: str
    ending_hook: str
    target_words: int
    related_arc_ids: List[str]
    status: Literal["pending", "ready", "done"] = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WritingSession:
    id: str
    project_id: str
    branch_id: str
    plan_ids: List[str]
    generated_chapter_ids: List[str]
    status: SessionStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MemoryView:
    id: str
    project_id: str
    memory_id: str
    main_characters: List[Dict[str, str]]
    world_summary: List[str]
    main_plot_lines: List[str]
    style_tags: List[str]
    current_progress: str
    outline_summary: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LLMConfig:
    id: str
    provider: str
    model_name: str
    api_key_encrypted: str
    base_url: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowJob:
    id: str
    project_id: str
    workflow_type: str
    status: WorkflowStatus
    input_json: str
    result_json: str = ""
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
