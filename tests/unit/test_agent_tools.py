import asyncio

from application.agent_mvp.tools import ContinueWritingTool, StoryBranchTool


class _FakeRouter:
    def __init__(self, text: str):
        self.text = text

    async def generate(self, prompt: str, max_tokens: int, temperature: float):
        return {"ok": True, "text": self.text}


def test_story_branch_tool_supports_object_payload():
    tool = StoryBranchTool()
    raw = """
    {
      "branches": [
        {"id": "b1", "title": "分支一", "summary": "推进A", "next_goal": "目标A", "impact": "影响A", "tone": "紧张"}
      ]
    }
    """
    branches = tool._extract_branches(raw)
    assert len(branches) == 1
    assert branches[0]["id"] == "b1"


def test_continue_writing_tool_maps_prompts_v2_payload():
    tool = ContinueWritingTool()
    tool.model_router = _FakeRouter(
        """
        {
          "title": "第10章",
          "content": "这是章节正文",
          "summary": "摘要",
          "new_facts": [{"event": "新事实"}],
          "possible_continuity_flags": [{"type": "outline_conflict"}]
        }
        """
    )
    payload = asyncio.run(tool._call_llm("mock_prompt"))
    assert payload["chapter_text"] == "这是章节正文"
    assert payload["new_events"] == [{"event": "新事实"}]
    assert payload["possible_continuity_flags"] == [{"type": "outline_conflict"}]


def test_continue_writing_tool_accepts_structured_memory():
    tool = ContinueWritingTool()
    memory = {
        "characters": [{"name": "主角"}],
        "world_facts": {"background": ["古城规则"]},
        "chapter_summaries": ["上章总结"],
        "style_profile": {"narrative_pov": "第三人称", "tone_tags": ["紧张"], "rhythm_tags": ["中速"]},
        "current_state": {"latest_chapter_number": 2, "latest_summary": "上章总结", "next_writing_focus": "冲突升级"},
        "events": [{"event": "冲突升级"}],
    }
    assert tool._has_required_memory(memory) is True
