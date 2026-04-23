from __future__ import annotations

import contextvars
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

from domain.utils import is_probably_garbled_message


_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
_logging_inited = False
_FORMAT = "%(asctime)s %(levelname)s %(name)s event=%(event)s request_id=%(request_id)s message=%(message)s"
_RESERVED_KEYS = set(logging.LogRecord("x", logging.INFO, "", 0, "", (), None).__dict__.keys())
_SUPPRESS_PROGRESS_POLL = str(os.getenv("INKTRACE_LOG_SUPPRESS_PROGRESS_POLL", "1")).strip().lower() not in {"0", "false"}


class _SafeExtraFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "event"):
            record.event = ""
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_ctx.get("")
        if not hasattr(record, "message"):
            record.message = record.getMessage()
        return super().format(record)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_ctx.get("")
        if not hasattr(record, "event"):
            record.event = ""
        return True


class _MessageEncodingGuardFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = str(getattr(record, "msg", "") or "")
        if is_probably_garbled_message(message):
            record.msg = "[garbled_message]"
            record.args = ()
        return True


class _UvicornAccessNoiseFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not _SUPPRESS_PROGRESS_POLL:
            return True
        try:
            args = getattr(record, "args", ()) or ()
            method = str(args[1] if len(args) > 1 else "")
            path = str(args[2] if len(args) > 2 else "")
            status = int(args[4]) if len(args) > 4 else 200
            if method.upper() == "GET" and path.startswith("/api/content/organize/progress/") and status < 400:
                return False
        except Exception:
            return True
        return True


def set_request_id(request_id: str) -> contextvars.Token:
    return _request_id_ctx.set(str(request_id or ""))


def reset_request_id(token: contextvars.Token) -> None:
    _request_id_ctx.reset(token)


def build_log_context(**kwargs: Any) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "event": str(kwargs.pop("event", "") or ""),
        "request_id": str(kwargs.pop("request_id", "") or _request_id_ctx.get("")),
    }
    for key, value in kwargs.items():
        safe_key = key if key not in _RESERVED_KEYS else f"ctx_{key}"
        context[safe_key] = value
    return context


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging() -> None:
    global _logging_inited
    if _logging_inited:
        return
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = _SafeExtraFormatter(_FORMAT)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    request_filter = _RequestIdFilter()
    encoding_guard_filter = _MessageEncodingGuardFilter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_filter)
    console_handler.addFilter(encoding_guard_filter)

    info_file = RotatingFileHandler(logs_dir / "backend.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    info_file.setLevel(logging.INFO)
    info_file.setFormatter(formatter)
    info_file.addFilter(request_filter)
    info_file.addFilter(encoding_guard_filter)

    error_file = RotatingFileHandler(logs_dir / "backend-error.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(formatter)
    error_file.addFilter(request_filter)
    error_file.addFilter(encoding_guard_filter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(info_file)
    root_logger.addHandler(error_file)
    access_logger = logging.getLogger("uvicorn.access")
    access_filter = _UvicornAccessNoiseFilter()
    for handler in access_logger.handlers:
        handler.addFilter(access_filter)
    access_logger.addFilter(access_filter)

    os.environ["INKTRACE_LOG_DIR"] = str(logs_dir.resolve())
    _logging_inited = True
