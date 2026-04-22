import sqlite3
import tempfile
import time
import uuid
from pathlib import Path

from infrastructure.persistence.sqlite_project_cleanup_repo import SQLiteProjectCleanupRepository


def _count(conn, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def test_cleanup_repo_deletes_style_requirements_with_project_id_schema():
    db_path = str(Path(tempfile.gettempdir()) / f"inktrace_cleanup_repo_{uuid.uuid4().hex}.db")
    project_id = "proj_cleanup_repo"
    novel_id = "nov_cleanup_repo"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS chapters (id TEXT PRIMARY KEY, novel_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS style_requirements (id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("INSERT INTO chapters (id, novel_id) VALUES (?, ?)", ("ch_1", novel_id))
        conn.execute("INSERT INTO style_requirements (id, project_id) VALUES (?, ?)", ("style_1", project_id))
        conn.commit()

    repo = SQLiteProjectCleanupRepository(db_path)
    repo.cleanup_project_payloads(project_id, novel_id)

    with sqlite3.connect(db_path) as conn:
        assert _count(conn, "chapters") == 0
        assert _count(conn, "style_requirements") == 0

    for _ in range(3):
        try:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)
            break
        except PermissionError:
            time.sleep(0.2)


def test_cleanup_repo_deletes_style_requirements_even_when_no_chapters():
    db_path = str(Path(tempfile.gettempdir()) / f"inktrace_cleanup_repo_{uuid.uuid4().hex}.db")
    project_id = "proj_cleanup_repo_empty"
    novel_id = "nov_cleanup_repo_empty"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS chapters (id TEXT PRIMARY KEY, novel_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS style_requirements (id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("INSERT INTO style_requirements (id, project_id) VALUES (?, ?)", ("style_1", project_id))
        conn.commit()

    repo = SQLiteProjectCleanupRepository(db_path)
    repo.cleanup_project_payloads(project_id, novel_id)

    with sqlite3.connect(db_path) as conn:
        assert _count(conn, "style_requirements") == 0

    for _ in range(3):
        try:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)
            break
        except PermissionError:
            time.sleep(0.2)


def test_cleanup_repo_cleans_project_metrics_and_orphans():
    db_path = str(Path(tempfile.gettempdir()) / f"inktrace_cleanup_repo_{uuid.uuid4().hex}.db")
    project_id = "proj_cleanup_repo_metrics"
    novel_id = "nov_cleanup_repo_metrics"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS novels (id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, novel_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS chapters (id TEXT PRIMARY KEY, novel_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS organize_batch_digests (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS organize_stage_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS chapter_tasks (id TEXT PRIMARY KEY, project_id TEXT)")
        conn.execute("INSERT INTO novels (id) VALUES (?)", (novel_id,))
        conn.execute("INSERT INTO projects (id, novel_id) VALUES (?, ?)", (project_id, novel_id))
        conn.execute("INSERT INTO chapters (id, novel_id) VALUES (?, ?)", ("ch_1", novel_id))
        conn.execute("INSERT INTO organize_batch_digests (project_id) VALUES (?)", (project_id,))
        conn.execute("INSERT INTO organize_stage_metrics (project_id) VALUES (?)", (project_id,))
        conn.execute("INSERT INTO chapter_tasks (id, project_id) VALUES (?, ?)", ("task_orphan", "missing_project"))
        conn.commit()

    repo = SQLiteProjectCleanupRepository(db_path)
    repo.cleanup_project_payloads(project_id, novel_id)

    with sqlite3.connect(db_path) as conn:
        assert _count(conn, "organize_batch_digests") == 0
        assert _count(conn, "organize_stage_metrics") == 0
        assert _count(conn, "chapter_tasks") == 0

    for _ in range(3):
        try:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)
            break
        except PermissionError:
            time.sleep(0.2)
