"""
InkTrace后端服务入口

作者：孔利群
"""

# 文件路径：main.py


import os
import sys

import uvicorn

from application.services.logging_service import get_logger
from config import config

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = get_logger(__name__)
logger.info("InkTrace后端服务启动中...")


if __name__ == "__main__":
    uvicorn.run(
        "presentation.api.app:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        use_colors=False,
    )
