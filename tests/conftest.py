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
def isolate_app_runtime(tmp_path, monkeypatch, request):
    runtime_dir = tmp_path / "runtime"
    db_path = runtime_dir / "inktrace.db"
    chroma_dir = runtime_dir / "chroma"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("INKTRACE_DB_PATH", str(db_path))
    monkeypatch.setenv("INKTRACE_CHROMA_DIR", str(chroma_dir))
    monkeypatch.setenv("INKTRACE_ENABLE_FAKE_PROVIDER", "1")
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
    settings_isolation_tests = {
        "test_ai_settings_api.py",
        "test_model_router.py",
        "test_real_provider.py",
    }
    if request.node.path.name not in settings_isolation_tests:
        analysis_roles = [
            "analysis",
            "planning",
            "outline_analyzer",
            "manuscript_analyzer",
            "memory_extractor",
            "style_extractor",
            "planner",
            "writing_task_builder",
            "opening_strategy_planner",
        ]
        writer_roles = [
            "writer",
            "rewriter",
            "quick_trial_writer",
            "opening_writer",
            "polisher",
            "dialogue_writer",
            "scene_generator",
        ]
        mappings = {
            **{role: {"provider_name": "fake", "model_name": "fake-chat"} for role in analysis_roles},
            **{role: {"provider_name": "fake", "model_name": "fake-writer"} for role in writer_roles},
            "reviewer": {"provider_name": "fake", "model_name": "fake-review"},
            "opening_risk_checker": {"provider_name": "fake", "model_name": "fake-review"},
        }
        db_path.with_name("ai_settings.json").write_text(
            json.dumps(
                {
                    "provider_configs": {
                        "fake": {
                            "provider_name": "fake",
                            "enabled": True,
                            "encrypted_api_key": "test-fake-key",
                            "default_model": "fake-chat",
                        }
                    },
                    "model_role_mappings": mappings,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    yield

    app.dependency_overrides.clear()
    _clear_dependency_caches()
