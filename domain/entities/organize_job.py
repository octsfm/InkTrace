from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from domain.types import NovelId, OrganizeJobStatus


@dataclass
class OrganizeJob:
    novel_id: NovelId
    source_hash: str = ""
    total_chunks: int = 0
    completed_chunks: int = 0
    checkpoint_memory: Dict[str, Any] = field(default_factory=dict)
    status: OrganizeJobStatus = OrganizeJobStatus.IDLE
    last_error: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def mark_running(self) -> None:
        self.status = OrganizeJobStatus.RUNNING
        self.updated_at = datetime.now()

    def mark_error(self, message: str) -> None:
        self.status = OrganizeJobStatus.ERROR
        self.last_error = message
        self.updated_at = datetime.now()

    def mark_done(self) -> None:
        self.status = OrganizeJobStatus.DONE
        self.last_error = ""
        self.updated_at = datetime.now()

    def reset(self, source_hash: str, total_chunks: int = 0) -> None:
        self.source_hash = source_hash
        self.total_chunks = total_chunks
        self.completed_chunks = 0
        self.checkpoint_memory = {}
        self.last_error = ""
        self.status = OrganizeJobStatus.RUNNING
        self.updated_at = datetime.now()

    def update_checkpoint(self, completed_chunks: int, total_chunks: int, memory: Dict[str, Any]) -> None:
        self.completed_chunks = completed_chunks
        self.total_chunks = total_chunks
        self.checkpoint_memory = memory if isinstance(memory, dict) else {}
        self.updated_at = datetime.now()

