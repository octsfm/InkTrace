"""
API依赖注入模块

作者：孔利群
"""

from functools import lru_cache
import os

from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.character_repository import ICharacterRepository
from domain.repositories.outline_repository import IOutlineRepository
from infrastructure.persistence.sqlite_novel_repo import SQLiteNovelRepository
from infrastructure.persistence.sqlite_chapter_repo import SQLiteChapterRepository
from infrastructure.persistence.sqlite_character_repo import SQLiteCharacterRepository
from infrastructure.persistence.sqlite_outline_repo import SQLiteOutlineRepository
from infrastructure.file.txt_parser import TxtParser
from infrastructure.llm.llm_factory import LLMFactory, LLMConfig
from application.services.project_service import ProjectService
from application.services.content_service import ContentService
from application.services.writing_service import WritingService
from application.services.export_service import ExportService


DB_PATH = os.environ.get("INKTRACE_DB_PATH", "data/inktrace.db")


@lru_cache()
def get_novel_repo() -> INovelRepository:
    """获取小说仓储"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteNovelRepository(DB_PATH)


@lru_cache()
def get_chapter_repo() -> IChapterRepository:
    """获取章节仓储"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteChapterRepository(DB_PATH)


@lru_cache()
def get_character_repo() -> ICharacterRepository:
    """获取人物仓储"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteCharacterRepository(DB_PATH)


@lru_cache()
def get_outline_repo() -> IOutlineRepository:
    """获取大纲仓储"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteOutlineRepository(DB_PATH)


@lru_cache()
def get_txt_parser() -> TxtParser:
    """获取TXT解析器"""
    return TxtParser()


@lru_cache()
def get_llm_factory() -> LLMFactory:
    """获取LLM工厂"""
    config = LLMConfig(
        deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        kimi_api_key=os.environ.get("KIMI_API_KEY", "")
    )
    return LLMFactory(config)


def get_project_service() -> ProjectService:
    """获取项目服务"""
    return ProjectService(get_novel_repo())


def get_content_service() -> ContentService:
    """获取内容服务"""
    return ContentService(
        get_novel_repo(),
        get_chapter_repo(),
        get_character_repo(),
        get_outline_repo(),
        get_txt_parser()
    )


def get_writing_service() -> WritingService:
    """获取续写服务"""
    return WritingService(
        get_novel_repo(),
        get_chapter_repo(),
        get_llm_factory()
    )


def get_export_service() -> ExportService:
    """获取导出服务"""
    return ExportService(
        get_novel_repo(),
        get_chapter_repo()
    )
