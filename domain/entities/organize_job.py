from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from domain.types import NovelId, OrganizeJobStatus


@dataclass(init=False)
class OrganizeJob:
    novel_id: NovelId
    source_hash: str = ""
    total_chapters: int = 0
    completed_chapters: int = 0
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

    def __init__(
        self,
        novel_id: NovelId,
        *,
        source_hash: str = "",
        total_chapters: int = 0,
        completed_chapters: int = 0,
        total_chunks: int | None = None,
        completed_chunks: int | None = None,
        checkpoint_memory: Dict[str, Any] | None = None,
        status: OrganizeJobStatus = OrganizeJobStatus.IDLE,
        stage: str = "idle",
        message: str = "",
        current_chapter_title: str = "",
        resumable: bool = False,
        percent: int = 0,
        last_error: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        if total_chunks is not None:
            total_chapters = int(total_chunks or 0)
        if completed_chunks is not None:
            completed_chapters = int(completed_chunks or 0)

        self.novel_id = novel_id
        self.source_hash = source_hash
        self.total_chapters = int(total_chapters or 0)
        self.completed_chapters = int(completed_chapters or 0)
        self.checkpoint_memory = checkpoint_memory if isinstance(checkpoint_memory, dict) else {}
        self.status = status
        self.stage = stage
        self.message = message
        self.current_chapter_title = current_chapter_title
        self.resumable = bool(resumable)
        self.percent = int(percent or 0)
        self.last_error = last_error
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def mark_running(self) -> None:
        self.status = OrganizeJobStatus.RUNNING
        if self.stage in {"idle", "paused", "pause_requested", "resume_requested", "cancelling", "cancelled", "error"}:
            self.stage = "running"
        self.resumable = self.completed_chapters < self.total_chapters if self.total_chapters > 0 else False
        self.updated_at = datetime.now()

    def mark_error(self, message: str) -> None:
        self.status = OrganizeJobStatus.ERROR
        self.stage = "error"
        self.message = message
        self.resumable = self.completed_chapters < self.total_chapters if self.total_chapters > 0 else False
        self.last_error = message
        self.updated_at = datetime.now()

    def mark_pause_requested(self) -> None:
        self.status = OrganizeJobStatus.PAUSE_REQUESTED
        self.stage = "pause_requested"
        self.message = self.message or "已请求暂停整理"
        self.resumable = True
        self.updated_at = datetime.now()

    def mark_paused(self, message: str = "整理任务已暂停，可继续整理") -> None:
        self.status = OrganizeJobStatus.PAUSED
        self.stage = "paused"
        self.message = message
        self.resumable = True
        self.updated_at = datetime.now()

    def mark_resume_requested(self) -> None:
        self.status = OrganizeJobStatus.RESUME_REQUESTED
        self.stage = "resume_requested"
        self.message = "已请求继续整理"
        self.resumable = True
        self.updated_at = datetime.now()

    def mark_cancelling(self) -> None:
        self.status = OrganizeJobStatus.CANCELLING
        self.stage = "cancelling"
        self.message = "正在取消整理任务"
        self.resumable = False
        self.updated_at = datetime.now()

    def mark_cancelled(self, message: str = "整理任务已取消") -> None:
        self.status = OrganizeJobStatus.CANCELLED
        self.stage = "cancelled"
        self.message = message
        self.resumable = False
        self.updated_at = datetime.now()

    def mark_done(self) -> None:
        self.status = OrganizeJobStatus.DONE
        self.stage = "done"
        self.percent = 100 if self.total_chapters > 0 else 0
        self.resumable = False
        self.message = f"整理完成（{self.total_chapters}/{self.total_chapters}）" if self.total_chapters > 0 else "整理完成"
        self.last_error = ""
        self.updated_at = datetime.now()

    def reset(self, source_hash: str, total_chapters: int = 0, total_chunks: int | None = None) -> None:
        if total_chunks is not None:
            total_chapters = int(total_chunks or 0)
        self.source_hash = source_hash
        self.total_chapters = total_chapters
        self.completed_chapters = 0
        self.checkpoint_memory = {}
        self.last_error = ""
        self.status = OrganizeJobStatus.RUNNING
        self.stage = "prepare"
        self.message = "准备整理"
        self.current_chapter_title = ""
        self.percent = 0
        self.resumable = False
        self.updated_at = datetime.now()

    def update_checkpoint(self, completed_chapters: int, total_chapters: int, memory: Dict[str, Any], completed_chunks: int | None = None, total_chunks: int | None = None) -> None:
        if completed_chunks is not None:
            completed_chapters = int(completed_chunks or 0)
        if total_chunks is not None:
            total_chapters = int(total_chunks or 0)
        self.completed_chapters = completed_chapters
        self.total_chapters = total_chapters
        self.percent = int((completed_chapters / total_chapters) * 100) if total_chapters > 0 else 0
        self.checkpoint_memory = memory if isinstance(memory, dict) else {}
        self.updated_at = datetime.now()

    def apply_progress(self, payload: Dict[str, Any]) -> None:
        self.completed_chapters = int(payload.get("current") or 0)
        self.total_chapters = int(payload.get("total") or 0)
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

    @property
    def total_chunks(self) -> int:
        return self.total_chapters

    @total_chunks.setter
    def total_chunks(self, value: int) -> None:
        self.total_chapters = int(value or 0)

    @property
    def completed_chunks(self) -> int:
        return self.completed_chapters

    @completed_chunks.setter
    def completed_chunks(self, value: int) -> None:
        self.completed_chapters = int(value or 0)
