from __future__ import annotations

import os
from pathlib import Path


DB_PATH = os.getenv("INKTRACE_DB_PATH", str(Path("data") / "inktrace.db"))
CHROMA_DIR = os.getenv("INKTRACE_CHROMA_DIR", str(Path("data") / "chroma"))


def warmup_singletons_for_startup() -> None:
    return None
