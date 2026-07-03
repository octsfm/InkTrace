from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import ChapterMention, MentionEntityType


class ChapterMentionRepository(ABC):
    @abstractmethod
    def replace_by_chapter(self, chapter_id: str, mentions: list[ChapterMention]) -> list[ChapterMention]:
        raise NotImplementedError

    @abstractmethod
    def get_by_chapter(self, chapter_id: str) -> list[ChapterMention]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, mention_id: str) -> ChapterMention | None:
        raise NotImplementedError

    @abstractmethod
    def mark_entity_deleted(self, entity_type: MentionEntityType, entity_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_by_entity(self, entity_type: MentionEntityType, entity_id: str) -> list[ChapterMention]:
        raise NotImplementedError
