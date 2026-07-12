from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


def trace_id_from_request(request: Request) -> str:
    header_value = request.headers.get("X-Trace-Id", "").strip()
    return header_value or f"trace_{uuid.uuid4().hex[:12]}"


SAFE_MESSAGE_MAP = {
    "caller_type_not_allowed": "当前请求来源不被允许。",
    "caller_type_forbidden": "当前请求来源不被允许。",
    "work_not_found": "未找到对应作品。",
    "chapter_not_found": "未找到对应章节。",
    "candidate_draft_not_found": "未找到候选稿。",
    "candidate_version_not_found": "未找到候选稿版本。",
    "context_pack_not_found": "未找到上下文包。",
    "plot_arc_not_found": "未找到对应剧情轨道。",
    "session_not_found": "未找到对应 Agent 会话。",
    "memory_gate_not_found": "未找到记忆审批门。",
    "memory_suggestion_not_found": "未找到记忆更新建议。",
    "memory_revision_not_found": "未找到记忆修订记录。",
    "memory_revision_apply_blocked": "当前记忆修订无法应用，请先完成审批或处理冲突。",
    "memory_rollback_not_allowed": "当前修订不允许回滚。",
    "trace_not_found": "未找到对应 Trace。",
    "permission_denied": "当前无权查看 Trace 详情。",
    "invalid_request": "当前请求无效。",
    "idempotency_key_required": "缺少幂等键，请刷新后重试。",
    "idempotency_key_conflict": "当前操作已提交，请勿重复执行。",
    "internal_error": "服务暂时不可用，请稍后重试。",
    "P2_CALLER_FORBIDDEN": "当前请求来源不被允许。",
    "P2_USER_ACTION_REQUIRED": "请由你本人点击确认后再试。",
    "P2_IDEMPOTENCY_KEY_REQUIRED": "操作标识缺失，请刷新后重试。",
    "P2_IDEMPOTENCY_CONFLICT": "这次操作与之前的请求不一致，请刷新后再试。",
    "P2_OUTLINE_TARGET_REQUIRED": "请先选择要处理的大纲或章节。",
    "P2_OUTLINE_TARGET_NOT_FOUND": "没有找到这份大纲，请刷新后重试。",
    "P2_OUTLINE_TARGET_CONFLICT": "这份大纲刚刚有改动，请刷新后重新生成建议。",
    "P2_OUTLINE_SUGGESTION_NOT_FOUND": "没有找到这条建议，请重新生成。",
    "P2_OUTLINE_SUGGESTION_NOT_ACCEPTED": "请先选择“先留着”，再放进大纲。",
    "P2_OUTLINE_SUGGESTION_TYPE_UNSUPPORTED": "这条建议不能直接放进大纲。",
    "P2_OUTLINE_APPLY_CONFIRMATION_REQUIRED": "请先查看前后对比并确认，再放进大纲。",
    "P2_OUTLINE_CONFLICT_REVIEW_REQUIRED": "发现需要你处理的冲突，暂未改动大纲。",
    "P2_OUTLINE_CONFLICT_CHECK_FAILED": "安全检查暂时失败，大纲没有改动，请稍后重试。",
    "P2_WRITING_TASK_PREREQUISITE_MISSING": "请先确认本章方向和章节计划，再整理写作要点。",
    "output_schema_invalid": "这次生成的结果格式不完整，请重试。",
    "P2_VECTOR_INVALID_INDEX_SCOPE": "请选择\"整部作品\"或\"指定章节\"。",
    "P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED": "请选择至少一个章节。",
    "P2_VECTOR_TARGET_CHAPTER_IDS_NOT_ALLOWED": "全作品重建不需要选择章节，请取消章节选择后重试。",
    "P2_VECTOR_TOO_MANY_CHAPTERS": "选择的章节数量超过上限，请分批操作。",
    "P2_VECTOR_WORK_NOT_FOUND": "未找到对应作品。",
    "P2_VECTOR_CHAPTER_NOT_FOUND": "未找到对应章节。",
    "P2_VECTOR_CHAPTER_NOT_IN_WORK": "所选章节不属于当前作品，请刷新后重试。",
    "P2_VECTOR_INDEXING_IN_PROGRESS": "这个作品已有索引任务正在运行，请等待完成后再试。",
    "P2_VECTOR_IDEMPOTENCY_CONFLICT": "当前操作已提交，请勿重复执行。",
    "P2_VECTOR_CALLER_FORBIDDEN": "当前请求来源不被允许。",
    "P2_VECTOR_EMBEDDING_UNAVAILABLE": "AI 嵌入服务暂时不可用，请稍后重试或检查 AI 设置。",
    "P2_VECTOR_STORE_UNAVAILABLE": "向量存储服务暂时不可用，请稍后重试。",
    "P2_VECTOR_REINDEX_FAILED": "索引重建失败，可以重试。",
    "multi_chapter_session_not_found": "未找到对应多章续写任务。",
    "invalid_target_chapters": "目标章节数不合法。",
    "not_waiting_user_decision": "当前状态下不能继续下一章。",
    "citation_not_found": "未找到对应引用记录。",
    "P2_CITATION_SOURCE_HASH_MISMATCH": "引用来源内容已变更，请刷新后重试。",
    "P2_CITATION_UNVERIFIED": "当前引用尚未通过校验。",
    "style_profile_not_found": "未找到对应风格画像。",
    "profile_not_confirmable": "当前风格画像状态下无法确认。",
    "profile_not_disableable": "当前风格画像状态下无法禁用。",
    "style_dna_source_text_empty": "请先提供标杆文本。",
    "style_dna_extract_failed": "风格画像提取失败，请稍后重试。",
    "mention_not_found": "未找到对应引用标记。",
    "mention_conflict": "当前章节版本已变更，请刷新后重试。",
    "invalid_mention_range": "引用位置无效，请检查后重试。",
    "overlap_mentions": "引用区间存在重叠，请调整后重试。",
    "duplicate_mention": "当前引用存在重复记录，请检查后重试。",
    "text_mismatch": "引用位置与正文内容不匹配，请刷新后重试。",
    "invalid_entity": "当前引用实体无效，请重新选择。",
    "selection_rewrite_not_found": "未找到对应选区改写结果。",
    "invalid_selection_range": "当前选区范围无效，请重新选择后重试。",
    "selection_too_short": "当前选区过短，请至少选择 2 个字符。",
    "selection_too_long": "当前选区过长，请缩小范围后重试。",
    "source_hash_mismatch": "原始选区内容已变化，请刷新后重试。",
    "draft_snapshot_invalid": "当前草稿快照无效，请刷新后重试。",
    "selection_conflict": "当前草稿已变化，请刷新后重试。",
    "selection_text_mismatch": "当前选区文本已变化，请刷新后重试。",
    "status_not_pending": "当前改写状态不允许执行该操作。",
    "auto_queue_config_not_found": "未找到当前作品的自动续写配置。",
    "auto_queue_run_not_found": "未找到对应自动续写队列任务。",
    "auto_queue_target_chapters_required": "当前配置缺少目标章节数，请先完成配置。",
    "auto_queue_already_running": "当前作品已有自动续写任务在运行。",
    "auto_queue_disabled": "当前自动续写配置已关闭，请先启用后再试。",
    "auto_queue_work_id_mismatch": "自动续写任务与当前作品不匹配，请刷新后重试。",
    "auto_queue_not_waiting_user_decision": "当前状态下不能执行确认后继续。",
}


def resolve_safe_message(code_or_message: str) -> str:
    normalized = str(code_or_message or "").strip()
    return SAFE_MESSAGE_MAP.get(normalized, normalized)


def success_response(
    request: Request,
    *,
    data: dict[str, object],
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": trace_id_from_request(request),
        "status": "ok",
        "data": data,
    }
    if extra:
        payload.update(extra)
    return payload


def error_response(
    request: Request,
    *,
    error_code: str,
    status_code: int = 400,
    retryable: bool = False,
    safe_message: str | None = None,
    data: dict[str, object] | None = None,
) -> JSONResponse:
    error_payload: dict[str, object] = {
        "error_code": error_code,
        "safe_message": resolve_safe_message(safe_message or error_code),
        "retryable": retryable,
    }
    if data:
        error_payload["data"] = data
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": getattr(request.state, "request_id", ""),
            "trace_id": trace_id_from_request(request),
            "status": "error",
            "error": error_payload,
        },
    )
