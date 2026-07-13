from __future__ import annotations

from pathlib import Path

from domain.entities.ai.models import AutoQueueConfig
from domain.repositories.ai.auto_queue_config_repository import AutoQueueConfigRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class SQLiteAutoQueueConfigRepository(AutoQueueConfigRepository):
    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def save(self, config: AutoQueueConfig) -> AutoQueueConfig:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            conn.execute(
                """
                INSERT INTO auto_queue_configs (
                    config_id, work_id, target_chapters, target_word_count,
                    stop_at_sequence_end, stop_on_blocking_review, max_consecutive_blocking,
                    stop_on_budget_exceeded, stop_on_foreshadow_premature,
                    max_consecutive_revision_failures, budget_limit_tokens,
                    enabled, created_at, updated_at
                    ,revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(config_id) DO UPDATE SET
                    work_id = excluded.work_id,
                    target_chapters = excluded.target_chapters,
                    target_word_count = excluded.target_word_count,
                    stop_at_sequence_end = excluded.stop_at_sequence_end,
                    stop_on_blocking_review = excluded.stop_on_blocking_review,
                    max_consecutive_blocking = excluded.max_consecutive_blocking,
                    stop_on_budget_exceeded = excluded.stop_on_budget_exceeded,
                    stop_on_foreshadow_premature = excluded.stop_on_foreshadow_premature,
                    max_consecutive_revision_failures = excluded.max_consecutive_revision_failures,
                    budget_limit_tokens = excluded.budget_limit_tokens,
                    enabled = excluded.enabled,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                    ,revision = excluded.revision
                """,
                self._params(config),
            )
            conn.commit()
            return config
        finally:
            conn.close()

    def get_by_work(self, work_id: str) -> AutoQueueConfig | None:
        items = self._query("SELECT * FROM auto_queue_configs WHERE work_id = ?", (work_id,))
        return items[0] if items else None

    def get_by_id(self, config_id: str) -> AutoQueueConfig | None:
        items = self._query("SELECT * FROM auto_queue_configs WHERE config_id = ?", (config_id,))
        return items[0] if items else None

    def update(self, config: AutoQueueConfig) -> AutoQueueConfig:
        return self.save(config)

    def _query(self, sql: str, params: tuple[object, ...]) -> list[AutoQueueConfig]:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(sql, params).fetchall()
            return [
                AutoQueueConfig(
                    config_id=row["config_id"],
                    work_id=row["work_id"],
                    target_chapters=int(row["target_chapters"] or 0),
                    target_word_count=int(row["target_word_count"] or 0),
                    stop_at_sequence_end=bool(row["stop_at_sequence_end"]),
                    stop_on_blocking_review=bool(row["stop_on_blocking_review"]),
                    max_consecutive_blocking=int(row["max_consecutive_blocking"] or 0),
                    stop_on_budget_exceeded=bool(row["stop_on_budget_exceeded"]),
                    stop_on_foreshadow_premature=bool(row["stop_on_foreshadow_premature"]),
                    max_consecutive_revision_failures=int(row["max_consecutive_revision_failures"] or 0),
                    budget_limit_tokens=int(row["budget_limit_tokens"] or 0),
                    enabled=bool(row["enabled"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    revision=int(row["revision"] or 1),
                )
                for row in rows
            ]
        finally:
            conn.close()

    def _params(self, config: AutoQueueConfig) -> tuple[object, ...]:
        return (
            config.config_id,
            config.work_id,
            config.target_chapters,
            config.target_word_count,
            int(config.stop_at_sequence_end),
            int(config.stop_on_blocking_review),
            config.max_consecutive_blocking,
            int(config.stop_on_budget_exceeded),
            int(config.stop_on_foreshadow_premature),
            config.max_consecutive_revision_failures,
            config.budget_limit_tokens,
            int(config.enabled),
            config.created_at,
            config.updated_at,
            config.revision,
        )
