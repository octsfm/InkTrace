from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from presentation.api.app import create_app


def verify_runtime_bootstrap() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200, response.text


def main() -> None:
    verify_runtime_bootstrap()
    print("agent_runtime_bootstrap_ok")


if __name__ == "__main__":
    main()
