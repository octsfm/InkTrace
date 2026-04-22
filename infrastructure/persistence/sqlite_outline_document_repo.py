from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from domain.repositories.outline_document_repository import IOutlineDocumentRepository
from infrastructure.persistence.sqlite_utils import connect_sqlite


class SQLiteOutlineDocumentRepository(IOutlineDocumentRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_table()

    def _init_table(self) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outline_documents (
                    id TEXT PRIMARY KEY,
                    novel_id TEXT UNIQUE NOT NULL,
                    raw_content TEXT NOT NULL,
                    digest_json TEXT NOT NULL,
                    raw_hash TEXT NOT NULL,
                    digest_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save_document(
        self,
        *,
        novel_id: str,
        raw_content: str,
        digest_json: Dict[str, Any],
        raw_hash: str,
        digest_version: str,
    ) -> None:
        now = datetime.now().isoformat()
        doc_id = hashlib.sha256(f"{novel_id}:{raw_hash}".encode("utf-8")).hexdigest()[:32]
        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO outline_documents
                (id, novel_id, raw_content, digest_json, raw_hash, digest_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(novel_id) DO UPDATE SET
                  raw_content=excluded.raw_content,
                  digest_json=excluded.digest_json,
                  raw_hash=excluded.raw_hash,
                  digest_version=excluded.digest_version,
                  updated_at=excluded.updated_at
                """,
                (
                    doc_id,
                    str(novel_id),
                    str(raw_content or ""),
                    json.dumps(digest_json or {}, ensure_ascii=False),
                    str(raw_hash or ""),
                    str(digest_version or "v1"),
                    now,
                    now,
                ),
            )
            conn.commit()

    def find_by_novel_id(self, novel_id: str) -> Optional[Dict[str, Any]]:
        with connect_sqlite(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM outline_documents WHERE novel_id = ?",
                (str(novel_id),),
            ).fetchone()
            if not row:
                return None
            return {
                "id": str(row["id"] or ""),
                "novel_id": str(row["novel_id"] or ""),
                "raw_content": str(row["raw_content"] or ""),
                "digest_json": json.loads(str(row["digest_json"] or "{}") or "{}"),
                "raw_hash": str(row["raw_hash"] or ""),
                "digest_version": str(row["digest_version"] or ""),
                "created_at": str(row["created_at"] or ""),
                "updated_at": str(row["updated_at"] or ""),
            }

    def delete_by_novel_id(self, novel_id: str) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute("DELETE FROM outline_documents WHERE novel_id = ?", (str(novel_id),))
            conn.commit()
