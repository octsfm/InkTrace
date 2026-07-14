from __future__ import annotations

from abc import ABC, abstractmethod


class RewriterPort(ABC):
    @abstractmethod
    def rewrite(
        self,
        *,
        work_id: str,
        chapter_id: str,
        source_content: str,
        instruction_summary: str,
        source_context_pack_id: str,
    ) -> dict[str, object]:
        raise NotImplementedError

