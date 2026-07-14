from __future__ import annotations

import json
import uuid

from domain.entities.ai.models import LLMRequest
from domain.services.ai.reviewer import ReviewerPort


class ModelRouterReviewer(ReviewerPort):
    def __init__(self, *, model_router, prompt_registry, output_validator) -> None:  # noqa: ANN001
        self._model_router = model_router
        self._prompt_registry = prompt_registry
        self._output_validator = output_validator

    def review(
        self,
        *,
        review_context: dict[str, object],
        review_mode: str,
        user_instruction: str = "",
    ) -> dict[str, object]:
        template = self._prompt_registry.get_template("ai_review_p0", version="p0")
        input_json = json.dumps(
            {
                "review_mode": review_mode,
                "user_instruction": str(user_instruction or ""),
                "review_context": review_context,
            },
            ensure_ascii=False,
        )
        rendered = self._prompt_registry.render(
            template.prompt_key,
            {"input_json": input_json},
            version=template.prompt_version,
        )
        last_error = "review_output_invalid"
        for _attempt in range(3):
            request = LLMRequest(
                model_role=template.model_role,
                work_id=str(review_context.get("work_id", "") or ""),
                prompt_key=template.prompt_key,
                prompt_version=template.prompt_version,
                output_schema_key=template.output_schema_key,
                request_id=f"req_{uuid.uuid4().hex[:12]}",
                trace_id=f"trace_{uuid.uuid4().hex[:12]}",
                messages=[{"role": "user", "content": rendered}],
                max_tokens=3072,
            )
            response = self._model_router.generate(request)
            validation = self._output_validator.validate(template.output_schema_key, response.content)
            if not validation.success:
                last_error = validation.error_code or last_error
                continue
            parsed = dict(validation.parsed_output or {})
            parsed.update(
                {
                    "provider_name": response.provider_name,
                    "model_name": response.model_name,
                    "reviewer_model_role": template.model_role,
                }
            )
            return parsed
        raise ValueError(last_error)

