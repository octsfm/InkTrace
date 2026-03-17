# 文件：模块：__init__
"""
API模块

作者：孔利群
"""

# 文件路径：presentation/api/__init__.py


from presentation.api.app import app, create_app
from presentation.api.dependencies import (
    get_novel_repo,
    get_chapter_repo,
    get_project_service,
    get_content_service,
    get_writing_service,
    get_export_service
)

__all__ = [
    'app',
    'create_app',
    'get_novel_repo',
    'get_chapter_repo',
    'get_project_service',
    'get_content_service',
    'get_writing_service',
    'get_export_service'
]
