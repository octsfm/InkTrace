from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from domain.types import ChapterId


@dataclass
class ChapterOutline:
    chapter_id: ChapterId
    goal: str = ""
    conflict: str = ""
    events: List[str] = field(default_factory=list)
    character_progress: str = ""
    ending_hook: str = ""
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
