from __future__ import annotations

import json
import uuid

from domain.entities.ai.models import (
    ChapterAnalysisResult,
    ChapterAnalysisStatus,
    ChapterSceneDetail,
    HierarchicalStorySummary,
    LLMRequest,
    OutlineAnalysisResult,
)


class OutlineAnalysisService:
    def __init__(self, *, model_router, prompt_registry, output_validator) -> None:  # noqa: ANN001
        self._model_router = model_router
        self._prompt_registry = prompt_registry
        self._output_validator = output_validator

    def analyze(
        self,
        *,
        work_id: str,
        work_title: str,
        user_outline: str,
        existing_chapters: list[dict[str, object]],
        job_id: str,
    ) -> OutlineAnalysisResult:
        outline_text = str(user_outline or "").strip()
        chapter_order = [str(item.get("chapter_id", "") or "") for item in existing_chapters]
        chapter_titles = [str(item.get("title", "") or "") for item in existing_chapters]
        if not outline_text:
            return OutlineAnalysisResult(
                work_id=work_id,
                title=work_title,
                chapter_order=chapter_order,
                chapter_titles=chapter_titles,
                global_summary=f"{work_title}尚未提供作品大纲。",
                issues=["outline_empty"],
                outline_empty=True,
                analysis_confidence=0.0,
            )

        template = self._prompt_registry.get_template("outline_analysis_p0", version="p0")
        input_json = json.dumps(
            {
                "work_id": work_id,
                "work_title": work_title,
                "user_outline_content_text": outline_text,
                "existing_chapter_list": existing_chapters,
            },
            ensure_ascii=False,
        )
        parsed = self._call_structured_model(
            template=template,
            rendered_prompt=self._prompt_registry.render(
                template.prompt_key,
                {"input_json": input_json},
                version=template.prompt_version,
            ),
            work_id=work_id,
            job_id=job_id,
        )
        parsed["outline_empty"] = False
        return OutlineAnalysisResult(
            work_id=work_id,
            title=work_title,
            chapter_order=chapter_order,
            chapter_titles=chapter_titles,
            **parsed,
        )

    def _call_structured_model(self, *, template, rendered_prompt: str, work_id: str, job_id: str) -> dict[str, object]:  # noqa: ANN001
        last_error = "output_schema_invalid"
        for _attempt in range(3):
            request = LLMRequest(
                model_role=template.model_role,
                work_id=work_id,
                job_id=job_id,
                prompt_key=template.prompt_key,
                prompt_version=template.prompt_version,
                output_schema_key=template.output_schema_key,
                request_id=f"req_{uuid.uuid4().hex[:12]}",
                trace_id=f"trace_{uuid.uuid4().hex[:12]}",
                messages=[{"role": "user", "content": rendered_prompt}],
                max_tokens=4096,
            )
            response = self._model_router.generate(request)
            validation = self._output_validator.validate(template.output_schema_key, response.content)
            if validation.success:
                return dict(validation.parsed_output or {})
            last_error = validation.error_code or last_error
        raise ValueError(last_error)


class ManuscriptAnalysisService:
    def __init__(self, *, model_router, prompt_registry, output_validator) -> None:  # noqa: ANN001
        self._model_router = model_router
        self._prompt_registry = prompt_registry
        self._output_validator = output_validator

    def analyze_chapter(
        self,
        *,
        work_id: str,
        chapter_id: str,
        chapter_title: str,
        chapter_content: str,
        chapter_version: int,
        chapter_order: int,
        outline_analysis: OutlineAnalysisResult,
        previous_chapter_summaries: list[str],
        job_id: str,
        analyzed_at: str = "",
    ) -> ChapterAnalysisResult:
        content = str(chapter_content or "").strip()
        if not content:
            return ChapterAnalysisResult(
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                chapter_version=chapter_version,
                status=ChapterAnalysisStatus.EMPTY,
                summary="chapter_empty",
                error_code="chapter_empty",
                warnings=["chapter_empty"],
                is_empty=True,
                analyzed_at=analyzed_at,
            )

        template = self._prompt_registry.get_template("manuscript_chapter_analysis_p0", version="p0")
        input_json = json.dumps(
            {
                "work_id": work_id,
                "chapter": {
                    "chapter_id": chapter_id,
                    "chapter_order": chapter_order,
                    "chapter_title": chapter_title,
                    "chapter_content": content,
                    "chapter_version": chapter_version,
                },
                "outline_analysis": outline_analysis.model_dump(mode="json"),
                "previous_chapter_summaries": previous_chapter_summaries,
            },
            ensure_ascii=False,
        )
        parsed = self._call_structured_model(
            template=template,
            rendered_prompt=self._prompt_registry.render(
                template.prompt_key,
                {"input_json": input_json},
                version=template.prompt_version,
            ),
            work_id=work_id,
            job_id=job_id,
        )
        raw_scenes = list(parsed.pop("scene_details", []) or [])
        scenes = [
            ChapterSceneDetail(
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                chapter_version=chapter_version,
                **dict(item),
            )
            for item in raw_scenes
        ]
        return ChapterAnalysisResult(
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            chapter_version=chapter_version,
            status=ChapterAnalysisStatus.SUCCEEDED,
            scene_details=scenes,
            analyzed_at=analyzed_at,
            **parsed,
        )

    def analyze_story_hierarchy(
        self,
        *,
        work_id: str,
        outline_analysis: OutlineAnalysisResult,
        chapter_results: list[ChapterAnalysisResult],
        job_id: str,
    ) -> HierarchicalStorySummary:
        successful = [item for item in chapter_results if item.status == ChapterAnalysisStatus.SUCCEEDED and item.summary]
        if not successful:
            raise ValueError("empty_chapter_analysis_results")

        chapter_summary_inputs = [
            {
                "chapter_id": item.chapter_id,
                "chapter_order": index,
                "chapter_title": item.chapter_title,
                "summary": item.summary,
                "chapter_position": item.chapter_position,
                "plot_progress": item.plot_progress,
                "plot_points": list(item.plot_points),
                "unresolved_threads": list(item.unresolved_threads),
            }
            for index, item in enumerate(successful, start=1)
        ]
        structure_template = self._prompt_registry.get_template("story_memory_structure_p1", version="p1")
        structure_input = json.dumps(
            {
                "work_id": work_id,
                "outline_analysis": outline_analysis.model_dump(mode="json"),
                "chapter_summaries": chapter_summary_inputs,
            },
            ensure_ascii=False,
        )
        structure = self._call_structured_model(
            template=structure_template,
            rendered_prompt=self._prompt_registry.render(
                structure_template.prompt_key,
                {"input_json": structure_input},
                version=structure_template.prompt_version,
            ),
            work_id=work_id,
            job_id=job_id,
            parsed_validator=lambda value: self._validate_hierarchy_coverage(value, successful),
        )

        global_template = self._prompt_registry.get_template("story_memory_global_p1", version="p1")
        global_input = json.dumps(
            {
                "work_id": work_id,
                "outline_global_summary": outline_analysis.global_summary,
                "stage_summaries": structure["stage_summaries"],
                "volume_summaries": structure["volume_summaries"],
                "latest_chapter_summary": chapter_summary_inputs[-1],
            },
            ensure_ascii=False,
        )
        global_result = self._call_structured_model(
            template=global_template,
            rendered_prompt=self._prompt_registry.render(
                global_template.prompt_key,
                {"input_json": global_input},
                version=global_template.prompt_version,
            ),
            work_id=work_id,
            job_id=job_id,
        )
        return HierarchicalStorySummary(
            stage_summaries=list(structure["stage_summaries"]),
            volume_summaries=list(structure["volume_summaries"]),
            warnings=self._unique([*list(structure.get("warnings", [])), *list(global_result.get("warnings", []))]),
            analysis_confidence=min(
                float(structure.get("analysis_confidence", 0.0) or 0.0),
                float(global_result.get("analysis_confidence", 0.0) or 0.0),
            ),
            **{key: value for key, value in global_result.items() if key not in {"warnings", "analysis_confidence"}},
        )

    @staticmethod
    def _validate_hierarchy_coverage(
        structure: dict[str, object],
        chapter_results: list[ChapterAnalysisResult],
    ) -> None:
        expected = {item.chapter_id for item in chapter_results}
        for layer_name in ("stage_summaries", "volume_summaries"):
            layer = structure.get(layer_name, [])
            if not isinstance(layer, list) or not layer:
                raise ValueError("output_schema_invalid")
            covered: set[str] = set()
            for raw_item in layer:
                if isinstance(raw_item, dict):
                    covered.update(str(value) for value in raw_item.get("chapter_ids", []) if str(value))
            if not expected.issubset(covered):
                raise ValueError("output_schema_invalid")

    @staticmethod
    def _unique(items: list[object]) -> list[str]:
        result: list[str] = []
        for item in items:
            value = str(item or "").strip()
            if value and value not in result:
                result.append(value)
        return result

    def _call_structured_model(
        self,
        *,
        template,
        rendered_prompt: str,
        work_id: str,
        job_id: str,
        parsed_validator=None,
    ) -> dict[str, object]:  # noqa: ANN001
        last_error = "output_schema_invalid"
        for _attempt in range(3):
            request = LLMRequest(
                model_role=template.model_role,
                work_id=work_id,
                job_id=job_id,
                prompt_key=template.prompt_key,
                prompt_version=template.prompt_version,
                output_schema_key=template.output_schema_key,
                request_id=f"req_{uuid.uuid4().hex[:12]}",
                trace_id=f"trace_{uuid.uuid4().hex[:12]}",
                messages=[{"role": "user", "content": rendered_prompt}],
                max_tokens=4096,
            )
            response = self._model_router.generate(request)
            validation = self._output_validator.validate(template.output_schema_key, response.content)
            if validation.success:
                parsed = dict(validation.parsed_output or {})
                if parsed_validator is not None:
                    try:
                        parsed_validator(parsed)
                    except (TypeError, ValueError):
                        last_error = "output_schema_invalid"
                        continue
                return parsed
            last_error = validation.error_code or last_error
        raise ValueError(last_error)
