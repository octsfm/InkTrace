from __future__ import annotations

import sqlite3
from pathlib import Path

from domain.entities.ai.models import CitationLink
from domain.repositories.ai.citation_link_repository import CitationLinkRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class SQLiteCitationLinkRepository(CitationLinkRepository):
    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def save(self, citation: CitationLink) -> CitationLink:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO citation_links (
                    citation_id, candidate_version_id, candidate_draft_id, work_id,
                    source_type, source_id, source_hash, source_name_snapshot, source_span,
                    source_excerpt, context_in_draft, verification_status,
                    verification_detail, confidence, verified_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(citation_id) DO UPDATE SET
                    candidate_version_id = excluded.candidate_version_id,
                    candidate_draft_id = excluded.candidate_draft_id,
                    work_id = excluded.work_id,
                    source_type = excluded.source_type,
                    source_id = excluded.source_id,
                    source_hash = excluded.source_hash,
                    source_name_snapshot = excluded.source_name_snapshot,
                    source_span = excluded.source_span,
                    source_excerpt = excluded.source_excerpt,
                    context_in_draft = excluded.context_in_draft,
                    verification_status = excluded.verification_status,
                    verification_detail = excluded.verification_detail,
                    confidence = excluded.confidence,
                    verified_at = excluded.verified_at,
                    created_at = excluded.created_at
                """,
                self._params(citation),
            )
            conn.commit()
            return citation
        finally:
            conn.close()

    def save_batch(self, citations: list[CitationLink]) -> list[CitationLink]:
        if not citations:
            return []
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.executemany(
                """
                INSERT INTO citation_links (
                    citation_id, candidate_version_id, candidate_draft_id, work_id,
                    source_type, source_id, source_hash, source_name_snapshot, source_span,
                    source_excerpt, context_in_draft, verification_status,
                    verification_detail, confidence, verified_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(citation_id) DO UPDATE SET
                    candidate_version_id = excluded.candidate_version_id,
                    candidate_draft_id = excluded.candidate_draft_id,
                    work_id = excluded.work_id,
                    source_type = excluded.source_type,
                    source_id = excluded.source_id,
                    source_hash = excluded.source_hash,
                    source_name_snapshot = excluded.source_name_snapshot,
                    source_span = excluded.source_span,
                    source_excerpt = excluded.source_excerpt,
                    context_in_draft = excluded.context_in_draft,
                    verification_status = excluded.verification_status,
                    verification_detail = excluded.verification_detail,
                    confidence = excluded.confidence,
                    verified_at = excluded.verified_at,
                    created_at = excluded.created_at
                """,
                [self._params(item) for item in citations],
            )
            conn.commit()
            return citations
        finally:
            conn.close()

    def get_by_candidate_version(self, candidate_version_id: str) -> list[CitationLink]:
        return self._query(
            "SELECT * FROM citation_links WHERE candidate_version_id = ? ORDER BY created_at ASC",
            (candidate_version_id,),
        )

    def get_by_candidate_draft(self, candidate_draft_id: str) -> list[CitationLink]:
        return self._query(
            "SELECT * FROM citation_links WHERE candidate_draft_id = ? ORDER BY created_at ASC",
            (candidate_draft_id,),
        )

    def get_by_source(self, source_type: str, source_id: str) -> list[CitationLink]:
        return self._query(
            "SELECT * FROM citation_links WHERE source_type = ? AND source_id = ? ORDER BY created_at ASC",
            (source_type, source_id),
        )

    def get_by_id(self, citation_id: str) -> CitationLink | None:
        items = self._query("SELECT * FROM citation_links WHERE citation_id = ?", (citation_id,))
        return items[0] if items else None

    def _query(self, sql: str, params: tuple[object, ...]) -> list[CitationLink]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_citation(row) for row in rows]
        finally:
            conn.close()

    def _row_to_citation(self, row: sqlite3.Row) -> CitationLink:
        return CitationLink.model_validate(
            {
                "citation_id": row["citation_id"],
                "candidate_version_id": row["candidate_version_id"],
                "candidate_draft_id": row["candidate_draft_id"],
                "work_id": row["work_id"],
                "source_type": row["source_type"],
                "source_id": row["source_id"],
                "source_hash": row["source_hash"],
                "source_name_snapshot": row["source_name_snapshot"],
                "source_span": row["source_span"],
                "source_excerpt": row["source_excerpt"],
                "context_in_draft": row["context_in_draft"],
                "verification_status": row["verification_status"],
                "verification_detail": row["verification_detail"],
                "confidence": float(row["confidence"] or 0.0),
                "verified_at": row["verified_at"],
                "created_at": row["created_at"],
            }
        )

    def _params(self, citation: CitationLink) -> tuple[object, ...]:
        return (
            citation.citation_id,
            citation.candidate_version_id,
            citation.candidate_draft_id,
            citation.work_id,
            citation.source_type.value,
            citation.source_id,
            citation.source_hash,
            citation.source_name_snapshot,
            citation.source_span,
            citation.source_excerpt,
            citation.context_in_draft,
            citation.verification_status.value,
            citation.verification_detail,
            citation.confidence,
            citation.verified_at,
            citation.created_at,
        )
