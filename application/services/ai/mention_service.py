from __future__ import annotations

from datetime import UTC, datetime

from application.services.v1.chapter_service import ChapterService
from application.services.v1.writing_asset_service import WritingAssetService
from domain.entities.ai.models import (
    ChapterMention,
    MentionEntityType,
    MentionSource,
    MentionStatus,
    MentionSuggestion,
    MentionSummary,
)
from domain.repositories.ai.chapter_mention_repository import ChapterMentionRepository
from domain.repositories.workbench import CharacterRepository, ForeshadowRepository, TimelineEventRepository


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MentionService:
    def __init__(
        self,
        *,
        mention_repository: ChapterMentionRepository,
        chapter_service: ChapterService,
        writing_asset_service: WritingAssetService,
        character_repository: CharacterRepository,
        timeline_repository: TimelineEventRepository,
        foreshadow_repository: ForeshadowRepository,
    ) -> None:
        self.mention_repository = mention_repository
        self.chapter_service = chapter_service
        self.writing_asset_service = writing_asset_service
        self.character_repository = character_repository
        self.timeline_repository = timeline_repository
        self.foreshadow_repository = foreshadow_repository

    def suggest(
        self,
        *,
        work_id: str,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[MentionSuggestion]:
        normalized_limit = max(1, min(int(limit or 10), 10))
        normalized_query = str(query or "").strip()
        if not normalized_query:
            return []
        requested_types = {str(item or "").strip() for item in (entity_types or []) if str(item or "").strip()}
        suggestions: list[MentionSuggestion] = []

        def allow(entity_type: MentionEntityType) -> bool:
            return not requested_types or entity_type.value in requested_types

        if allow(MentionEntityType.CHARACTER):
            suggestions.extend(
                self._match_character_suggestions(work_id, normalized_query)
            )
        if allow(MentionEntityType.EVENT):
            suggestions.extend(
                self._match_event_suggestions(work_id, normalized_query)
            )
        if allow(MentionEntityType.FORESHADOW):
            suggestions.extend(
                self._match_foreshadow_suggestions(work_id, normalized_query)
            )
        return suggestions[:normalized_limit]

    def replace_mentions(
        self,
        *,
        chapter_id: str,
        chapter_revision: int,
        mentions: list[ChapterMention],
    ) -> list[ChapterMention]:
        chapter = self.chapter_service.chapter_repo.find_by_id(str(chapter_id or ""))
        if chapter is None:
            raise ValueError("chapter_not_found")
        if int(chapter.version or 0) != int(chapter_revision or 0):
            raise ValueError("mention_conflict")
        normalized = self._validate_mentions(chapter.content, chapter_id, chapter.work_id.value, mentions)
        return self.mention_repository.replace_by_chapter(str(chapter_id or ""), normalized)

    def get_by_chapter(self, chapter_id: str) -> list[ChapterMention]:
        return self.mention_repository.get_by_chapter(str(chapter_id or ""))

    def get_summary(self, mention_id: str) -> MentionSummary:
        mention = self.mention_repository.get_by_id(str(mention_id or ""))
        if mention is None:
            raise ValueError("mention_not_found")
        entity_name, summary_text, active = self._resolve_entity_snapshot(
            mention.work_id,
            mention.entity_type,
            mention.entity_id,
        )
        status = mention.status
        if not active:
            status = MentionStatus.INACTIVE_ENTITY
        elif entity_name and entity_name != mention.entity_name_snapshot and mention.status == MentionStatus.ACTIVE:
            status = MentionStatus.STALE
        return MentionSummary(
            mention_id=mention.mention_id,
            entity_type=mention.entity_type,
            entity_id=mention.entity_id,
            entity_name_snapshot=mention.entity_name_snapshot,
            entity_current_name=entity_name or mention.entity_name_snapshot,
            summary_text=summary_text,
            status=status,
            is_active=active and mention.is_active,
            last_updated=mention.updated_at,
        )

    def mark_entity_deleted(self, entity_type: str, entity_id: str) -> None:
        self.mention_repository.mark_entity_deleted(MentionEntityType(str(entity_type)), str(entity_id or ""))

    def _validate_mentions(
        self,
        chapter_content: str,
        chapter_id: str,
        work_id: str,
        mentions: list[ChapterMention],
    ) -> list[ChapterMention]:
        normalized: list[ChapterMention] = []
        content = str(chapter_content or "")
        ranges: list[tuple[int, int, str]] = []
        seen_triplets: set[tuple[int, int, str]] = set()
        now = _now_iso()
        for item in mentions:
            start = int(item.start_pos or 0)
            end = int(item.end_pos or 0)
            if start < 0 or end <= start or end > len(content):
                raise ValueError("invalid_mention_range")
            triplet = (start, end, str(item.entity_id or ""))
            if triplet in seen_triplets:
                raise ValueError("duplicate_mention")
            for prev_start, prev_end, _ in ranges:
                if not (end <= prev_start or start >= prev_end):
                    raise ValueError("overlap_mentions")
            mention_text = content[start:end]
            entity_name = str(item.entity_name_snapshot or "").strip()
            if (
                item.status != MentionStatus.BROKEN
                and entity_name
                and entity_name not in mention_text
                and f"@{entity_name}" not in mention_text
            ):
                raise ValueError("text_mismatch")
            if not self._entity_exists(work_id, item.entity_type, item.entity_id):
                raise ValueError("invalid_entity")
            normalized.append(
                item.model_copy(
                    update={
                        "chapter_id": str(chapter_id or ""),
                        "work_id": str(work_id or ""),
                        "status": item.status or MentionStatus.ACTIVE,
                        "is_active": bool(item.is_active if item.is_active is not None else True),
                        "created_at": item.created_at or now,
                        "updated_at": now,
                        "source": item.source or MentionSource.USER_INPUT,
                    }
                )
            )
            ranges.append((start, end, str(item.entity_id or "")))
            seen_triplets.add(triplet)
        return normalized

    def _match_character_suggestions(self, work_id: str, query: str) -> list[MentionSuggestion]:
        items = self.writing_asset_service.list_characters(work_id, query)
        prefix_matches = [item for item in items if item.name.casefold().startswith(query.casefold())]
        fallback_matches = [item for item in items if item not in prefix_matches]
        ordered = prefix_matches + fallback_matches
        return [
            MentionSuggestion(
                entity_type=MentionEntityType.CHARACTER,
                entity_id=item.id,
                entity_name=item.name,
                match_type="prefix" if item in prefix_matches else "fuzzy",
                last_used_at=item.updated_at.isoformat(),
                summary_preview=item.description[:60],
            )
            for item in ordered
        ]

    def _match_event_suggestions(self, work_id: str, query: str) -> list[MentionSuggestion]:
        items = self.writing_asset_service.list_timeline_events(work_id)
        return self._match_named_entities(
            query=query,
            items=items,
            entity_type=MentionEntityType.EVENT,
            name_getter=lambda item: item.title,
            summary_getter=lambda item: item.description,
            updated_at_getter=lambda item: item.updated_at.isoformat(),
        )

    def _match_foreshadow_suggestions(self, work_id: str, query: str) -> list[MentionSuggestion]:
        items = self.writing_asset_service.list_foreshadows(work_id, None)
        return self._match_named_entities(
            query=query,
            items=items,
            entity_type=MentionEntityType.FORESHADOW,
            name_getter=lambda item: item.title,
            summary_getter=lambda item: item.description,
            updated_at_getter=lambda item: item.updated_at.isoformat(),
        )

    def _match_named_entities(self, *, query: str, items: list[object], entity_type: MentionEntityType, name_getter, summary_getter, updated_at_getter) -> list[MentionSuggestion]:
        normalized_query = query.casefold()
        prefix_matches = [item for item in items if name_getter(item).casefold().startswith(normalized_query)]
        fuzzy_matches = [
            item for item in items
            if normalized_query in name_getter(item).casefold() and item not in prefix_matches
        ]
        ordered = prefix_matches + fuzzy_matches
        return [
            MentionSuggestion(
                entity_type=entity_type,
                entity_id=str(item.id),
                entity_name=name_getter(item),
                match_type="prefix" if item in prefix_matches else "fuzzy",
                last_used_at=updated_at_getter(item),
                summary_preview=str(summary_getter(item) or "")[:60],
            )
            for item in ordered
        ]

    def _entity_exists(self, work_id: str, entity_type: MentionEntityType, entity_id: str) -> bool:
        entity_name, _, active = self._resolve_entity_snapshot(work_id, entity_type, entity_id)
        return bool(entity_name) and active

    def _resolve_entity_snapshot(self, work_id: str, entity_type: MentionEntityType, entity_id: str) -> tuple[str, str, bool]:
        if entity_type == MentionEntityType.CHARACTER:
            item = self.character_repository.find_by_id(str(entity_id or ""))
            if item and item.work_id == str(work_id or ""):
                return item.name, item.description, True
            return "", "", False
        if entity_type == MentionEntityType.EVENT:
            item = self.timeline_repository.find_by_id(str(entity_id or ""))
            if item and item.work_id == str(work_id or ""):
                return item.title, item.description, True
            return "", "", False
        if entity_type == MentionEntityType.FORESHADOW:
            item = self.foreshadow_repository.find_by_id(str(entity_id or ""))
            if item and item.work_id == str(work_id or ""):
                return item.title, item.description, True
            return "", "", False
        return "", "", False
