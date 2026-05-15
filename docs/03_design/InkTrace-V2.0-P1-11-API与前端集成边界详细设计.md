# InkTrace V2.0-P1-11 API 与前端集成边界详细设计

版本：v1.1 / P1 模块级详细设计候选冻结版  
状态：候选冻结  
所属阶段：InkTrace V2.0 P1  
设计范围：P1 API 资源边界、通用 DTO 规则、前端最小集成边界、轮询与 SSE 安全事件边界

合并说明：本文档以无后缀 `.md` v1.0 为主版本，吸收 `_001.md` 中的 11 组 API 分组、具体路由方向、caller_type 权限矩阵、前端最小入口、错误码方向、SSE 事件清单和附录路由速查表；`_001.md` 已被完全吸收，不再单独维护。

## 一、文档定位与设计范围

本文档只覆盖 P1-11 API 与前端集成边界详细设计，不写代码、不生成开发计划、不处理 Git。  
本文档冻结“P1 应暴露什么能力、如何安全暴露、前端最小要集成什么、哪些不能做”，不冻结具体 Controller/Router 实现细节。
实现阶段必须同时遵循 `docs/03_design/InkTrace-V2.0-P1-实施唯一依据清单.md`，且仅以无后缀正式文档为依据。

覆盖范围：

1. P1 API 资源分组与路由前缀方向。
2. 通用 Request / Response / Error DTO 规则。
3. caller_type 与 user_action 边界在 API 层的落实方向。
4. P1 前端最小可用入口（list + detail + action）边界。
5. 轮询优先策略与终态停止规则。
6. SSE 事件白名单方向（可选增强）与安全约束。
7. 与 P0 API、P1-01~P1-10、P1-UI、DESIGN.md 的关系。
8. 错误码分层与 safe_message 口径。
9. 验收标准与待确认点。

实施依据规则（冻结）：

1. `_001.md` 文件仅为历史合并来源，不作为实现依据。
2. 若 `_001.md` 与无后缀正式文档冲突，以无后缀正式文档为准。
3. API 实现评审必须附带“已对照无后缀正式文档”的检查记录。

不覆盖范围：

1. 不定义数据库结构与迁移。
2. 不定义 Provider / ModelRouter / ToolFacade 内部实现。
3. 不定义 P2 能力（自动连续续写队列、正文 token streaming、成本/分析看板、@ 引用、Citation Link、Opening Agent）。
4. 不重定义 P1-01 ~ P1-10 已冻结业务规则。
5. 不生成完整 OpenAPI 文档与字段级 DTO 全量清单。

## 二、核心定位与冻结结论

1. P1-11 是集成边界模块，负责接口表达和前端消费边界，不承载核心业务决策。
2. API 层必须透传 `caller_type / request_id / trace_id` 到 Application Service 与审计链路。
3. API 层不得伪造 user_action，不得让 workflow/agent/system 冒充 user_action。
4. API 层不得直接访问 Provider SDK / ModelRouter / Repository。
5. P1 默认轮询优先，SSE 仅可选增强，不得成为核心流程唯一依赖。
6. SSE 与 API 响应不得泄露完整正文 / Prompt / ContextPack / CandidateDraft / API Key。
7. HumanReviewGate / ConflictGuard / MemoryReviewGate 门控职责不在 API 层重写。
8. API 仅表达状态与动作入口，不改变各模块状态机语义。

## 三、API 总体原则与安全边界

1. API 只做边界校验、参数收敛、错误封装、追踪透传，不承载业务核心判断。
2. Presentation API 请求路径固定为：`Presentation API -> Application Service -> Domain/Infrastructure`。
3. Agent 写入路径固定为：`AgentRuntime -> ToolFacade -> Application Service`。
4. Presentation API 不得直调 ToolFacade；ToolFacade 是 Agent 入口，不是前端入口。
5. 所有门控动作必须双校验：`caller_type=user_action` 且 `user_action=true`。
6. 所有副作用写操作必须携带 `idempotency_key`。
7. API 响应和 SSE 仅返回安全摘要、安全引用、状态和错误码。

## 四、API 分组与路由方向

以下路由为方向建议，不是最终 Controller 实现；最终以后端路由注册为准。路由分组不代表可绕过 Application Service / ToolFacade 边界。

### 4.1 11 组 API 分组

1. Agent Session
2. Agent Trace
3. Plot Arc
4. Direction Proposal
5. Chapter Plan
6. Multi-round CandidateDraft
7. AI Suggestion
8. Conflict Guard
9. Memory Revision
10. Context Pack
11. Writing Task

### 4.2 分组与前缀方向表

| 分组 | 路由前缀（方向） | 核心职责 |
|---|---|---|
| Agent Session | `/api/v2/ai/sessions` | AgentSession 创建、状态查询、暂停、恢复、取消 |
| Agent Trace | `/api/v2/ai/traces` | Session/Step/Detail Trace 查询与摘要 |
| Plot Arc | `/api/v2/ai/plot-arcs` | 四层轨道读取、状态查询、受控刷新 |
| Direction Proposal | `/api/v2/ai/directions` | 方向推演生成、列表、详情、选择、重生成 |
| Chapter Plan | `/api/v2/ai/chapter-plans` | 计划生成、列表、详情、确认、拒绝、重生成 |
| Multi-round CandidateDraft | `/api/v2/ai/candidate-drafts` | 草稿容器、版本链、diff、accept/reject/apply |
| AI Suggestion | `/api/v2/ai/suggestions` | 建议列表、详情、accept/dismiss/convert |
| Conflict Guard | `/api/v2/ai/conflicts` | 冲突记录列表、详情、resolve/decide |
| Memory Revision | `/api/v2/ai/memory-revisions` + `/api/v2/ai/memory-gates` | 记忆建议审批、revision 查询、apply/rollback |
| Context Pack | `/api/v2/ai/context-packs` | ContextPack 摘要、层级预览 |
| Writing Task | `/api/v2/ai/writing-tasks` | WritingTask 查询、确认入口（首批）；直接编辑后置 |

### 4.3 CandidateDraft 主路径冻结

P1 默认主路径：

- `/api/v2/ai/candidate-drafts`
- `/api/v2/ai/candidate-drafts/{draft_id}/versions`
- `/api/v2/ai/candidate-drafts/{draft_id}/versions/{version_id}`
- `/api/v2/ai/candidate-drafts/{draft_id}/versions/diff`
- `/api/v2/ai/candidate-drafts/{draft_id}/versions/{version_id}/accept`
- `/api/v2/ai/candidate-drafts/{draft_id}/versions/{version_id}/reject`
- `/api/v2/ai/candidate-drafts/{draft_id}/apply`

`/api/v2/ai/candidates` 不作为 P1 默认主路径；如实现层保留仅可作为兼容别名。

### 4.4 Context Pack 预览开放范围（冻结）

1. P1 首批仅开放 Context Pack `summary + layers preview`。
2. 预览返回仅包含：`safe_ref`、层级摘要、token 分布、`warning_codes`。
3. 不返回完整 ContextPack 原文。
4. 不返回完整 Prompt。
5. 不返回完整候选稿正文。
6. 更完整层级展开作为后续增强，不作为 P1 必须能力。

## 五、通用 Request / Response / Error DTO 规则

### 5.1 通用 Request 字段方向

| 字段 | 必填 | 说明 |
|---|---|---|
| request_id | 是 | 幂等与追踪标识 |
| trace_id | 是 | 全链路追踪 ID |
| caller_type | 是 | user_action / agent / workflow_compat / system_maintenance / quick_trial |
| user_action | 门控动作必填 | 门控动作必须为 true |
| idempotency_key | 副作用写操作必填 | 防重放、冲突检测 |

### 5.2 通用 Response 包装方向

```text
{
  "request_id": "...",
  "trace_id": "...",
  "status": "ok|error",
  "data": { ... },
  "error": {
    "error_code": "...",
    "safe_message": "...",
    "retryable": true|false
  },
  "polling_hint": {
    "next_interval_ms": 2000,
    "stop": false
  }
}
```

### 5.3 Error DTO 规则

1. `safe_message` 面向用户，不泄露内部堆栈、Prompt、SQL、密钥、正文原文。
2. 可选 `details` 仅允许脱敏结构化信息。
3. 列表接口默认不返回完整内容文本；详情接口也遵守脱敏约束。

## 六、caller_type 与 user_action 权限边界

### 6.1 caller_type 枚举与语义（冻结）

| caller_type | 含义 | 禁止范围 |
|---|---|---|
| user_action | 用户明确操作 | 不得冒充 system 内部路径 |
| agent | AgentRuntime 受控调用 | 不得执行 user_action 专属动作，不得 formal_write |
| workflow_compat | P0 MinimalContinuationWorkflow 兼容路径 | 不得执行 user_action 专属动作 |
| system_maintenance | 诊断/维护任务 | 不得执行业务门控动作 |
| quick_trial | 试写链路 | 不得正式 apply 或写正式资产 |

### 6.2 门控动作专属清单

以下动作必须 `caller_type=user_action`：

1. CandidateDraft：accept / reject / apply
2. Direction：select
3. ChapterPlan：confirm / reject
4. AISuggestion：accept / dismiss / convert
5. ConflictGuard：resolve / decide
6. MemoryReviewGate：approve / edit_and_approve / reject / apply（路由段使用 `edit-approve`）

命名映射约定（冻结）：

- 业务动作语义名统一使用 `edit_and_approve`。
- API 路由段可使用 `edit-approve`（URL 风格）。
- `edit_approve` 仅作为历史兼容别名，不作为新增接口命名。
7. AgentWorkflow 控制：pause / resume / cancel

### 6.3 user_action 双校验（冻结）

门控动作必须同时满足：

1. `caller_type = user_action`
2. `user_action = true`
3. `idempotency_key` 存在

不满足默认返回：

- `caller_type_forbidden`
- `action_not_allowed`
- `idempotency_key_required` 或 `idempotency_key_conflict`

## 七、idempotency_key 与 request_id / trace_id 贯穿规则

1. 所有副作用写操作必须携带 `idempotency_key`。
2. 所有门控动作必须携带 `idempotency_key`。
3. `request_id / trace_id` 必须从 API 透传至 Application Service、AuditLog、AgentTrace。
4. 幂等冲突统一返回 `idempotency_key_conflict`。
5. 幂等策略沿用 P0 口径，P1 长流程过期时间可在实现阶段参数化。

## 八、轮询优先与 SSE 可选增强边界

### 8.1 轮询优先策略

| 资源 | 初始轮询间隔 | 建议上限 | 终态停止 |
|---|---:|---:|---|
| AgentSession | 2s | 5s | completed/failed/cancelled/waiting_for_user |
| AIJob | 1.5s~3s | 5s | completed/failed/cancelled |
| CandidateDraft | 2s | 5s | generated/failed |
| DirectionProposal | 3s | 5s | waiting_for_selection/failed |
| ChapterPlan | 3s | 5s | waiting_for_confirmation/failed |
| ConflictGuard | 3s | 5s | detected/failed |

### 8.2 SSE 默认策略（冻结）

1. P1 默认不开启 SSE。
2. SSE 是可选增强，允许环境级配置，建议配置项：`ai.sse.enabled = false`。
3. 前端必须以轮询为主路径。
4. SSE 不可用时必须自动回退轮询。
5. SSE 不作为 P1 验收必需能力。

### 8.3 SSE 安全事件白名单（合并去重）

1. `agent_session_started`
2. `agent_step_started`
3. `agent_step_completed`
4. `agent_step_failed`
5. `agent_session_completed`
6. `agent_session_failed`
7. `direction_proposals_ready`
8. `chapter_plan_ready`
9. `candidate_version_created`
10. `review_report_ready`
11. `memory_suggestion_generated`
12. `conflict_detected`
13. `waiting_for_user_entered`

### 8.4 SSE payload 安全约束

仅允许：状态、ID、安全摘要、`safe_ref`、`warning_code`、`error_code`、计数。  
禁止：完整正文、完整 Prompt、完整 ContextPack、完整 CandidateDraft、API Key。

## 九、前端最小集成边界

### 9.1 最小入口清单

1. Agent 进度面板
2. 方向推演面板
3. 章节计划面板
4. 候选稿版本面板
5. 审稿报告展示
6. AI 建议面板
7. Conflict Guard 对比
8. 记忆更新审批
9. Agent Trace 面板
10. Plot Arc 状态
11. Context Pack 预览

### 9.2 最低承诺

1. 轮询优先，SSE 可选增强。
2. 每个关键模块至少有 list + detail 两级可见入口。
3. `waiting_for_user` 必须有显著前端状态表达。
4. Detail Trace 默认折叠，且受权限控制。

### 9.3 AgentTrace Detail 权限（冻结）

1. AgentTrace Detail 查询必须具备开发者/高级模式权限。
2. 普通用户默认仅看 Session Trace + Step Trace 摘要。
3. `?detail=true` 不能绕过权限，仅在权限通过后生效。

## 十、错误码分层与 safe_message 规则

### 10.1 错误码分层

1. 通用层：`invalid_request / permission_denied / not_found / conflict / internal_error`
2. 门控层：`action_not_allowed / waiting_for_user_required / idempotency_key_required / idempotency_key_conflict / caller_type_forbidden`
3. 模块层：沿用各 P1 模块冻结口径

### 10.2 P1 新增错误码方向（吸收 _001）

- `agent_session_not_found`
- `agent_session_not_running`
- `direction_proposal_not_ready`
- `direction_already_selected`
- `chapter_plan_not_confirmed`
- `max_revision_rounds_exceeded`
- `candidate_version_not_found`
- `cannot_apply_superseded_version`
- `suggestion_not_found`
- `suggestion_already_decided`
- `conflict_record_not_found`
- `blocking_conflict_unresolved`
- `cannot_override_blocking`
- `memory_gate_not_found`
- `memory_revision_apply_blocked`
- `memory_rollback_not_allowed`
- `idempotency_key_conflict`
- `caller_type_forbidden`

### 10.3 safe_message 规则

1. 可理解、不可泄密。
2. 不包含堆栈、SQL、Prompt 片段、正文原文。
3. 对冲突类错误应给出下一步建议。

## 十一、与 P1-01 ~ P1-10 的接口边界

1. P1-01 AgentRuntime：API 仅暴露会话控制与状态，不定义 Runtime 内部推进。
2. P1-02 AgentWorkflow：API 仅暴露编排状态和用户门控入口，不重定义 Stage/Decision。
3. P1-03~P1-09：API 只映射已冻结模型和动作，不新增跨模块捷径。
4. P1-10 AgentTrace：API 暴露 Trace 摘要与受控 detail，不暴露敏感原始日志。

## 十二、与 P1-UI / DESIGN.md 的关系

1. P1-UI 定义信息架构与交互流程。
2. DESIGN.md 定义视觉系统与组件规范。
3. P1-11 负责把交互需求映射到可消费 API 边界。
4. 前端实现必须同时遵循 P1-UI、DESIGN.md、P1-11。

## 十三、安全边界与合规约束

1. API 层不得直连 Provider / ModelRouter / Repository。
2. API 层不得伪造 user_action。
3. API 层不得允许 AI/Workflow 自动执行 human gate 动作。
4. API 层不得泄露完整 Prompt / ContextPack / 正文 / CandidateDraft / API Key。
5. Quick Trial 不得产生正式资产副作用。
6. ConflictGuard blocking override API 默认禁用；请求 override 默认 `cannot_override_blocking`。
7. MemoryRevision 批量 approve/batch apply 不作为 P1 必须能力。
8. P1 保留 `workflow_compat` caller_type 作为 P0 MinimalContinuationWorkflow 兼容迁移路径。
9. `workflow_compat` 不得执行任何 user_action 专属动作，且不得 formal_write。
10. Writing Task 直接 edit 非 P1 首批必须能力；若实现阶段开放，必须 `caller_type=user_action` 且携带 `idempotency_key`，并不得绕过 Direction/ChapterPlan 确认边界。

## 十四、P1-11 不做事项清单

1. 不改造成完整 OpenAPI 文档。
2. 不生成字段级 DTO 大全。
3. 不写代码，不新增数据库表设计。
4. 不修改 P1-01 ~ P1-10 已冻结业务规则。
5. 不重定义 ConflictGuard 规则矩阵。
6. 不重定义 MemoryReviewGate 审批流程。
7. 不引入 P2 自动连续续写队列。
8. 不引入正文 token streaming。
9. 不引入成本看板 / 分析看板。
10. 不引入 @ 引用 / Citation Link / Opening Agent。
11. 不让 SSE 成为 P1 必需依赖。

## 十五、P1-11 验收标准

1. API 分组固定为 11 组并与 P1 总纲一致。
2. CandidateDraft 主路径为 `/api/v2/ai/candidate-drafts` 体系。
3. caller_type 枚举与语义冻结一致。
4. 门控动作具备 `caller_type + user_action + idempotency_key` 三重校验。
5. 轮询优先策略与终态停止规则明确。
6. SSE 可选增强，默认关闭，回退轮询路径明确。
7. SSE 白名单与 payload 脱敏规则明确。
8. AgentTrace Detail 权限控制明确，不可被 `?detail=true` 绕过。
9. Presentation API 与 ToolFacade 路径边界明确。
10. 错误码分层与 safe_message 规则明确。
11. 未引入 P2 功能与越界能力。
12. SSE 默认关闭且仅为可选增强，轮询是 P1 主路径。
13. `workflow_compat` 保留为 P0 兼容迁移 caller_type，但不得执行 user_action / formal_write。
14. Context Pack 预览仅暴露 summary + layers preview，不泄露完整上下文。
15. Writing Task 首批支持 list + detail + confirm；直接 edit 后置，或必须受 user_action/idempotency 约束。

## 十六、P1-11 待确认点

P1-11 封板前待确认点已全部落地，无阻塞待确认点。

后续仅允许在 P1 实现阶段细化：

1. `ai.sse.enabled` 在不同部署环境中的默认值；
2. `workflow_compat` 在 P1 收尾阶段是否移除；
3. Context Pack layers preview 的分页与摘要长度；
4. Writing Task edit 是否作为 P1 后续增强开放。

## 附录 A：P1 API 分组速查表

| 分组 | 前缀方向 | 最小入口 |
|---|---|---|
| Agent Session | `/api/v2/ai/sessions` | create + list + detail + pause/resume/cancel |
| Agent Trace | `/api/v2/ai/traces` | list + detail + step + detail-view |
| Plot Arc | `/api/v2/ai/plot-arcs` | list + detail + status |
| Direction Proposal | `/api/v2/ai/directions` | generate + list + detail + select |
| Chapter Plan | `/api/v2/ai/chapter-plans` | generate + list + detail + confirm/reject |
| Multi-round CandidateDraft | `/api/v2/ai/candidate-drafts` | draft + versions + diff + accept/reject/apply |
| AI Suggestion | `/api/v2/ai/suggestions` | list + detail + accept/dismiss/convert |
| Conflict Guard | `/api/v2/ai/conflicts` | list + detail + resolve/decide |
| Memory Revision | `/api/v2/ai/memory-gates` `/api/v2/ai/memory-revisions` | gate list/detail + approve/reject/apply + revision detail |
| Context Pack | `/api/v2/ai/context-packs` | summary + layers preview |
| Writing Task | `/api/v2/ai/writing-tasks` | list + detail + confirm（edit 为后续增强） |

## 附录 B：API 路由速查表

| Method | 路由方向 | caller_type |
|---|---|---|
| POST | `/api/v2/ai/sessions` | user_action |
| POST | `/api/v2/ai/sessions/{session_id}/pause` | user_action |
| POST | `/api/v2/ai/sessions/{session_id}/resume` | user_action |
| POST | `/api/v2/ai/sessions/{session_id}/cancel` | user_action |
| POST | `/api/v2/ai/directions/{proposal_id}/select` | user_action |
| POST | `/api/v2/ai/chapter-plans/{plan_id}/confirm` | user_action |
| POST | `/api/v2/ai/chapter-plans/{plan_id}/reject` | user_action |
| POST | `/api/v2/ai/candidate-drafts/{draft_id}/versions/{version_id}/accept` | user_action |
| POST | `/api/v2/ai/candidate-drafts/{draft_id}/versions/{version_id}/reject` | user_action |
| POST | `/api/v2/ai/candidate-drafts/{draft_id}/apply` | user_action |
| POST | `/api/v2/ai/suggestions/{suggestion_id}/accept` | user_action |
| POST | `/api/v2/ai/suggestions/{suggestion_id}/dismiss` | user_action |
| POST | `/api/v2/ai/suggestions/{suggestion_id}/convert` | user_action |
| POST | `/api/v2/ai/conflicts/{record_id}/items/{item_id}/resolve` | user_action |
| POST | `/api/v2/ai/conflicts/{record_id}/decide` | user_action |
| POST | `/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/approve` | user_action |
| POST | `/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/edit-approve` | user_action |
| POST | `/api/v2/ai/memory-gates/{gate_id}/suggestions/{suggestion_id}/reject` | user_action |
| POST | `/api/v2/ai/memory-gates/{gate_id}/apply` | user_action |
| GET | `/api/v2/ai/traces/{trace_id}` | user_action（detail 需开发者权限） |

## 附录 C：P1-11 与 P1 总纲对照

| P1 总纲要求 | P1-11 冻结内容 |
|---|---|
| P1 API 分组方向 | 固化为 11 组分组方向 |
| request_id / trace_id 贯穿 | 通用 DTO 规则冻结 |
| caller_type 与 user_action 边界 | 门控动作三重校验冻结 |
| 轮询优先，SSE 可选 | 默认轮询 + SSE 可选增强 |
| API 不承载业务逻辑 | API/ToolFacade/Application Service 路径边界明确 |
| 不泄露敏感内容 | 响应、日志、SSE 脱敏规则明确 |
| 前端最小集成边界 | 11 个入口与最低承诺明确 |
| 不引入 P2 功能 | 不做事项清单明确排除 |
