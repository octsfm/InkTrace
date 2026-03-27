"""
v2主流程服务。
负责导入、整理、分支、计划、写作、刷新memory全链路。
"""

from __future__ import annotations

from datetime import datetime, UTC
import json
import re
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from application.agent_mvp import AnalysisTool, ContinueWritingTool, StoryBranchTool, TaskContext
from application.dto.request_dto import ImportNovelRequest
from application.services.content_service import ContentService
from application.services.logging_service import build_log_context, get_logger
from application.services.project_service import ProjectService
from domain.entities.chapter import Chapter
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.outline_repository import IOutlineRepository
from domain.types import ChapterId, ChapterStatus, NovelId, ProjectId
from domain.types import GenreType
from domain.utils import looks_garbled_text, repair_mojibake, sanitize_display_text
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
        self.logger = get_logger(__name__)

    def clean_text(self, value: str) -> str:
        cleaned = sanitize_display_text(value)
        if not cleaned:
            return ""
        cleaned = repair_mojibake(cleaned).strip()
        cleaned = re.sub(r"chunk\s*=?\s*\d+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\?{2,}", "", cleaned)
        cleaned = cleaned.replace("分析完成", "").replace("组织完成", "")
        cleaned = cleaned.replace(";", "；")
        cleaned = cleaned.replace(",", "、")
        cleaned = re.sub(r"[|/\\\\]+", "；", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip("；、-:： ")
        return cleaned

    def looks_garbled_text(self, value: str) -> bool:
        if looks_garbled_text(value):
            return True
        if not isinstance(value, str):
            return False
        text = value.strip()
        if not text:
            return False
        if text.count("?") >= max(3, len(text) // 4):
            return True
        return False

    def normalize_text_list(self, items: List[str], limit: int) -> List[str]:
        unique: List[str] = []
        for item in items:
            cleaned = self.clean_text(str(item or ""))
            if not cleaned:
                continue
            if self.looks_garbled_text(cleaned):
                continue
            if cleaned not in unique:
                unique.append(cleaned)
            if len(unique) >= limit:
                break
        return unique[:limit]

    async def import_project(
        self,
        project_name: str,
        genre: str,
        novel_file_path: str,
        author: str = "",
        import_mode: str = "full",
        chapter_items: Optional[List[Dict[str, Any]]] = None,
        outline_file_path: str = "",
        auto_organize: bool = True,
    ) -> Dict[str, Any]:
        self.logger.info(
            "导入项目开始",
            extra=build_log_context(
                event="workflow_import_started",
                project_name=project_name,
                import_mode=import_mode,
                file_path=novel_file_path,
                outline_present=bool(outline_file_path),
            ),
        )
        try:
            genre_enum = GenreType(genre) if genre else GenreType.XUANHUAN
        except ValueError:
            genre_enum = GenreType.XUANHUAN
        project = self.project_service.create_project(name=project_name, genre=genre_enum, author=author)
        request = ImportNovelRequest(
            novel_id=str(project.novel_id),
            file_path=novel_file_path,
            author=author,
            import_mode=import_mode,
            chapter_items=chapter_items or [],
            outline_path=outline_file_path or None,
        )
        self.content_service.import_novel(request)
        memory_view = {}
        if auto_organize:
            organized = await self.organize_project(project.id.value, mode="chapter_first", rebuild_memory=True)
            memory_view = organized.get("memory_view") or {}
        self.logger.info(
            "导入项目完成",
            extra=build_log_context(
                event="workflow_import_finished",
                project_id=project.id.value,
                novel_id=str(project.novel_id),
                status="organized" if auto_organize else "imported",
            ),
        )
        return {
            "project_id": project.id.value,
            "novel_id": str(project.novel_id),
            "outline_id": f"outline_{project.id.value}",
            "status": "organized" if auto_organize else "imported",
            "memory_view": memory_view,
        }

    async def organize_project(
        self,
        project_id: str,
        mode: str,
        rebuild_memory: bool,
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        resume_from: int = 0,
        checkpoint_memory: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "整理开始",
            extra=build_log_context(
                event="organize_started",
                project_id=project_id,
                novel_id=str(project.novel_id),
                mode=mode,
                rebuild_memory=bool(rebuild_memory),
            ),
        )
        async def _emit_progress(
            stage: str,
            current: int,
            total: int,
            message: str,
            current_chapter_title: str = "",
            status: str = "running",
            resumable: bool = False,
            memory_snapshot: Optional[Dict[str, Any]] = None,
        ) -> None:
            if progress_callback is None:
                return
            safe_total = max(int(total), 0)
            safe_current = max(0, min(int(current), safe_total)) if safe_total else 0
            percent = 100 if safe_total and safe_current >= safe_total else int((safe_current / safe_total) * 100) if safe_total else 0
            payload = {
                "status": status,
                "stage": stage,
                "current": safe_current,
                "total": safe_total,
                "percent": percent,
                "message": self.clean_text(message) or message,
                "current_chapter_title": self.clean_text(current_chapter_title),
                "resumable": resumable,
            }
            if isinstance(memory_snapshot, dict):
                payload["memory_snapshot"] = memory_snapshot
            await progress_callback(payload)
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
        total_chapters = len(chapters)
        self.logger.info(
            "整理准备完成",
            extra=build_log_context(event="organize_prepare_done", project_id=project_id, total_chapters=total_chapters),
        )
        resume_cursor = 0 if rebuild_memory else max(0, min(int(resume_from or 0), total_chapters))
        merged_memory: Dict[str, Any] = self._empty_structured_memory(outline_context)
        if not rebuild_memory and resume_cursor > 0 and isinstance(checkpoint_memory, dict) and checkpoint_memory:
            merged_memory = checkpoint_memory
            merged_memory["outline_context"] = outline_context
        await _emit_progress(
            stage="prepare",
            current=resume_cursor,
            total=total_chapters,
            message=f"准备整理章节（{resume_cursor}/{total_chapters}）",
        )
        for index, chapter in enumerate(chapters, 1):
            if index <= resume_cursor:
                continue
            self.logger.info(
                "章节分析开始",
                extra=build_log_context(
                    event="chapter_analysis_started",
                    project_id=project_id,
                    chapter_number=index,
                    chapter_title=chapter.get("title") or f"第{index}章",
                    current=index,
                    total=total_chapters,
                ),
            )
            incremental = await analyzer.execute_async(
                TaskContext(novel_id=novel_id, goal="v2_organize_incremental"),
                {
                    "mode": "incremental_mode",
                    "chapter": chapter,
                    "memory": self._to_tool_memory_context(merged_memory),
                },
            )
            if incremental.status != "success":
                self.logger.error(
                    "章节分析失败",
                    extra=build_log_context(
                        event="chapter_analysis_failed",
                        project_id=project_id,
                        chapter_number=index,
                        chapter_title=chapter.get("title") or f"第{index}章",
                        error="incremental_analysis_failed",
                    ),
                )
                self.v2_repo.finish_workflow_job(job_id, "failed", error_message="章节分析失败")
                raise ValueError("章节分析失败")
            merged_memory = self._merge_structured_memory(
                merged_memory,
                incremental.payload or {},
                chapter.get("title") or "",
                chapter_number=int(chapter.get("index") or index),
                chapter_id=str(chapter.get("id") or ""),
                chapter_content=str(chapter.get("content") or ""),
            )
            self.logger.info(
                "章节分析完成",
                extra=build_log_context(
                    event="chapter_analysis_finished",
                    project_id=project_id,
                    chapter_number=index,
                    chapter_title=chapter.get("title") or f"第{index}章",
                ),
            )
            await _emit_progress(
                stage="chapter_analysis",
                current=index,
                total=total_chapters,
                message=f"正在分析第{index}/{total_chapters}章：{chapter.get('title') or f'第{index}章'}",
                current_chapter_title=str(chapter.get("title") or f"第{index}章"),
                resumable=index < total_chapters,
                memory_snapshot=merged_memory,
            )
        await _emit_progress(
            stage="memory_merge",
            current=total_chapters,
            total=total_chapters,
            message="正在合并章节记忆",
            resumable=False,
        )
        self.logger.info("开始合并记忆", extra=build_log_context(event="memory_merge_started", project_id=project_id))
        consolidate = await analyzer.execute_async(
            TaskContext(novel_id=novel_id, goal="v2_organize_consolidate"),
            {"mode": "consolidate_mode", "memory": self._to_tool_memory_context(merged_memory)},
        )
        if consolidate.status != "success":
            self.logger.error("记忆合并失败", extra=build_log_context(event="memory_merge_failed", project_id=project_id))
            self.v2_repo.finish_workflow_job(job_id, "failed", error_message="全局收敛失败")
            raise ValueError("全局收敛失败")
        memory = self._merge_structured_memory(merged_memory, consolidate.payload or {}, "全局收敛")
        self.logger.info("记忆合并完成", extra=build_log_context(event="memory_merge_finished", project_id=project_id))
        await _emit_progress(
            stage="memory_view_build",
            current=total_chapters,
            total=total_chapters,
            message="正在生成结构摘要",
            resumable=False,
        )
        self.logger.info("开始构建摘要视图", extra=build_log_context(event="memory_view_build_started", project_id=project_id))
        self.project_service.bind_memory_to_novel(NovelId(novel_id), memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        view_payload = self._to_memory_view_payload(project_id, memory_payload)
        self.v2_repo.save_memory_view(view_payload)
        self.logger.info("摘要视图构建完成", extra=build_log_context(event="memory_view_build_finished", project_id=project_id))
        self.v2_repo.finish_workflow_job(
            job_id,
            "success",
            result_payload={"organized_chapter_count": len(chapters), "memory_id": memory_payload["id"]},
        )
        self.logger.info(
            "整理完成",
            extra=build_log_context(
                event="organize_finished",
                project_id=project_id,
                organized_chapter_count=len(chapters),
                memory_id=memory_payload["id"],
            ),
        )
        await _emit_progress(
            stage="done",
            current=total_chapters,
            total=total_chapters,
            message=f"整理完成（{total_chapters}/{total_chapters}）",
            status="done",
            resumable=False,
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

    def get_style_requirements(self, project_id: str) -> Dict[str, Any]:
        memory = self.get_memory(project_id) or {}
        style_requirements = memory.get("style_requirements")
        if not isinstance(style_requirements, dict):
            style_requirements = {}
        return {
            "project_id": project_id,
            "style_requirements": {
                "author_voice_keywords": [str(x) for x in (style_requirements.get("author_voice_keywords") or []) if str(x).strip()],
                "avoid_patterns": [str(x) for x in (style_requirements.get("avoid_patterns") or []) if str(x).strip()],
                "preferred_rhythm": self.clean_text(str(style_requirements.get("preferred_rhythm") or "")),
                "narrative_distance": self.clean_text(str(style_requirements.get("narrative_distance") or "")),
                "dialogue_density": self.clean_text(str(style_requirements.get("dialogue_density") or "")),
            },
        }

    def update_style_requirements(self, project_id: str, style_requirements: Dict[str, Any]) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        outline_context = self._get_outline_context(project.novel_id)
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        incoming = style_requirements if isinstance(style_requirements, dict) else {}
        current = memory.get("style_requirements") if isinstance(memory.get("style_requirements"), dict) else {}
        merged = {
            "author_voice_keywords": self.normalize_text_list(
                [str(x) for x in ((incoming.get("author_voice_keywords") if "author_voice_keywords" in incoming else current.get("author_voice_keywords")) or [])],
                20,
            ),
            "avoid_patterns": self.normalize_text_list(
                [str(x) for x in ((incoming.get("avoid_patterns") if "avoid_patterns" in incoming else current.get("avoid_patterns")) or [])],
                20,
            ),
            "preferred_rhythm": self.clean_text(str(incoming.get("preferred_rhythm") if "preferred_rhythm" in incoming else current.get("preferred_rhythm") or "")),
            "narrative_distance": self.clean_text(str(incoming.get("narrative_distance") if "narrative_distance" in incoming else current.get("narrative_distance") or "")),
            "dialogue_density": self.clean_text(str(incoming.get("dialogue_density") if "dialogue_density" in incoming else current.get("dialogue_density") or "")),
        }
        memory["style_requirements"] = merged
        self.project_service.bind_memory_to_novel(project.novel_id, memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        self.v2_repo.save_memory_view(self._to_memory_view_payload(project_id, memory_payload))
        return {"project_id": project_id, "style_requirements": merged}

    def get_chapter_editor_context(self, project_id: str, chapter_number: int = 0, recent_limit: int = 5) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "加载章节编辑上下文",
            extra=build_log_context(
                event="chapter_context_loaded",
                project_id=project_id,
                chapter_number=chapter_number,
                recent_limit=recent_limit,
            ),
        )
        memory_view = self.get_memory_view(project_id) or {}
        memory_payload = self.get_memory(project_id) or {}
        chapters = sorted(self.chapter_repo.find_by_novel(project.novel_id), key=lambda x: x.number)
        if chapter_number > 0:
            history = [ch for ch in chapters if ch.number < chapter_number]
        else:
            history = chapters
        recent = history[-max(1, int(recent_limit)) :]
        recent_summaries = []
        for item in recent:
            summary = self.clean_text((item.content or "").strip().replace("\n", " ")[:120])
            if summary:
                recent_summaries.append(f"第{item.number}章 {item.title}：{summary}")
        outline_summary = memory_view.get("outline_summary") or []
        if not outline_summary:
            outline_ctx = memory_payload.get("outline_context") or {}
            outline_summary = [
                str(x).strip()
                for x in (outline_ctx.get("summary") or [])
                if str(x).strip()
            ]
        global_memory_summary = "；".join([str(x).strip() for x in (memory_view.get("main_plot_lines") or []) if str(x).strip()])
        if not global_memory_summary:
            global_memory_summary = self.clean_text(str(memory_view.get("current_progress") or ""))
        return {
            "project_id": project_id,
            "memory_view": memory_view,
            "outline_summary": outline_summary[:6],
            "recent_chapter_summaries": recent_summaries,
            "current_progress": self.clean_text(str(memory_view.get("current_progress") or "")),
            "global_memory_summary": global_memory_summary,
            "global_outline_summary": "；".join([str(x).strip() for x in outline_summary[:6] if str(x).strip()]),
        }

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
        self.logger.info(
            "分支生成开始",
            extra=build_log_context(event="branches_started", project_id=project_id, branch_count=branch_count),
        )
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
            self.logger.error("分支生成失败", extra=build_log_context(event="branches_failed", project_id=project_id, branch_count=branch_count))
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
        self.logger.info("分支生成完成", extra=build_log_context(event="branches_finished", project_id=project_id, branch_count=len(branches)))
        return {"project_id": project_id, "branches": branches}

    def create_chapter_plan(self, project_id: str, branch_id: str, chapter_count: int, target_words_per_chapter: int) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "章节计划开始",
            extra=build_log_context(event="chapter_plan_started", project_id=project_id, branch_id=branch_id, chapter_count=chapter_count),
        )
        chapters = self.chapter_repo.find_by_novel(project.novel_id)
        start_no = max([int(ch.number) for ch in chapters], default=0) + 1
        branches = self.v2_repo.list_branches(project_id)
        branch = next((b for b in branches if b["id"] == branch_id), None)
        if not branch:
            raise ValueError("分支不存在")
        outline_context = self._get_outline_context(project.novel_id)
        outline_summary = "；".join(
            [
                str(outline_context.get("premise") or ""),
                str(outline_context.get("story_background") or ""),
                str(outline_context.get("world_setting") or ""),
            ]
        ).strip("；")
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        plans = []
        continuation_memories = memory.get("chapter_continuation_memories") if isinstance(memory.get("chapter_continuation_memories"), list) else []
        latest_continuation = continuation_memories[-1] if continuation_memories else {}
        must_continue_points = latest_continuation.get("must_continue_points") if isinstance(latest_continuation, dict) else []
        forbidden_jumps = latest_continuation.get("forbidden_jumps") if isinstance(latest_continuation, dict) else []
        opening_continuation = str((latest_continuation or {}).get("last_hook") or memory.get("current_state", {}).get("latest_summary") or "")
        tone_tags = [str(x).strip() for x in ((memory.get("style_profile") or {}).get("tone_tags") or []) if str(x).strip()]
        for i in range(chapter_count):
            no = start_no + i
            outline_clause = f"并参考大纲约束：{outline_summary[:120]}" if outline_summary else "并保持与当前大纲和设定一致"
            plans.append(
                {
                    "id": f"plan_{uuid.uuid4().hex[:10]}",
                    "project_id": project_id,
                    "branch_id": branch_id,
                    "chapter_number": no,
                    "title": f"第{no}章",
                    "goal": f"围绕“{branch['title']}”推进第{i + 1}章情节，{outline_clause}",
                    "conflict": f"{branch['core_conflict'] or '制造新的关键冲突'}，并推动人物关系或主线变化",
                    "progression": f"承接分支摘要：{branch['summary']}，在本章内完成明确推进，并为下一章留下新的问题或压力。",
                    "ending_hook": f"在“{branch['title']}”方向上留下新的悬念或转折",
                    "target_words": target_words_per_chapter,
                    "related_arc_ids": [],
                    "status": "ready",
                    "chapter_id": f"planned_{project_id}_{no}",
                    "chapter_function": "推进主线",
                    "goals": [f"推进“{branch['title']}”分支主线", f"第{no}章完成阶段推进"],
                    "must_continue_points": [str(x) for x in (must_continue_points or []) if str(x).strip()],
                    "forbidden_jumps": [str(x) for x in (forbidden_jumps or []) if str(x).strip()],
                    "required_foreshadowing_action": "推进",
                    "required_hook_strength": "中",
                    "pace_target": "中速推进",
                    "opening_continuation": self.clean_text(opening_continuation),
                    "chapter_payoff": f"完成分支“{branch['title']}”的阶段性收益",
                    "style_bias": "、".join(tone_tags[:3]),
                }
            )
        self.v2_repo.replace_plans(project_id, plans)
        memory["chapter_tasks"] = [*(memory.get("chapter_tasks") or []), *plans][-300:]
        self.project_service.bind_memory_to_novel(project.novel_id, memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        self.v2_repo.save_memory_view(self._to_memory_view_payload(project_id, memory_payload))
        self.logger.info(
            "章节计划完成",
            extra=build_log_context(event="chapter_plan_finished", project_id=project_id, branch_id=branch_id, chapter_count=len(plans)),
        )
        return {"project_id": project_id, "branch_id": branch_id, "plans": plans}

    async def execute_writing(self, project_id: str, plan_ids: List[str], auto_commit: bool) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info("续写开始", extra=build_log_context(event="write_started", project_id=project_id, plan_ids=plan_ids))
        plans = self.v2_repo.find_plans(project_id, plan_ids)
        if not plans:
            raise ValueError("未找到可执行的章节计划")
        outline_context = self._get_outline_context(project.novel_id)
        memory = self._load_structured_memory(project_id, project.novel_id, outline_context)
        session_id = self.v2_repo.start_writing_session(project_id, plans[0]["branch_id"] if plans else "", plan_ids)
        tool = ContinueWritingTool(self.llm_factory.primary_client, self.llm_factory.backup_client)
        generated_ids: List[str] = []
        latest_content = ""
        latest_title = ""
        latest_chapter_number = 0
        latest_structural_draft: Dict[str, Any] = {}
        latest_detemplated_draft: Dict[str, Any] = {}
        latest_integrity_check: Dict[str, Any] = {}
        chapters = self.chapter_repo.find_by_novel(project.novel_id)
        next_number = max([int(ch.number) for ch in chapters], default=0) + 1 if auto_commit else 0
        memory["outline_context"] = outline_context
        for plan in plans:
            direction = f"{plan['goal']}；{plan['conflict']}；{plan['progression']}"
            result = await tool.execute_async(
                TaskContext(novel_id=str(project.novel_id), goal=direction, target_word_count=plan["target_words"]),
                {
                    "direction": direction,
                    "chapter_task": {
                        "chapter_id": str(plan.get("chapter_id") or ""),
                        "chapter_number": int(plan.get("chapter_number") or 0),
                        "chapter_function": str(plan.get("chapter_function") or ""),
                        "goals": [str(x) for x in (plan.get("goals") or [])],
                        "must_continue_points": [str(x) for x in (plan.get("must_continue_points") or [])],
                        "forbidden_jumps": [str(x) for x in (plan.get("forbidden_jumps") or [])],
                        "required_foreshadowing_action": str(plan.get("required_foreshadowing_action") or "推进"),
                        "required_hook_strength": str(plan.get("required_hook_strength") or "中"),
                        "pace_target": str(plan.get("pace_target") or ""),
                        "opening_continuation": str(plan.get("opening_continuation") or ""),
                        "chapter_payoff": str(plan.get("chapter_payoff") or ""),
                        "style_bias": str(plan.get("style_bias") or ""),
                    },
                    "global_constraints": memory.get("global_constraints") or {},
                    "style_requirements": memory.get("style_requirements") or {},
                    "memory": self._to_tool_memory_context(memory),
                    "chapters": [{"content": ch.content, "number": ch.number} for ch in chapters[-8:]],
                    "chapter_count": len(chapters),
                    "target_word_count": plan["target_words"],
                    "idempotency_key": f"{project_id}:{plan['id']}",
                },
            )
            if result.status != "success":
                self.logger.error("续写失败", extra=build_log_context(event="write_failed", project_id=project_id, plan_ids=plan_ids))
                self.v2_repo.finish_writing_session(session_id, "failed", generated_ids)
                raise ValueError("续写失败")
            chapter_text = str((result.payload or {}).get("chapter_text") or "")
            normalized = self._normalize_generated_chapter_output(
                chapter_text=chapter_text,
                plan_title=str(plan.get("title") or ""),
                chapter_number=int(plan.get("chapter_number") or 0),
            )
            task_id = str(plan.get("id") or "")
            structural_id = f"struct_{uuid.uuid4().hex[:10]}"
            structural_draft = {
                "id": structural_id,
                "chapter_id": str(plan.get("chapter_id") or ""),
                "chapter_number": int(normalized["chapter_number"] or 0),
                "title": self._ensure_chapter_title(normalized["title"], int(normalized["chapter_number"] or 0)),
                "content": normalized["content"],
                "source_task_id": task_id,
                "generation_notes": [self.clean_text(str(plan.get("chapter_function") or "推进主线"))],
            }
            detemplated_text = self._detemplate_content(structural_draft["content"], memory.get("style_requirements") or {}, plan)
            detemplated_draft = {
                "id": f"det_{uuid.uuid4().hex[:10]}",
                "chapter_id": str(plan.get("chapter_id") or ""),
                "chapter_number": structural_draft["chapter_number"],
                "title": structural_draft["title"],
                "content": detemplated_text,
                "based_on_structural_draft_id": structural_id,
                "style_requirements_snapshot": memory.get("style_requirements") or {},
            }
            integrity_check = self._check_draft_integrity(structural_draft, detemplated_draft, plan)
            used_structural_fallback = False
            if not self._is_integrity_ok(integrity_check):
                detemplated_draft["content"] = structural_draft["content"]
                detemplated_draft["title"] = structural_draft["title"]
                used_structural_fallback = True
                integrity_check["risk_notes"] = [*(integrity_check.get("risk_notes") or []), "检测到一致性风险，已回退结构稿"]
            memory["structural_drafts"] = [*(memory.get("structural_drafts") or []), structural_draft][-200:]
            memory["detemplated_drafts"] = [*(memory.get("detemplated_drafts") or []), detemplated_draft][-200:]
            memory["draft_integrity_checks"] = [*(memory.get("draft_integrity_checks") or []), integrity_check][-200:]
            latest_structural_draft = dict(structural_draft)
            latest_detemplated_draft = dict(detemplated_draft)
            latest_integrity_check = dict(integrity_check)
            latest_content = detemplated_draft["content"]
            latest_title = detemplated_draft["title"]
            latest_chapter_number = int(normalized["chapter_number"] or 0)
            if auto_commit:
                no = next_number
                next_number += 1
                now = datetime.now()
                chapter = Chapter(
                    id=ChapterId(str(uuid.uuid4())),
                    novel_id=project.novel_id,
                    number=no,
                    title=self._ensure_chapter_title(normalized["title"], no),
                    content=latest_content,
                    status=ChapterStatus.DRAFT,
                    created_at=now,
                    updated_at=now,
                )
                self.chapter_repo.save(chapter)
                chapters.append(chapter)
                generated_ids.append(chapter.id.value)
                latest_title = chapter.title
                latest_chapter_number = no
                structural_draft["chapter_id"] = chapter.id.value
                structural_draft["chapter_number"] = no
                structural_draft["title"] = chapter.title
                detemplated_draft["chapter_id"] = chapter.id.value
                detemplated_draft["chapter_number"] = no
                detemplated_draft["title"] = chapter.title
                integrity_check["chapter_number"] = no
                tasks = memory.get("chapter_tasks") or []
                updated_tasks = []
                for task in tasks:
                    if isinstance(task, dict) and str(task.get("id") or "") == str(plan.get("id") or ""):
                        copied = dict(task)
                        copied["chapter_id"] = chapter.id.value
                        copied["chapter_number"] = no
                        copied["title"] = chapter.title
                        copied["status"] = "done"
                        updated_tasks.append(copied)
                    else:
                        updated_tasks.append(task)
                memory["chapter_tasks"] = updated_tasks[-300:]
            if auto_commit:
                memory["events"] = [*(memory.get("events") or []), *((result.payload or {}).get("new_events") or [])][-120:]
                memory["chapter_summaries"] = [*(memory.get("chapter_summaries") or []), latest_content[:120]][-300:]
                current_state = memory.get("current_state") or {}
                current_state.update(
                    {
                        "latest_chapter_number": latest_chapter_number,
                        "latest_summary": latest_content[:120],
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
        self.logger.info(
            "续写完成",
            extra=build_log_context(event="write_finished", project_id=project_id, plan_ids=plan_ids, generated_count=len(generated_ids)),
        )
        return {
            "project_id": project_id,
            "generated_chapter_ids": generated_ids,
            "latest_content": latest_content,
            "latest_title": latest_title,
            "latest_chapter_number": latest_chapter_number,
            "latest_chapter": {
                "number": latest_chapter_number,
                "title": latest_title,
                "content": latest_content,
            },
            "latest_structural_draft": latest_structural_draft,
            "latest_detemplated_draft": latest_detemplated_draft,
            "latest_draft_integrity_check": latest_integrity_check,
            "used_structural_fallback": bool((latest_integrity_check.get("risk_notes") or []) and "回退结构稿" in "；".join(latest_integrity_check.get("risk_notes") or [])),
            "memory_view": view_payload,
        }

    async def refresh_memory(self, project_id: str, from_chapter_number: int, to_chapter_number: int) -> Dict[str, Any]:
        project = self.project_service.get_project(ProjectId(project_id))
        if not project:
            raise ValueError("项目不存在")
        self.logger.info(
            "刷新记忆开始",
            extra=build_log_context(
                event="refresh_memory_started",
                project_id=project_id,
                from_chapter_number=from_chapter_number,
                to_chapter_number=to_chapter_number,
            ),
        )
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
                memory = self._merge_structured_memory(
                    memory,
                    incremental.payload or {},
                    chapter.title or f"第{chapter.number}章",
                    chapter_number=chapter.number,
                    chapter_id=chapter.id.value,
                    chapter_content=chapter.content or "",
                )
        consolidate = await analyzer.execute_async(
            TaskContext(novel_id=str(project.novel_id), goal="v2_refresh_consolidate"),
            {"mode": "consolidate_mode", "memory": self._to_tool_memory_context(memory)},
        )
        if consolidate.status == "success":
            memory = self._merge_structured_memory(memory, consolidate.payload or {}, "增量汇总")
        self.project_service.bind_memory_to_novel(project.novel_id, memory)
        memory_payload = self._to_project_memory_payload(project_id, memory)
        self.v2_repo.save_project_memory(memory_payload)
        view_payload = self._to_memory_view_payload(project_id, memory_payload)
        self.v2_repo.save_memory_view(view_payload)
        self.logger.info(
            "刷新记忆完成",
            extra=build_log_context(
                event="refresh_memory_finished",
                project_id=project_id,
                from_chapter_number=from_chapter_number,
                to_chapter_number=to_chapter_number,
            ),
        )
        return {"project_id": project_id, "memory_view": view_payload}

    def _ensure_chapter_title(self, title: str, chapter_number: int) -> str:
        text = self.clean_text(str(title or "")).strip()
        return text or f"第{chapter_number}章"

    def _normalize_generated_chapter_output(self, chapter_text: str, plan_title: str, chapter_number: int) -> Dict[str, Any]:
        raw = str(chapter_text or "").strip()
        title = self.clean_text(str(plan_title or "")).strip()
        content = raw
        if raw.startswith("{") and raw.endswith("}"):
            try:
                payload = json.loads(raw)
            except Exception:
                payload = None
            if isinstance(payload, dict):
                title = self.clean_text(str(payload.get("title") or payload.get("chapter_title") or title)).strip()
                extracted = payload.get("content") or payload.get("chapter_text") or payload.get("result_text") or ""
                content = str(extracted or "").strip()
        if not content:
            content = raw
        safe_no = int(chapter_number or 0)
        if not title and safe_no > 0:
            title = f"第{safe_no}章"
        return {"chapter_number": safe_no, "title": title, "content": content}

    def _build_global_constraints(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        chapter_summaries = [self.clean_text(str(x)) for x in (memory.get("chapter_summaries") or []) if str(x).strip()]
        plot_lines = self._build_plot_lines(memory)
        protagonist_traits: List[str] = []
        for char in (memory.get("characters") or []):
            if isinstance(char, dict):
                protagonist_traits.extend([str(x) for x in (char.get("traits") or []) if str(x).strip()])
        return {
            "main_plot": plot_lines[0] if plot_lines else "",
            "hidden_plot": plot_lines[1] if len(plot_lines) > 1 else "",
            "core_selling_points": self.normalize_text_list(plot_lines[:5], 8),
            "protagonist_core_traits": self.normalize_text_list(protagonist_traits, 12),
            "must_keep_threads": self.normalize_text_list(chapter_summaries[-10:], 12),
            "genre_guardrails": self.normalize_text_list([str(memory.get("outline_context", {}).get("premise") or "")], 6),
        }

    def _build_style_requirements(self, style_profile: Dict[str, Any]) -> Dict[str, Any]:
        style = style_profile if isinstance(style_profile, dict) else {}
        return {
            "author_voice_keywords": self.normalize_text_list([str(x) for x in (style.get("tone_tags") or [])], 10),
            "avoid_patterns": [],
            "preferred_rhythm": self.clean_text(str("、".join([str(x) for x in (style.get("rhythm_tags") or []) if str(x).strip()]))),
            "narrative_distance": self.clean_text(str(style.get("narrative_pov") or "")),
            "dialogue_density": "中",
        }

    def _detemplate_content(self, content: str, style_requirements: Dict[str, Any], chapter_task: Dict[str, Any]) -> str:
        text = str(content or "").strip()
        if not text:
            return ""
        avoid_patterns = [str(x).strip() for x in ((style_requirements or {}).get("avoid_patterns") or []) if str(x).strip()]
        defaults = ["与此同时", "下一刻", "不由得", "仿佛", "毫无疑问"]
        for phrase in [*defaults, *avoid_patterns]:
            text = text.replace(phrase, "")
        style_bias = self.clean_text(str((chapter_task or {}).get("style_bias") or ""))
        if style_bias and style_bias not in text[:100]:
            text = f"{style_bias}。{text}"
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    def _check_draft_integrity(self, structural_draft: Dict[str, Any], detemplated_draft: Dict[str, Any], chapter_task: Dict[str, Any]) -> Dict[str, Any]:
        source = str(structural_draft.get("content") or "")
        target = str(detemplated_draft.get("content") or "")
        must_continue = [str(x) for x in ((chapter_task or {}).get("must_continue_points") or []) if str(x).strip()]
        forbidden = [str(x) for x in ((chapter_task or {}).get("forbidden_jumps") or []) if str(x).strip()]
        risk_notes: List[str] = []
        if not target:
            risk_notes.append("去模板化后正文为空")
        event_integrity_ok = len(target) >= max(200, int(len(source) * 0.5)) if source else bool(target)
        if not event_integrity_ok:
            risk_notes.append("事件信息疑似丢失")
        motivation_integrity_ok = True
        if must_continue:
            missing = [item for item in must_continue if item not in target]
            motivation_integrity_ok = len(missing) <= max(1, len(must_continue) // 2)
            if not motivation_integrity_ok:
                risk_notes.append("关键承接点缺失过多")
        foreshadowing_integrity_ok = True
        if str(chapter_task.get("required_foreshadowing_action") or "") == "回收" and "伏笔" not in target:
            foreshadowing_integrity_ok = False
            risk_notes.append("要求回收伏笔但正文未体现")
        hook_integrity_ok = str(chapter_task.get("required_hook_strength") or "中") != "强" or any(x in target[-60:] for x in ["？", "！", "……"])
        if not hook_integrity_ok:
            risk_notes.append("章节结尾钩子强度不足")
        continuity_ok = True
        violated = [item for item in forbidden if item and item in target]
        if violated:
            continuity_ok = False
            risk_notes.append(f"触发禁跳项: {'、'.join(violated[:3])}")
        return {
            "chapter_number": int(structural_draft.get("chapter_number") or 0),
            "event_integrity_ok": event_integrity_ok,
            "motivation_integrity_ok": motivation_integrity_ok,
            "foreshadowing_integrity_ok": foreshadowing_integrity_ok,
            "hook_integrity_ok": hook_integrity_ok,
            "continuity_ok": continuity_ok,
            "risk_notes": risk_notes,
        }

    def _is_integrity_ok(self, check: Dict[str, Any]) -> bool:
        return bool(
            check.get("event_integrity_ok")
            and check.get("motivation_integrity_ok")
            and check.get("foreshadowing_integrity_ok")
            and check.get("hook_integrity_ok")
            and check.get("continuity_ok")
        )

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
            "global_constraints": memory.get("global_constraints") or {},
            "chapter_analysis_memories": memory.get("chapter_analysis_memories") or [],
            "chapter_continuation_memories": memory.get("chapter_continuation_memories") or [],
            "chapter_tasks": memory.get("chapter_tasks") or [],
            "structural_drafts": memory.get("structural_drafts") or [],
            "detemplated_drafts": memory.get("detemplated_drafts") or [],
            "draft_integrity_checks": memory.get("draft_integrity_checks") or [],
            "style_requirements": memory.get("style_requirements") or {},
        }

    def _to_memory_view_payload(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        chars = payload.get("characters") or []
        main_characters = []
        for item in chars[:5]:
            if isinstance(item, dict):
                name = self.clean_text(str(item.get("name") or ""))
                role = self.clean_text(str(item.get("role") or "角色")) or "角色"
                if not name or self.looks_garbled_text(name):
                    continue
                trait_items = self.normalize_text_list([str(x) for x in (item.get("traits") or [])], 3)
                main_characters.append(
                    {
                        "name": name,
                        "role": role,
                        "traits": "、".join(trait_items),
                    }
                )
        world_summary = self.normalize_text_list(self._build_world_summary(payload.get("world_facts") or {}), 8)
        style = payload.get("style_profile") or {}
        style_tags: List[str] = []
        if isinstance(style, dict):
            style_tags = [
                *[str(x) for x in (style.get("tone_tags") or [])],
                *[str(x) for x in (style.get("rhythm_tags") or [])],
                str(style.get("narrative_pov") or ""),
            ]
        elif isinstance(style, str):
            style_tags = [x for x in re.split(r"[；;]", style) if x]
        style_tags = self.normalize_text_list(style_tags, 6)
        outline_context = payload.get("outline_context") or {}
        outline_summary = [str(x) for x in (outline_context.get("summary") or []) if str(x)]
        if not outline_summary:
            outline_summary = [
                str(outline_context.get("premise") or ""),
                str(outline_context.get("story_background") or ""),
                str(outline_context.get("world_setting") or ""),
            ]
            outline_summary = [x for x in outline_summary if x]
        outline_summary = self.normalize_text_list(outline_summary, 5)
        current_progress = self.clean_text(str((payload.get("current_state") or {}).get("latest_summary") or ""))
        return {
            "id": f"view_{uuid.uuid4().hex[:12]}",
            "project_id": project_id,
            "memory_id": payload["id"],
            "main_characters": main_characters,
            "world_summary": world_summary,
            "main_plot_lines": self._build_plot_lines(payload),
            "style_tags": style_tags,
            "current_progress": current_progress,
            "outline_summary": outline_summary,
        }

    def _build_world_summary(self, world_facts: Dict[str, Any]) -> List[str]:
        if not isinstance(world_facts, dict):
            return []
        ordered: List[str] = []
        for key in ("background", "power_system", "organizations", "locations", "rules", "artifacts"):
            ordered.extend([self.clean_text(str(x)) for x in (world_facts.get(key) or [])])
        return self.normalize_text_list(ordered, 8)

    def _build_plot_lines(self, payload: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        for arc in (payload.get("plot_arcs") or []):
            if not isinstance(arc, dict):
                continue
            title = self.clean_text(str(arc.get("title") or ""))
            summary = self.clean_text(str(arc.get("summary") or ""))
            stage = self.clean_text(str(arc.get("current_stage") or ""))
            candidate = summary or (f"{title}：{stage}" if title and stage else title)
            if candidate:
                lines.append(candidate)
        chapter_summaries = [self.clean_text(str(x)) for x in (payload.get("chapter_summaries") or []) if str(x).strip()]
        lines.extend(chapter_summaries[-6:])
        current_state = payload.get("current_state") or {}
        latest_summary = self.clean_text(str(current_state.get("latest_summary") or "")) if isinstance(current_state, dict) else ""
        if latest_summary:
            lines.append(latest_summary)
        filtered = [line for line in lines if line and "chunk=" not in line and "分析完成" not in line]
        return self.normalize_text_list(filtered, 8)

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
        premise = self.clean_text(str(outline_context.get("premise") or ""))
        summary = self.clean_text(str(branch.get("summary") or ""))
        if not premise:
            return "暂无大纲约束"
        if premise and premise[:10] in summary:
            return "与当前大纲方向基本一致"
        return f"与当前大纲存在偏移风险，需留意设定：{premise[:48]}"

    def _build_outline_risk_note(self, branch: Dict[str, Any], outline_context: Dict[str, Any]) -> str:
        premise = self.clean_text(str(outline_context.get("premise") or ""))
        summary = self.clean_text(str(branch.get("summary") or ""))
        if not premise:
            return ""
        if premise and premise[:10] in summary:
            return ""
        return f"与当前大纲存在偏移风险，需留意设定：{premise[:48]}"

    def _build_chapter_units(self, novel_id: NovelId, mode: str) -> List[Dict[str, Any]]:
        chapters = self.chapter_repo.find_by_novel(novel_id)
        if mode == "chapter_first" and chapters:
            return [
                {
                    "title": self.clean_text(chapter.title) or f"第{chapter.number}章",
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
                chunks.append({"title": f"片段{idx}", "content": part, "index": idx})
        return chunks

    def _empty_structured_memory(self, outline_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "characters": [],
            "world_facts": {"background": [], "power_system": [], "organizations": [], "locations": [], "rules": [], "artifacts": []},
            "plot_arcs": [],
            "events": [],
            "style_profile": {"narrative_pov": "第三人称有限视角", "tone_tags": [], "rhythm_tags": []},
            "outline_context": outline_context or {},
            "current_state": {"latest_chapter_number": 0, "latest_summary": "", "active_arc_ids": [], "recent_conflicts": [], "next_writing_focus": ""},
            "chapter_summaries": [],
            "continuity_flags": [],
            "global_constraints": {
                "main_plot": "",
                "hidden_plot": "",
                "core_selling_points": [],
                "protagonist_core_traits": [],
                "must_keep_threads": [],
                "genre_guardrails": [],
            },
            "chapter_analysis_memories": [],
            "chapter_continuation_memories": [],
            "chapter_tasks": [],
            "structural_drafts": [],
            "detemplated_drafts": [],
            "draft_integrity_checks": [],
            "style_requirements": {
                "author_voice_keywords": [],
                "avoid_patterns": [],
                "preferred_rhythm": "",
                "narrative_distance": "",
                "dialogue_density": "",
            },
        }

    def _normalize_legacy_memory(self, memory: Dict[str, Any], outline_context: Dict[str, Any]) -> Dict[str, Any]:
        base = self._empty_structured_memory(outline_context)
        chars = memory.get("characters") or []
        base["characters"] = [x for x in chars if isinstance(x, dict)]
        world_settings = self.clean_text(str(memory.get("world_settings") or ""))
        segments = [x.strip() for x in re.split(r"[；;]", world_settings) if x.strip()]
        base["world_facts"]["background"] = segments[:4]
        base["events"] = [x for x in (memory.get("events") or []) if isinstance(x, dict)]
        writing_style = self.clean_text(str(memory.get("writing_style") or ""))
        style_parts = [x.strip() for x in re.split(r"[；;]", writing_style) if x.strip()]
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
            base["current_state"]["latest_summary"] = self.clean_text(current)
        outline = memory.get("plot_outline")
        if outline:
            base["chapter_summaries"] = self.normalize_text_list([x.strip() for x in re.split(r"[；;]", str(outline)) if x.strip()], 20)
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
            "global_constraints": memory.get("global_constraints") or {},
            "style_requirements": memory.get("style_requirements") or {},
            "chapter_analysis_memories": memory.get("chapter_analysis_memories") or [],
            "chapter_continuation_memories": memory.get("chapter_continuation_memories") or [],
            "chapter_tasks": memory.get("chapter_tasks") or [],
        }
        if self._is_legacy_memory(memory):
            world_parts: List[str] = []
            for key in ("background", "power_system", "organizations", "locations", "rules", "artifacts"):
                world_parts.extend([self.clean_text(str(x)) for x in ((memory.get("world_facts") or {}).get(key) or []) if str(x)])
            style = memory.get("style_profile") or {}
            style_text = "；".join(
                [
                    self.clean_text(str(style.get("narrative_pov") or "")),
                    "、".join(self.normalize_text_list([str(x) for x in (style.get("tone_tags") or []) if str(x)], 6)),
                    "、".join(self.normalize_text_list([str(x) for x in (style.get("rhythm_tags") or []) if str(x)], 6)),
                ]
            ).strip("；")
            current = memory.get("current_state") or {}
            structured.update(
                {
                    "world_settings": "；".join([x for x in world_parts if x]),
                    "plot_outline": "；".join(self.normalize_text_list([str(x) for x in (memory.get("chapter_summaries") or [])], 20)),
                    "writing_style": style_text,
                    "current_progress": {
                        "latest_chapter_number": int(current.get("latest_chapter_number") or 0),
                        "latest_goal": str(current.get("next_writing_focus") or ""),
                        "last_summary": str(current.get("latest_summary") or ""),
                    },
                }
            )
        return structured

    def _merge_structured_memory(
        self,
        base: Dict[str, Any],
        analysis_payload: Dict[str, Any],
        chapter_title: str,
        chapter_number: int = 0,
        chapter_id: str = "",
        chapter_content: str = "",
    ) -> Dict[str, Any]:
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
            items = self.normalize_text_list([str(x).strip() for x in (incoming_world.get(key) or []) if str(x).strip()], 40)
            world_facts[key] = list(dict.fromkeys([*(world_facts.get(key) or []), *items]))[:40]
        merged["world_facts"] = world_facts
        events = merged.get("events") or []
        incoming_events = [x for x in (analysis_payload.get("events") or []) if isinstance(x, dict)]
        merged["events"] = [*events, *incoming_events][-160:]
        style = merged.get("style_profile") or {"narrative_pov": "第三人称有限视角", "tone_tags": [], "rhythm_tags": []}
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
        incoming_summaries = self.normalize_text_list(
            [str(x).strip() for x in (analysis_payload.get("chapter_summaries") or []) if str(x).strip()],
            20,
        )
        summary = self.clean_text(str(analysis_payload.get("chapter_summary") or chapter_title or ""))
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
        global_constraints = merged.get("global_constraints") if isinstance(merged.get("global_constraints"), dict) else {}
        if not global_constraints:
            global_constraints = self._build_global_constraints(merged)
        merged["global_constraints"] = {
            "main_plot": self.clean_text(str(global_constraints.get("main_plot") or "")),
            "hidden_plot": self.clean_text(str(global_constraints.get("hidden_plot") or "")),
            "core_selling_points": self.normalize_text_list([str(x) for x in (global_constraints.get("core_selling_points") or [])], 12),
            "protagonist_core_traits": self.normalize_text_list([str(x) for x in (global_constraints.get("protagonist_core_traits") or [])], 12),
            "must_keep_threads": self.normalize_text_list([str(x) for x in (global_constraints.get("must_keep_threads") or [])], 20),
            "genre_guardrails": self.normalize_text_list([str(x) for x in (global_constraints.get("genre_guardrails") or [])], 12),
        }
        style_requirements = merged.get("style_requirements") if isinstance(merged.get("style_requirements"), dict) else {}
        if not style_requirements:
            style_requirements = self._build_style_requirements(merged.get("style_profile") or {})
        merged["style_requirements"] = {
            "author_voice_keywords": self.normalize_text_list([str(x) for x in (style_requirements.get("author_voice_keywords") or [])], 12),
            "avoid_patterns": self.normalize_text_list([str(x) for x in (style_requirements.get("avoid_patterns") or [])], 12),
            "preferred_rhythm": self.clean_text(str(style_requirements.get("preferred_rhythm") or "")),
            "narrative_distance": self.clean_text(str(style_requirements.get("narrative_distance") or "")),
            "dialogue_density": self.clean_text(str(style_requirements.get("dialogue_density") or "")),
        }
        if chapter_number > 0:
            analysis_memory = {
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "chapter_title": self.clean_text(chapter_title),
                "summary": summary,
                "events": self.normalize_text_list([str(x) for x in incoming_summaries], 12),
                "plot_role": self.clean_text(str(analysis_payload.get("plot_role") or "推进主线")),
                "conflict": self.clean_text(str(analysis_payload.get("conflict") or "")),
                "foreshadowing": self.normalize_text_list([str(x) for x in (analysis_payload.get("foreshadowing") or [])], 12),
                "hook": self.clean_text(str(analysis_payload.get("hook") or "")),
                "problems": self.normalize_text_list([str(x) for x in (analysis_payload.get("problems") or [])], 12),
            }
            continuation_memory = {
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "chapter_title": self.clean_text(chapter_title),
                "scene_summary": summary,
                "scene_state": {"time": "", "location": "", "environment": ""},
                "protagonist_state": {"name": "", "physical_state": "", "emotion_state": "", "current_goal": "", "internal_tension": ""},
                "active_characters": [],
                "active_conflicts": self.normalize_text_list([str(x) for x in (current_state.get("recent_conflicts") or [])], 12),
                "immediate_threads": self.normalize_text_list([str(x) for x in incoming_summaries], 8),
                "long_term_threads": self.normalize_text_list([str(x) for x in (merged.get("chapter_summaries") or [])[-8:]], 8),
                "recent_reveals": self.normalize_text_list([str(x) for x in (analysis_payload.get("reveals") or [])], 8),
                "must_continue_points": self.normalize_text_list([str(x) for x in incoming_summaries], 8),
                "forbidden_jumps": self.normalize_text_list([str(x) for x in (analysis_payload.get("forbidden_jumps") or [])], 8),
                "tone_and_pacing": {"tone": "、".join(style.get("tone_tags") or []), "pace": "、".join(style.get("rhythm_tags") or [])},
                "last_hook": self.clean_text(str(analysis_payload.get("hook") or current_state.get("next_writing_focus") or "")),
            }
            merged["chapter_analysis_memories"] = [
                *(merged.get("chapter_analysis_memories") or []),
                analysis_memory,
            ][-300:]
            merged["chapter_continuation_memories"] = [
                *(merged.get("chapter_continuation_memories") or []),
                continuation_memory,
            ][-300:]
        return merged
