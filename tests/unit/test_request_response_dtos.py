from application.dto.request_dto import StyleRequirementsRequest
from application.dto.response_dto import ChapterTaskResponse, StyleRequirements


def test_style_requirements_request_has_source_and_version():
    dto = StyleRequirementsRequest(source_type="sample_extracted", version=3)
    assert dto.source_type == "sample_extracted"
    assert dto.version == 3


def test_chapter_task_response_defaults_are_clean():
    dto = ChapterTaskResponse()
    assert dto.required_foreshadowing_action == "advance"
    assert dto.required_hook_strength == "medium"


def test_style_requirements_response_defaults():
    dto = StyleRequirements()
    assert dto.source_type == "manual"
    assert dto.version == 1
