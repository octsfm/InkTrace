import asyncio
import math
import time
from typing import Any, Dict, Optional
import hashlib
import logging
import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from application.agent_mvp import AnalysisTool, NovelMemory, TaskContext
from application.agent_mvp.memory import merge_memory
from application.dto.request_dto import ImportNovelRequest
from application.dto.response_dto import PlotAnalysisResponse, StyleAnalysisResponse
from application.services.content_service import ContentService
from application.services.logging_service import build_log_context
from application.services.project_service import ProjectService
from application.services.runtime_metrics_service import (
    record_batch_resume,
    record_budget_block,
    record_token_limit_error,
    reset_budget_block_streak,
)
from application.services.v2_workflow_service import V2WorkflowService
from domain.entities.organize_job import OrganizeJob
from domain.exceptions import APIKeyError, LLMClientError, NetworkError, RateLimitError, TokenLimitError
from domain.repositories.organize_job_repository import IOrganizeJobRepository
from domain.types import NovelId, OrganizeJobStatus
from presentation.api.dependencies import (
    get_capacity_planner_service,
    get_content_service,
    get_llm_factory,
    get_organize_job_repo,
    get_project_service,
    get_token_budget_manager,
    get_txt_parser,
    get_v2_workflow_service,
)


router = APIRouter(prefix="/api/content", tags=["content"])
logger = logging.getLogger(__name__)
PROGRESS_CACHE: Dict[str, Dict[str, Any]] = {}
ACTIVE_ORGANIZE_TASKS: Dict[str, asyncio.Task] = {}
ORGANIZE_LOCKS: Dict[str, asyncio.Lock] = {}


def _new_organize_task_id(novel_id: str) -> str:
    return f"organize-{novel_id}-{int(time.time() * 1000)}"


class OrganizePauseRequested(Exception):
    pass


class OrganizeCancelRequested(Exception):
    pass


def _error_detail(code: str, message: str, user_message: str) -> Dict[str, Any]:
    return {"code": code, "message": message, "user_message": user_message}


def _to_dict(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model)


def _make_source_hash(novel_text: str, outline_context: Dict[str, Any]) -> str:
    outline_text = "|".join(
        [
            str(outline_context.get("premise") or ""),
            str(outline_context.get("story_background") or ""),
            str(outline_context.get("world_setting") or ""),
        ]
    )
    payload = f"{novel_text}\n##outline##\n{outline_text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_progress_payload(
    current: int,
    total: int,
    status: str,
    message: str,
    stage: str = "idle",
    current_chapter_title: str = "",
    resumable: bool = False,
    source_hash: str = "",
    last_error: str = "",
    task_id: str = "",
    strategy: str = "",
    batch_no: int = 0,
    batch_total: int = 0,
    chunked_chapter_count: int = 0,
) -> Dict[str, Any]:
    percent = 0 if total <= 0 else int(current / total * 100)
    return {
        "current": current,
        "total": total,
        "percent": percent,
        "status": status,
        "stage": stage,
        "message": message,
        "current_chapter_title": current_chapter_title,
        "resumable": resumable,
        "source_hash": source_hash,
        "last_error": last_error,
        "task_id": task_id,
        "strategy": strategy,
        "batch_no": int(batch_no or 0),
        "batch_total": int(batch_total or 0),
        "chunked_chapter_count": int(chunked_chapter_count or 0),
    }


def _cache_progress(novel_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    PROGRESS_CACHE[novel_id] = payload
    return payload


def _get_lock(novel_id: str) -> asyncio.Lock:
    lock = ORGANIZE_LOCKS.get(novel_id)
    if lock is None:
        lock = asyncio.Lock()
        ORGANIZE_LOCKS[novel_id] = lock
    return lock


def _get_active_task(novel_id: str) -> Optional[asyncio.Task]:
    task = ACTIVE_ORGANIZE_TASKS.get(novel_id)
    if task and task.done():
        ACTIVE_ORGANIZE_TASKS.pop(novel_id, None)
        return None
    return task


def _running_progress(
    novel_id: str,
    message: str,
    stage: str = "prepare",
    current: int = 0,
    total: int = 0,
    current_chapter_title: str = "",
    task_id: str = "",
    strategy: str = "",
) -> Dict[str, Any]:
    return _cache_progress(
        novel_id,
        {
            **_build_progress_payload(
                current=current,
                total=total,
                status=OrganizeJobStatus.RUNNING.value,
                message=message,
                stage=stage,
                current_chapter_title=current_chapter_title,
                resumable=False,
                task_id=task_id,
                strategy=strategy,
            ),
            "started_ts": int(time.time()),
        },
    )


def _paused_progress(
    novel_id: str,
    message: str = "整理任务已暂停，可继续整理",
    current: int = 0,
    total: int = 0,
    current_chapter_title: str = "",
    task_id: str = "",
    strategy: str = "",
) -> Dict[str, Any]:
    return _cache_progress(
        novel_id,
        _build_progress_payload(
            current=current,
            total=total,
            status=OrganizeJobStatus.PAUSED.value,
            message=message,
            stage="paused",
            current_chapter_title=current_chapter_title,
            resumable=True,
            task_id=task_id,
            strategy=strategy,
        ),
    )


def _cancelled_progress(
    novel_id: str,
    message: str = "整理任务已取消",
    current: int = 0,
    total: int = 0,
    current_chapter_title: str = "",
    task_id: str = "",
    strategy: str = "",
) -> Dict[str, Any]:
    return _cache_progress(
        novel_id,
        _build_progress_payload(
            current=current,
            total=total,
            status=OrganizeJobStatus.CANCELLED.value,
            message=message,
            stage="cancelled",
            current_chapter_title=current_chapter_title,
            resumable=False,
            task_id=task_id,
            strategy=strategy,
        ),
    )


def _is_not_found_error(message: str) -> bool:
    lowered = message.lower()
    novel_missing = "\u5c0f\u8bf4\u4e0d\u5b58\u5728"
    project_missing = "\u9879\u76ee\u4e0d\u5b58\u5728"
    return "not found" in lowered or novel_missing in message or project_missing in message


def _job_to_progress(job: Optional[OrganizeJob]) -> Dict[str, Any]:
    if not job:
        return _build_progress_payload(0, 0, OrganizeJobStatus.IDLE.value, "尚未开始整理", stage="idle")
    checkpoint = job.checkpoint_memory if isinstance(job.checkpoint_memory, dict) else {}
    persisted_progress = checkpoint.get("progress") if isinstance(checkpoint.get("progress"), dict) else {}
    stage = str(job.stage or persisted_progress.get("stage") or "idle")
    chapter_title = str(job.current_chapter_title or persisted_progress.get("current_chapter_title") or "")
    if job.status == OrganizeJobStatus.DONE:
        message = job.message or f"整理完成（{job.total_chapters}/{job.total_chapters}）"
        stage = "done"
    elif job.status == OrganizeJobStatus.ERROR:
        message = job.message or job.last_error or "整理失败"
        stage = stage or "error"
    elif job.status == OrganizeJobStatus.PAUSED:
        message = job.message or f"已暂停，可从第{job.completed_chapters + 1}章继续整理"
        stage = "paused"
    elif job.status == OrganizeJobStatus.PAUSE_REQUESTED:
        message = job.message or "已请求暂停，正在等待当前安全点"
        stage = "pause_requested"
    elif job.status == OrganizeJobStatus.RESUME_REQUESTED:
        message = job.message or "已请求继续整理"
        stage = "resume_requested"
    elif job.status == OrganizeJobStatus.CANCELLING:
        message = job.message or "正在取消整理任务"
        stage = "cancelling"
    elif job.status == OrganizeJobStatus.CANCELLED:
        message = job.message or "整理任务已取消"
        stage = "cancelled"
    elif job.completed_chapters > 0:
        message = job.message or f"可从第{job.completed_chapters + 1}章继续整理"
    else:
        message = job.message or "整理任务待执行"
    resumable = job.status in {OrganizeJobStatus.RUNNING, OrganizeJobStatus.ERROR, OrganizeJobStatus.PAUSED, OrganizeJobStatus.PAUSE_REQUESTED, OrganizeJobStatus.RESUME_REQUESTED} and job.completed_chapters < max(job.total_chapters, 1)
    return _build_progress_payload(
        current=job.completed_chapters,
        total=job.total_chapters,
        status=job.status.value,
        message=message,
        stage=stage,
        current_chapter_title=chapter_title,
        resumable=resumable,
        source_hash=job.source_hash,
        last_error=job.last_error,
        task_id=str(checkpoint.get("task_id") or ""),
        strategy=str(persisted_progress.get("strategy") or ""),
        batch_no=int(persisted_progress.get("batch_no") or 0),
        batch_total=int(persisted_progress.get("batch_total") or 0),
        chunked_chapter_count=int(persisted_progress.get("chunked_chapter_count") or 0),
    )


def _requested_control(job: Optional[OrganizeJob]) -> str:
    if not job:
        return ""
    if job.status == OrganizeJobStatus.PAUSE_REQUESTED:
        return "pause"
    if job.status == OrganizeJobStatus.CANCELLING:
        return "cancel"
    return ""


def _has_live_organize_task(novel_id: str) -> bool:
    return _get_active_task(novel_id) is not None


def _is_transient_organize_status(status: OrganizeJobStatus) -> bool:
    return status in {
        OrganizeJobStatus.RUNNING,
        OrganizeJobStatus.PAUSE_REQUESTED,
        OrganizeJobStatus.RESUME_REQUESTED,
        OrganizeJobStatus.CANCELLING,
    }


def _normalize_organize_mode(mode: str, force_rebuild: bool) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized in {"", "chapter_first"}:
        return "full_reanalyze" if force_rebuild else "rebuild_global"
    if normalized in {"full", "full_rebuild", "full_reanalyze"}:
        return "full_reanalyze"
    if normalized in {"global", "rebuild", "rebuild_global"}:
        return "rebuild_global"
    if normalized in {"refresh", "refresh_view", "view"}:
        return "refresh_view"
    return "full_reanalyze" if force_rebuild else "rebuild_global"


def _organize_mode_from_job(job: Optional[OrganizeJob]) -> str:
    checkpoint = job.checkpoint_memory if job and isinstance(job.checkpoint_memory, dict) else {}
    organize_meta = checkpoint.get("organize_meta") if isinstance(checkpoint.get("organize_meta"), dict) else {}
    return str(organize_meta.get("mode") or "")


def _build_capacity_plan(mode: str, llm_factory, capacity_planner_service, token_budget_manager) -> Dict[str, Any]:
    ff_budget_v2 = str(os.environ.get("FF_TOKEN_BUDGET_V2", "1")).strip() not in {"0", "false", "False"}
    if str(mode or "").strip().lower() != "full_reanalyze":
        base_plan = {
            "strategy": "reuse_artifact_first",
            "enable_chunking": False,
            "batch_size_chapters": 12,
            "chapter_soft_limit_chars": 30000,
            "chunk_size_chars": 9000,
            "need_outline_digest": True,
            "chunked_chapter_count": 0,
            "stage_cap_tokens": {"global_analysis": 3200},
            "budget_tokens": 3200,
            "reserve_tokens": 800,
        }
        return base_plan
    kimi_client_getter = getattr(llm_factory, "get_client_for_provider", None)
    kimi_client = kimi_client_getter("kimi") if callable(kimi_client_getter) else getattr(llm_factory, "kimi_client", None)
    if not kimi_client:
        return token_budget_manager.build_capacity_plan("", 8000)

    model_name = str(getattr(kimi_client, "model_name", "") or getattr(getattr(llm_factory, "config", None), "kimi_model", "") or "")
    max_context_tokens = int(getattr(kimi_client, "max_context_tokens", 0) or 0)
    if not ff_budget_v2:
        return capacity_planner_service.build_plan(model_name, max_context_tokens)
    # 新预算服务为主，保留旧字段兼容既有流程。
    plan = token_budget_manager.build_capacity_plan(model_name, max_context_tokens)
    legacy_plan = capacity_planner_service.build_plan(model_name, max_context_tokens)
    plan.update({k: v for k, v in (legacy_plan or {}).items() if k not in plan})
    if str((legacy_plan or {}).get("strategy") or "").strip():
        plan["strategy"] = str(legacy_plan.get("strategy"))
    return plan


def _validate_organize_model_capacity(
    *,
    novel_id: str,
    organize_mode: str,
    content_service: ContentService,
    token_budget_manager,
    capacity_plan: Dict[str, Any],
) -> None:
    if str(organize_mode or "").strip().lower() not in {"full_reanalyze", "rebuild_global"}:
        return
    outline_context = _safe_get_outline_context(content_service, novel_id)
    novel_text = content_service.get_novel_text(novel_id)
    total_chars = len(str(novel_text or ""))
    chapter_soft_limit = max(6000, int((capacity_plan or {}).get("chapter_soft_limit_chars") or 12000))
    estimated_chapters = max(1, int(math.ceil(total_chars / max(1, chapter_soft_limit * 0.75))))
    batch_size = max(1, int((capacity_plan or {}).get("batch_size_chapters") or (capacity_plan or {}).get("batch_size") or 8))
    estimated_batches = max(1, int(math.ceil(estimated_chapters / batch_size)))

    digest_payload = {
        "outline_digest": outline_context.get("outline_digest") if isinstance(outline_context, dict) else {},
        "estimated_batches": estimated_batches,
        "estimated_chapters": estimated_chapters,
        "mode": organize_mode,
    }
    estimated_tokens = int(token_budget_manager.estimate_stage_tokens(digest_payload))
    estimated_tokens += estimated_batches * 180
    estimated_tokens += min(1800, estimated_chapters * 12)
    stage_caps = (capacity_plan or {}).get("stage_cap_tokens") or {}
    budget_tokens = int(stage_caps.get("global_analysis") or (capacity_plan or {}).get("budget_tokens") or 0)
    if budget_tokens > 0 and estimated_tokens <= budget_tokens:
        reset_budget_block_streak()
        return

    suggested_batch = max(2, batch_size // 2)
    record_budget_block()
    detail = _error_detail(
        "ORGANIZE_BUDGET_BLOCK",
        "全局分析阶段预算不足",
        "当前模型预算不足以完成全局分析，请调整模型或批次策略后重试。",
    )
    detail.update(
        {
            "stage": "global_analysis",
            "model_name": str((capacity_plan or {}).get("model_name") or ""),
            "estimated_tokens": estimated_tokens,
            "budget_tokens": budget_tokens,
            "input_units": {"chars": total_chars, "estimated_chapters": estimated_chapters, "estimated_batches": estimated_batches},
            "suggestion": {
                "suggested_model": str((capacity_plan or {}).get("suggested_model") or "moonshot-v1-32k"),
                "suggested_batch_size": suggested_batch,
                "continue_strategies": list((capacity_plan or {}).get("suggested_continue_strategy") or ["reduce_batch_size", "raise_digest_abstraction", "enable_two_level_summary"]),
            },
        }
    )
    raise HTTPException(status_code=409, detail=detail)


def _humanize_organize_error(error: Exception) -> str:
    raw_message = str(error or "").strip()
    lowered = raw_message.lower()

    if isinstance(error, APIKeyError) or "api密钥" in raw_message or "api key" in lowered or "unauthorized" in lowered or "401" in lowered:
        if "kimi" in lowered:
            return "Kimi API Key 无效或未配置，请在模型配置页更新后重新整理。"
        if "deepseek" in lowered:
            return "DeepSeek API Key 无效或未配置，请在模型配置页更新后重新整理。"
        return "模型 API Key 无效或未配置，请在模型配置页更新后重新整理。"

    if isinstance(error, RateLimitError) or "限流" in raw_message or "rate limit" in lowered or "429" in lowered:
        retry_after = getattr(error, "retry_after", None)
        retry_hint = f"{int(retry_after)}秒后" if isinstance(retry_after, int) and retry_after > 0 else "稍后"
        if "kimi" in lowered:
            return f"Kimi 触发限流，系统已自动退避重试但仍未恢复。请在{retry_hint}点击“继续整理/重试整理”，或切换模型后再试。"
        if "deepseek" in lowered:
            return f"DeepSeek 触发限流，系统已自动退避重试但仍未恢复。请在{retry_hint}点击“继续整理/重试整理”，或切换模型后再试。"
        return f"模型调用触发限流，系统已自动退避重试但仍未恢复。请在{retry_hint}点击“继续整理/重试整理”，或切换模型后再试。"

    if isinstance(error, TokenLimitError) or "token" in lowered:
        record_token_limit_error()
        return "整理内容过长，已超过模型上下文限制，请拆分内容或调整后重试。"

    if isinstance(error, NetworkError) or "超时" in raw_message or "network" in lowered or "timeout" in lowered:
        return "模型连接失败，整理已停止，请检查网络或稍后重试。"

    if isinstance(error, LLMClientError):
        return raw_message or "模型调用失败，整理已停止，请检查模型配置后重试。"

    return raw_message or "整理失败，请稍后重试。"


def _ensure_rebuild_mode_ready(
    novel_id: str,
    organize_mode: str,
    project_service: ProjectService,
    v2_service: V2WorkflowService,
) -> None:
    if str(organize_mode or "").strip().lower() != "rebuild_global":
        return
    project = project_service.ensure_project_for_novel(NovelId(novel_id))
    can_rebuild = bool(getattr(v2_service, "can_rebuild_global", lambda _pid: False)(project.id.value))
    if can_rebuild:
        return
    message = "当前项目没有可复用章节分析结果，无法执行 rebuild_global。请先执行一次 full_reanalyze 完整整理。"
    raise HTTPException(
        status_code=409,
        detail=_error_detail(
            "REBUILD_BASELINE_MISSING",
            message,
            "请先执行完整整理（full_reanalyze）后再使用增量重建。",
        ),
    )


async def _run_v2_organize_task(
    novel_id: str,
    mode: str,
    force_rebuild: bool,
    project_service: ProjectService,
    organize_job_repo: IOrganizeJobRepository,
    v2_service: V2WorkflowService,
    task_id: str = "",
    capacity_plan: Optional[Dict[str, Any]] = None,
) -> None:
    novel_vo = NovelId(novel_id)
    job = organize_job_repo.find_by_novel_id(novel_vo) or OrganizeJob(novel_id=novel_vo)
    was_resume = False

    def _raise_if_control_requested() -> None:
        latest = organize_job_repo.find_by_novel_id(novel_vo) or job
        action = _requested_control(latest)
        if action == "pause":
            raise OrganizePauseRequested()
        if action == "cancel":
            raise OrganizeCancelRequested()

    try:
        project = project_service.ensure_project_for_novel(novel_vo)
        logger.info(
            "整理任务开始",
            extra=build_log_context(event="organize_task_started", novel_id=novel_id, project_id=project.id.value, current=job.completed_chapters, total=job.total_chapters, chapter_title=str(job.current_chapter_title or "")),
        )
        organize_mode = _normalize_organize_mode(mode, force_rebuild)
        if force_rebuild:
            job.reset(source_hash=f"v2:{int(time.time())}", total_chapters=0)
            job.update_checkpoint(0, 0, {})
        resume_from = max(0, int(job.completed_chapters or 0))
        was_resume = resume_from > 0
        checkpoint = job.checkpoint_memory if isinstance(job.checkpoint_memory, dict) else {}
        checkpoint_memory = checkpoint.get("memory") if isinstance(checkpoint.get("memory"), dict) else {}
        organize_job_repo.save(job)
        _running_progress(
            novel_id,
            f"准备整理（{resume_from}/{int(job.total_chapters or 0)}）",
            stage="prepare",
            current=resume_from,
            total=int(job.total_chapters or 0),
            task_id=task_id,
            strategy=str((capacity_plan or {}).get("strategy") or ""),
        )
        async def _on_progress(progress: Dict[str, Any]) -> None:
            latest = organize_job_repo.find_by_novel_id(novel_vo) or job
            if latest.status == OrganizeJobStatus.CANCELLING:
                job.mark_cancelling()
                organize_job_repo.save(job)
                raise OrganizeCancelRequested()
            if latest.status == OrganizeJobStatus.PAUSE_REQUESTED:
                job.mark_pause_requested()
                organize_job_repo.save(job)
                raise OrganizePauseRequested()
            job.apply_progress(progress)
            snapshot = progress.get("memory_snapshot") if isinstance(progress.get("memory_snapshot"), dict) else checkpoint_memory
            job.checkpoint_memory = {
                "memory": snapshot or {},
                "progress": {**{k: v for k, v in progress.items() if k != "memory_snapshot"}, "task_id": task_id},
                "organize_meta": {"mode": organize_mode},
                "task_id": task_id,
            }
            organize_job_repo.save(job)
            _cache_progress(novel_id, {**{k: v for k, v in progress.items() if k != "memory_snapshot"}, "task_id": task_id})
            _raise_if_control_requested()
        await v2_service.organize_project(
            project.id.value,
            organize_mode,
            force_rebuild,
            progress_callback=_on_progress,
            resume_from=resume_from,
            checkpoint_memory=checkpoint_memory,
            capacity_plan=capacity_plan,
        )
        memory = v2_service.get_memory(project.id.value) or {}
        final_progress = _build_progress_payload(
            current=job.total_chapters,
            total=job.total_chapters,
            status=OrganizeJobStatus.DONE.value,
            stage="done",
            message=f"整理完成（{job.total_chapters}/{job.total_chapters}）",
            current_chapter_title="",
            resumable=False,
            task_id=task_id,
            strategy=str((capacity_plan or {}).get("strategy") or ""),
        )
        job.update_checkpoint(
            job.total_chapters,
            job.total_chapters,
            {"memory": memory, "progress": final_progress, "organize_meta": {"mode": organize_mode}, "task_id": task_id},
        )
        job.mark_done()
        organize_job_repo.save(job)
        _cache_progress(novel_id, final_progress)
        logger.info(
            "整理任务完成",
            extra=build_log_context(event="organize_task_done", novel_id=novel_id, project_id=project.id.value, current=job.total_chapters, total=job.total_chapters, chapter_title=""),
        )
    except OrganizePauseRequested:
        latest = organize_job_repo.find_by_novel_id(novel_vo) or job
        job.completed_chapters = int(latest.completed_chapters or job.completed_chapters or 0)
        job.total_chapters = int(latest.total_chapters or job.total_chapters or 0)
        job.current_chapter_title = str((PROGRESS_CACHE.get(novel_id) or {}).get("current_chapter_title") or latest.current_chapter_title or "")
        job.mark_paused()
        organize_job_repo.save(job)
        _paused_progress(
            novel_id,
            "整理任务已暂停，可继续整理",
            current=job.completed_chapters,
            total=job.total_chapters,
            current_chapter_title=job.current_chapter_title,
            task_id=task_id,
            strategy=str((capacity_plan or {}).get("strategy") or ""),
        )
        logger.info(
            "整理任务已暂停",
            extra=build_log_context(event="organize_task_paused", novel_id=novel_id, project_id=project.id.value if 'project' in locals() else "", current=job.completed_chapters, total=job.total_chapters, chapter_title=str(job.current_chapter_title or "")),
        )
    except OrganizeCancelRequested:
        if was_resume:
            record_batch_resume(False)
        latest = organize_job_repo.find_by_novel_id(novel_vo) or job
        job.completed_chapters = int(latest.completed_chapters or job.completed_chapters or 0)
        job.total_chapters = int(latest.total_chapters or job.total_chapters or 0)
        job.current_chapter_title = str((PROGRESS_CACHE.get(novel_id) or {}).get("current_chapter_title") or latest.current_chapter_title or "")
        job.mark_cancelled()
        organize_job_repo.save(job)
        _cancelled_progress(
            novel_id,
            "整理任务已取消",
            current=job.completed_chapters,
            total=job.total_chapters,
            current_chapter_title=job.current_chapter_title,
            task_id=task_id,
            strategy=str((capacity_plan or {}).get("strategy") or ""),
        )
        logger.info(
            "整理任务已取消",
            extra=build_log_context(event="organize_task_cancelled", novel_id=novel_id, project_id=project.id.value if 'project' in locals() else "", current=job.completed_chapters, total=job.total_chapters, chapter_title=str(job.current_chapter_title or "")),
        )
    except asyncio.CancelledError:
        job.mark_paused("整理任务已暂停，可继续整理")
        organize_job_repo.save(job)
        _paused_progress(
            novel_id,
            "整理任务已暂停，可继续整理",
            current=job.completed_chapters,
            total=job.total_chapters,
            current_chapter_title=str((PROGRESS_CACHE.get(novel_id) or {}).get("current_chapter_title") or ""),
            task_id=task_id,
            strategy=str((capacity_plan or {}).get("strategy") or ""),
        )
        raise
    except Exception as e:
        if was_resume:
            record_batch_resume(False)
        message = _humanize_organize_error(e)
        job.mark_error(message)
        organize_job_repo.save(job)
        _cache_progress(
            novel_id,
            _build_progress_payload(
                current=job.completed_chunks,
                total=job.total_chapters,
                status=OrganizeJobStatus.ERROR.value,
                stage="error",
                message=message or "整理失败",
                resumable=True,
                last_error=message,
                task_id=task_id,
            ),
        )
        logger.error(
            "整理任务失败",
            extra=build_log_context(event="organize_task_error", novel_id=novel_id, project_id=project.id.value if 'project' in locals() else "", current=job.completed_chapters, total=job.total_chapters, chapter_title=str(job.current_chapter_title or ""), last_error=message, raw_error=str(e)),
        )
    finally:
        current = ACTIVE_ORGANIZE_TASKS.get(novel_id)
        if current and current.done():
            ACTIVE_ORGANIZE_TASKS.pop(novel_id, None)


def _apply_outline_context(memory: Dict[str, Any], outline_context: Dict[str, Any]) -> Dict[str, Any]:
    if not outline_context:
        return memory
    premise = str(outline_context.get("premise") or "").strip()
    story_background = str(outline_context.get("story_background") or "").strip()
    world_setting = str(outline_context.get("world_setting") or "").strip()
    if premise:
        plot_outline = str(memory.get("plot_outline") or "").strip()
        memory["plot_outline"] = " | ".join([part for part in [premise, plot_outline] if part])
    outline_world_parts = [part for part in [world_setting, story_background] if part]
    if outline_world_parts:
        world_text = str(memory.get("world_settings") or "").strip()
        memory["world_settings"] = " | ".join(
            [part for part in [*outline_world_parts, world_text] if part]
        )
    return memory


def _safe_get_outline_context(content_service: ContentService, novel_id: str) -> Dict[str, Any]:
    getter = getattr(content_service, "get_outline_context", None)
    if not callable(getter):
        return {}
    outline_context = getter(novel_id)
    return outline_context if isinstance(outline_context, dict) else {}


async def _analyze_and_bind_memory(
    novel_id: str,
    content_service: ContentService,
    project_service: ProjectService,
    organize_job_repo: IOrganizeJobRepository,
    llm_factory,
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    logger.info("[Structure] start novel_id=%s force_rebuild=%s", novel_id, force_rebuild)
    novel_id_vo = NovelId(novel_id)
    project = project_service.ensure_project_for_novel(novel_id_vo)
    novel_text = content_service.get_novel_text(novel_id)
    outline_context = _safe_get_outline_context(content_service, novel_id)
    source_hash = _make_source_hash(novel_text, outline_context)

    job = organize_job_repo.find_by_novel_id(novel_id_vo) or OrganizeJob(novel_id=novel_id_vo)
    if force_rebuild or job.source_hash != source_hash:
        job.reset(source_hash)
        organize_job_repo.save(job)
    elif job.status == OrganizeJobStatus.DONE and isinstance(job.checkpoint_memory, dict) and any(job.checkpoint_memory.values()):
        _cache_progress(novel_id, _job_to_progress(job))
        return {"project_id": project.id.value, "memory": job.checkpoint_memory}

    if not novel_text.strip():
        empty_memory = NovelMemory().to_agent_context()
        project_service.bind_memory_to_novel(novel_id_vo, empty_memory)
        job.reset(source_hash, 0)
        job.checkpoint_memory = empty_memory
        job.mark_done()
        organize_job_repo.save(job)
        _cache_progress(novel_id, _job_to_progress(job))
        return {"project_id": project.id.value, "memory": empty_memory}

    kimi_client_getter = getattr(llm_factory, "get_client_for_provider", None)
    kimi_client = kimi_client_getter("kimi") if callable(kimi_client_getter) else getattr(llm_factory, "kimi_client", None)
    analyzer = AnalysisTool(
        kimi_client,
        getattr(llm_factory, "get_fallback_client_for_provider", lambda _provider: None)("kimi"),
    )
    structure = await analyzer.execute_async(
        TaskContext(novel_id=novel_id, goal="organize_structure"),
        {"mode": "structure_mode", "novel_text": novel_text},
    )
    if structure.status != "success":
        message = "Failed to split source text into chapters"
        job.mark_error(message)
        organize_job_repo.save(job)
        _cache_progress(novel_id, _job_to_progress(job))
        raise ValueError(message)

    chapters = structure.payload.get("chapters") or []
    if not chapters:
        message = "No analyzable chapters were found"
        job.mark_error(message)
        organize_job_repo.save(job)
        _cache_progress(novel_id, _job_to_progress(job))
        raise ValueError(message)

    total_chapters = len(chapters)
    resume_from = 0 if force_rebuild else min(int(job.completed_chapters or 0), total_chapters)
    merged_memory: Dict[str, Any] = {}
    if resume_from > 0 and isinstance(job.checkpoint_memory, dict):
        merged_memory = job.checkpoint_memory
    job.total_chapters = total_chapters
    job.mark_running()
    organize_job_repo.save(job)
    _cache_progress(
        novel_id,
        _build_progress_payload(
            current=resume_from,
            total=total_chapters,
            status=OrganizeJobStatus.RUNNING.value,
            message=f"Analyzing chapters {resume_from}/{total_chapters}",
            resumable=resume_from > 0,
            source_hash=source_hash,
        ),
    )

    for idx, chapter in enumerate(chapters[resume_from:], resume_from + 1):
        chapter_title = chapter.get("title") or chapter.get("index")
        incremental = await analyzer.execute_async(
            TaskContext(novel_id=novel_id, goal="organize_incremental"),
            {"mode": "incremental_mode", "chapter": chapter},
        )
        if incremental.status != "success":
            message = f"Chapter analysis failed at {chapter_title}"
            job.mark_error(message)
            organize_job_repo.save(job)
            _cache_progress(novel_id, _job_to_progress(job))
            raise ValueError(message)
        merged_memory = merge_memory(merged_memory, incremental.payload)
        job.update_checkpoint(idx, total_chapters, merged_memory)
        job.mark_running()
        organize_job_repo.save(job)
        _cache_progress(
            novel_id,
            _build_progress_payload(
                current=idx,
                total=total_chapters,
                status=OrganizeJobStatus.RUNNING.value,
                message=f"Analyzing chapters {idx}/{total_chapters}",
                resumable=idx < total_chapters,
                source_hash=source_hash,
            ),
        )

    consolidate = await analyzer.execute_async(
        TaskContext(novel_id=novel_id, goal="organize_consolidate"),
        {"mode": "consolidate_mode", "memory": merged_memory},
    )
    if consolidate.status != "success":
        message = "Failed to consolidate analyzed chapters"
        job.mark_error(message)
        organize_job_repo.save(job)
        _cache_progress(novel_id, _job_to_progress(job))
        raise ValueError(message)

    merged_memory = merge_memory(merged_memory, consolidate.payload)
    merged_memory = _apply_outline_context(merged_memory, outline_context)
    progress_text = str(merged_memory.get("current_progress") or "").strip()
    final_summary = f"Organize complete: analyzed {total_chapters} chapters"
    merged_memory["current_progress"] = (
        f"{progress_text} | {final_summary}" if progress_text and final_summary not in progress_text else (final_summary or progress_text)
    )
    project_service.bind_memory_to_novel(novel_id_vo, merged_memory)
    job.update_checkpoint(total_chapters, total_chapters, merged_memory)
    job.mark_done()
    organize_job_repo.save(job)
    _cache_progress(novel_id, _job_to_progress(job))
    return {"project_id": project.id.value, "memory": merged_memory}


@router.post("/import")
async def import_novel(
    request: ImportNovelRequest,
    service: ContentService = Depends(get_content_service),
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        novel = service.import_novel(request)
        project = project_service.ensure_project_for_novel(NovelId(request.novel_id))
        memory_view = {}
        analysis_status = "queued"
        analysis_error = ""
        try:
            organize_result = await v2_service.organize_project(project.id.value, "full_reanalyze", True)
            memory_view = organize_result.get("memory_view") or {}
            analysis_status = "done"
        except Exception as organize_exc:
            analysis_status = "failed"
            analysis_error = _humanize_organize_error(organize_exc)
            logger.warning("[Import] organize failed after import novel_id=%s err=%s", request.novel_id, analysis_error)
        return {
            "novel": _to_dict(novel),
            "project_id": project.id.value,
            "memory": v2_service.get_memory(project.id.value),
            "memory_view": memory_view,
            "analysis_status": analysis_status,
            "analysis_error": analysis_error,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail=_error_detail(
                "IMPORT_ENCODING_INVALID",
                "TXT encoding decode failed",
                "File encoding is not supported. Please use UTF-8 or GB18030.",
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("IMPORT_INTERNAL_ERROR", str(e), "Import failed, please try again later."),
        )


@router.post("/import/preview")
async def preview_import_structure(
    payload: Dict[str, Any],
    parser=Depends(get_txt_parser),
):
    file_path = str(payload.get("file_path") or "").strip()
    if not file_path:
        raise HTTPException(status_code=400, detail="缺少 file_path")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    parsed = parser.parse_novel_file(file_path)
    chapters = parsed.get("chapters") or []
    return {
        "chapter_count": len(chapters),
        "chapters": [
            {
                "number": int(item.get("number") or index),
                "title": str(item.get("title") or f"第{index}章"),
                "content": str(item.get("content") or ""),
            }
            for index, item in enumerate(chapters, 1)
        ],
    }


@router.post("/import/upload")
async def import_novel_upload(
    novel_id: str = Form(...),
    novel_file: UploadFile = File(...),
    outline_file: Optional[UploadFile] = File(default=None),
    service: ContentService = Depends(get_content_service),
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    temp_dir = tempfile.mkdtemp(prefix="inktrace_upload_")
    novel_path = os.path.join(temp_dir, novel_file.filename or "novel.txt")
    outline_path = None
    try:
        with open(novel_path, "wb") as f:
            f.write(await novel_file.read())
        if outline_file is not None:
            outline_path = os.path.join(temp_dir, outline_file.filename or "outline.txt")
            with open(outline_path, "wb") as f:
                f.write(await outline_file.read())

        request = ImportNovelRequest(novel_id=novel_id, file_path=novel_path, outline_path=outline_path)
        novel = service.import_novel(request)
        project = project_service.ensure_project_for_novel(NovelId(novel_id))
        memory_view = {}
        analysis_status = "queued"
        analysis_error = ""
        try:
            organize_result = await v2_service.organize_project(project.id.value, "full_reanalyze", True)
            memory_view = organize_result.get("memory_view") or {}
            analysis_status = "done"
        except Exception as organize_exc:
            analysis_status = "failed"
            analysis_error = _humanize_organize_error(organize_exc)
            logger.warning("[ImportUpload] organize failed after import novel_id=%s err=%s", novel_id, analysis_error)
        return {
            "novel": _to_dict(novel),
            "project_id": project.id.value,
            "memory": v2_service.get_memory(project.id.value),
            "memory_view": memory_view,
            "analysis_status": analysis_status,
            "analysis_error": analysis_error,
            "outline_uploaded": bool(outline_path),
        }
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail=_error_detail(
                "IMPORT_ENCODING_INVALID",
                "TXT encoding decode failed",
                "File encoding is not supported. Please use UTF-8 or GB18030.",
            ),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("IMPORT_INTERNAL_ERROR", str(e), "Import failed, please try again later."),
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/style/{novel_id}", response_model=StyleAnalysisResponse)
async def analyze_style(
    novel_id: str,
    service: ContentService = Depends(get_content_service),
):
    try:
        return service.analyze_style(novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/plot/{novel_id}", response_model=PlotAnalysisResponse)
async def analyze_plot(
    novel_id: str,
    service: ContentService = Depends(get_content_service),
):
    try:
        return service.analyze_plot(novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/memory/{novel_id}")
async def get_memory_by_novel(
    novel_id: str,
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        project = project_service.get_project_by_novel(NovelId(novel_id))
        if not project:
            project = project_service.ensure_project_for_novel(NovelId(novel_id))
        memory = v2_service.get_memory(project.id.value) or {}
        memory_view = v2_service.get_memory_view(project.id.value) or {}
        return {
            "project_id": project.id.value,
            "memory": memory,
            "memory_view": memory_view,
            "compat_mode": True,
            "route": "content_compat_v2",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/organize/{novel_id}")
async def organize_story_structure(
    novel_id: str,
    force_rebuild: bool = Query(False),
    mode: str = Query("full_reanalyze"),
    content_service: ContentService = Depends(get_content_service),
    project_service: ProjectService = Depends(get_project_service),
    llm_factory=Depends(get_llm_factory),
    capacity_planner_service=Depends(get_capacity_planner_service),
    token_budget_manager=Depends(get_token_budget_manager),
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    try:
        organize_mode = _normalize_organize_mode(mode, force_rebuild)
        _ensure_rebuild_mode_ready(novel_id, organize_mode, project_service, v2_service)
        capacity_plan = _build_capacity_plan(organize_mode, llm_factory, capacity_planner_service, token_budget_manager)
        _validate_organize_model_capacity(
            novel_id=novel_id,
            organize_mode=organize_mode,
            content_service=content_service,
            token_budget_manager=token_budget_manager,
            capacity_plan=capacity_plan,
        )
        logger.info("[StructureAPI] request novel_id=%s force_rebuild=%s mode=%s", novel_id, force_rebuild, organize_mode)
        project = project_service.ensure_project_for_novel(NovelId(novel_id))
        async def _on_progress(progress: Dict[str, Any]) -> None:
            _cache_progress(novel_id, {k: v for k, v in progress.items() if k != "memory_snapshot"})
        if getattr(v2_service, "project_service", project_service) is not project_service:
            compat_result = await _analyze_and_bind_memory(
                novel_id,
                content_service,
                project_service,
                organize_job_repo,
                llm_factory,
                force_rebuild=force_rebuild,
            )
            progress = PROGRESS_CACHE.get(novel_id) or _job_to_progress(organize_job_repo.find_by_novel_id(NovelId(novel_id)))
            return {
                "status": "done",
                "project_id": compat_result.get("project_id") or project.id.value,
                "memory": compat_result.get("memory") or {},
                "memory_view": {},
                "progress": progress,
                "metadata": {"task_role": "GLOBAL_ANALYSIS", "routed_model": "kimi", "route": "compat_three_stage"},
            }
        v2_result = await v2_service.organize_project(
            project.id.value,
            organize_mode,
            force_rebuild,
            progress_callback=_on_progress,
            capacity_plan=capacity_plan,
        )
        progress = PROGRESS_CACHE.get(novel_id) or _job_to_progress(organize_job_repo.find_by_novel_id(NovelId(novel_id)))
        if progress.get("status") != OrganizeJobStatus.DONE.value:
            progress = _cache_progress(
                novel_id,
                _build_progress_payload(
                    current=int(progress.get("total") or 0),
                    total=int(progress.get("total") or 0),
                    status=OrganizeJobStatus.DONE.value,
                    stage="done",
                    message=f"整理完成（{int(progress.get('total') or 0)}/{int(progress.get('total') or 0)}）",
                ),
            )
        return {
            "status": "done",
            "project_id": project.id.value,
            "memory": v2_service.get_memory(project.id.value),
            "memory_view": v2_result.get("memory_view") or {},
            "progress": progress,
            "metadata": {"task_role": "GLOBAL_ANALYSIS", "routed_model": "kimi", "route": "v2_organize"},
        }
    except ValueError as e:
        message = _humanize_organize_error(e)
        job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
        if job:
            job.mark_error(message)
            organize_job_repo.save(job)
            _cache_progress(novel_id, _job_to_progress(job))
        else:
            _cache_progress(
                novel_id,
                _build_progress_payload(0, 0, OrganizeJobStatus.ERROR.value, message, last_error=message),
            )
        if _is_not_found_error(message):
            raise HTTPException(
                status_code=404,
                detail=_error_detail("NOVEL_NOT_FOUND", message, "Novel not found, please create or import it first."),
            )
        raise HTTPException(
            status_code=400,
            detail=_error_detail("STRUCTURE_INPUT_INVALID", message, "Story organize failed. Please review the content and try again."),
        )
    except HTTPException:
        raise
    except Exception as e:
        message = _humanize_organize_error(e)
        job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
        if job:
            job.mark_error(message)
            organize_job_repo.save(job)
            _cache_progress(novel_id, _job_to_progress(job))
        else:
            _cache_progress(
                novel_id,
                _build_progress_payload(0, 0, OrganizeJobStatus.ERROR.value, message, last_error=message),
            )
        logger.exception("[StructureAPI] unexpected error novel_id=%s", novel_id)
        raise HTTPException(
            status_code=500,
            detail=_error_detail("STRUCTURE_INTERNAL_ERROR", message, "Story organize failed. Please try again later."),
        )


@router.post("/organize/start/{novel_id}")
async def start_organize_story_structure(
    novel_id: str,
    force_rebuild: bool = Query(False),
    mode: str = Query("full_reanalyze"),
    content_service: ContentService = Depends(get_content_service),
    llm_factory=Depends(get_llm_factory),
    capacity_planner_service=Depends(get_capacity_planner_service),
    token_budget_manager=Depends(get_token_budget_manager),
    project_service: ProjectService = Depends(get_project_service),
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    lock = _get_lock(novel_id)
    async with lock:
        organize_mode = _normalize_organize_mode(mode, force_rebuild)
        capacity_plan = _build_capacity_plan(organize_mode, llm_factory, capacity_planner_service, token_budget_manager)
        _validate_organize_model_capacity(
            novel_id=novel_id,
            organize_mode=organize_mode,
            content_service=content_service,
            token_budget_manager=token_budget_manager,
            capacity_plan=capacity_plan,
        )
        _ensure_rebuild_mode_ready(novel_id, organize_mode, project_service, v2_service)
        running = _get_active_task(novel_id)
        if running:
            job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
            if job and job.status == OrganizeJobStatus.PAUSE_REQUESTED:
                progress = _job_to_progress(job)
                return {"status": OrganizeJobStatus.PAUSE_REQUESTED.value, "progress": progress}
            progress = PROGRESS_CACHE.get(novel_id) or _build_progress_payload(0, 0, OrganizeJobStatus.RUNNING.value, "整理任务运行中", stage="prepare")
            return {"status": "running", "progress": progress}
        existed = organize_job_repo.find_by_novel_id(NovelId(novel_id))
        if force_rebuild and existed:
            organize_job_repo.delete(NovelId(novel_id))
            PROGRESS_CACHE.pop(novel_id, None)
            existed = None
        task_id = _new_organize_task_id(novel_id)
        _running_progress(
            novel_id,
            "整理任务已启动",
            stage="prepare",
            current=int(existed.completed_chunks or 0) if existed else 0,
            total=int(existed.total_chunks or 0) if existed else 0,
            task_id=task_id,
        )
        task = asyncio.create_task(
            _run_v2_organize_task(
                novel_id,
                organize_mode,
                force_rebuild,
                project_service,
                organize_job_repo,
                v2_service,
                task_id=task_id,
                capacity_plan=capacity_plan,
            )
        )
        ACTIVE_ORGANIZE_TASKS[novel_id] = task
        return {"status": "started", "progress": PROGRESS_CACHE[novel_id]}


@router.post("/organize/pause/{novel_id}")
async def pause_organize_story_structure(
    novel_id: str,
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
):
    lock = _get_lock(novel_id)
    async with lock:
        task = _get_active_task(novel_id)
        job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
        if not task or not job:
            progress = _job_to_progress(job)
            return {"status": progress.get("status") or OrganizeJobStatus.IDLE.value, "progress": progress}
        job.mark_pause_requested()
        organize_job_repo.save(job)
        logger.info(
            "整理任务已请求暂停",
            extra=build_log_context(event="organize_task_pause_requested", novel_id=novel_id, project_id="", current=job.completed_chapters, total=job.total_chapters, chapter_title=str(job.current_chapter_title or "")),
        )
        progress = _cache_progress(
            novel_id,
            _build_progress_payload(
            current=int(job.completed_chunks or 0),
            total=int(job.total_chunks or 0),
            status=OrganizeJobStatus.PAUSE_REQUESTED.value,
            stage=OrganizeJobStatus.PAUSE_REQUESTED.value,
            message="已请求暂停，正在等待当前安全点",
            current_chapter_title=str((PROGRESS_CACHE.get(novel_id) or {}).get("current_chapter_title") or ""),
            resumable=True,
            ),
        )
        return {"status": "pause_requested", "progress": progress}


@router.post("/organize/stop/{novel_id}")
async def stop_organize_story_structure(
    novel_id: str,
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
):
    result = await pause_organize_story_structure(novel_id, organize_job_repo)
    result["status"] = "stopped"
    return result


@router.post("/organize/resume/{novel_id}")
async def resume_organize_story_structure(
    novel_id: str,
    mode: str = Query(""),
    content_service: ContentService = Depends(get_content_service),
    llm_factory=Depends(get_llm_factory),
    capacity_planner_service=Depends(get_capacity_planner_service),
    token_budget_manager=Depends(get_token_budget_manager),
    project_service: ProjectService = Depends(get_project_service),
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    lock = _get_lock(novel_id)
    async with lock:
        existed = organize_job_repo.find_by_novel_id(NovelId(novel_id))
        organize_mode = _normalize_organize_mode(mode or _organize_mode_from_job(existed), False)
        capacity_plan = _build_capacity_plan(organize_mode, llm_factory, capacity_planner_service, token_budget_manager)
        _validate_organize_model_capacity(
            novel_id=novel_id,
            organize_mode=organize_mode,
            content_service=content_service,
            token_budget_manager=token_budget_manager,
            capacity_plan=capacity_plan,
        )
        _ensure_rebuild_mode_ready(novel_id, organize_mode, project_service, v2_service)
        running = _get_active_task(novel_id)
        if running:
            progress = PROGRESS_CACHE.get(novel_id) or _build_progress_payload(
                0, 0, OrganizeJobStatus.RUNNING.value, "整理任务运行中", stage="prepare"
            )
            return {"status": "running", "progress": progress}
        if existed:
            existed.mark_resume_requested()
            organize_job_repo.save(existed)
            logger.info(
                "整理任务已请求继续",
                extra=build_log_context(event="organize_task_resumed", novel_id=novel_id, project_id="", current=existed.completed_chapters, total=existed.total_chapters, chapter_title=str(existed.current_chapter_title or "")),
            )
        task_id = _new_organize_task_id(novel_id)
        _running_progress(
            novel_id,
            f"从第{int((existed.completed_chunks or 0) + 1)}章继续整理" if existed and existed.total_chunks else "继续整理任务已启动",
            stage="prepare",
            current=int(existed.completed_chunks or 0) if existed else 0,
            total=int(existed.total_chunks or 0) if existed else 0,
            task_id=task_id,
        )
        task = asyncio.create_task(
            _run_v2_organize_task(
                novel_id,
                organize_mode,
                False,
                project_service,
                organize_job_repo,
                v2_service,
                task_id=task_id,
                capacity_plan=capacity_plan,
            )
        )
        ACTIVE_ORGANIZE_TASKS[novel_id] = task
        return {"status": "resumed", "progress": PROGRESS_CACHE[novel_id]}


@router.post("/organize/cancel/{novel_id}")
async def cancel_organize_story_structure(
    novel_id: str,
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
):
    lock = _get_lock(novel_id)
    async with lock:
        task = _get_active_task(novel_id)
        job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
        if task and job:
            job.mark_cancelling()
            organize_job_repo.save(job)
            logger.info(
                "整理任务已请求取消",
                extra=build_log_context(event="organize_task_cancel_requested", novel_id=novel_id, project_id="", current=job.completed_chapters, total=job.total_chapters, chapter_title=str(job.current_chapter_title or "")),
            )
            progress = _cache_progress(
                novel_id,
                _build_progress_payload(
                    current=int(job.completed_chunks or 0),
                    total=int(job.total_chunks or 0),
                    status=OrganizeJobStatus.CANCELLING.value,
                    stage=OrganizeJobStatus.CANCELLING.value,
                    message="已请求取消，正在等待当前安全点",
                    current_chapter_title=str((PROGRESS_CACHE.get(novel_id) or {}).get("current_chapter_title") or ""),
                    resumable=False,
                ),
            )
            return {"status": "cancelling", "progress": progress}
        if job:
            job.mark_cancelled()
            organize_job_repo.save(job)
        progress = _cancelled_progress(
            novel_id,
            current=int(job.completed_chunks or 0) if job else 0,
            total=int(job.total_chunks or 0) if job else 0,
            current_chapter_title=str((PROGRESS_CACHE.get(novel_id) or {}).get("current_chapter_title") or ""),
        )
        return {"status": "cancelled", "progress": progress}


@router.post("/organize/retry/{novel_id}")
async def retry_organize_story_structure(
    novel_id: str,
    mode: str = Query("full_reanalyze"),
    content_service: ContentService = Depends(get_content_service),
    llm_factory=Depends(get_llm_factory),
    capacity_planner_service=Depends(get_capacity_planner_service),
    token_budget_manager=Depends(get_token_budget_manager),
    project_service: ProjectService = Depends(get_project_service),
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    logger.info(
        "整理任务重新开始",
        extra=build_log_context(event="organize_task_restarted", novel_id=novel_id, project_id="", current=0, total=0, chapter_title=""),
    )
    return await start_organize_story_structure(
        novel_id=novel_id,
        force_rebuild=True,
        mode=mode,
        content_service=content_service,
        llm_factory=llm_factory,
        capacity_planner_service=capacity_planner_service,
        token_budget_manager=token_budget_manager,
        project_service=project_service,
        organize_job_repo=organize_job_repo,
        v2_service=v2_service,
    )


@router.get("/organize/progress/{novel_id}")
async def get_organize_progress(
    novel_id: str,
    organize_job_repo: IOrganizeJobRepository = Depends(get_organize_job_repo),
    project_service: ProjectService = Depends(get_project_service),
    v2_service: V2WorkflowService = Depends(get_v2_workflow_service),
):
    can_rebuild_global = False
    try:
        project = project_service.ensure_project_for_novel(NovelId(novel_id))
        can_rebuild_global = bool(getattr(v2_service, "can_rebuild_global", lambda _pid: False)(project.id.value))
    except Exception:
        can_rebuild_global = False

    job = organize_job_repo.find_by_novel_id(NovelId(novel_id))
    if job and _is_transient_organize_status(job.status) and not _has_live_organize_task(novel_id):
        if job.status == OrganizeJobStatus.CANCELLING:
            job.mark_cancelled()
            organize_job_repo.save(job)
            payload = _cancelled_progress(
                novel_id,
                current=int(job.completed_chunks or 0),
                total=int(job.total_chunks or 0),
                current_chapter_title=str(job.current_chapter_title or ""),
            )
            payload["can_rebuild_global"] = can_rebuild_global
            return payload
        job.mark_paused("整理任务未在运行，可继续整理")
        organize_job_repo.save(job)
        payload = _paused_progress(
            novel_id,
            "整理任务未在运行，可继续整理",
            current=int(job.completed_chunks or 0),
            total=int(job.total_chunks or 0),
            current_chapter_title=str(job.current_chapter_title or ""),
        )
        payload["can_rebuild_global"] = can_rebuild_global
        return payload
    cached = PROGRESS_CACHE.get(novel_id)
    if cached:
        payload = dict(cached)
        payload["can_rebuild_global"] = can_rebuild_global
        return payload
    progress = _job_to_progress(job)
    progress["can_rebuild_global"] = can_rebuild_global
    if job:
        PROGRESS_CACHE[novel_id] = progress
    return progress
