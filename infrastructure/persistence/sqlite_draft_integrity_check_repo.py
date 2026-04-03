from domain.entities.draft_integrity_check import DraftIntegrityCheck
from domain.repositories.draft_integrity_check_repository import IDraftIntegrityCheckRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteDraftIntegrityCheckRepository(_SQLiteRepoSupport, IDraftIntegrityCheckRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS draft_integrity_checks (
                    id TEXT PRIMARY KEY, chapter_id TEXT, project_id TEXT, structural_draft_id TEXT, detemplated_draft_id TEXT,
                    event_integrity_ok INTEGER, motivation_integrity_ok INTEGER, foreshadowing_integrity_ok INTEGER,
                    hook_integrity_ok INTEGER, continuity_ok INTEGER, arc_consistency_ok INTEGER, title_alignment_ok INTEGER,
                    progression_integrity_ok INTEGER, risk_notes_json TEXT, issue_list_json TEXT, revision_suggestion TEXT,
                    revision_attempted INTEGER, revision_succeeded INTEGER, created_at TEXT
                )"""
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(draft_integrity_checks)").fetchall()}
            if "arc_consistency_ok" not in columns:
                conn.execute("ALTER TABLE draft_integrity_checks ADD COLUMN arc_consistency_ok INTEGER DEFAULT 1")
            if "title_alignment_ok" not in columns:
                conn.execute("ALTER TABLE draft_integrity_checks ADD COLUMN title_alignment_ok INTEGER DEFAULT 1")
            if "progression_integrity_ok" not in columns:
                conn.execute("ALTER TABLE draft_integrity_checks ADD COLUMN progression_integrity_ok INTEGER DEFAULT 1")
            if "issue_list_json" not in columns:
                conn.execute("ALTER TABLE draft_integrity_checks ADD COLUMN issue_list_json TEXT DEFAULT '[]'")
            if "revision_suggestion" not in columns:
                conn.execute("ALTER TABLE draft_integrity_checks ADD COLUMN revision_suggestion TEXT DEFAULT ''")
            if "revision_attempted" not in columns:
                conn.execute("ALTER TABLE draft_integrity_checks ADD COLUMN revision_attempted INTEGER DEFAULT 0")
            if "revision_succeeded" not in columns:
                conn.execute("ALTER TABLE draft_integrity_checks ADD COLUMN revision_succeeded INTEGER DEFAULT 0")
            conn.commit()

    def find_by_id(self, item_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM draft_integrity_checks WHERE id = ?", (item_id,)).fetchone()
            return self._from_row(row) if row else None

    def find_by_project_id(self, project_id: str):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM draft_integrity_checks WHERE project_id = ? ORDER BY created_at ASC", (project_id,)).fetchall()
            return [self._from_row(row) for row in rows]

    def save(self, item: DraftIntegrityCheck) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT OR REPLACE INTO draft_integrity_checks
            (id, chapter_id, project_id, structural_draft_id, detemplated_draft_id, event_integrity_ok, motivation_integrity_ok, foreshadowing_integrity_ok, hook_integrity_ok, continuity_ok, arc_consistency_ok, title_alignment_ok, progression_integrity_ok, risk_notes_json, issue_list_json, revision_suggestion, revision_attempted, revision_succeeded, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.id,
                item.chapter_id,
                item.project_id,
                item.structural_draft_id,
                item.detemplated_draft_id,
                1 if item.event_integrity_ok else 0,
                1 if item.motivation_integrity_ok else 0,
                1 if item.foreshadowing_integrity_ok else 0,
                1 if item.hook_integrity_ok else 0,
                1 if item.continuity_ok else 0,
                1 if item.arc_consistency_ok else 0,
                1 if item.title_alignment_ok else 0,
                1 if item.progression_integrity_ok else 0,
                self._json_dumps(item.risk_notes),
                self._json_dumps(item.issue_list),
                item.revision_suggestion,
                1 if item.revision_attempted else 0,
                1 if item.revision_succeeded else 0,
                item.created_at.isoformat(),
            ))
            conn.commit()

    def _from_row(self, row):
        return DraftIntegrityCheck(
            id=row["id"],
            chapter_id=row["chapter_id"] or "",
            project_id=row["project_id"] or "",
            structural_draft_id=row["structural_draft_id"] or "",
            detemplated_draft_id=row["detemplated_draft_id"] or "",
            event_integrity_ok=bool(int(row["event_integrity_ok"] or 0)),
            motivation_integrity_ok=bool(int(row["motivation_integrity_ok"] or 0)),
            foreshadowing_integrity_ok=bool(int(row["foreshadowing_integrity_ok"] or 0)),
            hook_integrity_ok=bool(int(row["hook_integrity_ok"] or 0)),
            continuity_ok=bool(int(row["continuity_ok"] or 0)),
            arc_consistency_ok=bool(int(row["arc_consistency_ok"] or 0)),
            title_alignment_ok=bool(int(row["title_alignment_ok"] or 1)),
            progression_integrity_ok=bool(int(row["progression_integrity_ok"] or 1)),
            risk_notes=self._json_loads(row["risk_notes_json"], []),
            issue_list=self._json_loads(row["issue_list_json"], []),
            revision_suggestion=row["revision_suggestion"] or "",
            revision_attempted=bool(int(row["revision_attempted"] or 0)),
            revision_succeeded=bool(int(row["revision_succeeded"] or 0)),
            created_at=self._dt(row["created_at"]),
        )
