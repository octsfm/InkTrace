import sqlite3
from datetime import datetime
from typing import List

from domain.entities.chapter_arc_binding import ChapterArcBinding
from domain.repositories.chapter_arc_binding_repository import IChapterArcBindingRepository


class SQLiteChapterArcBindingRepository(IChapterArcBindingRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_table()

    def _init_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chapter_arc_bindings (
                    binding_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    chapter_id TEXT NOT NULL,
                    arc_id TEXT NOT NULL,
                    binding_role TEXT NOT NULL,
                    push_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chapter_arc_bindings_project_id ON chapter_arc_bindings(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chapter_arc_bindings_chapter_id ON chapter_arc_bindings(chapter_id)")
            conn.commit()

    def save(self, binding: ChapterArcBinding) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chapter_arc_bindings (
                    binding_id, project_id, chapter_id, arc_id, binding_role, push_type, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    binding.binding_id,
                    binding.project_id,
                    binding.chapter_id,
                    binding.arc_id,
                    binding.binding_role,
                    binding.push_type,
                    float(binding.confidence),
                    binding.created_at.isoformat(),
                ),
            )
            conn.commit()

    def list_by_project(self, project_id: str) -> List[ChapterArcBinding]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM chapter_arc_bindings WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def list_by_chapter(self, chapter_id: str) -> List[ChapterArcBinding]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM chapter_arc_bindings WHERE chapter_id = ? ORDER BY created_at DESC",
                (chapter_id,),
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def delete_by_project(self, project_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM chapter_arc_bindings WHERE project_id = ?", (project_id,))
            conn.commit()

    def _row_to_entity(self, row: sqlite3.Row) -> ChapterArcBinding:
        return ChapterArcBinding(
            binding_id=row["binding_id"],
            project_id=row["project_id"],
            chapter_id=row["chapter_id"],
            arc_id=row["arc_id"],
            binding_role=row["binding_role"] or "background",
            push_type=row["push_type"] or "advance",
            confidence=float(row["confidence"] or 0.6),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )
