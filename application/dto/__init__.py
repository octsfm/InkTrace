"""
数据传输对象模块

作者：孔利群
"""

from application.dto.request_dto import (
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
    'CreateNovelRequest',
    'ImportNovelRequest',
    'AnalyzeNovelRequest',
    'GenerateChapterRequest',
    'PlanPlotRequest',
    'ExportNovelRequest',
    'UpdateChapterRequest',
    'CreateCharacterRequest',
    'NovelResponse',
    'ChapterResponse',
    'CharacterResponse',
    'StyleAnalysisResponse',
    'PlotAnalysisResponse',
    'ConsistencyCheckResponse',
    'GenerateChapterResponse',
    'ExportResponse',
    'ErrorResponse',
    'PagedResponse'
]
