from domain.entities.global_constraints import GlobalConstraints
from domain.repositories.global_constraints_repository import IGlobalConstraintsRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteGlobalConstraintsRepository(_SQLiteRepoSupport, IGlobalConstraintsRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS global_constraints (
                    id TEXT PRIMARY KEY,
                    project_id TEXT UNIQUE,
                    main_plot TEXT,
                    hidden_plot TEXT,
                    core_selling_points_json TEXT,
                    protagonist_core_traits_json TEXT,
                    must_keep_threads_json TEXT,
                    genre_guardrails_json TEXT,
                    source_type TEXT,
                    version INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.commit()

    def find_by_project_id(self, project_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM global_constraints WHERE project_id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return GlobalConstraints(
                id=row["id"], project_id=row["project_id"], main_plot=row["main_plot"] or "", hidden_plot=row["hidden_plot"] or "",
                core_selling_points=self._json_loads(row["core_selling_points_json"], []),
                protagonist_core_traits=self._json_loads(row["protagonist_core_traits_json"], []),
                must_keep_threads=self._json_loads(row["must_keep_threads_json"], []),
                genre_guardrails=self._json_loads(row["genre_guardrails_json"], []),
                source_type=row["source_type"] or "system", version=int(row["version"] or 1),
                created_at=self._dt(row["created_at"]), updated_at=self._dt(row["updated_at"])
            )

    def save(self, item: GlobalConstraints) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO global_constraints
                (id, project_id, main_plot, hidden_plot, core_selling_points_json, protagonist_core_traits_json, must_keep_threads_json, genre_guardrails_json, source_type, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item.id, item.project_id, item.main_plot, item.hidden_plot, self._json_dumps(item.core_selling_points), self._json_dumps(item.protagonist_core_traits), self._json_dumps(item.must_keep_threads), self._json_dumps(item.genre_guardrails), item.source_type, item.version, item.created_at.isoformat(), item.updated_at.isoformat())
            )
            conn.commit()
