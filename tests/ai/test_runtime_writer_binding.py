from __future__ import annotations

from infrastructure.database.session import get_database_path
from presentation.api import dependencies


def _reset_runtime_dependencies() -> None:
    get_database_path.cache_clear()
    dependencies.get_ai_settings_repository.cache_clear()
    dependencies.get_llm_call_log_repository.cache_clear()
    dependencies.get_settings_cipher.cache_clear()
    dependencies.get_provider_registry.cache_clear()
    dependencies.get_model_router.cache_clear()
    dependencies.get_core_tool_facade.cache_clear()


def test_runtime_core_tool_facade_uses_model_router_writer(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKTRACE_DB_PATH", str(tmp_path / "runtime" / "inktrace.db"))
    _reset_runtime_dependencies()

    tool_facade = dependencies.get_core_tool_facade()

    assert type(tool_facade._writer_service._writer).__name__ == "ModelRouterWriter"  # noqa: SLF001

