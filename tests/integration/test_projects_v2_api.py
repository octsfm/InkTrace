from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from presentation.api.app import app
from presentation.api.dependencies import get_v2_workflow_service


def _create_temp_novel_file() -> str:
    fd, path = tempfile.mkstemp(suffix=".txt")
    Path(path).write_text("第1章 开始\n主角出场。\n\n第2章 推进\n冲突升级。", encoding="utf-8")
    return path


class _FakeTool:
    def __init__(self, *_args, **_kwargs):
        pass

    async def execute_async(self, *_args, **_kwargs):
        return type("Result", (), {"status": "success", "payload": {"chapter_text": "第3章 追击\n主角继续追击，门后传来异响。"}})()


class _FakePromptAIService:
    async def extract_continuation_memory(self, *_args, **_kwargs):
        return {
            "scene_summary": "主角继续追击",
            "scene_state": {"time": "", "location": "", "environment": ""},
            "protagonist_state": {
                "name": "主角",
                "physical_state": "",
                "emotion_state": "紧张",
                "current_goal": "追查线索",
                "internal_tension": "",
            },
            "active_characters": ["主角"],
            "active_conflicts": ["门后异响"],
            "immediate_threads": ["门后异响"],
            "long_term_threads": [],
            "recent_reveals": [],
            "must_continue_points": ["门后异响"],
            "forbidden_jumps": [],
            "tone_and_pacing": {"tone": "紧张", "pace": "快"},
            "last_hook": "门后异响",
            "used_fallback": False,
        }

    async def analyze_to_outline(self, chapter_title, *_args, **_kwargs):
        return {
            "outline_draft": {
                "goal": f"推进{chapter_title}",
                "conflict": "冲突升级",
                "events": ["事件1", "事件2"],
                "character_progress": "主角进一步成长",
                "ending_hook": "埋下新的悬念",
                "opening_continuation": "承接上一章",
                "notes": "整理阶段自动生成",
            },
            "used_fallback": False,
        }

    async def generate_structural_draft(self, *_args, **_kwargs):
        return {
            "title": "门后追击",
            "content": "主角继续追击，门后传来异响。",
            "new_events": [],
            "possible_continuity_flags": [],
            "used_fallback": False,
        }

    async def generate_chapter_task(self, *_args, **_kwargs):
        return {
            "chapter_function": "continue_crisis",
            "goals": ["推进危机"],
            "must_continue_points": ["门后异响"],
            "forbidden_jumps": ["不得突然跳场"],
            "required_foreshadowing_action": "advance",
            "required_hook_strength": "medium",
            "pace_target": "fast",
            "opening_continuation": "紧接门后异响",
            "chapter_payoff": "门后异响升级",
            "style_bias": "fast",
            "used_fallback": False,
        }

    async def rewrite_detemplated_draft(self, structural_draft, *_args, **_kwargs):
        return {
            "title": structural_draft.get("title") or "门后追击",
            "content": structural_draft["content"] + "\n去模板改写版",
            "used_fallback": False,
            "integrity_failed": False,
            "display_fallback_to_structural": False,
        }

    async def check_draft_integrity(self, *_args, **_kwargs):
        return {
            "event_integrity_ok": True,
            "motivation_integrity_ok": True,
            "foreshadowing_integrity_ok": True,
            "hook_integrity_ok": True,
            "continuity_ok": True,
            "title_alignment_ok": True,
            "progression_integrity_ok": True,
            "risk_notes": [],
        }

    async def backfill_title(self, *_args, **_kwargs):
        return "门后追击"


def test_projects_v2_import_and_query_chain():
    client = TestClient(app)
    novel_path = _create_temp_novel_file()
    try:
        resp = client.post(
            "/api/projects/import",
            json={
                "project_name": "v2测试项目",
                "author": "测试作者",
                "genre": "xuanhuan",
                "novel_file_path": novel_path,
                "outline_file_path": "",
                "auto_organize": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"]
        assert data["novel_id"]

        project_id = data["project_id"]
        novel_id = data["novel_id"]

        by_novel = client.get(f"/api/projects/by-novel/{novel_id}")
        assert by_novel.status_code == 200
        assert by_novel.json()["id"] == project_id

        memory = client.get(f"/api/projects/{project_id}/memory")
        assert memory.status_code == 200
        assert memory.json()["project_id"] == project_id
        payload = memory.json().get("memory") or {}
        for key in [
            "global_constraints",
            "chapter_analysis_memory_refs",
            "chapter_continuation_memory_refs",
            "chapter_task_refs",
            "chapter_analysis_memories",
            "chapter_continuation_memories",
            "chapter_tasks",
            "structural_drafts",
            "detemplated_drafts",
            "draft_integrity_checks",
            "style_requirements",
        ]:
            assert key in payload

        view = client.get(f"/api/projects/{project_id}/memory-view")
        assert view.status_code == 200
        assert view.json()["project_id"] == project_id
        continuation_context = client.get(f"/api/projects/{project_id}/continuation-context")
        assert continuation_context.status_code == 200
        assert continuation_context.json()["project_id"] == project_id
        assert "global_constraints" in continuation_context.json()
        continuation_context_build = client.post(
            f"/api/projects/{project_id}/continuation-context/build",
            json={"project_id": project_id, "chapter_id": "chapter_seed", "branch_id": "", "chapter_plan_id": ""},
        )
        assert continuation_context_build.status_code == 200
        chapter_tasks = client.get(f"/api/projects/{project_id}/chapter-tasks")
        assert chapter_tasks.status_code == 200
        style = client.get(f"/api/projects/{project_id}/style-requirements")
        assert style.status_code == 200
        assert style.json()["project_id"] == project_id
        update_style = client.put(
            f"/api/projects/{project_id}/style-requirements",
            json={
                "author_voice_keywords": ["紧张", "克制"],
                "avoid_patterns": ["与此同时"],
                "preferred_rhythm": "中速节奏",
                "narrative_distance": "第三人称",
                "dialogue_density": "中",
            },
        )
        assert update_style.status_code == 200
        assert "style_requirements" in update_style.json()
        extract_style = client.post(
            f"/api/projects/{project_id}/style-requirements/extract",
            json={"sample_chapter_count": 2},
        )
        assert extract_style.status_code == 200
        assert extract_style.json().get("style_requirements") is not None
    finally:
        try:
            Path(novel_path).unlink(missing_ok=True)
        except Exception:
            pass


def test_import_with_organize_generates_chapter_outlines():
    original_provider = app.dependency_overrides.get(get_v2_workflow_service)
    novel_path = _create_temp_novel_file()

    def _override_workflow_service():
        service = get_v2_workflow_service()
        service.continue_writing_tool_cls = _FakeTool
        service.prompt_ai_service = _FakePromptAIService()
        return service

    app.dependency_overrides[get_v2_workflow_service] = _override_workflow_service
    client = TestClient(app)
    try:
        resp = client.post(
            "/api/projects/import",
            json={
                "project_name": "导入后自动大纲测试",
                "author": "测试作者",
                "genre": "xuanhuan",
                "novel_file_path": novel_path,
                "outline_file_path": "",
                "auto_organize": True,
            },
        )
        assert resp.status_code == 200
        novel_id = resp.json()["novel_id"]
        detail = client.get(f"/api/novels/{novel_id}")
        assert detail.status_code == 200
        first_chapter_id = detail.json()["chapters"][0]["id"]
        outline = client.get(f"/api/chapters/{first_chapter_id}/outline")
        assert outline.status_code == 200
        payload = outline.json()
        assert payload["goal"] == "推进开始"
        assert payload["opening_continuation"] == "承接上一章"
        assert payload["notes"] == "整理阶段自动生成"
    finally:
        try:
            Path(novel_path).unlink(missing_ok=True)
        except Exception:
            pass
        if original_provider:
            app.dependency_overrides[get_v2_workflow_service] = original_provider
        else:
            app.dependency_overrides.pop(get_v2_workflow_service, None)


def test_chapter_plan_generates_distinct_goals_and_hooks():
    original_provider = app.dependency_overrides.get(get_v2_workflow_service)
    novel_path = _create_temp_novel_file()

    def _override_workflow_service():
        service = get_v2_workflow_service()
        service.continue_writing_tool_cls = _FakeTool
        service.prompt_ai_service = _FakePromptAIService()
        return service

    app.dependency_overrides[get_v2_workflow_service] = _override_workflow_service
    client = TestClient(app)
    try:
        resp = client.post(
            "/api/projects/import",
            json={
                "project_name": "计划差异化测试",
                "author": "测试作者",
                "genre": "xuanhuan",
                "novel_file_path": novel_path,
                "outline_file_path": "",
                "auto_organize": True,
            },
        )
        assert resp.status_code == 200
        project_id = resp.json()["project_id"]
        branches = client.post(
            f"/api/projects/{project_id}/branches",
            json={"direction_hint": "推进主线并制造冲突", "branch_count": 4},
        )
        assert branches.status_code == 200
        branch_id = branches.json()["branches"][0]["id"]
        plan = client.post(
            f"/api/projects/{project_id}/chapter-plan",
            json={"branch_id": branch_id, "chapter_count": 3, "target_words_per_chapter": 1800},
        )
        assert plan.status_code == 200
        plans = plan.json().get("plans") or []
        assert len(plans) == 3
        titles = [str(item.get("title") or "") for item in plans]
        goals = [str(item.get("goal") or "") for item in plans]
        hooks = [str(item.get("ending_hook") or "") for item in plans]
        functions = [str((item.get("chapter_task_seed") or {}).get("chapter_function") or "") for item in plans]
        assert len(set(titles)) == 3
        assert len(set(goals)) >= 2
        assert len(set(hooks)) >= 2
        assert len(set(functions)) >= 2
    finally:
        try:
            Path(novel_path).unlink(missing_ok=True)
        except Exception:
            pass
        if original_provider:
            app.dependency_overrides[get_v2_workflow_service] = original_provider
        else:
            app.dependency_overrides.pop(get_v2_workflow_service, None)


def test_projects_v2_upload_and_trace_endpoints():
    client = TestClient(app)
    files = {
        "novel_file": ("novel.txt", "第1章 起始\n主角登场。", "text/plain"),
        "outline_file": ("outline.txt", "世界观：上古崩塌后重建秩序。", "text/plain"),
    }
    data = {
        "project_name": "上传链路测试",
        "author": "上传作者",
        "genre": "xuanhuan",
        "auto_organize": "false",
    }
    resp = client.post("/api/projects/import/upload", data=data, files=files)
    assert resp.status_code == 200
    payload = resp.json()
    project_id = payload["project_id"]
    trace = client.get(f"/api/projects/{project_id}/trace")
    assert trace.status_code == 200
    trace_payload = trace.json()
    assert trace_payload["project_id"] == project_id
    jobs = client.get(f"/api/projects/{project_id}/workflow-jobs")
    assert jobs.status_code == 200
    assert "workflow_jobs" in jobs.json()
    sessions = client.get(f"/api/projects/{project_id}/writing-sessions")
    assert sessions.status_code == 200
    assert "writing_sessions" in sessions.json()


def test_projects_v2_final_acceptance_chain():
    original_provider = app.dependency_overrides.get(get_v2_workflow_service)

    def _override_workflow_service():
        service = get_v2_workflow_service()
        service.continue_writing_tool_cls = _FakeTool
        service.prompt_ai_service = _FakePromptAIService()
        return service

    app.dependency_overrides[get_v2_workflow_service] = _override_workflow_service
    client = TestClient(app)
    try:
        files = {
            "novel_file": (
                "novel.txt",
                "第1章 初入\n主角进入古城并发现禁制。\n\n第2章 对峙\n主角与守城势力发生冲突并逃离。",
                "text/plain",
            ),
            "outline_file": (
                "outline.txt",
                "故事背景：古城封印松动，三方势力争夺核心遗物。\n世界观：灵纹体系决定力量上限，越级使用会反噬。",
                "text/plain",
            ),
        }
        upload = client.post(
            "/api/projects/import/upload",
            data={"project_name": "最终验收链路", "author": "验收作者", "genre": "xuanhuan", "auto_organize": "true"},
            files=files,
        )
        assert upload.status_code == 200
        imported = upload.json()
        project_id = imported["project_id"]
        novel_id = imported["novel_id"]
        organize = client.post(
            f"/api/projects/{project_id}/organize",
            json={"mode": "chapter_first", "rebuild_memory": True},
        )
        assert organize.status_code == 200
        branches = client.post(
            f"/api/projects/{project_id}/branches",
            json={"direction_hint": "沿大纲推进并放大古城冲突", "branch_count": 3},
        )
        assert branches.status_code == 200
        branch_payload = branches.json()
        assert len(branch_payload["branches"]) >= 3
        branch_id = branch_payload["branches"][0]["id"]
        plan = client.post(
            f"/api/projects/{project_id}/chapter-plan",
            json={"branch_id": branch_id, "chapter_count": 1, "target_words_per_chapter": 1200},
        )
        assert plan.status_code == 200
        plan_payload = plan.json()
        plan_ids = [item["id"] for item in (plan_payload.get("plans") or [])]
        assert plan_ids
        first_plan = (plan_payload.get("plans") or [])[0]
        assert "chapter_task_seed" in first_plan
        task_seed = first_plan["chapter_task_seed"]
        for key in [
            "chapter_function",
            "goals",
            "must_continue_points",
            "forbidden_jumps",
            "required_foreshadowing_action",
            "required_hook_strength",
            "pace_target",
            "opening_continuation",
            "chapter_payoff",
            "style_bias",
        ]:
            assert key in task_seed
        tasks_resp = client.get(f"/api/projects/{project_id}/chapter-tasks")
        assert tasks_resp.status_code == 200
        assert tasks_resp.json()
        preview = client.post(
            f"/api/projects/{project_id}/write/preview",
            json={"plan_id": plan_ids[0], "target_word_count": 1800},
        )
        assert preview.status_code == 200
        preview_payload = preview.json()
        assert "chapter_task" in preview_payload
        assert "structural_draft" in preview_payload
        assert "detemplated_draft" in preview_payload
        assert "integrity_check" in preview_payload
        commit = client.post(
            f"/api/projects/{project_id}/write/commit",
            json={"plan_ids": plan_ids, "chapter_count": len(plan_ids), "auto_commit": True},
        )
        assert commit.status_code == 200
        commit_payload = commit.json()
        assert commit_payload.get("generated_chapters")
        assert commit_payload.get("saved_chapter_ids")
        assert commit_payload.get("memory_refreshed") is True
        write = client.post(
            f"/api/projects/{project_id}/write",
            json={"plan_ids": plan_ids, "auto_commit": True},
        )
        assert write.status_code == 200
        write_payload = write.json()
        assert write_payload.get("generated_chapter_ids")
        assert "latest_structural_draft" in write_payload
        assert "latest_detemplated_draft" in write_payload
        assert "latest_draft_integrity_check" in write_payload
        assert "used_structural_fallback" in write_payload
        refresh = client.post(
            f"/api/projects/{project_id}/refresh-memory",
            json={"from_chapter_number": 1, "to_chapter_number": 3},
        )
        assert refresh.status_code == 200
        view_resp = client.get(f"/api/projects/{project_id}/memory-view")
        assert view_resp.status_code == 200
    finally:
        if original_provider:
            app.dependency_overrides[get_v2_workflow_service] = original_provider
        else:
            app.dependency_overrides.pop(get_v2_workflow_service, None)
    memory_view = view_resp.json().get("memory_view") or {}
    assert memory_view.get("outline_summary")
    assert isinstance(memory_view.get("main_plot_lines"), list)
    by_novel = client.get(f"/api/projects/by-novel/{novel_id}")
    assert by_novel.status_code == 200


def test_delete_chapter_api_updates_novel_stats():
    client = TestClient(app)
    files = {
        "novel_file": (
            "novel.txt",
            "第1章 起始\n主角进城。\n\n第2章 变局\n冲突爆发。",
            "text/plain",
        ),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "删除章节测试", "author": "删除作者", "genre": "xuanhuan", "auto_organize": "false"},
        files=files,
    )
    assert upload.status_code == 200
    novel_id = upload.json()["novel_id"]
    novel_detail = client.get(f"/api/novels/{novel_id}")
    assert novel_detail.status_code == 200
    chapters = novel_detail.json().get("chapters") or []
    assert len(chapters) == 2
    delete_resp = client.delete(f"/api/novels/{novel_id}/chapters/{chapters[-1]['id']}")
    assert delete_resp.status_code == 200
    delete_payload = delete_resp.json()
    assert delete_payload["chapter_count"] == 1
    latest_detail = client.get(f"/api/novels/{novel_id}")
    assert latest_detail.status_code == 200
    latest = latest_detail.json()
    assert latest["chapter_count"] == 1
    assert latest["chapters"][0]["number"] == 1


def test_projects_v2_import_keeps_author():
    client = TestClient(app)
    novel_path = _create_temp_novel_file()
    try:
        resp = client.post(
            "/api/projects/import",
            json={
                "project_name": "作者贯通测试",
                "author": "孔利群",
                "genre": "xuanhuan",
                "novel_file_path": novel_path,
                "outline_file_path": "",
                "auto_organize": False,
            },
        )
        assert resp.status_code == 200
        novel_id = resp.json()["novel_id"]
        detail = client.get(f"/api/novels/{novel_id}")
        assert detail.status_code == 200
        assert detail.json()["author"] == "孔利群"
    finally:
        try:
            Path(novel_path).unlink(missing_ok=True)
        except Exception:
            pass


def test_content_progress_returns_real_chapter_fields():
    client = TestClient(app)
    files = {
        "novel_file": ("novel.txt", "第1章 起\n甲\n\n第2章 承\n乙", "text/plain"),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "进度字段测试", "author": "测试作者", "genre": "xuanhuan", "auto_organize": "false"},
        files=files,
    )
    assert upload.status_code == 200
    novel_id = upload.json()["novel_id"]
    started = client.post(f"/api/content/organize/start/{novel_id}?force_rebuild=true")
    assert started.status_code == 200
    observed = []
    for _ in range(12):
        progress = client.get(f"/api/content/organize/progress/{novel_id}")
        assert progress.status_code == 200
        payload = progress.json()
        observed.append(payload)
        if payload.get("status") == "done":
            break
        time.sleep(0.2)
    latest = observed[-1]
    assert "stage" in latest
    assert "current" in latest and "total" in latest
    assert latest["total"] >= 2
    assert latest["current"] <= latest["total"]
    assert latest["percent"] <= 100


def test_create_project_does_not_generate_first_chapter():
    client = TestClient(app)
    created = client.post(
        "/api/projects",
        json={
            "name": "纯创建项目",
            "genre": "xuanhuan",
            "target_words": 300000,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["first_chapter"] is None
    novel_id = payload["project"]["novel_id"]
    detail = client.get(f"/api/novels/{novel_id}")
    assert detail.status_code == 200
    assert detail.json()["chapter_count"] == 0


def test_project_flow_import_edit_and_export_modes():
    client = TestClient(app)
    files = {
        "novel_file": ("novel.txt", "第1章 起\n甲\n\n第2章 承\n乙", "text/plain"),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "主链验收", "author": "主链作者", "genre": "xuanhuan", "auto_organize": "false", "import_mode": "full"},
        files=files,
    )
    assert upload.status_code == 200
    novel_id = upload.json()["novel_id"]
    detail = client.get(f"/api/novels/{novel_id}")
    assert detail.status_code == 200
    assert detail.json()["chapter_count"] >= 1
    chapter_id = detail.json()["chapters"][0]["id"]
    updated = client.put(
        f"/api/chapters/{chapter_id}",
        json={"chapter_id": chapter_id, "content": "章节更新后的正文"},
    )
    assert updated.status_code == 200
    assert "memory_refreshed" in updated.json()
    for scope, fmt, output in [
        ("full", "markdown", "flow_full.md"),
        ("full", "txt", "flow_full.txt"),
        ("by_chapter", "markdown", "flow_dir_md"),
        ("by_chapter", "txt", "flow_dir_txt"),
    ]:
        exported = client.post(
            "/api/export/",
            json={"novel_id": novel_id, "scope": scope, "format": fmt, "output_path": output},
        )
        assert exported.status_code == 200
        payload = exported.json()
        if scope == "full":
            assert payload["mode"] == "file"
            assert payload["file_path"]
        else:
            assert payload["mode"] == "directory"
            assert payload["directory_path"]


def test_v2_write_appends_chapter_number_and_keeps_title():
    original_provider = app.dependency_overrides.get(get_v2_workflow_service)

    def _override_workflow_service():
        service = get_v2_workflow_service()
        service.continue_writing_tool_cls = _FakeTool
        service.prompt_ai_service = _FakePromptAIService()
        return service

    app.dependency_overrides[get_v2_workflow_service] = _override_workflow_service
    client = TestClient(app)
    try:
        files = {
            "novel_file": ("novel.txt", "第1章 起\n甲\n\n第2章 承\n乙", "text/plain"),
        }
        upload = client.post(
            "/api/projects/import/upload",
            data={"project_name": "续写编号测试", "author": "测试作者", "genre": "xuanhuan", "auto_organize": "false"},
            files=files,
        )
        assert upload.status_code == 200
        project_id = upload.json()["project_id"]
        novel_id = upload.json()["novel_id"]
        detail_before = client.get(f"/api/novels/{novel_id}").json()
        max_before = max(ch["number"] for ch in detail_before.get("chapters") or [])

        branches = client.post(
            f"/api/projects/{project_id}/branches",
            json={"direction_hint": "推进主线", "branch_count": 4},
        )
        assert branches.status_code == 200
        branch_id = branches.json()["branches"][0]["id"]

        plan = client.post(
            f"/api/projects/{project_id}/chapter-plan",
            json={"branch_id": branch_id, "chapter_count": 1, "target_words_per_chapter": 900},
        )
        assert plan.status_code == 200
        plan_ids = [item["id"] for item in (plan.json().get("plans") or [])]
        assert plan_ids

        write = client.post(
            f"/api/projects/{project_id}/write",
            json={"plan_ids": plan_ids, "auto_commit": True},
        )
        assert write.status_code == 200
        latest_chapter = write.json().get("latest_chapter") or {}
        assert latest_chapter.get("number", 0) >= max_before + 1
        assert str(latest_chapter.get("title") or "").strip() != ""

        detail_after = client.get(f"/api/novels/{novel_id}").json()
        max_after = max(ch["number"] for ch in detail_after.get("chapters") or [])
        assert max_after >= max_before + 1
    finally:
        if original_provider:
            app.dependency_overrides[get_v2_workflow_service] = original_provider
        else:
            app.dependency_overrides.pop(get_v2_workflow_service, None)


def test_v2_write_fallbacks_to_structural_when_integrity_failed():
    original_provider = app.dependency_overrides.get(get_v2_workflow_service)

    class _IntegrityFallbackPromptAIService(_FakePromptAIService):
        async def rewrite_detemplated_draft(self, structural_draft, *_args, **_kwargs):
            return {
                "title": structural_draft.get("title") or "门后追击",
                "content": structural_draft["content"],
                "used_fallback": False,
                "integrity_failed": True,
                "display_fallback_to_structural": True,
            }

        async def check_draft_integrity(self, *_args, **_kwargs):
            return {
                "event_integrity_ok": False,
                "motivation_integrity_ok": True,
                "foreshadowing_integrity_ok": True,
                "hook_integrity_ok": True,
                "continuity_ok": False,
                "title_alignment_ok": True,
                "progression_integrity_ok": False,
                "risk_notes": ["改写稿存在一致性风险"],
            }

    def _override_workflow_service():
        service = get_v2_workflow_service()
        service.continue_writing_tool_cls = _FakeTool
        service.prompt_ai_service = _IntegrityFallbackPromptAIService()
        return service

    app.dependency_overrides[get_v2_workflow_service] = _override_workflow_service
    client = TestClient(app)
    try:
        files = {
            "novel_file": ("novel.txt", "第1章 起\n甲\n\n第2章 承\n乙", "text/plain"),
        }
        upload = client.post(
            "/api/projects/import/upload",
            data={"project_name": "续写校验回退测试", "author": "测试作者", "genre": "xuanhuan", "auto_organize": "false"},
            files=files,
        )
        assert upload.status_code == 200
        project_id = upload.json()["project_id"]
        branches = client.post(
            f"/api/projects/{project_id}/branches",
            json={"direction_hint": "推进主线", "branch_count": 4},
        )
        assert branches.status_code == 200
        branch_id = branches.json()["branches"][0]["id"]
        plan = client.post(
            f"/api/projects/{project_id}/chapter-plan",
            json={"branch_id": branch_id, "chapter_count": 1, "target_words_per_chapter": 900},
        )
        assert plan.status_code == 200
        plan_ids = [item["id"] for item in (plan.json().get("plans") or [])]
        assert plan_ids

        write = client.post(
            f"/api/projects/{project_id}/write",
            json={"plan_ids": plan_ids, "auto_commit": True},
        )
        assert write.status_code == 200
        payload = write.json()
        assert payload.get("used_structural_fallback") is True
        check = payload.get("latest_draft_integrity_check") or {}
        assert check.get("risk_notes")
    finally:
        if original_provider:
            app.dependency_overrides[get_v2_workflow_service] = original_provider
        else:
            app.dependency_overrides.pop(get_v2_workflow_service, None)
