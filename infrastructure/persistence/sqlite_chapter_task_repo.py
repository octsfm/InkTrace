from domain.entities.chapter_task import ChapterTask
from domain.constants.story_constants import DEFAULT_FORESHADOWING_ACTION, DEFAULT_HOOK_STRENGTH
from domain.constants.story_enums import WRITING_STATUS_READY
from domain.repositories.chapter_task_repository import IChapterTaskRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteChapterTaskRepository(_SQLiteRepoSupport, IChapterTaskRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chapter_tasks (
                    id TEXT PRIMARY KEY, chapter_id TEXT, project_id TEXT, branch_id TEXT, chapter_number INTEGER,
                    chapter_function TEXT, goals_json TEXT, must_continue_points_json TEXT, forbidden_jumps_json TEXT,
                    required_foreshadowing_action TEXT, required_hook_strength TEXT, pace_target TEXT, opening_continuation TEXT,
                    chapter_payoff TEXT, style_bias TEXT, status TEXT, version INTEGER, created_at TEXT, updated_at TEXT
                )"""
            )
            conn.commit()

    def find_by_id(self, item_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM chapter_tasks WHERE id = ?", (item_id,)).fetchone()
            return self._from_row(row) if row else None

    def find_by_project_id(self, project_id: str):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM chapter_tasks WHERE project_id = ? ORDER BY chapter_number ASC, updated_at ASC", (project_id,)).fetchall()
            return [self._from_row(row) for row in rows]

    def replace_by_project(self, project_id: str, items):
        with self._connect() as conn:
            conn.execute("DELETE FROM chapter_tasks WHERE project_id = ?", (project_id,))
            conn.commit()
        for item in items:
            self.save(item)

    def save(self, item: ChapterTask) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT OR REPLACE INTO chapter_tasks
            (id, chapter_id, project_id, branch_id, chapter_number, chapter_function, goals_json, must_continue_points_json, forbidden_jumps_json, required_foreshadowing_action, required_hook_strength, pace_target, opening_continuation, chapter_payoff, style_bias, status, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.chapter_id, item.project_id, item.branch_id, item.chapter_number, item.chapter_function, self._json_dumps(item.goals), self._json_dumps(item.must_continue_points), self._json_dumps(item.forbidden_jumps), item.required_foreshadowing_action, item.required_hook_strength, item.pace_target, item.opening_continuation, item.chapter_payoff, item.style_bias, item.status, item.version, item.created_at.isoformat(), item.updated_at.isoformat()))
            conn.commit()

    def _from_row(self, row):
        return ChapterTask(id=row["id"], chapter_id=row["chapter_id"] or "", project_id=row["project_id"] or "", branch_id=row["branch_id"] or "", chapter_number=int(row["chapter_number"] or 0), chapter_function=row["chapter_function"] or "", goals=self._json_loads(row["goals_json"], []), must_continue_points=self._json_loads(row["must_continue_points_json"], []), forbidden_jumps=self._json_loads(row["forbidden_jumps_json"], []), required_foreshadowing_action=row["required_foreshadowing_action"] or DEFAULT_FORESHADOWING_ACTION, required_hook_strength=row["required_hook_strength"] or DEFAULT_HOOK_STRENGTH, pace_target=row["pace_target"] or "", opening_continuation=row["opening_continuation"] or "", chapter_payoff=row["chapter_payoff"] or "", style_bias=row["style_bias"] or "", status=row["status"] or WRITING_STATUS_READY, version=int(row["version"] or 1), created_at=self._dt(row["created_at"]), updated_at=self._dt(row["updated_at"]))
