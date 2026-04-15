from __future__ import annotations

import sqlite3
from typing import Optional


def connect_sqlite(db_path: str, *, row_factory: Optional[object] = None) -> sqlite3.Connection:
    # Use timeout to avoid immediate SQLITE_BUSY under concurrent access.
    conn = sqlite3.connect(db_path, timeout=10.0)
    # Ensure SQLite waits for locks instead of failing/looping hot.
    conn.execute("PRAGMA busy_timeout=10000")
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn
