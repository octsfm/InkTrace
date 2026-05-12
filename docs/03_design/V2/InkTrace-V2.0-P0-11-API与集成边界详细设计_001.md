# InkTrace V2.0-P0-11 API 与集成边界详细设计

版本：v2.0-p0-detail-11  
状态：P0 模块级详细设计  
依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`
- `docs/07_overview/InkTrace-V2.0-概要设计说明书.md`
- `docs/02_architecture/InkTrace-V2.0-架构设计说明书.md`
- `docs/03_design/InkTrace-V2.0-P0-详细设计总纲.md`
- `docs/03_design/InkTrace-V2.0-P0-01-AI基础设施详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-02-AIJobSystem详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-03-初始化流程详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-04-StoryMemory与StoryState详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-05-VectorRecall详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-06-ContextPack详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-07-ToolFacade与权限详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-08-MinimalContinuationWorkflow详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计.md`
- `docs/03_design/InkTrace-V2.0-P0-10-AIReview详细设计.md`

---

## 一、文档定位与设计范围

### 1.1 文档定位

本文档是 InkTrace V2.0-P0 的第十一个模块级详细设计文档，仅覆盖 P0 API 与集成边界。

P0-11 的核心目标是定义 P0 AI 能力对 Presentation / API 层的最小可用集成边界。它不实现后端、不定义数据库表、不定义前端 UI 细节，只定义 API 边界、DTO 方向、状态展示、错误响应、轮询 / SSE 边界。

本文档不替代任何 P0-01 ~ P0-10 模块级详细设计，不写代码、不修改源码、不生成数据库迁移、不拆 Task、不进入开发计划。

### 1.2 设计范围

本模块覆盖：

1. AI Settings API。
2. Initialization API。
3. AIJob API。
4. ContextPack / Continuation API。
5. CandidateDraft API。
6. HumanReviewGate API。
7. AIReview API。
8. Quick Trial API。
9. SSE / 轮询边界。
10. API 权限与 caller_type。
11. API DTO / Request / Response 方向。
12. 错误码统一格式。
13. idempotency_key 在 API 层的传递。
14. request_id / trace_id 在 API 层的传递。
15. API 与 ToolFacade 的边界。
16. API 与 Application Service 的边界。
17. API 与 V1.1 Local-First 保存链路的边界。
18. API 与前端状态展示的边界。
19. 安全、隐私与日志。
20. P0 验收标准。

### 1.3 本文档不覆盖

P0-11 不覆盖：

- 后端 Service / Repository / Infrastructure 实现。
- 数据库表结构 DDL。
- 前端 UI 组件、布局、交互细节。
- 完整 Agent Runtime。
- 五 Agent Workflow。
- 完整 AI Suggestion / Conflict Guard。
- 复杂 Knowledge Graph。
- Citation Link。
- @ 标签引用系统。
- 复杂多路召回融合。
- 自动连续续写队列。
- 成本看板。
- 分析看板。
- 复杂权限系统 / 多租户 RBAC。
- Provider SDK 适配实现。
- 数据清理策略完整定义。

---

## 二、P0 API 总体目标

### 2.1 核心目标

P0 API 层的核心目标是：

1. 为前端提供 P0 AI 能力的统一、安全、可追踪的 HTTP API 入口。
2. 维护 API 与 Application Service 之间的严格边界——API 层不承载业务逻辑。
3. 确保 request_id / trace_id 贯穿所有 AI API，支撑全链路追踪。
4. 确保 caller_type 正确传递，防止 AI / Workflow 冒充用户确认。
5. 定义统一的 Request / Response / Error 格式，降低前端集成成本。
6. 明确 SSE / 轮询边界，P0 默认非流式，通过轮询获取异步结果。

### 2.2 核心边界

必须明确：

1. API 层不得绕过 Application Service。
2. API 层不得直接访问 RepositoryPort。
3. API 层不得直接访问 Provider SDK。
4. API 层不得直接访问 ModelRouter。
5. API 层不得伪造 user_action。
6. API 层不得让 AI / Workflow 冒充用户确认。
7. API 层必须维护 request_id / trace_id。
8. API 层必须维护 caller_type。
9. API 层必须遵守 P0-07 ToolFacade 权限边界。
10. API 层必须遵守 P0-09 HumanReviewGate 用户确认边界。
11. API 层必须遵守 P0-10 AIReview 不阻断 HumanReviewGate 基本操作的边界。

---

## 三、模块边界与不做事项

### 3.1 P0-11 负责

| 职责 | 说明 |
|---|---|
| API 路由分组 | 按 AI Settings / Initialization / AIJob / Continuation / CandidateDraft / AIReview 分组 |
| DTO 方向定义 | Request / Response 字段方向，不含具体实现 |
| 错误码统一格式 | safe_message / error_code / retryable / request_id / trace_id |
| caller_type 权限矩阵 | 每个 API 的 caller_type 准入规则 |
| idempotency_key 规则 | API 层幂等键传递与安全约束 |
| SSE / 轮询边界 | P0 默认策略与安全事件白名单 |
| request_id / trace_id 传递 | 跨层贯穿规则 |
| 安全日志边界 | API 日志不记录敏感内容 |

### 3.2 P0-11 不负责

| 职责 | 归属 |
|---|---|
| 业务逻辑实现 | Application Service（P0-01 ~ P0-10） |
| 数据库 schema | Infrastructure / 数据库迁移 |
| 前端 UI 交互 | 前端设计文档 |
| AI 模型调用 | P0-01 / P0-08 / P0-10 |
| CandidateDraft 状态机 | P0-09 |
| Job 状态机 | P0-02 |
| 正文 Local-First 保存 | V1.1 / P0-09 apply 链路 |

### 3.3 禁止行为

- API 层不得直接调用 Provider SDK。
- API 层不得直接调用 ModelRouter。
- API 层不得直接访问 RepositoryPort。
- API 层不得绕过 ToolFacade 调用 Tool。
- API 层不得伪造 caller_type。
- API 层不得让 workflow / system 冒充 user_action 执行 accept / apply / reject。
- API Response 不得包含 API Key 明文。
- API Error Response 不得包含完整正文 / Prompt / CandidateDraft。

---

## 四、API 总体分组

P0 API 按以下 6 组组织：

| 分组 | 路由前缀（方向） | 核心职责 |
|---|---|---|
| AI Settings | `/api/v2/ai/settings` | Provider 配置、模型列表、连接测试 |
| Initialization | `/api/v2/ai/init` | 作品初始化启动、状态查询、取消、重试 |
| AIJob | `/api/v2/ai/jobs` | Job / Step 状态查询、取消、重试 |
| Continuation | `/api/v2/ai/continuation` | 正式续写、Quick Trial、保存为候选稿 |
| CandidateDraft | `/api/v2/ai/candidates` | 候选稿列表、详情、accept / apply / reject |
| AIReview | `/api/v2/ai/review` | 审阅启动、结果查询、取消 |

说明：

- 路由前缀为方向性建议，最终路径以后端路由注册为准。
- 所有 API 公共前缀 `/api/v2/ai` 用于区分 V1 非 AI API。
- V1.1 正文保存（Local-First）不在 P0-11 路由范围内，走现有 V1 路由。

---

## 五、通用 Request / Response / Error 规范

### 5.1 通用 Request 字段

所有 AI 相关 API Request 建议包含以下通用字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| request_id | string | 否 | 前端可传，后端未传时自动生成 |
| trace_id | string | 否 | 后端生成或贯穿，前端可传以关联客户端上下文 |
| idempotency_key | string | 否 | 涉及写入 / 触发任务时建议或必须 |
| caller_type | string | 是 | user_action / workflow / quick_trial / system |
| work_id | string | 是 | 作品 ID |
| target_chapter_id | string | 否 | 目标章节 ID |
| client_timestamp | string | 否 | 客户端时间戳，用于审计 |

规则：

1. user_action API 的 caller_type 必须是 user_action。
2. Quick Trial API 的 caller_type 可为 quick_trial。
3. Workflow 内部 API 不应由前端直接调用。
4. request_id / trace_id 必须贯穿 Application / ToolFacade / AIJob / AuditLog。
5. idempotency_key 不得包含正文、Prompt、API Key 或敏感信息。

### 5.2 通用 Response 字段

所有 AI 相关 API Response 建议包含以下通用字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| request_id | string | 是 | 请求 ID |
| trace_id | string | 是 | 追踪 ID |
| status | string | 是 | ok / error / pending |
| data | object | 否 | 业务数据，成功时返回 |
| warnings | string[] | 否 | 警告列表 |
| error | ErrorDetail | 否 | 错误详情，仅失败时返回 |
| job_id | string | 否 | 关联 AIJob ID，异步任务时返回 |
| result_ref | string | 否 | 结果引用，指向可查询的结果资源 |
| created_at | string | 否 | 创建时间 |
| updated_at | string | 否 | 更新时间 |

### 5.3 通用 Error 格式

统一错误结构：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| error_code | string | 是 | 错误码，如 `candidate_not_found` |
| safe_message | string | 是 | 可展示给用户的安全消息 |
| detail_ref | string | 否 | 指向安全日志或审计引用 |
| retryable | boolean | 是 | 是否可重试 |
| request_id | string | 是 | 请求 ID |
| trace_id | string | 是 | 追踪 ID |

规则：

1. safe_message 可展示给用户。
2. detail_ref 指向安全日志或审计引用。
3. 错误响应不得包含完整正文。
4. 错误响应不得包含完整 Prompt。
5. 错误响应不得包含完整 CandidateDraft。
6. 错误响应不得包含 API Key。
7. retryable 必须与 P0-01 / P0-02 retry 规则一致。

---

## 六、SSE / 轮询边界

### 6.1 P0 默认策略

1. P0 不实现正文 token stream。
2. P0 不逐 token 推送 Writer 输出。
3. P0 不逐 token 推送 Review 输出。
4. P0 默认通过轮询获取 Job / Result 状态。

### 6.2 轮询 API

前端通过以下 API 轮询状态：

| API | 说明 |
|---|---|
| get_job_status | 获取 Job 整体状态 |
| get_job_steps | 获取步骤列表和进度 |
| get_continuation_result | 获取续写结果 |
| list_candidate_drafts | 获取候选稿列表 |
| get_review_result | 获取审阅结果 |
| list_review_results | 获取审阅结果列表 |
| get_initialization_status | 获取初始化状态 |

### 6.3 SSE 安全事件白名单

如果 Presentation 层使用 SSE，P0 只允许推送以下安全状态事件：

| 事件 | 说明 | 禁止携带 |
|---|---|---|
| job_started | Job 已启动 | 正文 / Prompt / API Key |
| step_started | Step 已开始 | 正文 / Prompt / API Key |
| step_progress | Step 进度更新 | 正文 / Prompt / API Key |
| step_completed | Step 已完成 | 正文 / Prompt / API Key |
| workflow_blocked | Workflow 被阻断 | 正文 / Prompt / API Key |
| workflow_failed | Workflow 失败 | 正文 / Prompt / API Key |
| candidate_ready | 候选稿已生成 | 完整候选稿内容 |
| review_job_created | 审阅 Job 已创建 | 正文 / Prompt / API Key |
| review_completed | 审阅已完成 | 完整审阅结果正文 |
| warning | 警告事件 | 正文 / Prompt / API Key |

规则：

1. SSE 不得推送完整正文 token stream。
2. SSE 不得推送完整 Prompt。
3. SSE 不得推送完整 ContextPack。
4. SSE 不得推送完整 CandidateDraft。
5. SSE 不得推送 API Key。
6. candidate_ready 可携带 candidate_draft_id / job_id / request_id / trace_id，不携带完整候选稿内容。
7. review_completed 可携带 review_result_id / severity_summary，不携带完整 items 正文。
8. P1 / 后续可设计 streaming token 输出。

---

## 七、caller_type 与权限矩阵

### 7.1 caller_type 定义

| caller_type | 含义 | 来源 |
|---|---|---|
| user_action | 用户手动操作 | HumanReviewGate / UI 按钮 |
| workflow | Workflow 内部调用 | P0-08 MinimalContinuationWorkflow |
| quick_trial | Quick Trial 快速试写 | 用户 Quick Trial 请求 |
| system | 系统内部诊断 / 维护 | 后台任务、健康检查 |

### 7.2 权限矩阵

| API / Action | user_action | workflow | quick_trial | system |
|---|---|---|---|---|
| start_initialization | 允许 | 禁止 | 禁止 | 可选受限 |
| get_initialization_status | 允许 | 允许 | 允许 | 允许 |
| cancel_initialization | 允许 | 禁止 | 禁止 | 可选受限 |
| retry_initialization_step | 允许 | 禁止 | 禁止 | 可选受限 |
| start_continuation | 允许 | 禁止 | 禁止 | 禁止 |
| get_continuation_result | 允许 | 允许 | 允许 | 允许 |
| cancel_continuation | 允许 | 禁止 | 禁止 | 可选受限 |
| quick_trial_continuation | 允许 | 禁止 | 允许 | 禁止 |
| save_quick_trial_as_candidate | 允许 | 禁止 | 禁止 | 禁止 |
| list_candidate_drafts | 允许 | 允许 | 允许 | 允许 |
| get_candidate_draft | 允许 | 允许 | 允许 | 允许 |
| accept_candidate_draft | 允许 | 禁止 | 禁止 | 禁止 |
| apply_candidate_to_draft | 允许 | 禁止 | 禁止 | 禁止 |
| reject_candidate_draft | 允许 | 禁止 | 禁止 | 禁止 |
| start_review_candidate_draft | 允许 | 受限/默认禁止 | 可选受限 | 禁止 |
| get_review_result | 允许 | 允许 | 允许 | 允许 |
| list_review_results | 允许 | 允许 | 允许 | 允许 |
| cancel_review_job | 允许 | 禁止 | 可选受限 | 可选受限 |
| review_quick_trial_output | 允许 | 禁止 | 允许 | 禁止 |
| get_job_status | 允许 | 允许 | 允许 | 允许 |
| get_job_steps | 允许 | 允许 | 允许 | 允许 |
| cancel_job | 允许 | 禁止 | 禁止 | 可选受限 |
| retry_job | 允许 | 禁止 | 禁止 | 可选受限 |
| retry_step | 允许 | 禁止 | 禁止 | 可选受限 |
| get_ai_settings | 允许 | 允许 | 允许 | 允许 |
| update_ai_settings | 允许 | 禁止 | 禁止 | 禁止 |
| test_provider_connection | 允许 | 禁止 | 禁止 | 可选受限 |

### 7.3 权限规则

1. Presentation API 默认 caller_type = user_action。
2. 用户显式 Quick Trial 请求可转换为 caller_type = quick_trial。
3. Workflow caller_type 不应由前端伪造。
4. system caller_type 仅用于内部诊断 / 维护。
5. accept_candidate_draft / apply_candidate_to_draft / reject_candidate_draft 只能 user_action。
6. start_review_candidate_draft P0 默认只允许 user_action；workflow 触发默认禁止 / 受限。
7. save_candidate_draft 由 Workflow / ToolFacade 触发，不应由普通前端直接调用正式路径。
8. save_quick_trial_as_candidate 必须转为明确 user_action。
9. API 层必须把 caller_type 传递到 Application Service / ToolExecutionContext / AuditLog。
10. API 层不得让 AI / Workflow 冒充 user_action。

---

## 八、idempotency_key API 层规则

### 8.1 各 API 幂等要求

| API | idempotency_key | 规则 |
|---|---|---|
| start_initialization | 建议 | 同一 work_id 重复初始化返回当前状态 |
| start_continuation | 建议 | 同一 work_id + chapter_id + scope 去重 |
| save_candidate_draft | 内部必须 | Workflow / ToolFacade 内部生成，API 层不直接暴露 |
| save_quick_trial_as_candidate | 必须 | 用户保存 Quick Trial 为候选稿时必传 |
| accept_candidate_draft | 不强制 | 重复 accept 幂等返回当前状态 |
| apply_candidate_to_draft | 建议强制 | 建议使用 apply_request_id 防重复 apply |
| reject_candidate_draft | 不强制 | 重复 reject 幂等返回当前状态 |
| start_review_candidate_draft | 可选 | 提供时用于 duplicate_review_request 判断 |
| test_provider_connection | 不需要 | 只读操作，无需幂等 |
| update_ai_settings | 不强制 | 按 last_write_wins 或 version 乐观锁 |

### 8.2 幂等规则

1. idempotency_key 不得包含正文、Prompt、API Key 或敏感信息。
2. API 层可以记录 idempotency_key hash，不记录原文。
3. 缺少 idempotency_key 时允许生成新结果，但需记录 request_id / trace_id。
4. 重复请求返回已有结果时，Response 应包含 original_request_id / original_created_at。
5. idempotency_conflict 不创建新资源，返回已有资源引用。

---

## 九、AI Settings API

### 9.1 get_ai_settings

| 项 | 值 |
|---|---|
| API 名称 | get_ai_settings |
| 调用者 | 前端 / HumanReviewGate |
| caller_type | user_action |
| 是否异步 | 否，同步返回 |
| 是否返回 job_id | 否 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| provider_configs | 是 | Provider 配置列表，API Key 返回 mask（如 `ksX***a3b`） |
| model_roles | 是 | 模型角色配置（kimi_main / deepseek_writer / reviewer） |
| default_review_scope | 是 | 默认审阅范围 |
| allow_degraded_default | 是 | allow_degraded 默认值 |
| review_context_token_budget | 否 | token budget 配置 |
| last_test_status | 否 | 最近连接测试状态 |
| last_test_at | 否 | 最近连接测试时间 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：** 无特定错误码（只读操作）。

**安全日志边界：** API Key 返回 mask，不返回明文。普通日志不记录 API Key。

### 9.2 update_ai_settings

| 项 | 值 |
|---|---|
| API 名称 | update_ai_settings |
| 调用者 | 前端设置页 |
| caller_type | user_action（必须） |
| 是否异步 | 否，同步返回 |
| 是否返回 job_id | 否 |
| idempotency_key | 不强制 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| provider_configs | 否 | Provider 配置更新，API Key 允许写入 |
| model_roles | 否 | 模型角色更新 |
| default_review_scope | 否 | 审阅范围默认值 |
| allow_degraded_default | 否 | allow_degraded 默认值 |
| review_context_token_budget | 否 | token budget 配置 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| updated_fields | 是 | 已更新字段列表 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| provider_config_invalid | Provider 配置不合法 |
| model_role_invalid | 模型角色配置不合法 |

**安全日志边界：** API Key 只允许写入，不允许读取明文。普通日志不记录 API Key。

### 9.3 test_provider_connection

| 项 | 值 |
|---|---|
| API 名称 | test_provider_connection |
| 调用者 | 前端设置页 |
| caller_type | user_action |
| 是否异步 | 建议同步短路径（< 10s），超时降级返回 pending |
| 是否返回 job_id | 否（或可选返回轻量 job_id） |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| provider_name | 是 | Provider 名称 |
| model_name | 否 | 指定模型，不传则用默认 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| provider_name | 是 | Provider 名称 |
| success | 是 | 连接是否成功 |
| latency_ms | 否 | 延迟毫秒 |
| error_code | 否 | 失败时的错误码 |
| last_test_status | 是 | 测试结果，建议写回 AISettings |
| last_test_at | 是 | 测试时间 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| provider_timeout | 连接超时，按 P0-01 retry |
| provider_auth_failed | 鉴权失败，不 retry |
| provider_rate_limited | 限流，按 P0-01 retry |
| provider_unavailable | 不可用，按 P0-01 retry |

**安全日志边界：** 测试请求不记录 API Key 明文。Provider auth failed 不暴露 API Key。

---

## 十、Initialization API

### 10.1 start_initialization

| 项 | 值 |
|---|---|
| API 名称 | start_initialization |
| 调用者 | 前端 / 用户在作品初始化入口触发 |
| caller_type | user_action |
| 是否异步 | 是，创建 AIJob 后立即返回 |
| 是否返回 job_id | 是 |
| idempotency_key | 建议 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| force_reinitialize | 否 | 是否强制重新初始化（默认 false） |
| idempotency_key | 建议 | 同一 work_id 重复请求返回当前初始化状态 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 初始化 AIJob ID |
| initialization_status | 是 | pending / running（刚创建时） |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| initialization_already_running | 已有初始化 Job 在运行 |
| initialization_already_completed | 已完成且非 stale，force_reinitialize = false 时返回 |
| work_empty | 作品无内容，无法初始化 |

**安全日志边界：** 不记录作品正文。

### 10.2 get_initialization_status

| 项 | 值 |
|---|---|
| API 名称 | get_initialization_status |
| 调用者 | 前端轮询 |
| caller_type | user_action / workflow / system |
| 是否异步 | 否，同步返回当前状态 |
| 是否返回 job_id | 否（传入 job_id 或从 work_id 查询） |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 否 | 指定 Job ID，不传则返回最近一次 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 初始化 AIJob ID |
| initialization_status | 是 | pending / running / completed / failed / cancelled / stale |
| current_phase | 是 | outline_analysis / manuscript_analysis / building_index / completed |
| phase_progress | 是 | 当前阶段进度（如 3/15 章已分析） |
| analyzed_chapter_count | 是 | 已分析章节数 |
| total_chapter_count | 是 | 总章节数 |
| partial_success | 否 | 是否有部分章节分析失败但整体标记完成 |
| degraded_reasons | 否 | 降级原因列表 |
| stale_warning | 否 | 初始化结果是否 stale |
| warnings | 否 | 警告列表 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| initialization_not_found | 未找到初始化记录 |
| job_not_found | 指定的 Job ID 不存在 |

**安全日志边界：** 不记录章节正文摘要细节到普通日志。

### 10.3 cancel_initialization

| 项 | 值 |
|---|---|
| API 名称 | cancel_initialization |
| 调用者 | 前端 |
| caller_type | user_action |
| 是否异步 | 否，同步返回取消确认 |
| 是否返回 job_id | 是 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 否 | 指定 Job ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 已取消的 Job ID |
| previous_status | 是 | 取消前状态 |
| current_status | 是 | cancelled |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job ID 不存在 |
| job_not_cancellable | Job 状态不允许取消（如已完成） |

**安全日志边界：** 标准。

### 10.4 retry_initialization_step

| 项 | 值 |
|---|---|
| API 名称 | retry_initialization_step |
| 调用者 | 前端 |
| caller_type | user_action |
| 是否异步 | 是，重试后继续异步执行 |
| 是否返回 job_id | 是 |
| idempotency_key | 建议 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 是 | Job ID |
| step_id | 是 | 要重试的 Step ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | Job ID |
| step_id | 是 | 正在重试的 Step ID |
| step_status | 是 | retrying / pending |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job ID 不存在 |
| step_not_found | Step ID 不存在 |
| step_not_retryable | Step 不可重试 |
| retry_limit_exceeded | 重试次数已达上限 |

**安全日志边界：** 标准。

---

## 十一、AIJob API

### 11.1 get_job_status

| 项 | 值 |
|---|---|
| API 名称 | get_job_status |
| 调用者 | 前端轮询 |
| caller_type | user_action / workflow / system |
| 是否异步 | 否，同步返回 |
| 是否返回 job_id | 否（传入 job_id） |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 是 | Job ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | Job ID |
| job_type | 是 | initialization / continuation / review / quick_trial |
| job_status | 是 | pending / running / completed / failed / cancelled / partial_success |
| step_count | 是 | 总步骤数 |
| completed_step_count | 是 | 已完成步骤数 |
| failed_step_count | 是 | 失败步骤数 |
| can_retry | 是 | 是否可重试 |
| can_cancel | 是 | 是否可取消 |
| created_at | 是 | 创建时间 |
| updated_at | 是 | 更新时间 |
| warnings | 否 | 警告列表 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job ID 不存在 |

**安全日志边界：** 标准。

### 11.2 get_job_steps

| 项 | 值 |
|---|---|
| API 名称 | get_job_steps |
| 调用者 | 前端 |
| caller_type | user_action |
| 是否异步 | 否，同步返回 |
| 是否返回 job_id | 否 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 是 | Job ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | Job ID |
| steps | 是 | Step 列表，每个 step 包含 step_id / step_type / status / progress / error_code / can_retry / can_skip / created_at / updated_at |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job ID 不存在 |

**安全日志边界：** Step 详情不包含完整 Prompt 或正文。

### 11.3 cancel_job

| 项 | 值 |
|---|---|
| API 名称 | cancel_job |
| 调用者 | 前端 |
| caller_type | user_action |
| 是否异步 | 否，同步返回取消确认 |
| 是否返回 job_id | 是 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 是 | Job ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 已取消的 Job ID |
| previous_status | 是 | 取消前状态 |
| current_status | 是 | cancelled |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job ID 不存在 |
| job_not_cancellable | Job 状态不允许取消 |

**安全日志边界：** 标准。

### 11.4 retry_job

| 项 | 值 |
|---|---|
| API 名称 | retry_job |
| 调用者 | 前端 |
| caller_type | user_action |
| 是否异步 | 是 |
| 是否返回 job_id | 是（可能创建新 Job 或复用） |
| idempotency_key | 建议 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 是 | Job ID |
| retry_failed_only | 否 | 仅重试失败 Step（默认 true） |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 新 Job ID 或复用 ID |
| job_status | 是 | pending / running |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job ID 不存在 |
| job_not_retryable | Job 状态不允许重试 |
| retry_limit_exceeded | 重试次数已达上限 |

**安全日志边界：** 标准。

### 11.5 retry_step

| 项 | 值 |
|---|---|
| API 名称 | retry_step |
| 调用者 | 前端 |
| caller_type | user_action |
| 是否异步 | 是 |
| 是否返回 job_id | 是 |
| idempotency_key | 建议 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 是 | Job ID |
| step_id | 是 | Step ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | Job ID |
| step_id | 是 | Step ID |
| step_status | 是 | retrying / pending |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job ID 不存在 |
| step_not_found | Step ID 不存在 |
| step_not_retryable | Step 不可重试 |
| job_step_not_running | Step 不在运行状态，无法重试 |
| retry_limit_exceeded | 重试次数已达上限 |

**安全日志边界：** 标准。

---

## 十二、Continuation / Quick Trial API

### 12.1 start_continuation

| 项 | 值 |
|---|---|
| API 名称 | start_continuation |
| 调用者 | 前端 / HumanReviewGate |
| caller_type | user_action |
| 是否异步 | 是，创建 AIJob 后立即返回 |
| 是否返回 job_id | 是 |
| idempotency_key | 建议 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| target_chapter_id | 是 | 目标章节 ID |
| writing_task | 是 | 续写任务描述（用户输入或系统生成） |
| allow_degraded | 否 | 是否允许 degraded ContextPack（默认 true） |
| idempotency_key | 建议 | 防重复创建续写 Job |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 续写 AIJob ID |
| workflow_id | 是 | Workflow ID |
| workflow_status | 是 | pending |
| context_pack_status | 是 | ready / degraded / blocked |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| initialization_not_completed | 初始化未完成，正式续写 blocked |
| context_pack_blocked | ContextPack blocked，续写 blocked |
| context_pack_degraded | ContextPack degraded 且 allow_degraded = false，blocked |
| degraded_not_allowed | allow_degraded = false 且 degraded |
| writing_task_missing | 缺少续写任务描述 |
| chapter_empty | 目标章节为空 |

**安全日志边界：** 不记录完整 writing_task 到普通日志（可记录摘要）。

### 12.2 get_continuation_result

| 项 | 值 |
|---|---|
| API 名称 | get_continuation_result |
| 调用者 | 前端轮询 |
| caller_type | user_action / workflow |
| 是否异步 | 否，同步返回当前结果 |
| 是否返回 job_id | 否（传入 job_id 或 workflow_id） |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 否 | Job ID |
| workflow_id | 否 | Workflow ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | Job ID |
| workflow_id | 是 | Workflow ID |
| workflow_status | 是 | pending / running / completed_with_candidate / degraded_completed / failed / cancelled |
| candidate_draft_id | 否 | 生成成功时返回 CandidateDraft ID |
| candidate_summary | 否 | 候选稿安全摘要（不包含完整内容） |
| word_count | 否 | 候选稿字数 |
| warnings | 否 | 警告列表 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job / Workflow ID 不存在 |
| workflow_id_mismatch | Job 与 Workflow 不匹配 |

**安全日志边界：** 不返回完整候选稿内容；前端通过 get_candidate_draft 获取完整内容。

### 12.3 quick_trial_continuation

| 项 | 值 |
|---|---|
| API 名称 | quick_trial_continuation |
| 调用者 | 前端 Quick Trial 入口 |
| caller_type | quick_trial |
| 是否异步 | 是（P0 默认异步，可选同步短路径） |
| 是否返回 job_id | 是 |
| idempotency_key | 建议 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| target_chapter_id | 是 | 目标章节 ID |
| trial_prompt | 是 | 试写提示 |
| allow_degraded | 否 | 默认 true |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | Quick Trial Job ID |
| trial_status | 是 | pending / running |
| context_insufficient | 是 | 上下文是否不足 |
| degraded_context | 是 | 上下文是否降级 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| initialization_not_completed | 初始化未完成 |
| context_pack_blocked | ContextPack blocked |
| trial_prompt_empty | 试写提示为空 |

**安全日志边界：** 不记录完整 trial_prompt 到普通日志。Quick Trial 不保存 CandidateDraft，不更新 StoryMemory / StoryState / VectorIndex。

### 12.4 save_quick_trial_as_candidate

| 项 | 值 |
|---|---|
| API 名称 | save_quick_trial_as_candidate |
| 调用者 | 前端（用户明确点击保存） |
| caller_type | user_action（必须） |
| 是否异步 | 否，同步保存 |
| 是否返回 job_id | 否 |
| idempotency_key | 必须 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| target_chapter_id | 是 | 目标章节 ID |
| trial_job_id | 是 | Quick Trial Job ID |
| idempotency_key | 是 | 防重复保存 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| candidate_draft_id | 是 | 新创建的 CandidateDraft ID |
| candidate_status | 是 | pending_review |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| trial_job_not_found | Quick Trial Job 不存在 |
| trial_output_empty | Quick Trial 输出为空 |
| quick_trial_save_requires_user_action | caller_type 不是 user_action |
| idempotency_key_missing | 缺少 idempotency_key |
| duplicate_request | 重复请求，返回已有 candidate_draft_id |
| candidate_save_failed | 保存候选稿失败 |

**安全日志边界：** 保存后 Quick Trial 输出进入 CandidateDraft 受控存储。不记录完整候选稿内容到普通日志。

---

## 十三、CandidateDraft / HumanReviewGate API

### 13.1 list_candidate_drafts

| 项 | 值 |
|---|---|
| API 名称 | list_candidate_drafts |
| 调用者 | 前端 / HumanReviewGate |
| caller_type | user_action |
| 是否异步 | 否，同步返回 |
| 是否返回 job_id | 否 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| target_chapter_id | 否 | 按章节过滤 |
| status | 否 | 按状态过滤（pending_review / accepted / rejected / applied / stale） |
| sort_by | 否 | 排序字段（默认 created_at） |
| sort_order | 否 | asc / desc（默认 desc） |
| limit | 否 | 分页大小 |
| offset | 否 | 分页偏移 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| items | 是 | CandidateDraft 摘要列表 |
| total | 是 | 总数 |
| limit | 是 | 分页大小 |
| offset | 是 | 分页偏移 |

每个 item 包含：

| 字段 | 必填 | 说明 |
|---|---|---|
| candidate_draft_id | 是 | 候选稿 ID |
| work_id | 是 | 作品 ID |
| target_chapter_id | 是 | 目标章节 ID |
| status | 是 | pending_review / accepted / rejected / applied / stale / superseded |
| source | 是 | workflow / quick_trial |
| word_count | 否 | 字数 |
| overall_severity | 否 | 关联 AIReview 的 overall_severity（如有） |
| stale_status | 否 | fresh / stale |
| warnings | 否 | 警告摘要 |
| created_at | 是 | 创建时间 |
| updated_at | 是 | 更新时间 |

**关键错误码：** 无特定错误码（只读操作）。

**安全日志边界：** list 默认返回摘要，不返回完整候选稿内容。

### 13.2 get_candidate_draft

| 项 | 值 |
|---|---|
| API 名称 | get_candidate_draft |
| 调用者 | 前端 / HumanReviewGate |
| caller_type | user_action |
| 是否异步 | 否，同步返回 |
| 是否返回 job_id | 否 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| candidate_draft_id | 是 | 候选稿 ID |
| include_content | 否 | 是否返回完整内容（默认 true） |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| candidate_draft_id | 是 | 候选稿 ID |
| work_id | 是 | 作品 ID |
| target_chapter_id | 是 | 目标章节 ID |
| status | 是 | 当前状态 |
| source | 是 | 来源 |
| content | 否 | 完整候选稿内容（include_content = true 时） |
| content_ref | 否 | 内容安全引用（include_content = false 时） |
| word_count | 否 | 字数 |
| review_result_id | 否 | 关联 AIReviewResult ID |
| review_summary | 否 | 审阅摘要（如有） |
| overall_severity | 否 | 审阅严重程度（如有） |
| stale_status | 否 | fresh / stale |
| degraded_reasons | 否 | 降级原因 |
| warnings | 否 | 警告列表 |
| chapter_version_conflict | 否 | 是否存在版本冲突 |
| created_at | 是 | 创建时间 |
| updated_at | 是 | 更新时间 |

**关键错误码：**

| error_code | 说明 |
|---|---|
| candidate_not_found | 候选稿不存在 |
| candidate_content_unavailable | 候选稿内容因清理不可用 |

**安全日志边界：** 普通日志不记录完整候选稿内容。

### 13.3 accept_candidate_draft

| 项 | 值 |
|---|---|
| API 名称 | accept_candidate_draft |
| 调用者 | HumanReviewGate（用户点击"接受"） |
| caller_type | user_action（必须，唯一） |
| 是否异步 | 否，同步完成 |
| 是否返回 job_id | 否 |
| idempotency_key | 不强制，重复 accept 幂等返回当前状态 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| candidate_draft_id | 是 | 候选稿 ID |
| user_action_context | 否 | 用户操作上下文 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| candidate_draft_id | 是 | 候选稿 ID |
| previous_status | 是 | 变更前状态 |
| current_status | 是 | accepted |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| candidate_not_found | 候选稿不存在 |
| candidate_status_invalid | 状态不允许 accept（如已 rejected / applied） |
| candidate_already_accepted | 重复 accept，幂等返回 |
| user_confirmation_required | caller_type 不是 user_action |

**安全日志边界：** CandidateDraftAuditLog 记录决策。accepted 不等于 applied，正文不变。

### 13.4 apply_candidate_to_draft

| 项 | 值 |
|---|---|
| API 名称 | apply_candidate_to_draft |
| 调用者 | HumanReviewGate（用户点击"应用"） |
| caller_type | user_action（必须，唯一） |
| 是否异步 | 否，同步执行 Local-First 保存 |
| 是否返回 job_id | 否 |
| idempotency_key | 建议强制（apply_request_id） |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| candidate_draft_id | 是 | 候选稿 ID |
| target_chapter_id | 是 | 目标章节 ID |
| apply_mode | 否 | replace / append（P0 默认 replace） |
| apply_request_id | 建议 | 防重复 apply |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| candidate_draft_id | 是 | 候选稿 ID |
| previous_status | 是 | 变更前状态 |
| current_status | 是 | applied |
| chapter_version_after | 是 | apply 后章节版本号 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| candidate_not_found | 候选稿不存在 |
| candidate_status_invalid | 状态不允许 apply |
| candidate_already_applied | 重复 apply，幂等返回 |
| chapter_version_conflict | 章节版本冲突，不自动覆盖 |
| candidate_version_mismatch | 候选稿版本不匹配 |
| apply_target_missing | 缺少目标章节 |
| apply_mode_not_supported | P0 不支持该 apply_mode |
| local_first_save_failed | V1.1 Local-First 保存失败 |
| human_review_required | 未经过 HumanReviewGate |
| user_confirmation_required | caller_type 不是 user_action |

**安全日志边界：** apply 走 V1.1 Local-First 保存链路。apply 成功后通过 Local-First 或 Application 事件通知下游 stale 标记流程。CandidateDraftAuditLog 记录 apply 决策。

### 13.5 reject_candidate_draft

| 项 | 值 |
|---|---|
| API 名称 | reject_candidate_draft |
| 调用者 | HumanReviewGate（用户点击"拒绝"） |
| caller_type | user_action（必须，唯一） |
| 是否异步 | 否，同步完成 |
| 是否返回 job_id | 否 |
| idempotency_key | 不强制，重复 reject 幂等返回当前状态 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| candidate_draft_id | 是 | 候选稿 ID |
| reject_reason | 否 | 拒绝原因 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| candidate_draft_id | 是 | 候选稿 ID |
| previous_status | 是 | 变更前状态 |
| current_status | 是 | rejected |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| candidate_not_found | 候选稿不存在 |
| candidate_status_invalid | 状态不允许 reject |
| candidate_already_rejected | 重复 reject，幂等返回 |
| user_confirmation_required | caller_type 不是 user_action |

**安全日志边界：** CandidateDraftAuditLog 记录决策。正文不变。

---

## 十四、AIReview API

### 14.1 start_review_candidate_draft

| 项 | 值 |
|---|---|
| API 名称 | start_review_candidate_draft |
| 调用者 | HumanReviewGate（用户点击"审阅候选稿"） |
| caller_type | user_action（P0 默认唯一允许） |
| 是否异步 | 是，创建轻量 AIJob 后立即返回 |
| 是否返回 job_id | 是 |
| idempotency_key | 可选 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| target_chapter_id | 是 | 目标章节 ID |
| candidate_draft_id | 是 | 候选稿 ID |
| review_scope | 否 | basic_quality / consistency / apply_risk / all_p0（默认 basic_quality + apply_risk） |
| user_instruction | 否 | 用户附加审阅指令 |
| allow_degraded | 否 | 默认 true |
| idempotency_key | 否 | 提供时用于 duplicate_review_request |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 审阅 AIJob ID |
| review_status | 是 | review_job_created / review_result_pending |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| review_target_missing | candidate_draft_id 缺失 |
| candidate_not_found | 候选稿不存在 |
| candidate_content_unavailable | 候选稿内容不可用 |
| review_context_degraded_not_allowed | allow_degraded = false 且 Context degraded |
| review_context_token_budget_exceeded | 超预算且无法安全裁剪 |
| review_permission_denied | caller_type 不允许 |
| duplicate_review_request | 重复请求，返回已有 review_result_id |
| review_idempotency_conflict | 幂等冲突 |

**安全日志边界：** 不记录完整候选稿内容到普通日志。默认 user_action 触发，workflow 默认禁止。

### 14.2 get_review_result

| 项 | 值 |
|---|---|
| API 名称 | get_review_result |
| 调用者 | 前端轮询 / HumanReviewGate |
| caller_type | user_action |
| 是否异步 | 否，同步返回 |
| 是否返回 job_id | 否 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| review_result_id | 是 | 审阅结果 ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| review_result_id | 是 | 审阅结果 ID |
| candidate_draft_id | 否 | 关联候选稿 ID |
| review_status | 是 | completed / completed_with_warnings / failed / skipped / blocked / pending |
| overall_severity | 否 | info / low / medium / high / critical |
| summary | 否 | 审阅摘要 |
| items | 否 | AIReviewItem 列表（含 category / severity / title / description / suggested_action） |
| warnings | 否 | 警告列表 |
| stale_status | 否 | fresh / stale / unknown |
| degraded_reasons | 否 | 降级原因 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| review_result_not_found | 审阅结果不存在 |
| review_result_pending | 审阅尚未完成 |
| stale_review_result | 审阅结果可能基于过期上下文 |
| review_stale_unknown | 无法判断是否 stale |

**安全日志边界：** items 中的 evidence_ref / location_ref 为安全引用，不记录完整正文片段。普通日志不记录完整 items 内容。

### 14.3 list_review_results

| 项 | 值 |
|---|---|
| API 名称 | list_review_results |
| 调用者 | 前端 / HumanReviewGate |
| caller_type | user_action |
| 是否异步 | 否，同步返回 |
| 是否返回 job_id | 否 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| candidate_draft_id | 否 | 按候选稿过滤 |
| target_chapter_id | 否 | 按章节过滤 |
| review_status | 否 | 按状态过滤 |
| sort_by | 否 | 排序字段（默认 created_at） |
| sort_order | 否 | asc / desc（默认 desc） |
| limit | 否 | 分页大小 |
| offset | 否 | 分页偏移 |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| items | 是 | AIReviewResult 摘要列表 |
| total | 是 | 总数 |
| limit | 是 | 分页大小 |
| offset | 是 | 分页偏移 |

每个 item 包含：

| 字段 | 必填 | 说明 |
|---|---|---|
| review_result_id | 是 | 审阅结果 ID |
| candidate_draft_id | 否 | 关联候选稿 ID |
| review_status | 是 | 审阅状态 |
| overall_severity | 否 | 总体严重程度 |
| summary | 否 | 审阅摘要 |
| stale_status | 否 | fresh / stale / unknown |
| created_at | 是 | 创建时间 |

**关键错误码：** 无特定错误码（只读操作）。

**安全日志边界：** list 返回摘要，不返回完整 items。

### 14.4 cancel_review_job

| 项 | 值 |
|---|---|
| API 名称 | cancel_review_job |
| 调用者 | 前端 |
| caller_type | user_action |
| 是否异步 | 否，同步返回取消确认 |
| 是否返回 job_id | 是 |
| idempotency_key | 不需要 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| job_id | 是 | 审阅 Job ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 已取消的 Job ID |
| previous_status | 是 | 取消前状态 |
| current_status | 是 | cancelled |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| job_not_found | Job ID 不存在 |
| review_job_cancelled | 已取消（幂等） |

**安全日志边界：** cancel 后迟到 AIReviewResult 不持久化为 completed，不推进 JobStep。

### 14.5 review_quick_trial_output（可选）

| 项 | 值 |
|---|---|
| API 名称 | review_quick_trial_output |
| 调用者 | 前端 Quick Trial 面板 |
| caller_type | quick_trial（可选受限） |
| 是否异步 | 是 |
| 是否返回 job_id | 是 |
| idempotency_key | 可选 |

**Request DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| work_id | 是 | 作品 ID |
| target_chapter_id | 是 | 目标章节 ID |
| trial_job_id | 是 | Quick Trial Job ID |
| request_id | 否 | 请求 ID |
| trace_id | 否 | 追踪 ID |

**Response DTO 方向：**

| 字段 | 必填 | 说明 |
|---|---|---|
| job_id | 是 | 审阅 Job ID |
| review_status | 是 | review_job_created / review_result_pending |
| context_insufficient | 是 | 上下文不足标记 |
| degraded_context | 是 | 上下文降级标记 |
| request_id | 是 | 请求 ID |
| trace_id | 是 | 追踪 ID |

**关键错误码：**

| error_code | 说明 |
|---|---|
| trial_job_not_found | Quick Trial Job 不存在 |
| trial_output_empty | Quick Trial 输出为空 |

**安全日志边界：** Quick Trial review 不保存 CandidateDraft，不自动 accept / apply。必须标记 context_insufficient / degraded_context。

### 14.6 review_chapter_draft（可选）

| 项 | 值 |
|---|---|
| API 名称 | review_chapter_draft |
| 调用者 | 前端 |
| caller_type | user_action |
| 是否异步 | 是 |
| 是否返回 job_id | 是 |
| idempotency_key | 可选 |

**说明：** P0 可选能力，非必选。若实现，只能审阅当前章节草稿的安全引用或受控内容，不得直接读取未授权正文、不得修改正文、不得触发 reanalysis / reindex、不得写 StoryMemory / StoryState / VectorIndex、不得自动生成 CandidateDraft、不得绕过 HumanReviewGate。

---

## 十五、错误码统一收敛

### 15.1 错误码总表

以下汇总 P0 API 层需要暴露的错误码。不重新定义底层错误语义，只定义 API 层如何透出 safe_message / error_code / retryable。

#### AI Infrastructure

| error_code | retryable | 说明 |
|---|---|---|
| provider_timeout | true | Provider 调用超时，按 P0-01 retry |
| provider_auth_failed | false | Provider 认证失败，不 retry |
| provider_rate_limited | true | Provider 限流，按 P0-01 retry |
| provider_unavailable | true | Provider 不可用，按 P0-01 retry |
| output_validation_failed | true | 模型输出 schema 校验失败，可重试 |
| prompt_template_missing | false | Prompt 模板缺失 |
| prompt_render_failed | false | Prompt 渲染失败 |
| provider_config_invalid | false | Provider 配置不合法 |
| model_role_invalid | false | 模型角色配置不合法 |

#### Initialization

| error_code | retryable | 说明 |
|---|---|---|
| initialization_not_completed | false | 初始化未完成，续写 blocked |
| initialization_already_running | false | 已有初始化 Job 在运行 |
| initialization_already_completed | false | 已完成且非 stale |
| initialization_in_progress | false | 初始化进行中 |
| initialization_stale | false | 初始化结果已过期 |
| initialization_not_found | false | 未找到初始化记录 |
| reanalysis_in_progress | false | 重新分析进行中 |
| chapter_empty | false | 章节为空 |
| partial_success | — | 部分成功（warning，非 error） |
| work_empty | false | 作品无内容 |

#### AIJob

| error_code | retryable | 说明 |
|---|---|---|
| job_not_found | false | Job ID 不存在 |
| job_not_cancellable | false | Job 状态不允许取消 |
| job_not_retryable | false | Job 状态不允许重试 |
| job_cancelled | false | Job 已取消 |
| job_step_not_running | false | Step 不在运行状态 |
| stale_tool_result | false | 迟到 Tool 结果被忽略 |
| retry_limit_exceeded | false | 重试次数已达上限 |
| step_not_found | false | Step ID 不存在 |
| step_not_retryable | false | Step 不可重试 |

#### ContextPack / Continuation

| error_code | retryable | 说明 |
|---|---|---|
| context_pack_blocked | false | ContextPack blocked，续写 blocked |
| context_pack_degraded | false | ContextPack degraded |
| degraded_not_allowed | false | allow_degraded = false 且 degraded |
| context_stale_during_workflow | false | 续写期间上下文 stale |
| writing_task_missing | false | 缺少续写任务描述 |
| workflow_id_mismatch | false | Job 与 Workflow 不匹配 |
| candidate_save_failed | false | 候选稿保存失败 |
| validation_failed | false | 输入校验失败 |
| trial_prompt_empty | false | 试写提示为空 |
| trial_job_not_found | false | Quick Trial Job 不存在 |
| trial_output_empty | false | Quick Trial 输出为空 |

#### CandidateDraft

| error_code | retryable | 说明 |
|---|---|---|
| candidate_not_found | false | 候选稿不存在 |
| candidate_content_empty | false | 候选稿内容为空 |
| candidate_content_unavailable | false | 候选稿内容因清理不可用 |
| candidate_validation_failed | false | 候选稿校验失败 |
| idempotency_key_missing | false | 缺少 idempotency_key |
| duplicate_request | false | 重复请求，返回已有结果 |
| idempotency_conflict | false | 幂等冲突 |
| candidate_status_invalid | false | 候选稿状态不允许当前操作 |
| candidate_already_applied | false | 已 applied |
| candidate_already_rejected | false | 已 rejected |
| candidate_already_accepted | false | 已 accepted |
| chapter_version_conflict | false | 章节版本冲突 |
| candidate_version_mismatch | false | 候选稿版本不匹配 |
| candidate_version_missing | false | 候选稿版本缺失 |
| apply_target_missing | false | 缺少 apply 目标章节 |
| apply_mode_not_supported | false | P0 不支持该 apply_mode |
| local_first_save_failed | false | Local-First 保存失败 |
| human_review_required | false | 未经过 HumanReviewGate |
| user_confirmation_required | false | caller_type 不是 user_action |
| quick_trial_save_requires_user_action | false | 保存 Quick Trial 必须 user_action |

#### AIReview

| error_code | retryable | 说明 |
|---|---|---|
| review_target_missing | false | 缺少审阅目标 |
| review_target_not_found | false | 审阅目标不存在 |
| review_target_mismatch | false | review_target_type 与输入不匹配 |
| review_context_missing | false | 缺少审阅上下文 |
| review_context_degraded | — | 上下文降级（warning） |
| review_context_degraded_not_allowed | false | allow_degraded = false 且 degraded |
| review_context_trimmed | — | 上下文已裁剪（warning） |
| review_context_token_budget_exceeded | false | 超预算且无法安全裁剪 |
| stale_review_result | — | 审阅结果可能过期（warning） |
| review_stale_unknown | — | 无法判断 stale（warning） |
| duplicate_review_request | false | 重复请求 |
| review_idempotency_conflict | false | 幂等冲突 |
| review_result_pending | — | 结果尚未完成（状态） |
| review_job_created | — | Job 已创建（状态） |
| review_result_save_failed | false | 审阅结果保存失败 |
| review_result_not_found | false | 审阅结果不存在 |
| review_permission_denied | false | 无审阅权限 |
| review_job_cancelled | false | 审阅 Job 已取消 |

### 15.2 错误响应规则

1. 不重新定义底层错误语义。
2. 只定义 API 层如何透出 safe_message / error_code / retryable。
3. retryable 必须符合 P0-01 / P0-02。
4. 不向前端暴露敏感 detail。
5. 标记为 "—" 的是 warning 或状态，不作为系统 error 返回，而是出现在 warnings 数组中或作为 status 字段值。
6. warning 不阻断用户操作。

---

## 十六、安全、隐私与日志

### 16.1 API 层日志规则

必须明确：

1. API Request / Response 不得包含 API Key 明文。
2. get_ai_settings 不得返回 API Key 明文。
3. 普通 API 日志不记录完整正文。
4. 普通 API 日志不记录完整 Prompt。
5. 普通 API 日志不记录完整 ContextPack。
6. 普通 API 日志不记录完整 CandidateDraft。
7. 普通 API 日志不记录完整 Review Prompt。
8. 普通 API 日志不记录完整 user_instruction。
9. 普通 API 日志不记录 idempotency_key 原文，可记录 hash。
10. API 日志记录 request_id / trace_id / endpoint / status / error_code / duration / safe refs。

### 16.2 审计日志继承

| 日志类型 | 依据文档 | API 层职责 |
|---|---|---|
| LLMCallLog | P0-01 | 不直接记录，由 P0-01 基础设施层记录 |
| ToolAuditLog | P0-07 | API 层确保 caller_type / request_id / trace_id 传递到 ToolExecutionContext |
| CandidateDraftAuditLog | P0-09 | API 层确保 accept / apply / reject 操作记录完整 |
| AIReviewAuditLog | P0-10 | API 层确保 caller_type / trigger_source / request_id / trace_id 传递 |

### 16.3 数据清理

- API 层不负责清理业务数据，但不得阻断下游清理策略。
- API 层不直接删除 CandidateDraft、正式正文、StoryMemory、StoryState、VectorIndex。

---

## 十七、P0 验收标准

### 17.1 通用规范验收项

| 验收项 | 预期 |
|---|---|
| 所有 AI API 返回 request_id / trace_id | 全链路可追踪 |
| request_id / trace_id 贯穿 Application / ToolFacade / AIJob / AuditLog | 贯穿 |
| 错误响应使用统一格式（error_code / safe_message / retryable / request_id / trace_id） | 格式统一 |
| 错误响应不包含完整正文 / Prompt / CandidateDraft / API Key | 安全 |
| retryable 与 P0-01 / P0-02 一致 | 正确 |

### 17.2 AI Settings 验收项

| 验收项 | 预期 |
|---|---|
| get_ai_settings 不返回 API Key 明文 | API Key 返回 mask |
| update_ai_settings 允许写入 API Key | 写入正常 |
| test_provider_connection 结果写回 last_test_status / last_test_at | 写回正确 |
| provider_auth_failed 不 retry | 一次失败即返回 |
| provider_timeout / rate_limited / unavailable 按 P0-01 retry | retry 正确 |

### 17.3 Initialization 验收项

| 验收项 | 预期 |
|---|---|
| start_initialization 创建 AIJob 后立即返回 job_id | 异步非阻塞 |
| get_initialization_status 返回完整状态和阶段进度 | 可轮询 |
| initialization_not_completed 时正式续写 blocked | blocked |
| cancel_initialization 取消正在运行的 Job | cancel 正确 |
| retry_initialization_step 仅重试指定 Step | retry 正确 |

### 17.4 Continuation 验收项

| 验收项 | 预期 |
|---|---|
| start_continuation 默认非流式 | 返回 job_id / workflow_id |
| start_continuation 返回 job_id / workflow_id / request_id / trace_id | 字段完整 |
| ContextPack blocked 时不会生成 CandidateDraft | blocked |
| ContextPack degraded 且 allow_degraded = false 时 blocked | blocked |
| get_continuation_result 轮询返回 candidate_draft_id（完成时） | 轮询可用 |
| Quick Trial 默认不保存 CandidateDraft | 不保存 |
| save_quick_trial_as_candidate 必须 user_action + idempotency_key | 权限 + 幂等正确 |

### 17.5 CandidateDraft / HumanReviewGate 验收项

| 验收项 | 预期 |
|---|---|
| list_candidate_drafts 默认按 created_at desc 排序 | 排序正确 |
| list_candidate_drafts 默认不返回完整内容 | 仅摘要 |
| get_candidate_draft 可返回完整内容或 content_ref 解析结果 | 内容可获取 |
| accept_candidate_draft 只能 user_action | workflow/system 被拒绝 |
| apply_candidate_to_draft 只能 user_action | workflow/system 被拒绝 |
| apply_candidate_to_draft 走 V1.1 Local-First 保存链路 | Local-First |
| reject_candidate_draft 只能 user_action | workflow/system 被拒绝 |
| AI / Workflow 不能伪造 user_action | 伪造被拒绝 |
| chapter_version_conflict 不自动覆盖用户正文 | 冲突提示 |
| apply 失败不得标记 applied | 状态不变 |

### 17.6 AIReview 验收项

| 验收项 | 预期 |
|---|---|
| start_review_candidate_draft 默认 user_action | 其他 caller_type 受限 |
| start_review_candidate_draft 默认创建轻量 AIJob 异步执行 | 异步 |
| start_review_candidate_draft 返回 job_id / review_result_pending | pending |
| AIReview failed 不阻断 HumanReviewGate accept / reject / apply | 不阻断 |
| get_review_result 检测 stale_review_result / review_stale_unknown warning | warning 正确 |
| list_review_results 返回摘要，不返回完整 items 内容 | 安全 |
| review_quick_trial_output 默认 caller_type = quick_trial | 权限正确 |
| review_chapter_draft 标记为 P0 可选 | 非必选 |

### 17.7 SSE / 轮询验收项

| 验收项 | 预期 |
|---|---|
| P0 不实现正文 token stream | 非流式 |
| P0 不实现 SSE token stream | 非流式 |
| SSE 如存在，只推送安全状态事件 | 白名单内事件 |
| SSE 不推送完整正文 / Prompt / ContextPack / CandidateDraft / API Key | 安全 |
| 前端通过轮询 API 获取异步结果 | 轮询可用 |

### 17.8 安全与日志验收项

| 验收项 | 预期 |
|---|---|
| 普通 API 日志不记录完整正文 | 日志安全 |
| 普通 API 日志不记录完整 Prompt | 日志安全 |
| 普通 API 日志不记录完整 CandidateDraft | 日志安全 |
| 普通 API 日志不记录 API Key | 日志安全 |
| 普通 API 日志记录 request_id / trace_id / endpoint / status / error_code / duration | 日志完整 |
| idempotency_key 不记录原文，可记录 hash | 安全 |
| API 层不得绕过 Application Service | 边界正确 |
| API 层不得直接访问 Provider SDK / ModelRouter / RepositoryPort | 边界正确 |

### 17.9 P0 范围验收项

| 验收项 | 预期 |
|---|---|
| P0-11 不定义数据库迁移 | 不覆盖 |
| P0-11 不写代码 | 不覆盖 |
| P0-11 不新增 P1 / P2 能力 | 不覆盖 |
| P0-11 不设计五 Agent Workflow | 不覆盖 |
| P0-11 不设计完整 AI Suggestion / Conflict Guard | 不覆盖 |

---

## 附录 A：API 列表总表

| 分组 | API | 方法 | caller_type | 异步 | job_id | idempotency_key |
|---|---|---|---|---|---|---|
| AI Settings | get_ai_settings | GET | user_action | 否 | 否 | 不需要 |
| AI Settings | update_ai_settings | PUT/PATCH | user_action | 否 | 否 | 不强制 |
| AI Settings | test_provider_connection | POST | user_action | 短同步 | 否 | 不需要 |
| Initialization | start_initialization | POST | user_action | 是 | 是 | 建议 |
| Initialization | get_initialization_status | GET | user_action | 否 | 否 | 不需要 |
| Initialization | cancel_initialization | POST | user_action | 否 | 否 | 不需要 |
| Initialization | retry_initialization_step | POST | user_action | 是 | 否 | 建议 |
| AIJob | get_job_status | GET | user_action | 否 | 否 | 不需要 |
| AIJob | get_job_steps | GET | user_action | 否 | 否 | 不需要 |
| AIJob | cancel_job | POST | user_action | 否 | 否 | 不需要 |
| AIJob | retry_job | POST | user_action | 是 | 是 | 建议 |
| AIJob | retry_step | POST | user_action | 是 | 否 | 建议 |
| Continuation | start_continuation | POST | user_action | 是 | 是 | 建议 |
| Continuation | get_continuation_result | GET | user_action | 否 | 否 | 不需要 |
| Continuation | quick_trial_continuation | POST | quick_trial | 是 | 是 | 建议 |
| Continuation | save_quick_trial_as_candidate | POST | user_action | 否 | 否 | 必须 |
| CandidateDraft | list_candidate_drafts | GET | user_action | 否 | 否 | 不需要 |
| CandidateDraft | get_candidate_draft | GET | user_action | 否 | 否 | 不需要 |
| CandidateDraft | accept_candidate_draft | POST | user_action | 否 | 否 | 不强制 |
| CandidateDraft | apply_candidate_to_draft | POST | user_action | 否 | 否 | 建议强制 |
| CandidateDraft | reject_candidate_draft | POST | user_action | 否 | 否 | 不强制 |
| AIReview | start_review_candidate_draft | POST | user_action | 是 | 是 | 可选 |
| AIReview | get_review_result | GET | user_action | 否 | 否 | 不需要 |
| AIReview | list_review_results | GET | user_action | 否 | 否 | 不需要 |
| AIReview | cancel_review_job | POST | user_action | 否 | 否 | 不需要 |
| AIReview | review_quick_trial_output | POST | quick_trial | 是 | 是 | 可选 |
| AIReview | review_chapter_draft | POST | user_action | 是 | 是 | 可选 |

---

## 附录 B：错误码总表

（完整错误码列表参见第十五章 15.1 节。此处不重复列出，保持文档单一信息源。）

---

## 附录 C：与 P0-01 ~ P0-10 的引用关系

| 上游模块 | P0-11 引用内容 | 边界约束 |
|---|---|---|
| P0-01 AI Infrastructure | AI Settings API（get/update/test） | API Key 不返回明文；retry 规则继承 P0-01 |
| P0-02 AIJobSystem | AIJob API（get/cancel/retry） | 状态机不重新定义；cancel/retry 行为继承 |
| P0-03 Initialization | Initialization API（start/status/cancel/retry） | initialization_not_completed → 续写 blocked |
| P0-04 StoryMemory/StoryState | 间接（通过 ContextPack） | API 层不直接读写 |
| P0-05 VectorRecall | 间接（通过 ContextPack） | API 层不直接读写 |
| P0-06 ContextPack | Continuation API（blocked/degraded 判定） | ContextPack blocked → 续写 blocked |
| P0-07 ToolFacade | caller_type 权限矩阵 | API 层不绕过 ToolFacade 调用 Tool |
| P0-08 MinimalContinuationWorkflow | Continuation / Quick Trial API | P0 默认非流式；不自动触发 AIReview |
| P0-09 CandidateDraft/HumanReviewGate | CandidateDraft / HumanReviewGate API | accept/apply/reject 只能 user_action；apply 走 Local-First |
| P0-10 AIReview | AIReview API | 默认异步 AIJob；默认 user_action 触发；Review 不阻断 Gate |
