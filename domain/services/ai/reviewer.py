from __future__ import annotations

from abc import ABC, abstractmethod


class ReviewerPort(ABC):
    @abstractmethod
    def review(self, *, review_context: dict[str, object], review_mode: str, user_instruction: str = "") -> dict[str, object]:
        raise NotImplementedError
