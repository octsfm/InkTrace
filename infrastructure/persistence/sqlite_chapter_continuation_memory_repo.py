from domain.entities.chapter_continuation_memory import ChapterContinuationMemory
from domain.repositories.chapter_continuation_memory_repository import IChapterContinuationMemoryRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteChapterContinuationMemoryRepository(_SQLiteRepoSupport, IChapterContinuationMemoryRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chapter_continuation_memories (
                    id TEXT PRIMARY KEY, chapter_id TEXT, chapter_number INTEGER, chapter_title TEXT, scene_summary TEXT,
                    scene_state_json TEXT, protagonist_state_json TEXT, active_characters_json TEXT, active_conflicts_json TEXT,
                    immediate_threads_json TEXT, long_term_threads_json TEXT, recent_reveals_json TEXT, must_continue_points_json TEXT,
                    forbidden_jumps_json TEXT, tone_and_pacing_json TEXT, last_hook TEXT, version INTEGER, created_at TEXT, updated_at TEXT
                )"""
            )
            conn.commit()

    def find_by_id(self, item_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM chapter_continuation_memories WHERE id = ?", (item_id,)).fetchone()
            return self._from_row(row) if row else None

    def find_by_chapter_id(self, chapter_id: str):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM chapter_continuation_memories WHERE chapter_id = ? ORDER BY updated_at DESC", (chapter_id,)).fetchall()
            return [self._from_row(row) for row in rows]

    def save(self, item: ChapterContinuationMemory) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT OR REPLACE INTO chapter_continuation_memories
            (id, chapter_id, chapter_number, chapter_title, scene_summary, scene_state_json, protagonist_state_json, active_characters_json, active_conflicts_json, immediate_threads_json, long_term_threads_json, recent_reveals_json, must_continue_points_json, forbidden_jumps_json, tone_and_pacing_json, last_hook, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.chapter_id, item.chapter_number, item.chapter_title, item.scene_summary, self._json_dumps(item.scene_state), self._json_dumps(item.protagonist_state), self._json_dumps(item.active_characters), self._json_dumps(item.active_conflicts), self._json_dumps(item.immediate_threads), self._json_dumps(item.long_term_threads), self._json_dumps(item.recent_reveals), self._json_dumps(item.must_continue_points), self._json_dumps(item.forbidden_jumps), self._json_dumps(item.tone_and_pacing), item.last_hook, item.version, item.created_at.isoformat(), item.updated_at.isoformat()))
            conn.commit()

    def _from_row(self, row):
        return ChapterContinuationMemory(id=row["id"], chapter_id=row["chapter_id"], chapter_number=int(row["chapter_number"] or 0), chapter_title=row["chapter_title"] or "", scene_summary=row["scene_summary"] or "", scene_state=self._json_loads(row["scene_state_json"], {}), protagonist_state=self._json_loads(row["protagonist_state_json"], {}), active_characters=self._json_loads(row["active_characters_json"], []), active_conflicts=self._json_loads(row["active_conflicts_json"], []), immediate_threads=self._json_loads(row["immediate_threads_json"], []), long_term_threads=self._json_loads(row["long_term_threads_json"], []), recent_reveals=self._json_loads(row["recent_reveals_json"], []), must_continue_points=self._json_loads(row["must_continue_points_json"], []), forbidden_jumps=self._json_loads(row["forbidden_jumps_json"], []), tone_and_pacing=self._json_loads(row["tone_and_pacing_json"], {}), last_hook=row["last_hook"] or "", version=int(row["version"] or 1), created_at=self._dt(row["created_at"]), updated_at=self._dt(row["updated_at"]))
