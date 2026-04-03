from domain.entities.style_requirements import StyleRequirements
from domain.constants.story_enums import STYLE_SOURCE_MANUAL
from domain.repositories.style_requirements_repository import IStyleRequirementsRepository
from infrastructure.persistence.sqlite_structured_story_repo_support import _SQLiteRepoSupport


class SQLiteStyleRequirementsRepository(_SQLiteRepoSupport, IStyleRequirementsRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS style_requirements (
                    id TEXT PRIMARY KEY, project_id TEXT UNIQUE, author_voice_keywords_json TEXT, avoid_patterns_json TEXT,
                    preferred_rhythm TEXT, narrative_distance TEXT, dialogue_density TEXT, source_type TEXT, version INTEGER, created_at TEXT, updated_at TEXT
                )"""
            )
            conn.commit()

    def find_by_project_id(self, project_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM style_requirements WHERE project_id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return StyleRequirements(id=row["id"], project_id=row["project_id"], author_voice_keywords=self._json_loads(row["author_voice_keywords_json"], []), avoid_patterns=self._json_loads(row["avoid_patterns_json"], []), preferred_rhythm=row["preferred_rhythm"] or "", narrative_distance=row["narrative_distance"] or "", dialogue_density=row["dialogue_density"] or "", source_type=row["source_type"] or STYLE_SOURCE_MANUAL, version=int(row["version"] or 1), created_at=self._dt(row["created_at"]), updated_at=self._dt(row["updated_at"]))

    def save(self, item: StyleRequirements) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT OR REPLACE INTO style_requirements
            (id, project_id, author_voice_keywords_json, avoid_patterns_json, preferred_rhythm, narrative_distance, dialogue_density, source_type, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.project_id, self._json_dumps(item.author_voice_keywords), self._json_dumps(item.avoid_patterns), item.preferred_rhythm, item.narrative_distance, item.dialogue_density, item.source_type, item.version, item.created_at.isoformat(), item.updated_at.isoformat()))
            conn.commit()
