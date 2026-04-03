"""
API输入输出Schema（FastAPI层）。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field
from domain.constants.story_constants import (
    DEFAULT_BRANCH_COUNT,
    DEFAULT_GENERATE_CHAPTER_COUNT,
    DEFAULT_TARGET_WORDS_PER_CHAPTER,
)


class ImportProjectRequest(BaseModel):
    project_name: str = Field(..., min_length=1)
    genre: str = Field(default="")
    novel_file_path: str = Field(..., min_length=1)
    outline_file_path: Optional[str] = ""
    auto_organize: bool = True


class OrganizeProjectRequest(BaseModel):
    mode: str = "chapter_first"
    rebuild_memory: bool = True


class GenerateBranchesRequest(BaseModel):
    direction_hint: str = ""
    branch_count: int = Field(default=DEFAULT_BRANCH_COUNT, ge=3, le=4)


class CreateChapterPlanRequest(BaseModel):
    branch_id: str
    chapter_count: int = Field(default=DEFAULT_GENERATE_CHAPTER_COUNT, ge=1, le=10)
    target_words_per_chapter: int = Field(default=DEFAULT_TARGET_WORDS_PER_CHAPTER, ge=500, le=10000)


class ExecuteWritingRequest(BaseModel):
    plan_ids: List[str]
    auto_commit: bool = True


class RefreshMemoryRequest(BaseModel):
    from_chapter_number: int = Field(..., ge=1)
    to_chapter_number: int = Field(..., ge=1)
