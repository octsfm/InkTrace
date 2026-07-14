from __future__ import annotations

import json
import uuid

from domain.entities.ai.models import LLMRequest
from domain.services.ai.planning_generator import PlanningGeneratorPort


class ModelRouterPlanningGenerator(PlanningGeneratorPort):
    def __init__(self, *, model_router, prompt_registry, output_validator) -> None:  # noqa: ANN001
        self._model_router = model_router
        self._prompt_registry = prompt_registry
        self._output_validator = output_validator

    def generate_direction_options(
        self,
        *,
        work_id: str,
        chapter_id: str,
        chapter_title: str,
        user_instruction: str,
        context_pack: object,
    ) -> dict[str, object]:
        return self._generate(
            prompt_key="direction_generation_p1",
            prompt_version="p1",
            work_id=work_id,
            payload={
                "chapter_id": chapter_id,
                "chapter_title": chapter_title,
                "user_instruction": user_instruction,
                "context_pack": self._context_payload(context_pack),
            },
        )

    def generate_chapter_plan(
        self,
        *,
        work_id: str,
        chapter_id: str,
        selected_option: dict[str, object],
        context_pack: object,
    ) -> dict[str, object]:
        return self._generate(
            prompt_key="chapter_plan_generation_p1",
            prompt_version="p1",
            work_id=work_id,
            payload={
                "chapter_id": chapter_id,
                "selected_option": selected_option,
                "context_pack": self._context_payload(context_pack),
            },
        )

    def _generate(self, *, prompt_key: str, prompt_version: str, work_id: str, payload: dict[str, object]) -> dict[str, object]:
        template = self._prompt_registry.get_template(prompt_key, version=prompt_version)
        rendered = self._prompt_registry.render(
            prompt_key,
            {"input_json": json.dumps(payload, ensure_ascii=False)},
            version=prompt_version,
        )
        last_error = "planner_output_invalid"
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
                max_tokens=4096,
            )
            response = self._model_router.generate(request)
            validation = self._output_validator.validate(template.output_schema_key, response.content)
            if validation.success:
                result = dict(validation.parsed_output or {})
                result.update({"provider_name": response.provider_name, "model_name": response.model_name})
                return result
            last_error = validation.error_code or last_error
        raise ValueError(last_error)

    @staticmethod
    def _context_payload(context_pack: object) -> dict[str, object]:
        included_items = []
        for item in list(getattr(context_pack, "context_items", []) or []):
            if not bool(getattr(item, "included", False)):
                continue
            included_items.append(
                {
                    "source_type": str(getattr(item, "source_type", "") or ""),
                    "source_id": str(getattr(item, "source_id", "") or ""),
                    "content_text": str(getattr(item, "content_text", "") or ""),
                    "summary": str(getattr(item, "summary", "") or ""),
                }
            )
        return {
            "context_pack_id": str(getattr(context_pack, "context_pack_id", "") or ""),
            "status": str(getattr(getattr(context_pack, "status", ""), "value", getattr(context_pack, "status", "")) or ""),
            "summary": str(getattr(context_pack, "summary", "") or ""),
            "items": included_items,
        }
