from __future__ import annotations

from domain.entities.ai.models import ContextPackSnapshot, WritingTask
from domain.services.ai.writer import WriterPort


class WriterService:
    def __init__(self, writer: WriterPort) -> None:
        self._writer = writer

    def generate_candidate_text(self, *, context_pack: ContextPackSnapshot, writing_task: WritingTask) -> dict[str, str]:
        return self._writer.generate_candidate_text(context_pack=context_pack, writing_task=writing_task)
