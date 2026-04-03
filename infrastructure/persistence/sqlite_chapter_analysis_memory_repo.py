from domain.entities.chapter_analysis_memory import ChapterAnalysisMemory
from domain.repositories.chapter_analysis_memory_repository import IChapterAnalysisMemoryRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteChapterAnalysisMemoryRepository(_SQLiteRepoSupport, IChapterAnalysisMemoryRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chapter_analysis_memories (
                    id TEXT PRIMARY KEY, chapter_id TEXT, chapter_number INTEGER, chapter_title TEXT, summary TEXT,
                    events_json TEXT, plot_role TEXT, conflict TEXT, foreshadowing_json TEXT, hook TEXT, problems_json TEXT,
                    version INTEGER, created_at TEXT, updated_at TEXT
                )"""
            )
            conn.commit()

    def find_by_id(self, item_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM chapter_analysis_memories WHERE id = ?", (item_id,)).fetchone()
            return self._from_row(row) if row else None

    def find_by_chapter_id(self, chapter_id: str):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM chapter_analysis_memories WHERE chapter_id = ? ORDER BY updated_at DESC", (chapter_id,)).fetchall()
            return [self._from_row(row) for row in rows]

    def save(self, item: ChapterAnalysisMemory) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT OR REPLACE INTO chapter_analysis_memories
            (id, chapter_id, chapter_number, chapter_title, summary, events_json, plot_role, conflict, foreshadowing_json, hook, problems_json, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.chapter_id, item.chapter_number, item.chapter_title, item.summary, self._json_dumps(item.events), item.plot_role, item.conflict, self._json_dumps(item.foreshadowing), item.hook, self._json_dumps(item.problems), item.version, item.created_at.isoformat(), item.updated_at.isoformat()))
            conn.commit()

    def _from_row(self, row):
        return ChapterAnalysisMemory(id=row["id"], chapter_id=row["chapter_id"], chapter_number=int(row["chapter_number"] or 0), chapter_title=row["chapter_title"] or "", summary=row["summary"] or "", events=self._json_loads(row["events_json"], []), plot_role=row["plot_role"] or "", conflict=row["conflict"] or "", foreshadowing=self._json_loads(row["foreshadowing_json"], []), hook=row["hook"] or "", problems=self._json_loads(row["problems_json"], []), version=int(row["version"] or 1), created_at=self._dt(row["created_at"]), updated_at=self._dt(row["updated_at"]))
