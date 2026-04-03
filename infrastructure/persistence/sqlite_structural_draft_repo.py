from domain.entities.structural_draft import StructuralDraft
from domain.constants.story_enums import GENERATION_STAGE_STRUCTURAL
from domain.repositories.structural_draft_repository import IStructuralDraftRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteStructuralDraftRepository(_SQLiteRepoSupport, IStructuralDraftRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS structural_drafts (
                    id TEXT PRIMARY KEY, chapter_id TEXT, project_id TEXT, chapter_number INTEGER, title TEXT, content TEXT,
                    source_task_id TEXT, model_name TEXT, used_fallback INTEGER, generation_stage TEXT, version INTEGER, created_at TEXT, updated_at TEXT
                )"""
            )
            conn.commit()

    def find_by_id(self, item_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM structural_drafts WHERE id = ?", (item_id,)).fetchone()
            return self._from_row(row) if row else None

    def find_by_project_id(self, project_id: str):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM structural_drafts WHERE project_id = ? ORDER BY updated_at ASC", (project_id,)).fetchall()
            return [self._from_row(row) for row in rows]

    def save(self, item: StructuralDraft) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT OR REPLACE INTO structural_drafts
            (id, chapter_id, project_id, chapter_number, title, content, source_task_id, model_name, used_fallback, generation_stage, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.chapter_id, item.project_id, item.chapter_number, item.title, item.content, item.source_task_id, item.model_name, 1 if item.used_fallback else 0, item.generation_stage, item.version, item.created_at.isoformat(), item.updated_at.isoformat()))
            conn.commit()

    def _from_row(self, row):
        return StructuralDraft(id=row["id"], chapter_id=row["chapter_id"] or "", project_id=row["project_id"] or "", chapter_number=int(row["chapter_number"] or 0), title=row["title"] or "", content=row["content"] or "", source_task_id=row["source_task_id"] or "", model_name=row["model_name"] or "", used_fallback=bool(int(row["used_fallback"] or 0)), generation_stage=row["generation_stage"] or GENERATION_STAGE_STRUCTURAL, version=int(row["version"] or 1), created_at=self._dt(row["created_at"]), updated_at=self._dt(row["updated_at"]))
