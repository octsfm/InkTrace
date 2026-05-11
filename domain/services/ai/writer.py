from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import ContextPackSnapshot, WritingTask


class WriterPort(ABC):
    @abstractmethod
    def generate_candidate_text(self, *, context_pack: ContextPackSnapshot, writing_task: WritingTask) -> dict[str, str]:
        raise NotImplementedError
