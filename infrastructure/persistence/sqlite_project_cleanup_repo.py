from __future__ import annotations

from typing import List

from domain.repositories.project_cleanup_repository import IProjectCleanupRepository
from infrastructure.persistence.sqlite_utils import connect_sqlite


class SQLiteProjectCleanupRepository(IProjectCleanupRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def cleanup_project_payloads(self, project_id: str, novel_id: str) -> None:
        chapter_ids: List[str] = []
        arc_ids: List[str] = []
        with connect_sqlite(self.db_path) as conn:
            conn.row_factory = None

            def _table_exists(name: str) -> bool:
                row = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                    (name,),
                ).fetchone()
                return bool(row)

            def _table_has_column(table: str, column: str) -> bool:
                if not _table_exists(table):
                    return False
                rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
                return any(str(item[1]) == column for item in rows if len(item) > 1)

            def _execute_if_exists(table: str, sql: str, params: tuple = ()) -> None:
                if _table_exists(table):
                    conn.execute(sql, params)

            if _table_exists("chapters"):
                rows = conn.execute("SELECT id FROM chapters WHERE novel_id = ?", (novel_id,)).fetchall()
                chapter_ids = [str(item[0]) for item in rows if item and item[0]]
            if _table_exists("plot_arcs"):
                rows = conn.execute("SELECT arc_id FROM plot_arcs WHERE project_id = ?", (project_id,)).fetchall()
                arc_ids = [str(item[0]) for item in rows if item and item[0]]

            chapter_marks = ",".join(["?"] * len(chapter_ids))
            arc_marks = ",".join(["?"] * len(arc_ids))

            _execute_if_exists("organize_jobs", "DELETE FROM organize_jobs WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("foreshadows", "DELETE FROM foreshadows WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("outlines", "DELETE FROM outlines WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("characters", "DELETE FROM characters WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("worldviews", "DELETE FROM worldviews WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("techniques", "DELETE FROM techniques WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("factions", "DELETE FROM factions WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("locations", "DELETE FROM locations WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("items", "DELETE FROM items WHERE novel_id = ?", (novel_id,))
            _execute_if_exists("chapter_tasks", "DELETE FROM chapter_tasks WHERE project_id = ?", (project_id,))
            _execute_if_exists("global_constraints", "DELETE FROM global_constraints WHERE project_id = ?", (project_id,))
            _execute_if_exists("continuation_context_snapshots", "DELETE FROM continuation_context_snapshots WHERE project_id = ?", (project_id,))
            _execute_if_exists("project_memories", "DELETE FROM project_memories WHERE project_id = ?", (project_id,))
            _execute_if_exists("memory_views", "DELETE FROM memory_views WHERE project_id = ?", (project_id,))
            _execute_if_exists("organize_batch_digests", "DELETE FROM organize_batch_digests WHERE project_id = ?", (project_id,))
            _execute_if_exists("organize_stage_metrics", "DELETE FROM organize_stage_metrics WHERE project_id = ?", (project_id,))
            _execute_if_exists("story_branches", "DELETE FROM story_branches WHERE project_id = ?", (project_id,))
            _execute_if_exists("chapter_plans", "DELETE FROM chapter_plans WHERE project_id = ?", (project_id,))
            _execute_if_exists("workflow_jobs", "DELETE FROM workflow_jobs WHERE project_id = ?", (project_id,))
            _execute_if_exists("writing_sessions", "DELETE FROM writing_sessions WHERE project_id = ?", (project_id,))
            _execute_if_exists("chapter_arc_bindings", "DELETE FROM chapter_arc_bindings WHERE project_id = ?", (project_id,))
            _execute_if_exists("plot_arcs", "DELETE FROM plot_arcs WHERE project_id = ?", (project_id,))
            _execute_if_exists("outline_documents", "DELETE FROM outline_documents WHERE novel_id = ?", (novel_id,))
            if _table_exists("style_requirements"):
                if _table_has_column("style_requirements", "project_id"):
                    conn.execute("DELETE FROM style_requirements WHERE project_id = ?", (project_id,))
                elif _table_has_column("style_requirements", "chapter_id") and chapter_ids:
                    conn.execute(f"DELETE FROM style_requirements WHERE chapter_id IN ({chapter_marks})", tuple(chapter_ids))

            if chapter_ids:
                if _table_exists("chapter_outlines"):
                    conn.execute(f"DELETE FROM chapter_outlines WHERE chapter_id IN ({chapter_marks})", tuple(chapter_ids))
                if _table_exists("chapter_analysis_memories"):
                    conn.execute(f"DELETE FROM chapter_analysis_memories WHERE chapter_id IN ({chapter_marks})", tuple(chapter_ids))
                if _table_exists("chapter_continuation_memories"):
                    conn.execute(f"DELETE FROM chapter_continuation_memories WHERE chapter_id IN ({chapter_marks})", tuple(chapter_ids))
                if _table_exists("structural_drafts"):
                    conn.execute(f"DELETE FROM structural_drafts WHERE chapter_id IN ({chapter_marks})", tuple(chapter_ids))
                if _table_exists("detemplated_drafts"):
                    conn.execute(f"DELETE FROM detemplated_drafts WHERE chapter_id IN ({chapter_marks})", tuple(chapter_ids))
                if _table_exists("draft_integrity_checks"):
                    conn.execute(f"DELETE FROM draft_integrity_checks WHERE chapter_id IN ({chapter_marks})", tuple(chapter_ids))
                if _table_exists("chapters"):
                    conn.execute(f"DELETE FROM chapters WHERE id IN ({chapter_marks})", tuple(chapter_ids))
            else:
                _execute_if_exists("chapters", "DELETE FROM chapters WHERE novel_id = ?", (novel_id,))

            if arc_ids and _table_exists("arc_progress_snapshots"):
                conn.execute(f"DELETE FROM arc_progress_snapshots WHERE arc_id IN ({arc_marks})", tuple(arc_ids))

            # Best-effort orphan governance to prevent stale derived rows from causing future delete failures.
            if _table_exists("chapter_outlines") and _table_exists("chapters"):
                conn.execute("DELETE FROM chapter_outlines WHERE chapter_id NOT IN (SELECT id FROM chapters)")
            if _table_exists("chapter_analysis_memories") and _table_exists("chapters"):
                conn.execute("DELETE FROM chapter_analysis_memories WHERE chapter_id NOT IN (SELECT id FROM chapters)")
            if _table_exists("chapter_continuation_memories") and _table_exists("chapters"):
                conn.execute("DELETE FROM chapter_continuation_memories WHERE chapter_id NOT IN (SELECT id FROM chapters)")
            if _table_exists("style_requirements") and _table_has_column("style_requirements", "chapter_id") and _table_exists("chapters"):
                conn.execute("DELETE FROM style_requirements WHERE chapter_id IS NOT NULL AND chapter_id NOT IN (SELECT id FROM chapters)")
            if _table_exists("chapter_tasks") and _table_exists("projects"):
                conn.execute("DELETE FROM chapter_tasks WHERE project_id NOT IN (SELECT id FROM projects)")
            if _table_exists("plot_arcs") and _table_exists("projects"):
                conn.execute("DELETE FROM plot_arcs WHERE project_id NOT IN (SELECT id FROM projects)")
            if _table_exists("chapter_arc_bindings") and _table_exists("projects"):
                conn.execute("DELETE FROM chapter_arc_bindings WHERE project_id NOT IN (SELECT id FROM projects)")
            if _table_exists("arc_progress_snapshots") and _table_exists("plot_arcs"):
                conn.execute("DELETE FROM arc_progress_snapshots WHERE arc_id NOT IN (SELECT arc_id FROM plot_arcs)")
            conn.commit()
