from domain.entities.ai.models import StyleProfile, StyleProfileSourceType, StyleProfileStatus
from infrastructure.persistence.sqlite_style_profile_repo import SQLiteStyleProfileRepository


def test_style_profile_model_preserves_required_fields_and_builds_context_summary() -> None:
    profile = StyleProfile(
        profile_id="sp_001",
        work_id="work_001",
        source_type=StyleProfileSourceType.USER_UPLOAD,
        source_ref="upload_001",
        source_text_hash="sha256:abc123",
        source_text_length=2600,
        confidence=0.82,
        low_confidence_reason="",
        avg_sentence_length=18.4,
        sentence_length_variance=3.2,
        short_sentence_ratio=0.22,
        long_sentence_ratio=0.08,
        compound_sentence_ratio=0.37,
        avg_paragraph_length=86.5,
        paragraph_length_variance=12.0,
        dialogue_ratio=0.34,
        psychological_ratio=0.18,
        action_ratio=0.28,
        description_ratio=0.20,
        narrative_perspective="third_person_limited",
        tense_preference="past",
        style_summary="简洁冷峻，偏第三人称限知，短句推动节奏。",
        style_tags=["简洁", "冷峻"],
        version=1,
        status=StyleProfileStatus.PENDING_CONFIRM,
        created_at="2026-06-23T10:00:00Z",
        updated_at="2026-06-23T10:00:00Z",
        confirmed_at="",
    )

    summary = profile.to_context_summary()

    assert profile.source_text_hash == "sha256:abc123"
    assert profile.status == StyleProfileStatus.PENDING_CONFIRM
    assert "风格特征" in summary
    assert "风格标签" in summary
    assert "简洁冷峻" in summary
    assert "叙述视角：third_person_limited" in summary


def test_sqlite_style_profile_repository_persists_active_and_history_profiles(tmp_path) -> None:
    repo = SQLiteStyleProfileRepository(tmp_path / "style-profile.db")
    pending_profile = StyleProfile(
        profile_id="sp_pending_001",
        work_id="work_001",
        source_type=StyleProfileSourceType.USER_UPLOAD,
        source_ref="upload_001",
        source_text_hash="sha256:pending",
        source_text_length=800,
        confidence=0.42,
        low_confidence_reason="source_text_too_short",
        avg_sentence_length=11.0,
        sentence_length_variance=2.0,
        short_sentence_ratio=0.48,
        long_sentence_ratio=0.02,
        compound_sentence_ratio=0.15,
        avg_paragraph_length=40.0,
        paragraph_length_variance=8.0,
        dialogue_ratio=0.12,
        psychological_ratio=0.18,
        action_ratio=0.44,
        description_ratio=0.26,
        narrative_perspective="first_person",
        tense_preference="present",
        style_summary="短句密集，动作感强。",
        style_tags=["短句", "动作"],
        version=1,
        status=StyleProfileStatus.PENDING_CONFIRM,
        created_at="2026-06-23T10:00:00Z",
        updated_at="2026-06-23T10:00:00Z",
        confirmed_at="",
    )
    active_profile = pending_profile.model_copy(
        update={
            "profile_id": "sp_active_001",
            "status": StyleProfileStatus.ACTIVE,
            "version": 2,
            "created_at": "2026-06-23T10:10:00Z",
            "updated_at": "2026-06-23T10:10:00Z",
            "confirmed_at": "2026-06-23T10:11:00Z",
        }
    )

    repo.save(pending_profile)
    repo.save(active_profile)

    loaded_pending = repo.get_by_id("sp_pending_001")
    loaded_active = repo.get_active("work_001")
    history = repo.get_history("work_001")

    assert loaded_pending is not None
    assert loaded_pending.low_confidence_reason == "source_text_too_short"
    assert loaded_active is not None
    assert loaded_active.profile_id == "sp_active_001"
    assert [item.profile_id for item in history] == ["sp_active_001", "sp_pending_001"]

    repo.delete("sp_pending_001")
    assert repo.get_by_id("sp_pending_001") is None
