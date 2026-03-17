from __future__ import annotations

import asyncio
import json
import re
from typing import Dict, Any

from application.agent_mvp.chapter_splitter import split_into_chapters
from application.agent_mvp.memory import merge_memory
from application.agent_mvp.model_router import ModelRouter
from application.agent_mvp.models import TaskContext, ToolResult
from application.agent_mvp.recovery import RecoveryPipeline


class AnalysisTool:
    name = "AnalysisTool"
    side_effect_type = "read"

    def __init__(self, llm_client=None, backup_llm_client=None):
        self.llm_client = llm_client
        self.backup_llm_client = backup_llm_client
        self.model_router = ModelRouter(llm_client, backup_llm_client)
        self.recovery = RecoveryPipeline(max_retries=2)

    def execute(self, task_context: TaskContext, tool_input: Dict[str, Any]) -> ToolResult:
        try:
            asyncio.get_running_loop()
            return ToolResult(
                status="failed",
                error={"code": "ASYNC_REQUIRED", "message": "请使用execute_async", "is_retryable": False},
                observation="当前处于异步上下文，请调用execute_async",
                progress_made=False
            )
        except RuntimeError:
            return asyncio.run(self.execute_async(task_context, tool_input))

    async def execute_async(self, task_context: TaskContext, tool_input: Dict[str, Any]) -> ToolResult:
        mode = str(tool_input.get("mode") or "incremental_mode").strip()
        novel_text = str(tool_input.get("novel_text") or "").strip()
        initial_setting = str(tool_input.get("initial_setting") or "").strip()
        source_text = novel_text or initial_setting
        if mode == "structure_mode":
            if not source_text:
                return ToolResult(
                    status="failed",
                    error={"code": "INVALID_TEXT", "message": "novel_text或initial_setting不能为空", "is_retryable": False},
                    observation="缺少小说文本，无法拆章节",
                    progress_made=False
                )
            chapters = split_into_chapters(source_text)
            return ToolResult(
                status="success",
                payload={
                    "chapters": [
                        {"title": chapter.title, "content": chapter.content, "index": chapter.index}
                        for chapter in chapters
                    ]
                },
                observation=f"完成章节拆分，共{len(chapters)}章",
                progress_made=bool(chapters)
            )

        if mode == "consolidate_mode":
            memory_payload = tool_input.get("memory") or {}
            if not isinstance(memory_payload, dict):
                memory_payload = {}
            consolidated = self._consolidate_memory(memory_payload)
            return ToolResult(
                status="success",
                payload=consolidated,
                observation="完成全局收敛",
                progress_made=True
            )

        chapter_payload = tool_input.get("chapter")
        if isinstance(chapter_payload, dict):
            source_text = str(chapter_payload.get("content") or "").strip()
            chapter_title = str(chapter_payload.get("title") or "").strip()
        else:
            chapter_title = str(tool_input.get("chapter_title") or "").strip()
        if not source_text:
            return ToolResult(
                status="failed",
                error={"code": "INVALID_TEXT", "message": "chapter内容不能为空", "is_retryable": False},
                observation="缺少章节文本，无法分析",
                progress_made=False
            )

        async def _execute() -> Dict[str, Any]:
            if self.llm_client is None:
                raise RuntimeError("primary_unavailable")
            return await self._analyze_with_router(source_text, use_backup=False)

        async def _repair() -> Dict[str, Any]:
            fixed_text = re.sub(r"\s+", " ", source_text).strip()
            if self.llm_client is None:
                raise RuntimeError("primary_unavailable")
            return await self._analyze_with_router(fixed_text, use_backup=False)

        async def _fallback() -> Dict[str, Any]:
            if self.backup_llm_client is None:
                raise RuntimeError("backup_unavailable")
            return await self._analyze_with_router(source_text, use_backup=True)

        def _degrade() -> Dict[str, Any]:
            return self._fallback_analysis(source_text)

        recovered = await self.recovery.run(_execute, _repair, _fallback, _degrade)
        if not recovered.ok:
            return ToolResult(
                status="failed",
                error={"code": "ANALYSIS_FAILED", "message": recovered.error, "is_retryable": False},
                observation="结构整理失败",
                progress_made=False
            )
        result = recovered.data or self._fallback_analysis(source_text)

        incremental_memory = {
            "characters": result.get("characters") or [],
            "world_settings": result.get("world_settings") or [],
            "plot_outline": result.get("plot_outline") or [],
            "writing_style": result.get("writing_style") or {},
            "current_progress": {
                "latest_chapter_number": int(chapter_payload.get("index") or 0) if isinstance(chapter_payload, dict) else 0,
                "latest_goal": chapter_title,
                "last_summary": f"{chapter_title}分析完成" if chapter_title else "章节分析完成"
            }
        }
        return ToolResult(
            status="success",
            payload=incremental_memory,
            observation="完成章节增量分析",
            progress_made=True
        )

    async def _analyze_with_router(self, text: str, use_backup: bool) -> Dict[str, Any]:
        prompt = (
            "请分析以下小说文本并只输出JSON对象，不要输出任何额外说明。"
            "JSON结构必须为："
            "{\"characters\":[{\"name\":\"\",\"traits\":[],\"relationships\":{}}],"
            "\"world_settings\":[],\"plot_outline\":[],"
            "\"writing_style\":{\"tone\":\"\",\"pacing\":\"\",\"narrative_style\":\"\"},"
            "\"current_progress\":{\"latest_chapter_number\":0,\"latest_goal\":\"\",\"last_summary\":\"\"}}"
            f"\n\n小说文本：\n{text[:12000]}"
        )
        if use_backup:
            raw = await self.backup_llm_client.generate(prompt, max_tokens=1800, temperature=0.3)
        else:
            result = await self.model_router.generate(prompt, max_tokens=1800, temperature=0.3)
            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "router_failed")
            raw = result["text"]
        return self._parse_analysis_json(raw)

    def _parse_analysis_json(self, text: str) -> Dict[str, Any]:
        content = text.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
            content = re.sub(r"\n?```$", "", content).strip()
        data = json.loads(content)
        writing_style = data.get("writing_style") or data.get("style_profile") or {}
        return {
            "characters": data.get("characters") or [],
            "world_settings": data.get("world_settings") or [],
            "plot_outline": data.get("plot_outline") or data.get("plot_threads") or [],
            "writing_style": {
                "tone": writing_style.get("tone") or "",
                "pacing": writing_style.get("pacing") or "",
                "narrative_style": writing_style.get("narrative_style") or ""
            },
            "current_progress": data.get("current_progress") or {
                "latest_chapter_number": 0,
                "latest_goal": "",
                "last_summary": ""
            }
        }

    def _fallback_analysis(self, novel_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in novel_text.splitlines() if line.strip()]
        sample = " ".join(lines[:5])[:200]
        return {
            "characters": [],
            "world_settings": [sample] if sample else [],
            "plot_outline": ["主线推进：根据文本线索逐步展开"],
            "writing_style": {
                "tone": "叙事",
                "pacing": "中速",
                "narrative_style": "第三人称"
            },
            "current_progress": {
                "latest_chapter_number": 0,
                "latest_goal": "",
                "last_summary": ""
            }
        }

    def _consolidate_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        merged = merge_memory(memory, {})
        world_settings = merged.get("world_settings") or []
        plot_outline = merged.get("plot_outline") or []
        if len(world_settings) > 6:
            merged["world_settings"] = world_settings[:6]
        if len(plot_outline) > 10:
            merged["plot_outline"] = plot_outline[:10]
        style = merged.get("writing_style") or {}
        merged["writing_style"] = {
            "tone": str(style.get("tone") or "").strip() or "叙事",
            "pacing": str(style.get("pacing") or "").strip() or "中速",
            "narrative_style": str(style.get("narrative_style") or "").strip() or "第三人称"
        }
        merged["style_profile"] = dict(merged["writing_style"])
        return merged


class ProjectInitTool:
    name = "ProjectInitTool"
    side_effect_type = "read"

    def __init__(self, llm_client=None, backup_llm_client=None):
        self.llm_client = llm_client
        self.backup_llm_client = backup_llm_client
        self.model_router = ModelRouter(llm_client, backup_llm_client)
        self.recovery = RecoveryPipeline(max_retries=2)

    async def execute_async(self, task_context: TaskContext, tool_input: Dict[str, Any]) -> ToolResult:
        name = str(tool_input.get("name") or "").strip()
        genre = str(tool_input.get("genre") or "xuanhuan").strip()
        style = str(tool_input.get("style") or "").strip()
        protagonist = str(tool_input.get("protagonist") or "").strip()
        worldview = str(tool_input.get("worldview") or "").strip()
        if not name or not protagonist:
            return ToolResult(
                status="failed",
                error={"code": "INVALID_INPUT", "message": "name和protagonist不能为空", "is_retryable": False},
                observation="初始化参数不完整",
                progress_made=False
            )

        async def _execute() -> Dict[str, Any]:
            if self.llm_client is None:
                raise RuntimeError("primary_unavailable")
            return await self._init_with_router(name, genre, style, protagonist, worldview, use_backup=False)

        async def _repair() -> Dict[str, Any]:
            repaired_worldview = worldview or f"{genre}世界在动荡中重塑秩序"
            return await self._init_with_router(name, genre, style, protagonist, repaired_worldview, use_backup=False)

        async def _fallback() -> Dict[str, Any]:
            if self.backup_llm_client is None:
                raise RuntimeError("backup_unavailable")
            return await self._init_with_router(name, genre, style, protagonist, worldview, use_backup=True)

        def _degrade() -> Dict[str, Any]:
            return self._fallback_init(name, genre, style, protagonist, worldview)

        recovered = await self.recovery.run(_execute, _repair, _fallback, _degrade)
        if not recovered.ok:
            return ToolResult(
                status="failed",
                error={"code": "INIT_FAILED", "message": recovered.error, "is_retryable": False},
                observation="创作设定初始化失败",
                progress_made=False
            )
        payload = recovered.data or self._fallback_init(name, genre, style, protagonist, worldview)

        return ToolResult(
            status="success",
            payload=payload,
            observation="完成项目初始化结构生成",
            progress_made=True
        )

    async def _init_with_router(
        self,
        name: str,
        genre: str,
        style: str,
        protagonist: str,
        worldview: str,
        use_backup: bool
    ) -> Dict[str, Any]:
        prompt = (
            "请根据给定创作设定生成JSON，且只输出JSON。"
            "结构必须为："
            "{\"characters\":[{\"name\":\"\",\"traits\":[],\"relationships\":{}}],"
            "\"world_settings\":[],\"plot_outline\":[],"
            "\"writing_style\":{\"tone\":\"\",\"pacing\":\"\",\"narrative_style\":\"\"},"
            "\"current_progress\":{\"latest_chapter_number\":0,\"latest_goal\":\"\",\"last_summary\":\"\"}}"
            f"\n小说名称:{name}\n类型:{genre}\n风格:{style}\n主角设定:{protagonist}\n世界观:{worldview}"
        )
        if use_backup:
            raw = await self.backup_llm_client.generate(prompt, max_tokens=1800, temperature=0.4)
        else:
            result = await self.model_router.generate(prompt, max_tokens=1800, temperature=0.4)
            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "router_failed")
            raw = result["text"]
        content = raw.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
            content = re.sub(r"\n?```$", "", content).strip()
        data = json.loads(content)
        return {
            "characters": data.get("characters") or [],
            "world_settings": data.get("world_settings") or [],
            "plot_outline": data.get("plot_outline") or [],
            "writing_style": data.get("writing_style") or {},
            "current_progress": data.get("current_progress") or {
                "latest_chapter_number": 0,
                "latest_goal": "",
                "last_summary": ""
            }
        }

    def _fallback_init(self, name: str, genre: str, style: str, protagonist: str, worldview: str) -> Dict[str, Any]:
        return {
            "characters": [
                {
                    "name": protagonist.split("，")[0][:20],
                    "traits": [item.strip() for item in protagonist.replace("。", "，").split("，") if item.strip()][1:4],
                    "relationships": {}
                }
            ],
            "world_settings": [worldview] if worldview else [f"{genre}世界中，{name}的主线冲突即将展开。"],
            "plot_outline": [
                "第一卷开端：主角卷入异变事件",
                "中段推进：揭示隐藏势力与核心冲突",
                "卷末转折：主角做出关键选择并开启新篇章"
            ],
            "writing_style": {
                "tone": style or "热血成长",
                "pacing": "中快节奏",
                "narrative_style": "第三人称近距离"
            },
            "current_progress": {
                "latest_chapter_number": 0,
                "latest_goal": "",
                "last_summary": ""
            }
        }


class RAGSearchTool:
    name = "RAGSearchTool"
    side_effect_type = "read"

    def execute(self, task_context: TaskContext, tool_input: Dict[str, Any]) -> ToolResult:
        query = str(tool_input.get("query") or "").strip()
        if not query:
            return ToolResult(
                status="failed",
                error={"code": "INVALID_QUERY", "message": "query不能为空", "is_retryable": False},
                observation="缺少query，无法检索",
                progress_made=False
            )

        context_blocks = [
            {
                "source": "mock_chapter",
                "content": f"与“{query}”相关的前文线索：主角曾在古城边缘见过相同纹章。",
                "confidence": 0.72
            },
            {
                "source": "mock_worldview",
                "content": "古城遗迹与失落家族有关，符纹可触发血脉共鸣。",
                "confidence": 0.68
            }
        ]
        return ToolResult(
            status="success",
            payload={"context_blocks": context_blocks, "query": query},
            observation=f"RAG检索完成，返回{len(context_blocks)}条上下文",
            progress_made=True
        )


class WritingGenerateTool:
    name = "WritingGenerateTool"
    side_effect_type = "write"

    def execute(self, task_context: TaskContext, tool_input: Dict[str, Any]) -> ToolResult:
        goal = str(tool_input.get("goal") or task_context.goal).strip()
        target_word_count = int(tool_input.get("target_word_count") or task_context.target_word_count)
        if not goal:
            return ToolResult(
                status="failed",
                error={"code": "INVALID_GOAL", "message": "goal不能为空", "is_retryable": False},
                observation="缺少goal，无法生成",
                progress_made=False
            )

        seed = f"围绕目标“{goal}”推进情节，主角在冲突中做出选择并引出下一章悬念。"
        chunks = []
        while len("".join(chunks)) < target_word_count:
            chunks.append(seed)
        content = "".join(chunks)[:target_word_count]

        payload = {
            "novel_id": task_context.novel_id,
            "chapter_title": "MVP章节草稿",
            "content": content,
            "word_count": len(content),
            "goal": goal
        }
        return ToolResult(
            status="success",
            payload=payload,
            observation=f"已生成章节草稿，长度{len(content)}",
            progress_made=True
        )


class ContinueWritingTool:
    name = "ContinueWritingTool"
    side_effect_type = "write"

    def execute(self, task_context: TaskContext, tool_input: Dict[str, Any]) -> ToolResult:
        goal = str(tool_input.get("goal") or task_context.goal).strip()
        memory = tool_input.get("memory") or {}
        recent_chapter_text = str(tool_input.get("recent_chapter_text") or "").strip()
        if not isinstance(memory, dict):
            memory = {}
        if not goal:
            return ToolResult(
                status="failed",
                error={"code": "INVALID_GOAL", "message": "goal不能为空", "is_retryable": False},
                observation="缺少写作目标，无法续写",
                progress_made=False
            )

        if not memory:
            return ToolResult(
                status="failed",
                error={"code": "MISSING_MEMORY", "message": "缺少故事设定，无法续写", "is_retryable": False},
                observation="缺少memory",
                progress_made=False
            )

        characters = memory.get("characters") or []
        world_settings = memory.get("world_settings") or []
        plot_outline = memory.get("plot_outline") or []
        plot_threads = memory.get("plot_threads") or []
        style_profile = memory.get("writing_style") or memory.get("style_profile") or {}
        if not characters or not style_profile:
            return ToolResult(
                status="failed",
                error={"code": "INVALID_MEMORY", "message": "故事设定不完整，无法续写", "is_retryable": False},
                observation="memory缺少人物或风格",
                progress_made=False
            )

        lead_name = "主角"
        lead_traits = "冷静"
        relation_hint = ""
        if characters and isinstance(characters[0], dict):
            lead = characters[0]
            lead_name = str(lead.get("name") or lead_name)
            traits = [str(item).strip() for item in (lead.get("traits") or []) if str(item).strip()]
            if traits:
                lead_traits = "、".join(traits[:3])
            relations = lead.get("relationships") or {}
            if isinstance(relations, dict) and relations:
                target, relation = next(iter(relations.items()))
                relation_hint = f"{lead_name}与{target}目前是“{relation}”关系。"

        world_hint = "世界规则尚在迷雾中。"
        if world_settings:
            world_hint = "；".join([str(item).strip() for item in world_settings[:2] if str(item).strip()]) or world_hint

        plot_hint = "新的危机正在逼近。"
        if plot_outline:
            plot_hint = "；".join([str(item).strip() for item in plot_outline[:2] if str(item).strip()]) or plot_hint
        elif plot_threads and isinstance(plot_threads[0], dict):
            title = str(plot_threads[0].get("title") or "").strip()
            points = plot_threads[0].get("points") or []
            point_text = str(points[-1]).strip() if points else ""
            if title and point_text:
                plot_hint = f"{title}线推进到：{point_text}"
            elif title:
                plot_hint = f"{title}线仍在持续发酵。"

        tone = str(style_profile.get("tone") or "紧张克制").strip()
        pacing = str(style_profile.get("pacing") or "中快节奏").strip()
        narrative_style = str(style_profile.get("narrative_style") or "第三人称").strip()

        chapter_text = (
            f"【{goal}】\n\n"
            f"{narrative_style}下，{lead_name}保持着{lead_traits}的状态，沿着遗迹深处继续前行。"
            f"空气里浮动着旧时代的尘息，脚步声在石壁间回荡，像某种无形的倒计时。\n\n"
            + (f"上章承接：{recent_chapter_text[:120]}。\n\n" if recent_chapter_text else "")
            + (
            f"{world_hint} {relation_hint}".strip()
            + "\n\n"
            )
            + f"{plot_hint} 面对新的线索，{lead_name}没有贸然行动，而是先确认退路，再做选择。"
            f"这种选择让局势短暂稳定，却也引来了更强的对手注视。\n\n"
            + f"本章基调为“{tone}”，推进节奏为“{pacing}”。"
            f"{lead_name}在章末确认了下一步目标：先保全同伴，再主动切入冲突中心。"
        )

        return ToolResult(
            status="success",
            payload={
                "chapter_text": chapter_text,
                "goal": goal,
                "used_memory": {
                    "characters": len(characters),
                    "world_settings": len(world_settings),
                    "plot_outline": len(plot_outline) or len(plot_threads),
                    "style_profile": bool(style_profile)
                }
            },
            observation="续写完成，已融合Memory信息",
            progress_made=True
        )
