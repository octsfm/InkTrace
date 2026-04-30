"""V1.1 Workbench database connection baseline.

Stage 0 only defines connection behavior. Business repositories and writes are
introduced in later stages.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = Path("data") / "inktrace.db"
BUSY_TIMEOUT_MS = 5000


def resolve_database_path(db_path: Optional[str | Path] = None) -> Path:
    """Resolve the V1.1 database path without creating business data."""
    raw_path = db_path or os.getenv("INKTRACE_DB_PATH", str(DEFAULT_DB_PATH))
    return Path(raw_path).expanduser().resolve()


def connect(
    db_path: Optional[str | Path] = None,
    *,
    row_factory: Optional[object] = sqlite3.Row,
) -> sqlite3.Connection:
    """Create a SQLite connection with the V1.1 baseline PRAGMA settings."""
    resolved_path = resolve_database_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(resolved_path))
    conn.row_factory = row_factory
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
