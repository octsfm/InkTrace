import json
import os
import sqlite3
from datetime import datetime


class _SQLiteRepoSupport:
    def __init__(self, db_path: str):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = {row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in rows}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def _json_dumps(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _json_loads(self, value: str, default):
        try:
            data = json.loads(value or "")
        except Exception:
            return default
        return data if isinstance(data, type(default)) else default

    def _dt(self, value: str):
        return datetime.fromisoformat(value) if value else datetime.now()
