from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from application.services.ai.llm_call_logger import LLMCallLogger
from application.services.ai.prompt_registry import PromptRegistry
from domain.entities.ai.models import ContextPackSnapshot, LLMCallStatus, LLMRequest, WritingTask
from domain.services.ai.writer import WriterPort


class ModelRouterWriter(WriterPort):
    def __init__(
        self,
        *,
        model_router,
        llm_call_log_repository,
        prompt_registry: PromptRegistry | None = None,
        trace_service=None,
    ) -> None:
        self._model_router = model_router
        self._prompt_registry = prompt_registry or PromptRegistry()
        self._call_logger = LLMCallLogger(llm_call_log_repository, trace_service=trace_service)

    def generate_candidate_text(self, *, context_pack: ContextPackSnapshot, writing_task: WritingTask) -> dict[str, object]:
        request_id = str(writing_task.request_id or f"req_{uuid.uuid4().hex[:12]}")
        trace_id = str(writing_task.trace_id or f"trace_{uuid.uuid4().hex[:12]}")
        started_at = datetime.now(UTC)
        prompt_key = "continuation_writer_p0"
        prompt_version = "v1"
        selection = self._model_router.resolve_model(writing_task.model_role)
        llm_request = LLMRequest(
            model_role=writing_task.model_role,
            prompt_key=prompt_key,
            prompt_version=prompt_version,
            output_schema_key="candidate_with_citations",
            request_id=request_id,
            trace_id=trace_id,
            messages=self._build_messages(context_pack=context_pack, writing_task=writing_task),
        )

        try:
            response = self._model_router.generate(llm_request)
        except Exception as exc:  # noqa: BLE001
            finished_at = datetime.now(UTC)
            error_code = getattr(exc, "error_code", str(exc) or "writer_generation_failed")
            self._call_logger.record(
                prompt_key=prompt_key,
                prompt_version=prompt_version,
                work_id=writing_task.work_id,
                model_role=writing_task.model_role,
                provider_name=selection.provider_name,
                model_name=selection.model_name,
                request_id=request_id,
                trace_id=trace_id,
                status=LLMCallStatus.FAILED,
                started_at=started_at,
                finished_at=finished_at,
                error_code=error_code,
                error_message=str(exc),
                context_pack_snapshot_id=context_pack.context_pack_id,
                output_schema_key="candidate_with_citations",
            )
            raise

        finished_at = datetime.now(UTC)
        self._call_logger.record(
            prompt_key=prompt_key,
            prompt_version=prompt_version,
            work_id=writing_task.work_id,
            model_role=writing_task.model_role,
            provider_name=response.provider_name,
            model_name=response.model_name,
            request_id=request_id,
            trace_id=trace_id,
            status=LLMCallStatus.SUCCEEDED,
            started_at=started_at,
            finished_at=finished_at,
            usage=response.token_usage,
            context_pack_snapshot_id=context_pack.context_pack_id,
            output_schema_key="candidate_with_citations",
        )
        content, citations = self._parse_writer_payload(response.content)
        return {
            "content": content,
            "citations": citations,
            "provider_name": response.provider_name,
            "model_name": response.model_name,
            "model_role": writing_task.model_role,
        }

    def _build_messages(self, *, context_pack: ContextPackSnapshot, writing_task: WritingTask) -> list[dict[str, str]]:
        goal = str(writing_task.user_instruction or writing_task.writing_goal or "继续当前章节").strip()
        system_prompt = self._prompt_registry.render(prompt_key="continuation_writer_p0", variables={"goal": goal})
        summary = str(context_pack.summary or "").strip()
        user_parts = [
            f"目标章节ID: {writing_task.target_chapter_id or writing_task.chapter_id}",
            f"用户目标: {goal}",
            f"上下文摘要: {summary}" if summary else "上下文摘要: 无",
            "如使用前文设定、角色、事件或章节信息，请同时返回 citations 字段。",
        ]
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(user_parts)},
        ]

    def _parse_writer_payload(self, raw_content: object) -> tuple[str, list[dict[str, object]]]:
        if isinstance(raw_content, dict):
            payload = raw_content
        else:
            text = str(raw_content or "").strip()
            if not text:
                return "", []
            try:
                payload = json.loads(text)
            except (json.JSONDecodeError, TypeError, ValueError):
                return text, []
        if not isinstance(payload, dict):
            return str(raw_content or "").strip(), []
        content = str(payload.get("text") or payload.get("content") or "").strip()
        citations = payload.get("citations")
        if not isinstance(citations, list):
            citations = []
        normalized: list[dict[str, object]] = []
        for item in citations:
            if isinstance(item, dict):
                normalized.append(dict(item))
        return content, normalized
