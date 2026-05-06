"""Runtime database schema delegates to the V1.1 Workbench schema source."""

from __future__ import annotations

import sqlite3

from infrastructure.database.v1.models import (
    CORE_TABLES,
    INDEX_STATEMENTS,
    migrate_core_schema,
    verify_core_schema,
)


def initialize_schema(conn: sqlite3.Connection) -> None:
    migrate_core_schema(conn)


__all__ = [
    "CORE_TABLES",
    "INDEX_STATEMENTS",
    "initialize_schema",
    "migrate_core_schema",
    "verify_core_schema",
]
