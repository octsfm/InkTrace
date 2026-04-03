from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api.app import app
from presentation.api.dependencies import get_chapter_ai_service


class _FakeChapterAIService:
    def parse_imported_chapter(self, raw_text: str, fallback_title: str = ""):
        text = str(raw_text or "").strip()
        lines = text.splitlines()
        title = lines[0].strip() if lines else (fallback_title or "未命名章节")
        content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        return {"title": title, "content": content}

    async def analyze_to_outline(self, chapter_title: str, chapter_content: str, global_memory_summary: str = "", global_outline_summary: str = "", recent_chapter_summaries=None):
        return {
            "outline_draft": {
                "goal": f"推进{chapter_title}",
                "conflict": "冲突升级",
                "events": ["事件1", "事件2"],
                "character_progress": "角色成长",
                "ending_hook": "埋下悬念",
                "opening_continuation": "承接上章",
                "notes": "测试草稿",
            },
            "used_fallback": False,
        }

    async def optimize(self, chapter, outline, **kwargs):
        return {"result_text": "优化结果", "analysis": {}, "outline_draft": None, "used_fallback": False}

    async def continue_writing(self, chapter, target_word_count, outline, **kwargs):
        return {"result_text": "续写结果", "analysis": {}, "outline_draft": None, "used_fallback": False}

    async def rewrite_style(self, chapter, style, outline, **kwargs):
        return {"result_text": "改写结果", "analysis": {}, "outline_draft": None, "used_fallback": False}

    async def analyze(self, chapter, outline, **kwargs):
        draft = {
            "goal": "分析目标",
            "conflict": "分析冲突",
            "events": ["分析事件"],
            "character_progress": "分析推进",
            "ending_hook": "分析悬念",
            "opening_continuation": "分析承接",
            "notes": "分析备注",
        }
        return {"result_text": "", "analysis": {"outline_draft": draft}, "outline_draft": draft, "used_fallback": False}

    async def generate_from_outline(self, chapter, outline, target_word_count, **kwargs):
        return {"result_text": "目标：生成正文", "analysis": {}, "outline_draft": None, "used_fallback": False}


def test_chapter_editor_read_save_outline_and_ai_actions(caplog):
    app.dependency_overrides[get_chapter_ai_service] = lambda: _FakeChapterAIService()
    client = TestClient(app)
    try:
        files = {
            "novel_file": (
                "novel.txt",
                "第1章 起始\n主角进入古城。\n\n第2章 冲突\n主角遭遇围攻。",
                "text/plain",
            ),
        }
        upload = client.post(
            "/api/projects/import/upload",
            data={"project_name": "章节编辑接口测试", "author": "测试作者", "genre": "xuanhuan", "auto_organize": "false"},
            files=files,
        )
        assert upload.status_code == 200
        novel_id = upload.json()["novel_id"]
        detail = client.get(f"/api/novels/{novel_id}")
        assert detail.status_code == 200
        chapter_id = detail.json()["chapters"][0]["id"]

        read_resp = client.get(f"/api/chapters/{chapter_id}")
        assert read_resp.status_code == 200
        assert read_resp.json()["id"] == chapter_id
        continuation_context_resp = client.get(f"/api/chapters/{chapter_id}/continuation-context")
        assert continuation_context_resp.status_code == 200
        assert continuation_context_resp.json()["chapter_id"] == chapter_id

        save_resp = client.put(
            f"/api/chapters/{chapter_id}",
            json={"chapter_id": chapter_id, "title": "第1章 起始（修订）", "content": "修订后的正文内容"},
        )
        assert save_resp.status_code == 200
        read_after_save = client.get(f"/api/chapters/{chapter_id}")
        assert read_after_save.status_code == 200
        assert read_after_save.json()["title"] == "第1章 起始（修订）"
        assert "修订后的正文内容" in read_after_save.json()["content"]

        outline_resp = client.put(
            f"/api/chapters/{chapter_id}/outline",
            json={
                "chapter_id": chapter_id,
                "goal": "推进主角调查",
                "conflict": "守卫阻拦",
                "events": ["发现线索", "遭遇盘查"],
                "character_progress": "主角从试探转入主动调查",
                "ending_hook": "神秘人现身",
                "opening_continuation": "承接上一章的古城追踪",
                "notes": "保持紧张节奏",
            },
        )
        assert outline_resp.status_code == 200
        assert outline_resp.json()["goal"] == "推进主角调查"
        assert outline_resp.json()["character_progress"] == "主角从试探转入主动调查"
        assert outline_resp.json()["opening_continuation"] == "承接上一章的古城追踪"
        outline_get = client.get(f"/api/chapters/{chapter_id}/outline")
        assert outline_get.status_code == 200
        assert outline_get.json()["character_progress"] == "主角从试探转入主动调查"
        assert outline_get.json()["opening_continuation"] == "承接上一章的古城追踪"

        import_resp = client.post(
            f"/api/chapters/{chapter_id}/import",
            json={
                "raw_text": "第1章 再入古城\n主角再次进入古城并发现新线索。",
                "global_memory_summary": "当前主线围绕古城线索展开",
                "global_outline_summary": "大纲要求强化悬疑氛围",
            },
        )
        assert import_resp.status_code == 200
        imported = import_resp.json()
        assert imported["title"] == "第1章 再入古城"
        assert imported["content"]
        assert "used_fallback" in imported
        assert "chapter_task_seed" in imported
        assert "chapter_analysis_summary" in imported
        assert "continuation_summary" in imported
        for key in ["goal", "conflict", "events", "character_progress", "ending_hook", "opening_continuation", "notes"]:
            assert key in imported["outline_draft"]

        optimize_resp = client.post(
            f"/api/chapters/{chapter_id}/ai/optimize",
            json={"chapter_id": chapter_id, "action": "optimize"},
        )
        assert optimize_resp.status_code == 200
        assert optimize_resp.json()["action"] == "optimize"
        assert "result_text" in optimize_resp.json()
        assert "used_fallback" in optimize_resp.json()

        analyze_resp = client.post(
            f"/api/chapters/{chapter_id}/ai/analyze",
            json={
                "chapter_id": chapter_id,
                "action": "analyze",
                "global_memory_summary": "主线围绕古城危机",
                "global_outline_summary": "需要推进古城线索",
                "recent_chapter_summaries": ["第1章 主角入城"],
            },
        )
        assert analyze_resp.status_code == 200
        assert "analysis" in analyze_resp.json()
        assert "outline_draft" in (analyze_resp.json().get("analysis") or {})
        assert "outline_draft" in analyze_resp.json()
        assert "used_fallback" in analyze_resp.json()

        generate_resp = client.post(
            f"/api/chapters/{chapter_id}/ai/generate-from-outline",
            json={"chapter_id": chapter_id, "action": "generate-from-outline", "target_word_count": 1200},
        )
        assert generate_resp.status_code == 200
        generated_text = generate_resp.json()["result_text"]
        assert "目标：" in generated_text
        assert "used_fallback" in generate_resp.json()
        apply_save = client.put(
            f"/api/chapters/{chapter_id}",
            json={"chapter_id": chapter_id, "content": generated_text},
        )
        assert apply_save.status_code == 200
        assert "memory_refreshed" in apply_save.json()
        read_after_apply = client.get(f"/api/chapters/{chapter_id}")
        assert read_after_apply.status_code == 200
        assert "目标：" in read_after_apply.json()["content"]
        events = [getattr(rec, "event", "") for rec in caplog.records]
        assert "chapter_ai_started" in events
        assert "chapter_ai_finished" in events
    finally:
        app.dependency_overrides.clear()
