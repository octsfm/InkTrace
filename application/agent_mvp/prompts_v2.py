from __future__ import annotations

import json
from typing import Any, Dict

from application.prompts.prompt_input_builder import PromptInputBuilder
from application.prompts.prompt_templates import build_structural_draft_prompt


CHAPTER_ANALYSIS_SYSTEM_PROMPT = """你是章节结构分析器。只允许输出JSON对象，不允许解释文本。
输出结构必须严格为：
{
  "chapter_summary":"",
  "characters":[{"name":"","traits":[],"relationships":{}}],
  "world_facts":{
    "background":[],
    "power_system":[],
    "organizations":[],
    "locations":[],
    "rules":[],
    "artifacts":[]
  },
  "plot_points":[],
  "events":[{"event":"","actors":[],"action":"","result":"","impact":""}],
  "style_tags":[],
  "continuity_flags":[]
}
约束：
1) 只提取本章新增或强化的信息；
2) characters 只保留核心角色；
3) events 必须具体且字段完整；
4) style_tags 数量限制 3-5；
5) 禁止输出自然语言说明。"""


BRANCH_GENERATION_SYSTEM_PROMPT = """你是剧情分支生成器。你必须只输出JSON对象，不允许解释文本。
输出结构：
{
  "branches":[
    {
      "id":"",
      "title":"",
      "summary":"",
      "next_goal":"",
      "impact":"",
      "tone":""
    }
  ]
}
约束：
1) 必须输出指定数量分支；
2) 各分支要显著不同；
3) 必须与大纲与记忆一致；
4) 禁止输出正文。"""


CHAPTER_WRITING_SYSTEM_PROMPT = """你是单章写作引擎。必须只输出JSON对象，不允许解释文本。
输出结构：
{
  "chapter_text":"",
  "new_events":[],
  "possible_continuity_flags":[]
}
约束：
1) 只写当前一章；
2) 严格围绕章节目标与冲突；
3) 字数允许上下浮动10%；
4) 结尾必须落到 ending_hook。"""


def build_chapter_analysis_prompt(
    chapter_title: str,
    chapter_text: str,
    merge_memory: Dict[str, Any],
    outline_context: Dict[str, Any],
) -> str:
    return (
        f"{CHAPTER_ANALYSIS_SYSTEM_PROMPT}\n\n"
        f"章节标题: {chapter_title or '未命名章节'}\n"
        f"大纲上下文: {json.dumps(outline_context or {}, ensure_ascii=False)[:3000]}\n"
        f"已有memory: {json.dumps(merge_memory or {}, ensure_ascii=False)[:4000]}\n"
        f"章节正文:\n{(chapter_text or '')[:12000]}\n\n"
        "仅返回JSON对象。"
    )


def build_branch_generation_prompt(
    memory: Dict[str, Any],
    chapter_text: str,
    direction_hint: str,
    branch_count: int,
    outline_context: Dict[str, Any],
) -> str:
    return (
        f"{BRANCH_GENERATION_SYSTEM_PROMPT}\n\n"
        f"大纲上下文: {json.dumps(outline_context or {}, ensure_ascii=False)[:3000]}\n"
        f"当前memory: {json.dumps(memory or {}, ensure_ascii=False)[:5000]}\n"
        f"当前章节内容:\n{(chapter_text or '')[:5000]}\n"
        f"方向提示: {direction_hint or ''}\n"
        f"分支数量: {branch_count}\n\n"
        "只返回JSON对象。"
    )


def build_chapter_writing_prompt(
    memory: Dict[str, Any],
    direction: str,
    chapters_text: str,
    chapter_count: int,
    target_word_count: int,
    ending_hook: str,
) -> str:
    # Compatibility wrapper: the legacy agent_mvp writing entry now delegates to
    # the unified structural-draft prompt contract so Prompt C stays single-source.
    payload = PromptInputBuilder.build_structural_draft_input(
        chapter_task={"goals": [direction], "chapter_payoff": ending_hook, "pace_target": str(target_word_count)},
        global_constraints=(memory or {}).get("global_constraints") or {},
        continuation_context=type("PromptContext", (), {"recent_chapter_memories": (memory or {}).get("chapter_continuation_memories") or [], "last_chapter_tail": chapters_text[-800:]})(),
        relevant_characters=(memory or {}).get("characters") or [],
        relevant_foreshadowing=((memory or {}).get("global_constraints") or {}).get("must_keep_threads") or [],
    )
    payload.update(
        {
            "direction": direction or "",
            "chapter_count": chapter_count,
            "target_word_count": target_word_count,
            "ending_hook": ending_hook or "",
            "history_excerpt": (chapters_text or "")[:6000],
        }
    )
    return build_structural_draft_prompt(payload)
