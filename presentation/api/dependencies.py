"""
API依赖注入模块

作者：孔利群
"""

# 文件路径：presentation/api/dependencies.py


from functools import lru_cache
import os
import logging

from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.character_repository import ICharacterRepository
from domain.repositories.outline_repository import IOutlineRepository
from domain.repositories.project_repository import IProjectRepository
from domain.repositories.organize_job_repository import IOrganizeJobRepository
from domain.repositories.template_repository import ITemplateRepository
from domain.repositories.worldview_repository import IWorldviewRepository
from domain.repositories.vector_repository import IVectorRepository
from domain.repositories.llm_config_repository import ILLMConfigRepository
from infrastructure.persistence.sqlite_novel_repo import SQLiteNovelRepository
from infrastructure.persistence.sqlite_chapter_repo import SQLiteChapterRepository
from infrastructure.persistence.sqlite_character_repo import SQLiteCharacterRepository
from infrastructure.persistence.sqlite_outline_repo import SQLiteOutlineRepository
from infrastructure.persistence.sqlite_project_repo import SQLiteProjectRepository
from infrastructure.persistence.sqlite_organize_job_repo import SQLiteOrganizeJobRepository
from infrastructure.persistence.sqlite_template_repo import SQLiteTemplateRepository
from infrastructure.persistence.sqlite_worldview_repo import SQLiteWorldviewRepository
from infrastructure.persistence.chromadb_vector_repo import ChromaDBVectorRepository
from infrastructure.persistence.sqlite_llm_config_repo import SQLiteLLMConfigRepository
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
from application.services.config_service import ConfigService


DB_PATH = os.environ.get("INKTRACE_DB_PATH", "data/inktrace.db")
TEMPLATES_DIR = os.environ.get("INKTRACE_TEMPLATES_DIR", "infrastructure/templates")
CHROMA_DIR = os.environ.get("INKTRACE_CHROMA_DIR", "data/chroma")

ENCRYPTION_KEY = b"inktrace_default_encryption_key_32bytes!"[:32]


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
def get_organize_job_repo() -> IOrganizeJobRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteOrganizeJobRepository(DB_PATH)


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
def get_llm_config_repo() -> ILLMConfigRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteLLMConfigRepository(DB_PATH)


@lru_cache()
def get_txt_parser() -> TxtParser:
    return TxtParser()


@lru_cache()
def get_config_service() -> ConfigService:
    return ConfigService(get_llm_config_repo(), ENCRYPTION_KEY)


def _get_api_keys() -> tuple:
    """
    获取API密钥
    
    优先从数据库读取，环境变量作为fallback
    
    Returns:
        (deepseek_api_key, kimi_api_key)
    """
    logger = logging.getLogger(__name__)
    config_service = get_config_service()
    
    try:
        decrypted = config_service.get_decrypted_config()
        if decrypted:
            deepseek_key, kimi_key = decrypted
            logger.info(f"[API Keys] 从数据库获取成功, DeepSeek前4位: {deepseek_key[:4] if deepseek_key else 'N/A'}, Kimi前4位: {kimi_key[:4] if kimi_key else 'N/A'}")
            return deepseek_key, kimi_key
    except Exception as e:
        logger.warning(f"[API Keys] 从数据库获取失败: {e}")
    
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    kimi_key = os.environ.get("KIMI_API_KEY", "")
    logger.info(f"[API Keys] 从环境变量获取, DeepSeek前4位: {deepseek_key[:4] if deepseek_key else 'N/A'}, Kimi前4位: {kimi_key[:4] if kimi_key else 'N/A'}")
    
    return deepseek_key, kimi_key


def get_llm_factory() -> LLMFactory:
    logger = logging.getLogger(__name__)
    deepseek_key, kimi_key = _get_api_keys()
    
    logger.info(f"[LLM Factory] 创建LLMFactory, DeepSeek Key长度: {len(deepseek_key)}, Kimi Key长度: {len(kimi_key)}")
    
    config = LLMConfig(
        deepseek_api_key=deepseek_key,
        kimi_api_key=kimi_key
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
