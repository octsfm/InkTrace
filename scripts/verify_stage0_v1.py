from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from application.services.v1.text_metrics import count_effective_characters
from infrastructure.database.v1 import connect, migrate_core_schema, verify_core_schema
from presentation.api.app import create_app
from presentation.api.routers.v1.schemas import ERROR_HTTP_STATUS_MAP


def verify_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "healthy",
        "scope": "workbench",
        "api": "v1",
    }


def verify_database_baseline() -> None:
    with TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "stage0.db"
        conn = connect(db_path)
        migrate_core_schema(conn)
        migrate_core_schema(conn)

        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        schema = verify_core_schema(conn)
        assert {"works", "chapters", "edit_sessions"} == set(schema)
        for table_name in ("works", "chapters", "edit_sessions"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0] == 0

        version_column = next(
            row for row in conn.execute("PRAGMA table_info(chapters)").fetchall()
            if row[1] == "version"
        )
        assert version_column[2].upper() == "INTEGER"
        assert str(version_column[4]) == "1"
        conn.close()


def verify_error_mapping() -> None:
    assert ERROR_HTTP_STATUS_MAP["version_conflict"] == 409
    assert ERROR_HTTP_STATUS_MAP["asset_version_conflict"] == 409
    assert ERROR_HTTP_STATUS_MAP["work_not_found"] == 404
    assert ERROR_HTTP_STATUS_MAP["chapter_not_found"] == 404
    assert ERROR_HTTP_STATUS_MAP["asset_not_found"] == 404
    assert ERROR_HTTP_STATUS_MAP["invalid_input"] == 400


def verify_text_metrics() -> None:
    assert count_effective_characters("你 好\nInk\tTrace") == 10
    assert count_effective_characters("") == 0
    assert count_effective_characters(None) == 0


def main() -> None:
    verify_health_endpoint()
    verify_database_baseline()
    verify_error_mapping()
    verify_text_metrics()
    print("stage0_v1_baseline_ok")


if __name__ == "__main__":
    main()
