from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from application.agent_mvp.model_router import ModelRouter
from application.services.logging_service import build_log_context, get_logger
from domain.entities.chapter import Chapter
from infrastructure.llm.llm_factory import LLMFactory


class ChapterAIService:
    def __init__(self, llm_factory: Optional[LLMFactory] = None):
        self.llm_factory = llm_factory
        self.model_router = ModelRouter(
            llm_factory.primary_client if llm_factory else None,
            llm_factory.backup_client if llm_factory else None,
        )
        self.logger = get_logger(__name__)

    def _parse_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        raw = str(text or "").strip()
        if not raw:
            return None
        candidates = [raw]
        fenced = re.findall(r"```json\s*([\s\S]*?)```", raw, flags=re.IGNORECASE)
        candidates.extend(fenced)
        fenced_plain = re.findall(r"```\s*([\s\S]*?)```", raw, flags=re.IGNORECASE)
        candidates.extend(fenced_plain)
        obj_matches = re.findall(r"\{[\s\S]*?\}", raw)
        candidates.extend(obj_matches)
        for item in candidates:
            snippet = str(item).strip()
            if not snippet:
                continue
            try:
                payload = json.loads(snippet)
                if isinstance(payload, dict):
                    return payload
            except Exception:
                continue
        return None

    async def _call_llm_json(
        self,
        action: str,
        chapter_title: str,
        chapter_content: str,
        outline: Dict[str, Any],
        global_memory_summary: str,
        global_outline_summary: str,
        recent_chapter_summaries: List[str],
        style: str = "",
        target_word_count: int = 2200,
    ) -> Optional[Dict[str, Any]]:
        self.logger.info(
            "章节AI模型调用开始",
            extra=build_log_context(
                event="chapter_ai_llm_started",
                action=action,
                chapter_title=chapter_title,
                has_global_memory_summary=bool(global_memory_summary),
                has_global_outline_summary=bool(global_outline_summary),
                recent_summary_count=len(recent_chapter_summaries or []),
            ),
        )
        prompt_payload = {
            "action": action,
            "chapter_title": chapter_title,
            "chapter_content": chapter_content,
            "chapter_outline": outline or {},
            "global_memory_summary": global_memory_summary or "",
            "global_outline_summary": global_outline_summary or "",
            "recent_chapter_summaries": recent_chapter_summaries or [],
            "style": style or "",
            "target_word_count": target_word_count,
        }
        prompt = (
            "你是章节级写作助手。请严格返回JSON对象，不要返回markdown。\n"
            "JSON结构：{\"result_text\": str, \"analysis\": object, \"outline_draft\": object|null}\n"
            "其中outline_draft结构固定为：goal/conflict/events/character_progress/ending_hook/opening_continuation/notes。\n"
            f"输入数据：{json.dumps(prompt_payload, ensure_ascii=False)}"
        )
        result = await self.model_router.generate(prompt, max_tokens=2200, temperature=0.45)
        if not result.get("ok"):
            self.logger.error("章节AI模型调用失败", extra=build_log_context(event="chapter_ai_llm_failed", action=action, error=str(result.get("error") or "unknown")))
            return None
        text = str(result.get("text") or "").strip()
        if not text:
            self.logger.error("章节AI模型调用失败", extra=build_log_context(event="chapter_ai_llm_failed", action=action, error="empty_response"))
            return None
        payload = self._parse_json_from_text(text)
        if not payload:
            self.logger.warning("章节AI解析失败", extra=build_log_context(event="chapter_ai_json_parse_failed", action=action))
            return None
        self.logger.info("章节AI模型调用成功", extra=build_log_context(event="chapter_ai_llm_succeeded", action=action, response_length=len(text)))
        return payload

    async def _call_llm_outline(
        self,
        chapter_title: str,
        chapter_content: str,
        global_memory_summary: str,
        global_outline_summary: str,
        recent_chapter_summaries: List[str],
    ) -> Optional[Dict[str, Any]]:
        self.logger.info(
            "章节AI模型调用开始",
            extra=build_log_context(
                event="chapter_ai_llm_started",
                action="outline",
                chapter_title=chapter_title,
                has_global_memory_summary=bool(global_memory_summary),
                has_global_outline_summary=bool(global_outline_summary),
                recent_summary_count=len(recent_chapter_summaries or []),
            ),
        )
        prompt_payload = {
            "chapter_title": chapter_title or "",
            "chapter_content": chapter_content or "",
            "global_memory_summary": global_memory_summary or "",
            "global_outline_summary": global_outline_summary or "",
            "recent_chapter_summaries": recent_chapter_summaries or [],
        }
        prompt = (
            "你是章节分析助手。请只输出一个JSON对象，不要输出markdown，不要解释。\n"
            "固定字段：goal, conflict, events, character_progress, ending_hook, opening_continuation, notes。\n"
            "events必须是字符串数组，长度1-8。\n"
            f"输入：{json.dumps(prompt_payload, ensure_ascii=False)}"
        )
        result = await self.model_router.generate(prompt, max_tokens=1200, temperature=0.35)
        if not result.get("ok"):
            self.logger.error("章节AI模型调用失败", extra=build_log_context(event="chapter_ai_llm_failed", action="outline", error=str(result.get("error") or "unknown")))
            return None
        text = str(result.get("text") or "").strip()
        if not text:
            self.logger.error("章节AI模型调用失败", extra=build_log_context(event="chapter_ai_llm_failed", action="outline", error="empty_response"))
            return None
        payload = self._parse_json_from_text(text)
        if not payload:
            self.logger.warning("章节AI解析失败", extra=build_log_context(event="chapter_ai_json_parse_failed", action="outline"))
            return None
        self.logger.info("章节AI模型调用成功", extra=build_log_context(event="chapter_ai_llm_succeeded", action="outline", response_length=len(text)))
        return self._normalize_outline_draft(payload)

    def _normalize_outline_draft(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        events = draft.get("events") if isinstance(draft.get("events"), list) else []
        normalized_events = [str(x).strip() for x in events if str(x).strip()][:8]
        return {
            "goal": str(draft.get("goal") or "").strip(),
            "conflict": str(draft.get("conflict") or "").strip(),
            "events": normalized_events,
            "character_progress": str(draft.get("character_progress") or "").strip(),
            "ending_hook": str(draft.get("ending_hook") or "").strip(),
            "opening_continuation": str(draft.get("opening_continuation") or "").strip(),
            "notes": str(draft.get("notes") or "").strip(),
        }

    def _fallback_action(
        self,
        action: str,
        chapter: Chapter,
        outline: Dict[str, Any],
        global_memory_summary: str = "",
        global_outline_summary: str = "",
    ) -> Dict[str, Any]:
        if action == "optimize":
            return {"result_text": self._fallback_optimize(chapter, outline), "analysis": {}, "outline_draft": None}
        if action == "continue":
            return {"result_text": self._fallback_continue(chapter, 2200), "analysis": {}, "outline_draft": None}
        if action == "rewrite-style":
            return {"result_text": self._fallback_rewrite(chapter, "当前风格"), "analysis": {}, "outline_draft": None}
        if action == "generate-from-outline":
            return {"result_text": self._fallback_generate(chapter, outline, 2200), "analysis": {}, "outline_draft": None}
        outline_draft = self._rule_outline_draft(chapter.title or "", chapter.content or "", global_memory_summary, global_outline_summary)
        analysis = {
            "word_count": chapter.word_count,
            "paragraph_count": len([p for p in (chapter.content or "").split("\n") if p.strip()]),
            "outline_goal": str((outline or {}).get("goal") or ""),
            "key_events": [p for p in (chapter.content or "").split("\n") if p.strip()][:3],
            "outline_draft": outline_draft,
            "used_fallback": True,
        }
        return {"result_text": "", "analysis": analysis, "outline_draft": analysis.get("outline_draft")}

    def parse_imported_chapter(self, raw_text: str, fallback_title: str = "") -> Dict[str, str]:
        text = str(raw_text or "").strip()
        if not text:
            return {"title": fallback_title or "未命名章节", "content": ""}
        lines = [line.rstrip() for line in text.splitlines()]
        first = (lines[0] or "").strip() if lines else ""
        if first and len(first) <= 40 and any(token in first for token in ("第", "章", "Chapter")):
            title = first
            content = "\n".join(lines[1:]).strip()
        else:
            title = fallback_title or "未命名章节"
            content = text
        return {"title": title.strip() or "未命名章节", "content": content}

    def _rule_outline_draft(
        self,
        chapter_title: str,
        chapter_content: str,
        global_memory_summary: str = "",
        global_outline_summary: str = "",
    ) -> Dict[str, Any]:
        content = str(chapter_content or "").strip()
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        key_events = lines[:5]
        goal = f"围绕《{chapter_title or '本章'}》推进当前主线"
        conflict = lines[1] if len(lines) > 1 else "本章冲突待补充"
        character_progress = "人物关系出现推进" if len(lines) >= 2 else "人物状态变化待补充"
        ending_hook = lines[-1] if lines else "留出下一章悬念"
        notes = "；".join([x for x in [global_memory_summary, global_outline_summary] if str(x).strip()])[:200]
        return {
            "goal": goal,
            "conflict": conflict,
            "events": key_events,
            "character_progress": character_progress,
            "ending_hook": ending_hook,
            "opening_continuation": lines[0] if lines else "",
            "notes": notes,
        }

    async def analyze_to_outline(
        self,
        chapter_title: str,
        chapter_content: str,
        global_memory_summary: str = "",
        global_outline_summary: str = "",
        recent_chapter_summaries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        model_result = await self._call_llm_outline(
            chapter_title,
            chapter_content,
            global_memory_summary,
            global_outline_summary,
            recent_chapter_summaries or [],
        )
        if model_result:
            return {"outline_draft": model_result, "used_fallback": False}
        self.logger.warning("章节AI使用兜底", extra=build_log_context(event="chapter_ai_fallback_used", action="outline"))
        return {
            "outline_draft": self._rule_outline_draft(
                chapter_title,
                chapter_content,
                global_memory_summary,
                global_outline_summary,
            ),
            "used_fallback": True,
        }

    def _fallback_optimize(self, chapter: Chapter, outline: Dict[str, Any]) -> str:
        outline_goal = str((outline or {}).get("goal") or "").strip()
        prefix = f"【优化建议】目标：{outline_goal}\n\n" if outline_goal else "【优化建议】\n\n"
        return f"{prefix}{(chapter.content or '').strip()}"

    def _fallback_continue(self, chapter: Chapter, target_word_count: int) -> str:
        base = (chapter.content or "").strip()
        if not base:
            base = f"第{chapter.number}章 {chapter.title}\n\n"
        bridge = "\n\n（续写）剧情继续推进，人物冲突升级。"
        return (base + bridge)[: max(target_word_count, len(base) + len(bridge))]

    def _fallback_rewrite(self, chapter: Chapter, style: str) -> str:
        style_label = (style or "当前风格").strip()
        return f"【风格改写：{style_label}】\n\n{(chapter.content or '').strip()}"

    async def _fallback_analyze(
        self,
        chapter: Chapter,
        outline: Dict[str, Any],
        global_memory_summary: str = "",
        global_outline_summary: str = "",
    ) -> Dict[str, Any]:
        content = chapter.content or ""
        paragraphs = [p for p in content.split("\n") if p.strip()]
        events: List[str] = paragraphs[:3]
        outline_result = await self.analyze_to_outline(
            chapter.title or "",
            chapter.content or "",
            global_memory_summary,
            global_outline_summary,
            [],
        )
        return {
            "word_count": chapter.word_count,
            "paragraph_count": len(paragraphs),
            "outline_goal": str((outline or {}).get("goal") or ""),
            "key_events": events,
            "outline_draft": outline_result["outline_draft"],
            "used_fallback": outline_result["used_fallback"],
        }

    def _fallback_generate(self, chapter: Chapter, outline: Dict[str, Any], target_word_count: int) -> str:
        goal = str((outline or {}).get("goal") or "").strip() or "推进主线"
        conflict = str((outline or {}).get("conflict") or "").strip()
        events = [str(x).strip() for x in ((outline or {}).get("events") or []) if str(x).strip()]
        character_progress = str((outline or {}).get("character_progress") or "").strip()
        ending_hook = str((outline or {}).get("ending_hook") or "").strip()
        parts = [
            f"第{chapter.number}章 {chapter.title}",
            "",
            f"目标：{goal}",
        ]
        if conflict:
            parts.append(f"冲突：{conflict}")
        if events:
            parts.append("关键事件：")
            parts.extend([f"- {item}" for item in events[:6]])
        if character_progress:
            parts.append(f"人物推进：{character_progress}")
        if ending_hook:
            parts.append(f"结尾钩子：{ending_hook}")
        parts.append("")
        parts.append("正文：")
        parts.append("本章围绕既定目标展开，人物在冲突中做出关键选择。")
        text = "\n".join(parts)
        return text[:max(target_word_count, len(text))]

    async def optimize(
        self,
        chapter: Chapter,
        outline: Dict[str, Any],
        global_memory_summary: str = "",
        global_outline_summary: str = "",
        recent_chapter_summaries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload = await self._call_llm_json(
            "optimize",
            chapter.title or "",
            chapter.content or "",
            outline,
            global_memory_summary,
            global_outline_summary,
            recent_chapter_summaries or [],
        )
        if payload:
            result = {"result_text": str(payload.get("result_text") or ""), "analysis": payload.get("analysis") or {}, "outline_draft": payload.get("outline_draft"), "used_fallback": False}
            self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="optimize", used_fallback=False))
            return result
        fallback = self._fallback_action("optimize", chapter, outline, global_memory_summary, global_outline_summary)
        fallback["used_fallback"] = True
        self.logger.warning("章节AI使用兜底", extra=build_log_context(event="chapter_ai_fallback_used", action="optimize"))
        self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="optimize", used_fallback=True))
        return fallback

    async def continue_writing(
        self,
        chapter: Chapter,
        target_word_count: int,
        outline: Dict[str, Any],
        global_memory_summary: str = "",
        global_outline_summary: str = "",
        recent_chapter_summaries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload = await self._call_llm_json(
            "continue_writing",
            chapter.title or "",
            chapter.content or "",
            outline,
            global_memory_summary,
            global_outline_summary,
            recent_chapter_summaries or [],
            target_word_count=target_word_count,
        )
        if payload:
            result = {"result_text": str(payload.get("result_text") or ""), "analysis": payload.get("analysis") or {}, "outline_draft": payload.get("outline_draft"), "used_fallback": False}
            self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="continue", used_fallback=False))
            return result
        self.logger.warning("章节AI使用兜底", extra=build_log_context(event="chapter_ai_fallback_used", action="continue"))
        self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="continue", used_fallback=True))
        return {"result_text": self._fallback_continue(chapter, target_word_count), "analysis": {}, "outline_draft": None, "used_fallback": True}

    async def rewrite_style(
        self,
        chapter: Chapter,
        style: str,
        outline: Dict[str, Any],
        global_memory_summary: str = "",
        global_outline_summary: str = "",
        recent_chapter_summaries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload = await self._call_llm_json(
            "rewrite_style",
            chapter.title or "",
            chapter.content or "",
            outline,
            global_memory_summary,
            global_outline_summary,
            recent_chapter_summaries or [],
            style=style,
        )
        if payload:
            result = {"result_text": str(payload.get("result_text") or ""), "analysis": payload.get("analysis") or {}, "outline_draft": payload.get("outline_draft"), "used_fallback": False}
            self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="rewrite-style", used_fallback=False))
            return result
        self.logger.warning("章节AI使用兜底", extra=build_log_context(event="chapter_ai_fallback_used", action="rewrite-style"))
        self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="rewrite-style", used_fallback=True))
        return {"result_text": self._fallback_rewrite(chapter, style), "analysis": {}, "outline_draft": None, "used_fallback": True}

    async def analyze(
        self,
        chapter: Chapter,
        outline: Dict[str, Any],
        global_memory_summary: str = "",
        global_outline_summary: str = "",
        recent_chapter_summaries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload = await self._call_llm_json(
            "analyze",
            chapter.title or "",
            chapter.content or "",
            outline,
            global_memory_summary,
            global_outline_summary,
            recent_chapter_summaries or [],
        )
        if payload:
            analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
            outline_draft = payload.get("outline_draft") if isinstance(payload.get("outline_draft"), dict) else analysis.get("outline_draft")
            if outline_draft:
                analysis["outline_draft"] = outline_draft
            self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="analyze", used_fallback=False))
            return {"result_text": str(payload.get("result_text") or ""), "analysis": analysis, "outline_draft": outline_draft, "used_fallback": False}
        analysis = await self._fallback_analyze(chapter, outline, global_memory_summary, global_outline_summary)
        self.logger.warning("章节AI使用兜底", extra=build_log_context(event="chapter_ai_fallback_used", action="analyze"))
        self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="analyze", used_fallback=True))
        return {"result_text": "", "analysis": analysis, "outline_draft": analysis.get("outline_draft"), "used_fallback": True}

    async def generate_from_outline(
        self,
        chapter: Chapter,
        outline: Dict[str, Any],
        target_word_count: int,
        global_memory_summary: str = "",
        global_outline_summary: str = "",
        recent_chapter_summaries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload = await self._call_llm_json(
            "generate_from_outline",
            chapter.title or "",
            chapter.content or "",
            outline,
            global_memory_summary,
            global_outline_summary,
            recent_chapter_summaries or [],
            target_word_count=target_word_count,
        )
        if payload:
            result = {"result_text": str(payload.get("result_text") or ""), "analysis": payload.get("analysis") or {}, "outline_draft": payload.get("outline_draft"), "used_fallback": False}
            self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="generate-from-outline", used_fallback=False))
            return result
        self.logger.warning("章节AI使用兜底", extra=build_log_context(event="chapter_ai_fallback_used", action="generate-from-outline"))
        self.logger.info("章节AI完成", extra=build_log_context(event="chapter_ai_finished", action="generate-from-outline", used_fallback=True))
        return {"result_text": self._fallback_generate(chapter, outline, target_word_count), "analysis": {}, "outline_draft": None, "used_fallback": True}
