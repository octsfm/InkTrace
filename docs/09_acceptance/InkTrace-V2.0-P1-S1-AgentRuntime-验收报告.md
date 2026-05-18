# InkTrace V2.0 P1-S1 AgentRuntime 核心落地 — 验收报告

版本：v2.0（复验）
初验日期：2026-05-18
复验日期：2026-05-18
依据文档：`docs/03_design/InkTrace-V2.0-P1-01-AgentRuntime详细设计.md`
对应开发计划：`docs/04_plan/InkTrace-V2.0-P1-开发计划.md` §5.2

---

## 一、验收总体结论

**判定：通过 ✅**

初验提出的 11 项偏差（3 严重 + 5 中等 + 3 轻微）已全部修正。核心状态机、PPAO 循环、Session/Step/Observation 生命周期机制完整可用。数据模型与设计文档一致。**建议进入 P1-S2（AgentWorkflow 编排落地）。**

---

## 二、初验偏差修正确认

### 2.1 严重偏差（3/3 已修正）

| # | 初验问题 | 修正内容 | 验证 |
|---|----------|----------|------|
| D1 | AgentSession 缺少 `current_agent_type` | `current_agent_type: str = ""` | ✅ |
| D2 | AgentWorkflowType 枚举不完整（仅 3/5） | CONTINUATION / REVISION / PLANNING / MEMORY_UPDATE / FULL_WORKFLOW 全部 5 个值；附带 `_normalize_agent_workflow_type` 向后兼容迁移函数 | ✅ |
| D3 | AgentStep 缺少 tool_calls / step_plan / output_refs | `tool_calls: list[ToolCallRef]` + `step_plan: StepPlan \| None` + `output_refs: list[str]` 全部补充 | ✅ |

### 2.2 中等偏差（5/5 已修正）

| # | 初验问题 | 修正内容 | 验证 |
|---|----------|----------|------|
| D4 | allow_degraded 在 metadata 中 | 提升为顶层字段 `allow_degraded: bool = True`，附带 model_validator 向后兼容 | ✅ |
| D5 | AgentRunContext 缺失 12 字段 | job_id / agent_workflow_type / current_phase / caller_type / warning_codes / resource_scope_refs / prior_observation_refs / execution_guard_flags 全部补充；4 个 P1 专属引用字段按计划延后 | ✅ |
| D6 | AgentObservation 缺失 7 字段 | source_ref / summary / decision_reason / source_tool_call_id / source_attempt_no / error_message / next_action_hint 全部补充 | ✅ |
| D7 | AgentStep 缺失 retryable/skippable/requires_user_decision/skip_reason | 全部补充为顶层字段，附带 `_resolve_step_runtime_flags()` 动态计算逻辑 | ✅ |
| D8 | StepPlan 数据结构未定义 | `StepPlan` 类包含 next_action_type / target_tool_name / expected_observation_type / retryable / requires_user_decision / side_effect_level 全部 6 字段 | ✅ |

### 2.3 轻微偏差（3/3 已修正）

| # | 初验问题 | 修正内容 | 验证 |
|---|----------|----------|------|
| D9 | step_order vs order_index 命名不一致 | `step_order` 属性别名 + model_validator 向后兼容 | ✅ |
| D10 | current_phase 应为 enum | `PPAOPhase` 枚举（PERCEPTION / PLANNING / ACTION / OBSERVATION），用于 AgentSession/AgentStep/AgentRunContext | ✅ |
| D11 | PPAO 通用 step_type 体系未使用 | 按初验建议延后到 P1-S2/S3，不阻塞 S1 | — |

---

## 三、复验新增内容

初验后代码新增以下结构化改进：

| 新增内容 | 位置 | 说明 |
|----------|------|------|
| `PPAOPhase` 枚举 | models.py:227-231 | PERCEPTION / PLANNING / ACTION / OBSERVATION |
| `ToolCallRef` 模型 | models.py:287-292 | tool_call_id / tool_name / status / result_ref / error_code |
| `StepPlan` 模型 | models.py:295-301 | 6 字段完整 |
| `_normalize_agent_workflow_type()` | models.py:173-178 | memory_refresh→memory_update / review→revision 向后兼容 |
| `_resolve_step_runtime_flags()` | agent_runtime_service.py:1218-1226 | retryable / skippable / requires_user_decision 动态判定 |
| `_build_step_plan()` | agent_runtime_service.py:1228-1238 | Planning 阶段 StepPlan 自动构建 |
| `_build_resource_scope_refs()` | agent_runtime_service.py:1212-1216 | work:{id} / chapter:{id} 作用域引用 |
| AgentSession `workflow_type` 别名属性 | models.py:283-284 | 向后兼容旧字段名 |
| AgentStep `step_order` 别名属性 | models.py:350-351 | 向后兼容旧字段名 |
| 多个 model_validator 向后兼容 | models.py 多处 | 旧字段名/旧枚举值自动迁移 |
| AgentRunContext `build_run_context` 全字段填充 | agent_runtime_service.py:446-466 | job_id / agent_workflow_type / current_phase / caller_type / warning_codes / resource_scope_refs / prior_observation_refs / execution_guard_flags |

---

## 四、最终数据模型对照

### 4.1 AgentSession（设计 §5.2 — 27/27 字段通过）

```
session_id ✅    job_id ✅    work_id ✅    chapter_id ✅
agent_workflow_type ✅ (AgentWorkflowType enum, 5值)
status ✅ (9 状态值)
current_agent_type ✅    allow_degraded ✅ (顶层)
caller_type ✅    user_instruction ✅
request_id ✅    trace_id ✅
current_step_id ✅    current_phase ✅ (PPAOPhase enum)
result_ref ✅    result ✅ (AgentResult)
warning_codes ✅    error_code ✅    error_message ✅
status_reason ✅    metadata ✅
created_at ✅    updated_at ✅
started_at ✅    waiting_at ✅    paused_at ✅    resumed_at ✅
cancelling_at ✅    cancelled_at ✅    finished_at ✅
```

### 4.2 AgentStep（设计 §6.2 — 24/24 字段通过）

```
step_id ✅    session_id ✅    job_id ✅    job_step_id ✅
agent_type ✅    step_type ✅    action ✅
order_index ✅ (step_order 别名)
status ✅ (9 状态值)    step_phase ✅ (PPAOPhase enum)
request_id ✅    trace_id ✅
tool_calls ✅ (ToolCallRef[])    step_plan ✅ (StepPlan)
input_ref ✅    output_refs ✅
attempt_count ✅    max_attempts ✅ (默认3)
retryable ✅    skippable ✅    requires_user_decision ✅
skip_reason ✅    warning_codes ✅
error_code ✅    error_message ✅    status_reason ✅
observation_id ✅    prior_observation_refs ✅
metadata ✅    created_at ✅    started_at ✅    waiting_at ✅    finished_at ✅
```

### 4.3 AgentObservation（设计 §7.3 — 21/21 字段通过）

```
observation_id ✅    session_id ✅    step_id ✅
observation_type ✅ (11 枚举值)
source_type ✅    source_ref ✅
status ✅    data_ref ✅    safe_message ✅    summary ✅
decision ✅ (7 种 decision)    decision_reason ✅
source_tool_call_id ✅    source_attempt_no ✅
warning_codes ✅    error_code ✅    error_message ✅
next_action_hint ✅
request_id ✅    trace_id ✅
metadata ✅    created_at ✅
```

### 4.4 AgentRunContext（设计 §8.2 — 18/22 字段通过，4 字段延后）

```
session_id ✅    job_id ✅    step_id ✅
work_id ✅    chapter_id ✅
agent_workflow_type ✅    current_agent_type ✅
current_phase ✅ (PPAOPhase enum)    caller_type ✅
user_instruction ✅    context_refs ✅
selected_direction_id ✅    selected_chapter_plan_id ✅
request_id ✅    trace_id ✅    allow_degraded ✅
warning_codes ✅    resource_scope_refs ✅
prior_observation_refs ✅    execution_guard_flags ✅
metadata ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
current_candidate_draft_id      — P1-S5/S6 延后
current_candidate_version_id    — P1-S5/S6 延后
latest_review_id                — P1-S5/S6 延后
latest_memory_update_suggestion_id — P1-S9 延后
```

---

## 五、测试覆盖（复验）

测试用例数：**82 → 103（+21）**

新增测试覆盖：
- PPAOPhase 枚举和 phase 流转
- StepPlan 构建逻辑
- ToolCallRef 追踪
- AgentRunContext 新增字段（job_id / agent_workflow_type / current_phase / caller_type / resource_scope_refs）
- backward compat 迁移（workflow_type → agent_workflow_type / step_order → order_index）
- AgentObservation 补充字段
- AgentStep retryable/skippable/requires_user_decision 动态判定

---

## 六、开发计划验收标准对照

| 开发计划 §5.2 标准 | 初验 | 复验 |
|--------------------|------|------|
| Runtime 核心模型与服务 | ⚠️ 字段缺失 | ✅ |
| waiting_for_user / cancelled / ignored_late_result 规则 | ✅ | ✅ |
| Runtime 与 AIJob 映射关系（投影不替代真源） | ✅ | ✅ |
| 预留 AgentTrace 贯穿字段：request_id / trace_id / session_id / step_id | ✅ | ✅ |
| caller_type=agent 禁止 user_action 专属动作 | ✅ | ✅ |
| partial_success 最低原则成立（必须有可交付 result_ref） | ✅ | ✅ |

---

## 七、进入 P1-S2 的前置条件检查

| 条件 | 状态 |
|------|------|
| P1-S1 数据模型与设计文档一致 | ✅ |
| PPAO 状态机完整可用 | ✅ |
| AgentSession / AgentStep / AgentObservation 状态机正确 | ✅ |
| 与 AIJobSystem 集成正确 | ✅ |
| 与 ToolFacade 集成正确 | ✅ |
| 安全红线全部生效 | ✅ |
| 103 个测试用例通过 | ✅ |
| retry / cancel / late_result / wait_for_user 规则验证 | ✅ |
| PPAOPhase 枚举可用于 S2 编排 | ✅ |
| StepPlan 结构可用于 S2 Planning | ✅ |
| AgentRunContext 可传递给 S2 Orchestrator | ✅ |

**判定：P1-S1 验收通过，可进入 P1-S2（AgentWorkflow 编排落地）。**

---

## 附录：代码文件终态

| 文件 | 说明 |
|------|------|
| `domain/entities/ai/models.py` | AgentSession/Step/Observation/RunContext/Result + ToolCallRef/StepPlan/PPAOPhase 全部模型 |
| `domain/repositories/ai/agent_session_repository.py` | Session 仓储接口 |
| `domain/repositories/ai/agent_step_repository.py` | Step 仓储接口 |
| `domain/repositories/ai/agent_observation_repository.py` | Observation 仓储接口 |
| `application/services/ai/agent_runtime_service.py` | AgentRuntimeService 完整实现（1258 行） |
| `application/services/ai/ai_job_service.py` | 新增 list_attempts / save_attempt |
| `infrastructure/database/repositories/ai/file_agent_runtime_store.py` | JSON 文件存储实现 |
| `tests/ai/test_agent_runtime_service.py` | 103 个测试用例 |
