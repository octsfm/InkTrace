from __future__ import annotations

from pathlib import Path

from domain.entities.ai.models import LLMCallLog
from domain.repositories.ai.llm_call_log_repository import LLMCallLogRepository
from infrastructure.database.session import get_database_path


class FileLLMCallLogStore(LLMCallLogRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("llm_call_logs.jsonl")

    def append(self, entry: LLMCallLog) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._file_path.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json())
            handle.write("\n")
