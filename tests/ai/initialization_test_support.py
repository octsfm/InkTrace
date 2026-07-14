from __future__ import annotations

from application.services.ai.initialization_analysis_service import ManuscriptAnalysisService, OutlineAnalysisService
from application.services.ai.output_validation_service import OutputValidationService
from application.services.ai.prompt_registry import PromptRegistry
from application.services.v1.service_factory import build_writing_asset_service
from presentation.api import dependencies


def build_initialization_analysis_dependencies() -> dict[str, object]:
    router = dependencies.get_model_router()
    return {
        "writing_asset_service": build_writing_asset_service(),
        "outline_analysis_service": OutlineAnalysisService(
            model_router=router,
            prompt_registry=PromptRegistry(),
            output_validator=OutputValidationService(),
        ),
        "manuscript_analysis_service": ManuscriptAnalysisService(
            model_router=router,
            prompt_registry=PromptRegistry(),
            output_validator=OutputValidationService(),
        ),
    }

