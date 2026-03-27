from __future__ import annotations

import importlib
import logging
from pathlib import Path


def test_setup_logging_creates_handlers_and_logs_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("application.services.logging_service")
    module = importlib.reload(module)

    module.setup_logging()

    logs_dir = Path(tmp_path) / "logs"
    assert logs_dir.exists()
    assert (logs_dir / "backend.log").exists()
    assert (logs_dir / "backend-error.log").exists()

    handlers = logging.getLogger().handlers
    assert len(handlers) >= 3

    logger = module.get_logger("test.logging")
    logger.info("test", extra=module.build_log_context(event="unit_test"))
