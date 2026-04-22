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
from domain.repositories.outline_document_repository import IOutlineDocumentRepository
from domain.repositories.project_repository import IProjectRepository
from domain.repositories.project_cleanup_repository import IProjectCleanupRepository
from domain.repositories.organize_job_repository import IOrganizeJobRepository
from domain.repositories.chapter_outline_repository import IChapterOutlineRepository
from domain.repositories.template_repository import ITemplateRepository
from domain.repositories.worldview_repository import IWorldviewRepository
from domain.repositories.vector_repository import IVectorRepository
from domain.repositories.llm_config_repository import ILLMConfigRepository
from domain.repositories.global_constraints_repository import IGlobalConstraintsRepository
from domain.repositories.chapter_analysis_memory_repository import IChapterAnalysisMemoryRepository
from domain.repositories.chapter_continuation_memory_repository import IChapterContinuationMemoryRepository
from domain.repositories.chapter_task_repository import IChapterTaskRepository
from domain.repositories.structural_draft_repository import IStructuralDraftRepository
from domain.repositories.detemplated_draft_repository import IDetemplatedDraftRepository
from domain.repositories.draft_integrity_check_repository import IDraftIntegrityCheckRepository
from domain.repositories.style_requirements_repository import IStyleRequirementsRepository
from domain.repositories.continuation_context_snapshot_repository import IContinuationContextSnapshotRepository
from domain.repositories.plot_arc_repository import IPlotArcRepository
from domain.repositories.arc_progress_snapshot_repository import IArcProgressSnapshotRepository
from domain.repositories.chapter_arc_binding_repository import IChapterArcBindingRepository
from infrastructure.persistence.sqlite_novel_repo import SQLiteNovelRepository
from infrastructure.persistence.sqlite_chapter_repo import SQLiteChapterRepository
from infrastructure.persistence.sqlite_character_repo import SQLiteCharacterRepository
from infrastructure.persistence.sqlite_outline_repo import SQLiteOutlineRepository
from infrastructure.persistence.sqlite_outline_document_repo import SQLiteOutlineDocumentRepository
from infrastructure.persistence.sqlite_project_repo import SQLiteProjectRepository
from infrastructure.persistence.sqlite_project_cleanup_repo import SQLiteProjectCleanupRepository
from infrastructure.persistence.sqlite_organize_job_repo import SQLiteOrganizeJobRepository
from infrastructure.persistence.sqlite_chapter_outline_repo import SQLiteChapterOutlineRepository
from infrastructure.persistence.sqlite_template_repo import SQLiteTemplateRepository
from infrastructure.persistence.sqlite_worldview_repo import SQLiteWorldviewRepository
from infrastructure.persistence.chromadb_vector_repo import ChromaDBVectorRepository
from infrastructure.persistence.sqlite_llm_config_repo import SQLiteLLMConfigRepository
from infrastructure.persistence.sqlite_global_constraints_repo import SQLiteGlobalConstraintsRepository
from infrastructure.persistence.sqlite_chapter_analysis_memory_repo import SQLiteChapterAnalysisMemoryRepository
from infrastructure.persistence.sqlite_chapter_continuation_memory_repo import SQLiteChapterContinuationMemoryRepository
from infrastructure.persistence.sqlite_chapter_task_repo import SQLiteChapterTaskRepository
from infrastructure.persistence.sqlite_structural_draft_repo import SQLiteStructuralDraftRepository
from infrastructure.persistence.sqlite_detemplated_draft_repo import SQLiteDetemplatedDraftRepository
from infrastructure.persistence.sqlite_draft_integrity_check_repo import SQLiteDraftIntegrityCheckRepository
from infrastructure.persistence.sqlite_style_requirements_repo import SQLiteStyleRequirementsRepository
from infrastructure.persistence.sqlite_continuation_context_snapshot_repo import SQLiteContinuationContextSnapshotRepository
from infrastructure.persistence.sqlite_plot_arc_repo import SQLitePlotArcRepository
from infrastructure.persistence.sqlite_arc_progress_snapshot_repo import SQLiteArcProgressSnapshotRepository
from infrastructure.persistence.sqlite_chapter_arc_binding_repo import SQLiteChapterArcBindingRepository
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
from application.services.capacity_planner_service import CapacityPlannerService
from application.services.chapter_chunk_analysis_service import ChapterChunkAnalysisService
from application.services.outline_digest_service import OutlineDigestService
from application.services.token_budget_manager import TokenBudgetManager
from application.services.chapter_ai_service import ChapterAIService
from application.services.chapter_import_workflow_service import ChapterImportWorkflowService
from application.services.plot_arc_service import PlotArcService
from application.services.arc_planning_service import ArcPlanningService
from application.services.arc_writeback_service import ArcWritebackService
from application.services.global_analysis_service import GlobalAnalysisService
from application.services.chapter_memory_service import ChapterMemoryService
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
def get_outline_document_repo() -> IOutlineDocumentRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteOutlineDocumentRepository(DB_PATH)


@lru_cache()
def get_project_repo() -> IProjectRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    logger.info("仓储初始化", extra=build_log_context(event="repo_initialized", repo="project", db_path=DB_PATH))
    return SQLiteProjectRepository(DB_PATH)


@lru_cache()
def get_project_cleanup_repo() -> IProjectCleanupRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteProjectCleanupRepository(DB_PATH)


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
def get_global_constraints_repo() -> IGlobalConstraintsRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteGlobalConstraintsRepository(DB_PATH)


@lru_cache()
def get_chapter_analysis_memory_repo() -> IChapterAnalysisMemoryRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteChapterAnalysisMemoryRepository(DB_PATH)


@lru_cache()
def get_chapter_continuation_memory_repo() -> IChapterContinuationMemoryRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteChapterContinuationMemoryRepository(DB_PATH)


@lru_cache()
def get_chapter_task_repo() -> IChapterTaskRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteChapterTaskRepository(DB_PATH)


@lru_cache()
def get_structural_draft_repo() -> IStructuralDraftRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteStructuralDraftRepository(DB_PATH)


@lru_cache()
def get_detemplated_draft_repo() -> IDetemplatedDraftRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteDetemplatedDraftRepository(DB_PATH)


@lru_cache()
def get_draft_integrity_check_repo() -> IDraftIntegrityCheckRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteDraftIntegrityCheckRepository(DB_PATH)


@lru_cache()
def get_style_requirements_repo() -> IStyleRequirementsRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteStyleRequirementsRepository(DB_PATH)


@lru_cache()
def get_continuation_context_snapshot_repo() -> IContinuationContextSnapshotRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteContinuationContextSnapshotRepository(DB_PATH)


@lru_cache()
def get_plot_arc_repo() -> IPlotArcRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLitePlotArcRepository(DB_PATH)


@lru_cache()
def get_arc_progress_snapshot_repo() -> IArcProgressSnapshotRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteArcProgressSnapshotRepository(DB_PATH)


@lru_cache()
def get_chapter_arc_binding_repo() -> IChapterArcBindingRepository:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return SQLiteChapterArcBindingRepository(DB_PATH)


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
        deepseek_model=os.environ.get("INKTRACE_DEEPSEEK_MODEL", "deepseek-chat"),
        deepseek_base_url=os.environ.get("INKTRACE_DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        deepseek_fallback_model=os.environ.get("INKTRACE_DEEPSEEK_FALLBACK_MODEL", ""),
        deepseek_fallback_base_url=os.environ.get("INKTRACE_DEEPSEEK_FALLBACK_BASE_URL", os.environ.get("INKTRACE_DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")),
        kimi_api_key=kimi_key,
        kimi_model=os.environ.get("INKTRACE_KIMI_MODEL", "moonshot-v1-8k"),
        kimi_base_url=os.environ.get("INKTRACE_KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        kimi_fallback_model=os.environ.get("INKTRACE_KIMI_FALLBACK_MODEL", ""),
        kimi_fallback_base_url=os.environ.get("INKTRACE_KIMI_FALLBACK_BASE_URL", os.environ.get("INKTRACE_KIMI_BASE_URL", "https://api.moonshot.cn/v1")),
    )
    return LLMFactory(config)


@lru_cache()
def get_worldview_checker() -> WorldviewChecker:
    return WorldviewChecker()


@lru_cache()
def get_rag_context_builder() -> RAGContextBuilder:
    return RAGContextBuilder()


def get_project_service() -> ProjectService:
    return ProjectService(get_project_repo(), get_novel_repo(), get_project_cleanup_repo())


def get_content_service() -> ContentService:
    return ContentService(
        get_novel_repo(),
        get_chapter_repo(),
        get_character_repo(),
        get_outline_repo(),
        get_txt_parser(),
        get_outline_document_repo(),
        get_outline_digest_service(),
    )


@lru_cache()
def get_outline_digest_service() -> OutlineDigestService:
    return OutlineDigestService()


@lru_cache()
def get_capacity_planner_service() -> CapacityPlannerService:
    return CapacityPlannerService()


@lru_cache()
def get_chapter_chunk_analysis_service() -> ChapterChunkAnalysisService:
    return ChapterChunkAnalysisService()


@lru_cache()
def get_token_budget_manager() -> TokenBudgetManager:
    return TokenBudgetManager()


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


@lru_cache()
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
        global_constraints_repo=get_global_constraints_repo(),
        chapter_analysis_memory_repo=get_chapter_analysis_memory_repo(),
        chapter_continuation_memory_repo=get_chapter_continuation_memory_repo(),
        chapter_outline_repo=get_chapter_outline_repo(),
        chapter_task_repo=get_chapter_task_repo(),
        structural_draft_repo=get_structural_draft_repo(),
        detemplated_draft_repo=get_detemplated_draft_repo(),
        draft_integrity_check_repo=get_draft_integrity_check_repo(),
        style_requirements_repo=get_style_requirements_repo(),
        continuation_context_snapshot_repo=get_continuation_context_snapshot_repo(),
        arc_progress_snapshot_repo=get_arc_progress_snapshot_repo(),
        plot_arc_service=get_plot_arc_service(),
        chapter_arc_binding_repo=get_chapter_arc_binding_repo(),
        arc_planning_service=get_arc_planning_service(),
        arc_writeback_service=get_arc_writeback_service(),
        chapter_chunk_analysis_service=get_chapter_chunk_analysis_service(),
    )


def get_chapter_ai_service() -> ChapterAIService:
    logger.info("创建章节AI服务", extra=build_log_context(event="dependency_initialized", dependency="chapter_ai_service"))
    return ChapterAIService(get_llm_factory())


def get_chapter_import_workflow_service() -> ChapterImportWorkflowService:
    logger.info("创建章节导入工作流服务", extra=build_log_context(event="dependency_initialized", dependency="chapter_import_workflow_service"))
    return ChapterImportWorkflowService(get_chapter_ai_service())


def get_plot_arc_service() -> PlotArcService:
    return PlotArcService(get_plot_arc_repo())


def get_arc_planning_service() -> ArcPlanningService:
    return ArcPlanningService(get_plot_arc_service())


def get_arc_writeback_service() -> ArcWritebackService:
    return ArcWritebackService(
        get_plot_arc_repo(),
        get_arc_progress_snapshot_repo(),
        get_chapter_arc_binding_repo(),
    )


def get_global_analysis_service() -> GlobalAnalysisService:
    return GlobalAnalysisService(get_chapter_ai_service(), lambda project_id: get_v2_repo().find_active_project_memory(project_id) or {})


def get_chapter_memory_service() -> ChapterMemoryService:
    return ChapterMemoryService(get_chapter_ai_service())


def warmup_singletons_for_startup() -> None:
    """
    Eagerly initialize repositories/config in startup phase, so request phase
    does not trigger schema migration/DDL lazily under concurrency.
    """
    warmup_steps = [
        ("novel_repo", get_novel_repo),
        ("chapter_repo", get_chapter_repo),
        ("character_repo", get_character_repo),
        ("outline_repo", get_outline_repo),
        ("outline_document_repo", get_outline_document_repo),
        ("project_repo", get_project_repo),
        ("organize_job_repo", get_organize_job_repo),
        ("chapter_outline_repo", get_chapter_outline_repo),
        ("template_repo", get_template_repo),
        ("worldview_repo", get_worldview_repo),
        ("llm_config_repo", get_llm_config_repo),
        ("global_constraints_repo", get_global_constraints_repo),
        ("chapter_analysis_memory_repo", get_chapter_analysis_memory_repo),
        ("chapter_continuation_memory_repo", get_chapter_continuation_memory_repo),
        ("chapter_task_repo", get_chapter_task_repo),
        ("structural_draft_repo", get_structural_draft_repo),
        ("detemplated_draft_repo", get_detemplated_draft_repo),
        ("draft_integrity_check_repo", get_draft_integrity_check_repo),
        ("style_requirements_repo", get_style_requirements_repo),
        ("continuation_context_snapshot_repo", get_continuation_context_snapshot_repo),
        ("plot_arc_repo", get_plot_arc_repo),
        ("arc_progress_snapshot_repo", get_arc_progress_snapshot_repo),
        ("chapter_arc_binding_repo", get_chapter_arc_binding_repo),
        ("v2_repo", get_v2_repo),
        ("capacity_planner_service", get_capacity_planner_service),
        ("chapter_chunk_analysis_service", get_chapter_chunk_analysis_service),
        ("outline_digest_service", get_outline_digest_service),
        ("token_budget_manager", get_token_budget_manager),
        ("config_service", get_config_service),
        ("llm_factory", get_llm_factory),
    ]
    for name, factory in warmup_steps:
        logger.info("启动预热依赖", extra=build_log_context(event="dependency_warmup", dependency=name))
        try:
            factory()
        except Exception as exc:
            logger.exception(
                "启动预热依赖失败，已跳过",
                extra=build_log_context(
                    event="dependency_warmup_failed",
                    dependency=name,
                    error=str(exc),
                ),
            )
