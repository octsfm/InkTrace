from datetime import datetime

from application.services.continuation_context_builder import ContinuationContextBuilder
from domain.entities.continuation_context import ContinuationContext


class _SnapshotRepo:
    def __init__(self):
        self.items = []

    def save(self, item):
        self.items.append(item)


class _WorkflowService:
    def __init__(self):
        self.continuation_context_snapshot_repo = _SnapshotRepo()

    def build_continuation_context(self, project_id: str, chapter_id: str, chapter_number: int):
        return ContinuationContext(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            recent_chapter_memories=[{"chapter_id": "c1"}],
            last_chapter_tail="尾部内容",
            relevant_characters=[{"name": "主角"}],
            relevant_foreshadowing=["伏笔A"],
            global_constraints={"must_keep_threads": ["主线"]},
            chapter_outline={"goal": "推进"},
            chapter_task_seed={"goals": ["推进"]},
            style_requirements={"source_type": "manual"},
            created_at=datetime.now(),
        )


def test_continuation_context_builder_persists_snapshot():
    workflow = _WorkflowService()
    builder = ContinuationContextBuilder(workflow)
    context = builder.build("p1", "c9", 9, plan_id="plan-1", branch_id="b1")
    assert context.project_id == "p1"
    assert len(workflow.continuation_context_snapshot_repo.items) == 1
    snapshot = workflow.continuation_context_snapshot_repo.items[0]
    assert snapshot.project_id == "p1"
    assert snapshot.chapter_id == "c9"
    assert snapshot.last_chapter_tail == "尾部内容"
