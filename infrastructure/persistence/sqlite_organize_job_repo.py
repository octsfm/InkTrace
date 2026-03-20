import json
import os
import sqlite3
from datetime import datetime
from typing import Optional

from domain.entities.organize_job import OrganizeJob
from domain.repositories.organize_job_repository import IOrganizeJobRepository
from domain.types import NovelId, OrganizeJobStatus


class SQLiteOrganizeJobRepository(IOrganizeJobRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_table()

    def _init_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organize_jobs (
                    novel_id TEXT PRIMARY KEY,
                    source_hash TEXT,
                    total_chunks INTEGER DEFAULT 0,
                    completed_chunks INTEGER DEFAULT 0,
                    checkpoint_memory TEXT,
                    status TEXT DEFAULT 'idle',
                    last_error TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.commit()

    def find_by_novel_id(self, novel_id: NovelId) -> Optional[OrganizeJob]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM organize_jobs WHERE novel_id = ?",
                (str(novel_id),)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def save(self, job: OrganizeJob) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO organize_jobs
                (novel_id, source_hash, total_chunks, completed_chunks, checkpoint_memory, status, last_error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(job.novel_id),
                    job.source_hash,
                    job.total_chunks,
                    job.completed_chunks,
                    json.dumps(job.checkpoint_memory or {}, ensure_ascii=False),
                    job.status.value,
                    job.last_error,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                )
            )
            conn.commit()

    def delete(self, novel_id: NovelId) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM organize_jobs WHERE novel_id = ?", (str(novel_id),))
            conn.commit()

    def _row_to_job(self, row: sqlite3.Row) -> OrganizeJob:
        try:
            status = OrganizeJobStatus(row["status"])
        except Exception:
            status = OrganizeJobStatus.IDLE
        try:
            checkpoint_memory = json.loads(row["checkpoint_memory"] or "{}")
        except Exception:
            checkpoint_memory = {}
        return OrganizeJob(
            novel_id=NovelId(row["novel_id"]),
            source_hash=row["source_hash"] or "",
            total_chunks=int(row["total_chunks"] or 0),
            completed_chunks=int(row["completed_chunks"] or 0),
            checkpoint_memory=checkpoint_memory if isinstance(checkpoint_memory, dict) else {},
            status=status,
            last_error=row["last_error"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )
