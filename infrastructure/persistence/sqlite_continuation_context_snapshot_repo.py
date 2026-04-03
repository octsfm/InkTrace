from domain.entities.continuation_context_snapshot import ContinuationContextSnapshot
from domain.repositories.continuation_context_snapshot_repository import IContinuationContextSnapshotRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteContinuationContextSnapshotRepository(_SQLiteRepoSupport, IContinuationContextSnapshotRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS continuation_context_snapshots (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    chapter_id TEXT,
                    chapter_number INTEGER,
                    recent_chapter_memories_json TEXT,
                    last_chapter_tail TEXT,
                    relevant_characters_json TEXT,
                    relevant_foreshadowing_json TEXT,
                    global_constraints_json TEXT,
                    chapter_task_seed_json TEXT,
                    style_requirements_json TEXT,
                    created_at TEXT
                )"""
            )
            conn.commit()

    def find_latest(self, project_id: str, chapter_id: str = ""):
        with self._connect() as conn:
            if chapter_id:
                row = conn.execute(
                    "SELECT * FROM continuation_context_snapshots WHERE project_id = ? AND chapter_id = ? ORDER BY created_at DESC LIMIT 1",
                    (project_id, chapter_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM continuation_context_snapshots WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                    (project_id,),
                ).fetchone()
            return self._from_row(row) if row else None

    def list_by_project_id(self, project_id: str, limit: int = 20):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM continuation_context_snapshots WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, max(1, int(limit or 20))),
            ).fetchall()
            return [self._from_row(row) for row in rows]

    def save(self, item: ContinuationContextSnapshot) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO continuation_context_snapshots
                (id, project_id, chapter_id, chapter_number, recent_chapter_memories_json, last_chapter_tail, relevant_characters_json, relevant_foreshadowing_json, global_constraints_json, chapter_task_seed_json, style_requirements_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.id,
                    item.project_id,
                    item.chapter_id,
                    item.chapter_number,
                    self._json_dumps(item.recent_chapter_memories),
                    item.last_chapter_tail,
                    self._json_dumps(item.relevant_characters),
                    self._json_dumps(item.relevant_foreshadowing),
                    self._json_dumps(item.global_constraints),
                    self._json_dumps(item.chapter_task_seed),
                    self._json_dumps(item.style_requirements),
                    item.created_at.isoformat(),
                ),
            )
            conn.commit()

    def _from_row(self, row):
        return ContinuationContextSnapshot(
            id=row["id"],
            project_id=row["project_id"] or "",
            chapter_id=row["chapter_id"] or "",
            chapter_number=int(row["chapter_number"] or 0),
            recent_chapter_memories=self._json_loads(row["recent_chapter_memories_json"], []),
            last_chapter_tail=row["last_chapter_tail"] or "",
            relevant_characters=self._json_loads(row["relevant_characters_json"], []),
            relevant_foreshadowing=self._json_loads(row["relevant_foreshadowing_json"], []),
            global_constraints=self._json_loads(row["global_constraints_json"], {}),
            chapter_task_seed=self._json_loads(row["chapter_task_seed_json"], {}),
            style_requirements=self._json_loads(row["style_requirements_json"], {}),
            created_at=self._dt(row["created_at"]),
        )
