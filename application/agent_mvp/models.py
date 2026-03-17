from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ActionType(str, Enum):
    TOOL_CALL = "TOOL_CALL"
    TERMINATE = "TERMINATE"


@dataclass
class NextAction:
    action_type: ActionType
    tool_name: Optional[str] = None
    tool_input: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class ToolResult:
    status: str
    payload: Dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    progress_made: bool = False
    error: Optional[Dict[str, Any]] = None


@dataclass
class TraceRecord:
    step: int
    layer: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskContext:
    novel_id: str
    goal: str
    target_word_count: int = 800
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory: Dict[str, Any] = field(default_factory=dict)
    context_blocks: List[Dict[str, Any]] = field(default_factory=list)
    rag_called_count: int = 0
    final_output: Optional[Dict[str, Any]] = None
    traces: List[TraceRecord] = field(default_factory=list)


@dataclass
class ExecutionContext:
    timeout_seconds: int = 20
    max_steps: int = 3
    max_no_progress_steps: int = 2
    max_retries_per_action: int = 2
    started_at: datetime = field(default_factory=datetime.now)
    current_step: int = 0
    no_progress_streak: int = 0

    @property
    def step_count(self) -> int:
        return self.current_step

    @property
    def deadline_at(self) -> datetime:
        return self.started_at + timedelta(seconds=self.timeout_seconds)

    def deadline_exceeded(self) -> bool:
        return datetime.now() >= self.deadline_at

    def step_exceeded(self) -> bool:
        return self.current_step >= self.max_steps

    def can_execute(self) -> bool:
        return not self.deadline_exceeded() and not self.step_exceeded()

    def record_progress(self, progress_made: bool) -> None:
        if progress_made:
            self.no_progress_streak = 0
        else:
            self.no_progress_streak += 1

    def no_progress_exceeded(self) -> bool:
        return self.no_progress_streak >= self.max_no_progress_steps

    def next_step(self) -> None:
        self.current_step += 1
