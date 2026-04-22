from __future__ import annotations

import sqlite3
import threading
import time
from typing import Optional

from application.services.logging_service import build_log_context, get_logger

logger = get_logger(__name__)
_metrics_lock = threading.Lock()
_sqlite_metrics = {
    "connections_total": 0,
    "statements_total": 0,
    "slow_statements_total": 0,
    "lock_wait_suspected_total": 0,
    "locked_errors_total": 0,
}
_SLOW_SQL_MS = 200
_LOCK_WAIT_SUSPECT_MS = 600


def _record_sql_metric(key: str, delta: int = 1) -> None:
    with _metrics_lock:
        _sqlite_metrics[key] = int(_sqlite_metrics.get(key, 0)) + int(delta)


def get_sqlite_metrics_snapshot() -> dict:
    with _metrics_lock:
        return dict(_sqlite_metrics)


def _is_write_sql(sql: str) -> bool:
    normalized = str(sql or "").strip().lower()
    return normalized.startswith(("insert", "update", "delete", "replace", "create", "alter", "drop"))


class ObservedSQLiteConnection(sqlite3.Connection):
    def _observe_success(self, sql: str, started_at: float) -> None:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        _record_sql_metric("statements_total")
        if duration_ms >= _SLOW_SQL_MS:
            _record_sql_metric("slow_statements_total")
            logger.warning(
                "检测到慢SQL",
                extra=build_log_context(
                    event="sqlite_slow_statement",
                    duration_ms=duration_ms,
                    sql_preview=str(sql or "")[:120],
                ),
            )
        if _is_write_sql(sql) and duration_ms >= _LOCK_WAIT_SUSPECT_MS:
            _record_sql_metric("lock_wait_suspected_total")
            logger.warning(
                "检测到疑似锁等待",
                extra=build_log_context(
                    event="sqlite_lock_wait_suspected",
                    duration_ms=duration_ms,
                    sql_preview=str(sql or "")[:120],
                ),
            )

    def _observe_error(self, sql: str, exc: Exception) -> None:
        if "locked" in str(exc).lower():
            _record_sql_metric("locked_errors_total")
            logger.error(
                "SQLite锁冲突",
                extra=build_log_context(
                    event="sqlite_locked_error",
                    sql_preview=str(sql or "")[:120],
                    error=str(exc),
                ),
            )

    def execute(self, sql, parameters=(), /):
        started_at = time.perf_counter()
        try:
            result = super().execute(sql, parameters)
            self._observe_success(str(sql), started_at)
            return result
        except Exception as exc:
            self._observe_error(str(sql), exc)
            raise

    def executemany(self, sql, seq_of_parameters, /):
        started_at = time.perf_counter()
        try:
            result = super().executemany(sql, seq_of_parameters)
            self._observe_success(str(sql), started_at)
            return result
        except Exception as exc:
            self._observe_error(str(sql), exc)
            raise

    def executescript(self, sql_script, /):
        started_at = time.perf_counter()
        try:
            result = super().executescript(sql_script)
            self._observe_success(str(sql_script), started_at)
            return result
        except Exception as exc:
            self._observe_error(str(sql_script), exc)
            raise


def connect_sqlite(db_path: str, *, row_factory: Optional[object] = None) -> sqlite3.Connection:
    # Use timeout to avoid immediate SQLITE_BUSY under concurrent access.
    conn = sqlite3.connect(db_path, timeout=10.0, factory=ObservedSQLiteConnection)
    _record_sql_metric("connections_total")
    # Better concurrent read/write behavior.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    # Ensure SQLite waits for locks instead of failing/looping hot.
    conn.execute("PRAGMA busy_timeout=10000")
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn
