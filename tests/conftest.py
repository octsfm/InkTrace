import inspect

import pytest

from presentation.api import dependencies
from presentation.api.app import app
from presentation.api.routers import content


def _clear_dependency_caches() -> None:
    for _, value in inspect.getmembers(dependencies):
        cache_clear = getattr(value, "cache_clear", None)
        if callable(cache_clear):
            cache_clear()


def _reset_organize_runtime() -> None:
    for task in list(content.ACTIVE_ORGANIZE_TASKS.values()):
        cancel = getattr(task, "cancel", None)
        done = getattr(task, "done", None)
        if callable(cancel) and callable(done) and not done():
            cancel()
    content.ACTIVE_ORGANIZE_TASKS.clear()
    content.PROGRESS_CACHE.clear()
    content.ORGANIZE_LOCKS.clear()


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
    _reset_organize_runtime()
    _clear_dependency_caches()

    yield

    app.dependency_overrides.clear()
    _reset_organize_runtime()
    _clear_dependency_caches()
