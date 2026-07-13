import inspect
import json

import pytest

from presentation.api import dependencies
from presentation.api.app import app


def _clear_dependency_caches() -> None:
    for _, value in inspect.getmembers(dependencies):
        cache_clear = getattr(value, "cache_clear", None)
        if callable(cache_clear):
            cache_clear()


@pytest.fixture(autouse=True)
def isolate_app_runtime(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime"
    db_path = runtime_dir / "inktrace.db"
    chroma_dir = runtime_dir / "chroma"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    monkeypatch.setenv("INKTRACE_CHROMA_DIR", str(chroma_dir))
    monkeypatch.setattr(dependencies, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(dependencies, "CHROMA_DIR", str(chroma_dir), raising=False)

    app.dependency_overrides.clear()
    _clear_dependency_caches()
    # API tests exercise feature behavior directly; explicitly enable author
    # preferences so production defaults can remain safely off.
    from application.services.ai.feature_capability_service import FEATURE_DEFINITIONS
    db_path.with_name("feature_preferences.json").write_text(
        json.dumps({"preferences": {item.feature_key: True for item in FEATURE_DEFINITIONS}, "receipts": {}}),
        encoding="utf-8",
    )

    yield

    app.dependency_overrides.clear()
    _clear_dependency_caches()
