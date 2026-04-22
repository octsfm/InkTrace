from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from application.agent_mvp.model_router import ModelRouter
from application.agent_mvp.model_role_router import ModelRoleRouter
from application.prompts.prompt_input_builder import PromptInputBuilder
from application.prompts.prompt_parser import (
    parse_json_object,
    parse_json_object_with_diagnostics,
    strip_code_fence,
)
from application.prompts.prompt_templates import (
    build_chapter_ai_json_prompt,
    build_chapter_outline_prompt,
    build_chapter_task_prompt,
    build_continuation_memory_prompt,
    build_detemplating_prompt,
    build_detemplating_revision_prompt,
    build_global_analysis_prompt,
    build_integrity_check_prompt,
    build_plot_arc_extraction_prompt,
    build_structural_draft_prompt,
    build_title_backfill_prompt,
)
from application.services.logging_service import build_log_context, get_logger
from domain.entities.chapter import Chapter
from domain.constants.story_constants import (
    DEFAULT_FORESHADOWING_ACTION,
    DEFAULT_HOOK_STRENGTH,
    DEFAULT_PACE_TARGET,
)
from domain.constants.story_enums import CHAPTER_FUNCTION_ADVANCE_INVESTIGATION
from domain.entities.model_role import ModelRole
from domain.exceptions import LLMClientError
from infrastructure.llm.llm_factory import LLMFactory


class ChapterAIService:
    def __init__(self, llm_factory: Optional[LLMFactory] = None):
        self.llm_factory = llm_factory
        deepseek_client = None
        kimi_client = None
        if llm_factory:
            client_getter = getattr(llm_factory, "get_client_for_provider", None)
            if callable(client_getter):
                deepseek_client = client_getter("deepseek")
                kimi_client = client_getter("kimi")
            else:
                deepseek_client = getattr(llm_factory, "deepseek_client", None)
                kimi_client = getattr(llm_factory, "kimi_client", None)
                if deepseek_client is None and kimi_client is None:
                    deepseek_client = getattr(llm_factory, "primary_client", None)
                    kimi_client = getattr(llm_factory, "backup_client", None)
        self.model_router = ModelRouter(
            deepseek_client,
            kimi_client,
        )
        self.model_role_router = ModelRoleRouter(llm_factory) if llm_factory else None
        self.logger = get_logger(__name__)

    def _raise_required_model_failure(self, role: ModelRole, step_label: str) -> None:
        provider = "模型"
        if self.model_role_router is not None:
            try:
                provider = str(self.model_role_router.provider_for_role(role) or provider)
            except Exception:
                provider = "模型"
        elif role in {
            ModelRole.GLOBAL_ANALYSIS,
            ModelRole.CHAPTER_ANALYSIS,
            ModelRole.CONTINUATION_MEMORY_EXTRACTION,
            ModelRole.PLOT_ARC_EXTRACTION,
            ModelRole.ARC_STATE_UPDATE,
            ModelRole.ARC_SELECTION,
            ModelRole.CHAPTER_PLANNING,
            ModelRole.CONSISTENCY_VALIDATION,
        }:
            provider = "kimi"
        raise LLMClientError(f"{provider} {step_label}失败，已停止整理，请检查模型配置后重试")

    def _parse_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        return parse_json_object(text)

    def _use_role_router(self) -> bool:
        if self.model_role_router is None or self.llm_factory is None:
            return False
        if callable(getattr(self.llm_factory, "get_client_for_provider", None)):
            return True
        return any(
            getattr(self.llm_factory, attr, None) is not None
            for attr in ("deepseek_client", "kimi_client")
        )

    def _resolve_action_role(self, action: str) -> ModelRole:
        action_key = str(action or "").strip().lower()
        if action_key in {"analyze", "outline"}:
            return ModelRole.CHAPTER_ANALYSIS
        if action_key == "rewrite_style":
            return ModelRole.STYLE_REWRITE
        if action_key == "generate_from_outline":
            return ModelRole.STRUCTURAL_WRITING
        if action_key in {"continue", "continue_writing", "optimize"}:
            return ModelRole.CONTINUATION_WRITING
        return ModelRole.CONTINUATION_WRITING

    def _format_parse_failed_response(self, text: str) -> str:
        raw = str(text or "")
        if not raw:
            return ""
        if os.getenv("INKTRACE_LOG_FULL_MODEL_RESPONSE_ON_PARSE_FAIL", "").strip().lower() in {"1", "true", "yes", "on"}:
            return raw
        if len(raw) <= 2000:
            return raw
        return f"{raw[:1200]}\n\n...[TRUNCATED {len(raw) - 2000} chars]...\n\n{raw[-800:]}"

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
        prompt = build_chapter_ai_json_prompt(prompt_payload)
        role = self._resolve_action_role(action)
        result = await self.model_role_router.generate(role, prompt, max_tokens=2200, temperature=0.45) if self._use_role_router() else await self.model_router.generate(prompt, max_tokens=2200, temperature=0.45)
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
        prompt = build_chapter_outline_prompt(prompt_payload)
        result = await self.model_role_router.generate(ModelRole.CHAPTER_ANALYSIS, prompt, max_tokens=1200, temperature=0.35) if self._use_role_router() else await self.model_router.generate(prompt, max_tokens=1200, temperature=0.35)
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

    async def _call_prompt_json(self, prompt_type: str, prompt: str, role: ModelRole, max_tokens: int = 1600, temperature: float = 0.35, sent_event: str = "", metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        context = {"prompt_type": prompt_type, "project_id": "", "chapter_id": "", "chapter_number": 0, "model_name": role.value, **(metadata or {})}
        self.logger.info("Prompt调用开始", extra=build_log_context(event=sent_event or f"{prompt_type}_prompt_sent", **context, used_fallback=False, response_parse_failed=False))
        result = await self.model_role_router.generate(role, prompt, max_tokens=max_tokens, temperature=temperature) if self._use_role_router() else await self.model_router.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        if not result.get("ok"):
            self.logger.error("Prompt调用失败", extra=build_log_context(event=f"{prompt_type}_prompt_failed", **context, error=str(result.get("error") or "unknown"), used_fallback=True, response_parse_failed=False))
            return None
        text = str(result.get("text") or "").strip()
        if not text:
            self.logger.warning("Prompt空响应", extra=build_log_context(event=f"{prompt_type}_prompt_failed", **context, error="empty_response", used_fallback=True, response_parse_failed=False))
            return None
        payload, parse_meta = parse_json_object_with_diagnostics(text)
        if not payload:
            parse_reason = str(parse_meta.get("reason") or "parse_failed")
            if parse_reason == "model_output_noncompliant":
                self.logger.warning(
                    "Prompt模型返回不合规",
                    extra=build_log_context(
                        event=f"{prompt_type}_model_output_noncompliant",
                        **context,
                        parse_failure_reason=parse_reason,
                        response_parse_failed=True,
                        used_fallback=True,
                        response_length=len(text),
                        response_prefix=text[:240],
                        response_suffix=text[-240:],
                    ),
                )
            else:
                self.logger.warning(
                    "Prompt解析器兜底失败",
                    extra=build_log_context(
                        event=f"{prompt_type}_parser_fallback_failed",
                        **context,
                        parse_failure_reason=parse_reason,
                        parse_attempt_count=int(parse_meta.get("attempt_count") or 0),
                        response_parse_failed=True,
                        used_fallback=True,
                        response_length=len(text),
                        response_prefix=text[:240],
                        response_suffix=text[-240:],
                    ),
                )
            self.logger.warning(
                f"Prompt解析失败原始响应={self._format_parse_failed_response(text)}",
                extra=build_log_context(
                    event=f"{prompt_type}_parse_failed_payload",
                    **context,
                    parse_failure_reason=parse_reason,
                    parse_attempt_count=int(parse_meta.get("attempt_count") or 0),
                    response_parse_failed=True,
                    used_fallback=True,
                ),
            )
            return None
        return payload

    async def _call_prompt_text(self, prompt_type: str, prompt: str, role: ModelRole, max_tokens: int = 2200, temperature: float = 0.45, sent_event: str = "", metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        context = {"prompt_type": prompt_type, "project_id": "", "chapter_id": "", "chapter_number": 0, "model_name": role.value, **(metadata or {})}
        self.logger.info("Prompt调用开始", extra=build_log_context(event=sent_event or f"{prompt_type}_prompt_sent", **context, used_fallback=False, response_parse_failed=False))
        result = await self.model_role_router.generate(role, prompt, max_tokens=max_tokens, temperature=temperature) if self._use_role_router() else await self.model_router.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        if not result.get("ok"):
            self.logger.error("Prompt调用失败", extra=build_log_context(event=f"{prompt_type}_prompt_failed", **context, error=str(result.get("error") or "unknown"), used_fallback=True, response_parse_failed=False))
            return None
        text = str(result.get("text") or "").strip()
        content = strip_code_fence(text) if text else ""
        if not content:
            self.logger.warning("Prompt空响应", extra=build_log_context(event=f"{prompt_type}_prompt_failed", **context, error="empty_response", used_fallback=True, response_parse_failed=False))
            return None
        return content

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
        require_model_success: bool = False,
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
        if require_model_success:
            self._raise_required_model_failure(ModelRole.CHAPTER_ANALYSIS, "章节分析")
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

    async def extract_continuation_memory(self, chapter_title: str, chapter_content: str, relevant_characters: List[Dict[str, Any]], global_constraints: Dict[str, Any], require_model_success: bool = False) -> Dict[str, Any]:
        payload = PromptInputBuilder.build_continuation_memory_input(chapter_title, chapter_content, relevant_characters, global_constraints)
        model_result = await self._call_prompt_json("continuation_memory_extracted", build_continuation_memory_prompt(payload), ModelRole.CONTINUATION_MEMORY_EXTRACTION, max_tokens=1400, temperature=0.25, sent_event="continuation_memory_prompt_sent", metadata={"chapter_id": "", "chapter_number": 0})
        if model_result:
            model_result["used_fallback"] = bool(model_result.get("used_fallback"))
            self.logger.info("续写型memory提取完成", extra=build_log_context(event="continuation_memory_extracted", prompt_type="continuation_memory", used_fallback=bool(model_result.get("used_fallback"))))
            return self._normalize_continuation_memory(model_result)
        if require_model_success:
            self._raise_required_model_failure(ModelRole.CONTINUATION_MEMORY_EXTRACTION, "续写记忆提取")
        return self._fallback_continuation_memory(chapter_title, chapter_content, global_constraints)

    async def generate_chapter_task(self, continuation_context, chapter_plan: Dict[str, Any]) -> Dict[str, Any]:
        payload = PromptInputBuilder.build_chapter_task_input(continuation_context, chapter_plan)
        model_result = await self._call_prompt_json("chapter_task", build_chapter_task_prompt(payload), ModelRole.CHAPTER_PLANNING, max_tokens=1200, temperature=0.3, sent_event="chapter_task_prompt_sent", metadata={"project_id": continuation_context.project_id, "chapter_id": continuation_context.chapter_id, "chapter_number": continuation_context.chapter_number})
        if model_result:
            model_result["used_fallback"] = bool(model_result.get("used_fallback"))
            self.logger.info("章节任务Prompt生成完成", extra=build_log_context(event="chapter_task_prompt_generated", prompt_type="chapter_task", used_fallback=bool(model_result.get("used_fallback"))))
            return self._normalize_chapter_task(model_result)
        return self._fallback_chapter_task(chapter_plan)

    async def rewrite_detemplated_draft(self, structural_draft: Dict[str, Any], chapter_task: Dict[str, Any], global_constraints: Dict[str, Any], style_requirements: Dict[str, Any]) -> Dict[str, Any]:
        payload = PromptInputBuilder.build_detemplate_input(structural_draft, chapter_task, global_constraints, style_requirements)
        text = await self._call_prompt_text("detemplate", build_detemplating_prompt(payload), ModelRole.DETEMPLATING_REWRITE, max_tokens=2600, temperature=0.5, sent_event="detemplate_prompt_sent", metadata={"project_id": str(structural_draft.get("project_id") or ""), "chapter_id": str(structural_draft.get("chapter_id") or ""), "chapter_number": int(structural_draft.get("chapter_number") or 0)})
        if text:
            return {
                "content": text,
                "used_fallback": False,
                "integrity_failed": False,
                "display_fallback_to_structural": False,
            }
        return {
            "content": str(structural_draft.get("content") or ""),
            "used_fallback": True,
            "integrity_failed": False,
            "display_fallback_to_structural": True,
        }

    async def revise_detemplated_draft(
        self,
        structural_draft: Dict[str, Any],
        detemplated_draft: Dict[str, Any],
        chapter_task: Dict[str, Any],
        global_constraints: Dict[str, Any],
        style_requirements: Dict[str, Any],
        issue_list: List[Dict[str, Any]],
        revision_suggestion: str = "",
    ) -> Dict[str, Any]:
        payload = PromptInputBuilder.build_detemplate_revision_input(
            structural_draft=structural_draft,
            detemplated_draft=detemplated_draft,
            chapter_task=chapter_task,
            global_constraints=global_constraints,
            style_requirements=style_requirements,
            issue_list=issue_list,
            revision_suggestion=revision_suggestion,
        )
        text = await self._call_prompt_text(
            "detemplate_revision",
            build_detemplating_revision_prompt(payload),
            ModelRole.DETEMPLATING_REWRITE,
            max_tokens=2800,
            temperature=0.45,
            sent_event="detemplate_revision_prompt_sent",
            metadata={
                "project_id": str(structural_draft.get("project_id") or ""),
                "chapter_id": str(structural_draft.get("chapter_id") or ""),
                "chapter_number": int(structural_draft.get("chapter_number") or 0),
            },
        )
        if text:
            return {
                "content": text,
                "used_fallback": False,
                "integrity_failed": False,
                "display_fallback_to_structural": False,
                "revision_applied": True,
            }
        return {
            "content": str(detemplated_draft.get("content") or structural_draft.get("content") or ""),
            "used_fallback": True,
            "integrity_failed": True,
            "display_fallback_to_structural": bool(detemplated_draft.get("display_fallback_to_structural")),
            "revision_applied": False,
        }

    async def generate_structural_draft(self, chapter_task: Dict[str, Any], continuation_context, global_constraints: Dict[str, Any], target_word_count: int) -> Dict[str, Any]:
        payload = PromptInputBuilder.build_structural_draft_input(
            chapter_task=chapter_task,
            global_constraints=global_constraints,
            continuation_context=continuation_context,
            relevant_characters=continuation_context.relevant_characters or [],
            relevant_foreshadowing=continuation_context.relevant_foreshadowing or [],
        )
        payload["target_word_count"] = int(target_word_count or 0)
        prompt = build_structural_draft_prompt(payload)
        model_result = await self._call_prompt_json(
            "structural_draft",
            prompt,
            ModelRole.STRUCTURAL_WRITING,
            max_tokens=2600,
            temperature=0.45,
            sent_event="structural_prompt_sent",
            metadata={"project_id": continuation_context.project_id, "chapter_id": continuation_context.chapter_id, "chapter_number": continuation_context.chapter_number},
        )
        if model_result:
            normalized = self._normalize_structural_draft_result(model_result)
            self.logger.info("结构稿Prompt生成完成", extra=build_log_context(event="structural_draft_generated", prompt_type="structural_draft", project_id=continuation_context.project_id, chapter_id=str(chapter_task.get("chapter_id") or ""), chapter_number=int(chapter_task.get("chapter_number") or 0), model_name="primary_or_backup", used_fallback=False, response_parse_failed=False))
            return normalized
        fallback_text = await self._call_prompt_text(
            "structural_draft_text_fallback",
            prompt,
            ModelRole.STRUCTURAL_WRITING,
            max_tokens=2600,
            temperature=0.35,
            sent_event="structural_prompt_text_fallback_sent",
            metadata={"project_id": continuation_context.project_id, "chapter_id": continuation_context.chapter_id, "chapter_number": continuation_context.chapter_number},
        )
        if fallback_text:
            parsed = parse_json_object(fallback_text)
            if parsed:
                normalized = self._normalize_structural_draft_result(parsed)
                if str(normalized.get("content") or "").strip():
                    normalized["used_fallback"] = True
                    return normalized
            plain_text = strip_code_fence(fallback_text).strip()
            if plain_text:
                return {
                    "title": "",
                    "content": plain_text,
                    "new_events": [],
                    "possible_continuity_flags": [],
                    "used_fallback": True,
                }
        return {
            "title": "",
            "content": "",
            "new_events": [],
            "possible_continuity_flags": [],
            "used_fallback": True,
        }

    async def check_draft_integrity(self, structural_draft: Dict[str, Any], detemplated_draft: Dict[str, Any], chapter_task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = PromptInputBuilder.build_integrity_check_input(structural_draft, detemplated_draft, chapter_task)
        model_result = await self._call_prompt_json("integrity_check", build_integrity_check_prompt(payload), ModelRole.CONSISTENCY_VALIDATION, max_tokens=1200, temperature=0.2, sent_event="integrity_check_prompt_sent", metadata={"project_id": str(structural_draft.get("project_id") or ""), "chapter_id": str(structural_draft.get("chapter_id") or ""), "chapter_number": int(structural_draft.get("chapter_number") or 0)})
        if model_result:
            self.logger.info("一致性校验Prompt完成", extra=build_log_context(event="integrity_check_finished", prompt_type="integrity_check", used_fallback=False))
            return self._normalize_integrity_check(model_result)
        return None

    async def backfill_title(self, chapter_task: Dict[str, Any], content: str, recent_context: Dict[str, Any]) -> str:
        payload = PromptInputBuilder.build_title_backfill_input(chapter_task, content, recent_context)
        model_result = await self._call_prompt_json("title_backfill", build_title_backfill_prompt(payload), ModelRole.TITLE_BACKFILL, max_tokens=300, temperature=0.3, sent_event="title_backfill_prompt_sent", metadata={"project_id": str(recent_context.get("project_id") or ""), "chapter_id": str(chapter_task.get("chapter_id") or ""), "chapter_number": int(chapter_task.get("chapter_number") or 0)})
        title = str((model_result or {}).get("title") or "").strip()
        if title:
            self.logger.info("标题补写完成", extra=build_log_context(event="title_backfill_generated", prompt_type="title_backfill", used_fallback=False))
        return title

    def _normalize_structural_draft_result(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        title = str(draft.get("title") or draft.get("chapter_title") or "").strip()
        content = str(draft.get("content") or draft.get("chapter_text") or draft.get("result_text") or "").strip()
        return {
            "title": title,
            "content": content,
            "new_events": [item for item in (draft.get("new_events") or draft.get("new_facts") or []) if isinstance(item, dict)],
            "possible_continuity_flags": [str(x).strip() for x in (draft.get("possible_continuity_flags") or []) if str(x).strip()],
            "used_fallback": bool(draft.get("used_fallback")),
        }

    def _normalize_continuation_memory(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "scene_summary": str(draft.get("scene_summary") or "").strip(),
            "scene_state": draft.get("scene_state") if isinstance(draft.get("scene_state"), dict) else {},
            "protagonist_state": draft.get("protagonist_state") if isinstance(draft.get("protagonist_state"), dict) else {},
            "active_characters": [item for item in (draft.get("active_characters") or []) if isinstance(item, dict)][:6],
            "active_conflicts": [str(x).strip() for x in (draft.get("active_conflicts") or []) if str(x).strip()][:6],
            "immediate_threads": [str(x).strip() for x in (draft.get("immediate_threads") or []) if str(x).strip()][:6],
            "long_term_threads": [str(x).strip() for x in (draft.get("long_term_threads") or []) if str(x).strip()][:8],
            "recent_reveals": [str(x).strip() for x in (draft.get("recent_reveals") or []) if str(x).strip()][:8],
            "must_continue_points": [str(x).strip() for x in (draft.get("must_continue_points") or []) if str(x).strip()][:8],
            "forbidden_jumps": [str(x).strip() for x in (draft.get("forbidden_jumps") or []) if str(x).strip()][:8],
            "tone_and_pacing": draft.get("tone_and_pacing") if isinstance(draft.get("tone_and_pacing"), dict) else {},
            "last_hook": str(draft.get("last_hook") or "").strip(),
            "used_fallback": bool(draft.get("used_fallback")),
        }

    def _fallback_continuation_memory(self, chapter_title: str, chapter_content: str, global_constraints: Dict[str, Any]) -> Dict[str, Any]:
        text = str(chapter_content or "").strip()
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
        must_continue = [paragraphs[-1]] if paragraphs else []
        must_continue.extend([str(x) for x in ((global_constraints or {}).get("must_keep_threads") or []) if str(x).strip()][:3])
        return {
            "scene_summary": text[:180],
            "scene_state": {"environment": paragraphs[-1][:60] if paragraphs else ""},
            "protagonist_state": {"current_goal": paragraphs[0][:60] if paragraphs else ""},
            "active_characters": [],
            "active_conflicts": [paragraphs[1][:60]] if len(paragraphs) > 1 else [],
            "immediate_threads": must_continue[:3],
            "long_term_threads": [str(x) for x in ((global_constraints or {}).get("must_keep_threads") or []) if str(x).strip()][:5],
            "recent_reveals": [paragraphs[-2][:60]] if len(paragraphs) > 1 else [],
            "must_continue_points": must_continue[:6],
            "forbidden_jumps": ["不得突然时间跳跃"],
            "tone_and_pacing": {"tone": "", "pace": ""},
            "last_hook": paragraphs[-1][:80] if paragraphs else chapter_title,
            "used_fallback": True,
        }

    def _normalize_chapter_task(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "chapter_function": str(draft.get("chapter_function") or CHAPTER_FUNCTION_ADVANCE_INVESTIGATION).strip(),
            "goals": [str(x).strip() for x in (draft.get("goals") or []) if str(x).strip()][:6],
            "must_continue_points": [str(x).strip() for x in (draft.get("must_continue_points") or []) if str(x).strip()][:8],
            "forbidden_jumps": [str(x).strip() for x in (draft.get("forbidden_jumps") or []) if str(x).strip()][:8],
            "required_foreshadowing_action": str(draft.get("required_foreshadowing_action") or DEFAULT_FORESHADOWING_ACTION).strip(),
            "required_hook_strength": str(draft.get("required_hook_strength") or DEFAULT_HOOK_STRENGTH).strip(),
            "pace_target": str(draft.get("pace_target") or DEFAULT_PACE_TARGET).strip(),
            "opening_continuation": str(draft.get("opening_continuation") or "").strip(),
            "chapter_payoff": str(draft.get("chapter_payoff") or "").strip(),
            "style_bias": str(draft.get("style_bias") or "").strip(),
            "used_fallback": bool(draft.get("used_fallback")),
        }

    def _fallback_chapter_task(self, chapter_plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "chapter_function": CHAPTER_FUNCTION_ADVANCE_INVESTIGATION,
            "goals": [str(x) for x in [chapter_plan.get("goal"), chapter_plan.get("progression")] if str(x or "").strip()],
            "must_continue_points": [str(chapter_plan.get("ending_hook") or "")] if str(chapter_plan.get("ending_hook") or "").strip() else [],
            "forbidden_jumps": ["不得突然时间跳跃"],
            "required_foreshadowing_action": DEFAULT_FORESHADOWING_ACTION,
            "required_hook_strength": DEFAULT_HOOK_STRENGTH,
            "pace_target": DEFAULT_PACE_TARGET,
            "opening_continuation": "",
            "chapter_payoff": str(chapter_plan.get("ending_hook") or chapter_plan.get("goal") or ""),
            "style_bias": "",
            "used_fallback": True,
        }

    def _normalize_integrity_check(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "event_integrity_ok": bool(draft.get("event_integrity_ok")),
            "motivation_integrity_ok": bool(draft.get("motivation_integrity_ok")),
            "foreshadowing_integrity_ok": bool(draft.get("foreshadowing_integrity_ok")),
            "hook_integrity_ok": bool(draft.get("hook_integrity_ok")),
            "continuity_ok": bool(draft.get("continuity_ok")),
            "arc_consistency_ok": bool(draft.get("arc_consistency_ok", True)),
            "title_alignment_ok": bool(draft.get("title_alignment_ok", True)),
            "progression_integrity_ok": bool(draft.get("progression_integrity_ok", True)),
            "risk_notes": [str(x).strip() for x in (draft.get("risk_notes") or []) if str(x).strip()][:8],
        }

    async def analyze_global_story(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        require_model_success = bool(payload.get("require_model_success"))
        model_result = await self._call_prompt_json(
            "global_analysis",
            build_global_analysis_prompt(payload),
            ModelRole.GLOBAL_ANALYSIS,
            max_tokens=2400,
            temperature=0.2,
            sent_event="global_analysis_prompt_sent",
            metadata={"project_id": str(payload.get("project_id") or "")},
        )
        if model_result:
            normalized = self._normalize_global_analysis(model_result, payload)
            normalized["used_fallback"] = bool(model_result.get("used_fallback"))
            return normalized
        if require_model_success:
            self._raise_required_model_failure(ModelRole.GLOBAL_ANALYSIS, "全书分析")
        return self._fallback_global_analysis(payload)

    async def extract_plot_arcs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        require_model_success = bool(payload.get("require_model_success"))
        model_result = await self._call_prompt_json(
            "plot_arc_extraction",
            build_plot_arc_extraction_prompt(payload),
            ModelRole.PLOT_ARC_EXTRACTION,
            max_tokens=2600,
            temperature=0.25,
            sent_event="plot_arc_extraction_prompt_sent",
            metadata={"project_id": str(payload.get("project_id") or "")},
        )
        if model_result:
            normalized = self._normalize_plot_arc_payload(model_result, payload)
            normalized["used_fallback"] = bool(model_result.get("used_fallback"))
            return normalized
        if require_model_success:
            self._raise_required_model_failure(ModelRole.PLOT_ARC_EXTRACTION, "剧情弧抽取")
        return self._fallback_plot_arc_payload(payload)

    def _normalize_global_analysis(self, result: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        world = result.get("world_facts") if isinstance(result.get("world_facts"), dict) else {}
        style = result.get("style_profile") if isinstance(result.get("style_profile"), dict) else {}
        constraints = result.get("global_constraints") if isinstance(result.get("global_constraints"), dict) else {}
        characters = []
        for item in (result.get("characters") or []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            characters.append(
                {
                    "name": name,
                    "traits": [str(x).strip() for x in (item.get("traits") or []) if str(x).strip()][:6],
                    "relationships": item.get("relationships") if isinstance(item.get("relationships"), dict) else {},
                }
            )
        return {
            "characters": characters[:12],
            "world_facts": {
                "background": [str(x).strip() for x in (world.get("background") or []) if str(x).strip()][:12],
                "power_system": [str(x).strip() for x in (world.get("power_system") or []) if str(x).strip()][:12],
                "organizations": [str(x).strip() for x in (world.get("organizations") or []) if str(x).strip()][:12],
                "locations": [str(x).strip() for x in (world.get("locations") or []) if str(x).strip()][:12],
                "rules": [str(x).strip() for x in (world.get("rules") or []) if str(x).strip()][:12],
                "artifacts": [str(x).strip() for x in (world.get("artifacts") or []) if str(x).strip()][:12],
            },
            "style_profile": {
                "narrative_pov": str(style.get("narrative_pov") or "").strip(),
                "tone_tags": [str(x).strip() for x in (style.get("tone_tags") or []) if str(x).strip()][:8],
                "rhythm_tags": [str(x).strip() for x in (style.get("rhythm_tags") or []) if str(x).strip()][:8],
            },
            "global_constraints": {
                "main_plot": str(constraints.get("main_plot") or "").strip(),
                "hidden_plot": str(constraints.get("hidden_plot") or "").strip(),
                "core_selling_points": [str(x).strip() for x in (constraints.get("core_selling_points") or []) if str(x).strip()][:10],
                "protagonist_core_traits": [str(x).strip() for x in (constraints.get("protagonist_core_traits") or []) if str(x).strip()][:10],
                "must_keep_threads": [str(x).strip() for x in (constraints.get("must_keep_threads") or []) if str(x).strip()][:20],
                "genre_guardrails": [str(x).strip() for x in (constraints.get("genre_guardrails") or []) if str(x).strip()][:12],
            },
            "chapter_summaries": [str(x).strip() for x in (result.get("chapter_summaries") or []) if str(x).strip()][:120],
            "main_plot_lines": [str(x).strip() for x in (result.get("main_plot_lines") or []) if str(x).strip()][:12],
        }

    def _fallback_global_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        batch_digests = [item for item in (payload.get("batch_digests") or []) if isinstance(item, dict)]
        chapters = [item for item in (payload.get("chapters") or []) if isinstance(item, dict)]
        summaries = []
        for item in batch_digests:
            digest_text = str(item.get("digest") or "").strip().replace("\n", " ")
            if digest_text:
                summaries.append(digest_text)
        if not summaries:
            for item in chapters[:120]:
                title = str(item.get("title") or "").strip()
                preview = str(item.get("content_preview") or "").strip().replace("\n", " ")
                text = f"{title}：{preview}".strip("：")
                if text:
                    summaries.append(text)
        outline_context = payload.get("outline_context") if isinstance(payload.get("outline_context"), dict) else {}
        outline_digest = payload.get("outline_digest") if isinstance(payload.get("outline_digest"), dict) else {}
        main_plot = str(outline_digest.get("premise") or outline_context.get("premise") or "").strip()
        hidden_plot = str(outline_digest.get("summary") or outline_context.get("story_background") or "").strip()
        world_setting = str(outline_digest.get("style_guidance") or outline_context.get("world_setting") or "").strip()
        return {
            "characters": [],
            "world_facts": {
                "background": [world_setting] if world_setting else [],
                "power_system": [],
                "organizations": [],
                "locations": [],
                "rules": [],
                "artifacts": [],
            },
            "style_profile": {
                "narrative_pov": "third_person_limited",
                "tone_tags": [],
                "rhythm_tags": [],
            },
            "global_constraints": {
                "main_plot": main_plot,
                "hidden_plot": hidden_plot,
                "core_selling_points": [],
                "protagonist_core_traits": [],
                "must_keep_threads": [main_plot] if main_plot else [],
                "genre_guardrails": [],
            },
            "chapter_summaries": summaries,
            "main_plot_lines": [x for x in [main_plot, hidden_plot] if x],
            "used_fallback": True,
        }

    def _normalize_arc_type(self, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"main", "main_story", "mainline"}:
            normalized = "main_arc"
        if normalized in {"character", "character_story"}:
            normalized = "character_arc"
        if normalized in {"support", "supporting", "sub"}:
            normalized = "supporting_arc"
        return normalized if normalized in {"main_arc", "character_arc", "supporting_arc"} else "supporting_arc"

    def _normalize_arc_priority(self, value: str, arc_type: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"critical", "core"}:
            return "core"
        if normalized in {"major", "important"}:
            return "major"
        if normalized in {"minor", "low"}:
            return "minor"
        if arc_type == "main_arc":
            return "core"
        if arc_type == "character_arc":
            return "major"
        return "minor"

    def _normalize_arc_status(self, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"active", "dormant", "completed", "archived"}:
            return normalized
        return "active"

    def _infer_arc_stage(self, value: str, covered_count: int, status: str) -> str:
        normalized = str(value or "").strip().lower()
        stage_order = ["setup", "early_push", "escalation", "crisis", "turning_point", "payoff", "aftermath"]
        if normalized in stage_order:
            return normalized
        if status == "completed":
            return "payoff"
        if status == "archived":
            return "aftermath"
        if covered_count >= 20:
            return "payoff"
        if covered_count >= 14:
            return "turning_point"
        if covered_count >= 9:
            return "crisis"
        if covered_count >= 5:
            return "escalation"
        if covered_count >= 3:
            return "early_push"
        return "setup"

    def _normalize_stage_confidence(self, value: Any, covered_count: int, stage_reason: str) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence <= 0:
            confidence = 0.45 + min(0.4, covered_count * 0.04)
        if stage_reason:
            confidence = max(confidence, 0.55)
        return max(0.35, min(0.95, confidence))

    def _priority_rank(self, priority: str) -> int:
        return {"core": 0, "major": 1, "minor": 2}.get(str(priority or "").strip().lower(), 3)

    def _compact_arc_text(self, value: Any, fallback: str = "") -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            return fallback
        if len(text) <= 80:
            return text
        return f"{text[:80].rstrip('，；。,. ')}..."

    def _collect_recent_arc_lines(self, payload: Dict[str, Any], limit: int = 6) -> List[str]:
        global_analysis = payload.get("global_analysis") if isinstance(payload.get("global_analysis"), dict) else {}
        chapter_artifacts = [item for item in (payload.get("chapter_artifacts") or []) if isinstance(item, dict)]
        lines: List[str] = []
        for item in chapter_artifacts[-8:]:
            for candidate in (
                item.get("scene_summary"),
                item.get("analysis_summary"),
                item.get("goal"),
                item.get("conflict"),
                *(item.get("must_continue_points") or []),
            ):
                compact = self._compact_arc_text(candidate)
                if compact and compact not in lines:
                    lines.append(compact)
                if len(lines) >= limit:
                    return lines
        for candidate in (global_analysis.get("main_plot_lines") or []):
            compact = self._compact_arc_text(candidate)
            if compact and compact not in lines and "Story Arc" not in compact:
                lines.append(compact)
            if len(lines) >= limit:
                break
        return lines[:limit]

    def _build_supplemental_arcs(self, payload: Dict[str, Any], existing_arc_ids: List[str]) -> List[Dict[str, Any]]:
        project_id = str(payload.get("project_id") or "")
        global_analysis = payload.get("global_analysis") if isinstance(payload.get("global_analysis"), dict) else {}
        chapter_artifacts = [item for item in (payload.get("chapter_artifacts") or []) if isinstance(item, dict)]
        covered_chapter_ids = [str(item.get("chapter_id") or "") for item in chapter_artifacts[:8] if str(item.get("chapter_id") or "").strip()]
        characters = [item for item in (global_analysis.get("characters") or []) if isinstance(item, dict)]
        main_plot_lines = [str(x).strip() for x in (global_analysis.get("main_plot_lines") or []) if str(x).strip()]
        world_facts = global_analysis.get("world_facts") if isinstance(global_analysis.get("world_facts"), dict) else {}
        must_keep_threads = [str(x).strip() for x in ((global_analysis.get("global_constraints") or {}).get("must_keep_threads") or []) if str(x).strip()]
        recent_story_lines = self._collect_recent_arc_lines(payload)
        main_seed = recent_story_lines[0] if recent_story_lines else self._compact_arc_text(main_plot_lines[0] if main_plot_lines else "", "继续推进当前主线冲突")
        supplemental: List[Dict[str, Any]] = []

        if "arc_main_auto" not in existing_arc_ids and main_plot_lines:
            supplemental.append(
                {
                    "arc_id": "arc_main_auto",
                    "project_id": project_id,
                    "title": "主线推进弧",
                    "arc_type": "main_arc",
                    "priority": "core",
                    "status": "active",
                    "goal": self._compact_arc_text(main_plot_lines[0]),
                    "core_conflict": self._compact_arc_text(main_plot_lines[1] if len(main_plot_lines) > 1 else main_seed, main_seed),
                    "current_stage": self._infer_arc_stage("", len(covered_chapter_ids), "active"),
                    "stage_reason": "supplemented_from_main_plot_lines",
                    "stage_confidence": 0.58,
                    "covered_chapter_ids": covered_chapter_ids[:5],
                    "latest_progress_summary": main_seed,
                    "next_push_suggestion": self._compact_arc_text(must_keep_threads[0] if must_keep_threads else main_seed, "继续推进当前主线冲突"),
                }
            )
            existing_arc_ids.append("arc_main_auto")

        if characters and "arc_character_auto" not in existing_arc_ids:
            first_character = characters[0]
            name = str(first_character.get("name") or "核心角色").strip() or "核心角色"
            traits = [str(x).strip() for x in (first_character.get("traits") or []) if str(x).strip()]
            supplemental.append(
                {
                    "arc_id": "arc_character_auto",
                    "project_id": project_id,
                    "title": f"{name}人物弧",
                    "arc_type": "character_arc",
                    "priority": "major",
                    "status": "active",
                    "goal": traits[0] if traits else f"推动{name}发生关键改变",
                    "core_conflict": f"{name}必须在目标与代价之间做选择",
                    "current_stage": self._infer_arc_stage("", max(2, len(covered_chapter_ids) // 2), "active"),
                    "stage_reason": "supplemented_from_character_profile",
                    "stage_confidence": 0.56,
                    "related_characters": [name],
                    "covered_chapter_ids": covered_chapter_ids[:4],
                    "latest_progress_summary": f"{name}的人物压力线需要继续推进",
                    "next_push_suggestion": f"在下一章让{name}付出新的代价",
                }
            )
            existing_arc_ids.append("arc_character_auto")

        supporting_seed = [str(x).strip() for x in (world_facts.get("rules") or []) if str(x).strip()]
        supporting_seed.extend([str(x).strip() for x in (world_facts.get("background") or []) if str(x).strip()])
        supporting_seed.extend(must_keep_threads)
        supporting_seed.extend(main_plot_lines[:1])
        supporting_seed = [item for item in supporting_seed if item]
        if supporting_seed and "arc_supporting_auto" not in existing_arc_ids:
            supplemental.append(
                {
                    "arc_id": "arc_supporting_auto",
                    "project_id": project_id,
                    "title": "支线压力弧",
                    "arc_type": "supporting_arc",
                    "priority": "minor",
                    "status": "active",
                    "goal": self._compact_arc_text(supporting_seed[0]),
                    "core_conflict": self._compact_arc_text(supporting_seed[1] if len(supporting_seed) > 1 else supporting_seed[0]),
                    "current_stage": self._infer_arc_stage("", max(1, len(covered_chapter_ids) // 3), "active"),
                    "stage_reason": "supplemented_from_world_and_threads",
                    "stage_confidence": 0.52,
                    "related_world_rules": supporting_seed[:4],
                    "covered_chapter_ids": covered_chapter_ids[:3],
                    "latest_progress_summary": self._compact_arc_text(supporting_seed[0]),
                    "next_push_suggestion": self._compact_arc_text(supporting_seed[0], "让支线因素重新影响主线"),
                }
            )
        return supplemental

    def _stabilize_plot_arc_window(
        self,
        plot_arcs: List[Dict[str, Any]],
        bindings: List[Dict[str, Any]],
        payload: Dict[str, Any],
        requested_active_arc_ids: List[str],
    ) -> Dict[str, Any]:
        arc_map = {str(item.get("arc_id") or ""): item for item in plot_arcs if str(item.get("arc_id") or "").strip()}
        if len(arc_map) < 3:
            supplemental = self._build_supplemental_arcs(payload, list(arc_map.keys()))
            for item in supplemental:
                arc_map[item["arc_id"]] = item
        plot_arcs = list(arc_map.values())
        ranked_arcs = sorted(plot_arcs, key=lambda item: (self._priority_rank(item.get("priority") or ""), str(item.get("title") or "")))
        active_arc_ids = [arc_id for arc_id in requested_active_arc_ids if arc_id in arc_map and arc_map[arc_id].get("status") not in {"completed", "archived"}]
        if not active_arc_ids:
            active_arc_ids = [str(item.get("arc_id") or "") for item in ranked_arcs if item.get("status") == "active"]
        for item in ranked_arcs:
            arc_id = str(item.get("arc_id") or "")
            if len(active_arc_ids) >= 3:
                break
            if arc_id and arc_id not in active_arc_ids and item.get("status") not in {"completed", "archived"}:
                active_arc_ids.append(arc_id)
        active_arc_ids = active_arc_ids[:5]
        for item in plot_arcs:
            arc_id = str(item.get("arc_id") or "")
            if arc_id in active_arc_ids and item.get("status") not in {"completed", "archived"}:
                item["status"] = "active"
            elif item.get("status") not in {"completed", "archived"}:
                item["status"] = "dormant"
        if plot_arcs and not bindings:
            first_active_arc_id = active_arc_ids[0] if active_arc_ids else str(plot_arcs[0].get("arc_id") or "")
            chapter_artifacts = [item for item in (payload.get("chapter_artifacts") or []) if isinstance(item, dict)]
            bindings = [
                {
                    "chapter_id": str(item.get("chapter_id") or ""),
                    "chapter_number": int(item.get("chapter_number") or 0),
                    "arc_id": first_active_arc_id,
                    "binding_role": "primary",
                    "push_type": "advance",
                    "confidence": 0.55,
                }
                for item in chapter_artifacts[: min(5, len(chapter_artifacts))]
                if str(item.get("chapter_id") or "").strip() and first_active_arc_id
            ]
        return {
            "plot_arcs": sorted(plot_arcs, key=lambda item: (0 if item.get("status") == "active" else 1, self._priority_rank(item.get("priority") or ""), str(item.get("title") or ""))),
            "chapter_arc_bindings": bindings,
            "active_arc_ids": active_arc_ids,
        }

    def _normalize_plot_arc_payload(self, result: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        plot_arcs = []
        chapter_ids = {
            int(item.get("chapter_number") or 0): str(item.get("chapter_id") or "")
            for item in (payload.get("chapter_artifacts") or [])
            if isinstance(item, dict)
        }
        for item in (result.get("plot_arcs") or []):
            if not isinstance(item, dict):
                continue
            arc_id = str(item.get("arc_id") or "").strip()
            title = str(item.get("title") or "").strip()
            if not arc_id or not title:
                continue
            covered_chapter_ids = [str(x).strip() for x in (item.get("covered_chapter_ids") or []) if str(x).strip()][:30]
            arc_type = self._normalize_arc_type(str(item.get("arc_type") or "supporting_arc"))
            priority = self._normalize_arc_priority(str(item.get("priority") or ""), arc_type)
            status = self._normalize_arc_status(str(item.get("status") or "active"))
            current_stage = self._infer_arc_stage(str(item.get("current_stage") or ""), len(covered_chapter_ids), status)
            stage_reason = str(item.get("stage_reason") or "").strip() or f"inferred_from_{max(1, len(covered_chapter_ids))}_bound_chapters"
            plot_arcs.append(
                {
                    "arc_id": arc_id,
                    "project_id": str(payload.get("project_id") or item.get("project_id") or "").strip(),
                    "title": title,
                    "arc_type": arc_type,
                    "priority": priority,
                    "status": status,
                    "goal": str(item.get("goal") or "").strip(),
                    "core_conflict": str(item.get("core_conflict") or "").strip(),
                    "stakes": str(item.get("stakes") or "").strip(),
                    "start_chapter_number": int(item.get("start_chapter_number") or 0),
                    "end_chapter_number": int(item.get("end_chapter_number") or 0),
                    "current_stage": current_stage,
                    "stage_reason": stage_reason,
                    "stage_confidence": self._normalize_stage_confidence(item.get("stage_confidence"), len(covered_chapter_ids), stage_reason),
                    "key_turning_points": [str(x).strip() for x in (item.get("key_turning_points") or []) if str(x).strip()][:8],
                    "must_resolve_points": [str(x).strip() for x in (item.get("must_resolve_points") or []) if str(x).strip()][:8],
                    "related_characters": [str(x).strip() for x in (item.get("related_characters") or []) if str(x).strip()][:8],
                    "related_items": [str(x).strip() for x in (item.get("related_items") or []) if str(x).strip()][:8],
                    "related_world_rules": [str(x).strip() for x in (item.get("related_world_rules") or []) if str(x).strip()][:8],
                    "covered_chapter_ids": covered_chapter_ids,
                    "latest_progress_summary": str(item.get("latest_progress_summary") or "").strip(),
                    "latest_result": str(item.get("latest_result") or "").strip(),
                    "next_push_suggestion": str(item.get("next_push_suggestion") or "").strip(),
                }
            )
        bindings = []
        for item in (result.get("chapter_arc_bindings") or []):
            if not isinstance(item, dict):
                continue
            chapter_number = int(item.get("chapter_number") or 0)
            chapter_id = str(item.get("chapter_id") or chapter_ids.get(chapter_number) or "").strip()
            arc_id = str(item.get("arc_id") or "").strip()
            if not chapter_id or not arc_id:
                continue
            bindings.append(
                {
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "arc_id": arc_id,
                    "binding_role": str(item.get("binding_role") or "background").strip(),
                    "push_type": str(item.get("push_type") or "advance").strip(),
                    "confidence": float(item.get("confidence") or 0.6),
                }
            )
        active_arc_ids = [str(x).strip() for x in (result.get("active_arc_ids") or []) if str(x).strip()]
        return self._stabilize_plot_arc_window(plot_arcs, bindings, payload, active_arc_ids)

    def _fallback_plot_arc_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        global_analysis = payload.get("global_analysis") if isinstance(payload.get("global_analysis"), dict) else {}
        chapter_artifacts = [item for item in (payload.get("chapter_artifacts") or []) if isinstance(item, dict)]
        main_plot_lines = [str(x).strip() for x in (global_analysis.get("main_plot_lines") or []) if str(x).strip()]
        recent_story_lines = self._collect_recent_arc_lines(payload)
        main_seed = recent_story_lines[0] if recent_story_lines else self._compact_arc_text(main_plot_lines[0] if main_plot_lines else "", "继续推进当前主线冲突")
        chapter_bindings = []
        plot_arcs = []
        if main_plot_lines:
            arc_id = "arc_main_auto"
            plot_arcs.append(
                {
                    "arc_id": arc_id,
                    "project_id": str(payload.get("project_id") or ""),
                    "title": "主线推进弧",
                    "arc_type": "main_arc",
                    "priority": "core",
                    "status": "active",
                    "goal": self._compact_arc_text(main_plot_lines[0]),
                    "core_conflict": self._compact_arc_text(main_plot_lines[1] if len(main_plot_lines) > 1 else main_seed, main_seed),
                    "stakes": "",
                    "start_chapter_number": 1,
                    "end_chapter_number": 0,
                    "current_stage": "setup",
                    "stage_reason": "fallback_global_analysis",
                    "stage_confidence": 0.4,
                    "key_turning_points": [],
                    "must_resolve_points": [],
                    "related_characters": [str(item.get("name") or "") for item in (global_analysis.get("characters") or []) if isinstance(item, dict)][:4],
                    "related_items": [],
                    "related_world_rules": [str(x).strip() for x in ((global_analysis.get("world_facts") or {}).get("rules") or []) if str(x).strip()][:4],
                    "covered_chapter_ids": [str(item.get("chapter_id") or "") for item in chapter_artifacts[:5] if str(item.get("chapter_id") or "").strip()],
                    "latest_progress_summary": main_seed,
                    "latest_result": "",
                    "next_push_suggestion": main_seed,
                }
            )
            for item in chapter_artifacts[: min(len(chapter_artifacts), 5)]:
                chapter_bindings.append(
                    {
                        "chapter_id": str(item.get("chapter_id") or ""),
                        "chapter_number": int(item.get("chapter_number") or 0),
                        "arc_id": arc_id,
                        "binding_role": "primary",
                        "push_type": "advance",
                        "confidence": 0.55,
                    }
                )
        stabilized = self._stabilize_plot_arc_window(
            plot_arcs,
            chapter_bindings,
            payload,
            [item["arc_id"] for item in plot_arcs[:5]],
        )
        stabilized["used_fallback"] = True
        return stabilized
