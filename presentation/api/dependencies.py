"""
API dependency injection helpers.
"""

from functools import lru_cache
import os

from application.services.logging_service import build_log_context, get_logger
from domain.repositories.novel_repository import INovelRepository
from domain.repositories.chapter_repository import IChapterRepository
from domain.repositories.character_repository import ICharacterRepository
from domain.repositories.outline_repository import IOutlineRepository
from domain.repositories.project_repository import IProjectRepository
from domain.repositories.organize_job_repository import IOrganizeJobRepository
from domain.repositories.chapter_outline_repository import IChapterOutlineRepository
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
from infrastructure.persistence.sqlite_chapter_outline_repo import SQLiteChapterOutlineRepository
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
from application.services.v2_workflow_service import V2WorkflowService
from application.services.chapter_ai_service import ChapterAIService
from infrastructure.persistence.sqlite_v2_repo import SQLiteV2Repository


DB_PATH = os.environ.get("INKTRACE_DB_PATH", "data/inktrace.db")
TEMPLATES_DIR = os.environ.get("INKTRACE_TEMPLATES_DIR", "infrastructure/templates")
CHROMA_DIR = os.environ.get("INKTRACE_CHROMA_DIR", "data/chroma")

ENCRYPTION_KEY = b"inktrace_default_encryption_key_32bytes!"[:32]
logger = get_logger(__name__)


@lru_cache()
def get_novel_repo() -> INovelRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    logger.info("仓储初始化", extra=build_log_context(event="repo_initialized", repo="novel", db_path=DB_PATH))
    return SQLiteNovelRepository(DB_PATH)


@lru_cache()
def get_chapter_repo() -> IChapterRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    logger.info("仓储初始化", extra=build_log_context(event="repo_initialized", repo="chapter", db_path=DB_PATH))
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
    logger.info("仓储初始化", extra=build_log_context(event="repo_initialized", repo="project", db_path=DB_PATH))
    return SQLiteProjectRepository(DB_PATH)


@lru_cache()
def get_organize_job_repo() -> IOrganizeJobRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    logger.info("仓储初始化", extra=build_log_context(event="repo_initialized", repo="organize_job", db_path=DB_PATH))
    return SQLiteOrganizeJobRepository(DB_PATH)


@lru_cache()
def get_chapter_outline_repo() -> IChapterOutlineRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteChapterOutlineRepository(DB_PATH)


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
    logger.info("向量仓储初始化", extra=build_log_context(event="repo_initialized", repo="vector", chroma_dir=CHROMA_DIR))
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


def _get_api_keys() -> tuple[str, str]:
    """
    Only read API credentials from the persisted database config.
    """
    config_service = get_config_service()

    try:
        decrypted = config_service.get_decrypted_config()
        if decrypted:
            deepseek_key, kimi_key = decrypted
            logger.info(
                "LLM配置已加载",
                extra=build_log_context(
                    event="llm_config_loaded",
                    has_deepseek_key=bool(deepseek_key),
                    has_kimi_key=bool(kimi_key),
                ),
            )
            return deepseek_key, kimi_key
    except Exception as exc:
        logger.warning(
            "依赖初始化失败",
            extra=build_log_context(event="dependency_init_failed", dependency="api_keys", error=str(exc)),
        )

    logger.warning(
        "LLM配置缺失",
        extra=build_log_context(event="llm_config_missing", has_deepseek_key=False, has_kimi_key=False),
    )
    return "", ""


def get_llm_factory() -> LLMFactory:
    deepseek_key, kimi_key = _get_api_keys()
    logger.info(
        "创建LLM工厂",
        extra=build_log_context(
            event="llm_factory_created",
            has_deepseek_key=bool(deepseek_key),
            has_kimi_key=bool(kimi_key),
        ),
    )

    config = LLMConfig(
        deepseek_api_key=deepseek_key,
        kimi_api_key=kimi_key,
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
        get_txt_parser(),
    )


def get_writing_service() -> WritingService:
    return WritingService(
        get_novel_repo(),
        get_chapter_repo(),
        get_llm_factory(),
    )


def get_export_service() -> ExportService:
    return ExportService(
        get_novel_repo(),
        get_chapter_repo(),
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
        get_worldview_repo(),
    )


def get_rag_retrieval_service() -> RAGRetrievalService:
    return RAGRetrievalService(
        get_vector_repo(),
        get_chapter_repo(),
        get_character_repo(),
    )


@lru_cache()
def get_v2_repo() -> SQLiteV2Repository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteV2Repository(DB_PATH)


def get_v2_workflow_service() -> V2WorkflowService:
    logger.info("创建工作流服务", extra=build_log_context(event="dependency_initialized", dependency="v2_workflow_service"))
    return V2WorkflowService(
        project_service=get_project_service(),
        content_service=get_content_service(),
        chapter_repo=get_chapter_repo(),
        novel_repo=get_novel_repo(),
        outline_repo=get_outline_repo(),
        llm_factory=get_llm_factory(),
        v2_repo=get_v2_repo(),
    )


def get_chapter_ai_service() -> ChapterAIService:
    logger.info("创建章节AI服务", extra=build_log_context(event="dependency_initialized", dependency="chapter_ai_service"))
    return ChapterAIService(get_llm_factory())
