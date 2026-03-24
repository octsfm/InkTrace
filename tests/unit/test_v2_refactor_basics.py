from __future__ import annotations

import tempfile
import os

from application.dto.request_dto import ImportNovelRequest
from infrastructure.persistence.sqlite_v2_repo import SQLiteV2Repository


def test_import_request_contains_outline_path():
    req = ImportNovelRequest(
        novel_id="novel_1",
        file_path="d:/tmp/a.txt",
        outline_path="d:/tmp/outline.txt",
    )
    assert req.outline_path == "d:/tmp/outline.txt"


def test_v2_repo_memory_persistence():
    fd, db_file = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        repo = SQLiteV2Repository(db_file)
        memory = {
            "id": "memory_001",
            "project_id": "proj_001",
            "version": 1,
            "characters": [{"name": "孔凡圣"}],
            "world_facts": {"facts": ["现代都市与修真世界并存"]},
            "plot_arcs": [],
            "events": [{"summary": "主角暴露异常能力"}],
            "style_profile": {"tone": "紧张"},
            "outline_context": {"summary": ["中期进入宗门线"]},
            "current_state": {"latest_summary": "主角已接触核心势力外围"},
            "chapter_summaries": ["第87章：风起幽月潭"],
            "continuity_flags": [],
        }
        repo.save_project_memory(memory)
        loaded = repo.find_active_project_memory("proj_001")
        assert loaded is not None
        assert loaded["project_id"] == "proj_001"
        assert loaded["characters"][0]["name"] == "孔凡圣"
        assert loaded["world_facts"]["facts"][0] == "现代都市与修真世界并存"
    finally:
        try:
            os.remove(db_file)
        except OSError:
            pass


def test_v2_repo_memory_view_persistence():
    fd, db_file = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        repo = SQLiteV2Repository(db_file)
        view = {
            "id": "view_001",
            "project_id": "proj_001",
            "memory_id": "memory_001",
            "main_characters": [{"name": "孔凡圣", "role": "主角", "traits": "谨慎、理性"}],
            "world_summary": ["现代都市与修真世界并存"],
            "main_plot_lines": ["主角逐步卷入修真世界"],
            "style_tags": ["第三人称有限视角", "紧张写实"],
            "current_progress": "主角已接触核心势力外围",
            "outline_summary": ["中期进入宗门线"],
        }
        repo.save_memory_view(view)
        loaded = repo.find_memory_view("proj_001")
        assert loaded is not None
        assert loaded["memory_id"] == "memory_001"
        assert loaded["main_characters"][0]["name"] == "孔凡圣"
        assert loaded["current_progress"] == "主角已接触核心势力外围"
    finally:
        try:
            os.remove(db_file)
        except OSError:
            pass


def test_v2_repo_workflow_and_session_persistence():
    fd, db_file = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        repo = SQLiteV2Repository(db_file)
        job_id = repo.start_workflow_job("proj_001", "organize_novel", {"mode": "chapter_first"})
        repo.finish_workflow_job(job_id, "success", {"organized_chapter_count": 12})
        session_id = repo.start_writing_session("proj_001", "branch_001", ["plan_1", "plan_2"])
        repo.finish_writing_session(session_id, "finished", ["chap_101", "chap_102"])
    finally:
        try:
            os.remove(db_file)
        except OSError:
            pass
