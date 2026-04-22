from __future__ import annotations

import importlib
import logging
from pathlib import Path


def test_encoding_guard_keeps_normal_message():
    module = importlib.import_module("application.services.logging_service")
    module = importlib.reload(module)
    guard = module._MessageEncodingGuardFilter()
    record = logging.LogRecord(
        name="unit",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="chapter analysis finished",
        args=(),
        exc_info=None,
    )
    assert guard.filter(record) is True
    assert record.msg == "chapter analysis finished"


def test_encoding_guard_replaces_garbled_message():
    module = importlib.import_module("application.services.logging_service")
    module = importlib.reload(module)
    guard = module._MessageEncodingGuardFilter()
    record = logging.LogRecord(
        name="unit",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="绔犺妭鍒嗘瀽瀹屾垚",
        args=(),
        exc_info=None,
    )
    assert guard.filter(record) is True
    assert record.msg == "[garbled_message]"


def test_encoding_guard_preserves_event_searchability(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("application.services.logging_service")
    module = importlib.reload(module)
    module.setup_logging()

    logger = module.get_logger("unit.logging.guard")
    logger.info("绔犺妭鍒嗘瀽瀹屾垚", extra=module.build_log_context(event="chapter_analysis_finished", request_id="req-1"))

    for handler in logging.getLogger().handlers:
        if hasattr(handler, "flush"):
            handler.flush()

    log_text = (Path(tmp_path) / "logs" / "backend.log").read_text(encoding="utf-8")
    assert "event=chapter_analysis_finished" in log_text
    assert "[garbled_message]" in log_text
