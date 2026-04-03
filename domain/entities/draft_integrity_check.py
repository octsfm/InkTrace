from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class DraftIntegrityCheck:
    id: str
    chapter_id: str
    project_id: str
    structural_draft_id: str
    detemplated_draft_id: str
    event_integrity_ok: bool = True
    motivation_integrity_ok: bool = True
    foreshadowing_integrity_ok: bool = True
    hook_integrity_ok: bool = True
    continuity_ok: bool = True
    arc_consistency_ok: bool = True
    title_alignment_ok: bool = True
    progression_integrity_ok: bool = True
    risk_notes: List[str] = field(default_factory=list)
    issue_list: List[Dict[str, Any]] = field(default_factory=list)
    revision_suggestion: str = ""
    revision_attempted: bool = False
    revision_succeeded: bool = False
    created_at: datetime = field(default_factory=datetime.now)
