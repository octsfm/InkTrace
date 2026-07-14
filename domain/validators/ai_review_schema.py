from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewIssueOutputModel(_StrictModel):
    issue_id: str = Field(min_length=1)
    severity: str = "medium"
    category: str = "consistency"
    message: str = Field(min_length=1)
    suggestion: str = ""
    source_ref: str = ""


class AIReviewOutputModel(_StrictModel):
    summary: str = Field(min_length=1)
    issues: list[ReviewIssueOutputModel] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    consistency_notes: list[str] = Field(default_factory=list)
    style_notes: list[str] = Field(default_factory=list)
    logic_notes: list[str] = Field(default_factory=list)

