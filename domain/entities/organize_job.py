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
    stage: str = "idle"
    message: str = ""
    current_chapter_title: str = ""
    resumable: bool = False
    percent: int = 0
    last_error: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def mark_running(self) -> None:
        self.status = OrganizeJobStatus.RUNNING
        self.resumable = self.completed_chunks < self.total_chunks if self.total_chunks > 0 else False
        self.updated_at = datetime.now()

    def mark_error(self, message: str) -> None:
        self.status = OrganizeJobStatus.ERROR
        self.stage = "stopped"
        self.message = message
        self.resumable = True
        self.last_error = message
        self.updated_at = datetime.now()

    def mark_done(self) -> None:
        self.status = OrganizeJobStatus.DONE
        self.stage = "done"
        self.percent = 100 if self.total_chunks > 0 else 0
        self.resumable = False
        self.message = f"整理完成（{self.total_chunks}/{self.total_chunks}）" if self.total_chunks > 0 else "整理完成"
        self.last_error = ""
        self.updated_at = datetime.now()

    def reset(self, source_hash: str, total_chunks: int = 0) -> None:
        self.source_hash = source_hash
        self.total_chunks = total_chunks
        self.completed_chunks = 0
        self.checkpoint_memory = {}
        self.last_error = ""
        self.status = OrganizeJobStatus.RUNNING
        self.stage = "prepare"
        self.message = "准备整理"
        self.current_chapter_title = ""
        self.percent = 0
        self.resumable = False
        self.updated_at = datetime.now()

    def update_checkpoint(self, completed_chunks: int, total_chunks: int, memory: Dict[str, Any]) -> None:
        self.completed_chunks = completed_chunks
        self.total_chunks = total_chunks
        self.percent = int((completed_chunks / total_chunks) * 100) if total_chunks > 0 else 0
        self.checkpoint_memory = memory if isinstance(memory, dict) else {}
        self.updated_at = datetime.now()

    def apply_progress(self, payload: Dict[str, Any]) -> None:
        self.completed_chunks = int(payload.get("current") or 0)
        self.total_chunks = int(payload.get("total") or 0)
        self.percent = int(payload.get("percent") or 0)
        self.stage = str(payload.get("stage") or self.stage or "idle")
        self.message = str(payload.get("message") or self.message or "")
        self.current_chapter_title = str(payload.get("current_chapter_title") or "")
        self.resumable = bool(payload.get("resumable"))
        status = str(payload.get("status") or "")
        if status:
            try:
                self.status = OrganizeJobStatus(status)
            except Exception:
                pass
        self.updated_at = datetime.now()
