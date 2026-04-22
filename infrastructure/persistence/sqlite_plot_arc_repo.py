import json
import sqlite3
from datetime import datetime
from typing import List, Optional

from domain.entities.plot_arc import PlotArc
from domain.repositories.plot_arc_repository import IPlotArcRepository
from infrastructure.persistence.sqlite_utils import connect_sqlite


class SQLitePlotArcRepository(IPlotArcRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_table()

    def _init_table(self) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plot_arcs (
                    arc_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    arc_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    goal TEXT,
                    core_conflict TEXT,
                    stakes TEXT,
                    start_chapter_number INTEGER,
                    end_chapter_number INTEGER,
                    current_stage TEXT,
                    stage_reason TEXT,
                    stage_confidence REAL,
                    key_turning_points_json TEXT,
                    must_resolve_points_json TEXT,
                    related_characters_json TEXT,
                    related_items_json TEXT,
                    related_world_rules_json TEXT,
                    covered_chapter_ids_json TEXT,
                    latest_progress_summary TEXT,
                    latest_result TEXT,
                    next_push_suggestion TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plot_arcs_project_id ON plot_arcs(project_id)")
            conn.commit()

    def save(self, arc: PlotArc) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO plot_arcs (
                    arc_id, project_id, title, arc_type, priority, status, goal, core_conflict, stakes,
                    start_chapter_number, end_chapter_number, current_stage, stage_reason, stage_confidence,
                    key_turning_points_json, must_resolve_points_json, related_characters_json, related_items_json,
                    related_world_rules_json, covered_chapter_ids_json, latest_progress_summary, latest_result,
                    next_push_suggestion, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    arc.arc_id,
                    arc.project_id,
                    arc.title,
                    arc.arc_type,
                    arc.priority,
                    arc.status,
                    arc.goal,
                    arc.core_conflict,
                    arc.stakes,
                    int(arc.start_chapter_number or 0),
                    int(arc.end_chapter_number or 0),
                    arc.current_stage,
                    arc.stage_reason,
                    float(arc.stage_confidence or 0.0),
                    json.dumps(arc.key_turning_points, ensure_ascii=False),
                    json.dumps(arc.must_resolve_points, ensure_ascii=False),
                    json.dumps(arc.related_characters, ensure_ascii=False),
                    json.dumps(arc.related_items, ensure_ascii=False),
                    json.dumps(arc.related_world_rules, ensure_ascii=False),
                    json.dumps(arc.covered_chapter_ids, ensure_ascii=False),
                    arc.latest_progress_summary,
                    arc.latest_result,
                    arc.next_push_suggestion,
                    arc.created_at.isoformat(),
                    arc.updated_at.isoformat(),
                ),
            )
            conn.commit()

    def find_by_project(self, project_id: str) -> List[PlotArc]:
        with connect_sqlite(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM plot_arcs WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def find_by_id(self, arc_id: str) -> Optional[PlotArc]:
        with connect_sqlite(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM plot_arcs WHERE arc_id = ?", (arc_id,)).fetchone()
        return self._row_to_entity(row) if row else None

    def delete_by_project(self, project_id: str) -> None:
        with connect_sqlite(self.db_path) as conn:
            conn.execute("DELETE FROM plot_arcs WHERE project_id = ?", (project_id,))
            conn.commit()

    def _row_to_entity(self, row: sqlite3.Row) -> PlotArc:
        return PlotArc(
            arc_id=row["arc_id"],
            project_id=row["project_id"],
            title=row["title"] or "",
            arc_type=row["arc_type"] or "supporting_arc",
            priority=row["priority"] or "minor",
            status=row["status"] or "active",
            goal=row["goal"] or "",
            core_conflict=row["core_conflict"] or "",
            stakes=row["stakes"] or "",
            start_chapter_number=int(row["start_chapter_number"] or 0),
            end_chapter_number=int(row["end_chapter_number"] or 0),
            current_stage=row["current_stage"] or "setup",
            stage_reason=row["stage_reason"] or "",
            stage_confidence=float(row["stage_confidence"] or 0.6),
            key_turning_points=json.loads(row["key_turning_points_json"] or "[]"),
            must_resolve_points=json.loads(row["must_resolve_points_json"] or "[]"),
            related_characters=json.loads(row["related_characters_json"] or "[]"),
            related_items=json.loads(row["related_items_json"] or "[]"),
            related_world_rules=json.loads(row["related_world_rules_json"] or "[]"),
            covered_chapter_ids=json.loads(row["covered_chapter_ids_json"] or "[]"),
            latest_progress_summary=row["latest_progress_summary"] or "",
            latest_result=row["latest_result"] or "",
            next_push_suggestion=row["next_push_suggestion"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )
