from __future__ import annotations

import json

from domain.entities.ai.models import AIProviderConfig, LLMRequest, LLMResponse, LLMUsage
from domain.services.ai.provider import LLMProvider, ProviderConfigurationError


class FakeLLMProvider(LLMProvider):
    provider_name = "fake"

    def __init__(self) -> None:
        self._supported_models = {"fake-chat", "fake-writer", "fake-review"}

    def supports_model(self, model_name: str) -> bool:
        return model_name in self._supported_models

    def generate(self, request: LLMRequest, provider_config: AIProviderConfig, model_name: str) -> LLMResponse:
        if not provider_config.encrypted_api_key:
            raise ProviderConfigurationError("provider_key_missing")
        if not self.supports_model(model_name):
            raise ProviderConfigurationError("model_not_supported")
        user_message = ""
        for message in request.messages:
            if message.get("role") == "user":
                user_message = message.get("content", "")
        content = user_message.strip() or f"fake provider response for {request.model_role}"
        if request.output_schema_key == "candidate_with_citations":
            citations: list[dict[str, object]] = []
            if any(token in user_message for token in ("引用", "前文", "线索")):
                citations.append(
                    {
                        "source_type": "chapter",
                        "source_name": "第一章",
                        "source_id_hint": "",
                        "context_in_draft": "顾迟发现海图的线索",
                        "confidence": 0.88,
                    }
                )
            content = json.dumps(
                {
                    "text": content,
                    "citations": citations,
                },
                ensure_ascii=False,
            )
        elif request.output_schema_key == "selection_rewrite_schema":
            rewritten_text = self._build_selection_rewrite_text(
                prompt_key=str(request.prompt_key or ""),
                source_text=user_message,
            )
            content = json.dumps(
                {
                    "rewritten_text": rewritten_text,
                    "diff_summary": f"{request.prompt_key or request.model_role}_generated",
                    "risk_notes": [],
                },
                ensure_ascii=False,
            )
        elif request.output_schema_key in {
            "outline_polish_schema",
            "outline_expand_schema",
            "chapter_outline_detail_schema",
            "writing_task_suggestion_schema",
        }:
            content = json.dumps(
                self._build_outline_assist_output(request.output_schema_key, user_message),
                ensure_ascii=False,
            )
        elif request.output_schema_key == "outline_analysis_result_p0":
            content = json.dumps(self._build_initialization_outline_output(user_message), ensure_ascii=False)
        elif request.output_schema_key == "manuscript_chapter_analysis_p0":
            content = json.dumps(self._build_initialization_chapter_output(user_message), ensure_ascii=False)
        elif request.output_schema_key == "story_memory_structure_p1":
            content = json.dumps(self._build_story_memory_structure_output(user_message), ensure_ascii=False)
        elif request.output_schema_key == "story_memory_global_p1":
            content = json.dumps(self._build_story_memory_global_output(user_message), ensure_ascii=False)
        elif request.output_schema_key == "ai_review_result_p0":
            content = json.dumps(
                {
                    "summary": "已完成候选稿一致性、逻辑与表达检查。",
                    "issues": [
                        {
                            "issue_id": "fake-timeline-1",
                            "severity": "medium",
                            "category": "timeline",
                            "message": "测试模型识别到一处时间线衔接风险。",
                            "suggestion": "核对前后场景的时间顺序。",
                            "source_ref": "candidate_draft",
                        }
                    ],
                    "suggestions": ["核对时间顺序。"],
                    "risk_level": "medium",
                    "consistency_notes": [],
                    "style_notes": [],
                    "logic_notes": [],
                },
                ensure_ascii=False,
            )
        elif request.output_schema_key == "candidate_rewrite_result_p1":
            prompt_input = self._initialization_input(user_message)
            source = str(prompt_input.get("source_content") or "")
            instruction = str(prompt_input.get("instruction_summary") or "")
            content = json.dumps(
                {
                    "rewritten_text": f"{source}\n\n{instruction}".strip(),
                    "revision_summary": instruction,
                    "addressed_issues": [instruction] if instruction else [],
                },
                ensure_ascii=False,
            )
        elif request.output_schema_key == "direction_generation_p1":
            content = json.dumps(self._build_direction_generation_output(user_message), ensure_ascii=False)
        elif request.output_schema_key == "chapter_plan_generation_p1":
            content = json.dumps(self._build_chapter_plan_generation_output(user_message), ensure_ascii=False)
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=model_name,
            content=content,
            request_id=request.request_id,
            trace_id=request.trace_id,
            token_usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            finish_reason="stop",
        )

    @staticmethod
    def _build_selection_rewrite_text(*, prompt_key: str, source_text: str) -> str:
        base = str(source_text or "").strip() or "测试片段"
        if prompt_key == "selection_expand_v1":
            return f"{base}风更冷些"
        if prompt_key == "selection_abbreviate_v1":
            keep_length = max(1, int(len(base) * 0.5))
            return base[:keep_length]
        if prompt_key == "selection_polish_v1":
            return f"{base}，语气与节奏更克制。"
        if prompt_key == "selection_dialogue_opt_v1":
            return f"{base}，他说得更自然。"
        if prompt_key == "selection_de_ai_v1":
            return f"{base}，表达更贴近日常叙事。"
        return f"{base}，细节更完整。"

    @staticmethod
    def _build_outline_assist_output(schema_key: str, user_message: str) -> dict[str, object]:
        try:
            prompt_input = json.loads(user_message)
        except (json.JSONDecodeError, TypeError):
            prompt_input = {}
        source = str(prompt_input.get("formal_target_content_text") or prompt_input.get("source_text") or "当前大纲")
        tree = prompt_input.get("target_content_tree_json", [])
        if schema_key == "writing_task_suggestion_schema":
            return {
                "task_title": "本章写作要点",
                "writing_goal": "按已确认的章节计划推进本章冲突",
                "must_include": ["推进本章核心目标"],
                "must_not_include": ["越过尚未确认的剧情"],
                "target_word_count": 2500,
                "tone_guidance": "保持自然、清楚的叙事节奏",
                "required_beats": ["开场承接", "冲突升级", "结尾钩子"],
                "context_summary": "依据已确认的章节计划整理",
            }
        base: dict[str, object] = {
            "proposed_content_text": f"{source}（已整理）",
            "proposed_content_tree_json": tree,
            "diff_summary": ["整理表达与推进顺序"],
        }
        if schema_key == "outline_polish_schema":
            base["polish_notes"] = ["未新增剧情事实"]
        elif schema_key == "outline_expand_schema":
            base.update(
                {
                    "expansion_points": ["补足人物动机", "补足场景转折"],
                    "expand_focus": prompt_input.get("expand_focus"),
                }
            )
        else:
            base.update(
                {
                    "chapter_goal": str(prompt_input.get("chapter_goal") or "推进本章主要矛盾"),
                    "scene_beats": [
                        {
                            "beat_no": 1,
                            "description": "承接上一场并建立本章目标",
                            "characters_involved": [],
                            "estimated_words": 800,
                        }
                    ],
                    "conflict_points": ["人物目标受到阻碍"],
                    "ending_hook": "留下下一步选择",
                }
            )
        return base

    @staticmethod
    def _initialization_input(user_message: str) -> dict[str, object]:
        marker = "输入如下：\n"
        raw = user_message.split(marker, 1)[-1] if marker in user_message else user_message
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @classmethod
    def _build_initialization_outline_output(cls, user_message: str) -> dict[str, object]:
        payload = cls._initialization_input(user_message)
        outline = str(payload.get("user_outline_content_text") or "").strip()
        known_names = [name for name in ("孔凡圣", "宋成", "顾迟", "沈砚", "林舟", "顾宁", "陆川", "温遥") if name in outline]
        return {
            "global_summary": outline[:180] or "作品尚未提供大纲。",
            "genre": "测试类型",
            "tone": "自然叙事",
            "issues": [] if outline else ["outline_empty"],
            "outline_empty": not bool(outline),
            "story_phase_map": ["当前阶段"] if outline else [],
            "main_conflict": "依据正式大纲推进核心冲突" if outline else "",
            "important_characters": known_names,
            "setting_facts": [],
            "foreshadow_map": [],
            "expected_story_direction": "沿正式大纲继续推进" if outline else "",
            "analysis_confidence": 0.9 if outline else 0.0,
        }

    @classmethod
    def _build_initialization_chapter_output(cls, user_message: str) -> dict[str, object]:
        payload = cls._initialization_input(user_message)
        chapter = payload.get("chapter") if isinstance(payload.get("chapter"), dict) else {}
        content = str(chapter.get("chapter_content") or "")
        title = str(chapter.get("chapter_title") or "本章")
        known_names = [name for name in ("孔凡圣", "宋成", "顾迟", "沈砚", "林舟", "顾宁", "陆川", "温遥") if name in content]
        location = next(
            (name for name in ("东南亚丛林", "白塔城", "灯塔顶层", "旧灯塔", "档案馆", "旧城", "港口", "群岛", "海边灯塔") if name in content),
            "当前场景",
        )
        reveal_points = [fragment for fragment in ("发现线索", "意识到异常") if fragment[:2] in content]
        return {
            "summary": f"{title}已完成结构化章节分析。",
            "characters": known_names,
            "locations": [location],
            "plot_points": [],
            "unresolved_threads": ["存在待确认问题"] if "？" in content or "?" in content else [],
            "scene_details": [
                {
                    "scene_order": 1,
                    "location": location,
                    "time_of_day": "夜里" if "夜" in content else "",
                    "atmosphere": "紧张" if any(value in content for value in ("逃", "追", "危险")) else "",
                    "characters_present": known_names,
                    "emotional_tone": "警觉" if any(value in content for value in ("意识到", "追", "逃")) else "",
                    "pov_hint": known_names[0] if known_names else "",
                    "reveal_points": reveal_points,
                }
            ],
            "chapter_position": "当前正文进度",
            "plot_progress": "本章剧情继续推进。",
            "character_state_delta": [
                {
                    "character_name": name,
                    "current_location": location,
                    "current_status": "出现在本章",
                    "recent_actions": [],
                    "relationships": [],
                    "confidence": 0.9,
                }
                for name in known_names
            ],
            "setting_fact_delta": [],
            "foreshadow_candidate_delta": [],
            "deviations_from_outline": [],
            "timeline_info": [],
            "warnings": [],
            "analysis_confidence": 0.9,
        }

    @classmethod
    def _build_story_memory_structure_output(cls, user_message: str) -> dict[str, object]:
        payload = cls._initialization_input(user_message)
        chapters = payload.get("chapter_summaries") if isinstance(payload.get("chapter_summaries"), list) else []
        chapter_ids = [str(item.get("chapter_id") or "") for item in chapters if isinstance(item, dict) and item.get("chapter_id")]
        summaries = [str(item.get("summary") or "") for item in chapters if isinstance(item, dict) and item.get("summary")]
        summary = " ".join(summaries).strip() or "测试章节摘要"
        layer = {
            "title": "当前阶段",
            "chapter_ids": chapter_ids,
            "summary": summary,
            "main_conflict": "",
            "plot_progress": "",
            "open_loops": [],
        }
        return {
            "stage_summaries": [layer],
            "volume_summaries": [{**layer, "title": "当前卷"}],
            "warnings": [],
            "analysis_confidence": 0.9,
        }

    @classmethod
    def _build_story_memory_global_output(cls, user_message: str) -> dict[str, object]:
        payload = cls._initialization_input(user_message)
        volumes = payload.get("volume_summaries") if isinstance(payload.get("volume_summaries"), list) else []
        summaries = [str(item.get("summary") or "") for item in volumes if isinstance(item, dict) and item.get("summary")]
        return {
            "global_summary": " ".join(summaries).strip() or "测试全书当前进度摘要",
            "current_story_phase": "当前阶段",
            "main_plot_threads": [],
            "unresolved_questions": [],
            "warnings": [],
            "analysis_confidence": 0.9,
        }

    @classmethod
    def _build_direction_generation_output(cls, user_message: str) -> dict[str, object]:
        payload = cls._initialization_input(user_message)
        instruction = str(payload.get("user_instruction") or "按当前上下文继续推进").strip()
        title = str(payload.get("chapter_title") or "当前章节").strip()
        options: list[dict[str, object]] = []
        for index, label in enumerate(("A", "B", "C"), start=1):
            premise = f"{instruction}（方案{label}）"
            options.append(
                {
                    "label": label,
                    "title": f"{title}后续方案{label}",
                    "plot_summary": premise,
                    "narrative_premise": premise,
                    "narrative_benefits": ["承接现有上下文", "保留作者后续选择空间"],
                    "main_conflicts": [],
                    "foreshadow_usage": [],
                    "risk_points": [],
                    "estimated_chapters": 3,
                    "chapter_preview": [f"方案{label}推进节点{step}" for step in range(1, 4)],
                    "score": {
                        "total_score": 80 - index,
                        "consistency_score": 80,
                        "conflict_density_score": 75,
                        "satisfaction_rhythm_score": 75,
                        "foreshadow_progress_score": 70,
                        "risk_controllability_score": 80,
                        "score_rationale": "测试模型依据输入生成。",
                    },
                    "confidence": 0.8,
                    "tone_direction": "延续当前语气",
                    "key_characters_involved": [],
                }
            )
        return {"options": options}

    @classmethod
    def _build_chapter_plan_generation_output(cls, user_message: str) -> dict[str, object]:
        payload = cls._initialization_input(user_message)
        selected = payload.get("selected_option") if isinstance(payload.get("selected_option"), dict) else {}
        premise = str(selected.get("plot_summary") or selected.get("narrative_premise") or "按已选方向推进")
        plan_items = []
        for index in range(1, 4):
            plan_items.append(
                {
                    "plan_order": index,
                    "chapter_goal": f"推进已选方向的第{index}个阶段",
                    "key_events": [
                        {
                            "beat_order": 1,
                            "beat_name": f"推进节点{index}",
                            "beat_description": premise,
                            "beat_type": "development",
                            "emotional_tone": "延续当前语气",
                            "involved_characters": [],
                        }
                    ],
                    "conflict_progression": premise,
                    "foreshadow_arrangement": [],
                    "forbidden_items": [],
                    "required_beats": [f"完成推进节点{index}"],
                    "estimated_word_count": 2200,
                    "estimated_word_count_max": 3200,
                    "tone_hint": "延续当前语气",
                    "pov_hint": "",
                }
            )
        return {"plan_items": plan_items, "plan_summary": premise, "constraints": []}

    def test_connection(self, provider_config: AIProviderConfig, model_name: str) -> dict[str, str]:
        if not provider_config.encrypted_api_key:
            raise ProviderConfigurationError("provider_key_missing")
        if not self.supports_model(model_name):
            raise ProviderConfigurationError("model_not_supported")
        return {
            "provider_name": self.provider_name,
            "model_name": model_name,
            "test_status": "ok",
            "message": "fake provider connection ok",
        }
