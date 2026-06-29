from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from domain.entities.ai.models import StyleProfile
from domain.repositories.ai.style_profile_repository import StyleProfileRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class SQLiteStyleProfileRepository(StyleProfileRepository):
    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def save(self, profile: StyleProfile) -> StyleProfile:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO style_profiles (
                    profile_id, work_id, source_type, source_ref, source_text_hash, source_text_length,
                    confidence, low_confidence_reason, avg_sentence_length, sentence_length_variance,
                    short_sentence_ratio, long_sentence_ratio, compound_sentence_ratio, avg_paragraph_length,
                    paragraph_length_variance, dialogue_ratio, psychological_ratio, action_ratio,
                    description_ratio, narrative_perspective, tense_preference, style_summary,
                    style_tags_json, version, status, created_at, updated_at, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    work_id = excluded.work_id,
                    source_type = excluded.source_type,
                    source_ref = excluded.source_ref,
                    source_text_hash = excluded.source_text_hash,
                    source_text_length = excluded.source_text_length,
                    confidence = excluded.confidence,
                    low_confidence_reason = excluded.low_confidence_reason,
                    avg_sentence_length = excluded.avg_sentence_length,
                    sentence_length_variance = excluded.sentence_length_variance,
                    short_sentence_ratio = excluded.short_sentence_ratio,
                    long_sentence_ratio = excluded.long_sentence_ratio,
                    compound_sentence_ratio = excluded.compound_sentence_ratio,
                    avg_paragraph_length = excluded.avg_paragraph_length,
                    paragraph_length_variance = excluded.paragraph_length_variance,
                    dialogue_ratio = excluded.dialogue_ratio,
                    psychological_ratio = excluded.psychological_ratio,
                    action_ratio = excluded.action_ratio,
                    description_ratio = excluded.description_ratio,
                    narrative_perspective = excluded.narrative_perspective,
                    tense_preference = excluded.tense_preference,
                    style_summary = excluded.style_summary,
                    style_tags_json = excluded.style_tags_json,
                    version = excluded.version,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    confirmed_at = excluded.confirmed_at
                """,
                self._params(profile),
            )
            conn.commit()
            return profile
        finally:
            conn.close()

    def update(self, profile: StyleProfile) -> StyleProfile:
        return self.save(profile)

    def get_by_id(self, profile_id: str) -> StyleProfile | None:
        items = self._query("SELECT * FROM style_profiles WHERE profile_id = ?", (profile_id,))
        return items[0] if items else None

    def get_active(self, work_id: str) -> StyleProfile | None:
        items = self._query(
            """
            SELECT * FROM style_profiles
            WHERE work_id = ? AND status = 'active'
            ORDER BY version DESC, created_at DESC
            LIMIT 1
            """,
            (work_id,),
        )
        return items[0] if items else None

    def get_history(self, work_id: str) -> list[StyleProfile]:
        return self._query(
            "SELECT * FROM style_profiles WHERE work_id = ? ORDER BY version DESC, created_at DESC",
            (work_id,),
        )

    def delete(self, profile_id: str) -> None:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute("DELETE FROM style_profiles WHERE profile_id = ?", (profile_id,))
            conn.commit()
        finally:
            conn.close()

    def _query(self, sql: str, params: tuple[object, ...]) -> list[StyleProfile]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_profile(row) for row in rows]
        finally:
            conn.close()

    def _row_to_profile(self, row: sqlite3.Row | dict[str, object]) -> StyleProfile:
        if isinstance(row, dict):
            payload = dict(row)
        else:
            payload = {
                "profile_id": row["profile_id"],
                "work_id": row["work_id"],
                "source_type": row["source_type"],
                "source_ref": row["source_ref"],
                "source_text_hash": row["source_text_hash"],
                "source_text_length": int(row["source_text_length"] or 0),
                "confidence": float(row["confidence"] or 0.0),
                "low_confidence_reason": row["low_confidence_reason"],
                "avg_sentence_length": float(row["avg_sentence_length"] or 0.0),
                "sentence_length_variance": float(row["sentence_length_variance"] or 0.0),
                "short_sentence_ratio": float(row["short_sentence_ratio"] or 0.0),
                "long_sentence_ratio": float(row["long_sentence_ratio"] or 0.0),
                "compound_sentence_ratio": float(row["compound_sentence_ratio"] or 0.0),
                "avg_paragraph_length": float(row["avg_paragraph_length"] or 0.0),
                "paragraph_length_variance": float(row["paragraph_length_variance"] or 0.0),
                "dialogue_ratio": float(row["dialogue_ratio"] or 0.0),
                "psychological_ratio": float(row["psychological_ratio"] or 0.0),
                "action_ratio": float(row["action_ratio"] or 0.0),
                "description_ratio": float(row["description_ratio"] or 0.0),
                "narrative_perspective": row["narrative_perspective"],
                "tense_preference": row["tense_preference"],
                "style_summary": row["style_summary"],
                "style_tags": json.loads(str(row["style_tags_json"] or "[]")),
                "version": int(row["version"] or 1),
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "confirmed_at": row["confirmed_at"],
            }
        if "style_tags_json" in payload:
            payload["style_tags"] = json.loads(str(payload.pop("style_tags_json") or "[]"))
        return StyleProfile.model_validate(payload)

    def _params(self, profile: StyleProfile) -> tuple[object, ...]:
        return (
            profile.profile_id,
            profile.work_id,
            profile.source_type.value,
            profile.source_ref,
            profile.source_text_hash,
            profile.source_text_length,
            profile.confidence,
            profile.low_confidence_reason,
            profile.avg_sentence_length,
            profile.sentence_length_variance,
            profile.short_sentence_ratio,
            profile.long_sentence_ratio,
            profile.compound_sentence_ratio,
            profile.avg_paragraph_length,
            profile.paragraph_length_variance,
            profile.dialogue_ratio,
            profile.psychological_ratio,
            profile.action_ratio,
            profile.description_ratio,
            profile.narrative_perspective,
            profile.tense_preference,
            profile.style_summary,
            json.dumps(profile.style_tags, ensure_ascii=False),
            profile.version,
            profile.status.value,
            profile.created_at,
            profile.updated_at,
            profile.confirmed_at,
        )
