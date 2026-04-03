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
                    total_chapters INTEGER DEFAULT 0,
                    completed_chapters INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    completed_chunks INTEGER DEFAULT 0,
                    percent INTEGER DEFAULT 0,
                    stage TEXT DEFAULT 'idle',
                    message TEXT DEFAULT '',
                    current_chapter_title TEXT DEFAULT '',
                    resumable INTEGER DEFAULT 0,
                    checkpoint_memory TEXT,
                    status TEXT DEFAULT 'idle',
                    last_error TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            self._ensure_column(conn, "organize_jobs", "percent", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "organize_jobs", "stage", "TEXT DEFAULT 'idle'")
            self._ensure_column(conn, "organize_jobs", "message", "TEXT DEFAULT ''")
            self._ensure_column(conn, "organize_jobs", "current_chapter_title", "TEXT DEFAULT ''")
            self._ensure_column(conn, "organize_jobs", "resumable", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "organize_jobs", "total_chapters", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "organize_jobs", "completed_chapters", "INTEGER DEFAULT 0")
            conn.commit()

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = {row[1] for row in rows}
        if column_name in columns:
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

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
                (novel_id, source_hash, total_chapters, completed_chapters, total_chunks, completed_chunks, percent, stage, message, current_chapter_title, resumable, checkpoint_memory, status, last_error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(job.novel_id),
                    job.source_hash,
                    job.total_chapters,
                    job.completed_chapters,
                    job.total_chunks,
                    job.completed_chunks,
                    int(job.percent or 0),
                    job.stage or "idle",
                    job.message or "",
                    job.current_chapter_title or "",
                    1 if job.resumable else 0,
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
            total_chapters=int(row["total_chapters"] or row["total_chunks"] or 0),
            completed_chapters=int(row["completed_chapters"] or row["completed_chunks"] or 0),
            checkpoint_memory=checkpoint_memory if isinstance(checkpoint_memory, dict) else {},
            status=status,
            percent=int(row["percent"] or 0),
            stage=row["stage"] or "idle",
            message=row["message"] or "",
            current_chapter_title=row["current_chapter_title"] or "",
            resumable=bool(int(row["resumable"] or 0)),
            last_error=row["last_error"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )
