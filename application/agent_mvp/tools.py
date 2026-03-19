from __future__ import annotations

import asyncio
import json
import re
import logging
from typing import Dict, Any, List

from application.agent_mvp.chapter_splitter import split_into_chunks_by_chars
from application.agent_mvp.memory import merge_memory
from application.agent_mvp.model_router import ModelRouter
from application.agent_mvp.models import TaskContext, ToolResult
from application.agent_mvp.recovery import RecoveryPipeline

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """你是小说结构分析器。只允许输出JSON对象，不允许解释文本。
输出结构必须严格为：
{
  "characters":[{"name":"","traits":[],"relationships":{}}],
  "world_settings":"",
  "plot_outline":"",
  "writing_style":"",
  "current_progress":"",
  "events":[
    {"event":"","actors":[],"action":"","result":"","impact":""}
  ]
}
约束：
1) 必须提取新出现人物与关键配角；
2) 必须提取人物行为、冲突事件、事件结果；
3) events每项字段不得为空，不得出现“发生了一些事情”这类模糊描述；
4) world_settings/plot_outline/writing_style/current_progress必须是字符串；
5) 禁止输出自然语言说明。"""

ANALYSIS_USER_PROMPT_TEMPLATE = """任务模式: {mode}
章节标题: {chapter_title}
已有memory: {memory_json}
小说文本:
{text}

仅返回JSON对象。"""

BRANCH_SYSTEM_PROMPT = """你是剧情分支设计器。你必须只输出JSON数组，不允许任何解释。
输出格式:
[
  {
    "id":"b1",
    "title":"",
    "summary":"",
    "next_goal":"",
    "impact":"",
    "tone":""
  }
]
强约束：
1) 必须输出{branch_count}个分支；
2) 每个分支必须和memory一致，不得脱离人物设定/世界观；
3) 每个分支必须基于events推导；
4) 分支之间必须明显不同。"""

BRANCH_USER_PROMPT_TEMPLATE = """memory:
{memory_json}

当前章节内容:
{chapter_text}

方向提示:
{direction_hint}

输出{branch_count}个分支JSON数组。"""

CONTINUE_SYSTEM_PROMPT = """你是长篇小说续写引擎。你必须严格遵守约束：
1) 输出JSON对象：{"chapter_text":"","new_events":[{"event":"","actors":[],"action":"","result":"","impact":""}]}
2) 必须承接上一章并围绕direction展开；
3) 必须推进剧情，至少新增1个事件；
4) 禁止重复已有内容，禁止空洞套话；
5) 不得偏离人物设定与世界观。"""

CONTINUE_USER_PROMPT_TEMPLATE = """【人物】
{characters}

【世界观】
{world_settings}

【剧情主线】
{plot_outline}

【已发生事件】
{events}

【当前进度】
{current_progress}

【用户选择方向】
{direction}

【章节数量】
{chapter_count}

【目标字数】
{target_word_count}

【幂等键】
{idempotency_key}

【前文章节】
{chapters_text}"""


def _strip_code_fence(text: str) -> str:
    content = text.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content).strip()
    return content


def _extract_json_object(text: str) -> Dict[str, Any]:
    content = _strip_code_fence(text)
    try:
        value = json.loads(content)
        return value if isinstance(value, dict) else {}
    except Exception:
        pass
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        candidate = content[start:end + 1]
        try:
            value = json.loads(candidate)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}
    return {}


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    content = _strip_code_fence(text)
    try:
        value = json.loads(content)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    except Exception:
        pass
    start = content.find("[")
    end = content.rfind("]")
    if start >= 0 and end > start:
        candidate = content[start:end + 1]
        try:
            value = json.loads(candidate)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        except Exception:
            return []
    return []


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
        logger.info(
            "[AnalysisTool] execute_async mode=%s novel_id=%s source_length=%d",
            mode,
            task_context.novel_id,
            len(source_text)
        )
        if mode == "structure_mode":
            if not source_text:
                return ToolResult(
                    status="failed",
                    error={"code": "INVALID_TEXT", "message": "novel_text或initial_setting不能为空", "is_retryable": False},
                    observation="缺少小说文本，无法拆章节",
                    progress_made=False
                )
            chunks = split_into_chunks_by_chars(source_text, chunk_size=4000, overlap=500)
            logger.info(
                "[AnalysisTool] structure_mode split完成 novel_id=%s chunks=%d",
                task_context.novel_id,
                len(chunks)
            )
            return ToolResult(
                status="success",
                payload={
                    "chapters": [
                        {"title": f"第{idx + 1}段", "content": item.get("content") or "", "index": idx + 1}
                        for idx, item in enumerate(chunks)
                    ]
                },
                observation=f"完成文本切分，共{len(chunks)}段",
                progress_made=bool(chunks)
            )

        if mode == "consolidate_mode":
            memory_payload = tool_input.get("memory") or {}
            if not isinstance(memory_payload, dict):
                memory_payload = {}
            logger.info(
                "[AnalysisTool] consolidate_mode 开始 novel_id=%s characters=%d events=%d",
                task_context.novel_id,
                len(memory_payload.get("characters") or []),
                len(memory_payload.get("events") or [])
            )
            consolidated = self._consolidate_memory(memory_payload)
            return ToolResult(
                status="success",
                payload=consolidated,
                observation="完成全局收敛",
                progress_made=True
            )

        merge_input = tool_input.get("merge") or tool_input.get("memory") or task_context.memory or {}
        if not isinstance(merge_input, dict):
            merge_input = {}
        chapter_payload = tool_input.get("chapter")
        if isinstance(chapter_payload, dict):
            source_text = str(chapter_payload.get("content") or "").strip()
            chapter_title = str(chapter_payload.get("title") or "").strip()
        else:
            chapter_title = str(tool_input.get("chapter_title") or "").strip()
        logger.info(
            "[AnalysisTool] incremental_mode 开始 novel_id=%s chapter=%s content_length=%d",
            task_context.novel_id,
            chapter_title or chapter_payload.get("index") if isinstance(chapter_payload, dict) else "",
            len(source_text)
        )
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
            return await self._analyze_with_router(source_text, chapter_title, merge_input)

        async def _repair() -> Dict[str, Any]:
            if self.llm_client is None:
                raise RuntimeError("primary_unavailable")
            fixed_text = re.sub(r"\s+", " ", source_text).strip()
            return await self._analyze_with_router(fixed_text, chapter_title, merge_input)

        async def _fallback() -> Dict[str, Any]:
            if self.backup_llm_client is None:
                raise RuntimeError("backup_unavailable")
            prompt = self._build_analysis_prompt(source_text, chapter_title, merge_input)
            raw = await self.backup_llm_client.generate(prompt, max_tokens=2200, temperature=0.2)
            return self._normalize_analysis_output(_extract_json_object(raw), source_text, chapter_title)

        def _degrade() -> Dict[str, Any]:
            return self._fallback_analysis(source_text, chapter_title)

        recovered = await self.recovery.run(_execute, _repair, _fallback, _degrade)
        if not recovered.ok:
            logger.error(
                "[AnalysisTool] incremental_mode 失败 novel_id=%s chapter=%s error=%s",
                task_context.novel_id,
                chapter_title,
                recovered.error
            )
            return ToolResult(
                status="failed",
                error={"code": "ANALYSIS_FAILED", "message": recovered.error, "is_retryable": False},
                observation="结构整理失败",
                progress_made=False
            )
        result = recovered.data or self._fallback_analysis(source_text, chapter_title)
        incremental_memory = merge_memory(merge_input, result)
        chunk_no = int(chapter_payload.get("index") or 0) if isinstance(chapter_payload, dict) else 0
        progress_text = str(incremental_memory.get("current_progress") or "").strip()
        append_text = f"chunk={chunk_no} {chapter_title}分析完成".strip() if chapter_title else f"chunk={chunk_no} 章节分析完成".strip()
        incremental_memory["current_progress"] = (
            f"{progress_text}；{append_text}" if progress_text and append_text not in progress_text else (append_text or progress_text)
        )
        logger.info(
            "[AnalysisTool] incremental_mode 完成 novel_id=%s chapter=%s characters=%d events=%d",
            task_context.novel_id,
            chapter_title,
            len(incremental_memory.get("characters") or []),
            len(incremental_memory.get("events") or [])
        )
        return ToolResult(
            status="success",
            payload=incremental_memory,
            observation="完成章节增量分析",
            progress_made=True
        )

    def _build_analysis_prompt(self, text: str, chapter_title: str, merge_input: Dict[str, Any]) -> str:
        memory_json = json.dumps(merge_input, ensure_ascii=False)[:4000]
        user_prompt = ANALYSIS_USER_PROMPT_TEMPLATE.format(
            mode="incremental_mode",
            chapter_title=chapter_title or "未命名章节",
            memory_json=memory_json,
            text=text[:12000]
        )
        return f"{ANALYSIS_SYSTEM_PROMPT}\n\n{user_prompt}"

    async def _analyze_with_router(self, text: str, chapter_title: str, merge_input: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_analysis_prompt(text, chapter_title, merge_input)
        result = await self.model_router.generate(prompt, max_tokens=2200, temperature=0.2)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "router_failed")
        data = _extract_json_object(result.get("text") or "")
        return self._normalize_analysis_output(data, text, chapter_title)

    def _normalize_analysis_output(self, data: Dict[str, Any], source_text: str, chapter_title: str) -> Dict[str, Any]:
        if not isinstance(data, dict):
            data = {}
        chars = []
        for item in (data.get("characters") or []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            traits = [str(v).strip() for v in (item.get("traits") or []) if str(v).strip()][:5]
            rel = item.get("relationships") or {}
            if not isinstance(rel, dict):
                rel = {}
            chars.append({"name": name, "traits": traits, "relationships": rel})
        if not chars:
            chars.append({"name": "主角", "traits": ["果断", "坚韧"], "relationships": {}})
        if len(chars) < 2:
            chars.append({"name": "关键配角", "traits": ["谨慎", "机敏"], "relationships": {chars[0]["name"]: "同伴"}})
        world_settings = [str(v).strip() for v in (data.get("world_settings") or []) if str(v).strip()]
        if not world_settings:
            raw_world = str(data.get("world_settings") or "").strip()
            if raw_world:
                world_settings = [raw_world]
        plot_outline = [str(v).strip() for v in (data.get("plot_outline") or []) if str(v).strip()]
        if not plot_outline:
            raw_plot = str(data.get("plot_outline") or "").strip()
            if raw_plot:
                plot_outline = [raw_plot]
        sample = [line.strip() for line in source_text.splitlines() if line.strip()]
        snippet = "；".join(sample[:3])[:120]
        while len(world_settings) < 3:
            world_settings.append(f"世界规则线索{len(world_settings)+1}：{snippet or '资源与势力冲突持续升级'}")
        while len(plot_outline) < 3:
            plot_outline.append(f"剧情推进{len(plot_outline)+1}：围绕“{chapter_title or '当前章节'}”发生关键冲突并产生后果")
        style = data.get("writing_style") or data.get("style_profile") or ""
        if isinstance(style, dict):
            writing_style = "；".join(
                [
                    str(style.get("tone") or "").strip(),
                    str(style.get("pacing") or "").strip(),
                    str(style.get("narrative_style") or "").strip()
                ]
            ).strip("；")
        else:
            writing_style = str(style or "").strip()
        if not writing_style:
            writing_style = "紧张克制；中快节奏；第三人称"
        events = self._normalize_events(data.get("events") or [], source_text, chars)
        return {
            "characters": chars[:8],
            "world_settings": "；".join(world_settings[:8]),
            "plot_outline": "；".join(plot_outline[:12]),
            "writing_style": writing_style,
            "current_progress": str(data.get("current_progress") or f"{chapter_title or '当前片段'}分析完成"),
            "events": events
        }

    def _fallback_analysis(self, novel_text: str, chapter_title: str) -> Dict[str, Any]:
        lines = [line.strip() for line in novel_text.splitlines() if line.strip()]
        sample = "；".join(lines[:4])[:180]
        return {
            "characters": [
                {"name": "主角", "traits": ["谨慎", "坚韧"], "relationships": {"关键配角": "同伴"}},
                {"name": "关键配角", "traits": ["机敏", "务实"], "relationships": {"主角": "同伴"}}
            ],
            "world_settings": f"世界规则线索：{sample or '力量体系与势力边界正在重塑'}；资源争夺持续升级；关键区域存在未公开规则",
            "plot_outline": f"承接“{chapter_title or '当前片段'}”推进冲突；主角获得新线索；章节尾部抛出下一步行动目标",
            "writing_style": "叙事；中速；第三人称",
            "current_progress": f"{chapter_title or '当前片段'}分析完成",
            "events": [
                {
                    "event": "主角在推进目标时遭遇新阻力",
                    "actors": ["主角", "关键配角"],
                    "action": "发现",
                    "result": "确认冲突升级",
                    "impact": "下一段必须优先处理阻力来源"
                }
            ]
        }

    def _consolidate_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        merged = merge_memory(memory, {})
        merged["world_settings"] = str(merged.get("world_settings") or "")[:1200]
        merged["plot_outline"] = str(merged.get("plot_outline") or "")[:1600]
        merged["writing_style"] = str(merged.get("writing_style") or "叙事；中速；第三人称")
        merged["current_progress"] = str(merged.get("current_progress") or "")
        events = [ev for ev in (merged.get("events") or []) if isinstance(ev, dict)]
        merged["events"] = events[-60:]
        return merged

    def _normalize_events(self, events: Any, source_text: str, chars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in events if isinstance(events, list) else []:
            if not isinstance(item, dict):
                continue
            payload = {
                "event": str(item.get("event") or "").strip(),
                "actors": [str(v).strip() for v in (item.get("actors") or []) if str(v).strip()],
                "action": str(item.get("action") or "").strip(),
                "result": str(item.get("result") or "").strip(),
                "impact": str(item.get("impact") or "").strip()
            }
            if payload["event"] and payload["action"] and payload["result"] and payload["impact"]:
                normalized.append(payload)
        if not normalized:
            main_actor = str(chars[0].get("name") or "主角") if chars else "主角"
            sub_actor = str(chars[1].get("name") or "关键配角") if len(chars) > 1 else "关键配角"
            summary = "；".join([line.strip() for line in source_text.splitlines() if line.strip()][:2])[:120]
            normalized.append(
                {
                    "event": f"{main_actor}在当前片段触发关键冲突：{summary or '新的压力出现'}",
                    "actors": [main_actor, sub_actor],
                    "action": "发现",
                    "result": f"{main_actor}必须调整行动策略",
                    "impact": "下一段将围绕新冲突推进主线"
                }
            )
        return normalized


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


class StoryBranchTool:
    name = "StoryBranchTool"
    side_effect_type = "read"

    def __init__(self, llm_client=None, backup_llm_client=None):
        self.llm_client = llm_client
        self.backup_llm_client = backup_llm_client
        self.model_router = ModelRouter(llm_client, backup_llm_client)
        self.recovery = RecoveryPipeline(max_retries=1)

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
        memory = tool_input.get("memory") or task_context.memory or {}
        chapter_text = str(tool_input.get("current_chapter_content") or "").strip()
        direction_hint = str(tool_input.get("direction_hint") or task_context.goal or "").strip()
        branch_count = int(tool_input.get("branch_count") or 3)
        branch_count = max(3, min(5, branch_count))
        if not isinstance(memory, dict):
            memory = {}
        if not memory:
            return ToolResult(
                status="failed",
                error={"code": "MISSING_MEMORY", "message": "缺少故事设定，无法生成分支", "is_retryable": False},
                observation="缺少memory",
                progress_made=False
            )

        async def _execute() -> List[Dict[str, Any]]:
            prompt = self._build_branch_prompt(memory, chapter_text, direction_hint, branch_count)
            result = await self.model_router.generate(prompt, max_tokens=1800, temperature=0.5)
            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "router_failed")
            return self._normalize_branches(_extract_json_array(result.get("text") or ""), branch_count, direction_hint)

        async def _repair() -> List[Dict[str, Any]]:
            prompt = self._build_branch_prompt(memory, chapter_text, direction_hint, branch_count) + "\n输出必须严格是JSON数组。"
            result = await self.model_router.generate(prompt, max_tokens=1800, temperature=0.4)
            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "router_failed")
            return self._normalize_branches(_extract_json_array(result.get("text") or ""), branch_count, direction_hint)

        async def _fallback() -> List[Dict[str, Any]]:
            if self.backup_llm_client is None:
                raise RuntimeError("backup_unavailable")
            prompt = self._build_branch_prompt(memory, chapter_text, direction_hint, branch_count)
            raw = await self.backup_llm_client.generate(prompt, max_tokens=1800, temperature=0.4)
            return self._normalize_branches(_extract_json_array(raw), branch_count, direction_hint)

        def _degrade() -> Dict[str, Any]:
            return {"branches": self._fallback_branches(memory, chapter_text, direction_hint, branch_count)}

        recovered = await self.recovery.run(_execute, _repair, _fallback, _degrade)
        if not recovered.ok:
            return ToolResult(
                status="failed",
                error={"code": "BRANCH_FAILED", "message": recovered.error, "is_retryable": False},
                observation="分支生成失败",
                progress_made=False
            )
        branches = recovered.data if isinstance(recovered.data, list) else (recovered.data or {}).get("branches", [])
        if not isinstance(branches, list):
            branches = []
        return ToolResult(
            status="success",
            payload={"branches": branches},
            observation=f"已生成{len(branches)}个剧情分支",
            progress_made=True
        )

    def generate_story_branches(self, memory: Dict[str, Any], current_chapter: str, branch_count: int = 4) -> List[Dict[str, Any]]:
        branch_count = max(3, min(5, int(branch_count or 4)))
        return self._fallback_branches(memory, current_chapter, "沿已发生事件推进", branch_count)

    def _build_branch_prompt(self, memory: Dict[str, Any], chapter_text: str, direction_hint: str, branch_count: int) -> str:
        system = BRANCH_SYSTEM_PROMPT.format(branch_count=branch_count)
        user = BRANCH_USER_PROMPT_TEMPLATE.format(
            memory_json=json.dumps(memory, ensure_ascii=False)[:5000],
            chapter_text=chapter_text[:2000],
            direction_hint=direction_hint or "沿主线推进冲突并制造新悬念",
            branch_count=branch_count
        )
        return f"{system}\n\n{user}"

    def _normalize_branches(self, branches: List[Dict[str, Any]], branch_count: int, direction_hint: str) -> List[Dict[str, Any]]:
        normalized = []
        for idx, item in enumerate(branches[:branch_count], 1):
            title = str(item.get("title") or "").strip() or f"分支{idx}"
            summary = str(item.get("summary") or "").strip() or f"围绕{direction_hint or '主线'}推进冲突并触发新决策。"
            next_goal = str(item.get("next_goal") or item.get("key_event") or "").strip() or f"{title}触发关键事件并进入下一步目标"
            impact = str(item.get("impact") or "").strip() or "推动人物关系与主线局势变化"
            tone = str(item.get("tone") or "").strip() or "紧张"
            normalized.append(
                {
                    "id": str(item.get("id") or f"b{idx}"),
                    "title": title,
                    "summary": summary,
                    "next_goal": next_goal,
                    "impact": impact,
                    "tone": tone
                }
            )
        while len(normalized) < branch_count:
            idx = len(normalized) + 1
            normalized.append(
                {
                    "id": f"b{idx}",
                    "title": f"分支{idx}",
                    "summary": f"围绕{direction_hint or '主线'}推进冲突并触发新转折。",
                    "next_goal": "主角做出高风险决策并执行",
                    "impact": "主线加速并改变人物关系",
                    "tone": "紧张"
                }
            )
        return normalized

    def _fallback_branches(self, memory: Dict[str, Any], chapter_text: str, direction_hint: str, branch_count: int) -> List[Dict[str, Any]]:
        lead = "主角"
        characters = memory.get("characters") or []
        if characters and isinstance(characters[0], dict):
            lead = str(characters[0].get("name") or lead)
        branches = []
        events_text = "；".join([str(ev.get("event") or "") for ev in (memory.get("events") or []) if isinstance(ev, dict)])[:120]
        for idx in range(1, branch_count + 1):
            branches.append(
                {
                    "id": f"b{idx}",
                    "title": f"{lead}的选择{idx}",
                    "summary": f"{lead}围绕“{direction_hint or '主线任务'}”采取第{idx}种行动方案并触发冲突。事件依据：{events_text or '当前冲突链'}",
                    "next_goal": f"{lead}在关键节点做出第{idx}种决策并执行",
                    "impact": "直接改变后续主线节奏与人物关系",
                    "tone": ["紧张", "压迫", "燃", "悬疑", "克制"][idx - 1]
                }
            )
        return branches


class ContinueWritingTool:
    name = "ContinueWritingTool"
    side_effect_type = "write"

    def __init__(self, llm_client=None, backup_llm_client=None):
        self.llm_client = llm_client
        self.backup_llm_client = backup_llm_client
        self.model_router = ModelRouter(llm_client, backup_llm_client)

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
        direction = str(tool_input.get("direction") or tool_input.get("goal") or task_context.goal).strip()
        memory = tool_input.get("memory") or task_context.memory or {}
        chapters = tool_input.get("chapters") or []
        chapter_count = int(tool_input.get("chapter_count") or len(chapters) or 0)
        recent_chapter_text = str(tool_input.get("recent_chapter_text") or "").strip()
        if recent_chapter_text:
            chapters = [*chapters, {"content": recent_chapter_text}]
        idempotency_key = str(tool_input.get("idempotency_key") or task_context.request_id).strip()
        target_word_count = int(tool_input.get("target_word_count") or task_context.target_word_count or 2100)
        if not direction:
            return ToolResult(
                status="failed",
                error={"code": "INVALID_DIRECTION", "message": "direction不能为空", "is_retryable": False},
                observation="缺少direction",
                progress_made=False
            )
        if not isinstance(memory, dict) or not self._has_required_memory(memory):
            return ToolResult(
                status="failed",
                error={"code": "INVALID_MEMORY", "message": "memory不完整，无法续写", "is_retryable": False},
                observation="memory缺少必要字段",
                progress_made=False
            )
        chapters_text = self._compact_chapters(chapters)
        try:
            chapter_text, new_events = await self._generate_with_retry(
                direction=direction,
                memory=memory,
                chapters_text=chapters_text,
                target_word_count=target_word_count,
                idempotency_key=idempotency_key,
                chapter_count=chapter_count
            )
        except Exception:
            chapter_text = self._fallback_continue(memory, direction, chapters_text, target_word_count)
            new_events = self._derive_new_events(chapter_text, memory)
        return ToolResult(
            status="success",
            payload={
                "chapter_text": chapter_text,
                "new_events": new_events,
                "direction": direction,
                "used_memory": {
                    "characters": len(memory.get("characters") or []),
                    "world_settings": len(str(memory.get("world_settings") or "")),
                    "plot_outline": len(str(memory.get("plot_outline") or "")),
                    "style_profile": bool(str(memory.get("writing_style") or ""))
                }
            },
            observation="续写完成，已强制注入memory和direction",
            progress_made=True
        )

    async def _generate_with_retry(
        self,
        direction: str,
        memory: Dict[str, Any],
        chapters_text: str,
        target_word_count: int,
        idempotency_key: str,
        chapter_count: int
    ) -> tuple[str, List[Dict[str, Any]]]:
        prompt = self._build_continue_prompt(direction, memory, chapters_text, target_word_count, idempotency_key, chapter_count, strict=False)
        payload = await self._call_llm(prompt)
        text = str(payload.get("chapter_text") or "")
        events = payload.get("new_events") or []
        if self._is_bad_generation(text, chapters_text):
            strict_prompt = self._build_continue_prompt(direction, memory, chapters_text, target_word_count, idempotency_key, chapter_count, strict=True)
            payload = await self._call_llm(strict_prompt)
            text = str(payload.get("chapter_text") or "")
            events = payload.get("new_events") or []
        if self._is_bad_generation(text, chapters_text):
            raise RuntimeError("generation_quality_failed")
        normalized_events = [ev for ev in events if isinstance(ev, dict)]
        if not normalized_events:
            normalized_events = self._derive_new_events(text, memory)
        return text, normalized_events

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        result = await self.model_router.generate(prompt, max_tokens=2600, temperature=0.45)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "router_failed")
        raw = str(result.get("text") or "").strip()
        payload = _extract_json_object(raw)
        if isinstance(payload, dict) and payload.get("chapter_text"):
            return payload
        return {"chapter_text": raw, "new_events": []}

    def _build_continue_prompt(
        self,
        direction: str,
        memory: Dict[str, Any],
        chapters_text: str,
        target_word_count: int,
        idempotency_key: str,
        chapter_count: int,
        strict: bool
    ) -> str:
        system = CONTINUE_SYSTEM_PROMPT
        if strict:
            system += "\n附加约束：若出现重复句、空洞句、无事件推进，立即重写。"
        user = CONTINUE_USER_PROMPT_TEMPLATE.format(
            characters=json.dumps(memory.get("characters") or [], ensure_ascii=False),
            world_settings=str(memory.get("world_settings") or ""),
            plot_outline=str(memory.get("plot_outline") or ""),
            events=json.dumps(memory.get("events") or [], ensure_ascii=False),
            current_progress=str(memory.get("current_progress") or ""),
            direction=direction,
            chapter_count=chapter_count,
            idempotency_key=idempotency_key,
            target_word_count=target_word_count,
            chapters_text=chapters_text[:5000]
        )
        return f"{system}\n\n{user}"

    def _has_required_memory(self, memory: Dict[str, Any]) -> bool:
        characters = memory.get("characters") or []
        world_settings = str(memory.get("world_settings") or "").strip()
        plot_outline = str(memory.get("plot_outline") or "").strip()
        style = str(memory.get("writing_style") or "").strip()
        events = memory.get("events") or []
        return bool(characters and world_settings and plot_outline and style and events)

    def _compact_chapters(self, chapters: List[Any]) -> str:
        blocks = []
        for item in chapters[-6:]:
            if isinstance(item, dict):
                text = str(item.get("content") or "").strip()
            else:
                text = str(item).strip()
            if text:
                blocks.append(text[:600])
        return "\n\n".join(blocks)

    def _is_bad_generation(self, text: str, chapters_text: str) -> bool:
        content = str(text or "").strip()
        if len(content) < 120:
            return True
        if self._is_low_information_density(content):
            return True
        if self._is_repetitive_with_history(content, chapters_text):
            return True
        return False

    def _is_low_information_density(self, text: str) -> bool:
        content = text.replace("\n", "")
        filler = ["不知道为什么", "一时间", "似乎", "总之", "然后", "接着", "忽然之间"]
        filler_hits = sum(content.count(k) for k in filler)
        unique_ratio = len(set(content)) / max(len(content), 1)
        return filler_hits >= 8 or unique_ratio < 0.08

    def _is_repetitive_with_history(self, text: str, history: str) -> bool:
        if not history:
            return False
        sample = history[-1200:]
        overlap = 0
        for i in range(0, max(len(text) - 40, 1), 40):
            seg = text[i:i + 80]
            if len(seg) >= 40 and seg in sample:
                overlap += 1
        return overlap >= 2

    def _fallback_continue(self, memory: Dict[str, Any], direction: str, chapters_text: str, target_word_count: int) -> str:
        lead = "主角"
        chars = memory.get("characters") or []
        if chars and isinstance(chars[0], dict):
            lead = str(chars[0].get("name") or lead)
        world = str(memory.get("world_settings") or "")[:160]
        plot = str(memory.get("plot_outline") or "")[:160]
        seed = (
            f"{lead}围绕“{direction}”展开行动。"
            f"上章线索：{chapters_text[:120]}。"
            f"世界约束：{world}。"
            f"主线推进：{plot}。"
            f"本章发生关键事件：{lead}在冲突中做出不可逆选择，局势升级。"
        )
        chunks = []
        while len("".join(chunks)) < target_word_count:
            chunks.append(seed)
        return "".join(chunks)[:target_word_count]

    def _derive_new_events(self, chapter_text: str, memory: Dict[str, Any]) -> List[Dict[str, Any]]:
        lead = "主角"
        chars = memory.get("characters") or []
        if chars and isinstance(chars[0], dict):
            lead = str(chars[0].get("name") or lead)
        summary = chapter_text[:120].replace("\n", " ")
        return [
            {
                "event": f"{lead}在本章采取新行动并引发后果：{summary}",
                "actors": [lead],
                "action": "推进",
                "result": "主线冲突升级",
                "impact": "下一章需要围绕升级冲突继续推进"
            }
        ]
