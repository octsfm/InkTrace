# InkTrace V2.0-P1-03 五Agent职责与编排详细设计

版本：v1.0 / P1 模块级详细设计候选冻结版
状态：候选冻结
所属阶段：InkTrace V2.0 P1
设计范围：五 Agent 职责、输入输出、Step 序列、Tool 权限、数据交接与协作边界

依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`
- `docs/07_overview/InkTrace-V2.0-概要设计说明书.md`
- `docs/02_architecture/InkTrace-V2.0-架构设计说明书.md`
- `docs/03_design/InkTrace-V2.0-P1-详细设计总纲.md`
- `docs/03_design/InkTrace-V2.0-P1-01-AgentRuntime详细设计.md`
- `docs/03_design/InkTrace-V2.0-P1-02-AgentWorkflow详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-01-AI基础设施详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-03-初始化流程详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-04-StoryMemory与StoryState详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-06-ContextPack详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-07-ToolFacade与权限详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-08-MinimalContinuationWorkflow详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-10-AIReview详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-11-API与集成边界详细设计.md`

说明：本文档只冻结五 Agent 的职责、输入输出、Step 序列、Tool 权限矩阵、数据交接与协作边界。不进入 AgentRuntime 状态机、AgentWorkflow Stage/Transition/Decision、剧情轨道、方向推演算法等下游模块的内部设计。不写代码、不生成开发计划、不修改 P0 / P1-01 / P1-02。

---

## 一、文档定位与设计范围

### 1.1 文档定位

本文档是 InkTrace V2.0-P1 的第三个模块级详细设计文档，仅覆盖五 Agent 的职责定义、输入输出、Step 序列、Tool 调用权限、数据交接与协作边界。

P1-03 的目标是冻结每个 Agent 的完整职责边界：Memory Agent、Planner Agent、Writer Agent、Reviewer Agent、Rewriter Agent。冻结内容包括：每个 Agent 负责什么、不负责什么、输入来源与必需项、输出对象与禁止项、方向性 Step 序列、Tool 白名单、Tool 黑名单、side_effect_level、degraded / partial_success / failed 行为，以及五 Agent 之间的数据交接规则。

P1-03 是 P1-01（AgentRuntime）和 P1-02（AgentWorkflow）的下游模块。P1-01 定义了 AgentStep 如何通过 PPAO 执行；P1-02 定义了 Agent 之间如何编排；P1-03 定义每个 Agent 内部具体做什么、用什么、产出什么。

### 1.2 设计范围

本模块覆盖：

- AgentType 与 AgentCapability 定义。
- AgentInput / AgentOutput 通用结构。
- AgentStepPlan 方向。
- AgentExecutionProfile 方向。
- AgentToolPermission 模型。
- AgentResultRef 规则。
- Memory Agent 完整职责、输入输出、Step 序列、Tool 权限。
- Planner Agent 完整职责、输入输出、Step 序列、Tool 权限。
- Writer Agent 完整职责、输入输出、Step 序列、Tool 权限。
- Reviewer Agent 完整职责、输入输出、Step 序列、Tool 权限。
- Rewriter Agent 完整职责、输入输出、Step 序列、Tool 权限。
- 五 Agent Tool 权限矩阵。
- 五 Agent side_effect_level 设计。
- 五 Agent 之间的数据交接。
- 五 Agent 与确认门（DirectionSelection / PlanConfirmation / HumanReviewGate / MemoryReviewGate）的关系。
- 五 Agent 与 Conflict Guard 的关系。
- 五 Agent 与 P0 能力的复用关系。
- 五 Agent 的错误处理与降级规则。

### 1.3 不覆盖范围

P1-03 不覆盖：

- AgentRuntime 状态机与 PPAO 执行机制（属于 P1-01）。
- AgentWorkflow Stage / Transition / Decision 详细规则（属于 P1-02）。
- 四层剧情轨道数据结构（属于 P1-04）。
- A/B/C 方向推演算法（属于 P1-05）。
- ChapterPlan 完整结构（属于 P1-05）。
- CandidateDraftVersion 版本链详细设计（属于 P1-06）。
- AI Suggestion 类型系统（属于 P1-07）。
- Conflict Guard 规则矩阵（属于 P1-08）。
- StoryMemory Revision 数据结构（属于 P1-09）。
- AgentTrace 完整字段（属于 P1-10）。
- API 路由 / DTO / 前端展示（属于 P1-11）。
- P2 自动连续续写队列。
- 正文 token streaming。
- AI 自动 apply。
- AI 自动写正式正文。

### 1.4 与 P1 总纲的关系

P1 总纲已冻结以下与 P1-03 直接相关的前提：

1. P1 必须覆盖五类 Agent 完整职责与编排（Memory Agent、Planner Agent、Writer Agent、Reviewer Agent、Rewriter Agent）。
2. AgentPermissionPolicy（每个 Agent 的可调用 Tool 白名单与禁止行为）属于 P1-03。
3. 完整 Tool 权限矩阵（扩展 P0 ToolFacade 权限模型）属于 P1-03。
4. PPAO 是 Agent 内部执行机制（P1-01 冻结）。
5. Workflow 是 Agent 间编排顺序（P1-02 冻结）。
6. Agent 不直接执行 Tool，必须通过 AgentRuntime → ToolFacade 调用。

### 1.5 与 P1-01 AgentRuntime 的关系

P1-03 继承 P1-01 的以下冻结结论：

| P1-01 冻结结论 | P1-03 继承方式 |
|---|---|
| PPAO 是 Agent 内部执行机制 | 五 Agent 的每个 Step 在 PPAO 循环中执行，P1-03 定义 Step 序列但不定义 PPAO 机制 |
| AgentRuntimeService 提供 run_next_step 等接口 | 五 Agent 的 Step 由 AgentOrchestrator 通过 run_next_step 触发，Agent 不自行调用 |
| AgentSession / AgentStep / AgentObservation / AgentResult | P1-03 使用这些模型承载 Agent 执行，不新增 Runtime 层实体 |
| caller_type = agent 不能执行 user_action 专属操作 | 五 Agent 全部以 agent 身份运行，不持有 user_action 权限 |
| Agent 不直接执行 Tool | 五 Agent 通过 AgentRuntime → ToolFacade 调用 Tool |
| ToolFacade 是唯一受控入口 | 五 Agent 的 Tool 调用全部经过 ToolFacade 权限校验 |
| Agent 不持有 formal_write 权限 | 五 Agent 全部 formal_write_forbidden |
| partial_success 必须存在至少一个可交付 result_ref | 继承，Writer/Rewriter 无产出则不能 partial_success |

### 1.6 与 P1-02 AgentWorkflow 的关系

P1-03 继承 P1-02 的以下冻结结论：

| P1-02 冻结结论 | P1-03 继承方式 |
|---|---|
| 五 Agent 编排顺序：Memory → Planner → Writer → Reviewer → [Rewriter → Reviewer] | P1-03 按此顺序定义各 Agent 的输入来源和输出去向 |
| WorkflowStage 与 responsible_agent_type 的对应关系 | P1-03 中每个 Agent 的 Step 序列与对应 Stage 对齐 |
| P1-02 中的 responsible_agent_type 和 action 名称都是方向性引用 | P1-03 冻结最终 agent_type 名称和 action 清单 |
| AgentOrchestrator 负责决定下一个 Agent / Stage | Agent 不自行切换 Stage，只通过 AgentOutput.decision_hint 提供建议 |
| waiting_for_user 不能被 Agent 自动跳过 | Agent 进入等待状态后必须停止，由 Workflow 层面和 user_action 推进 |

### 1.7 与 P0 的关系

P1-03 的 Agent 在以下方面复用 P0 能力：

| P0 成果 | P1-03 复用方式 |
|---|---|
| ToolFacade 权限模型 | 扩展为五 Agent Tool 权限矩阵 |
| StoryMemory / StoryState | Memory Agent 读取，不直接修改 |
| ContextPack | Writer Agent 使用 ContextPack 作为输入 |
| CandidateDraft / HumanReviewGate | Writer/Rewriter Agent 产出 CandidateDraft/CandidateDraftVersion，不自动 apply |
| AIReview | Reviewer Agent 复用 P0 AIReview 维度和方法方向 |
| AIJobSystem | Agent 不直接操作 AIJob，AIJob 由 AgentRuntimeService 管理 |
| V1.1 Local-First | Agent 完全不接触正式正文保存链路 |

---

## 二、五 Agent 总体职责边界

### 2.1 五 Agent 总览

| Agent | 定位 | 一句话职责 |
|---|---|---|
| Memory Agent | 记忆感知与建议 | 读取 StoryMemory / StoryState，准备记忆上下文，可选生成 MemoryUpdateSuggestion |
| Planner Agent | 方向推演与计划 | 生成 Direction Proposal（A/B/C）和 ChapterPlan，准备 WritingTask |
| Writer Agent | 候选稿生成 | 基于确认后的计划和 ContextPack 生成 CandidateDraft |
| Reviewer Agent | 审阅与建议 | 审阅 CandidateDraft / CandidateDraftVersion，输出 ReviewReport / ReviewIssue |
| Rewriter Agent | 候选稿修订 | 基于 ReviewReport / 用户反馈生成 CandidateDraftVersion |

### 2.2 五 Agent 与 PPAO

每个 Agent 内部的 Step 序列在 PPAO 循环中执行。P1-03 定义每个 Agent 的 Step（相当于 PPAO 中 Planning 阶段的 output 方向），但：

- Perception 阶段由 AgentRuntime 根据 AgentRunContext 统一处理。
- Planning 阶段由 Agent 自身逻辑（经 AgentRuntime 调度）根据 AgentStepPlan 决定。
- Action 阶段由 AgentRuntime 通过 ToolFacade 执行 Tool 调用。
- Observation 阶段由 AgentRuntime 记录并传递给 AgentOrchestrator。

Agent 不自行控制 PPAO 状态机，不自行切换 AgentStep 状态。

### 2.3 五 Agent 与 Workflow

- Agent 不自行决定下一个 Agent 或下一个 Stage。
- Agent 的 AgentOutput.decision_hint 只是方向性建议。
- 最终 WorkflowDecision 由 AgentOrchestrator 基于 WorkflowPolicy 和 AgentObservation 产生。
- Agent 不绕过 WorkflowStage 的进入/退出条件。

### 2.4 五 Agent 与 ToolFacade

- Agent 的所有 Tool 调用必须通过 AgentRuntime → ToolFacade 链路。
- Agent 不直接 import / 引用 ToolFacade。
- Agent 不直接构造 ToolExecutionContext。
- Agent 的 Tool 权限由 AgentToolPermission 定义，由 ToolFacade 在调用时执行校验。

### 2.5 五 Agent 与 user_action

- Agent 的 caller_type 固定为 agent。
- Agent 不能执行 user_action 专属操作。
- Agent 不能 accept / reject / apply CandidateDraft。
- Agent 不能 confirm Direction / ChapterPlan / MemoryRevision。
- Agent 不能 formal_write。

### 2.6 五 Agent 禁止事项（共同）

1. 禁止直接访问 Provider / ModelRouter / Repository / DB。
2. 禁止直接写正式正文。
3. 禁止执行 accept / reject / apply CandidateDraft。
4. 禁止确认 DirectionSelection / PlanConfirmation。
5. 禁止确认 MemoryRevision。
6. 禁止绕过 Conflict Guard 修改正式资产。
7. 禁止伪造 user_action。
8. 禁止自动跳过 waiting_for_user。
9. 禁止直接调用 ToolFacade。
10. 禁止直接构造 ToolExecutionContext。
11. 禁止持有 formal_write 权限。
12. 禁止记录完整正文 / 完整 Prompt / API Key 到 AgentOutput。

---

## 三、通用 Agent 模型

### 3.1 AgentType

| agent_type | 枚举值 | 说明 |
|---|---|---|
| memory | memory | Memory Agent |
| planner | planner | Planner Agent |
| writer | writer | Writer Agent |
| reviewer | reviewer | Reviewer Agent |
| rewriter | rewriter | Rewriter Agent |

### 3.2 AgentCapability

每个 Agent 的能力标签方向：

| Agent | 能力标签 |
|---|---|
| Memory Agent | story_context_read, memory_gap_detection, memory_update_suggestion |
| Planner Agent | direction_proposal, chapter_planning, writing_task_preparation |
| Writer Agent | candidate_generation, candidate_validation |
| Reviewer Agent | consistency_review, style_review, plot_review, issue_reporting |
| Rewriter Agent | candidate_revision, revision_validation |

### 3.3 AgentInput

通用 AgentInput 结构方向：

| 字段 | 类型 | 说明 |
|---|---|---|
| session_id | string | AgentSession ID |
| workflow_type | enum | continuation_workflow / revision_workflow / planning_workflow / memory_update_workflow / review_workflow / full_workflow |
| stage | enum | 当前 WorkflowStage |
| agent_type | enum | 当前 Agent 类型 |
| work_id | string | 作品 ID |
| chapter_id | string | 章节 ID |
| user_instruction | string | 用户指令，可选 |
| context_refs | ResultRef[] | 上游传入的安全引用（如 memory_context_ref、selected_direction_id） |
| selected_direction_id | string | 已选方向 ID，可选 |
| selected_chapter_plan_id | string | 已选章节计划 ID，可选 |
| current_candidate_draft_id | string | 当前候选稿 ID，可选 |
| current_candidate_version_id | string | 当前候选稿版本 ID，可选 |
| review_id | string | ReviewReport ID，可选 |
| allow_degraded | boolean | 是否允许 degraded 上下文 |
| warning_codes | string[] | 上游传入的 warning |
| metadata | object | 扩展元数据 |

AgentInput 不包含完整正文、完整 ContextPack、完整 Prompt、API Key。

### 3.4 AgentOutput

通用 AgentOutput 结构方向：

| 字段 | 类型 | 说明 |
|---|---|---|
| agent_type | enum | 当前 Agent 类型 |
| step_id | string | 当前 AgentStep ID |
| status | enum | step 状态：succeeded / failed / partial / degraded |
| result_refs | ResultRef[] | 可交付结果安全引用 |
| warning_codes | string[] | warning 列表 |
| error_code | string | 错误码 |
| decision_hint | enum | 方向性建议：continue / retry / wait_user / fail / complete |
| suggested_next_stage | enum | 建议的下一 stage，可选 |
| requires_user_action | boolean | 是否需要用户动作 |
| metadata | object | 扩展元数据，包含 degraded_context_summary 等 |

AgentOutput 只提供 decision_hint，最终 WorkflowDecision 由 AgentOrchestrator 产生。Agent 不通过 AgentOutput 切换 WorkflowStage。

AgentOutput 不包含完整正文、完整 Prompt、API Key。

### 3.5 AgentStepPlan

AgentStepPlan 是一次 Agent 执行的方向性步骤计划：

| 字段 | 类型 | 说明 |
|---|---|---|
| plan_id | string | 计划 ID |
| agent_type | enum | Agent 类型 |
| steps | AgentStepDef[] | 有序步骤列表 |
| expected_result_refs | string[] | 期望产出引用类型 |
| allow_degraded | boolean | 是否允许降级 |
| max_retry | integer | 最大重试次数，默认 1 |

AgentStepDef 方向：

| 字段 | 类型 | 说明 |
|---|---|---|
| step_name | string | 步骤名称 |
| step_order | integer | 步骤序号 |
| action | string | 动作名称 |
| required_tools | string[] | 需要的 Tool 名称 |
| expected_output_ref | string | 期望的产出引用 key |

### 3.6 AgentExecutionProfile

每个 Agent 的执行配置方向：

| 字段 | 类型 | 说明 |
|---|---|---|
| agent_type | enum | Agent 类型 |
| model_role | enum | analysis / planning / writer / reviewer / rewriter |
| default_timeout | integer | 默认超时（秒），默认 300 |
| max_retry | integer | 最大重试次数，默认 1 |
| allow_degraded | boolean | 是否允许 degraded |
| allowed_tool_names | string[] | Tool 白名单 |
| denied_tool_names | string[] | Tool 黑名单 |
| max_output_chars | integer | 最大输出字符数，可选 |
| output_schema_key | string | 输出 schema 标识 |
| trace_level | enum | minimal / standard / verbose |
| metadata | object | 扩展元数据 |

model_role 方向：

| agent_type | model_role | 说明 |
|---|---|---|
| memory | analysis | 理解与分析的模型角色 |
| planner | planning | 规划与推演的模型角色 |
| writer | writer | 写作生成的模型角色 |
| reviewer | reviewer | 审阅评估的模型角色 |
| rewriter | rewriter | 修订改写的模型角色 |

model_role 只是传给 Core / ModelRouter 的角色标识方向。Agent 不直接调用 ModelRouter。AgentRuntime / Core Application Service 通过 ToolFacade 间接完成模型调用。

### 3.7 AgentToolPermission

单个 Tool 的 Agent 权限定义方向：

| 字段 | 类型 | 说明 |
|---|---|---|
| tool_name | string | Tool 名称 |
| agent_type | enum | Agent 类型 |
| permission | enum | allow / deny / conditional |
| side_effect_level | enum | read_only / analysis_write / draft_write / suggestion_write / memory_suggestion_write / formal_write_forbidden |
| requires_user_action | boolean | 是否需要 user_action |
| allow_degraded | boolean | 是否允许 degraded 下调用 |
| retryable | boolean | 是否可重试 |
| notes | string | 备注 |

### 3.8 AgentResultRef

Agent 产出的安全引用方向：

| 字段 | 类型 | 说明 |
|---|---|---|
| ref_type | string | 引用类型（如 candidate_draft、review_report） |
| ref_id | string | 引用实体 ID |
| ref_summary | string | 引用摘要，可选 |
| created_at | string | 创建时间 |

规则：

- AgentOutput.result_refs 使用 AgentResultRef 格式。
- 不包含完整正文、完整 Prompt、完整 ContextPack。
- 交接数据时只传 safe_ref，下游 Agent 通过 ToolFacade 读取实际内容。

---

## 四、Memory Agent 详细设计

### 4.1 职责

Memory Agent 负责在 AgentWorkflow 中读取、整理、感知 StoryMemory / StoryState，为下游 Agent 准备记忆上下文基础。可选地在 CandidateDraft apply 后生成 MemoryUpdateSuggestion。

核心职责：

1. 读取当前作品的 StoryMemory / StoryState。
2. 检测记忆缺口（缺失的人物状态、未记录的情节变化、过时的设定信息）。
3. 生成 memory_context_summary，供 Planner / Writer 使用。
4. 可选：在 CandidateDraft apply 后，基于新旧正文状态的变化生成 MemoryUpdateSuggestion。

### 4.2 不负责什么

Memory Agent 不负责：

- 不直接写正式 StoryMemory。
- 不确认 MemoryRevision。
- 不自动 apply MemoryUpdateSuggestion。
- 不绕过 MemoryReviewGate。
- 不修改 StoryState analysis_baseline（这属于 P0 初始化流程或 P1-09 的 StoryMemoryRevision 路径）。
- 不直接调用 VectorRecall / ContextPack 的完整构建管线（这些属于 P0-06 ContextPackService）。

### 4.3 输入

**必需输入**：

- work_id：作品 ID。
- chapter_id（可选，用于限定上下文范围）。
- session_id。

**可选输入**：

- user_instruction：用户对记忆关注点的指令。
- applied_candidate_ref：来自 HumanReviewGate apply 后的已应用候选稿引用（仅在 memory_suggestion 阶段）。
- chapter_version_ref：apply 后的正文版本引用（仅在 memory_suggestion 阶段）。

**不接受的输入**：

- 完整正文。
- 完整 ContextPack。
- 正式 StoryMemory 的直接写权限。

### 4.4 输出

**主要输出**：

| result_ref | 说明 |
|---|---|
| memory_context_ref | 记忆上下文摘要引用 |
| memory_warning_refs | 记忆缺口 / 风险提示引用 |

**可选输出（仅在 memory_suggestion 阶段）**：

| result_ref | 说明 |
|---|---|
| memory_update_suggestion_ref | MemoryUpdateSuggestion 引用 |

**禁止输出**：

- 正式 MemoryRevision。
- 正式 StoryMemory 写入。
- formal_write 相关任何内容。

### 4.5 Step 序列（方向性）

```text
step_1: perceive_story_state
  读取当前 StoryState analysis_baseline，确认作品进展位置

step_2: collect_memory_context
  读取 StoryMemory，收集人物、设定、伏笔、时间线等记忆上下文

step_3: detect_memory_gaps
  检测记忆缺口：过期信息、缺失事件、不一致状态
  产出 memory_warning_refs

step_4: produce_memory_context_summary
  生成 memory_context_summary
  产出 memory_context_ref

step_5: optionally_propose_memory_update（可选，仅在 memory_suggestion 阶段）
  基于已应用的 CandidateDraft 变化生成 MemoryUpdateSuggestion
  产出 memory_update_suggestion_ref
```

Step 说明：

- step_1 ~ step_4 对应 memory_context_prepare 阶段。
- step_5 对应 memory_suggestion 阶段。
- step_5 仅在 continuation_workflow 的 human_review_waiting apply 成功 + allow_memory_suggestion_after_apply = true 时激活。
- 每个 Step 在 PPAO 中独立推进，Step 间通过 AgentRuntime 传递上下文。

### 4.6 可调用 Tool

| tool_name | permission | side_effect_level | 说明 |
|---|---|---|---|
| read_story_memory | allow | read_only | 读取 StoryMemory |
| read_story_state | allow | read_only | 读取 StoryState |
| read_context_pack | allow | read_only | 读取 ContextPack 摘要 |
| read_chapter_plan | allow | read_only | 读取章节计划（了解叙事方向） |
| read_candidate_draft | allow | read_only | 读取已 apply 的候选稿 |
| create_memory_update_suggestion | allow | memory_suggestion_write | 创建记忆更新建议 |
| create_agent_observation | allow | analysis_write | 记录 AgentObservation |
| create_agent_trace_event | allow | analysis_write | 记录 Trace 事件 |

### 4.7 禁止 Tool

| tool_name | 原因 |
|---|---|
| generate_candidate_draft | 不属于 Memory Agent 职责 |
| create_candidate_version | 不属于 Memory Agent 职责 |
| create_review_report | 不属于 Memory Agent 职责 |
| formal_write（所有 formal 写操作） | formal_write_forbidden |
| accept / reject / apply CandidateDraft | user_action 专属 |
| confirm_memory_revision | user_action 专属 |
| 任何直接操作 Provider / ModelRouter 的 Tool | 安全边界 |

### 4.8 degraded / blocked

- **blocked**：StoryMemory 不可用且不可恢复 → 标记 error_code，Memory Agent failed。此时 Workflow 可能进入 failed 或 waiting_for_user。
- **degraded**：部分 StoryMemory / StoryState 信息缺失但核心结构完整 → 产出 memory_warning_refs，AgentOutput.warning_codes 包含 memory_partial_stale / story_state_incomplete。
- 不得伪造 memory ready。关键记忆缺失必须标记为 blocked，不得以 degraded 掩盖。

### 4.9 failure / partial_success

- **failed**：无法完成 memory_context_prepare → 不产出 memory_context_ref → Workflow 进入 failed 或 waiting_for_user。
- **partial_success**：Memory Agent 在 continuation_workflow 中较少独立判定 partial_success。如果 memory_context_prepare 成功但 memory_suggestion 失败 → memory_suggestion 是可选阶段，不影响 completed 判定。
- Memory Agent 的 failure 通常阻断 Planner Agent 启动（因为 memory_context_ref 不可用）。

### 4.10 与 StoryMemoryRevision 的边界

- Memory Agent 只生成 MemoryUpdateSuggestion，不生成 MemoryRevision。
- MemoryRevision 的形成需要 MemoryReviewGate 用户确认。
- MemoryUpdateSuggestion 的结构由 P1-09 冻结，P1-03 只定义 Memory Agent 作为建议的生成者。

### 4.11 与 P0 初始化分析的关系

- P0 初始化分析（Initialization）生成初始 StoryMemory / StoryState。
- Memory Agent 在 P1 中读取这些成果，但不重新执行完整的初始化分析。
- Memory Agent 的感知可以比 P0 初始化更深（例如检测记忆缺口），但基础数据结构复用 P0。

---

## 五、Planner Agent 详细设计

### 5.1 职责

Planner Agent 负责基于 Memory Agent 的记忆上下文，生成 Direction Proposal（A/B/C）、ChapterPlan 和 WritingTask，为 Writer Agent 的写作提供方向约束和计划输入。

核心职责：

1. 读取 memory_context_ref 和记忆上下文。
2. 生成多个剧情方向选项（Direction Proposal A/B/C）。
3. 根据用户选择的方向生成章节计划（ChapterPlan）。
4. 准备 WritingTask。

### 5.2 不负责什么

Planner Agent 不负责：

- 不自动选择方向（DirectionSelection 是用户确认门）。
- 不自动确认章节计划（PlanConfirmation 是用户确认门）。
- 不直接生成正文。
- 不生成 CandidateDraft。
- 不修改正式章节大纲或正式剧情资产（除非通过 AI Suggestion 路径经用户确认）。
- 不绕过 DirectionSelection / PlanConfirmation。

### 5.3 输入

**必需输入**：

- work_id。
- chapter_id。
- memory_context_ref：来自 Memory Agent 的记忆上下文引用。
- session_id。

**可选输入**：

- user_instruction：用户对方向和计划的意图描述。
- selected_direction_id：仅在 chapter_plan 阶段，用户已选择方向后传入。
- writing_constraints：写作约束（如字数范围、风格偏好），可选。

**不接受的输入**：

- 完整正文。
- 正式章节大纲的直接写权限。

### 5.4 输出

**主要输出**：

| result_ref | 说明 |
|---|---|
| direction_proposal_ref | Direction Proposal 引用（包含 A/B/C 方向） |
| chapter_plan_ref | ChapterPlan 引用 |
| writing_task_ref | WritingTask 引用 |

**可选输出**：

| result_ref | 说明 |
|---|---|
| planning_warning_refs | 计划不确定性或风险提示 |

**禁止输出**：

- CandidateDraft 正文。
- 自动选择的方向 ID（选择必须由用户完成）。
- 自动确认的章节计划 ID（确认必须由用户完成）。
- formal_write 相关任何内容。

### 5.5 Step 序列（方向性）

```text
step_1: read_memory_context
  读取 Memory Agent 产出的 memory_context_ref

step_2: generate_direction_options
  基于记忆上下文生成 A/B/C 三个剧情方向
  产出 direction_proposal_ref（包含 direction_a / direction_b / direction_c）

step_3: evaluate_direction_options
  评估各个方向的可行性、风险、叙事潜力
  可选产出 planning_warning_refs

step_4: wait_direction_selection
  此步骤由 Workflow 进入 direction_selection_waiting
  Planner Agent 在此停止，不自动选择方向
  AgentOutput.decision_hint = wait_user
  AgentOutput.requires_user_action = true

step_5: generate_chapter_plan
  在用户选择方向后（selected_direction_id 传入）生成章节计划
  产出 chapter_plan_ref

step_6: prepare_writing_task
  生成 WritingTask，供 Writer Agent 使用
  产出 writing_task_ref
```

Step 说明：

- step_1 ~ step_3 对应 planning_prepare 阶段。
- step_4 是等待点，Agent 不能自动越过。
- step_5 ~ step_6 在用户确认方向后执行，对应章节计划生成阶段。

### 5.6 可调用 Tool

| tool_name | permission | side_effect_level | 说明 |
|---|---|---|---|
| read_story_memory | allow | read_only | 读取 StoryMemory |
| read_story_state | allow | read_only | 读取 StoryState |
| read_context_pack | allow | read_only | 读取 ContextPack 结构 |
| read_direction_proposal | allow | read_only | 读取已有 Direction Proposal |
| create_direction_proposal | allow | suggestion_write | 创建 Direction Proposal |
| read_chapter_plan | allow | read_only | 读取已有 ChapterPlan |
| create_chapter_plan | allow | suggestion_write | 创建 ChapterPlan |
| read_writing_task | allow | read_only | 读取已有 WritingTask |
| create_writing_task | allow | suggestion_write | 创建 WritingTask |
| create_agent_observation | allow | analysis_write | 记录 AgentObservation |
| create_agent_trace_event | allow | analysis_write | 记录 Trace 事件 |

### 5.7 禁止 Tool

| tool_name | 原因 |
|---|---|
| generate_candidate_draft | 不属于 Planner Agent 职责 |
| create_candidate_version | 不属于 Planner Agent 职责 |
| create_review_report | 不属于 Planner Agent 职责 |
| confirm_direction | user_action 专属 |
| confirm_chapter_plan | user_action 专属 |
| formal_write（所有 formal 写操作） | formal_write_forbidden |
| 任何直接操作 Provider / ModelRouter 的 Tool | 安全边界 |

### 5.8 DirectionProposal 边界

- P1-03 只定义 Planner Agent 产出 Direction Proposal 这个能力方向。
- Direction Proposal 的具体数据结构、A/B/C 标签、评分维度由 P1-05 冻结。
- Planner Agent 不允许只生成 1 个方向后就自动确认。默认生成 A/B/C 三个方向，是否允许 2 个或 1 个由 P1-05 确认。

### 5.9 ChapterPlan 边界

- P1-03 只定义 Planner Agent 产出 ChapterPlan 这个能力方向。
- ChapterPlan 的完整结构（scene 序列、节奏、POV、字数分配）由 P1-05 冻结。
- Planner Agent 不得在用户确认前把 ChapterPlan 直接送入 Writer。

### 5.10 DirectionSelection / PlanConfirmation 边界

- DirectionSelection 和 PlanConfirmation 是用户确认门，不是 Planner Agent 的 Step。
- Planner Agent 在 step_4（wait_direction_selection）时必须停止，AgentOutput.requires_user_action = true。
- Planner Agent 不得自动选择 direction_id，不得自动确认 chapter_plan_id。

### 5.11 failure / degraded

- **degraded**：记忆上下文不完整但方向推演仍可进行 → planning_warning_refs 标记，可继续。
- **failed**：无法生成任何方向（StoryMemory 完全不可用、作品结构无法解析等）→ failed。
- Planner Agent 无法生成方向时，Workflow 可进入 failed 或 waiting_for_user（等待用户手动输入方向）。

---

## 六、Writer Agent 详细设计

### 6.1 职责

Writer Agent 负责基于用户确认后的 Direction / ChapterPlan / ContextPack / WritingTask 生成 CandidateDraft。Writer Agent 是唯一能生成正文候选稿的 Agent。

核心职责：

1. 读取已确认的 Direction 和 ChapterPlan。
2. 读取 ContextPack（由 Core Application 构建）。
3. 读取 WritingTask。
4. 生成 CandidateDraft 正文。
5. 对生成结果进行基础校验（字数、格式、完整性）。

### 6.2 不负责什么

Writer Agent 不负责：

- 不直接写正式正文。
- 不 apply CandidateDraft。
- 不 accept / reject CandidateDraft。
- 不自动确认方向或计划。
- 不绕过 HumanReviewGate。
- 不直接调用 ModelRouter（由 AgentRuntime 内部经 ToolFacade 间接调用）。
- 不修改原 CandidateDraft（修订由 Rewriter Agent 负责）。

### 6.3 输入

**必需输入**：

- work_id。
- chapter_id。
- selected_direction_id：用户已选择的方向 ID。
- selected_chapter_plan_id：用户已确认的章节计划 ID。
- writing_task_ref：WritingTask 引用。
- context_pack_ref：ContextPack 引用（由 writing_prepare 阶段构建）。
- session_id。

**可选输入**：

- user_instruction：用户对写作风格、内容、关键场景的指令。
- writing_constraints：字数、节奏、POV 等约束。

**不接受的输入**：

- 正式正文的直接写权限。
- 完整 StoryMemory / StoryState 的直接修改权限。

### 6.4 输出

**主要输出**：

| result_ref | 说明 |
|---|---|
| candidate_draft_ref | CandidateDraft 引用 |

**可选输出**：

| result_ref | 说明 |
|---|---|
| writing_warning_refs | 生成风险提示（如上下文不完整、字数偏差） |

**禁止输出**：

- 正式章节正文。
- formal_write 相关任何内容。

### 6.5 Step 序列（方向性）

```text
step_1: read_confirmed_plan
  读取用户已确认的 selected_direction_id 和 selected_chapter_plan_id

step_2: read_context_pack
  读取 ContextPack（Plot Arc + StoryMemory + VectorRecall + WritingTask 上下文）

step_3: generate_candidate_text
  基于计划与上下文生成 CandidateDraft 正文
  产出 candidate_draft_ref

step_4: validate_candidate_output
  校验生成结果的字数、格式、基本完整性
  可选产出 writing_warning_refs

step_5: save_candidate_draft
  持久化 CandidateDraft
  产出最终 candidate_draft_ref
```

Step 说明：

- step_1 ~ step_5 全部在 drafting 阶段执行。
- step_3（generate_candidate_text）是核心步骤，由 AgentRuntime 通过 ToolFacade 调用 generate_candidate_draft Tool。
- 生成结果只进入 CandidateDraft，不进入正式正文。
- 如果 degraded 上下文下生成，step_4 必须标记 writing_warning_refs。

### 6.6 可调用 Tool

| tool_name | permission | side_effect_level | 说明 |
|---|---|---|---|
| read_context_pack | allow | read_only | 读取 ContextPack |
| read_direction_proposal | allow | read_only | 读取方向 |
| read_chapter_plan | allow | read_only | 读取章节计划 |
| read_writing_task | allow | read_only | 读取 WritingTask |
| read_story_memory | allow | read_only | 读取 StoryMemory 参考 |
| read_candidate_draft | allow | read_only | 读取已有候选稿（用于修订参考） |
| generate_candidate_draft | allow | draft_write | 生成 CandidateDraft |
| create_agent_observation | allow | analysis_write | 记录 AgentObservation |
| create_agent_trace_event | allow | analysis_write | 记录 Trace 事件 |

### 6.7 禁止 Tool

| tool_name | 原因 |
|---|---|
| create_candidate_version | 修订由 Rewriter Agent 负责 |
| create_review_report | 不属于 Writer Agent 职责 |
| create_direction_proposal | 不属于 Writer Agent 职责 |
| create_chapter_plan | 不属于 Writer Agent 职责 |
| create_memory_update_suggestion | 不属于 Writer Agent 职责 |
| accept / reject / apply CandidateDraft | user_action 专属 |
| formal_write（所有 formal 写操作） | formal_write_forbidden |
| 任何直接操作 Provider / ModelRouter 的 Tool | 安全边界 |

### 6.8 CandidateDraft 边界

- Writer Agent 的唯一正文输出是 CandidateDraft。
- CandidateDraft 的结构由 P0-09 定义。
- Writer Agent 不自动 apply CandidateDraft。
- Writer Agent 不自动创建 CandidateDraftVersion（修订由 Rewriter Agent 负责）。

### 6.9 degraded 写作规则

- Writer Agent 可在 allow_degraded = true 时接受 degraded 上下文。
- degraded 下生成必须：
  - AgentOutput.warning_codes 包含 context_degraded 等标记。
  - CandidateDraft.metadata 中包含 degraded_context_summary。
  - step_4（validate_candidate_output）特别关注上下文不足导致的质量风险。
- degraded 下生成质量不满意时，用户可 reject 或触发 revision_workflow。

### 6.10 failure / partial_success

- **failed**：未生成 CandidateDraft → AgentOutput.status = failed → Workflow 进入 failed（continuation_workflow 无候选稿即无成果）。
- **partial_success**：Writer Agent 成功但后续 Reviewer 失败 → CandidateDraft 仍可交付 → Workflow 可能 partial_success。
- Writer Agent 自身的 partial_success 较少见，因为它要么产出 CandidateDraft 要么不产出。

### 6.11 与 P0 MinimalContinuationWorkflow 的关系

- P0 MinimalContinuationWorkflow 是 P1 Writer Agent 的轻量前身。
- P1 Writer Agent 在 P0 基础上增加：
  - 接入 Planner Agent 的方向和计划输入。
  - 更完整的 degraded 处理。
  - 与 Reviewer / Rewriter Agent 的数据交接。
- P0 路径作为兼容模式保留，Writer Agent 是 P1 主链路的默认写作 Agent。

---

## 七、Reviewer Agent 详细设计

### 7.1 职责

Reviewer Agent 负责对 CandidateDraft / CandidateDraftVersion 执行多维度审阅，输出 ReviewReport / ReviewIssue，为 HumanReviewGate 提供辅助判断依据，为 Rewriter Agent 提供修订建议。

核心职责：

1. 读取 CandidateDraft 或 CandidateDraftVersion。
2. 执行一致性审阅（与 StoryMemory、Plot Arc、人物设定的一致性）。
3. 执行风格审阅（与作品风格画像的一致性）。
4. 执行剧情推进审阅（节奏、信息密度、伏笔处理）。
5. 生成 ReviewReport，包含 ReviewIssue 列表。
6. 可选：生成 AI Suggestion（通过 create_ai_suggestion Tool）。
7. 提出修订建议或标记 candidate_ready。

### 7.2 不负责什么

Reviewer Agent 不负责：

- 不 accept / reject / apply CandidateDraft。
- 不自动阻断 CandidateDraft 进入 HumanReviewGate。
- 不自动驳回候选稿。
- 不直接修改正文。
- 不执行 Conflict Guard 检查（Conflict Guard 在 Core Application 层）。
- ReviewReport 只是辅助判断，不是最终裁决。

### 7.3 输入

**必需输入**：

- candidate_draft_ref 或 candidate_version_ref。
- work_id。
- chapter_id。
- session_id。

**可选输入**：

- review_id：如果是二次审阅（修订后），可传入上一次的 ReviewReport ID。
- user_instruction：用户特别关注的审阅维度。

**不接受的输入**：

- 正式正文的直接修改权限。
- accept / reject / apply 权限。

### 7.4 输出

**主要输出**：

| result_ref | 说明 |
|---|---|
| review_report_ref | ReviewReport 引用 |

**可选输出**：

| result_ref | 说明 |
|---|---|
| review_issue_refs | ReviewIssue 列表引用 |
| quality_score | 质量评分，可选 |
| rewrite_recommendation | 修订建议（是否建议进入 Rewriter） |
| ai_suggestion_refs | AI Suggestion 引用（如一致性风险建议） |

**禁止输出**：

- accept / reject / apply 决策。
- 对 CandidateDraft 的自动修改。
- 正式正文写入。

### 7.5 Step 序列（方向性）

```text
step_1: read_candidate_draft
  读取 CandidateDraft 或 CandidateDraftVersion 正文

step_2: evaluate_consistency
  评估候选稿与 StoryMemory / Plot Arc / 人物设定的一致性
  产出 review_issue_refs（一致性类）

step_3: evaluate_style
  评估候选稿与作品风格画像的匹配度
  产出 review_issue_refs（风格类）

step_4: evaluate_plot_progress
  评估候选稿的剧情推进（节奏、信息密度、伏笔处理）
  产出 review_issue_refs（剧情类）

step_5: produce_review_report
  汇总各维度评估结果为 ReviewReport
  产出 review_report_ref

step_6: recommend_rewrite_or_ready
  根据审阅结果建议是否进入 Rewriter 或标记为 candidate_ready
  AgentOutput.decision_hint = enter_rewriter 或 continue
```

Step 说明：

- step_1 ~ step_6 在 reviewing 或 final_reviewing 阶段执行。
- Reviewer Agent 只提供建议，不自动裁决。
- 如果 Reviewer Agent 标记 blocking 风险（如与正式设定严重冲突），AgentOrchestrator 应进入 waiting_for_user。

### 7.6 可调用 Tool

| tool_name | permission | side_effect_level | 说明 |
|---|---|---|---|
| read_candidate_draft | allow | read_only | 读取候选稿 |
| read_story_memory | allow | read_only | 读取 StoryMemory 供一致性审阅 |
| read_story_state | allow | read_only | 读取 StoryState |
| read_context_pack | allow | read_only | 读取 ContextPack |
| read_chapter_plan | allow | read_only | 读取原章节计划供对比 |
| read_review_report | allow | read_only | 读取已有 ReviewReport |
| create_review_report | allow | analysis_write | 创建 ReviewReport |
| create_ai_suggestion | conditional | suggestion_write | 创建 AI Suggestion（当审阅发现一致性 / 风格风险时） |
| request_conflict_check | allow | analysis_write | 请求 Conflict Guard 检查（由 Core Application 层执行） |
| read_conflict_status | allow | read_only | 读取冲突状态 |
| create_agent_observation | allow | analysis_write | 记录 AgentObservation |
| create_agent_trace_event | allow | analysis_write | 记录 Trace 事件 |

### 7.7 禁止 Tool

| tool_name | 原因 |
|---|---|
| generate_candidate_draft | 不属于 Reviewer Agent 职责 |
| create_candidate_version | 修订由 Rewriter Agent 负责 |
| create_direction_proposal | 不属于 Reviewer Agent 职责 |
| create_chapter_plan | 不属于 Reviewer Agent 职责 |
| create_memory_update_suggestion | 不属于 Reviewer Agent 职责 |
| accept / reject / apply CandidateDraft | user_action 专属 |
| formal_write（所有 formal 写操作） | formal_write_forbidden |
| 任何直接操作 Provider / ModelRouter 的 Tool | 安全边界 |

### 7.8 ReviewReport / ReviewIssue

- P1-03 定义 Reviewer Agent 产出 ReviewReport 和 ReviewIssue 的方向。
- ReviewReport / ReviewIssue 的具体字段由 P0-10 AIReview 的结构方向继承并扩展。
- P1-03 不冻结 ReviewReport 的完整 schema，只定义方向性内容：
  - 一致性评估（与 StoryMemory / Plot Arc 的一致性）；
  - 风格评估；
  - 剧情推进评估；
  - 修订建议；
  - 风险级别标记。

### 7.9 AIReview 复用关系

- P0-10 AIReview 定义了轻量 AI 审阅的维度和方法。
- Reviewer Agent 复用 P0 AIReview 的维度方向（AIReviewCategory、AIReviewSeverity）。
- Reviewer Agent 扩展 P0 AIReview 为完整的多维度审阅，增加：
  - 与 Plot Arc 的剧情进度一致性；
  - 修订建议（rewrite_recommendation）；
  - 与 Conflict Guard 的协作。

### 7.10 Conflict Guard 关系

- Reviewer Agent 不直接执行 Conflict Guard 检查。
- Reviewer Agent 可通过 request_conflict_check Tool 请求 Core Application 层执行 Conflict Guard。
- Reviewer Agent 可通过 read_conflict_status Tool 读取冲突检查结果。
- 如果冲突为 blocking 级别，Reviewer Agent 应在 review_report 中标记，AgentOutput.decision_hint = wait_user。

### 7.11 failure / partial_success

- **Reviewer Agent 失败不应自动阻断 CandidateDraft 展示**。
- Reviewer 失败时，CandidateDraft 仍可进入 candidate_ready 和 HumanReviewGate。
- Workflow 可判定为 partial_success（CandidateDraft 可交付但缺少审阅报告）。
- 但 blocking Conflict Guard 风险必须阻断 completed，进入 waiting_for_user。

### 7.12 不自动裁决边界

- Reviewer Agent 只能建议，不自动裁决。
- reviewer 产出的 ReviewReport 是"建议"，不是"驳回"。
- 最终是否进入 Rewriter、是否 apply，由用户通过 HumanReviewGate 决定。

---

## 八、Rewriter Agent 详细设计

### 8.1 职责

Rewriter Agent 负责基于 ReviewReport / 用户反馈对 CandidateDraft 进行修订，生成 CandidateDraftVersion。它不覆盖原 CandidateDraft，而是产出新版本。

核心职责：

1. 读取 CandidateDraft 或 CandidateDraftVersion。
2. 读取 ReviewReport（审阅意见）。
3. 读取用户修订指令（如有）。
4. 生成 CandidateDraftVersion（修订稿）。
5. 校验修订结果。

### 8.2 不负责什么

Rewriter Agent 不负责：

- 不覆盖原 CandidateDraft。
- 不 apply CandidateDraft / CandidateDraftVersion。
- 不生成全新的 CandidateDraft（新稿由 Writer Agent 负责）。
- 不绕过 Reviewer Agent 直接进入 candidate_ready。
- 不自动决定是否继续修订（达到 max_revision_rounds 后停止）。
- 不修改正式正文。

### 8.3 输入

**必需输入**：

- base_candidate_draft_id 或 base_candidate_version_id：要修订的基础稿。
- review_report_ref：ReviewReport 引用。
- work_id。
- chapter_id。
- session_id。

**可选输入**：

- user_instruction：用户的修订指令。
- revision_focus：修订重点（如只修风格、只修一致性）。

**不接受的输入**：

- 正式正文的直接修改权限。
- 原 CandidateDraft 的覆盖权限。

### 8.4 输出

**主要输出**：

| result_ref | 说明 |
|---|---|
| candidate_version_ref | CandidateDraftVersion 引用 |

**可选输出**：

| result_ref | 说明 |
|---|---|
| rewrite_summary_ref | 修订摘要（哪些 issue 被处理、哪些未处理） |
| rewrite_warning_refs | 修订风险提示 |

**禁止输出**：

- 覆盖后的 CandidateDraft（原稿不变）。
- 正式章节正文。
- formal_write 相关任何内容。

### 8.5 Step 序列（方向性）

```text
step_1: read_candidate_draft_or_version
  读取要修订的基础稿

step_2: read_review_report
  读取 ReviewReport，提取修订建议和 ReviewIssue

step_3: apply_revision_instruction
  结合 ReviewReport 和用户指令确定修订策略

step_4: generate_candidate_version
  生成 CandidateDraftVersion
  产出 candidate_version_ref

step_5: validate_rewrite_output
  校验修订结果：issue 处理情况、是否引入新问题
  产出 rewrite_summary_ref / rewrite_warning_refs

step_6: save_candidate_version
  持久化 CandidateDraftVersion
  产出最终 candidate_version_ref
```

Step 说明：

- step_1 ~ step_6 在 rewriting 阶段执行。
- revision_round 由 Workflow 层管理，Rewriter Agent 不自行判断轮次。
- 修订稿只作为 CandidateDraftVersion，不修改原 CandidateDraft。

### 8.6 可调用 Tool

| tool_name | permission | side_effect_level | 说明 |
|---|---|---|---|
| read_candidate_draft | allow | read_only | 读取原候选稿 |
| read_review_report | allow | read_only | 读取审阅报告 |
| read_context_pack | allow | read_only | 读取上下文 |
| read_chapter_plan | allow | read_only | 读取原计划 |
| create_candidate_version | allow | draft_write | 创建 CandidateDraftVersion |
| read_conflict_status | allow | read_only | 读取冲突状态 |
| create_agent_observation | allow | analysis_write | 记录 AgentObservation |
| create_agent_trace_event | allow | analysis_write | 记录 Trace 事件 |

### 8.7 禁止 Tool

| tool_name | 原因 |
|---|---|
| generate_candidate_draft | 新稿生成由 Writer Agent 负责 |
| create_direction_proposal | 不属于 Rewriter Agent 职责 |
| create_chapter_plan | 不属于 Rewriter Agent 职责 |
| create_review_report | 审阅由 Reviewer Agent 负责 |
| create_memory_update_suggestion | 不属于 Rewriter Agent 职责 |
| accept / reject / apply CandidateDraft | user_action 专属 |
| formal_write（所有 formal 写操作） | formal_write_forbidden |
| 任何覆盖原 CandidateDraft 的操作 | 安全边界 |
| 任何直接操作 Provider / ModelRouter 的 Tool | 安全边界 |

### 8.8 CandidateDraftVersion 边界

- Rewriter Agent 的唯一正文输出是 CandidateDraftVersion。
- CandidateDraftVersion 与原 CandidateDraft 的关系（parent_version_id、版本链）由 P1-06 冻结。
- Rewriter Agent 不负责管理版本链，只负责生成新版本。

### 8.9 max_revision_rounds

- max_revision_rounds 是 WorkflowPolicy 参数，由 AgentOrchestrator 控制。
- Rewriter Agent 不自行判断 revision_round 是否达到上限。
- 当 revision_round >= max_revision_rounds 时，AgentOrchestrator 不再触发 rewriting stage。

### 8.10 failure / partial_success

- **Rewriter Agent 失败时保留旧 CandidateDraft**。
- 修订失败不删除原候选稿。
- 如果旧 CandidateDraft 仍可交付 → Workflow 可判定 partial_success。
- 修订连续失败（如在 max_revision_rounds 内全部失败）→ 退出修订循环，记录 warning。

---

## 九、五 Agent Tool 权限矩阵

### 9.1 Tool 权限总表

| tool_name | Memory | Planner | Writer | Reviewer | Rewriter |
|---|---|---|---|---|---|
| read_story_memory | allow | allow | allow | allow | deny |
| read_story_state | allow | allow | deny | allow | deny |
| read_context_pack | allow | allow | allow | allow | allow |
| build_context_pack | deny | deny | deny | deny | deny |
| read_direction_proposal | allow | allow | allow | deny | deny |
| create_direction_proposal | deny | allow | deny | deny | deny |
| read_chapter_plan | allow | allow | allow | allow | allow |
| create_chapter_plan | deny | allow | deny | deny | deny |
| read_writing_task | deny | allow | allow | deny | deny |
| create_writing_task | deny | allow | deny | deny | deny |
| generate_candidate_draft | deny | deny | allow | deny | deny |
| read_candidate_draft | allow | deny | allow | allow | allow |
| create_candidate_version | deny | deny | deny | deny | allow |
| read_review_report | deny | deny | deny | allow | allow |
| create_review_report | deny | deny | deny | allow | deny |
| create_ai_suggestion | deny | deny | deny | conditional | deny |
| create_memory_update_suggestion | allow | deny | deny | deny | deny |
| read_conflict_status | deny | deny | deny | allow | allow |
| request_conflict_check | deny | deny | deny | allow | deny |
| create_agent_observation | allow | allow | allow | allow | allow |
| create_agent_trace_event | allow | allow | allow | allow | allow |

说明：

- `build_context_pack` 对所有 Agent deny。ContextPack 构建由 Core Application Service 在 writing_prepare 阶段执行。
- `create_ai_suggestion` 对 Reviewer Agent 为 conditional：仅在审阅发现一致性 / 风格风险时可用。
- Tool 权限矩阵在 AgentRuntime → ToolFacade 调用时执行校验。

### 9.2 side_effect_level 权限总表

| side_effect_level | 允许的 Agent | 说明 |
|---|---|---|
| read_only | 全部 Agent | 读取 StoryMemory、StoryState、ContextPack、CandidateDraft、ReviewReport 等 |
| analysis_write | Memory、Planner、Reviewer | 创建 Observation、Trace 事件、ReviewReport |
| suggestion_write | Planner、Reviewer | 创建 DirectionProposal、ChapterPlan、WritingTask、AI Suggestion |
| draft_write | Writer、Rewriter | 生成 CandidateDraft / CandidateDraftVersion |
| memory_suggestion_write | Memory | 创建 MemoryUpdateSuggestion |
| formal_write_forbidden | 全部 Agent | 所有 Agent 都不能执行 formal_write |

### 9.3 side_effect_level 分层

| level | 值 | 含义 | 是否可自动重试 |
|---|---|---|---|
| read_only | 1 | 只读，无副作用 | 是 |
| analysis_write | 2 | 分析写入（Observation、Trace、ReviewReport） | 是 |
| suggestion_write | 3 | 建议写入（Plan、Suggestion） | 是（但有上限） |
| draft_write | 4 | 草稿写入（CandidateDraft / CandidateDraftVersion） | 是（但有上限） |
| memory_suggestion_write | 5 | 记忆建议写入（MemoryUpdateSuggestion） | 是（但有上限） |
| formal_write_forbidden | — | 正式写入（禁止） | 不适用 |

规则：

- level 1~5 的 Tool 可在 Agent 权限内自动重试。
- formal_write / apply / memory formalize 永远不能自动重试。
- 重试上限由 AgentExecutionProfile.max_retry 和 WorkflowPolicy.max_retry_per_stage 双重约束。

### 9.4 caller_type 规则

- 五 Agent 的 Tool 调用 caller_type 固定为 agent。
- user_action 专属 Tool 不接受 caller_type = agent 的调用。
- ToolFacade 在权限校验时根据 caller_type 拒绝越权调用。

### 9.5 可重试规则

| Tool side_effect_level | 可重试 | 条件 |
|---|---|---|
| read_only | 是 | 默认可重试 1 次 |
| analysis_write | 是 | 默认可重试 1 次 |
| suggestion_write | 是 | 默认可重试 1 次 |
| draft_write | 是 | 默认可重试 1 次，但 generate_candidate_draft / create_candidate_version 通常只重试 1 次 |
| memory_suggestion_write | 是 | 默认可重试 1 次 |
| formal_write / apply / memory formalize | 否 | 永远不可自动重试 |

### 9.6 degraded 规则

| Tool side_effect_level | degraded 下是否可调用 | 条件 |
|---|---|---|
| read_only | 是 | 无 |
| analysis_write | 是 | 产出必须标记 warning_codes |
| suggestion_write | 是 | 产出必须标记 planning_warning_refs |
| draft_write | 是（如果 allow_degraded = true） | 产出必须标记 degraded_context_summary |
| memory_suggestion_write | 是（如果 allow_degraded = true） | 产出必须标记 degraded 来源 |
| formal_write | 否 | 永远禁止 |

---

## 十、五 Agent 数据交接设计

### 10.1 交接原则

1. 交接使用 safe_ref / AgentResultRef，不传完整正文。
2. 下游 Agent 通过 ToolFacade 的 read_* Tool 读取上游产出的实际内容。
3. 交接不传完整 Prompt、完整 ContextPack、API Key。
4. 交接数据由 AgentOrchestrator 在 WorkflowTransition 时通过 AgentInput.context_refs 传递。

### 10.2 Memory Agent → Planner Agent

| 交接内容 | ref_type | 说明 |
|---|---|---|
| memory_context_ref | memory_context | 记忆上下文摘要 |
| memory_warning_refs | memory_warning | 记忆缺口 / 风险提示 |

传递方式：

```text
Memory Agent AgentOutput.result_refs
  → AgentOrchestrator 记录到 WorkflowCheckpoint.result_refs
  → AgentOrchestrator 构建 Planner Agent 的 AgentInput.context_refs
  → Planner Agent 通过 read_story_memory / read_story_state 读取详细内容
```

### 10.3 Planner Agent → Writer Agent

| 交接内容 | ref_type | 说明 |
|---|---|---|
| selected_direction_id | direction | 用户已选择的方向 ID |
| selected_chapter_plan_id | chapter_plan | 用户已确认的章节计划 ID |
| writing_task_ref | writing_task | WritingTask 引用 |

传递方式：

```text
Planner Agent 产出 + 用户确认
  → AgentOrchestrator 在 writing_prepare 阶段构建 ContextPack
  → Writer Agent 的 AgentInput 包含 selected_direction_id / selected_chapter_plan_id / writing_task_ref
  → Writer Agent 通过 read_* Tool 读取详细内容
```

### 10.4 Writer Agent → Reviewer Agent

| 交接内容 | ref_type | 说明 |
|---|---|---|
| candidate_draft_ref | candidate_draft | CandidateDraft 引用 |
| candidate_version_ref | candidate_version | 如果是修订后审阅 |
| writing_warning_refs | writing_warning | 生成风险提示 |

传递方式：

```text
Writer Agent AgentOutput.result_refs
  → AgentOrchestrator 将 CandidateDraft 状态设为 ready（进入 candidate_ready 或直接到 reviewing）
  → Reviewer Agent 的 AgentInput 包含 candidate_draft_ref
  → Reviewer Agent 通过 read_candidate_draft Tool 读取全文
```

### 10.5 Reviewer Agent → Rewriter Agent

| 交接内容 | ref_type | 说明 |
|---|---|---|
| review_report_ref | review_report | ReviewReport 引用 |
| rewrite_recommendation | review_recommendation | 修订建议（在 ReviewReport 内） |

传递方式：

```text
Reviewer Agent AgentOutput.result_refs
  → AgentOrchestrator 根据 review 结果和 WorkflowPolicy 决定是否进入 rewriting
  → Rewriter Agent 的 AgentInput 包含 review_report_ref + base_candidate_draft_id
  → Rewriter Agent 通过 read_review_report / read_candidate_draft Tool 读取详细内容
```

### 10.6 Rewriter Agent → Reviewer Agent

| 交接内容 | ref_type | 说明 |
|---|---|---|
| candidate_version_ref | candidate_version | CandidateDraftVersion 引用 |
| rewrite_summary_ref | rewrite_summary | 修订摘要 |

传递方式：同 Writer → Reviewer，但传递的是 CandidateDraftVersion。

### 10.7 HumanReviewGate apply 后 → Memory Agent

| 交接内容 | ref_type | 说明 |
|---|---|---|
| applied_candidate_ref | candidate_draft | 已 apply 的候选稿引用 |
| chapter_version_ref | chapter_version | apply 后的章节版本引用 |

传递方式：

```text
HumanReviewGate user_action: apply
  → V1.1 Local-First 保存
  → AgentOrchestrator 在 memory_suggestion 阶段传入 applied_candidate_ref
  → Memory Agent 通过 read_candidate_draft 读取已应用候选稿
```

### 10.8 safe_ref / result_ref 规则

1. 交接数据使用 safe_ref 格式：`{ref_type}:{ref_id}`。
2. 下游 Agent 不直接访问上游 Agent 的内部数据结构，只通过 ToolFacade 的 read_* Tool 读取。
3. 不传递完整的 JSON body、Prompt、ContextPack 文本。
4. AgentResultRef 的 ref_summary 可选，用于 Workflow 层的人类可读摘要。

---

## 十一、五 Agent 与确认门关系

### 11.1 DirectionSelection

| 项目 | 说明 |
|---|---|
| 负责产生 | Planner Agent（生成 Direction Proposal A/B/C） |
| 负责确认 | 用户（通过 user_action: confirm_direction） |
| Agent 角色 | Planner Agent 在 step_4 停止，AgentOutput.requires_user_action = true |
| Agent 禁止 | 自动选择方向、自动确认方向 |

### 11.2 PlanConfirmation

| 项目 | 说明 |
|---|---|
| 负责产生 | Planner Agent（生成 ChapterPlan） |
| 负责确认 | 用户（通过 user_action: confirm_chapter_plan） |
| Agent 角色 | Planner Agent 在用户选择方向后生成计划，但不自动确认 |
| Agent 禁止 | 自动确认计划、在确认前将计划送入 Writer |

### 11.3 HumanReviewGate

| 项目 | 说明 |
|---|---|
| 负责产生 | Writer Agent（CandidateDraft）/ Rewriter Agent（CandidateDraftVersion） |
| 负责确认 | 用户（通过 user_action: accept / reject / apply） |
| Agent 角色 | Writer / Rewriter 产出候选稿后停止；Reviewer 提供辅助审阅 |
| Agent 禁止 | accept / reject / apply CandidateDraft |

### 11.4 MemoryReviewGate

| 项目 | 说明 |
|---|---|
| 负责产生 | Memory Agent（MemoryUpdateSuggestion） |
| 负责确认 | 用户（通过 user_action: confirm_memory_revision） |
| Agent 角色 | Memory Agent 产出建议后停止 |
| Agent 禁止 | 自动确认 MemoryRevision、直接写入正式 StoryMemory |

### 11.5 用户确认边界

- Agent 只能提出建议或产出候选对象。
- 所有确认动作必须走 user_action 路径。
- Agent 不得通过任何方式（包括 Tool 调用、AgentOutput 标记）伪造或跳过用户确认。
- AgentOutput.requires_user_action = true 时，AgentOrchestrator 必须进入 waiting_for_user。

---

## 十二、五 Agent 与 Conflict Guard 关系

### 12.1 检查触发点

- Agent 不直接修改正式资产，因此 Agent 不直接触发 Conflict Guard。
- Conflict Guard 在 Core Application 层由以下操作自动触发：
  - AI Suggestion 创建（当建议涉及正式资产时）。
  - MemoryUpdateSuggestion 创建（当建议影响正式 StoryMemory 时）。
  - CandidateDraft apply（由 user_action 触发，非 Agent）。
- Reviewer Agent 可通过 request_conflict_check Tool 请求前置检查。

### 12.2 blocking / warning 处理

- Agent 通过 read_conflict_status Tool 读取冲突状态。
- 如果冲突为 blocking：
  - Agent 停止当前操作。
  - AgentOutput.decision_hint = wait_user。
  - AgentOrchestrator 进入 waiting_for_user。
- Agent 不自动修复冲突。
- Agent 不自动覆盖人物、设定、伏笔、时间线、大纲。

### 12.3 Agent 行为限制

1. Agent 不直接修改正式资产。
2. Agent 不自动覆盖有冲突的资产。
3. Agent 不绕过 Conflict Guard 写入。
4. Agent 不在 blocking 冲突未解决时继续推进。
5. Reviewer Agent 可以标记冲突风险，但不裁决。

---

## 十三、五 Agent 与 P0 能力复用

### 13.1 AI Settings / ModelRouter

- Agent 不直接调用 ModelRouter。
- AgentRuntime 在 Action 阶段通过 ToolFacade 间接调用模型。
- AgentExecutionProfile.model_role 是传给 Core 的角色标识。
- P0 AI Settings 的 Provider 配置、API Key 管理、ModelRouter 路由逻辑保持不变。

### 13.2 AIJobSystem

- Agent 不直接操作 AIJob。
- AIJob 的创建、状态同步、Step 映射由 AgentRuntimeService 内部完成。
- AgentSession 与 AIJob 的关联关系由 P1-01 定义，P1-03 不改变。

### 13.3 ContextPack

- Agent 不直接构建 ContextPack。
- ContextPack 由 Core Application Service 在 writing_prepare 阶段构建。
- Writer Agent 通过 read_context_pack Tool 读取。
- Reviewer Agent 通过 read_context_pack Tool 读取参考。

### 13.4 CandidateDraft / HumanReviewGate

- P0 CandidateDraft 数据结构复用。
- P0 HumanReviewGate 的 accept / reject / apply 流程复用。
- Writer Agent 产出 CandidateDraft，Rewriter Agent 产出 CandidateDraftVersion。
- Agent 不接触 HumanReviewGate 的 user_action 决策。

### 13.5 AIReview

- P0 AIReview 的维度（AIReviewCategory、AIReviewSeverity）方向复用。
- Reviewer Agent 扩展 P0 AIReview 为完整多维度审阅。
- ReviewReport 可以复用部分 AIReviewResult 字段，但 Reviewer Agent 的审阅范围更广。

### 13.6 ToolFacade

- P0 CoreToolFacade 的权限模型复用。
- P1 扩展 Tool 白名单（增加 Agent 专属 Tool）。
- P1 扩展 ToolPermissionPolicy（增加 Agent 维度的权限校验）。
- Tool 调用链路保持不变：AgentRuntime → ToolFacade → Core Application Service。

---

## 十四、错误处理与降级规则

### 14.1 Memory Agent

| 场景 | 行为 |
|---|---|
| StoryMemory 完全不可用 | failed → Workflow 进入 failed 或 waiting_for_user |
| 部分 StoryMemory 信息缺失 | degraded → memory_warning_refs + warning_codes |
| MemoryUpdateSuggestion 生成失败 | 记录 warning，不影响 continuation_workflow completed |
| 不得伪造 ready | 关键记忆缺失 = blocked，不得以 degraded 掩盖 |

### 14.2 Planner Agent

| 场景 | 行为 |
|---|---|
| 无法生成任何方向 | failed → Workflow 进入 failed 或 waiting_for_user |
| 只能生成 1~2 个方向（非 A/B/C 全部） | degraded → planning_warning_refs |
| ChapterPlan 生成失败 | failed → 不进入 Writer |
| 不得自动选择方向 | AgentOutput.requires_user_action = true |

### 14.3 Writer Agent

| 场景 | 行为 |
|---|---|
| 未生成 CandidateDraft | failed → Workflow 进入 failed |
| degraded 上下文下生成 | degraded → writing_warning_refs + degraded_context_summary |
| 生成后校验失败（格式 / 字数严重异常） | 可 retry_step 或 failed |
| 生成成功 | AgentOutput.status = succeeded，产出 candidate_draft_ref |

### 14.4 Reviewer Agent

| 场景 | 行为 |
|---|---|
| ReviewReport 生成失败 | Reviewer 失败不应自动阻断 CandidateDraft 展示 |
| blocking 冲突风险 | AgentOutput.decision_hint = wait_user → 阻断 completed |
| 一致性 / 风格有小问题 | 记录 review_issue_refs，不影响 candidate_ready |

### 14.5 Rewriter Agent

| 场景 | 行为 |
|---|---|
| 修订失败 | 保留原 CandidateDraft，记录 warning |
| 修订未改进 | 记录 rewrite_warning_refs，可退出修订循环 |
| revision_round 达上限 | 不再进入 rewriting（由 Workflow 层控制） |

### 14.6 degraded 传递规则

1. Agent 在 degraded 输入下执行时，AgentOutput.warning_codes 必须包含 degraded 来源。
2. 下游 Agent 收到带 warning_codes 的 AgentInput 时，在自己的 AgentOutput 中保留并追加新的 warning。
3. 最终 WorkflowRun.warning_codes 是整条链路的 warning 聚合。
4. degraded 不得被任何 Agent 伪装为 ready。

### 14.7 partial_success 触发条件

| 条件 | 说明 |
|---|---|
| 至少一个可交付 result_ref | 源自 P1-01 最低原则 |
| continuation_workflow | Writer 成功但 Reviewer 失败可 partial_success |
| revision_workflow | Rewriter 失败但旧稿可用可 partial_success |
| Writer/Rewriter 无产出 | 不能 partial_success → failed |

### 14.8 blocking 风险

- blocking 冲突未处理 → 不得 completed。
- Agent 在遇到 blocking 时必须停止并设置 decision_hint = wait_user。
- Agent 不得自行判断 blocking 是否可忽略。

---

## 十五、P1-03 不做事项清单

P1-03 不做：

1. 不定义 AgentRuntime 状态机（属于 P1-01）。
2. 不定义 WorkflowStage / Transition / Decision 详细规则（属于 P1-02）。
3. 不定义四层剧情轨道结构（属于 P1-04）。
4. 不定义 DirectionProposal 算法（属于 P1-05）。
5. 不定义 ChapterPlan 完整结构（属于 P1-05）。
6. 不定义 CandidateDraftVersion 版本链（属于 P1-06）。
7. 不定义 AI Suggestion 类型系统（属于 P1-07）。
8. 不定义 Conflict Guard 规则矩阵（属于 P1-08）。
9. 不定义 StoryMemoryRevision 数据结构（属于 P1-09）。
10. 不定义 AgentTrace 完整字段（属于 P1-10）。
11. 不定义 API / 前端（属于 P1-11）。
12. 不实现 P2 自动连续续写。
13. 不实现正文 token streaming。
14. 不实现 AI 自动 apply。
15. 不实现 AI 自动写正式正文。
16. 不修改 P0 文档。
17. 不修改 P1 总纲。
18. 不修改 P1-01。
19. 不修改 P1-02。
20. 不生成数据库迁移。
21. 不生成开发计划。
22. 不拆开发任务。

---

## 十六、P1-03 验收标准

### 16.1 五 Agent 职责边界

- [ ] Memory / Planner / Writer / Reviewer / Rewriter 五个 Agent 职责定位清楚。
- [ ] 每个 Agent 的负责与不负责清单明确。
- [ ] 五 Agent 与 PPAO 的关系清楚。
- [ ] 五 Agent 与 Workflow 的关系清楚。
- [ ] 五 Agent 与 ToolFacade 的关系清楚。

### 16.2 输入输出

- [ ] 每个 Agent 的必需输入、可选输入、禁止输入定义清楚。
- [ ] 每个 Agent 的主要输出、可选输出、禁止输出定义清楚。
- [ ] AgentInput / AgentOutput 通用结构定义清楚。
- [ ] AgentResultRef 规则清楚。

### 16.3 Step 序列

- [ ] 每个 Agent 的方向性 Step 序列定义清楚。
- [ ] Step 与 WorkflowStage 的对应关系清楚。
- [ ] 确认门等待步骤（wait_direction_selection 等）明确标记。

### 16.4 Tool 权限

- [ ] 五 Agent Tool 权限矩阵完整。
- [ ] 每个 Tool 的 allow / deny / conditional 标注清楚。
- [ ] side_effect_level 分层清楚。
- [ ] caller_type 规则清楚。
- [ ] 可重试规则与禁止自动重试规则清楚。
- [ ] degraded 下 Tool 调用规则清楚。

### 16.5 数据交接

- [ ] 五 Agent 之间六条交接链路清楚。
- [ ] safe_ref / result_ref 规则清楚。
- [ ] 明确交接不传完整正文 / Prompt / ContextPack / API Key。

### 16.6 确认门边界

- [ ] DirectionSelection / PlanConfirmation / HumanReviewGate / MemoryReviewGate 确认门边界清楚。
- [ ] Agent 不自动越过任一确认门。
- [ ] AgentOutput.requires_user_action 使用场景清楚。

### 16.7 Conflict Guard 关系

- [ ] Agent 不直接修改正式资产。
- [ ] Agent 不自动修复冲突。
- [ ] blocking 冲突处理行为清楚。

### 16.8 安全边界

- [ ] 所有 Agent formal_write_forbidden。
- [ ] 所有 Agent 不能 user_action。
- [ ] 所有 Agent 不直接访问 Provider / ModelRouter / Repository / DB。
- [ ] Agent 不直接调用 ToolFacade（通过 AgentRuntime 间接调用）。

### 16.9 与相邻模块边界

- [ ] 与 P1-01 / P1-02 边界清楚。
- [ ] 与 P0 能力复用关系清楚。
- [ ] 不进入 P1-04 ~ P1-11 / P2。

---

## 十七、P1-03 待确认点

### 17.1 P1-03 开发前建议确认

1. **Memory Agent 是否在 P1 默认生成 MemoryUpdateSuggestion**：P1-03 默认仅在 apply 后生成。是否允许在 planning 阶段也生成记忆建议（如发现关键记忆缺失），由 P1-09 确认。

2. **Planner Agent 是否必须生成 A/B/C 三个方向**：P1-03 默认生成三个。是否允许 2 个或 1 个，由 P1-05 确认。

3. **Writer Agent 在 degraded 上下文下生成候选稿的最低条件**：P1-03 给出方向（Master Arc + WritingTask + Immediate Window 不得缺失）。具体 blocked / degraded 条件由 P1-04 和 P1 ContextPack 增强设计冻结。

4. **Reviewer Agent 是否允许跳过**：P1-02 默认不允许（allow_skip_reviewer = false）。P1-03 保持此默认值。最终由产品需求确认。

5. **Reviewer Agent 输出是否复用 P0 AIReviewResult 还是新增 ReviewReport**：P1-03 建议新增 ReviewReport 结构，复用 P0 AIReview 的维度方向但不完全复用 AIReviewResult。最终由 P1-03 与 P0-10 开发实现确认。

6. **max_revision_rounds 默认 1 还是 2**：P1-02 登记为待确认点。P1-03 的 Rewriter Agent Step 序列不受此值影响（由 Workflow 层控制轮次）。由 P1-06 协同确认。

7. **create_ai_suggestion 是否由 Reviewer Agent 专属**：P1-03 默认 Reviewer Agent conditional；Planner / Memory 不使用。是否允许 Planner 也使用（如发现计划与 StoryMemory 不一致时），由 P1-07 确认。

### 17.2 后续模块设计时确认即可

8. **Conflict Guard 检查由哪个 Agent 触发**：P1-03 默认 Reviewer Agent 通过 request_conflict_check 触发。Conflict Guard 在 Core Application 层自动触发的情况由 P1-08 确认。

9. **AgentExecutionProfile 是否配置化**：P1-03 推荐代码静态注册。是否允许用户通过配置文件或 UI 修改，由 P1-11 或开发计划确认。

10. **AgentToolPermission 是否静态注册**：P1-03 推荐代码静态注册权限矩阵。权限矩阵是否可运行时配置，由 P1-11 或开发计划确认。

11. **P1 是否允许不同 Agent 使用不同 model_role**：P1-03 默认五个 model_role（analysis / planning / writer / reviewer / rewriter）。是否允许用户配置 model_role → Provider/Model 映射，由 P0-01 AI 基础设施和开发计划确认。

12. **是否允许用户在 Workflow 中禁用某个 Agent**：P1-03 不默认支持。如果 P1-11 或产品需求要求，可通过 WorkflowPolicy.allow_skip_* 系列参数控制。

13. **Rewriter Agent 是否必须生成 CandidateDraftVersion 还是可生成新 CandidateDraft**：P1-03 默认生成 CandidateDraftVersion。如果用户要求基于同一方向重新写作（而非修订），应使用 continuation_workflow 而非 revision_workflow。由 P1-06 确认。

---

## 附录 A：P1-03 术语表

| 术语 | 定义 |
|---|---|
| Memory Agent | 负责读取 StoryMemory / StoryState、检测记忆缺口、生成记忆上下文摘要和 MemoryUpdateSuggestion 的 Agent |
| Planner Agent | 负责生成 Direction Proposal（A/B/C）、ChapterPlan 和 WritingTask 的 Agent |
| Writer Agent | 负责基于确认后的计划和 ContextPack 生成 CandidateDraft 的 Agent |
| Reviewer Agent | 负责审阅 CandidateDraft / CandidateDraftVersion、输出 ReviewReport / ReviewIssue 的 Agent |
| Rewriter Agent | 负责基于 ReviewReport / 用户反馈生成 CandidateDraftVersion 的 Agent |
| AgentType | 五 Agent 的类型枚举：memory / planner / writer / reviewer / rewriter |
| AgentCapability | Agent 的能力标签集合 |
| AgentInput | Agent 执行时的输入结构，包含 session_id、work_id、context_refs 等 |
| AgentOutput | Agent 执行后的输出结构，包含 result_refs、warning_codes、decision_hint 等 |
| AgentStepPlan | Agent 执行的方向性步骤计划 |
| AgentExecutionProfile | Agent 的执行配置：model_role、timeout、allowed_tool_names 等 |
| AgentToolPermission | 单个 Tool 对特定 Agent 的权限定义：allow / deny / conditional |
| AgentResultRef | Agent 产出的安全引用：ref_type + ref_id + ref_summary |
| side_effect_level | Tool 副作用级别：read_only / analysis_write / suggestion_write / draft_write / memory_suggestion_write / formal_write_forbidden |
| model_role | Agent 传给 ModelRouter 的角色标识：analysis / planning / writer / reviewer / rewriter |
| formal_write_forbidden | 所有 Agent 不能执行正式写入的永久约束 |

## 附录 B：P1-03 与 P1 总纲的对照

| P1 总纲要求 | P1-03 冻结内容 |
|---|---|
| 五类 Agent 完整职责与编排 | 第四~八章：每个 Agent 的职责、输入输出、Step 序列、Tool 权限 |
| AgentPermissionPolicy | 第九章：五 Agent Tool 权限矩阵、side_effect_level |
| 完整 Tool 权限矩阵 | 第九章 9.1 节：21 个 Tool × 5 个 Agent 权限总表 |
| PPAO 是 Agent 内部执行机制 | 第二章 2.2 节：五 Agent 与 PPAO 的关系 |
| Agent 不直接执行 Tool | 第二章 2.4 节：通过 AgentRuntime → ToolFacade 链路 |
| caller_type = agent 不能执行 user_action | 第九章 9.4 节：caller_type 规则 |
| Agent 不持有 formal_write | 第九章：formal_write_forbidden |
| 四层剧情轨道 | 不覆盖（属于 P1-04），但 Writer / Reviewer Agent 预留 Plot Arc 引用 |
| A/B/C 方向推演 | 不覆盖完整算法（属于 P1-05），但 Planner Agent 定义生成 Direction Proposal 的方向 |
| 章节计划 | 不覆盖完整结构（属于 P1-05），但 Planner Agent 定义产出 ChapterPlan 的方向 |
| 多轮 CandidateDraft 迭代 | 不覆盖版本链（属于 P1-06），但 Rewriter Agent 定义产出 CandidateDraftVersion 的方向 |
| HumanReviewGate 仍是用户确认门 | 第十一章：Agent 不自动越过确认门 |
| MemoryReviewGate 仍是记忆确认门 | 第十一章：Agent 不自动确认 MemoryRevision |
