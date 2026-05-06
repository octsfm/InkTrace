from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from application.services.v1.content_tree_schema import validate_content_tree_json
from domain.entities.writing_assets import CharacterProfile, ChapterOutline, Foreshadow, TimelineEvent, WorkOutline
from domain.repositories.workbench import (
    CharacterRepository,
    ChapterOutlineRepository,
    ChapterRepository,
    ForeshadowRepository,
    TimelineEventRepository,
    WorkOutlineRepository,
    WorkRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_version(current_version: int, expected_version: int | None, force_override: bool) -> None:
    if force_override:
        return
    if expected_version is not None and int(expected_version) != int(current_version):
        raise ValueError("asset_version_conflict")


class WritingAssetService:
    def __init__(
        self,
        *,
        work_repo: WorkRepository,
        chapter_repo: ChapterRepository,
        work_outline_repo: WorkOutlineRepository,
        chapter_outline_repo: ChapterOutlineRepository,
        timeline_event_repo: TimelineEventRepository | None = None,
        foreshadow_repo: ForeshadowRepository | None = None,
        character_repo: CharacterRepository | None = None,
    ) -> None:
        self.work_repo = work_repo
        self.chapter_repo = chapter_repo
        self.work_outline_repo = work_outline_repo
        self.chapter_outline_repo = chapter_outline_repo
        self.timeline_event_repo = timeline_event_repo
        self.foreshadow_repo = foreshadow_repo
        self.character_repo = character_repo

    def get_work_outline(self, work_id: str) -> WorkOutline:
        work = self.work_repo.find_by_id(str(work_id))
        if work is None:
            raise ValueError("work_not_found")
        existing = self.work_outline_repo.find_by_work(str(work_id))
        if existing is not None:
            return existing
        now = _now()
        return WorkOutline(
            id=str(uuid4()),
            work_id=str(work_id),
            content_text="",
            content_tree_json=[],
            version=1,
            created_at=now,
            updated_at=now,
        )

    def save_work_outline(
        self,
        work_id: str,
        *,
        content_text: str,
        content_tree_json=None,
        expected_version: int | None = None,
        force_override: bool = False,
    ) -> WorkOutline:
        current = self.get_work_outline(work_id)
        _assert_version(current.version, expected_version, force_override)
        normalized_tree = validate_content_tree_json(content_tree_json)
        now = _now()
        next_outline = WorkOutline(
            id=current.id,
            work_id=str(work_id),
            content_text=str(content_text or ""),
            content_tree_json=[] if normalized_tree is None else normalized_tree,
            version=current.version + 1 if self.work_outline_repo.find_by_work(str(work_id)) else 1,
            created_at=current.created_at,
            updated_at=now,
        )
        self.work_outline_repo.save(next_outline)
        return next_outline

    def get_chapter_outline(self, chapter_id: str) -> ChapterOutline:
        chapter = self.chapter_repo.find_by_id(str(chapter_id))
        if chapter is None:
            raise ValueError("chapter_not_found")
        existing = self.chapter_outline_repo.find_by_chapter(str(chapter_id))
        if existing is not None:
            return existing
        now = _now()
        return ChapterOutline(
            id=str(uuid4()),
            chapter_id=str(chapter_id),
            content_text="",
            content_tree_json=[],
            version=1,
            created_at=now,
            updated_at=now,
        )

    def save_chapter_outline(
        self,
        chapter_id: str,
        *,
        content_text: str,
        content_tree_json=None,
        expected_version: int | None = None,
        force_override: bool = False,
    ) -> ChapterOutline:
        current = self.get_chapter_outline(chapter_id)
        _assert_version(current.version, expected_version, force_override)
        normalized_tree = validate_content_tree_json(content_tree_json)
        now = _now()
        next_outline = ChapterOutline(
            id=current.id,
            chapter_id=str(chapter_id),
            content_text=str(content_text or ""),
            content_tree_json=[] if normalized_tree is None else normalized_tree,
            version=current.version + 1 if self.chapter_outline_repo.find_by_chapter(str(chapter_id)) else 1,
            created_at=current.created_at,
            updated_at=now,
        )
        self.chapter_outline_repo.save(next_outline)
        return next_outline

    def _require_timeline_repo(self) -> TimelineEventRepository:
        if self.timeline_event_repo is None:
            raise ValueError("invalid_input")
        return self.timeline_event_repo

    def _ensure_work_exists(self, work_id: str) -> None:
        if self.work_repo.find_by_id(str(work_id)) is None:
            raise ValueError("work_not_found")

    def _ensure_chapter_ref(self, chapter_id: str | None) -> str | None:
        if not chapter_id:
            return None
        if self.chapter_repo.find_by_id(str(chapter_id)) is None:
            raise ValueError("invalid_input")
        return str(chapter_id)

    def list_timeline_events(self, work_id: str) -> list[TimelineEvent]:
        self._ensure_work_exists(work_id)
        return self._require_timeline_repo().list_by_work(str(work_id))

    def create_timeline_event(self, work_id: str, payload: dict) -> TimelineEvent:
        self._ensure_work_exists(work_id)
        repo = self._require_timeline_repo()
        now = _now()
        order_index = len(repo.list_by_work(str(work_id))) + 1
        event = TimelineEvent(
            id=str(uuid4()),
            work_id=str(work_id),
            order_index=order_index,
            title=str(payload.get("title") or ""),
            description=str(payload.get("description") or ""),
            chapter_id=self._ensure_chapter_ref(payload.get("chapter_id")),
            version=1,
            created_at=now,
            updated_at=now,
        )
        repo.save(event)
        return event

    def update_timeline_event(
        self,
        event_id: str,
        payload: dict,
        expected_version: int | None,
        force_override: bool = False,
    ) -> TimelineEvent:
        repo = self._require_timeline_repo()
        current = repo.find_by_id(str(event_id))
        if current is None:
            raise ValueError("timeline_event_not_found")
        _assert_version(current.version, expected_version, force_override)
        chapter_id = current.chapter_id
        if "chapter_id" in payload:
            chapter_id = self._ensure_chapter_ref(payload.get("chapter_id"))
        updated = TimelineEvent(
            id=current.id,
            work_id=current.work_id,
            order_index=current.order_index,
            title=str(payload.get("title", current.title) or ""),
            description=str(payload.get("description", current.description) or ""),
            chapter_id=chapter_id,
            version=current.version + 1,
            created_at=current.created_at,
            updated_at=_now(),
        )
        repo.save(updated)
        return updated

    def delete_timeline_event(self, event_id: str) -> None:
        repo = self._require_timeline_repo()
        if repo.find_by_id(str(event_id)) is None:
            raise ValueError("timeline_event_not_found")
        repo.delete(str(event_id))

    def reorder_timeline_events(self, work_id: str, mappings: list[dict]) -> list[TimelineEvent]:
        self._ensure_work_exists(work_id)
        repo = self._require_timeline_repo()
        current_events = repo.list_by_work(str(work_id))
        current_ids = {event.id for event in current_events}
        items = mappings if isinstance(mappings, list) else []
        item_ids = [str(item.get("id") or "") for item in items if isinstance(item, dict)]
        order_indexes = [int(item.get("order_index") or 0) for item in items if isinstance(item, dict)]
        if len(items) != len(current_events):
            raise ValueError("invalid_input")
        if len(item_ids) != len(items) or len(set(item_ids)) != len(item_ids):
            raise ValueError("invalid_input")
        if set(item_ids) != current_ids:
            raise ValueError("invalid_input")
        if sorted(order_indexes) != list(range(1, len(current_events) + 1)):
            raise ValueError("invalid_input")
        return repo.reorder(str(work_id), items)

    def _require_foreshadow_repo(self) -> ForeshadowRepository:
        if self.foreshadow_repo is None:
            raise ValueError("invalid_input")
        return self.foreshadow_repo

    def _normalize_foreshadow_status(self, status: str | None, *, default: str = "open") -> str:
        next_status = str(status or default)
        if next_status not in {"open", "resolved"}:
            raise ValueError("invalid_input")
        return next_status

    def list_foreshadows(self, work_id: str, status: str | None = "open") -> list[Foreshadow]:
        self._ensure_work_exists(work_id)
        normalized_status = None if status is None else self._normalize_foreshadow_status(status)
        return self._require_foreshadow_repo().list_by_work(str(work_id), normalized_status)

    def create_foreshadow(self, work_id: str, payload: dict) -> Foreshadow:
        self._ensure_work_exists(work_id)
        now = _now()
        item = Foreshadow(
            id=str(uuid4()),
            work_id=str(work_id),
            status=self._normalize_foreshadow_status(payload.get("status")),
            title=str(payload.get("title") or ""),
            description=str(payload.get("description") or ""),
            introduced_chapter_id=self._ensure_chapter_ref(payload.get("introduced_chapter_id")),
            resolved_chapter_id=self._ensure_chapter_ref(payload.get("resolved_chapter_id")),
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._require_foreshadow_repo().save(item)
        return item

    def update_foreshadow(
        self,
        foreshadow_id: str,
        payload: dict,
        expected_version: int | None,
        force_override: bool = False,
    ) -> Foreshadow:
        repo = self._require_foreshadow_repo()
        current = repo.find_by_id(str(foreshadow_id))
        if current is None:
            raise ValueError("foreshadow_not_found")
        _assert_version(current.version, expected_version, force_override)
        updated = Foreshadow(
            id=current.id,
            work_id=current.work_id,
            status=self._normalize_foreshadow_status(payload.get("status", current.status)),
            title=str(payload.get("title", current.title) or ""),
            description=str(payload.get("description", current.description) or ""),
            introduced_chapter_id=(
                self._ensure_chapter_ref(payload.get("introduced_chapter_id"))
                if "introduced_chapter_id" in payload else current.introduced_chapter_id
            ),
            resolved_chapter_id=(
                self._ensure_chapter_ref(payload.get("resolved_chapter_id"))
                if "resolved_chapter_id" in payload else current.resolved_chapter_id
            ),
            version=current.version + 1,
            created_at=current.created_at,
            updated_at=_now(),
        )
        repo.save(updated)
        return updated

    def delete_foreshadow(self, foreshadow_id: str) -> None:
        repo = self._require_foreshadow_repo()
        if repo.find_by_id(str(foreshadow_id)) is None:
            raise ValueError("foreshadow_not_found")
        repo.delete(str(foreshadow_id))

    def _require_character_repo(self) -> CharacterRepository:
        if self.character_repo is None:
            raise ValueError("invalid_input")
        return self.character_repo

    def _normalize_aliases_json(self, aliases) -> str:
        values = aliases
        if values is None:
            values = []
        if isinstance(values, str):
            try:
                values = json.loads(values or "[]")
            except json.JSONDecodeError:
                values = []
        if not isinstance(values, list):
            values = []
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            alias = str(item or "").strip()
            if not alias:
                continue
            key = alias.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(alias)
        return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))

    def list_characters(self, work_id: str, keyword: str = "") -> list[CharacterProfile]:
        self._ensure_work_exists(work_id)
        return self._require_character_repo().list_by_work(str(work_id), str(keyword or ""))

    def create_character(self, work_id: str, payload: dict) -> CharacterProfile:
        self._ensure_work_exists(work_id)
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("invalid_input")
        now = _now()
        character = CharacterProfile(
            id=str(uuid4()),
            work_id=str(work_id),
            name=name,
            description=str(payload.get("description") or ""),
            aliases_json=self._normalize_aliases_json(payload.get("aliases", payload.get("aliases_json"))),
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._require_character_repo().save(character)
        return character

    def update_character(
        self,
        character_id: str,
        payload: dict,
        expected_version: int | None,
        force_override: bool = False,
    ) -> CharacterProfile:
        repo = self._require_character_repo()
        current = repo.find_by_id(str(character_id))
        if current is None:
            raise ValueError("character_not_found")
        _assert_version(current.version, expected_version, force_override)
        name = str(payload.get("name", current.name) or "").strip()
        if not name:
            raise ValueError("invalid_input")
        aliases_json = current.aliases_json
        if "aliases" in payload or "aliases_json" in payload:
            aliases_json = self._normalize_aliases_json(payload.get("aliases", payload.get("aliases_json")))
        updated = CharacterProfile(
            id=current.id,
            work_id=current.work_id,
            name=name,
            description=str(payload.get("description", current.description) or ""),
            aliases_json=aliases_json,
            version=current.version + 1,
            created_at=current.created_at,
            updated_at=_now(),
        )
        repo.save(updated)
        return updated

    def delete_character(self, character_id: str) -> None:
        repo = self._require_character_repo()
        if repo.find_by_id(str(character_id)) is None:
            raise ValueError("character_not_found")
        repo.delete(str(character_id))

