from domain.entities.chapter_task import ChapterTask
from domain.entities.detemplated_draft import DetemplatedDraft
from domain.entities.style_requirements import StyleRequirements
from domain.entities.structural_draft import StructuralDraft


def test_chapter_task_defaults_clean():
    task = ChapterTask(id="t1", chapter_id="c1", project_id="p1", branch_id="b1", chapter_number=1)
    assert task.required_foreshadowing_action == "advance"
    assert task.required_hook_strength == "medium"


def test_style_requirements_defaults_include_source_version():
    style = StyleRequirements(id="s1", project_id="p1")
    assert style.source_type == "manual"
    assert style.version == 1


def test_draft_entities_have_stable_stage_fields():
    structural = StructuralDraft(id="sd1", chapter_id="c1", project_id="p1", chapter_number=1)
    detemplated = DetemplatedDraft(id="dd1", chapter_id="c1", project_id="p1", chapter_number=1)
    assert structural.generation_stage == "structural"
    assert detemplated.generation_stage == "detemplated"
