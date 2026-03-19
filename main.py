"""
InkTrace后端服务入口

作者：孔利群
"""

# 文件路径：main.py


import os
import logging
import uvicorn
from config import config

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'app.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("InkTrace后端服务启动中...")


if __name__ == "__main__":
    uvicorn.run(
        "presentation.api.app:app",
        host=config.host,
        port=config.port,
        reload=config.debug
    )
