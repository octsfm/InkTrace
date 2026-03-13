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
from domain.repositories.project_repository import IProjectRepository
from domain.repositories.template_repository import ITemplateRepository
from domain.repositories.worldview_repository import IWorldviewRepository
from domain.repositories.vector_repository import IVectorRepository
from infrastructure.persistence.sqlite_novel_repo import SQLiteNovelRepository
from infrastructure.persistence.sqlite_chapter_repo import SQLiteChapterRepository
from infrastructure.persistence.sqlite_character_repo import SQLiteCharacterRepository
from infrastructure.persistence.sqlite_outline_repo import SQLiteOutlineRepository
from infrastructure.persistence.sqlite_project_repo import SQLiteProjectRepository
from infrastructure.persistence.sqlite_template_repo import SQLiteTemplateRepository
from infrastructure.persistence.sqlite_worldview_repo import SQLiteWorldviewRepository
from infrastructure.persistence.chromadb_vector_repo import ChromaDBVectorRepository
from infrastructure.file.txt_parser import TxtParser
from infrastructure.llm.llm_factory import LLMFactory, LLMConfig
from domain.services.worldview_checker import WorldviewChecker
from domain.services.rag_context_builder import RAGContextBuilder
from application.services.project_service import ProjectService
from application.services.content_service import ContentService
from application.services.writing_service import WritingService
from application.services.export_service import ExportService
from application.services.template_service import TemplateService
from application.services.character_service import CharacterService
from application.services.worldview_service import WorldviewService
from application.services.vector_index_service import VectorIndexService
from application.services.rag_retrieval_service import RAGRetrievalService


DB_PATH = os.environ.get("INKTRACE_DB_PATH", "data/inktrace.db")
TEMPLATES_DIR = os.environ.get("INKTRACE_TEMPLATES_DIR", "infrastructure/templates")
CHROMA_DIR = os.environ.get("INKTRACE_CHROMA_DIR", "data/chroma")


@lru_cache()
def get_novel_repo() -> INovelRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteNovelRepository(DB_PATH)


@lru_cache()
def get_chapter_repo() -> IChapterRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteChapterRepository(DB_PATH)


@lru_cache()
def get_character_repo() -> ICharacterRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteCharacterRepository(DB_PATH)


@lru_cache()
def get_outline_repo() -> IOutlineRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteOutlineRepository(DB_PATH)


@lru_cache()
def get_project_repo() -> IProjectRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteProjectRepository(DB_PATH)


@lru_cache()
def get_template_repo() -> ITemplateRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteTemplateRepository(DB_PATH, TEMPLATES_DIR)


@lru_cache()
def get_worldview_repo() -> IWorldviewRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteWorldviewRepository(DB_PATH)


@lru_cache()
def get_vector_repo() -> IVectorRepository:
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return ChromaDBVectorRepository(CHROMA_DIR)


@lru_cache()
def get_txt_parser() -> TxtParser:
    return TxtParser()


@lru_cache()
def get_llm_factory() -> LLMFactory:
    config = LLMConfig(
        deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        kimi_api_key=os.environ.get("KIMI_API_KEY", "")
    )
    return LLMFactory(config)


@lru_cache()
def get_worldview_checker() -> WorldviewChecker:
    return WorldviewChecker()


@lru_cache()
def get_rag_context_builder() -> RAGContextBuilder:
    return RAGContextBuilder()


def get_project_service() -> ProjectService:
    return ProjectService(get_project_repo(), get_novel_repo())


def get_content_service() -> ContentService:
    return ContentService(
        get_novel_repo(),
        get_chapter_repo(),
        get_character_repo(),
        get_outline_repo(),
        get_txt_parser()
    )


def get_writing_service() -> WritingService:
    return WritingService(
        get_novel_repo(),
        get_chapter_repo(),
        get_llm_factory()
    )


def get_export_service() -> ExportService:
    return ExportService(
        get_novel_repo(),
        get_chapter_repo()
    )


def get_template_service() -> TemplateService:
    return TemplateService(get_template_repo(), get_project_repo())


def get_character_service() -> CharacterService:
    return CharacterService(get_character_repo())


def get_worldview_service() -> WorldviewService:
    return WorldviewService(get_worldview_repo(), get_worldview_checker())


def get_vector_index_service() -> VectorIndexService:
    return VectorIndexService(
        get_vector_repo(),
        get_chapter_repo(),
        get_character_repo(),
        get_worldview_repo()
    )


def get_rag_retrieval_service() -> RAGRetrievalService:
    return RAGRetrievalService(
        get_vector_repo(),
        get_chapter_repo(),
        get_character_repo()
    )
