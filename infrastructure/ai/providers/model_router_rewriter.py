from __future__ import annotations

import json
import uuid

from domain.entities.ai.models import LLMRequest
from domain.services.ai.rewriter import RewriterPort


class ModelRouterRewriter(RewriterPort):
    def __init__(self, *, model_router, prompt_registry, output_validator) -> None:  # noqa: ANN001
        self._model_router = model_router
        self._prompt_registry = prompt_registry
        self._output_validator = output_validator

    def rewrite(
        self,
        *,
        work_id: str,
        chapter_id: str,
        source_content: str,
        instruction_summary: str,
        source_context_pack_id: str,
    ) -> dict[str, object]:
        template = self._prompt_registry.get_template("candidate_rewrite_p1", version="p1")
        rendered = self._prompt_registry.render(
            template.prompt_key,
            {
                "input_json": json.dumps(
                    {
                        "work_id": work_id,
                        "chapter_id": chapter_id,
                        "source_content": source_content,
                        "instruction_summary": instruction_summary,
                        "source_context_pack_id": source_context_pack_id,
                    },
                    ensure_ascii=False,
                )
            },
            version=template.prompt_version,
        )
        last_error = "rewrite_output_invalid"
        for _attempt in range(3):
            request = LLMRequest(
                model_role=template.model_role,
                work_id=work_id,
                prompt_key=template.prompt_key,
                prompt_version=template.prompt_version,
                output_schema_key=template.output_schema_key,
                request_id=f"req_{uuid.uuid4().hex[:12]}",
                trace_id=f"trace_{uuid.uuid4().hex[:12]}",
                messages=[{"role": "user", "content": rendered}],
                max_tokens=max(512, len(source_content) * 2),
            )
            response = self._model_router.generate(request)
            validation = self._output_validator.validate(template.output_schema_key, response.content)
            if validation.success:
                result = dict(validation.parsed_output or {})
                result.update({"provider_name": response.provider_name, "model_name": response.model_name})
                return result
            last_error = validation.error_code or last_error
        raise ValueError(last_error)

