from __future__ import annotations

from fastapi import APIRouter, Request

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response
from presentation.api.routers.v2.ai.schemas import StartInitializationRequest

router = APIRouter(tags=["v2-ai-initialization"])


def _serialize_initialization(item) -> dict[str, object]:
    return {
        "initialization_id": item.initialization_id,
        "work_id": item.work_id,
        "job_id": item.job_id,
        "status": item.status.value,
        "completion_status": item.completion_status.value,
        "analyzed_chapter_count": item.analyzed_chapter_count,
        "total_confirmed_chapter_count": item.total_confirmed_chapter_count,
        "empty_chapter_count": item.empty_chapter_count,
        "failed_chapter_count": item.failed_chapter_count,
        "partial_success_reason": item.partial_success_reason,
        "story_memory_snapshot_id": item.story_memory_snapshot_id,
        "story_state_snapshot_id": item.story_state_snapshot_id,
        "error_code": item.error_code,
        "error_message": item.error_message,
        "stale": item.stale,
        "stale_reason": item.stale_reason,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "finalized_at": item.finalized_at,
    }


@router.post("/api/v2/ai/initializations")
def start_initialization(payload: StartInitializationRequest, request: Request):
    service = dependencies.get_initialization_service()
    try:
        initialization = service.start_initialization(payload.work_id, created_by=payload.created_by)
    except ValueError as exc:
        error_code = str(exc)
        status_code = 404 if error_code == "work_not_found" else 400
        return error_response(request, error_code=error_code, status_code=status_code)
    return success_response(request, data=_serialize_initialization(initialization))


@router.get("/api/v2/ai/initializations/{initialization_id}")
def get_initialization(initialization_id: str, request: Request):
    service = dependencies.get_initialization_service()
    try:
        initialization = service.get_initialization(initialization_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    return success_response(request, data=_serialize_initialization(initialization))


@router.get("/api/v2/ai/works/{work_id}/initialization/latest")
def get_latest_initialization(work_id: str, request: Request):
    service = dependencies.get_initialization_service()
    try:
        initialization = service.get_latest_initialization(work_id)
    except ValueError as exc:
        return error_response(request, error_code=str(exc), status_code=404)
    if initialization is None:
        return success_response(
            request,
            data={
                "work_id": work_id,
                "status": "not_started",
                "analyzed_chapter_count": 0,
                "total_confirmed_chapter_count": 0,
                "empty_chapter_count": 0,
                "failed_chapter_count": 0,
                "stale": False,
            },
        )
    return success_response(request, data=_serialize_initialization(initialization))


@router.get("/api/v2/ai/works/{work_id}/story-memory/latest")
def get_latest_story_memory(work_id: str, request: Request):
    service = dependencies.get_initialization_service()
    snapshot = service.get_latest_story_memory(work_id)
    if snapshot is None:
        return error_response(request, error_code="story_memory_not_found", status_code=404)
    return success_response(
        request,
        data={
            "snapshot_id": snapshot.snapshot_id,
            "work_id": snapshot.work_id,
            "source_initialization_id": snapshot.source_initialization_id,
            "source_job_id": snapshot.source_job_id,
            "source_chapter_ids": snapshot.source_chapter_ids,
            "source_chapter_versions": snapshot.source_chapter_versions,
            "global_summary": snapshot.global_summary,
            "chapter_summaries": snapshot.chapter_summaries,
            "stage_summaries": snapshot.stage_summaries,
            "volume_summaries": snapshot.volume_summaries,
            "characters": snapshot.characters,
            "locations": snapshot.locations,
            "plot_threads": snapshot.plot_threads,
            "source": snapshot.source,
            "source_analysis_version": snapshot.source_analysis_version,
            "outline_analysis_id": snapshot.outline_analysis_id,
            "story_blueprint_id": snapshot.story_blueprint_id,
            "chapter_analysis_ids": snapshot.chapter_analysis_ids,
            "current_story_summary": snapshot.current_story_summary,
            "character_states": snapshot.character_states,
            "setting_facts": snapshot.setting_facts,
            "foreshadow_candidates": snapshot.foreshadow_candidates,
            "unresolved_questions": snapshot.unresolved_questions,
            "timeline_facts": snapshot.timeline_facts,
            "warnings": snapshot.warnings,
            "confidence": snapshot.confidence,
            "stale_status": snapshot.stale_status,
            "stale_reason": snapshot.stale_reason,
            "created_at": snapshot.created_at,
        },
    )


@router.get("/api/v2/ai/works/{work_id}/story-state/latest")
def get_latest_story_state(work_id: str, request: Request):
    service = dependencies.get_initialization_service()
    story_state = service.get_latest_story_state(work_id)
    if story_state is None:
        return error_response(request, error_code="story_state_not_found", status_code=404)
    return success_response(
        request,
        data={
            "story_state_id": story_state.story_state_id,
            "work_id": story_state.work_id,
            "source_initialization_id": story_state.source_initialization_id,
            "source_job_id": story_state.source_job_id,
            "latest_chapter_id": story_state.latest_chapter_id,
            "latest_chapter_version": story_state.latest_chapter_version,
            "current_position_summary": story_state.current_position_summary,
            "active_characters": story_state.active_characters,
            "active_locations": story_state.active_locations,
            "unresolved_threads": story_state.unresolved_threads,
            "continuity_notes": story_state.continuity_notes,
            "source_snapshot_id": story_state.source_snapshot_id,
            "baseline_type": story_state.baseline_type,
            "source": story_state.source,
            "source_chapter_analysis_ids": story_state.source_chapter_analysis_ids,
            "current_chapter_id": story_state.current_chapter_id,
            "current_chapter_order": story_state.current_chapter_order,
            "current_story_phase": story_state.current_story_phase,
            "current_time_position": story_state.current_time_position,
            "current_character_states": story_state.current_character_states,
            "active_conflicts": story_state.active_conflicts,
            "active_foreshadows": story_state.active_foreshadows,
            "resolved_foreshadows": story_state.resolved_foreshadows,
            "important_setting_facts": story_state.important_setting_facts,
            "current_location_scope": story_state.current_location_scope,
            "recent_key_events": story_state.recent_key_events,
            "unresolved_questions": story_state.unresolved_questions,
            "analysis_confidence": story_state.analysis_confidence,
            "stale_status": story_state.stale_status,
            "stale_reason": story_state.stale_reason,
            "created_at": story_state.created_at,
        },
    )
