# 文件：模块：main
"""
启动脚本

作者：孔利群
"""

# 文件路径：main.py


import uvicorn
from config import config


if __name__ == "__main__":
    uvicorn.run(
        "presentation.api.app:app",
        host=config.host,
        port=config.port,
        reload=config.debug
    )
