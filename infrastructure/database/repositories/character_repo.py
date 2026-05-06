from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from domain.entities.writing_assets import CharacterProfile
from infrastructure.database.session import get_connection, initialize_database


def normalize_aliases_json(value) -> str:
    if value is None:
        return "[]"
    aliases = value
    if isinstance(value, str):
        try:
            aliases = json.loads(value or "[]")
        except json.JSONDecodeError:
            aliases = []
    if not isinstance(aliases, list):
        aliases = []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in aliases:
        alias = str(item or "").strip()
        if not alias:
            continue
        key = alias.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(alias)
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def _aliases_from_json(value: str) -> list[str]:
    try:
        aliases = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return [str(item) for item in aliases] if isinstance(aliases, list) else []


class CharacterRepo:
    def __init__(self) -> None:
        initialize_database()

    def list_by_work(self, work_id: str, keyword: str = "") -> list[CharacterProfile]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, work_id, name, description, aliases_json, version, created_at, updated_at
                FROM characters
                WHERE work_id = ?
                ORDER BY updated_at DESC, id ASC
                """,
                (str(work_id),),
            ).fetchall()
        items = [self._row_to_entity(row) for row in rows]
        query = str(keyword or "").strip().casefold()
        if not query:
            return items
        return [
            item for item in items
            if query in item.name.casefold()
            or any(query in alias.casefold() for alias in _aliases_from_json(item.aliases_json))
        ]

    def find_by_id(self, character_id: str) -> Optional[CharacterProfile]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, work_id, name, description, aliases_json, version, created_at, updated_at
                FROM characters
                WHERE id = ?
                """,
                (str(character_id),),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, character: CharacterProfile) -> None:
        aliases_json = normalize_aliases_json(character.aliases_json)
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO characters (
                    id, work_id, name, description, aliases_json, version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    work_id = excluded.work_id,
                    name = excluded.name,
                    description = excluded.description,
                    aliases_json = excluded.aliases_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    str(character.id),
                    str(character.work_id),
                    str(character.name or ""),
                    str(character.description or ""),
                    aliases_json,
                    int(character.version or 1),
                    character.created_at.isoformat(),
                    character.updated_at.isoformat(),
                ),
            )

    def delete(self, character_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM characters WHERE id = ?", (str(character_id),))

    def delete_by_work(self, work_id: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM characters WHERE work_id = ?", (str(work_id),))

    @staticmethod
    def _row_to_entity(row) -> CharacterProfile:
        return CharacterProfile(
            id=str(row["id"]),
            work_id=str(row["work_id"]),
            name=str(row["name"]),
            description=str(row["description"]),
            aliases_json=normalize_aliases_json(row["aliases_json"]),
            version=int(row["version"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
