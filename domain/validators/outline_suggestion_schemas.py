from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _OutlineOutputBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_content_text: str
    proposed_content_tree_json: Any = Field(default_factory=list)
    diff_summary: list[str] = Field(default_factory=list)

    @field_validator("proposed_content_text")
    @classmethod
    def proposed_text_must_not_be_empty(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("proposed_content_text_empty")
        return normalized


class OutlinePolishOutputModel(_OutlineOutputBase):
    polish_notes: list[str] = Field(default_factory=list)


class OutlineExpandOutputModel(_OutlineOutputBase):
    expansion_points: list[str] = Field(default_factory=list)
    expand_focus: str | None = None


class SceneBeatOutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beat_no: int
    description: str
    characters_involved: list[str] = Field(default_factory=list)
    estimated_words: int = 0


class ChapterOutlineDetailOutputModel(_OutlineOutputBase):
    chapter_goal: str
    scene_beats: list[SceneBeatOutputModel] = Field(default_factory=list)
    conflict_points: list[str] = Field(default_factory=list)
    ending_hook: str = ""


class WritingTaskSuggestionOutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_title: str = Field(min_length=1, max_length=200)
    writing_goal: str = Field(min_length=1, max_length=1000)
    must_include: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=20)
    must_not_include: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=20)
    target_word_count: int = Field(default=0, ge=0, le=100000)
    tone_guidance: str = Field(default="", max_length=500)
    required_beats: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=30)
    context_summary: str = Field(default="", max_length=1000)

    @field_validator("writing_goal")
    @classmethod
    def writing_goal_must_not_be_empty(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("writing_goal_empty")
        return normalized
