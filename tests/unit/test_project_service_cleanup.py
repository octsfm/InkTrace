import os
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path

from application.services.project_service import ProjectService
from domain.types import ProjectId


class _Id:
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value


class _FakeProject:
    def __init__(self, project_id: str, novel_id: str):
        self.id = _Id(project_id)
        self.novel_id = _Id(novel_id)


class _FakeProjectRepo:
    def __init__(self, project):
        self.project = project
        self.deleted = []

    def find_by_id(self, _project_id):
        return self.project

    def delete(self, project_id):
        self.deleted.append(str(project_id))


class _FakeNovelRepo:
    def __init__(self):
        self.deleted = []

    def delete(self, novel_id):
        self.deleted.append(str(novel_id))


def _setup_tables(db_path: str, project_id: str, novel_id: str):
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS novels (id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, novel_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS chapters (id TEXT PRIMARY KEY, novel_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS organize_jobs (novel_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS chapter_tasks (id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS plot_arcs (arc_id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS chapter_arc_bindings (id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS project_memories (id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS memory_views (id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS style_requirements (id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS chapter_outlines (id TEXT PRIMARY KEY, chapter_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS arc_progress_snapshots (snapshot_id TEXT PRIMARY KEY, arc_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS organize_batch_digests (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS organize_stage_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS outline_documents (id TEXT PRIMARY KEY, novel_id TEXT)")
        conn.execute("INSERT INTO chapters (id, novel_id) VALUES (?, ?)", ("ch_1", novel_id))
        conn.execute("INSERT INTO organize_jobs (novel_id) VALUES (?)", (novel_id,))
        conn.execute("INSERT INTO chapter_tasks (id, project_id) VALUES (?, ?)", ("task_1", project_id))
        conn.execute("INSERT INTO plot_arcs (arc_id, project_id) VALUES (?, ?)", ("arc_1", project_id))
        conn.execute("INSERT INTO chapter_arc_bindings (id, project_id) VALUES (?, ?)", ("bind_1", project_id))
        conn.execute("INSERT INTO project_memories (id, project_id) VALUES (?, ?)", ("mem_1", project_id))
        conn.execute("INSERT INTO memory_views (id, project_id) VALUES (?, ?)", ("view_1", project_id))
        conn.execute("INSERT INTO style_requirements (id, project_id) VALUES (?, ?)", ("style_1", project_id))
        conn.execute("INSERT INTO chapter_outlines (id, chapter_id) VALUES (?, ?)", ("outline_1", "ch_1"))
        conn.execute("INSERT INTO chapter_outlines (id, chapter_id) VALUES (?, ?)", ("outline_orphan", "ch_orphan"))
        conn.execute("INSERT INTO arc_progress_snapshots (snapshot_id, arc_id) VALUES (?, ?)", ("snap_1", "arc_1"))
        conn.execute("INSERT INTO organize_batch_digests (project_id) VALUES (?)", (project_id,))
        conn.execute("INSERT INTO organize_stage_metrics (project_id) VALUES (?)", (project_id,))
        conn.execute("INSERT INTO outline_documents (id, novel_id) VALUES (?, ?)", ("doc_1", novel_id))
        conn.commit()


def _count(conn, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def test_delete_project_cleans_related_rows():
    db_path = str(Path(tempfile.gettempdir()) / f"inktrace_cleanup_{uuid.uuid4().hex}.db")
    project_id = "proj_cleanup"
    novel_id = "nov_cleanup"
    _setup_tables(db_path, project_id, novel_id)

    project = _FakeProject(project_id, novel_id)
    project_repo = _FakeProjectRepo(project)
    novel_repo = _FakeNovelRepo()
    service = ProjectService(project_repo, novel_repo)

    old_db_path = os.environ.get("INKTRACE_DB_PATH")
    os.environ["INKTRACE_DB_PATH"] = db_path
    try:
        service.delete_project(ProjectId(project_id))
    finally:
        if old_db_path is None:
            os.environ.pop("INKTRACE_DB_PATH", None)
        else:
            os.environ["INKTRACE_DB_PATH"] = old_db_path

    with sqlite3.connect(db_path) as conn:
        assert _count(conn, "chapters") == 0
        assert _count(conn, "organize_jobs") == 0
        assert _count(conn, "chapter_tasks") == 0
        assert _count(conn, "plot_arcs") == 0
        assert _count(conn, "chapter_arc_bindings") == 0
        assert _count(conn, "project_memories") == 0
        assert _count(conn, "memory_views") == 0
        assert _count(conn, "style_requirements") == 0
        assert _count(conn, "chapter_outlines") == 0
        assert _count(conn, "arc_progress_snapshots") == 0
        assert _count(conn, "organize_batch_digests") == 0
        assert _count(conn, "organize_stage_metrics") == 0
        assert _count(conn, "outline_documents") == 0

    assert project_repo.deleted
    assert novel_repo.deleted == [novel_id]

    for _ in range(3):
        try:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)
            break
        except PermissionError:
            time.sleep(0.2)
