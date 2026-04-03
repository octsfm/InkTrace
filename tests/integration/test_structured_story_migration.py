import sqlite3
from pathlib import Path
import json

from application.services import structured_story_migration_service as migration


def test_migration_script_marks_projects(tmp_path: Path, monkeypatch):
    db_path = str(tmp_path / "migration.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE project_memories (
                project_id TEXT,
                is_active INTEGER DEFAULT 1,
                structured_story_migrated INTEGER DEFAULT 0,
                global_constraints_json TEXT DEFAULT '{}',
                chapter_analysis_memories_json TEXT DEFAULT '[]',
                chapter_continuation_memories_json TEXT DEFAULT '[]',
                chapter_tasks_json TEXT DEFAULT '[]',
                structural_drafts_json TEXT DEFAULT '[]',
                detemplated_drafts_json TEXT DEFAULT '[]',
                draft_integrity_checks_json TEXT DEFAULT '[]',
                style_requirements_json TEXT DEFAULT '{}'
            )
            """
        )
        conn.execute(
            "INSERT INTO project_memories (project_id, global_constraints_json, chapter_tasks_json, style_requirements_json) VALUES (?, ?, ?, ?)",
            ("p1", json.dumps({"main_plot": "A"}), json.dumps([{"id": "t1", "chapter_number": 1}]), json.dumps({"preferred_rhythm": "中速"})),
        )
        conn.execute("INSERT INTO project_memories (project_id) VALUES ('p2')")
        conn.commit()

    marked = []
    saved_tasks = []

    class _Repo:
        def save(self, *_args, **_kwargs):
            return None

        def replace_by_project(self, *_args, **_kwargs):
            return None

        def find_by_id(self, *_args, **_kwargs):
            return None

        def find_by_chapter_id(self, *_args, **_kwargs):
            return []

        def find_by_project_id(self, *_args, **_kwargs):
            return []

    class _TaskRepo(_Repo):
        def save(self, item):
            saved_tasks.append(item.id)

    class _FakeV2Repo:
        def mark_structured_story_migrated(self, project_id: str):
            marked.append(project_id)

    monkeypatch.setattr(migration, "DB_PATH", db_path)
    monkeypatch.setattr(migration, "get_v2_repo", lambda: _FakeV2Repo())
    monkeypatch.setattr(migration, "get_global_constraints_repo", lambda: _Repo())
    monkeypatch.setattr(migration, "get_chapter_analysis_memory_repo", lambda: _Repo())
    monkeypatch.setattr(migration, "get_chapter_continuation_memory_repo", lambda: _Repo())
    monkeypatch.setattr(migration, "get_chapter_task_repo", lambda: _TaskRepo())
    monkeypatch.setattr(migration, "get_structural_draft_repo", lambda: _Repo())
    monkeypatch.setattr(migration, "get_detemplated_draft_repo", lambda: _Repo())
    monkeypatch.setattr(migration, "get_draft_integrity_check_repo", lambda: _Repo())
    monkeypatch.setattr(migration, "get_style_requirements_repo", lambda: _Repo())

    result = migration.StructuredStoryMigrationService().run()

    assert marked == ["p1", "p2"]
    assert result["migrated_projects"] == 2
    assert saved_tasks == ["t1"]
