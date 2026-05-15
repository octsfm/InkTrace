﻿# InkTrace V2.0-P1-03 五Agent职责与编排详细设计
版本：v1.3 / P1 模块级详细设计候选冻结版  
状态：候选冻结  
所属阶段：InkTrace V2.0 P1  
设计范围：五 Agent（Memory / Planner / Writer / Reviewer / Rewriter）职责、输入输出、Step 序列、Tool 权限、数据交接与协作编排约束

说明：本文档为 P1-03 五Agent职责与编排详细设计的正式候选冻结版。本文档不推翻 P0 已冻结设计，不修改 P1 总纲、P1-01、P1-02 已封板结论。

依据文档：
- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`
- `docs/07_overview/InkTrace-V2.0-概要设计说明书.md`
- `docs/02_architecture/InkTrace-V2.0-架构设计说明书.md`
- `docs/03_design/InkTrace-V2.0-P1-详细设计总纲.md`
- `docs/03_design/InkTrace-V2.0-P1-01-AgentRuntime详细设计.md`
- `docs/03_design/InkTrace-V2.0-P1-02-AgentWorkflow详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-02-AIJobSystem详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-07-ToolFacade与权限详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-08-MinimalContinuationWorkflow详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-10-AIReview详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-11-API与集成边界详细设计.md`

---

## 一、文档定位与设计范围

### 1.1 文档定位
P1-03 只冻结五 Agent 的职责、输入输出、方向性 Step 序列、Tool 权限、side_effect_level、数据交接规则与协作约束。

### 1.2 设计范围
1. 五 Agent 分别做什么与不做什么。  
2. 每个 Agent 的输入、输出、result_ref、禁止输出。  
3. 每个 Agent 的方向性 Step 序列。  
4. 每个 Agent 的 Tool 白名单/黑名单与权限等级。  
5. 五 Agent 间 safe_ref/result_ref 交接规则。  
6. 失败、degraded、partial_success、waiting_for_user 的行为边界。  

### 1.3 不覆盖范围
不定义 AgentRuntime 状态机、不定义 AgentWorkflow Stage/Transition/Decision、不定义四层剧情轨道、不定义 Direction Proposal 算法、不定义 ChapterPlan 完整结构、不定义 CandidateDraftVersion 版本链、不定义 AI Suggestion 类型系统、不定义 Conflict Guard 规则矩阵、不定义 StoryMemory Revision 数据结构、不定义 AgentTrace 完整字段、不定义 API/前端，不进入 P2 自动连续续写、token streaming、AI 自动 apply、AI 自动写正式正文。

---

## 二、五 Agent 总体职责边界

### 2.1 五 Agent 总览
| Agent | 核心职责 | 主要产出 | 禁止项 |
|---|---|---|---|
| Memory | 记忆上下文读取、记忆缺口识别、记忆更新建议 | `memory_context_ref` / `memory_update_suggestion_ref` | 直接写正式 StoryMemory/StoryState |
| Planner | 方向提案与章节计划、写作任务准备 | `direction_proposal_ref` / `chapter_plan_ref` / `writing_task_ref` | 自动选择方向、自动确认计划 |
| Writer | 候选稿生成与候选稿校验 | `candidate_draft_ref` | 写正式正文、自动 apply |
| Reviewer | 一致性/风格/剧情审阅与问题报告 | `review_report_ref` / `review_issue_refs` | 自动 accept/reject/apply |
| Rewriter | 基于审阅反馈修订候选稿 | `candidate_version_ref` / `rewrite_summary_ref` | 覆盖原候选稿、写正式正文 |

### 2.2 与 P1-01 / P1-02 关系
1. PPAO 是 Agent 内部执行机制，P1-03 只定义 Agent 做什么。  
2. AgentRuntimeService 负责单 Step 推进；Agent 不直接执行 Tool。  
3. AgentOutput 只提供 `decision_hint`，最终决策由 AgentOrchestrator 产生。  
4. waiting_for_user 不得由 Agent 自动越过。  

---

## 三、通用 Agent 模型

### 3.1 AgentCapability（补充）
| Agent | 能力标签 |
|---|---|
| Memory Agent | story_context_read, memory_gap_detection, memory_update_suggestion |
| Planner Agent | direction_proposal, chapter_planning, writing_task_preparation |
| Writer Agent | candidate_generation, candidate_validation |
| Reviewer Agent | consistency_review, style_review, plot_review, issue_reporting |
| Rewriter Agent | candidate_revision, revision_validation |

### 3.2 AgentExecutionProfile
| 字段 | 类型 | 说明 |
|---|---|---|
| agent_type | enum | Agent 类型 |
| model_role | enum | analysis / planning / writer / reviewer / rewriter |
| default_timeout | integer | 默认超时（建议 300 秒） |
| max_retry | integer | 最大重试次数（默认 1） |
| allow_degraded | boolean | 是否允许 degraded |
| allowed_tool_names | string[] | Tool 白名单 |
| denied_tool_names | string[] | Tool 黑名单 |
| max_output_chars | integer | 最大输出字符数 |
| output_schema_key | string | 输出 schema 标识 |
| trace_level | enum | minimal / standard / verbose |
| metadata | object | 扩展元数据 |

model_role 方向：
| agent_type | model_role |
|---|---|
| memory | analysis |
| planner | planning |
| writer | writer |
| reviewer | reviewer |
| rewriter | rewriter |

约束：model_role 只是角色标识；Agent 不直接调用 ModelRouter；模型调用通过 AgentRuntime / Core Service 经 ToolFacade 间接完成。

### 3.3 AgentToolPermission
| 字段 | 类型 | 说明 |
|---|---|---|
| tool_name | string | Tool 名称 |
| agent_type | enum | Agent 类型 |
| permission | enum | allow / deny / conditional |
| side_effect_level | enum | read_only / plan_write / safe_write_candidate / safe_write_review / safe_write_suggestion / trace_only / formal_write_forbidden |
| requires_user_action | boolean | 是否需要 user_action |
| allow_degraded | boolean | degraded 下是否允许调用 |
| retryable | boolean | 是否可重试 |
| notes | string | 备注 |

### 3.4 AgentResultRef / safe_ref
| 字段 | 类型 | 说明 |
|---|---|---|
| ref_type | string | 引用类型 |
| ref_id | string | 引用实体 ID |
| ref_scope | enum | work / chapter / session |
| checksum | string | 可选一致性校验 |
| summary | string | 可选摘要（不得含完整正文） |
| created_at | datetime | 创建时间 |

约束：
1. AgentOutput.result_refs 使用 AgentResultRef。  
2. 不包含完整正文、完整 Prompt、完整 ContextPack、API Key。  
3. 下游 Agent 通过 ToolFacade 的 read_* 工具读取实体内容。  

### 3.5 side_effect_level（正式口径）
正式判定口径仅使用：
- read_only
- plan_write
- safe_write_candidate
- safe_write_review
- safe_write_suggestion
- trace_only
- formal_write_forbidden

业务映射（仅说明）：
- analysis_write ≈ plan_write + trace_only
- draft_write ≈ safe_write_candidate
- suggestion_write ≈ safe_write_suggestion / safe_write_review
- memory_suggestion_write ≈ safe_write_suggestion（对象限定 MemoryUpdateSuggestion）

---

## 四、Memory Agent 详细设计

### 4.1 职责
1. 读取 StoryMemory/StoryState/ContextPack 安全引用。  
2. 识别记忆缺口与不一致风险。  
3. 产出 `memory_context_ref` 与可选 `memory_update_suggestion_ref`。  

### 4.2 输入输出
- 输入：work/chapter/session refs、warning_codes、allow_degraded。  
- 输出：memory_context_ref、memory_warning_refs、可选 memory_update_suggestion_ref。  
- 禁止输出：正式 MemoryRevision、已确认结论。  

### 4.3 Step 序列（方向）
1. read_memory_state  
2. detect_gaps  
3. summarize_memory_context  
4. build_memory_update_suggestion（可选）

Stage 对应：step_1~4 对应 `memory_context_prepare`；建议分支对应 `memory_suggestion`。

### 4.4 可调用/禁止 Tool（补充表）
| 可调用 Tool | 权限 | side_effect_level | 说明 |
|---|---|---|---|
| get_story_memory_snapshot | allow | read_only | 读取快照 |
| get_story_state_baseline | allow | read_only | 读取基线 |
| create_memory_update_suggestion | allow | safe_write_suggestion | 仅写建议 |
| request_conflict_check | conditional | read_only | 请求冲突检查 |
| create_agent_observation / create_agent_trace_event | allow | trace_only | 记录观测 |

| 禁止 Tool | 原因 |
|---|---|
| apply_candidate_to_draft | user_action 专属 |
| accept/reject_candidate_draft | user_action 专属 |
| formal_chapter_write | formal_write_forbidden |

---

## 五、Planner Agent 详细设计

### 5.1 职责
1. 生成方向提案（A/B/C 方向语义）。  
2. 生成章节计划。  
3. 准备 WritingTask 输入。  

### 5.2 输入输出
- 输入：memory_context_ref、用户意图、约束条件。  
- 输出：direction_proposal_ref、chapter_plan_ref、writing_task_ref。  
- 禁止：自动完成 DirectionSelection/PlanConfirmation。  

### 5.3 Step 序列（方向）
1. generate_direction_proposals  
2. wait_direction_selection  
3. generate_chapter_plan  
4. wait_plan_confirmation  
5. prepare_writing_task

Stage 对应：step_1~3 对应 `planning_prepare`；等待步骤分别对应 `direction_selection_waiting` 与 `chapter_plan_confirm_waiting`。

### 5.4 可调用/禁止 Tool
| 可调用 Tool | 权限 | side_effect_level | 说明 |
|---|---|---|---|
| build_context_pack | allow | read_only | 仅用于规划上下文 |
| create_direction_proposal | allow | plan_write | 产出方向建议 |
| create_chapter_plan | allow | plan_write | 产出章节计划 |
| create_writing_task | allow | plan_write | 准备写作任务 |
| request_conflict_check | conditional | read_only | 风险预检 |
| create_agent_observation / create_agent_trace_event | allow | trace_only | 记录观测 |

| 禁止 Tool | 原因 |
|---|---|
| generate_candidate_draft | Writer 专属 |
| apply_candidate_to_draft | user_action 专属 |
| formal_chapter_write | formal_write_forbidden |

---

## 六、Writer Agent 详细设计

### 6.1 职责
1. 基于已确认方向与计划生成 CandidateDraft。  
2. 执行候选稿基础校验。  
3. 保留 degraded/warning 摘要供下游使用。  

### 6.2 输入输出
- 输入：writing_task_ref、context_pack_ref、direction/plan refs。  
- 输出：candidate_draft_ref、candidate_generation_summary_ref。  
- 禁止：直接写正式正文、自动 apply。  

### 6.3 Step 序列（方向）
1. read_writing_task_and_context  
2. run_writer_step  
3. validate_writer_output  
4. save_candidate_draft

Stage 对应：`drafting`。

### 6.4 可调用/禁止 Tool
| 可调用 Tool | 权限 | side_effect_level | 说明 |
|---|---|---|---|
| build_context_pack | conditional | read_only | 仅构建上下文 |
| run_writer_step | allow | safe_write_candidate | 生成候选正文 |
| validate_writer_output | allow | safe_write_candidate | 输出校验 |
| save_candidate_draft | allow | safe_write_candidate | 保存候选稿 |
| request_conflict_check | conditional | read_only | 写作前风险检查 |
| create_agent_observation / create_agent_trace_event | allow | trace_only | 记录观测 |

| 禁止 Tool | 原因 |
|---|---|
| apply_candidate_to_draft | user_action 专属 |
| accept/reject_candidate_draft | user_action 专属 |
| formal_chapter_write | formal_write_forbidden |

### 6.5 与 P0 MinimalContinuationWorkflow 关系
1. P0 MinimalContinuationWorkflow 是 P1 Writer Agent 的轻量前身。  
2. P1 Writer 在其基础上增加：接收 Planner 输入、更完整 degraded 处理、与 Reviewer/Rewriter 交接。  
3. P0 兼容路径可保留；P1 主链路默认由 Writer Agent 承担。  

---

## 七、Reviewer Agent 详细设计

### 7.1 职责
1. 对 CandidateDraft / CandidateDraftVersion 做一致性、风格、剧情审阅。  
2. 产出 ReviewReport / ReviewIssue。  
3. 给出 rewrite 或通过的决策建议。  

### 7.2 输入输出
- 输入：candidate refs、context refs、历史 issues。  
- 输出：review_report_ref、review_issue_refs、可选 ai_suggestion_refs。  
- 禁止：自动 accept/reject/apply。  

### 7.3 Step 序列（方向）
1. load_candidate_and_context  
2. run_review_checks  
3. build_review_report  
4. produce_decision_hint

Stage 对应：`reviewing` / `final_reviewing`。

### 7.4 可调用/禁止 Tool
| 可调用 Tool | 权限 | side_effect_level | 说明 |
|---|---|---|---|
| create_review_report | allow | safe_write_review | 生成审阅报告 |
| create_review_issue | allow | safe_write_review | 问题结构化 |
| request_conflict_check | conditional | read_only | 冲突预检 |
| create_ai_suggestion | conditional | safe_write_suggestion | 建议型产物 |
| create_agent_observation / create_agent_trace_event | allow | trace_only | 记录观测 |

| 禁止 Tool | 原因 |
|---|---|
| accept/reject/apply_candidate_draft | user_action 专属 |
| formal_chapter_write | formal_write_forbidden |

### 7.5 与 P0-10 AIReview 复用关系
1. Reviewer 复用 P0 AIReview 的维度方向。  
2. Reviewer 将其扩展为多轮审阅链路中的结构化报告。  
3. ReviewReport 可复用 AIReviewResult 部分字段；是否完全复用作为待确认点。  
4. 无论复用方式，Reviewer 都不能自动 accept/reject/apply。  

---

## 八、Rewriter Agent 详细设计

### 8.1 职责
1. 基于 ReviewReport 和用户反馈修订候选稿。  
2. 产出新 CandidateDraftVersion。  
3. 输出修订说明与改动摘要引用。  

### 8.2 输入输出
- 输入：candidate_draft_ref/candidate_version_ref、review_report_ref、rewrite constraints。  
- 输出：candidate_version_ref、rewrite_summary_ref。  
- 禁止：覆盖原 CandidateDraft、自动 apply。  

### 8.3 Step 序列（方向）
1. load_review_feedback  
2. generate_rewrite_version  
3. validate_rewrite_output  
4. create_candidate_version

Stage 对应：`rewriting`。

### 8.4 可调用/禁止 Tool
| 可调用 Tool | 权限 | side_effect_level | 说明 |
|---|---|---|---|
| create_candidate_version | allow | safe_write_candidate | 生成新版本 |
| validate_writer_output | allow | safe_write_candidate | 修订校验 |
| request_conflict_check | conditional | read_only | 冲突预检 |
| create_agent_observation / create_agent_trace_event | allow | trace_only | 记录观测 |

| 禁止 Tool | 原因 |
|---|---|
| formal_chapter_write | formal_write_forbidden |
| apply_candidate_to_draft | user_action 专属 |

### 8.5 CandidateDraftVersion 边界
1. Rewriter 的正文输出只允许 CandidateDraftVersion。  
2. 版本链定义由 P1-06 冻结；Rewriter 不管理版本树。  
3. 若需求是“重新续写”而非“修订”，应走 continuation_workflow 而不是 revision_workflow。  

---

## 九、五 Agent Tool 权限矩阵

> 本矩阵为正式主矩阵；任何补充表不得与其冲突。

| Tool 名 | Memory | Planner | Writer | Reviewer | Rewriter | 备注 |
|---|---|---|---|---|---|---|
| build_context_pack | conditional | allow | deny | deny | deny | 规划/准备可用 |
| generate_candidate_draft / run_writer_step | deny | deny | allow | deny | deny | Writer 专属 |
| create_candidate_version | deny | deny | conditional | deny | allow | Rewriter 主用 |
| create_review_report | deny | deny | deny | allow | deny | Reviewer 专属 |
| create_memory_update_suggestion | allow | deny | deny | deny | deny | Memory 专属 |
| request_conflict_check | conditional | conditional | conditional | conditional | conditional | 五 Agent 可条件调用 |
| create_agent_observation / create_agent_trace_event | allow | allow | allow | allow | allow | 允许记录 |

统一禁止：
- accept_candidate_draft / reject_candidate_draft / apply_candidate_to_draft（user_action 专属）
- formal_chapter_write（formal_write_forbidden）

---

## 十、五 Agent 数据交接设计

### 10.1 交接规则
1. 仅交接 safe_ref/result_ref，不交接完整正文/完整 Prompt/完整 ContextPack。  
2. 交接对象必须可追溯至 session/work/chapter。  
3. partial_success 必须包含至少一个可交付 result_ref。  

### 10.2 交接链路（方向）
1. Memory Agent `result_refs` -> AgentOrchestrator -> WorkflowCheckpoint.result_refs -> Planner Agent `AgentInput.context_refs`。  
2. Planner 产出 + 用户确认 -> writing_prepare -> ContextPack -> Writer 输入。  
3. Writer 产出 CandidateDraft -> Reviewer 输入。  
4. Reviewer 产出 ReviewReport -> Rewriter 输入。  
5. Rewriter 产出 CandidateDraftVersion -> Reviewer 复审。  
6. HumanReviewGate apply 后 -> Memory Agent memory_suggestion 分支。  

```mermaid
flowchart LR
  M["Memory Agent"] --> P["Planner Agent"]
  P -->|"direction/plan confirmed"| W["Writer Agent"]
  W --> R["Reviewer Agent"]
  R -->|"need rewrite"| RW["Rewriter Agent"]
  RW --> R2["Reviewer Agent (final)"]
  R2 --> HRG["HumanReviewGate"]
  HRG -->|"apply success"| M2["Memory Agent (suggestion)"]
```

---

## 十一、五 Agent 与确认门关系

| 确认门 | 负责产生 | 负责确认 | Agent 角色 | Agent 禁止 |
|---|---|---|---|---|
| DirectionSelection | Planner | user_action | 提供方向提案 | 自动代选方向 |
| PlanConfirmation | Planner | user_action | 提供章节计划 | 自动确认计划 |
| HumanReviewGate | Writer/Reviewer/Rewriter（产物） | user_action | 提供候选稿与报告 | 自动 accept/reject/apply |
| MemoryReviewGate | Memory（建议） | user_action | 提供记忆更新建议 | 自动写正式记忆 |

说明：DirectionSelection 与 PlanConfirmation 不等于 HumanReviewGate；MemoryReviewGate 只处理记忆更新建议。

---

## 十二、五 Agent 与 Conflict Guard 关系

1. Agent 不直接修改正式资产，Conflict Guard 在 Core Application 层执行。  
2. Reviewer 可通过 `request_conflict_check` 请求前置检查。  
3. CandidateDraft apply、AI Suggestion、MemoryUpdateSuggestion 等动作可能触发冲突检查。  
4. blocking 冲突未处理时，Agent 不得给出 completed 结论。  
5. Agent 不自动修复冲突，不自动覆盖人物/设定/伏笔/时间线/大纲。  
6. 具体规则矩阵由 P1-08 冻结。  

---

## 十三、五 Agent 与 P0 能力复用

1. 复用 P0-07 ToolFacade 受控调用边界。  
2. 复用 P0-08 最小续写链路作为 Writer 轻量兼容路径。  
3. 复用 P0-09 CandidateDraft/HumanReviewGate 边界，不得越权。  
4. 复用 P0-10 AIReview 维度方向（Reviewer 扩展，但不越权）。  
5. 复用 P0-11 API caller_type/user_action 安全边界。  

---

## 十四、错误处理与降级规则

### 14.1 Agent 级规则
| Agent | 失败处理 | degraded 处理 | partial_success 条件 |
|---|---|---|---|
| Memory | 无法读取核心上下文则 failed | 非关键上下文缺失可 degraded | 至少产出 memory_context_ref |
| Planner | 无方向/计划产出通常 failed | 可 degraded 但需 warning_codes | 至少产出 direction 或 plan ref |
| Writer | 无 CandidateDraft 产出通常 failed | allow_degraded=true 时可继续 | 至少产出 candidate_draft_ref |
| Reviewer | 审阅失败可 failed 或 degraded | 可 completed_with_warnings | 至少产出 review_report_ref |
| Rewriter | 无新版本产出通常 failed | 可 degraded 但需 warning_codes | 至少产出 candidate_version_ref |

### 14.2 通用规则
1. degraded 必须传递 warning_codes。  
2. blocking 冲突未处理不得 completed。  
3. Agent 不得自行忽略 blocking。  
4. cancelled 后迟到结果必须 ignored（继承 P1-01/P1-02）。  

---

## 十五、P1-03 不做事项清单

1. 不定义五 Agent 之外的新 Agent（如 Opening Agent、Style Agent）。  
2. 不定义完整 Tool 权限系统实现细节（仅冻结矩阵与边界）。  
3. 不定义 Plot Arc 数据结构。  
4. 不定义 Direction Proposal 算法。  
5. 不定义 ChapterPlan 完整结构。  
6. 不定义 CandidateDraftVersion 版本链结构。  
7. 不定义 AI Suggestion 类型系统。  
8. 不定义 Conflict Guard 规则矩阵。  
9. 不定义 StoryMemory Revision 数据结构。  
10. 不定义 AgentTrace 完整字段。  
11. 不定义 API / 前端。  
12. 不实现 P2 自动连续续写、token streaming、AI 自动 apply、AI 自动写正式正文。  

---

## 十六、P1-03 验收标准

### 16.1 五 Agent 职责边界
- [ ] 五 Agent 各自职责与禁止项清晰且不重叠。  
- [ ] 无 Agent 拥有 formal_write 权限。  

### 16.2 输入输出
- [ ] 每个 Agent 输入输出明确。  
- [ ] result_refs 规则统一为 AgentResultRef。  

### 16.3 Step 序列
- [ ] 每个 Agent 有方向性 Step 序列。  
- [ ] Step 与 P1-02 Stage 有清晰方向对应。  

### 16.4 Tool 权限
- [ ] 主矩阵完整且与各 Agent 小节一致。  
- [ ] user_action 专属 Tool 不可由 Agent 调用。  

### 16.5 数据交接
- [ ] 交接只用 safe_ref/result_ref。  
- [ ] 不交接完整正文/Prompt/ContextPack/API Key。  

### 16.6 确认门边界
- [ ] DirectionSelection / PlanConfirmation / HumanReviewGate / MemoryReviewGate 区分清晰。  
- [ ] Agent 不自动越过确认门。  

### 16.7 Conflict Guard 关系
- [ ] blocking 未处理不得 completed。  
- [ ] Agent 不自动冲突修复。  

### 16.8 安全边界
- [ ] Agent 不直接访问 Provider/ModelRouter/Repository/DB。  
- [ ] Agent 不伪造 user_action。  

### 16.9 与相邻模块边界
- [ ] 与 P1-01、P1-02 边界清晰。  
- [ ] 不越界进入 P1-04~P1-11 详细内部设计。  

---

## 十七、P1-03 待确认点

### 17.1 P1-03 开发前建议确认
1. Memory Agent 是否默认生成 MemoryUpdateSuggestion。  
2. Planner Agent 是否必须始终生成 A/B/C 三方向。  
3. Writer 在 degraded 上下文下继续生成的最低条件。  
4. Reviewer 是否允许在特定策略下跳过。  
5. Reviewer 输出是否完全复用 AIReviewResult。  
6. `max_revision_rounds` 默认取 1 还是 2。  
7. `create_ai_suggestion` 是否 Reviewer 专属。  

### 17.2 后续模块设计时确认即可
1. Conflict Guard 检查由哪个 Agent 主动触发，还是由 Core 自动触发。  
2. AgentExecutionProfile 是否全面配置化。  
3. AgentToolPermission 是否静态注册或可动态策略化。  
4. P1 是否允许不同 Agent 使用不同 model_role 组合。  
5. 是否允许用户在 Workflow 中禁用某个 Agent。  
6. Rewriter 是否必须产出 CandidateDraftVersion，还是允许新 CandidateDraft。  
7. workflow_compat 是否在 P1-11 后继续保留。  

---

## 附录 A：P1-03 术语表

| 术语 | 说明 |
|---|---|
| Memory Agent | 负责记忆上下文读取、缺口识别、记忆更新建议 |
| Planner Agent | 负责方向提案、章节计划、写作任务准备 |
| Writer Agent | 负责候选稿生成 |
| Reviewer Agent | 负责候选稿审阅与问题报告 |
| Rewriter Agent | 负责候选稿修订 |
| AgentType | memory/planner/writer/reviewer/rewriter |
| AgentCapability | Agent 的能力标签集合 |
| AgentInput | Agent 执行输入上下文 |
| AgentOutput | Agent 执行输出与 decision_hint |
| AgentStepPlan | Agent 方向性步骤计划 |
| AgentExecutionProfile | Agent 执行参数配置 |
| AgentToolPermission | Agent 与 Tool 的权限条目 |
| AgentResultRef | Agent 产出安全引用 |
| side_effect_level | 副作用等级口径 |
| model_role | 角色化模型路由标识 |
| formal_write_forbidden | Agent 永久禁止正式写入权限 |

---

## 附录 B：P1-03 与 P1 总纲的对照

| P1 总纲要求 | P1-03 冻结内容 |
|---|---|
| 五类 Agent 完整职责与编排 | 已冻结五 Agent 职责、输入输出、Step 序列 |
| AgentPermissionPolicy | 已冻结 AgentToolPermission 与主矩阵 |
| 完整 Tool 权限矩阵 | 已冻结第九章矩阵 |
| PPAO 是 Agent 内部执行机制 | 已继承 P1-01，P1-03 不重定义 |
| Agent 不直接执行 Tool | 已冻结 AgentRuntime -> ToolFacade 间接调用边界 |
| caller_type = agent 不能执行 user_action | 已冻结为强约束 |
| Agent 不持有 formal_write | 已冻结 formal_write_forbidden |
| 四层剧情轨道 | 不覆盖，归 P1-04 |
| A/B/C 方向推演算法 | 不覆盖算法，归 P1-05 |
| 章节计划完整结构 | 不覆盖完整结构，归 P1-05 |
| 多轮 CandidateDraft 迭代 | 不覆盖版本链，归 P1-06 |
| HumanReviewGate | 保留为用户确认门，不可绕过 |
| MemoryReviewGate | 保留为记忆确认门，不可绕过 |
