from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _count(conn, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    return int(row[0] if row else 0)


def collect_orphan_stats(db_path: str) -> Dict[str, int]:
    with sqlite3.connect(db_path, timeout=10.0) as conn:
        return {
            "chapters_orphan_by_novel": _count(
                conn,
                "SELECT COUNT(*) FROM chapters c LEFT JOIN novels n ON n.id = c.novel_id WHERE n.id IS NULL",
            ),
            "organize_jobs_orphan_by_novel": _count(
                conn,
                "SELECT COUNT(*) FROM organize_jobs j LEFT JOIN novels n ON n.id = j.novel_id WHERE n.id IS NULL",
            ),
            "chapter_tasks_orphan_by_project": _count(
                conn,
                "SELECT COUNT(*) FROM chapter_tasks t LEFT JOIN projects p ON p.id = t.project_id WHERE p.id IS NULL",
            ),
            "plot_arcs_orphan_by_project": _count(
                conn,
                "SELECT COUNT(*) FROM plot_arcs a LEFT JOIN projects p ON p.id = a.project_id WHERE p.id IS NULL",
            ),
            "chapter_arc_bindings_orphan_by_project": _count(
                conn,
                "SELECT COUNT(*) FROM chapter_arc_bindings b LEFT JOIN projects p ON p.id = b.project_id WHERE p.id IS NULL",
            ),
        }


def clean_orphans(db_path: str) -> None:
    with sqlite3.connect(db_path, timeout=10.0) as conn:
        conn.execute("DELETE FROM chapters WHERE novel_id NOT IN (SELECT id FROM novels)")
        conn.execute("DELETE FROM organize_jobs WHERE novel_id NOT IN (SELECT id FROM novels)")
        conn.execute("DELETE FROM chapter_tasks WHERE project_id NOT IN (SELECT id FROM projects)")
        conn.execute("DELETE FROM plot_arcs WHERE project_id NOT IN (SELECT id FROM projects)")
        conn.execute("DELETE FROM chapter_arc_bindings WHERE project_id NOT IN (SELECT id FROM projects)")
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and optionally clean orphan rows in InkTrace SQLite database.")
    parser.add_argument("--db-path", default=os.environ.get("INKTRACE_DB_PATH", "data/inktrace.db"))
    parser.add_argument("--clean", action="store_true", help="Delete orphan rows after reporting")
    args = parser.parse_args()

    before = collect_orphan_stats(args.db_path)
    print("[ORPHAN REPORT] before")
    for key, value in before.items():
        print(f"  {key}: {value}")

    if args.clean:
        clean_orphans(args.db_path)
        after = collect_orphan_stats(args.db_path)
        print("[ORPHAN REPORT] after")
        for key, value in after.items():
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
