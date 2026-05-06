from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class WorkOutline:
    id: str
    work_id: str
    content_text: str
    content_tree_json: Any
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass
class ChapterOutline:
    id: str
    chapter_id: str
    content_text: str
    content_tree_json: Any
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass
class TimelineEvent:
    id: str
    work_id: str
    order_index: int
    title: str
    description: str
    chapter_id: str | None
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass
class Foreshadow:
    id: str
    work_id: str
    status: str
    title: str
    description: str
    introduced_chapter_id: str | None
    resolved_chapter_id: str | None
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass
class CharacterProfile:
    id: str
    work_id: str
    name: str
    description: str
    aliases_json: str
    version: int
    created_at: datetime
    updated_at: datetime
