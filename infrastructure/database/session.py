from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from infrastructure.database.models import initialize_schema
from infrastructure.persistence.sqlite_utils import connect_sqlite


DEFAULT_DB_PATH = Path("data") / "inktrace.db"


def get_database_path() -> Path:
    raw_path = os.getenv("INKTRACE_DB_PATH", str(DEFAULT_DB_PATH))
    return Path(raw_path).expanduser().resolve()


def _clear_database_path_cache() -> None:
    return None


get_database_path.cache_clear = _clear_database_path_cache  # type: ignore[attr-defined]


def ensure_database_directory(db_path: Optional[Path] = None) -> Path:
    path = Path(db_path or get_database_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def create_connection(*, row_factory: Optional[object] = sqlite3.Row) -> sqlite3.Connection:
    db_path = ensure_database_directory()
    conn = connect_sqlite(str(db_path), row_factory=row_factory)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_connection(*, row_factory: Optional[object] = sqlite3.Row) -> Iterator[sqlite3.Connection]:
    conn = create_connection(row_factory=row_factory)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database() -> Path:
    db_path = ensure_database_directory()
    with create_connection(row_factory=sqlite3.Row) as conn:
        initialize_schema(conn)
    return db_path
