import json
from typing import Any, Dict

from application.prompts.prompt_constants import (
    PROMPT_SECTION_CONTINUATION_RULES,
    PROMPT_SECTION_DETEMPLATE_OPTIMIZATION,
    PROMPT_SECTION_DETEMPLATE_RULES,
    PROMPT_SECTION_INTEGRITY_RULES,
    PROMPT_SECTION_TASK_GENERATION,
    PROMPT_SECTION_TITLE_RULES,
)
from application.prompts.prompt_rules import (
    CONTINUATION_HARD_RULES,
    CONTINUATION_MEMORY_RULES,
    DETEMPLATE_HARD_RULES,
    DETEMPLATE_OPTIMIZATION_RULES,
    INTEGRITY_CHECK_RULES,
    TASK_GENERATION_RULES,
    TITLE_BACKFILL_RULES,
)


def build_chapter_ai_json_prompt(payload: Dict[str, Any]) -> str:
    rules = {
        PROMPT_SECTION_CONTINUATION_RULES: CONTINUATION_HARD_RULES,
        PROMPT_SECTION_TASK_GENERATION: TASK_GENERATION_RULES,
    }
    return (
        "You are a chapter-level fiction assistant. Return exactly one JSON object and no markdown.\n"
        'JSON schema: {"result_text": str, "analysis": object, "outline_draft": object|null}.\n'
        "outline_draft fields: goal, conflict, events, character_progress, ending_hook, opening_continuation, notes.\n"
        f"Rules: {json.dumps(rules, ensure_ascii=False)}\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_chapter_outline_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are a chapter analysis assistant. Return exactly one JSON object and no markdown.\n"
        "Required fields: goal, conflict, events, character_progress, ending_hook, opening_continuation, notes.\n"
        "events must be an array of short strings.\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_global_analysis_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are the global analysis model for a long-form fiction assistant.\n"
        "Return exactly one JSON object. No markdown.\n"
        "Required fields: characters, world_facts, style_profile, global_constraints, chapter_summaries, main_plot_lines.\n"
        "characters: array of objects with name, traits, relationships.\n"
        "world_facts: object with background, power_system, organizations, locations, rules, artifacts arrays.\n"
        "style_profile: object with narrative_pov, tone_tags, rhythm_tags.\n"
        "global_constraints: object with main_plot, hidden_plot, core_selling_points, protagonist_core_traits, must_keep_threads, genre_guardrails.\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_plot_arc_extraction_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are the plot arc extraction model for a long-form fiction assistant.\n"
        "Return exactly one JSON object. No markdown.\n"
        "Required fields: plot_arcs, chapter_arc_bindings, active_arc_ids.\n"
        "plot_arcs items must contain arc_id, title, arc_type, priority, status, goal, core_conflict, current_stage, stage_reason, stage_confidence, key_turning_points, must_resolve_points, related_characters, related_items, related_world_rules, covered_chapter_ids, latest_progress_summary, latest_result, next_push_suggestion.\n"
        "chapter_arc_bindings items must contain chapter_id, chapter_number, arc_id, binding_role, push_type, confidence.\n"
        "Keep active arcs between 3 and 5 whenever enough material exists.\n"
        "Stages must be one of setup, early_push, escalation, crisis, turning_point, payoff, aftermath.\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_continuation_memory_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are the continuation-memory extractor. Return exactly one JSON object and no markdown.\n"
        "Required fields: scene_summary, scene_state, protagonist_state, active_characters, active_conflicts, immediate_threads, long_term_threads, recent_reveals, must_continue_points, forbidden_jumps, tone_and_pacing, last_hook, used_fallback.\n"
        "Use strict JSON punctuation and ASCII double quotes only. Do not use full-width punctuation like ： ， ｛ ｝.\n"
        f"Rules: {json.dumps({PROMPT_SECTION_CONTINUATION_RULES: CONTINUATION_MEMORY_RULES}, ensure_ascii=False)}\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_chapter_task_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are the chapter task planner. Return exactly one JSON object and no markdown.\n"
        "Required fields: chapter_function, goals, must_continue_points, forbidden_jumps, required_foreshadowing_action, required_hook_strength, pace_target, opening_continuation, chapter_payoff, style_bias, target_arc_id, secondary_arc_ids, arc_stage_before, arc_stage_after_expected, arc_push_goal, arc_conflict_focus, arc_payoff_expectation, planning_mode, used_fallback.\n"
        f"Rules: {json.dumps({PROMPT_SECTION_TASK_GENERATION: TASK_GENERATION_RULES}, ensure_ascii=False)}\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_structural_draft_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are the structural draft writer. Return exactly one JSON object and no markdown.\n"
        "Required fields: title, content, new_events, possible_continuity_flags.\n"
        "content不能为空 and must never be empty.\n"
        f"Rules: {json.dumps({PROMPT_SECTION_CONTINUATION_RULES: CONTINUATION_HARD_RULES}, ensure_ascii=False)}\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_detemplating_prompt(payload: Dict[str, Any]) -> str:
    rules = {
        PROMPT_SECTION_DETEMPLATE_RULES: DETEMPLATE_HARD_RULES,
        PROMPT_SECTION_DETEMPLATE_OPTIMIZATION: DETEMPLATE_OPTIMIZATION_RULES,
    }
    return (
        "You are the detemplating rewriter. Return plain prose only, no markdown, no explanation.\n"
        f"Rules: {json.dumps(rules, ensure_ascii=False)}\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_detemplating_revision_prompt(payload: Dict[str, Any]) -> str:
    rules = {
        PROMPT_SECTION_DETEMPLATE_RULES: DETEMPLATE_HARD_RULES,
        PROMPT_SECTION_DETEMPLATE_OPTIMIZATION: DETEMPLATE_OPTIMIZATION_RULES,
    }
    return (
        "You are the revision rewriter for a fiction assistant. Return plain prose only, no markdown, no explanation.\n"
        "Revise the existing detemplated draft according to the issue list. Preserve valid plot facts, continuity, and arc direction.\n"
        "Do not switch responsibilities: this is a writing-layer rewrite, not a global analysis task.\n"
        f"Rules: {json.dumps(rules, ensure_ascii=False)}\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_integrity_check_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are the integrity checker. Return exactly one JSON object and no markdown.\n"
        "Required fields: event_integrity_ok, motivation_integrity_ok, foreshadowing_integrity_ok, hook_integrity_ok, continuity_ok, arc_consistency_ok, title_alignment_ok, progression_integrity_ok, risk_notes.\n"
        f"Rules: {json.dumps({PROMPT_SECTION_INTEGRITY_RULES: INTEGRITY_CHECK_RULES}, ensure_ascii=False)}\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )


def build_title_backfill_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are the title backfill assistant. Return exactly one JSON object and no markdown.\n"
        "Required fields: title.\n"
        f"Rules: {json.dumps({PROMPT_SECTION_TITLE_RULES: TITLE_BACKFILL_RULES}, ensure_ascii=False)}\n"
        f"Input: {json.dumps(payload, ensure_ascii=False)}"
    )
