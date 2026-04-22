import json
import sqlite3
from datetime import datetime
from typing import List

from domain.entities.arc_progress_snapshot import ArcProgressSnapshot
from domain.repositories.arc_progress_snapshot_repository import IArcProgressSnapshotRepository
from infrastructure.persistence.sqlite_utils import connect_sqlite


class SQLiteArcProgressSnapshotRepository(IArcProgressSnapshotRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_table()

    def _init_table(self) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS arc_progress_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    arc_id TEXT NOT NULL,
                    chapter_id TEXT NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    stage_before TEXT NOT NULL,
                    stage_after TEXT NOT NULL,
                    progress_summary TEXT,
                    change_reason TEXT,
                    new_conflicts_json TEXT,
                    new_payoffs_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_arc_snapshots_arc_id ON arc_progress_snapshots(arc_id)")
            conn.commit()

    def save(self, snapshot: ArcProgressSnapshot) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO arc_progress_snapshots (
                    snapshot_id, arc_id, chapter_id, chapter_number, stage_before, stage_after,
                    progress_summary, change_reason, new_conflicts_json, new_payoffs_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.arc_id,
                    snapshot.chapter_id,
                    int(snapshot.chapter_number),
                    snapshot.stage_before,
                    snapshot.stage_after,
                    snapshot.progress_summary,
                    snapshot.change_reason,
                    json.dumps(snapshot.new_conflicts, ensure_ascii=False),
                    json.dumps(snapshot.new_payoffs, ensure_ascii=False),
                    snapshot.created_at.isoformat(),
                ),
            )
            conn.commit()

    def list_by_arc(self, arc_id: str) -> List[ArcProgressSnapshot]:
        with connect_sqlite(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM arc_progress_snapshots WHERE arc_id = ? ORDER BY created_at DESC",
                (arc_id,),
            ).fetchall()
        return [
            ArcProgressSnapshot(
                snapshot_id=row["snapshot_id"],
                arc_id=row["arc_id"],
                chapter_id=row["chapter_id"],
                chapter_number=int(row["chapter_number"] or 0),
                stage_before=row["stage_before"] or "setup",
                stage_after=row["stage_after"] or "setup",
                progress_summary=row["progress_summary"] or "",
                change_reason=row["change_reason"] or "",
                new_conflicts=json.loads(row["new_conflicts_json"] or "[]"),
                new_payoffs=json.loads(row["new_payoffs_json"] or "[]"),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            )
            for row in rows
        ]
