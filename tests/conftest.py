import inspect

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

    yield

    app.dependency_overrides.clear()
    _clear_dependency_caches()
