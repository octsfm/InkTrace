from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from domain.types import ChapterId


@dataclass
class ChapterDetailOutlineScene:
    scene_no: int = 0
    goal: str = ""
    conflict: str = ""
    turning_point: str = ""
    hook: str = ""
    foreshadow: str = ""
    target_words: int = 0


@dataclass
class ChapterDetailOutline:
    chapter_id: ChapterId
    scenes: List[ChapterDetailOutlineScene] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
