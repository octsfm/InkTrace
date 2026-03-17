# 文件：模块：__init__
"""
数据传输对象模块

作者：孔利群
"""

# 文件路径：application/dto/__init__.py


from application.dto.request_dto import (
    BaseRequest,
    CreateNovelRequest,
    ImportNovelRequest,
    AnalyzeNovelRequest,
    GenerateChapterRequest,
    PlanPlotRequest,
    ExportNovelRequest,
    UpdateChapterRequest,
    CreateCharacterRequest
)
from application.dto.response_dto import (
    BaseResponse,
    NovelResponse,
    ChapterResponse,
    CharacterResponse,
    StyleAnalysisResponse,
    PlotAnalysisResponse,
    ConsistencyCheckResponse,
    GenerateChapterResponse,
    ExportResponse,
    ErrorResponse,
    PagedResponse
)

__all__ = [
    'BaseRequest',
    'CreateNovelRequest',
    'ImportNovelRequest',
    'AnalyzeNovelRequest',
    'GenerateChapterRequest',
    'PlanPlotRequest',
    'ExportNovelRequest',
    'UpdateChapterRequest',
    'CreateCharacterRequest',
    'BaseResponse',
    'NovelResponse',
    'ChapterResponse',
    'CharacterResponse',
    'StyleAnalysisResponse',
    'PlotAnalysisResponse',
    'ConsistencyCheckResponse',
    'GenerateChapterResponse',
    'ErrorResponse',
    'PagedResponse'
]
