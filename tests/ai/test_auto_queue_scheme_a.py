import sqlite3

import pytest
from pydantic import ValidationError

from domain.entities.ai import models
from infrastructure.database.models import initialize_schema
from infrastructure.persistence.sqlite_auto_queue_config_repo import SQLiteAutoQueueConfigRepository
from infrastructure.persistence.sqlite_auto_queue_run_repo import SQLiteAutoQueueRunRepository
from presentation.api.routers.v2.ai.auto_queues import AutoQueueConfigUpsertRequest


def test_scheme_a_removes_queue_mode_from_domain_contract() -> None:
    assert not hasattr(models, "AutoQueueMode")
    assert "queue_mode" not in models.AutoQueueConfig.model_fields
    assert "queue_mode" not in models.AutoQueueRun.model_fields

    with pytest.raises(ValidationError):
        models.AutoQueueConfig(config_id="aqc_001", work_id="work_001", queue_mode="continuous")


def test_scheme_a_rejects_queue_mode_from_api_contract() -> None:
    with pytest.raises(ValidationError):
        AutoQueueConfigUpsertRequest(work_id="work_001", queue_mode="continuous")


def test_scheme_a_new_database_has_no_queue_mode_columns() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        initialize_schema(conn)
        config_columns = {row[1] for row in conn.execute("PRAGMA table_info(auto_queue_configs)")}
        run_columns = {row[1] for row in conn.execute("PRAGMA table_info(auto_queue_runs)")}
    finally:
        conn.close()

    assert "queue_mode" not in config_columns
    assert "queue_mode" not in run_columns


def test_scheme_a_repositories_tolerate_legacy_queue_mode_columns(tmp_path) -> None:
    database_path = tmp_path / "legacy-auto-queue.db"
    conn = sqlite3.connect(database_path)
    try:
        initialize_schema(conn)
        conn.execute("ALTER TABLE auto_queue_configs ADD COLUMN queue_mode TEXT NOT NULL DEFAULT 'safe'")
        conn.execute("ALTER TABLE auto_queue_runs ADD COLUMN queue_mode TEXT NOT NULL DEFAULT 'safe'")
        conn.commit()
    finally:
        conn.close()

    config_repository = SQLiteAutoQueueConfigRepository(database_path)
    run_repository = SQLiteAutoQueueRunRepository(database_path)
    config_repository.save(models.AutoQueueConfig(config_id="aqc_legacy", work_id="work_legacy"))
    run_repository.save(
        models.AutoQueueRun(
            run_id="aqr_legacy",
            config_id="aqc_legacy",
            work_id="work_legacy",
            multi_chapter_session_id="mcs_legacy",
            status=models.AutoQueueStatus.WAITING_USER_DECISION,
        )
    )

    restored_config = config_repository.get_by_id("aqc_legacy")
    restored_run = run_repository.get_by_id("aqr_legacy")
    assert restored_config is not None
    assert restored_run is not None
    assert "queue_mode" not in restored_config.model_fields
    assert restored_run.status == models.AutoQueueStatus.WAITING_USER_DECISION
