from infrastructure.persistence.sqlite_v2_repo import SQLiteV2Repository


def _build_memory_payload(project_id: str, memory_id: str, version: int):
    return {
        "id": memory_id,
        "project_id": project_id,
        "version": version,
        "characters": [{"name": "主角"}],
        "world_facts": {"background": ["规则A"]},
        "plot_arcs": [],
        "events": [{"event": "冲突"}],
        "style_profile": {"narrative_pov": "第三人称"},
        "outline_context": {"premise": "大纲前提"},
        "current_state": {"latest_summary": "进度"},
        "chapter_summaries": ["第1章摘要"],
        "continuity_flags": [],
    }


def test_project_memory_active_switch(tmp_path):
    db_path = str(tmp_path / "v2.sqlite3")
    repo = SQLiteV2Repository(db_path)
    repo.save_project_memory(_build_memory_payload("proj_1", "memory_1", 1))
    repo.save_project_memory(_build_memory_payload("proj_1", "memory_2", 2))
    active = repo.find_active_project_memory("proj_1")
    assert active is not None
    assert active["id"] == "memory_2"
    assert active["version"] == 2


def test_memory_view_upsert(tmp_path):
    db_path = str(tmp_path / "v2.sqlite3")
    repo = SQLiteV2Repository(db_path)
    payload = {
        "id": "view_1",
        "project_id": "proj_1",
        "memory_id": "memory_1",
        "main_characters": [{"name": "主角"}],
        "world_summary": ["世界A"],
        "main_plot_lines": ["主线A"],
        "style_tags": ["紧张"],
        "current_progress": "推进中",
        "outline_summary": ["大纲A"],
    }
    repo.save_memory_view(payload)
    payload["memory_id"] = "memory_2"
    payload["current_progress"] = "推进完成"
    repo.save_memory_view(payload)
    view = repo.find_memory_view("proj_1")
    assert view is not None
    assert view["memory_id"] == "memory_2"
    assert view["current_progress"] == "推进完成"


def test_workflow_job_and_writing_session_queries(tmp_path):
    db_path = str(tmp_path / "v2.sqlite3")
    repo = SQLiteV2Repository(db_path)
    job_id = repo.start_workflow_job("proj_1", "organize_novel", {"mode": "chapter_first"})
    repo.finish_workflow_job(job_id, "success", {"ok": True})
    jobs = repo.list_workflow_jobs("proj_1", 10)
    job = repo.get_workflow_job(job_id)
    assert len(jobs) == 1
    assert job is not None
    assert job["status"] == "success"
    session_id = repo.start_writing_session("proj_1", "branch_1", ["plan_1"])
    repo.finish_writing_session(session_id, "finished", ["chapter_1"])
    sessions = repo.list_writing_sessions("proj_1", 10)
    session = repo.get_writing_session(session_id)
    assert len(sessions) == 1
    assert session is not None
    assert session["status"] == "finished"
    assert session["generated_chapter_ids"] == ["chapter_1"]
