from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CandidateRewriteOutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rewritten_text: str = Field(min_length=1)
    revision_summary: str = ""
    addressed_issues: list[str] = Field(default_factory=list)

