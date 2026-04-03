from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class ChapterContinuationMemory:
    id: str
    chapter_id: str
    chapter_number: int
    chapter_title: str
    scene_summary: str = ""
    scene_state: Dict[str, str] = field(default_factory=dict)
    protagonist_state: Dict[str, str] = field(default_factory=dict)
    active_characters: List[Dict[str, str]] = field(default_factory=list)
    active_conflicts: List[str] = field(default_factory=list)
    immediate_threads: List[str] = field(default_factory=list)
    long_term_threads: List[str] = field(default_factory=list)
    recent_reveals: List[str] = field(default_factory=list)
    must_continue_points: List[str] = field(default_factory=list)
    forbidden_jumps: List[str] = field(default_factory=list)
    tone_and_pacing: Dict[str, str] = field(default_factory=dict)
    last_hook: str = ""
    active_arc_ids: List[str] = field(default_factory=list)
    target_arc_id: str = ""
    target_arc_stage: str = ""
    arc_must_continue_points: List[str] = field(default_factory=list)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
