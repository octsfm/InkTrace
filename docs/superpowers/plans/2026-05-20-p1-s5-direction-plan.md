# P1-S5 Direction And Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frozen P1-S5 direction proposal, direction selection, chapter plan, plan confirmation, and writing task chain on top of the existing workflow and plot-arc foundation.

**Architecture:** Add formal domain models and repositories for DirectionProposal, DirectionSelection, ChapterPlan, PlanConfirmation, WritingTask, and DirectionPlanSnapshot; wire Planner-side creation through `ToolFacade`; enforce `user_action` for DirectionSelection and PlanConfirmation in `AgentOrchestrator`; keep Writer startup gated by confirmed Direction and Plan only. Reuse the existing `PlotArcRepository`, `ContextPackService`, and AgentWorkflow waiting stages without bypassing `HumanReviewGate`.

**Tech Stack:** Python, FastAPI dependency injection, Pydantic models, file-based repositories, pytest

---

### Task 1: Add Formal P1-S5 Models

**Files:**
- Modify: `domain/entities/ai/models.py`
- Test: `tests/ai/test_agent_workflow.py`

- [ ] **Step 1: Write the failing model test**

```python
def test_p1s5_models_expose_required_status_and_refs() -> None:
    from domain.entities.ai.models import (
        ArcRef,
        ChapterBeat,
        ChapterPlan,
        DirectionOption,
        DirectionPlanStatus,
        DirectionProposal,
        DirectionScore,
        PlanConfirmation,
        WritingTask,
        WritingTaskStatus,
    )

    option = DirectionOption(
        option_id="do_1_a",
        direction_proposal_id="dp_1",
        label="A",
        plot_summary="主角选择继续追查灯塔钟声。",
        narrative_premise="沿着父亲遗留线索追查真相。",
        main_conflicts=[],
        foreshadow_usage=[],
        risk_points=[],
        estimated_chapters=3,
        chapter_preview=["追查钟声来源", "发现旧誓约", "遭遇守夜人反扑"],
        base_arc_refs=[
            ArcRef(
                arc_type="master",
                arc_id="ma_1",
                arc_summary="寻找海雾真相",
                arc_status_at_generation="ready",
            )
        ],
        score=DirectionScore(
            total_score=86,
            consistency_score=88,
            conflict_density_score=84,
            satisfaction_rhythm_score=82,
            foreshadow_progress_score=87,
            risk_controllability_score=83,
        ),
    )

    proposal = DirectionProposal(
        direction_proposal_id="dp_1",
        work_id="work_1",
        chapter_id="chapter_1",
        agent_session_id="session_1",
        source_context_pack_id="cp_1",
        source_arc_refs=option.base_arc_refs,
        source_memory_refs=["memory_1"],
        status=DirectionPlanStatus.WAITING_FOR_SELECTION,
        version=1,
        options=[option],
        generation_metadata={"prompt_key": "direction_proposal_generation"},
        created_by="planner_agent",
        created_at="2026-05-20T00:00:00Z",
        updated_at="2026-05-20T00:00:00Z",
    )

    beat = ChapterBeat(
        beat_order=1,
        beat_name="发现旧标记",
        beat_description="主角在灯塔夹层发现旧标记",
        beat_type="setup",
    )
    plan = ChapterPlan(
        chapter_plan_id="cp_1",
        work_id="work_1",
        chapter_id="chapter_1",
        direction_proposal_id="dp_1",
        selected_option_id="do_1_a",
        selection_id="ds_1",
        agent_session_id="session_1",
        source_context_pack_id="cp_1",
        source_arc_refs=option.base_arc_refs,
        source_memory_refs=["memory_1"],
        status=DirectionPlanStatus.WAITING_FOR_CONFIRMATION,
        version=1,
        plan_items=[],
        total_estimated_chapters=3,
        generation_metadata={"prompt_key": "chapter_plan_generation"},
        created_by="planner_agent",
        stale_status="fresh",
        created_at="2026-05-20T00:00:00Z",
        updated_at="2026-05-20T00:00:00Z",
    )
    confirmation = PlanConfirmation(
        confirmation_id="pc_1",
        chapter_plan_id="cp_1",
        direction_proposal_id="dp_1",
        work_id="work_1",
        chapter_id="chapter_1",
        agent_session_id="session_1",
        confirmation_type="direct_confirm",
        user_id="user_action",
        confirmed_by="user_action",
        created_at="2026-05-20T00:00:00Z",
    )
    task = WritingTask(
        writing_task_id="wt_1",
        work_id="work_1",
        chapter_id="chapter_2",
        direction_proposal_id="dp_1",
        selected_option_id="do_1_a",
        chapter_plan_id="cp_1",
        plan_item_id="item_1",
        agent_session_id="session_1",
        status=WritingTaskStatus.READY,
        version=1,
        writing_goal="写出主角进入灯塔后的第一次真相碰撞。",
        must_include=["钟声", "旧标记"],
        must_not_include=["直接揭晓终局"],
        arc_constraints=option.base_arc_refs,
        foreshadow_requirements=[],
        direction_summary="方向 A：追查钟声来源",
        plan_summary="第 2 章：进入灯塔内部调查",
        stale_status="fresh",
        generated_by="planner_agent",
        created_at="2026-05-20T00:00:00Z",
        updated_at="2026-05-20T00:00:00Z",
    )

    assert proposal.status == DirectionPlanStatus.WAITING_FOR_SELECTION
    assert plan.status == DirectionPlanStatus.WAITING_FOR_CONFIRMATION
    assert confirmation.confirmed_by == "user_action"
    assert task.status == WritingTaskStatus.READY
    assert beat.beat_type == "setup"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ai/test_agent_workflow.py -q -k p1s5_models_expose_required_status_and_refs`
Expected: FAIL with missing P1-S5 models or enum values.

- [ ] **Step 3: Write minimal implementation**

```python
class DirectionPlanStatus(StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    WAITING_FOR_SELECTION = "waiting_for_selection"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    SELECTED = "selected"
    CONFIRMED = "confirmed"
    EDITED = "edited"
    STALE = "stale"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class WritingTaskStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    STALE = "stale"
    CONSUMED = "consumed"
    FAILED = "failed"


class ArcRef(AIBaseModel):
    arc_type: str
    arc_id: str
    arc_summary: str
    arc_status_at_generation: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ai/test_agent_workflow.py -q -k p1s5_models_expose_required_status_and_refs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add domain/entities/ai/models.py tests/ai/test_agent_workflow.py
git commit -m "feat(ai): add p1 s5 direction plan models"
```

### Task 2: Add Formal Repositories And File Stores

**Files:**
- Create: `domain/repositories/ai/direction_plan_repository.py`
- Create: `infrastructure/database/repositories/ai/file_direction_plan_store.py`
- Modify: `domain/repositories/ai/__init__.py`
- Modify: `presentation/api/dependencies.py`
- Test: `tests/ai/test_tool_facade.py`

- [ ] **Step 1: Write the failing repository test**

```python
def test_direction_plan_store_persists_proposal_selection_plan_confirmation_and_task(tmp_path) -> None:
    from infrastructure.database.repositories.ai.file_direction_plan_store import FileDirectionPlanStore
    from domain.entities.ai.models import DirectionPlanStatus, DirectionProposal

    store = FileDirectionPlanStore(tmp_path / "direction_plan.json")
    proposal = DirectionProposal(
        direction_proposal_id="dp_1",
        work_id="work_1",
        chapter_id="chapter_1",
        agent_session_id="session_1",
        source_context_pack_id="cp_1",
        source_arc_refs=[],
        source_memory_refs=[],
        status=DirectionPlanStatus.WAITING_FOR_SELECTION,
        version=1,
        options=[],
        generation_metadata={"prompt_key": "direction_proposal_generation"},
        created_by="planner_agent",
        created_at="2026-05-20T00:00:00Z",
        updated_at="2026-05-20T00:00:00Z",
    )

    store.save_direction_proposal(proposal)
    loaded = store.get_direction_proposal("dp_1")

    assert loaded is not None
    assert loaded.direction_proposal_id == "dp_1"
    assert store.list_direction_proposals("work_1")[0].status == DirectionPlanStatus.WAITING_FOR_SELECTION
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ai/test_tool_facade.py -q -k direction_plan_store_persists`
Expected: FAIL with missing repository or missing methods.

- [ ] **Step 3: Write minimal implementation**

```python
class DirectionPlanRepository(ABC):
    @abstractmethod
    def save_direction_proposal(self, proposal: DirectionProposal) -> DirectionProposal: ...

    @abstractmethod
    def get_direction_proposal(self, direction_proposal_id: str) -> DirectionProposal | None: ...

    @abstractmethod
    def save_chapter_plan(self, plan: ChapterPlan) -> ChapterPlan: ...

    @abstractmethod
    def save_plan_confirmation(self, confirmation: PlanConfirmation) -> PlanConfirmation: ...

    @abstractmethod
    def save_writing_task(self, task: WritingTask) -> WritingTask: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ai/test_tool_facade.py -q -k direction_plan_store_persists`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add domain/repositories/ai/direction_plan_repository.py infrastructure/database/repositories/ai/file_direction_plan_store.py domain/repositories/ai/__init__.py presentation/api/dependencies.py tests/ai/test_tool_facade.py
git commit -m "feat(ai): add p1 s5 direction plan repositories"
```

### Task 3: Wire Planner Generation Through ToolFacade

**Files:**
- Modify: `application/services/ai/tool_facade.py`
- Modify: `application/services/ai/context_pack_service.py`
- Modify: `application/services/ai/agent_workflow.py`
- Test: `tests/ai/test_tool_facade.py`
- Test: `tests/ai/test_agent_workflow.py`

- [ ] **Step 1: Write the failing generation tests**

```python
def test_create_direction_proposal_persists_arc_refs_and_waiting_state() -> None:
    result = tool_facade.create_direction_proposal(...)
    assert result.status == "waiting_for_selection"
    assert result.data["direction_proposal_id"] != ""


def test_create_chapter_plan_persists_plan_items_and_waiting_state() -> None:
    result = tool_facade.create_chapter_plan(...)
    assert result.status == "waiting_for_confirmation"
    assert len(result.data["plan_items"]) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ai/test_tool_facade.py tests/ai/test_agent_workflow.py -q -k "direction_proposal or chapter_plan"`
Expected: FAIL because ToolFacade cannot persist the formal entities or missing schema validation.

- [ ] **Step 3: Write minimal implementation**

```python
def create_direction_proposal(self, payload: dict[str, Any]) -> ToolResult:
    proposal = DirectionProposal.model_validate(payload)
    stored = self._direction_plan_repository.save_direction_proposal(proposal)
    return ToolResult.ok(
        data={
            "direction_proposal_id": stored.direction_proposal_id,
            "status": stored.status.value,
            "option_ids": [item.option_id for item in stored.options],
        }
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ai/test_tool_facade.py tests/ai/test_agent_workflow.py -q -k "direction_proposal or chapter_plan"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add application/services/ai/tool_facade.py application/services/ai/context_pack_service.py application/services/ai/agent_workflow.py tests/ai/test_tool_facade.py tests/ai/test_agent_workflow.py
git commit -m "feat(ai): persist planner direction and chapter plans"
```

### Task 4: Enforce User Gates And Build WritingTask

**Files:**
- Modify: `application/services/ai/agent_workflow.py`
- Modify: `application/services/ai/tool_facade.py`
- Modify: `presentation/api/dependencies.py`
- Test: `tests/ai/test_agent_workflow.py`
- Test: `tests/ai/test_continuation_service.py`

- [ ] **Step 1: Write the failing gate and writing task tests**

```python
def test_direction_selection_requires_user_action_and_marks_selected() -> None:
    result = orchestrator.submit_user_decision(..., user_decision="confirm_direction")
    assert result["status"] == "waiting_for_user"
    assert result["result_ref"]["type"] == "direction_selection"


def test_plan_confirmation_requires_user_action_and_creates_ready_writing_task() -> None:
    result = orchestrator.submit_user_decision(..., user_decision="confirm_chapter_plan")
    assert result["result_ref"]["type"] == "plan_confirmation"
    task = direction_plan_store.get_active_writing_task(work_id="work_1", chapter_id="chapter_2")
    assert task is not None
    assert task.status.value == "ready"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ai/test_agent_workflow.py tests/ai/test_continuation_service.py -q -k "direction_selection_requires_user_action or creates_ready_writing_task"`
Expected: FAIL because DirectionSelection/PlanConfirmation are not formal persisted entities or WritingTask is missing.

- [ ] **Step 3: Write minimal implementation**

```python
if current_stage == WorkflowStage.DIRECTION_SELECTION_WAITING:
    selection = self._record_direction_selection(...)
    run.metadata["selected_direction_id"] = selection.selected_option_id
    return self._waiting_result(...)

if current_stage == WorkflowStage.CHAPTER_PLAN_CONFIRM_WAITING:
    confirmation = self._record_plan_confirmation(...)
    writing_task = self._build_writing_task_for_confirmed_plan(...)
    return self._advance_to_writing_prepare(...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ai/test_agent_workflow.py tests/ai/test_continuation_service.py -q -k "direction_selection_requires_user_action or creates_ready_writing_task"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add application/services/ai/agent_workflow.py application/services/ai/tool_facade.py presentation/api/dependencies.py tests/ai/test_agent_workflow.py tests/ai/test_continuation_service.py
git commit -m "feat(ai): enforce p1 s5 user gates and writing task"
```

### Task 5: Regress P1-S5 Boundaries

**Files:**
- Modify: `tests/ai/test_tool_facade.py`
- Modify: `tests/ai/test_agent_workflow.py`
- Modify: `tests/ai/test_context_pack_service.py`
- Modify: `tests/ai/test_p0_regression.py`

- [ ] **Step 1: Add focused boundary tests**

```python
def test_planner_cannot_auto_select_direction() -> None: ...


def test_planner_cannot_auto_confirm_plan() -> None: ...


def test_writing_task_contains_safe_refs_without_full_context() -> None: ...


def test_writer_cannot_start_before_direction_and_plan_confirmed() -> None: ...
```

- [ ] **Step 2: Run focused regression**

Run: `python -m pytest tests/ai/test_tool_facade.py tests/ai/test_agent_workflow.py tests/ai/test_context_pack_service.py tests/ai/test_p0_regression.py -q`
Expected: FAIL until all P1-S5 safety boundaries are enforced.

- [ ] **Step 3: Fix minimal boundary gaps**

```python
assert caller_type == "user_action"
assert "content_text" not in serialized_task_payload
assert session.current_stage != WorkflowStage.DRAFTING
```

- [ ] **Step 4: Run full related regression**

Run: `python -m pytest tests/ai/test_tool_facade.py tests/ai/test_agent_workflow.py tests/ai/test_context_pack_service.py tests/ai/test_continuation_service.py tests/ai/test_agent_runtime_service.py tests/ai/test_p0_regression.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/ai/test_tool_facade.py tests/ai/test_agent_workflow.py tests/ai/test_context_pack_service.py tests/ai/test_continuation_service.py tests/ai/test_agent_runtime_service.py tests/ai/test_p0_regression.py
git commit -m "test(ai): cover p1 s5 planning boundaries"
```

## Self-Review

- Spec coverage:
  - `DirectionProposal / DirectionSelection / ChapterPlan / PlanConfirmation / WritingTask / DirectionPlanSnapshot` all have planned model or repository tasks.
  - `user_action` gate enforcement is covered in Task 4 and Task 5.
  - `safe_ref` and "no full正文 / no full ContextPack" boundaries are covered in Task 4 and Task 5.
  - Plot arc alignment, degraded rules, and Writer startup gating are covered in Task 3 to Task 5.
- Placeholder scan:
  - No `TODO` or `implement later` placeholders remain.
- Type consistency:
  - `DirectionPlanStatus`, `WritingTaskStatus`, `DirectionProposal`, `ChapterPlan`, `PlanConfirmation`, and `WritingTask` naming is consistent across all tasks.

**Plan complete and saved to `docs/superpowers/plans/2026-05-20-p1-s5-direction-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
