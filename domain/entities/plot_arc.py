from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class PlotArc:
    arc_id: str
    project_id: str
    title: str
    arc_type: str = "supporting_arc"
    priority: str = "minor"
    status: str = "active"
    goal: str = ""
    core_conflict: str = ""
    stakes: str = ""
    start_chapter_number: int = 0
    end_chapter_number: int = 0
    current_stage: str = "setup"
    stage_reason: str = ""
    stage_confidence: float = 0.6
    key_turning_points: List[str] = field(default_factory=list)
    must_resolve_points: List[str] = field(default_factory=list)
    related_characters: List[str] = field(default_factory=list)
    related_items: List[str] = field(default_factory=list)
    related_world_rules: List[str] = field(default_factory=list)
    covered_chapter_ids: List[str] = field(default_factory=list)
    latest_progress_summary: str = ""
    latest_result: str = ""
    next_push_suggestion: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
