from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class ChapterAnalysisMemory:
    id: str
    chapter_id: str
    chapter_number: int
    chapter_title: str
    summary: str = ""
    events: List[str] = field(default_factory=list)
    plot_role: str = ""
    conflict: str = ""
    foreshadowing: List[str] = field(default_factory=list)
    hook: str = ""
    problems: List[str] = field(default_factory=list)
    primary_arc_id: str = ""
    secondary_arc_ids: List[str] = field(default_factory=list)
    arc_push_summary: str = ""
    arc_stage_impact: str = ""
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
