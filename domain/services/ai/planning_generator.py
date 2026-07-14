from __future__ import annotations

from abc import ABC, abstractmethod


class PlanningGeneratorPort(ABC):
    @abstractmethod
    def generate_direction_options(
        self,
        *,
        work_id: str,
        chapter_id: str,
        chapter_title: str,
        user_instruction: str,
        context_pack: object,
    ) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def generate_chapter_plan(
        self,
        *,
        work_id: str,
        chapter_id: str,
        selected_option: dict[str, object],
        context_pack: object,
    ) -> dict[str, object]:
        raise NotImplementedError

