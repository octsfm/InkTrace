"""
v2 重构版仓储实现（SQLite）。

职责：
- 初始化 v2 schema
- 提供 project_memories / memory_views / story_branches / chapter_plans / writing_sessions / workflow_jobs 的持久化能力
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional


class SQLiteV2Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        row = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        names = {item["name"] for item in row}
        if column_name not in names:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def _init_schema(self) -> None:
        schema_path = Path(__file__).resolve().parents[2] / "backend" / "src" / "infrastructure" / "persistence" / "sqlite" / "schema_v2.sql"
        if not schema_path.exists():
            schema_path = Path(__file__).resolve().parents[3] / "backend" / "src" / "infrastructure" / "persistence" / "sqlite" / "schema_v2.sql"
        if not schema_path.exists():
            return
        with self._connect() as conn:
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            self._ensure_column(conn, "project_memories", "global_constraints_json", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "project_memories", "chapter_analysis_memories_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "project_memories", "chapter_continuation_memories_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "project_memories", "chapter_tasks_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "project_memories", "structural_drafts_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "project_memories", "detemplated_drafts_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "project_memories", "draft_integrity_checks_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "project_memories", "style_requirements_json", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "chapter_plans", "chapter_id", "TEXT DEFAULT ''")
            self._ensure_column(conn, "chapter_plans", "chapter_function", "TEXT DEFAULT ''")
            self._ensure_column(conn, "chapter_plans", "goals_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "chapter_plans", "must_continue_points_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "chapter_plans", "forbidden_jumps_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "chapter_plans", "required_foreshadowing_action", "TEXT DEFAULT ''")
            self._ensure_column(conn, "chapter_plans", "required_hook_strength", "TEXT DEFAULT ''")
            self._ensure_column(conn, "chapter_plans", "pace_target", "TEXT DEFAULT ''")
            self._ensure_column(conn, "chapter_plans", "opening_continuation", "TEXT DEFAULT ''")
            self._ensure_column(conn, "chapter_plans", "chapter_payoff", "TEXT DEFAULT ''")
            self._ensure_column(conn, "chapter_plans", "style_bias", "TEXT DEFAULT ''")
            conn.commit()

    def save_project_memory(self, payload: Dict[str, Any]) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute("UPDATE project_memories SET is_active=0 WHERE project_id=?", (payload["project_id"],))
            conn.execute(
                """
                INSERT INTO project_memories (
                  id, project_id, version, characters_json, world_facts_json, plot_arcs_json,
                  events_json, style_profile_json, outline_context_json, current_state_json,
                  chapter_summaries_json, continuity_flags_json, global_constraints_json,
                  chapter_analysis_memories_json, chapter_continuation_memories_json, chapter_tasks_json,
                  structural_drafts_json, detemplated_drafts_json, draft_integrity_checks_json, style_requirements_json,
                  is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    payload["id"],
                    payload["project_id"],
                    int(payload.get("version") or 1),
                    json.dumps(payload.get("characters") or [], ensure_ascii=False),
                    json.dumps(payload.get("world_facts") or {}, ensure_ascii=False),
                    json.dumps(payload.get("plot_arcs") or [], ensure_ascii=False),
                    json.dumps(payload.get("events") or [], ensure_ascii=False),
                    json.dumps(payload.get("style_profile") or {}, ensure_ascii=False),
                    json.dumps(payload.get("outline_context") or {}, ensure_ascii=False),
                    json.dumps(payload.get("current_state") or {}, ensure_ascii=False),
                    json.dumps(payload.get("chapter_summaries") or [], ensure_ascii=False),
                    json.dumps(payload.get("continuity_flags") or [], ensure_ascii=False),
                    json.dumps(payload.get("global_constraints") or {}, ensure_ascii=False),
                    json.dumps(payload.get("chapter_analysis_memories") or [], ensure_ascii=False),
                    json.dumps(payload.get("chapter_continuation_memories") or [], ensure_ascii=False),
                    json.dumps(payload.get("chapter_tasks") or [], ensure_ascii=False),
                    json.dumps(payload.get("structural_drafts") or [], ensure_ascii=False),
                    json.dumps(payload.get("detemplated_drafts") or [], ensure_ascii=False),
                    json.dumps(payload.get("draft_integrity_checks") or [], ensure_ascii=False),
                    json.dumps(payload.get("style_requirements") or {}, ensure_ascii=False),
                    now,
                ),
            )
            conn.commit()

    def find_active_project_memory(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM project_memories WHERE project_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "project_id": row["project_id"],
                "version": row["version"],
                "characters": json.loads(row["characters_json"] or "[]"),
                "world_facts": json.loads(row["world_facts_json"] or "{}"),
                "plot_arcs": json.loads(row["plot_arcs_json"] or "[]"),
                "events": json.loads(row["events_json"] or "[]"),
                "style_profile": json.loads(row["style_profile_json"] or "{}"),
                "outline_context": json.loads(row["outline_context_json"] or "{}"),
                "current_state": json.loads(row["current_state_json"] or "{}"),
                "chapter_summaries": json.loads(row["chapter_summaries_json"] or "[]"),
                "continuity_flags": json.loads(row["continuity_flags_json"] or "[]"),
                "global_constraints": json.loads(row["global_constraints_json"] or "{}"),
                "chapter_analysis_memories": json.loads(row["chapter_analysis_memories_json"] or "[]"),
                "chapter_continuation_memories": json.loads(row["chapter_continuation_memories_json"] or "[]"),
                "chapter_tasks": json.loads(row["chapter_tasks_json"] or "[]"),
                "structural_drafts": json.loads(row["structural_drafts_json"] or "[]"),
                "detemplated_drafts": json.loads(row["detemplated_drafts_json"] or "[]"),
                "draft_integrity_checks": json.loads(row["draft_integrity_checks_json"] or "[]"),
                "style_requirements": json.loads(row["style_requirements_json"] or "{}"),
            }

    def save_memory_view(self, payload: Dict[str, Any]) -> None:
        now = self._now()
        with self._connect() as conn:
            exists = conn.execute("SELECT id FROM memory_views WHERE project_id=?", (payload["project_id"],)).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE memory_views SET
                      memory_id=?, main_characters_json=?, world_summary_json=?, main_plot_lines_json=?,
                      style_tags_json=?, current_progress=?, outline_summary_json=?, updated_at=?
                    WHERE project_id=?
                    """,
                    (
                        payload["memory_id"],
                        json.dumps(payload.get("main_characters") or [], ensure_ascii=False),
                        json.dumps(payload.get("world_summary") or [], ensure_ascii=False),
                        json.dumps(payload.get("main_plot_lines") or [], ensure_ascii=False),
                        json.dumps(payload.get("style_tags") or [], ensure_ascii=False),
                        payload.get("current_progress") or "",
                        json.dumps(payload.get("outline_summary") or [], ensure_ascii=False),
                        now,
                        payload["project_id"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO memory_views (
                      id, project_id, memory_id, main_characters_json, world_summary_json,
                      main_plot_lines_json, style_tags_json, current_progress, outline_summary_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["id"],
                        payload["project_id"],
                        payload["memory_id"],
                        json.dumps(payload.get("main_characters") or [], ensure_ascii=False),
                        json.dumps(payload.get("world_summary") or [], ensure_ascii=False),
                        json.dumps(payload.get("main_plot_lines") or [], ensure_ascii=False),
                        json.dumps(payload.get("style_tags") or [], ensure_ascii=False),
                        payload.get("current_progress") or "",
                        json.dumps(payload.get("outline_summary") or [], ensure_ascii=False),
                        now,
                        now,
                    ),
                )
            conn.commit()

    def find_memory_view(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memory_views WHERE project_id=? LIMIT 1", (project_id,)).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "project_id": row["project_id"],
                "memory_id": row["memory_id"],
                "main_characters": json.loads(row["main_characters_json"] or "[]"),
                "world_summary": json.loads(row["world_summary_json"] or "[]"),
                "main_plot_lines": json.loads(row["main_plot_lines_json"] or "[]"),
                "style_tags": json.loads(row["style_tags_json"] or "[]"),
                "current_progress": row["current_progress"] or "",
                "outline_summary": json.loads(row["outline_summary_json"] or "[]"),
            }

    def replace_branches(self, project_id: str, branches: List[Dict[str, Any]]) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute("DELETE FROM story_branches WHERE project_id=?", (project_id,))
            for item in branches:
                conn.execute(
                    """
                    INSERT INTO story_branches (
                      id, project_id, title, summary, core_conflict, key_progressions_json,
                      related_characters_json, style_tags_json, consistency_note, risk_note, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["id"],
                        project_id,
                        item.get("title") or "",
                        item.get("summary") or "",
                        item.get("core_conflict") or "",
                        json.dumps(item.get("key_progressions") or [], ensure_ascii=False),
                        json.dumps(item.get("related_characters") or [], ensure_ascii=False),
                        json.dumps(item.get("style_tags") or [], ensure_ascii=False),
                        item.get("consistency_note") or "",
                        item.get("risk_note") or "",
                        item.get("status") or "candidate",
                        now,
                        now,
                    ),
                )
            conn.commit()

    def list_branches(self, project_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM story_branches WHERE project_id=? ORDER BY created_at ASC", (project_id,)).fetchall()
            return [
                {
                    "id": row["id"],
                    "project_id": row["project_id"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "core_conflict": row["core_conflict"],
                    "key_progressions": json.loads(row["key_progressions_json"] or "[]"),
                    "related_characters": json.loads(row["related_characters_json"] or "[]"),
                    "style_tags": json.loads(row["style_tags_json"] or "[]"),
                    "consistency_note": row["consistency_note"] or "",
                    "risk_note": row["risk_note"] or "",
                    "status": row["status"] or "candidate",
                }
                for row in rows
            ]

    def replace_plans(self, project_id: str, plans: List[Dict[str, Any]]) -> None:
        now = self._now()
        with self._connect() as conn:
            if plans:
                branch_id = plans[0].get("branch_id") or ""
                conn.execute("DELETE FROM chapter_plans WHERE project_id=? AND branch_id=?", (project_id, branch_id))
            for item in plans:
                conn.execute(
                    """
                    INSERT INTO chapter_plans (
                      id, project_id, branch_id, chapter_number, title, goal, conflict, progression,
                      ending_hook, target_words, related_arc_ids_json, chapter_id, chapter_function, goals_json,
                      must_continue_points_json, forbidden_jumps_json, required_foreshadowing_action, required_hook_strength,
                      pace_target, opening_continuation, chapter_payoff, style_bias, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["id"],
                        project_id,
                        item.get("branch_id") or "",
                        int(item.get("chapter_number") or 0),
                        item.get("title") or "",
                        item.get("goal") or "",
                        item.get("conflict") or "",
                        item.get("progression") or "",
                        item.get("ending_hook") or "",
                        int(item.get("target_words") or 2500),
                        json.dumps(item.get("related_arc_ids") or [], ensure_ascii=False),
                        item.get("chapter_id") or "",
                        item.get("chapter_function") or "",
                        json.dumps(item.get("goals") or [], ensure_ascii=False),
                        json.dumps(item.get("must_continue_points") or [], ensure_ascii=False),
                        json.dumps(item.get("forbidden_jumps") or [], ensure_ascii=False),
                        item.get("required_foreshadowing_action") or "",
                        item.get("required_hook_strength") or "",
                        item.get("pace_target") or "",
                        item.get("opening_continuation") or "",
                        item.get("chapter_payoff") or "",
                        item.get("style_bias") or "",
                        item.get("status") or "pending",
                        now,
                        now,
                    ),
                )
            conn.commit()

    def find_plans(self, project_id: str, plan_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if plan_ids:
                marks = ",".join(["?"] * len(plan_ids))
                rows = conn.execute(
                    f"SELECT * FROM chapter_plans WHERE project_id=? AND id IN ({marks}) ORDER BY chapter_number ASC",
                    (project_id, *plan_ids),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM chapter_plans WHERE project_id=? ORDER BY chapter_number ASC",
                    (project_id,),
                ).fetchall()
            return [
                {
                    "id": row["id"],
                    "project_id": row["project_id"],
                    "branch_id": row["branch_id"],
                    "chapter_number": row["chapter_number"],
                    "title": row["title"] or "",
                    "goal": row["goal"] or "",
                    "conflict": row["conflict"] or "",
                    "progression": row["progression"] or "",
                    "ending_hook": row["ending_hook"] or "",
                    "target_words": row["target_words"] or 2500,
                    "related_arc_ids": json.loads(row["related_arc_ids_json"] or "[]"),
                    "chapter_id": row["chapter_id"] or "",
                    "chapter_function": row["chapter_function"] or "",
                    "goals": json.loads(row["goals_json"] or "[]"),
                    "must_continue_points": json.loads(row["must_continue_points_json"] or "[]"),
                    "forbidden_jumps": json.loads(row["forbidden_jumps_json"] or "[]"),
                    "required_foreshadowing_action": row["required_foreshadowing_action"] or "",
                    "required_hook_strength": row["required_hook_strength"] or "",
                    "pace_target": row["pace_target"] or "",
                    "opening_continuation": row["opening_continuation"] or "",
                    "chapter_payoff": row["chapter_payoff"] or "",
                    "style_bias": row["style_bias"] or "",
                    "status": row["status"] or "pending",
                }
                for row in rows
            ]

    def start_workflow_job(self, project_id: str, workflow_type: str, input_payload: Dict[str, Any]) -> str:
        job_id = f"wf_{os.urandom(6).hex()}"
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_jobs (id, project_id, workflow_type, status, input_json, result_json, error_message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, project_id, workflow_type, "running", json.dumps(input_payload, ensure_ascii=False), "", "", now, now),
            )
            conn.commit()
        return job_id

    def finish_workflow_job(
        self,
        job_id: str,
        status: str,
        result_payload: Optional[Dict[str, Any]] = None,
        error_message: str = "",
    ) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE workflow_jobs SET status=?, result_json=?, error_message=?, updated_at=? WHERE id=?",
                (status, json.dumps(result_payload or {}, ensure_ascii=False), error_message, now, job_id),
            )
            conn.commit()

    def list_workflow_jobs(self, project_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM workflow_jobs WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                (project_id, int(limit)),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "project_id": row["project_id"],
                    "workflow_type": row["workflow_type"],
                    "status": row["status"],
                    "input": json.loads(row["input_json"] or "{}"),
                    "result": json.loads(row["result_json"] or "{}"),
                    "error_message": row["error_message"] or "",
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    def get_workflow_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM workflow_jobs WHERE id=? LIMIT 1", (job_id,)).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "project_id": row["project_id"],
                "workflow_type": row["workflow_type"],
                "status": row["status"],
                "input": json.loads(row["input_json"] or "{}"),
                "result": json.loads(row["result_json"] or "{}"),
                "error_message": row["error_message"] or "",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    def start_writing_session(self, project_id: str, branch_id: str, plan_ids: List[str]) -> str:
        session_id = f"ws_{os.urandom(6).hex()}"
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO writing_sessions (
                  id, project_id, branch_id, status, plan_ids_json, generated_chapter_ids_json,
                  started_at, finished_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    project_id,
                    branch_id,
                    "running",
                    json.dumps(plan_ids or [], ensure_ascii=False),
                    json.dumps([], ensure_ascii=False),
                    now,
                    "",
                    now,
                    now,
                ),
            )
            conn.commit()
        return session_id

    def finish_writing_session(self, session_id: str, status: str, generated_chapter_ids: List[str]) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE writing_sessions
                SET status=?, generated_chapter_ids_json=?, finished_at=?, updated_at=?
                WHERE id=?
                """,
                (status, json.dumps(generated_chapter_ids or [], ensure_ascii=False), now, now, session_id),
            )
            conn.commit()

    def list_writing_sessions(self, project_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM writing_sessions WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                (project_id, int(limit)),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "project_id": row["project_id"],
                    "branch_id": row["branch_id"] or "",
                    "status": row["status"] or "",
                    "plan_ids": json.loads(row["plan_ids_json"] or "[]"),
                    "generated_chapter_ids": json.loads(row["generated_chapter_ids_json"] or "[]"),
                    "started_at": row["started_at"] or "",
                    "finished_at": row["finished_at"] or "",
                    "created_at": row["created_at"] or "",
                    "updated_at": row["updated_at"] or "",
                }
                for row in rows
            ]

    def get_writing_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM writing_sessions WHERE id=? LIMIT 1", (session_id,)).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "project_id": row["project_id"],
                "branch_id": row["branch_id"] or "",
                "status": row["status"] or "",
                "plan_ids": json.loads(row["plan_ids_json"] or "[]"),
                "generated_chapter_ids": json.loads(row["generated_chapter_ids_json"] or "[]"),
                "started_at": row["started_at"] or "",
                "finished_at": row["finished_at"] or "",
                "created_at": row["created_at"] or "",
                "updated_at": row["updated_at"] or "",
            }
