"""
v2 閲嶆瀯涓绘祦绋嬫湇鍔°€?
璇ユ湇鍔¤礋璐ｇ湡姝ｈ惤鍦板叚鏉′富閾撅細
1) 瀵煎叆涓庨」鐩粦瀹?2) 绔犺妭浼樺厛鏁寸悊骞舵瀯寤?project_memory
3) 鐢熸垚 memory_view
4) 鐢熸垚鍒嗘敮
5) 鐢熸垚澶氱珷璁″垝骞舵墽琛岀画鍐?6) 鍒锋柊 memory
"""

from __future__ import annotations

from datetime import datetime, UTC
import re
import uuid
from typing import Any, Dict, List, Optional

from application.agent_mvp import AnalysisTool, ContinueWritingTool, StoryBranchTool, TaskContext
from application.dto.request_dto import ImportNovelRequest
from application.services.content_service import ContentService
from application.services.project_service import ProjectService
from domain.entities.chapter import Chapter
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.outline_repository import IOutlineRepository
from domain.types import ChapterId, ChapterStatus, NovelId, ProjectId
from domain.types import GenreType
from infrastructure.llm.llm_factory import LLMFactory
from infrastructure.persistence.sqlite_v2_repo import SQLiteV2Repository


class V2WorkflowService:
    def __init__(
        self,
        project_service: ProjectService,
        content_service: ContentService,
        chapter_repo: IChapterRepository,
        novel_repo: INovelRepository,
        outline_repo: IOutlineRepository,
        llm_factory: LLMFactory,
        v2_repo: SQLiteV2Repository,
    ):
        self.project_service = project_service
        self.content_service = content_service
        self.chapter_repo = chapter_repo
        self.novel_repo = novel_repo
        self.outline_repo = outline_repo
        self.llm_factory = llm_factory
        self.v2_repo = v2_repo

    async def import_project(
        self,
        project_name: str,
        genre: str,
        novel_file_path: str,
        outline_file_path: str = "",
        auto_organize: bool = True,
    ) -> Dict[str, Any]:
        try:
            genre_enum = GenreType(genre) if genre else GenreType.XUANHUAN
        except ValueError:
            genre_enum = GenreType.XUANHUAN
        project = self.project_service.create_project(name=project_name, genre=genre_enum)
        request = ImportNovelRequest(
            novel_id=str(project.novel_id),
            file_path=novel_file_path,
            outline_path=outline_file_path or None,
        )
        self.content_service.import_novel(request)
        memory_view = {}
        if auto_organize:
            organized = await self.organize_project(project.id.value, mode="chapter_first", rebuild_memory=True)
            memory_view = organized.get("memory_view") or {}
        return {
            "project_id": project.id.value,
            "novel_id": str(project.novel_id),
            "outline_id": f"outline_{project.id.value}",
            "status": "organized" if auto_organize else "imported",
            "memory_view": memory_view,
        }

    async def organize_project(self, project_id: str, mode: str, rebuild_memory: bool) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        job_id = self.v2_repo.start_workflow_job(
            project_id=project_id,
            workflow_type="organize_novel",
            input_payload={"mode": mode, "rebuild_memory": rebuild_memory},
        )
        novel_id = str(project.novel_id)
        analyzer = AnalysisTool(self.llm_factory.primary_client, self.llm_factory.backup_client)
        outline = self.outline_repo.find_by_novel(project.novel_id)
        outline_context = {
            "premise": outline.premise if outline else "",
            "story_background": outline.story_background if outline else "",
            "world_setting": outline.world_setting if outline else "",
            "summary": [outline.premise, outline.story_background] if outline else [],
        }
        chapters = self._build_chapter_units(project.novel_id, mode)
        merged_memory: Dict[str, Any] = self._empty_structured_memory(outline_context)
        for chapter in chapters:
            incremental = await analyzer.execute_async(
                TaskContext(novel_id=novel_id, goal="v2_organize_incremental"),
                {
                    "mode": "incremental_mode",
                    "chapter": chapter,
                    "memory": self._to_tool_memory_context(merged_memory),
                },
            )
            if incremental.status != "success":
                self.v2_repo.finish_workflow_job(job_id, "failed", error_message="绔犺妭鍒嗘瀽澶辫触")
                raise ValueError("章节分析失败")
            merged_memory = self._merge_structured_memory(merged_memory, incremental.payload or {}, chapter.get("title") or "")
        consolidate = await analyzer.execute_async(
            TaskContext(novel_id=novel_id, goal="v2_organize_consolidate"),
            {"mode": "consolidate_mode", "memory": self._to_tool_memory_context(merged_memory)},
        )
        if consolidate.status != "success":
            self.v2_repo.finish_workflow_job(job_id, "failed", error_message="鍏ㄥ眬鏀舵暃澶辫触")
            raise ValueError("全局收敛失败")
        memory = self._merge_structured_memory(merged_memory, consolidate.payload or {}, "鍏ㄥ眬鏀舵暃")
        self.project_service.bind_memory_to_novel(NovelId(novel_id), memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        view_payload = self._to_memory_view_payload(project_id, memory_payload)
        self.v2_repo.save_memory_view(view_payload)
        self.v2_repo.finish_workflow_job(
            job_id,
            "success",
            result_payload={"organized_chapter_count": len(chapters), "memory_id": memory_payload["id"]},
        )
        return {
            "project_id": project_id,
            "organized_chapter_count": len(chapters),
            "memory_id": memory_payload["id"],
            "memory_view": view_payload,
        }

    def get_memory(self, project_id: str) -> Dict[str, Any]:
        return self.v2_repo.find_active_project_memory(project_id) or {}

    def get_memory_view(self, project_id: str) -> Dict[str, Any]:
        return self.v2_repo.find_memory_view(project_id) or {}

    def list_workflow_jobs(self, project_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        return self.v2_repo.list_workflow_jobs(project_id, limit)

    def list_writing_sessions(self, project_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        return self.v2_repo.list_writing_sessions(project_id, limit)

    def get_project_trace(self, project_id: str) -> Dict[str, Any]:
        memory = self.get_memory(project_id)
        view = self.get_memory_view(project_id)
        jobs = self.list_workflow_jobs(project_id, 10)
        sessions = self.list_writing_sessions(project_id, 10)
        latest_job = jobs[0] if jobs else {}
        latest_session = sessions[0] if sessions else {}
        return {
            "project_id": project_id,
            "memory_version": int(memory.get("version") or 0),
            "latest_progress": str(view.get("current_progress") or ""),
            "latest_workflow_job": latest_job,
            "latest_writing_session": latest_session,
        }

    async def generate_branches(self, project_id: str, direction_hint: str, branch_count: int) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        outline_context = self._get_outline_context(project.novel_id)
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        chapters = self.chapter_repo.find_by_novel(project.novel_id)
        latest = chapters[-1].content if chapters else ""
        tool = StoryBranchTool(self.llm_factory.primary_client, self.llm_factory.backup_client)
        result = await tool.execute_async(
            TaskContext(novel_id=str(project.novel_id), goal=direction_hint, target_word_count=0),
            {
                "memory": self._to_tool_memory_context(memory),
                "current_chapter_content": latest,
                "direction_hint": direction_hint,
                "branch_count": branch_count,
            },
        )
        if result.status != "success":
            raise ValueError("分支生成失败")
        branches = []
        for idx, item in enumerate((result.payload or {}).get("branches") or [], 1):
            generated_id = str(item.get("id") or "").strip()
            if not generated_id:
                generated_id = f"branch_{uuid.uuid4().hex[:8]}"
            else:
                generated_id = f"{project_id[:8]}_{generated_id}_{idx}"
            branches.append(
                {
                    "id": generated_id,
                    "project_id": project_id,
                    "title": item.get("title") or "",
                    "summary": item.get("summary") or "",
                    "core_conflict": item.get("impact") or "",
                    "key_progressions": [item.get("next_goal") or ""],
                    "related_characters": [c.get("name") for c in (memory.get("characters") or []) if isinstance(c, dict)][:3],
                    "style_tags": [item.get("tone") or ""],
                    "consistency_note": self._build_outline_consistency_note(item, outline_context),
                    "risk_note": self._build_outline_risk_note(item, outline_context),
                    "status": "candidate",
                }
            )
        self.v2_repo.replace_branches(project_id, branches)
        return {"project_id": project_id, "branches": branches}

    def create_chapter_plan(self, project_id: str, branch_id: str, chapter_count: int, target_words_per_chapter: int) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        novel = self.novel_repo.find_by_id(project.novel_id)
        start_no = (novel.chapter_count if novel else 0) + 1
        branches = self.v2_repo.list_branches(project_id)
        branch = next((b for b in branches if b["id"] == branch_id), None)
        if not branch:
            raise ValueError("分支不存在")
        outline_context = self._get_outline_context(project.novel_id)
        outline_summary = "?".join(
            [
                str(outline_context.get("premise") or ""),
                str(outline_context.get("story_background") or ""),
                str(outline_context.get("world_setting") or ""),
            ]
        ).strip("?")
        plans = []
        for i in range(chapter_count):
            no = start_no + i
            outline_clause = f"???????{outline_summary[:120]}" if outline_summary else "??????????????"
            plans.append(
                {
                    "id": f"plan_{uuid.uuid4().hex[:10]}",
                    "project_id": project_id,
                    "branch_id": branch_id,
                    "chapter_number": no,
                    "title": f"?{no}?",
                    "goal": f"{branch['title']} ?{i + 1}??????{outline_clause}",
                    "conflict": f"{branch['core_conflict'] or '??????'}??????????",
                    "progression": f"鍥寸粫{branch['summary']}鎺ㄨ繘鍏抽敭浜嬩欢锛屽苟鏍￠獙涓庡ぇ绾蹭笉鍐茬獊",
                    "ending_hook": f"{branch['title']} ???????",
                    "target_words": target_words_per_chapter,
                    "related_arc_ids": [],
                    "status": "ready",
                }
            )
        self.v2_repo.replace_plans(project_id, plans)
        return {"project_id": project_id, "branch_id": branch_id, "plans": plans}

    async def execute_writing(self, project_id: str, plan_ids: List[str], auto_commit: bool) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        plans = self.v2_repo.find_plans(project_id, plan_ids)
        if not plans:
            raise ValueError("未找到可执行的章节计划")
        outline_context = self._get_outline_context(project.novel_id)
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        session_id = self.v2_repo.start_writing_session(project_id, plans[0]["branch_id"] if plans else "", plan_ids)
        tool = ContinueWritingTool(self.llm_factory.primary_client, self.llm_factory.backup_client)
        generated_ids: List[str] = []
        latest_content = ""
        chapters = self.chapter_repo.find_by_novel(project.novel_id)
        memory["outline_context"] = outline_context
        for plan in plans:
            direction = f"{plan['goal']}?{plan['conflict']}?{plan['progression']}"
            result = await tool.execute_async(
                TaskContext(novel_id=str(project.novel_id), goal=direction, target_word_count=plan["target_words"]),
                {
                    "direction": direction,
                    "memory": self._to_tool_memory_context(memory),
                    "chapters": [{"content": ch.content, "number": ch.number} for ch in chapters[-8:]],
                    "chapter_count": len(chapters),
                    "target_word_count": plan["target_words"],
                    "idempotency_key": f"{project_id}:{plan['id']}",
                },
            )
            if result.status != "success":
                self.v2_repo.finish_writing_session(session_id, "failed", generated_ids)
                raise ValueError("续写失败")
            chapter_text = str((result.payload or {}).get("chapter_text") or "")
            latest_content = chapter_text
            if auto_commit:
                no = int(plan["chapter_number"])
                now = datetime.now()
                chapter = Chapter(
                    id=ChapterId(str(uuid.uuid4())),
                    novel_id=project.novel_id,
                    number=no,
                    title=plan["title"] or f"?{no}?",
                    content=chapter_text,
                    status=ChapterStatus.DRAFT,
                    created_at=now,
                    updated_at=now,
                )
                self.chapter_repo.save(chapter)
                chapters.append(chapter)
                generated_ids.append(chapter.id.value)
            if auto_commit:
                memory["events"] = [*(memory.get("events") or []), *((result.payload or {}).get("new_events") or [])][-120:]
                memory["chapter_summaries"] = [*(memory.get("chapter_summaries") or []), chapter_text[:120]][-300:]
                current_state = memory.get("current_state") or {}
                current_state.update(
                    {
                        "latest_chapter_number": int(plan["chapter_number"]),
                        "latest_summary": chapter_text[:120],
                        "next_writing_focus": plan["ending_hook"],
                    }
                )
                memory["current_state"] = current_state
                memory["continuity_flags"] = [
                    *(memory.get("continuity_flags") or []),
                    *((result.payload or {}).get("possible_continuity_flags") or []),
                ][-80:]
                self.project_service.bind_memory_to_novel(project.novel_id, memory)
        if auto_commit:
            memory_payload = self._to_project_memory_payload(project_id, memory)
            self.v2_repo.save_project_memory(memory_payload)
            view_payload = self._to_memory_view_payload(project_id, memory_payload)
            self.v2_repo.save_memory_view(view_payload)
        else:
            view_payload = self.get_memory_view(project_id)
        self.v2_repo.finish_writing_session(session_id, "finished", generated_ids)
        return {
            "project_id": project_id,
            "generated_chapter_ids": generated_ids,
            "latest_content": latest_content,
            "memory_view": view_payload,
        }

    async def refresh_memory(self, project_id: str, from_chapter_number: int, to_chapter_number: int) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        chapters = self.chapter_repo.find_by_novel(project.novel_id)
        selected = [c for c in chapters if from_chapter_number <= c.number <= to_chapter_number]
        outline_context = self._get_outline_context(project.novel_id)
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        memory["outline_context"] = outline_context
        analyzer = AnalysisTool(self.llm_factory.primary_client, self.llm_factory.backup_client)
        for chapter in selected:
            incremental = await analyzer.execute_async(
                TaskContext(novel_id=str(project.novel_id), goal="v2_refresh_memory"),
                {
                    "mode": "incremental_mode",
                    "chapter": {"index": chapter.number, "title": chapter.title, "content": chapter.content},
                    "memory": self._to_tool_memory_context(memory),
                },
            )
            if incremental.status == "success":
                memory = self._merge_structured_memory(memory, incremental.payload or {}, chapter.title or f"?{chapter.number}?")
        consolidate = await analyzer.execute_async(
            TaskContext(novel_id=str(project.novel_id), goal="v2_refresh_consolidate"),
            {"mode": "consolidate_mode", "memory": self._to_tool_memory_context(memory)},
        )
        if consolidate.status == "success":
            memory = self._merge_structured_memory(memory, consolidate.payload or {}, "璁板繂鍒锋柊")
        self.project_service.bind_memory_to_novel(project.novel_id, memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        view_payload = self._to_memory_view_payload(project_id, memory_payload)
        self.v2_repo.save_memory_view(view_payload)
        return {"project_id": project_id, "memory_view": view_payload}

    def _to_project_memory_payload(self, project_id: str, memory: Dict[str, Any]) -> Dict[str, Any]:
        active_memory = self.v2_repo.find_active_project_memory(project_id) or {}
        version = int(active_memory.get("version") or 0) + 1
        return {
            "id": f"memory_{uuid.uuid4().hex[:12]}",
            "project_id": project_id,
            "version": max(version, 1),
            "characters": memory.get("characters") or [],
            "world_facts": memory.get("world_facts") or {},
            "plot_arcs": memory.get("plot_arcs") or [],
            "events": memory.get("events") or [],
            "style_profile": memory.get("style_profile") or {},
            "outline_context": memory.get("outline_context") or {},
            "current_state": memory.get("current_state") or {},
            "chapter_summaries": memory.get("chapter_summaries") or [],
            "continuity_flags": memory.get("continuity_flags") or [],
        }

    def _to_memory_view_payload(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        chars = payload.get("characters") or []
        main_characters = []
        for item in chars[:5]:
            if isinstance(item, dict):
                main_characters.append(
                    {
                        "name": str(item.get("name") or ""),
                        "role": str(item.get("role") or "瑙掕壊"),
                        "traits": "?".join([str(x) for x in (item.get("traits") or [])[:3]]),
                    }
                )
        world_summary = self._build_world_summary(payload.get("world_facts") or {})
        style = payload.get("style_profile") or {}
        style_tags = []
        if isinstance(style, dict):
            style_tags = [str(style.get("tone") or ""), str(style.get("pacing") or ""), str(style.get("narrative_style") or "")]
            style_tags = [x for x in style_tags if x]
        elif isinstance(style, str):
            style_tags = [x for x in style.split("?") if x]
        outline_context = payload.get("outline_context") or {}
        outline_summary = [str(x) for x in (outline_context.get("summary") or []) if str(x)]
        if not outline_summary:
            outline_summary = [
                str(outline_context.get("premise") or ""),
                str(outline_context.get("story_background") or ""),
                str(outline_context.get("world_setting") or ""),
            ]
            outline_summary = [x for x in outline_summary if x]
        return {
            "id": f"view_{uuid.uuid4().hex[:12]}",
            "project_id": project_id,
            "memory_id": payload["id"],
            "main_characters": main_characters,
            "world_summary": [str(x) for x in world_summary if str(x)],
            "main_plot_lines": self._build_plot_lines(payload),
            "style_tags": style_tags,
            "current_progress": str((payload.get("current_state") or {}).get("latest_summary") or ""),
            "outline_summary": outline_summary[:5],
        }

    def _build_world_summary(self, world_facts: Dict[str, Any]) -> List[str]:
        if not isinstance(world_facts, dict):
            return []
        ordered: List[str] = []
        for key in ("background", "power_system", "organizations", "locations", "rules", "artifacts"):
            ordered.extend([str(x).strip() for x in (world_facts.get(key) or []) if str(x).strip()])
        unique: List[str] = []
        for item in ordered:
            if item not in unique:
                unique.append(item)
        return unique[:8]

    def _build_plot_lines(self, payload: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        for arc in (payload.get("plot_arcs") or []):
            if not isinstance(arc, dict):
                continue
            title = str(arc.get("title") or "").strip()
            summary = str(arc.get("summary") or "").strip()
            stage = str(arc.get("current_stage") or "").strip()
            candidate = summary or (f"{title}: {stage}" if title and stage else title)
            if candidate:
                lines.append(candidate)
        chapter_summaries = [str(x).strip() for x in (payload.get("chapter_summaries") or []) if str(x).strip()]
        lines.extend(chapter_summaries[-6:])
        current_state = payload.get("current_state") or {}
        latest_summary = str(current_state.get("latest_summary") or "").strip() if isinstance(current_state, dict) else ""
        if latest_summary:
            lines.append(latest_summary)
        unique: List[str] = []
        for item in lines:
            if item not in unique:
                unique.append(item)
        return unique[-8:]

    def _get_outline_context(self, novel_id: NovelId) -> Dict[str, Any]:
        outline = self.outline_repo.find_by_novel(novel_id)
        summary = []
        if outline:
            summary = [str(outline.premise or ""), str(outline.story_background or ""), str(outline.world_setting or "")]
            summary = [x for x in summary if x]
        return {
            "premise": outline.premise if outline else "",
            "story_background": outline.story_background if outline else "",
            "world_setting": outline.world_setting if outline else "",
            "summary": summary,
        }

    def _load_structured_memory(
        self,
        project_id: str,
        novel_id: NovelId,
        outline_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        memory = self.v2_repo.find_active_project_memory(project_id) or {}
        if isinstance(memory, dict) and memory.get("world_facts"):
            memory["outline_context"] = outline_context or (memory.get("outline_context") or {})
            return memory
        legacy = self.project_service.get_memory_by_novel(novel_id)
        if self._is_legacy_memory(legacy):
            normalized = self._normalize_legacy_memory(legacy if isinstance(legacy, dict) else {}, outline_context or {})
            normalized["outline_context"] = outline_context or {}
            return normalized
        return self._empty_structured_memory(outline_context or {})

    def _is_legacy_memory(self, memory: Any) -> bool:
        if not isinstance(memory, dict):
            return False
        for key in ("world_settings", "plot_outline", "writing_style", "current_progress"):
            value = memory.get(key)
            if isinstance(value, str) and value.strip():
                return True
            if isinstance(value, dict) and value:
                return True
            if isinstance(value, list) and value:
                return True
        return False

    def _build_outline_consistency_note(self, branch: Dict[str, Any], outline_context: Dict[str, Any]) -> str:
        premise = str(outline_context.get("premise") or "").strip()
        summary = str(branch.get("summary") or "").strip()
        if not premise:
            return "??? memory ??"
        if premise and premise[:10] in summary:
            return "?????????"
        return f"?????????{premise[:48]}"

    def _build_outline_risk_note(self, branch: Dict[str, Any], outline_context: Dict[str, Any]) -> str:
        premise = str(outline_context.get("premise") or "").strip()
        summary = str(branch.get("summary") or "").strip()
        if not premise:
            return ""
        if premise and premise[:10] in summary:
            return ""
        return "鍒嗘敮鍙兘鍋忕澶х翰鍓嶆彁锛屾墽琛屽墠闇€澶嶆牳"

    def _build_chapter_units(self, novel_id: NovelId, mode: str) -> List[Dict[str, Any]]:
        chapters = self.chapter_repo.find_by_novel(novel_id)
        if mode == "chapter_first" and chapters:
            return [
                {
                    "title": chapter.title or f"?{chapter.number}?",
                    "content": chapter.content or "",
                    "index": chapter.number,
                }
                for chapter in chapters
                if (chapter.content or "").strip()
            ]
        novel_text = self.content_service.get_novel_text(str(novel_id))
        chunks = []
        if novel_text.strip():
            for idx, part in enumerate([x for x in novel_text.split("\n\n") if x.strip()], 1):
                chunks.append({"title": f"?{idx}?", "content": part, "index": idx})
        return chunks

    def _empty_structured_memory(self, outline_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "characters": [],
            "world_facts": {"background": [], "power_system": [], "organizations": [], "locations": [], "rules": [], "artifacts": []},
            "plot_arcs": [],
            "events": [],
            "style_profile": {"narrative_pov": "绗笁浜虹О鏈夐檺瑙嗚", "tone_tags": [], "rhythm_tags": []},
            "outline_context": outline_context or {},
            "current_state": {"latest_chapter_number": 0, "latest_summary": "", "active_arc_ids": [], "recent_conflicts": [], "next_writing_focus": ""},
            "chapter_summaries": [],
            "continuity_flags": [],
        }

    def _normalize_legacy_memory(self, memory: Dict[str, Any], outline_context: Dict[str, Any]) -> Dict[str, Any]:
        base = self._empty_structured_memory(outline_context)
        chars = memory.get("characters") or []
        base["characters"] = [x for x in chars if isinstance(x, dict)]
        world_settings = str(memory.get("world_settings") or "")
        segments = [x.strip() for x in re.split(r"[;；?]", world_settings) if x.strip()]
        base["world_facts"]["background"] = segments[:4]
        base["events"] = [x for x in (memory.get("events") or []) if isinstance(x, dict)]
        writing_style = str(memory.get("writing_style") or "")
        style_parts = [x.strip() for x in re.split(r"[;；?]", writing_style) if x.strip()]
        if style_parts:
            base["style_profile"]["narrative_pov"] = style_parts[0]
            base["style_profile"]["tone_tags"] = style_parts[1:3]
            base["style_profile"]["rhythm_tags"] = style_parts[3:5]
        current = memory.get("current_progress")
        if isinstance(current, dict):
            base["current_state"] = {
                "latest_chapter_number": int(current.get("latest_chapter_number") or 0),
                "latest_summary": str(current.get("last_summary") or ""),
                "active_arc_ids": [],
                "recent_conflicts": [],
                "next_writing_focus": str(current.get("latest_goal") or ""),
            }
        elif isinstance(current, str):
            base["current_state"]["latest_summary"] = current
        outline = memory.get("plot_outline")
        if outline:
            base["chapter_summaries"] = [x.strip() for x in re.split(r"[;；?]", str(outline)) if x.strip()][:20]
        return base

    def _to_tool_memory_context(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        structured = {
            "characters": memory.get("characters") or [],
            "world_facts": memory.get("world_facts") or {},
            "plot_arcs": memory.get("plot_arcs") or [],
            "style_profile": memory.get("style_profile") or {},
            "chapter_summaries": memory.get("chapter_summaries") or [],
            "current_state": memory.get("current_state") or {},
            "events": memory.get("events") or [],
            "continuity_flags": memory.get("continuity_flags") or [],
            "outline_context": memory.get("outline_context") or {},
        }
        if self._is_legacy_memory(memory):
            world_parts: List[str] = []
            for key in ("background", "power_system", "organizations", "locations", "rules", "artifacts"):
                world_parts.extend([str(x) for x in ((memory.get("world_facts") or {}).get(key) or []) if str(x)])
            style = memory.get("style_profile") or {}
            style_text = "?".join(
                [
                    str(style.get("narrative_pov") or ""),
                    "?".join([str(x) for x in (style.get("tone_tags") or []) if str(x)]),
                    "?".join([str(x) for x in (style.get("rhythm_tags") or []) if str(x)]),
                ]
            ).strip("?")
            current = memory.get("current_state") or {}
            structured.update(
                {
                    "world_settings": "?".join(world_parts),
                    "plot_outline": "?".join([str(x) for x in (memory.get("chapter_summaries") or [])[:20]]),
                    "writing_style": style_text,
                    "current_progress": {
                        "latest_chapter_number": int(current.get("latest_chapter_number") or 0),
                        "latest_goal": str(current.get("next_writing_focus") or ""),
                        "last_summary": str(current.get("latest_summary") or ""),
                    },
                }
            )
        return structured

    def _merge_structured_memory(self, base: Dict[str, Any], analysis_payload: Dict[str, Any], chapter_title: str) -> Dict[str, Any]:
        merged = dict(base or {})
        characters = merged.get("characters") or []
        new_chars = analysis_payload.get("characters") or []
        by_name = {str(x.get("name") or ""): x for x in characters if isinstance(x, dict)}
        for item in new_chars:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            if name not in by_name:
                by_name[name] = {"name": name, "traits": [], "relationships": {}}
            traits = [str(x).strip() for x in (item.get("traits") or []) if str(x).strip()]
            by_name[name]["traits"] = list(dict.fromkeys([*(by_name[name].get("traits") or []), *traits]))
            relations = item.get("relationships") or {}
            if isinstance(relations, dict):
                by_name[name]["relationships"] = {**(by_name[name].get("relationships") or {}), **relations}
        merged["characters"] = list(by_name.values())
        world_facts = merged.get("world_facts") or {"background": [], "power_system": [], "organizations": [], "locations": [], "rules": [], "artifacts": []}
        incoming_world = analysis_payload.get("world_facts") if isinstance(analysis_payload.get("world_facts"), dict) else {}
        for key in ("background", "power_system", "organizations", "locations", "rules", "artifacts"):
            items = [str(x).strip() for x in (incoming_world.get(key) or []) if str(x).strip()]
            world_facts[key] = list(dict.fromkeys([*(world_facts.get(key) or []), *items]))[:40]
        merged["world_facts"] = world_facts
        events = merged.get("events") or []
        incoming_events = [x for x in (analysis_payload.get("events") or []) if isinstance(x, dict)]
        merged["events"] = [*events, *incoming_events][-160:]
        style = merged.get("style_profile") or {"narrative_pov": "绗笁浜虹О鏈夐檺瑙嗚", "tone_tags": [], "rhythm_tags": []}
        style_profile_payload = analysis_payload.get("style_profile") if isinstance(analysis_payload.get("style_profile"), dict) else {}
        if style_profile_payload:
            tone_tags = [str(x).strip() for x in (style_profile_payload.get("tone_tags") or []) if str(x).strip()]
            rhythm_tags = [str(x).strip() for x in (style_profile_payload.get("rhythm_tags") or []) if str(x).strip()]
            if tone_tags:
                style["tone_tags"] = list(dict.fromkeys([*(style.get("tone_tags") or []), *tone_tags[:3]]))
            if rhythm_tags:
                style["rhythm_tags"] = list(dict.fromkeys([*(style.get("rhythm_tags") or []), *rhythm_tags[:3]]))
            narrative_pov = str(style_profile_payload.get("narrative_pov") or "").strip()
            if narrative_pov:
                style["narrative_pov"] = narrative_pov
        style_tags = [str(x).strip() for x in (analysis_payload.get("style_tags") or []) if str(x).strip()]
        if style_tags:
            style["tone_tags"] = list(dict.fromkeys([*(style.get("tone_tags") or []), *style_tags[:3]]))
        merged["style_profile"] = style
        incoming_summaries = [str(x).strip() for x in (analysis_payload.get("chapter_summaries") or []) if str(x).strip()]
        summary = str(analysis_payload.get("chapter_summary") or chapter_title or "").strip()
        if not incoming_summaries and summary:
            incoming_summaries = [summary]
        if incoming_summaries:
            merged["chapter_summaries"] = [*(merged.get("chapter_summaries") or []), *incoming_summaries][-300:]
        flags = [x for x in (analysis_payload.get("continuity_flags") or []) if isinstance(x, dict)]
        merged["continuity_flags"] = [*(merged.get("continuity_flags") or []), *flags][-80:]
        current_state = merged.get("current_state") or {}
        incoming_state = analysis_payload.get("current_state") if isinstance(analysis_payload.get("current_state"), dict) else {}
        current_state.update(
            {
                "latest_chapter_number": int(
                    incoming_state.get("latest_chapter_number")
                    or current_state.get("latest_chapter_number")
                    or 0
                ),
                "latest_summary": str(
                    incoming_state.get("latest_summary")
                    or summary
                    or current_state.get("latest_summary")
                    or ""
                ),
                "active_arc_ids": incoming_state.get("active_arc_ids") or current_state.get("active_arc_ids") or [],
                "recent_conflicts": incoming_state.get("recent_conflicts") or current_state.get("recent_conflicts") or [],
                "next_writing_focus": str(
                    incoming_state.get("next_writing_focus")
                    or current_state.get("next_writing_focus")
                    or ""
                ),
            }
        )
        merged["current_state"] = current_state
        merged["outline_context"] = merged.get("outline_context") or {}
        merged["plot_arcs"] = merged.get("plot_arcs") or []
        return merged

