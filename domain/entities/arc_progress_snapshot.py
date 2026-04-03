from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class ArcProgressSnapshot:
    snapshot_id: str
    arc_id: str
    chapter_id: str
    chapter_number: int
    stage_before: str
    stage_after: str
    progress_summary: str = ""
    change_reason: str = ""
    new_conflicts: List[str] = field(default_factory=list)
    new_payoffs: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
