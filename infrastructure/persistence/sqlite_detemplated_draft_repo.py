from domain.entities.detemplated_draft import DetemplatedDraft
from domain.constants.story_enums import GENERATION_STAGE_DETEMPLATED
from domain.repositories.detemplated_draft_repository import IDetemplatedDraftRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteDetemplatedDraftRepository(_SQLiteRepoSupport, IDetemplatedDraftRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS detemplated_drafts (
                    id TEXT PRIMARY KEY, chapter_id TEXT, project_id TEXT, chapter_number INTEGER, title TEXT, content TEXT,
                    based_on_structural_draft_id TEXT, style_requirements_snapshot_json TEXT, model_name TEXT, used_fallback INTEGER,
                    integrity_failed INTEGER DEFAULT 0, display_fallback_to_structural INTEGER DEFAULT 0,
                    generation_stage TEXT, version INTEGER, created_at TEXT, updated_at TEXT
                )"""
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(detemplated_drafts)").fetchall()}
            if "integrity_failed" not in columns:
                conn.execute("ALTER TABLE detemplated_drafts ADD COLUMN integrity_failed INTEGER DEFAULT 0")
            if "display_fallback_to_structural" not in columns:
                conn.execute("ALTER TABLE detemplated_drafts ADD COLUMN display_fallback_to_structural INTEGER DEFAULT 0")
            conn.commit()

    def find_by_id(self, item_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM detemplated_drafts WHERE id = ?", (item_id,)).fetchone()
            return self._from_row(row) if row else None

    def find_by_project_id(self, project_id: str):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM detemplated_drafts WHERE project_id = ? ORDER BY updated_at ASC", (project_id,)).fetchall()
            return [self._from_row(row) for row in rows]

    def save(self, item: DetemplatedDraft) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT OR REPLACE INTO detemplated_drafts
            (id, chapter_id, project_id, chapter_number, title, content, based_on_structural_draft_id, style_requirements_snapshot_json, model_name, used_fallback, integrity_failed, display_fallback_to_structural, generation_stage, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.chapter_id, item.project_id, item.chapter_number, item.title, item.content, item.based_on_structural_draft_id, self._json_dumps(item.style_requirements_snapshot), item.model_name, 1 if item.used_fallback else 0, 1 if item.integrity_failed else 0, 1 if item.display_fallback_to_structural else 0, item.generation_stage, item.version, item.created_at.isoformat(), item.updated_at.isoformat()))
            conn.commit()

    def _from_row(self, row):
        return DetemplatedDraft(id=row["id"], chapter_id=row["chapter_id"] or "", project_id=row["project_id"] or "", chapter_number=int(row["chapter_number"] or 0), title=row["title"] or "", content=row["content"] or "", based_on_structural_draft_id=row["based_on_structural_draft_id"] or "", style_requirements_snapshot=self._json_loads(row["style_requirements_snapshot_json"], {}), model_name=row["model_name"] or "", used_fallback=bool(int(row["used_fallback"] or 0)), integrity_failed=bool(int(row["integrity_failed"] or 0)), display_fallback_to_structural=bool(int(row["display_fallback_to_structural"] or 0)), generation_stage=row["generation_stage"] or GENERATION_STAGE_DETEMPLATED, version=int(row["version"] or 1), created_at=self._dt(row["created_at"]), updated_at=self._dt(row["updated_at"]))
