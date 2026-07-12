# InkTrace V2.0-P2-11 API 与前端集成边界详细设计

版本：v2.5 / P2 模块级详细设计冻结版（“接着写”入口契约已同步）
状态：冻结生效
所属阶段：InkTrace V2.0 P2 集成
设计范围：P2 全部 API 路由注册、前端路由与组件集成边界、Feature Flag 体系、分期落地策略

依据文档：

- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§7、§8）
- `docs/03_design/InkTrace-V2.0-P2-01~10-*.md`
- `docs/03_design/InkTrace-V2.0-P1-11-API与前端集成边界详细设计.md`

说明：本文档收口 P2 全部 **12 组 API 路由**和前端模块的集成边界，确保与 P1 现有路由和组件体系无冲突。本文档不写代码、不修改源码。

> **端点数声明**：本文档中的端点数以各模块详细设计文档为准。路由注册和基础路径由本文档统一管理，具体端点定义见各模块设计文档（P2-01~P2-10）。本文档仅维护集成层必须感知的边界信息。

> **文件扩展名声明**：本文档示例使用 `.js` / `.vue`，实际开发以当前 InkTrace 前端工程现有扩展名为准。若工程为 TypeScript，统一使用 `.ts` / `.vue`；若为 JavaScript，保持 `.js` / `.vue`。

---

## 一、P2 分期落地策略与 Feature Flag

### 1.1 分期启用计划

P2 模块分三个阶段落地，避免一次性全接入导致前端入口空转：

| 阶段 | 模块 | 前端入口 | 说明 |
|---|---|---|---|
| **P2-S1** | Multi-Chapter (§01)、Citation Link (§02)、Style DNA (§03)、Auto Queue (§04) | WritingStudio 内嵌 + StyleDNA 配置页 | 核心续写流程 |
| **P2-S2** | Mentions (§05)、Opening Agent (§06)、Outline Assist (§07)、Selection Rewrite (§08) | WritingStudio 编辑器内嵌 + 右侧面板 Tab | 编辑器增强功能 |
| **P2-S3** | Cost Dashboard (§09)、Analysis Dashboard (§10) | 独立路由页（`/works/:workId/cost`、`/works/:workId/analysis`） | 看板类功能，不触发 LLM 调用 |

### 1.2 Feature Flag 体系

每个 P2 模块对应一个 Feature Flag，控制前端入口、路由守卫和 API 可用性：

```javascript
// frontend/src/config/p2FeatureFlags.js (或 .env / 后端配置)
const P2_FEATURE_FLAGS = {
  // P2-S1
  enable_multi_chapter:     true,   // P2-01 多章续写
  enable_citation_link:     true,   // P2-02 Citation 引用校验
  enable_style_dna:         true,   // P2-03 风格画像
  enable_auto_queue:        true,   // P2-04 自动续写队列

  // P2-S2
  enable_mentions:          false,  // P2-05 @Mention（S2 启用时改为 true）
  enable_opening_agent:     false,  // P2-06 开篇助手
  enable_outline_assist:    false,  // P2-07 大纲辅助
  enable_selection_rewrite: false,  // P2-08 选区改写

  // P2-S3
  enable_cost_dashboard:    false,  // P2-09 成本看板
  enable_analysis_dashboard:false,  // P2-10 分析看板
};
```

**使用规则**：

- `false` 的模块：前端不显示对应功能入口。后端统一注册该模块路由，但返回 `503 P2_FEATURE_DISABLED`。**P2-09 例外**：`enable_cost_dashboard` 只关闭 `/cost-dashboard/*` 和作品内看板入口；预算门控始终执行，`/cost-budget` 与 `/cost-prices` 始终保留在 SettingsCenter，避免用户无法调整已生效保护。
- 模块复用 P1 通用端点时，后端必须先按实体 `source/metadata` 判断归属：`enable_outline_assist=false` 时，P2-07 来源的 `/suggestions/{id}/accept|dismiss|convert` 与 `/writing-tasks/{id}/confirm` 同样返回 503；P1 来源实体继续正常工作，禁止粗暴关闭全部通用端点。
- `true` 的模块：前端正常显示入口，后端 API 正常响应。
- Flag 来源：开发阶段用配置文件/环境变量；生产环境可从后端 API `/api/v2/ai/feature-flags` 动态获取。
- 成本看板和分析看板即使 `enable_* = true`，也不强制要求 Provider 已配置（见 §2.1 路由守卫）。

---

## 二、P2 全部 API 路由汇总

### 2.1 路由注册

所有 P2 API 注册在 `presentation/api/routers/v2/` 下，在 `presentation/api/app.py` 中追加：

```python
from presentation.api.routers.v2.ai import (
    multi_chapter,      # P2-01
    citations,          # P2-02
    style_dna,          # P2-03
    auto_queues,        # P2-04
    mentions,           # P2-05
    opening,            # P2-06
    outline_assist,     # P2-07
    selection_rewrite,  # P2-08
    cost_dashboard,     # P2-09 查询（CostDashboardQueryService）
    cost_budget,        # P2-09 预算配置（CostBudgetService）
    cost_prices,        # P2-09 费用估算设置（CostPricePolicyService）
    analysis_dashboard, # P2-10
)

# AI 功能域模块（P2-01~04, P2-06~10）
app.include_router(multi_chapter.router, prefix="/api/v2/ai")
app.include_router(citations.router, prefix="/api/v2/ai")
app.include_router(style_dna.router, prefix="/api/v2/ai")
app.include_router(auto_queues.router, prefix="/api/v2/ai")
app.include_router(opening.router, prefix="/api/v2/ai")
app.include_router(outline_assist.router, prefix="/api/v2/ai")
app.include_router(selection_rewrite.router, prefix="/api/v2/ai")
app.include_router(cost_dashboard.router, prefix="/api/v2/ai")
app.include_router(cost_budget.router, prefix="/api/v2/ai")       # P2-09 v1.3 受控预算写
app.include_router(cost_prices.router, prefix="/api/v2/ai")       # P2-09 v1.3 受控价格写
app.include_router(analysis_dashboard.router, prefix="/api/v2/ai")

# P2-05 Mentions 路由前缀为 /api/v2（非 /api/v2/ai）
# 原因：@-Mention 是编辑器实体引用功能（角色/资产/章节的 @-提及、suggest、highlight、tooltip），
# 主要服务于编辑器交互，不直接触发 LLM 调用。AI 产生的 mention 建议通过 AISuggestion 流程
# 进入，Mention API 只负责用户采纳后的持久化与查询。因此不挂载在 /ai 子路径下。
app.include_router(mentions.router, prefix="/api/v2")
```

### 2.2 全部端点索引

| # | 分组 | 基础路径 | 阶段 | Feature Flag |
|---|---|---|---|---|
| 1 | Multi-Chapter | `/api/v2/ai/multi-chapter` | P2-S1 | `enable_multi_chapter` |
| 2 | Citations | `/api/v2/ai/citations` | P2-S1 | `enable_citation_link` |
| 3 | Style DNA | `/api/v2/ai/style-dna` | P2-S1 | `enable_style_dna` |
| 4 | Auto Queues | `/api/v2/ai/auto-queues` | P2-S1 | `enable_auto_queue` |
| 5 | Mentions | `/api/v2/mentions` + `/api/v2/chapters/{id}/mentions` | P2-S2 | `enable_mentions` |
| 6 | Opening | `/api/v2/ai/opening` | P2-S2 | `enable_opening_agent` |
| 7 | Outline Assist | `/api/v2/ai/outline-assist` | P2-S2 | `enable_outline_assist` |
| 8 | Selection Rewrite | `/api/v2/ai/selection-rewrite` | P2-S2 | `enable_selection_rewrite` |
| 9 | Cost Dashboard | `/api/v2/ai/cost-dashboard` | P2-S3 | `enable_cost_dashboard` |
| 10 | Cost Budget | `/api/v2/ai/cost-budget` | P2-S3 | 不受看板 Flag 影响 |
| 11 | Cost Prices | `/api/v2/ai/cost-prices` | P2-S3 | 不受看板 Flag 影响 |
| 12 | Analysis Dashboard | `/api/v2/ai/analysis-dashboard` | P2-S3 | `enable_analysis_dashboard` |

> **端点数**不在此表中硬写——以各模块详细设计文档为准。P2-09（Cost Dashboard + Cost Budget + Cost Prices）和 P2-10（Analysis Dashboard）已拆分路由，具体端点定义见 P2-09 v1.3 和 P2-10 v1.2。

### 2.3 通用规范

- 所有端点沿用 P0-11 定义的 `{ request_id, trace_id, status, data, error, polling_hint }` 格式。
- **caller_type=user_action 必检端点**（需要 Presentation 层校验调用方为用户真实操作，拒绝 agent/system 调用）：

| 端点 | 动作 | 原因 |
|---|---|---|
| `POST /multi-chapter/{id}/advance` | 推进多章续写 | 用户确认当前章后推进 |
| `POST /style-dna/{id}/confirm` | 确认风格画像 | 用户确认后才能生效 |
| `POST /style-dna/{id}/disable` | 禁用风格画像 | 用户操作 |
| `POST /auto-queues/{id}/confirm-continue` | 安全模式继续 | 用户逐章确认（不可被 Agent 自动推进） |
| `POST /auto-queues/start` | 启动“接着写” | 真实用户授权长任务；必须完整 UserActionContext、幂等键和 expected_config_revision；可带 0..60 字 `user_instruction` |
| `POST /auto-queues/{id}/pause` | 暂停自动续写 | 用户操作；Application 也复核 UserActionContext |
| `POST /auto-queues/{id}/resume` | 恢复暂停/可恢复停止 | 用户操作；必须带 expected_config_revision，不得与 system recovery 共用方法 |
| `POST /auto-queues/{id}/cancel` | 放弃这次自动续写 | 用户操作；转 CANCELLED 且不删除候选稿/成本事实 |
| `POST /opening/directions/{direction_id}:confirm` | 确认开篇方向 | P2-06 direction confirm |
| `POST /opening/draft-batches/{batch_id}:stop` | 停止开篇候选稿生成 | 用户主动停止，保留已完成候选稿 |
| `POST /outline-assist/suggestions/{suggestion_id}/apply` | 将大纲建议放进正式大纲 | 必须同时校验 `caller_type=user_action`、`user_action=true`、非空 `idempotency_key`、`confirm_apply=true` |
| `POST /selection-rewrite/*/apply` | 应用选区改写 | 用户确认改写结果 |
| `POST /auto-queues/{id}/stop` | 手动停止队列 | 用户操作 |
| `PUT /cost-budget` | 新建、调整、启用或关闭预算保护 | 必须校验真实 user_action、user_id、幂等键、确认字段并先写审计；关闭保护额外二次确认 |
| `PUT /cost-prices` | 新建、调整或停用手动价格 | 必须校验真实 user_action、user_id、幂等键、价格确认字段并先写审计 |
| `PUT /auto-queues/config`（请求包含预算字段时） | 修改同一 auto_queue 预算事实 | 与 `/cost-budget` 使用完全相同的用户门、幂等和审计要求，禁止旧入口旁路 |

> **注**：开篇助手不新增独立的正式正文 apply 端点。CandidateDraft apply 仍走 P0/P1 标准 HumanReviewGate。方向确认、停止生成和候选稿 apply 都必须由真实 user_action 触发。
**原则**：凡是会导致正式数据变更（apply/confirm/accept）或推进工作流越过用户确认门（advance/confirm-continue）的端点，必须校验 `caller_type=user_action`。

- API 层不承载业务逻辑，不直接访问 Provider/Repository/ModelRouter。

### 2.4 Opening Agent v2.0 冻结 API

开篇助手使用分段短用例，不以一个长生命周期 Job 跨越用户确认：

```text
POST /api/v2/ai/opening/briefs
POST /api/v2/ai/opening/briefs/{brief_id}/references
POST /api/v2/ai/opening/briefs/{brief_id}/directions:generate
GET  /api/v2/ai/opening/direction-batches/{batch_id}
POST /api/v2/ai/opening/directions/{direction_id}:confirm
POST /api/v2/ai/opening/directions/{direction_id}:revise
POST /api/v2/ai/opening/directions/{direction_id}/drafts:generate
GET  /api/v2/ai/opening/draft-batches/{batch_id}
POST /api/v2/ai/opening/draft-batches/{batch_id}:stop
GET  /api/v2/ai/opening/works/{work_id}/latest
```

冻结规则：

- `briefs` 不要求参考文本；无参考是正式主路径。
- 完整参考文本只进入 `TemporarySensitiveTextStore`，不得进入 AIJob.context、API response、Trace 或日志。
- `directions:generate` 返回短任务引用；方向批次查询返回三个方向及状态。
- `direction:confirm` 必须携带 `caller_type=user_action`、`user_action=true`、`user_id`、`idempotency_key`。
- `drafts:generate` 后端校验 direction 已确认且策略相似风险未阻断。
- `draft-batches` 返回逐章状态和有效 CandidateDraft 引用；`partial_success` 必须至少包含一个 result_ref。
- `draft-batches:stop` 必须为 user_action，且保留已完成 CandidateDraft。
- 稿件原创性 high 时，现有 CandidateDraft apply 用例返回 blocked，并提供安全中文提示。

Opening v1.x 的 `/import-reference`、`/analyze`、`/strategies/*`、`/generate` 与按 work 查询长 Job 状态方案废止，不得新增兼容旁路。

### 2.5 Outline Assist v2.0 冻结 API

P2-07 自有端点固定为 5 个 POST：

```text
POST /api/v2/ai/outline-assist/polish
POST /api/v2/ai/outline-assist/expand
POST /api/v2/ai/outline-assist/chapter-outline
POST /api/v2/ai/outline-assist/writing-task
POST /api/v2/ai/outline-assist/suggestions/{suggestion_id}/apply
```

冻结规则：

- 四个生成端点统一先创建 `AISuggestion(status=pending)` 并返回 `suggestion_id`/`job_id`；成功为 `generated`，失败为 `failed`，禁止使用 `generating/completed`。
- 查询与用户决策复用 P1 `/api/v2/ai/suggestions/*`，不重复新增查询、accept、dismiss、convert 端点。
- 正式目标只允许 `work_outline`（`target_id=work_id`）或 `chapter_outline`（`target_id=chapter_id`）；`selection` 不允许直接 apply。
- `chapter-outline` 必须明确携带 `target_kind=chapter_outline`、`target_id=chapter_id` 与 `target_revision=ChapterOutline.version`。
- 普通大纲建议先 accept（界面“先留着”），再 apply（“放进大纲”）。apply 成功后使用 P1 `converted` + `action_status=completed`，不新增 applied。
- 写作要点建议无需先 accept；用户点击“设为本章写作计划”后，复用 P1 convert 创建 `WritingTask(pending)`，再由现有 WritingTask confirm 变为 `ready`。禁止新增 `pending_confirm`。
- apply 请求必须携带 `caller_type=user_action`、`user_action=true`、`user_id`、非空 `idempotency_key`、`confirm_apply=true` 和 `target_revision`。`target_revision` 在应用层映射为 WritingAssetService 的 `expected_version`。
- `confirm_apply=true` 表示 UI 已展示当前大纲与 AI 建议的前后对比，并取得用户“放进大纲”的明确确认；后端仍须独立执行门控。
- 生成时服务端读取真实 WorkOutline/ChapterOutline，并把 `target_revision` 与完整内容的 `target_content_hash` 存入 `AISuggestion.payload`；用户可编辑的 `selected_text` 只供 AI 参考，不是正式资产基线。
- apply 同一用例内同时比对当前 version 与 content hash，再执行 ConflictGuard 审计；保存时把生成基线映射为 `expected_version` 与仅供 P2 内部使用的可选 `expected_content_hash`，由 WritingAssetService 在同一互斥临界区内再次复核。普通成功路径的保护记录在用户确认后 acknowledged、保存成功后 resolved，不要求额外前端冲突参数或第二次请求。版本/哈希或其他真实 blocking 冲突保存 blocking record、当次返回 409 且不写入；用户处理后刷新目标并重新生成建议，不得恢复旧 HTTP 请求或强制覆盖。

### 2.6 AI 用量与预算 v1.3 冻结 API

```text
GET /api/v2/ai/cost-dashboard/summary
GET /api/v2/ai/cost-dashboard/trend
GET /api/v2/ai/cost-dashboard/details
GET /api/v2/ai/cost-dashboard/task-cost
GET /api/v2/ai/cost-budget
PUT /api/v2/ai/cost-budget
GET /api/v2/ai/cost-budget/check
POST /api/v2/ai/cost-budget/reconcile-usage
GET /api/v2/ai/cost-prices
PUT /api/v2/ai/cost-prices
```

冻结规则：

- 四个 cost-dashboard 端点纯只读，不调用 Provider/ModelRouter，不要求当前 Provider 或 API Key 可用。
- summary/trend 使用 `costs_by_currency`、已知/未知用量计数、已知/未知费用计数、`usage_completeness/cost_completeness/history_completeness`；逐条费用读取权威 `cost_currency`，Provider 实际账单币种不得被调用前报价币种覆盖；未知不得返回 0 或用当前单价回算。
- details 支持 month，并允许 job/session/run 零个或一个；task-cost 必须恰好一个。目标不存在或不属于 work_id 均返回 `404 P2_COST_SCOPE_NOT_FOUND`。
- 明细可返回逐条 `user_adopted/adoption_state`，但 P2-09 不返回 adoption_rate。
- `/cost-budget` 不提供 DELETE；关闭保护使用 PUT `enabled=false + confirm_disable=true`，保留恢复和审计能力。
- 预算 PUT 必须携带 `caller_type=user_action`、`user_action=true`、`user_id`、`Idempotency-Key`、`confirm_budget_change=true` 和更新时的并发基线；创建作品级覆盖还要携带继承基线。同 key 不同请求返回 409。
- 价格 PUT 采用同一用户门、UoW、幂等回执和 AgentTrace 审计，额外要求 `confirm_price_change=true + confirm_manual_price_source=true`；金额/单价均为 Decimal 字符串，不使用 float。
- 启用月度预算或修改价格时，服务端通过版本化 WorkModelInventory 校验作品当前 primary/retry/fallback 精确路由；global 改价校验全部继承作品。模型路由 revision 变化返回并发冲突，整次写回滚，不允许部分作品生效。
- 预算调整成功后不自动恢复暂停/停止的 Job、Session 或 AutoQueueRun。
- `auto_queue` 预算写回 P2-04 AutoQueueConfig，同一上限不得再写入 cost_budgets。
- 作品预算/手动价格通过 PUT `inherit_global=true` 恢复默认，不提供 DELETE；创建覆盖或恢复继承都携带对应 global id + updated_at 基线。
- `/cost-budget/check` 只返回当前事实，不接受客户端 `projected_tokens/projected_cost`。真实模型调用由服务端 `TokenEstimatorPort + LLMRequest.max_tokens` 计算投影。
- `reconcile-usage` 只凭确定持久化证据补写缺口，无法确定时保持 unknown 并返回可选出口；修复成功也不自动恢复任务。
- `enable_cost_dashboard=false` 只让四个看板查询返回 503；预算/价格 API 继续可用，已启用预算继续门控。
- 手动价格只影响之后的新调用，设置入口固定为 `/settings?section=ai-cost`；历史费用不回算。

### 2.7 统一预算模型调用边界

初始化/分析、P0 续写与审稿、作品内 Quick Trial、AgentRuntime 全部 Agent、Multi-Chapter/AutoQueue 下游、Opening、OutlineAssist、SelectionRewrite、StyleDNA 的生产调用都必须经过 `GuardedLLMExecutor`，并由服务端贯穿 `LLMCallScope(work_id, job_id, session_id?, step_id?, run_id?, adoption_target_ref?)`。依赖不得标为 optional。

业务 LLMRequest 仍只指定 model_role。P0 Core 在 `application/ports/ai/provider_attempt_guard_port.py` 定义通用 `ResolvedModelAttempt/AttemptGuardDecision/ProviderAttemptGuardPort`；ModelRouter 只依赖这些 Core 契约，不 import P2 BudgetGateResult。P2 的预算 Guard 实现该 Port。Router 对首选、retry、fallback 每次解析精确 provider/model 后调用必需 guard：先按该精确模型价格门控，再调用 Provider，SQLite 日志成功后做调用后门控。fallback 不得复用首选价格/准入。`LLMResponse.billing` 只有 Provider 明确返回本次费用时才填；此时 amount/currency 原样成为权威费用事实。

`GuardedLLMExecutor` 必须把 `response + call_log_ref + after_gate + further_provider_calls_allowed` 一并交给上层。调用后超限/无法核算时不得发 retry/fallback、Reviewer、修订或下一章调用，但已落权威日志且通过本地校验的本次结果仍可保存为 CandidateDraft/result_ref。调用前超限返回 409；调用后超限不得把已经完成的 attempt 伪装成 HTTP 失败，`partial_success` 只有在携带非空 result_ref 时才允许使用。

Provider 连接测试是唯一排除项：它不产生作品结果，也不计入作品预算/看板。Provider 请求已返回但 LLMCallLog 权威事实未落 SQLite 时，统一返回 `P2_LLM_USAGE_AUDIT_FAILED`，不得生成 CandidateDraft 或把 Job/Session 标 completed。

---

## 三、P2 前端路由与组件集成

### 3.1 新增前端路由

```javascript
// frontend/src/router/index.js (或 .ts，以项目实际扩展名为准)
{
  path: '/works/:workId/cost',
  name: 'CostDashboard',
  component: () => import('@/views/CostDashboard.vue'),
  meta: { requiresAIWorkspace: true, requiresProviderConfigured: false }
  // 成本看板只读聚合 llm_call_logs，不发起 LLM 调用 → 不要求 Provider 已配置
},
{
  path: '/works/:workId/analysis',
  name: 'AnalysisDashboard',
  component: () => import('@/views/AnalysisDashboard.vue'),
  meta: { requiresAIWorkspace: true, requiresProviderConfigured: false }
  // 分析看板本地统计，不发起 LLM 调用 → 不要求 Provider 已配置
}
```

**路由守卫 meta 说明**：

| meta key | 含义 | 适用页面 |
|---|---|---|
| `requiresAIWorkspace: true` | 需要 AI 功能域已启用（AI Settings 基础配置存在） | CostDashboard、AnalysisDashboard、所有 P2 页面 |
| `requiresProviderConfigured: true` | 需要至少一个 Provider 已配置 API Key 且可用 | WritingStudio 内发起 AI 调用的按钮/Tab（如 Multi-Chapter、Style DNA、Auto Queue） |

**守卫逻辑**（位于 `router/index.js` 的 `beforeEach`）：

1. `requiresAIWorkspace` → 检查 AI Settings 基础配置 → 未配置则跳转 `/settings/ai`。
2. `requiresProviderConfigured` → 检查 Provider 可用性 → 不可用则跳转 `/settings/ai` 并提示"请先配置 AI 模型"。
3. 成本看板和分析看板只检查 `requiresAIWorkspace`，不检查 `requiresProviderConfigured`。即使 AI 模型未配置，用户仍可查看历史成本和分析数据。
4. 预算与费用估算不新增独立页面：复用 SettingsCenter `/settings?section=ai-cost`。该 section 不受 `enable_cost_dashboard` 控制；否则既有预算可能生效却无法调整。

### 3.2 WritingStudio 内集成点

```
WritingStudio.vue
├── 顶部工具栏
│   └── [多章续写] 按钮                → MultiChapterPanel 弹窗
├── 中间编辑区 (PureTextEditor)
│   ├── MentionDetector                 → P2-05 内联 (composable)
│   ├── MentionPopup                    → P2-05 浮动 (组件)
│   └── SelectionToolbar                → P2-08 浮动 + DraftSnapshot 采集
├── 右侧面板 (RightWorkspacePanel)
│   ├── [候选稿] tab (已有)
│   │   └── Citation 引用浮层          → P2-02 内联
│   ├── [接着写] 子视图 (新增)         → AutoQueuePanel
│   ├── [大纲辅助] tab (新增)          → OutlineAssistPanel
│   └── [开篇助手] 入口 (新增)         → OpeningAgentWizard
└── 状态栏 (StatusBar)
    └── 多章进度指示器                  → P2-01 内联
```

### 3.3 新增 Store

```javascript
// frontend/src/stores/ (以项目实际扩展名 .js 或 .ts 为准)
useMultiChapterStore.js        // P2-01 多章续写进度
useCitationStore.js            // P2-02 Citation 校验状态
useAutoQueueStore.js           // P2-04 自动队列状态
useMentionStore.js             // P2-05 @Mention 状态
useStyleDNAStore.js            // P2-03 Style DNA 配置
useOpeningStore.js             // P2-06 Opening Agent 状态
useOutlineAssistStore.js       // P2-07 大纲辅助状态
useSelectionRewriteStore.js    // P2-08 选区改写状态
useCostDashboardStore.js       // P2-09 成本看板查询数据
useCostBudgetStore.js          // P2-09 预算配置编辑状态
useAICostSettingsStore.js      // P2-09 手动价格与费用估算设置
useAnalysisDashboardStore.js   // P2-10 分析看板数据
```

`AutoQueuePanel`、`useAutoQueueStore`、`/auto-queues` 保持内部技术命名，用户可见入口只显示“接着写”。`POST /auto-queues/start` 的 `user_instruction` 仅承载作者最终输入，不承载快捷选项枚举；完整文本不得进入日志、Trace、审计回执或可持久化的通用任务载荷。前端必须在 60 字处提供计数与输入限制，后端独立执行同一上限校验。

> P2-09 拆分为 `useCostDashboardStore`（只读聚合）、`useCostBudgetStore`（预算表单）和 `useAICostSettingsStore`（手动价格），避免写设置逻辑与看板查询耦合。

### 3.4 P2-05 Mentions 前端组件命名统一

P2-05 前端组件统一使用 `Mention*` 命名（不带 `At` 前缀）：

| 组件/模块 | 文件 | 说明 |
|---|---|---|
| MentionDetector | `frontend/src/composables/useMentionDetector.js` | 输入监听 composable |
| MentionPopup | `frontend/src/components/workspace/MentionPopup.vue` | 建议列表弹出面板 |
| MentionHighlight | `frontend/src/components/workspace/MentionHighlight.vue` | 已插入 Mention 高亮渲染 |
| MentionTooltip | `frontend/src/components/workspace/MentionTooltip.vue` | Hover 信息浮层 |
| useMentionStore | `frontend/src/stores/useMentionStore.js` | Mention 状态管理 |

---

## 四、与 P1 现有体系的兼容性

### 4.1 P1 组件的扩展策略

| 组件 | 扩展策略 |
|---|---|
| `AIPanel.vue` | 优先通过 props/slots/composable 扩展。若 P1 组件缺少必要扩展点，**只允许添加非破坏性扩展点**（如新增 named slot），**不改变既有行为** |
| `PureTextEditor.vue` | P2 通过 composable hook 注入 Mention 能力，不改编辑器核心逻辑 |
| `ChapterTitleInput.vue` | 不动 |
| `StatusBar.vue` | 仅追加 P2 进度指示器，不改已有逻辑 |

### 4.2 P2-08 DraftSnapshot 集成边界（冻结）

P2-08 `Selection Rewrite` 在集成层新增如下冻结边界：

1. 当前草稿权威源仍为前端 Workbench Local-First 状态。
2. 后端 `selection_rewrite` 路由**不直接读取服务端草稿正文**。
3. `useSelectionRewriteStore` 在 create/apply 时负责上传 `DraftSnapshot` 元信息。

`DraftSnapshot` 最小字段：

| 字段 | 来源 | 说明 |
|---|---|---|
| `draft_revision` | `useSelectionRewriteStore` / `WritingStudio` | 当前草稿 revision |
| `draft_text_hash` | 前端对当前整章草稿计算 SHA-256 | 用于整章快照冲突校验 |
| `draft_length` | 当前整章草稿长度 | 用于位置范围校验 |
| `range_text` | apply 时由前端当前选区区间文本计算 | 用于区间文本匹配校验 |

约束：

1. 前端不得上传完整草稿正文到 `selection_rewrite` API。
2. 后端不得新增服务端 draft 正文持久化作为 P2-08 初期实现前提。
3. `apply` 仍只返回 patch，由前端 Workbench Store 替换当前草稿并进入既有保存链路。

### 4.3 P1 API 不受影响

- P1 的 `/api/v2/ai/sessions`、`/api/v2/ai/continuation`、`/api/v2/ai/suggestions` 等全部保留。
- P2 新增路由使用不同前缀子路径，不与 P1 冲突。

---

## 五、SSE / 轮询策略

### 5.1 轮询端点完整列表

P2 默认继续使用**轮询**（与 P1 一致）。

| 端点 | 所属模块 | 轮询场景 | 间隔建议 |
|---|---|---|---|
| `/multi-chapter/{id}/progress` | P2-01 | 多章续写进度 | 1.5-2s（短）/ 3-5s（长生成） |
| `/auto-queues/{id}/status` | P2-04 | 自动队列状态（安全模式等待） | 2-3s（运行中）/ 5s（等待用户） |
| `/opening/direction-batches/{batch_id}` | P2-06 | 开篇方向生成 | 1.5-2s |
| `/opening/draft-batches/{batch_id}` | P2-06 | 分章候选稿生成 | 1.5-2s |
| `/style-dna/{id}` | P2-03 | 风格画像提取状态 | 3-5s（提取中） |
| `/api/v2/ai/suggestions/{suggestion_id}` | P2-07 | 大纲辅助建议生成状态 | 2-3s |
| `/selection-rewrite/{rewrite_id}` | P2-08 | 选区改写候选生成状态 | 2-3s |
| `/analysis-dashboard/recompute/status` | P2-10 | 大作品重算进度 | 5s |

### 5.2 策略说明

- **同步返回**的端点（如大部分 GET 查询、PUT 配置）不涉及轮询。
- **Style DNA `extract`**：`StyleDNAExtractionService.extract()` 通过必需的 `GuardedLLMExecutor` 间接使用 ModelRouter。P2 默认同步返回（阻塞等待 LLM 响应），超时由 HTTP 层处理（默认 60s）。若未来改为异步，则另行冻结轮询端点，不在本阶段预增。
- **Selection Rewrite**（P2-08 v1.2）：异步模式，后台执行，不阻塞 HTTP。前端轮询 `GET /selection-rewrite/{rewrite_id}`。
- **Outline Assist**（P2-07）：四个生成操作均为异步，前端轮询 `GET /api/v2/ai/suggestions/{suggestion_id}`（复用 P1 AI Suggestion 轮询机制）。`pending` 继续轮询；`generated`、`shown` 或 `failed` 停止生成轮询。
- SSE 作为可选增强（P2 不默认依赖）。
- 轮询终态停止：按资源自己的状态机判断。通用长任务进入 completed / failed / cancelled / stopped 后停止；P2-07 AISuggestion 按上一条的 generated / shown / failed 停止，禁止等待不存在的 completed。

---

## 六、错误码统一

### 6.1 错误码映射原则

- 所有 P2 新增错误码前缀 `P2_`。
- 所有错误响应沿用 P0-11 格式：`{ error: { code, message, safe_message, data? } }`。
- HTTP 状态码映射：调用前拒绝新 Provider 请求时，`P2_BUDGET_EXCEEDED` 固定为 `409`；调用后才确定超限时不返回该错误，而在成功/带 result_ref 的 partial_success 或后台状态数据中报告预算状态。`P2_CALLER_FORBIDDEN` → `403`；`P2_*_CONFLICT` → `409`；其余业务错误 → `400`、`422` 或可重试的 `503`。裸 `budget_exceeded` 只用于内部 stop/status reason，不得作为公开错误码。
- 各模块的具体错误码以模块详细设计为准；本文档只列跨模块通用错误码和映射原则。

### 6.2 跨模块通用错误码

| 错误码 | HTTP | 说明 | 来源模块 |
|---|---|---|---|
| `P2_CALLER_FORBIDDEN` | 403 | caller_type 校验失败（agent/system 调用 user_action 专属端点） | 全部 |
| `P2_USER_ACTION_REQUIRED` | 403 | user_action 不是 true | P2-07/P2-09 |
| `P2_IDEMPOTENCY_KEY_REQUIRED` | 400 | 缺少非空幂等键 | P2-07/P2-09 |
| `P2_IDEMPOTENCY_CONFLICT` | 409 | 同一幂等键对应不同请求 | P2-07/P2-09 |
| `P2_FEATURE_DISABLED` | 503 | 该功能在当前版本未启用（Feature Flag = false） | 全部 |
| `P2_BUDGET_EXCEEDED` | 409 | 调用前确定新 attempt 会超过用户设置的预算上限 | P2-09 |
| `P2_BUDGET_USAGE_UNKNOWN` | 409 | 预算用量无法可靠核算，保护性阻止/暂停 | P2-09 |
| `P2_BUDGET_PRICE_UNKNOWN` | 409 | 启用金额预算但当前价格无法解析 | P2-09 |
| `P2_BUDGET_CURRENCY_MISMATCH` | 409 | 调用价格币种与金额预算不一致 | P2-09 |
| `P2_BUDGET_CHECK_FAILED` | 503 | 预算查询失败，可重试 | P2-09 |
| `P2_BUDGET_NOT_FOUND` | 404 | 预算不存在或不属于作品 | P2-09 |
| `P2_BUDGET_VALIDATION_FAILED` | 422 | 预算上限、币种或阈值非法 | P2-09 |
| `P2_BUDGET_CHANGE_CONFIRMATION_REQUIRED` | 400 | 缺少预算保存确认或关闭保护二次确认 | P2-09 |
| `P2_BUDGET_CONFLICT` | 409 | 预算更新基线已经变化 | P2-09 |
| `P2_BUDGET_AUDIT_WRITE_FAILED` | 503 | 写前审计失败，预算未改变 | P2-09 |
| `P2_PRICE_VALIDATION_FAILED` | 422 | 手动价格、币种或精确模型键非法 | P2-09 |
| `P2_PRICE_CONFLICT` | 409 | 手动价格更新基线已经变化 | P2-09 |
| `P2_PRICE_REQUIRED_FOR_ACTIVE_BUDGET` | 422 | 变更会使启用中的月度保护无法判断 | P2-09 |
| `P2_PRICE_SOURCE_CONFIRMATION_REQUIRED` | 400 | 手填价格前未确认已按官方来源核对 | P2-09 |
| `P2_COST_SCOPE_REQUIRED` | 400 | 缺少 job/session/run 范围 | P2-09 |
| `P2_COST_SCOPE_CONFLICT` | 422 | 同时提供多个任务范围 | P2-09 |
| `P2_COST_SCOPE_NOT_FOUND` | 404 | 范围不存在或不属于作品 | P2-09 |
| `P2_COST_RANGE_INVALID` | 422 | 成本查询时间范围非法 | P2-09 |
| `P2_COST_QUERY_FAILED` | 503 | 成本只读查询失败，可重试 | P2-09 |
| `P2_LLM_USAGE_AUDIT_FAILED` | 503 | Provider 结果的用量事实未能安全落库 | P2-09（所有生产调用） |
| `P2_USAGE_RECONCILE_FAILED` | 503 | 用量缺口修复服务失败，原暂停状态保持 | P2-09 |
| `P2_CITATION_UNVERIFIED` | 400 | Citation 未通过校验 | P2-02 |
| `P2_CITATION_SOURCE_HASH_MISMATCH` | 400 | Citation 源文本哈希与当前正文不一致 | P2-02 |
| `P2_STYLE_LOW_CONFIDENCE` | 200† | 风格画像低置信度（非错误，warning 级） | P2-03 |
| `P2_STYLE_NO_ACTIVE_PROFILE` | 200† | 无活跃 StyleProfile（降级展示） | P2-10 |
| `P2_COPYRIGHT_NOT_CONFIRMED` | 400 | 版权未确认 | P2-06 |
| `P2_OPENING_STRATEGY_SIMILARITY_BLOCKED` | 409 | 开篇方向与参考作品关键安排过于相似，需先修改方向 | P2-06 |
| `P2_OPENING_DRAFT_ORIGINALITY_REVIEW_REQUIRED` | 409 | 候选稿原创性风险未处理，暂不可 apply | P2-06 |
| `P2_STRATEGY_NOT_CONFIRMED` | 400 | 开篇策略未确认 | P2-06 |
| `P2_RIGHTS_NOT_CONFIRMED` | 400 | 权利声明未确认 | P2-06 |
| `P2_SELECTION_EMPTY` | 400 | 选区为空 | P2-08 |
| `P2_DRAFT_SNAPSHOT_INVALID` | 400 | 前端未提供有效 DraftSnapshot 元信息 | P2-08 |
| `P2_SELECTION_CONFLICT` | 409 | 选区与其他版本冲突 | P2-08 |
| `P2_SELECTION_TEXT_MISMATCH` | 409 | 选区基准文本与当前正文不匹配 | P2-08 |
| `P2_OUTLINE_TARGET_REQUIRED` | 400 | 缺少明确的大纲目标或目标版本 | P2-07 |
| `P2_OUTLINE_TARGET_CONFLICT` | 409 | 作品/章节大纲版本或完整内容哈希已变化，禁止覆盖 | P2-07 |
| `P2_OUTLINE_APPLY_CONFIRMATION_REQUIRED` | 400 | 未获得用户“放进大纲”的明确确认 | P2-07 |
| `P2_OUTLINE_CONFLICT_REVIEW_REQUIRED` | 409 | blocking 冲突需人工处理后重新 apply | P2-07 |
| `P2_OUTLINE_CONFLICT_CHECK_FAILED` | 503 | apply 前冲突检测失败，fail-safe 阻止写入 | P2-07 |
| `P2_OUTLINE_AUDIT_WRITE_FAILED` | 503 | 必需 LLMCallLog/AgentTrace 写入失败，生成不得 completed，convert/confirm 不推进 | P2-07 |
| `P2_WRITING_TASK_PREREQUISITE_MISSING` | 409 | 缺少已确认方向/章节计划，不能创建 WritingTask | P2-07 |
| `P2_MULTI_CHAPTER_BLOCKED` | 409 | 某章审稿 blocking | P2-01 |
| `P2_AUTO_QUEUE_CONFIG_CONFLICT` | 409 | 启动门控后队列配置 revision 已变化；未创建运行对象 | P2-04 |
| `P2_ANALYSIS_STALE` | 200† | 分析数据已过期（warning 级，非错误） | P2-10 |

> † 标记为 `200` 的错误码表示该状态不是 HTTP 层面的错误，而是业务 warning——响应 `status: "success"`，`error` 字段为空，warning 信息放在 `data.warning` 或 `data.note` 中。

### 6.3 AutoQueue STOPPED 状态响应

`STOPPED` 是可由用户处理原因后恢复的业务状态，不是错误码，也不是不可逆终态。`GET /api/v2/ai/auto-queues/{run_id}/status` 固定返回 HTTP 200、`status="success"`、`error=null`，停止原因放在 `data.run`：

```json
{
  "status": "success",
  "data": {
    "run": {
      "run_id": "run_ref",
      "status": "stopped",
      "resume_allowed": true,
      "safe_status_message": "这次续写已停下：已到达你设置的 AI 用量上限",
      "stop_record": {
      "stop_reason": "budget_exceeded",
      "stop_severity": "budget",
      "suggested_action": "adjust_budget",
      "generated_count": 5,
      "consumed_tokens": 350000,
      "stopped_at": "2025-06-09T15:30:00+08:00"
      }
    }
  },
  "error": null
}
```

前端根据 `stop_reason` 做差异化展示（`budget_exceeded` → 调整预算；`user_manual_stop` → 继续写；`blocking_review_consecutive` → 处理冲突）。针对 STOPPED 发起 pause/stop/confirm-continue 等不适用 mutation 时，按 P2-04 状态机返回已有的非法状态转换 409；`resume` 只有在 `resume_allowed=true` 且对应门控通过时可成功。不得为 STOPPED 另造 200“错误响应”。

---

## 七、后端修改文件改动原因

| 文件 | 改动原因 |
|---|---|
| `domain/entities/ai/models.py` | P2 公共实体与 LLMCallLog 补 scope/usage/cost 不可变事实；P2-09 CostBudget/CostSummary 只放 `cost_entities.py`，不重复定义 |
| `application/services/ai/agent_runtime_service.py` | 所有 Agent 模型调用强制注入 GuardedLLMExecutor/LLMCallScope；P2-05 Mention 路由复用 AgentRuntime 查询能力 |
| `application/services/ai/agent_workflow.py` | P2-04 AutoContinuationQueueService 复用 P1 MultiChapterContinuationService；P2-06/07 委托 Planner Agent |
| `application/services/ai/tool_facade.py` | P2 各模块新增 Tool 白名单注册 |
| `application/services/ai/context_pack_service.py` | P2-03 Style DNA 层以 `OPTIONAL_LOWEST` 优先级注入 ContextPack 可选层（见 P2-03 §4.1）；P2-05 Mention 上下文可能作为 ContextPack 扩展源 |
| `application/services/v1/chapter_service.py` | P2-10 章节保存/确认后触发 `AnalysisMetricRefreshService.mark_stale` |
| `application/services/ai/style_dna_extraction_service.py` | P2-10 StyleProfile 变更后触发 `mark_stale` |
| `presentation/api/app.py` | 注册 P2 全部 12 个 router（含 P2-09 的 cost_dashboard + cost_budget + cost_prices）；P2-02 verify 写入口仍复用 citations router |

---

## 附录 A：P2 全部文件清单（以各模块详细设计为准）

> **注意**：以下清单从 P2-01~P2-10 各模块代码改动面汇总，以各模块设计文档为权威源。本文只列集成层感知的文件，不做独立统计。

### 后端新增

```
application/ports/ai/
  provider_attempt_guard_port.py          # P0 Core 通用门控 Port/DTO

application/services/ai/
  multi_chapter_service.py               # P2-01
  citation_link_service.py               # P2-02
  style_dna_service.py                   # P2-03
  auto_queue_service.py                  # P2-04
  stop_condition_evaluator.py            # P2-04
  mention_service.py                     # P2-05
  opening_agent_service.py               # P2-06
  outline_assist_service.py              # P2-07
  outline_application_service.py         # P2-07 apply 门控
  selection_rewrite_service.py           # P2-08
  cost_dashboard_query_service.py        # P2-09 只读查询
  cost_budget_service.py                 # P2-09 受控预算配置
  cost_price_policy_service.py           # P2-09 手动价格受控配置
  cost_usage_reconciliation_service.py   # P2-09 用量缺口确定性修复
  price_resolver_service.py              # P2-09 价格解析与快照
  budget_gate_service.py                 # P2-09 Application 预算编排
  budget_provider_attempt_guard.py       # P2-09 实现 Core Guard Port
  guarded_llm_executor.py                # P2-09 所有生产模型调用统一入口
  analysis_dashboard_query_service.py    # P2-10 只读查询
  analysis_metric_refresh_service.py     # P2-10 缓存写入
  analysis_dashboard_constants.py        # P2-10 STOP_WORDS_ZH / AI_SIGNAL_WORDS / CLIFFHANGER_WORDS

domain/entities/ai/
  cost_entities.py                       # P2-09 LLMCallScope、Cost/Budget/Price 领域契约
  analysis_entities.py                   # P2-10 AnalysisMetric + 各维度返回结构
  suggestion_payloads.py                 # P2-07 4 个 Payload dataclass [修改]

domain/services/ai/
  budget_guard.py                        # P2-09 预算核心规则 Domain Service

domain/validators/
  outline_suggestion_schemas.py          # P2-07 4 个 OutputValidator schema
  selection_rewrite_schema.py            # P2-08 选区改写 schema

domain/repositories/ai/
  multi_chapter_session_repository.py    # P2-01
  citation_link_repository.py            # P2-02
  style_profile_repository.py            # P2-03
  auto_queue_config_repository.py        # P2-04
  auto_queue_run_repository.py           # P2-04
  auto_queue_lifecycle_uow_port.py       # P2-04 生命周期原子事务/回执
  chapter_mention_repository.py          # P2-05
  opening_analysis_repository.py         # P2-06
  opening_strategy_repository.py         # P2-06
  imitation_risk_report_repository.py    # P2-06
  selection_rewrite_repository.py        # P2-08
  cost_budget_repository.py              # P2-09
  llm_call_log_cost_query_port.py        # P2-09 独立只读查询 Port
  llm_call_log_reconciliation_port.py    # P2-09 用量缺口修复 Port
  user_decision_query_port.py            # P2-09 采用状态只读投影
  auto_queue_budget_policy_port.py       # P2-09 AutoQueue 预算适配
  provider_price_catalog_port.py         # P2-09 官方精确价格目录
  model_price_policy_repository.py       # P2-09 手动价格 Port
  work_model_inventory_port.py           # P2-09 当前模型/受影响作品只读 Port
  cost_policy_mutation_coordinator_port.py # P2-09 跨设置一致性锁
  cost_control_mutation_uow_port.py      # P2-09 资源+回执原子事务
  budget_audit_port.py                   # P2-09 AgentTrace 审计适配 Port
  token_estimator_port.py                # P2-09 服务端输入用量估算
  analysis_metric_repository.py          # P2-10

infrastructure/persistence/
  sqlite_multi_chapter_session_repo.py   # P2-01
  sqlite_citation_link_repo.py           # P2-02
  sqlite_style_profile_repo.py           # P2-03
  sqlite_auto_queue_config_repo.py       # P2-04
  sqlite_auto_queue_run_repo.py          # P2-04
  sqlite_auto_queue_lifecycle_uow.py     # P2-04 生命周期原子事务/回执
  sqlite_chapter_mention_repo.py         # P2-05
  sqlite_opening_analysis_repo.py        # P2-06
  sqlite_opening_strategy_repo.py        # P2-06
  sqlite_imitation_risk_report_repo.py   # P2-06
  sqlite_selection_rewrite_repo.py       # P2-08
  sqlite_cost_budget_repo.py             # P2-09
  sqlite_llm_call_log_cost_query_adapter.py # P2-09 只读 Adapter
  sqlite_llm_call_log_reconciliation_adapter.py # P2-09 确定性修复 Adapter
  sqlite_model_price_policy_repo.py      # P2-09 手动价格
  sqlite_cost_control_mutation_uow.py    # P2-09 原子设置/回执
  ai_settings_work_model_inventory_adapter.py # P2-09 版本化模型清单
  sqlite_analysis_metric_repo.py         # P2-10

infrastructure/ai/pricing/
  provider_price_catalog_adapter.py      # P2-09 官方精确价格目录 Adapter

infrastructure/ai/tokenization/
  model_token_estimator_adapter.py       # P2-09 输入用量估算 Adapter

infrastructure/ai/audit/
  agent_trace_budget_audit_adapter.py    # P2-09 BudgetAuditPort Adapter

infrastructure/locking/
  cost_policy_mutation_coordinator.py    # P2-09 跨设置一致性锁

presentation/api/routers/v2/ai/
  multi_chapter.py         # P2-01
  citations.py             # P2-02
  style_dna.py             # P2-03
  auto_queues.py           # P2-04
  opening.py               # P2-06
  outline_assist.py        # P2-07
  selection_rewrite.py     # P2-08
  cost_dashboard.py        # P2-09 查询路由
  cost_budget.py           # P2-09 预算配置路由
  cost_prices.py           # P2-09 费用估算设置路由
  analysis_dashboard.py    # P2-10

presentation/api/routers/v2/
  mentions.py              # P2-05 prefix=/api/v2 (非 /api/v2/ai)
```

### 后端修改

```
domain/entities/ai/models.py
application/services/ai/llm_call_logger.py
application/services/ai/stop_condition_evaluator.py
application/services/ai/auto_queue_service.py
application/services/ai/agent_runtime_service.py
application/services/ai/agent_workflow.py
application/services/ai/tool_facade.py
application/services/ai/context_pack_service.py
application/services/v1/chapter_service.py
application/services/ai/style_dna_extraction_service.py
presentation/api/app.py
```

### 前端新增

```
frontend/src/views/
  CostDashboard.vue                    # P2-09
  AnalysisDashboard.vue               # P2-10

frontend/src/config/
  p2FeatureFlags.js                   # P2 Feature Flag 配置

frontend/src/components/workspace/
  MultiChapterPanel.vue                # P2-01
  AutoQueuePanel.vue                   # P2-04
  MentionPopup.vue                     # P2-05
  MentionHighlight.vue                 # P2-05
  MentionTooltip.vue                   # P2-05
  OpeningAgentWizard.vue               # P2-06
  OutlineAssistPanel.vue               # P2-07
  SelectionRewriteToolbar.vue          # P2-08
  SelectionRewriteDiffModal.vue        # P2-08

frontend/src/components/settings/
  AICostSettings.vue                   # P2-09 费用估算（复用 SettingsCenter）

frontend/src/composables/
  useMentionDetector.js                # P2-05
  useSelectionRewrite.js               # P2-08（如保留，仅做 UI/composable，不承载 DraftSnapshot 权威）

frontend/src/stores/
  useMultiChapterStore.js              # P2-01
  useCitationStore.js                  # P2-02
  useAutoQueueStore.js                 # P2-04
  useMentionStore.js                   # P2-05
  useStyleDNAStore.js                  # P2-03
  useOpeningStore.js                   # P2-06
  useOutlineAssistStore.js             # P2-07
  useSelectionRewriteStore.js          # P2-08
  useCostDashboardStore.js             # P2-09 查询
  useCostBudgetStore.js                # P2-09 预算配置
  useAICostSettingsStore.js            # P2-09 手动价格
  useAnalysisDashboardStore.js         # P2-10
```

### 前端修改

```
frontend/src/components/workspace/PureTextEditor.vue      # Mention 注入
frontend/src/components/workspace/RightWorkspacePanel.vue  # 新增 Tab
frontend/src/router/index.js                               # 新增路由 + Feature Flag 守卫
```

---

## 附录 B：v1.1 → v1.2 变更摘要

| # | 变更 | 原因 |
|---|---|---|
| 1 | 说明文字"9 组 API"→"11 组 API"，端点索引表拆分 Cost Dashboard + Cost Budget 为两组 | P2-09 v1.2 拆为两个 router |
| 2 | 删除端点数合计（50/55），改为"以各模块详细设计为准"声明 | 端点数已不可信，硬写总数会产生维护债务 |
| 3 | 路由注册代码补齐 `cost_budget` 的 import 和 `include_router` | P2-09 v1.2 预算配置 API 需要独立注册 |
| 4 | 附录文件清单中 P2-09/10 服务文件名已与最新模块设计对齐（v1.1 已修复，v1.2 确认） | 避免新旧文件名混淆 |
| 5 | P2-06 附录补 `opening_strategy_repository.py` + `imitation_risk_report_repository.py` + 对应 SQLite 实现（v1.1 已补，v1.2 确认） | — |
| 6 | P2-07 附录补 `outline_application_service.py` + `outline_suggestion_schemas.py` + `suggestion_payloads.py` | P2-07 v1.2 新增文件 |
| 7 | P2-08 附录补 `selection_rewrite_schema.py`（domain/validators） | P2-08 v1.2 新增 |
| 8 | P2-05 前端组件命名统一：`AtMention*` → `Mention*`，WritingStudio 集成图同步 | 消除 AtMention / @Mention / Mention 混用 |
| 9 | §3.3 Store 补 `useCitationStore` + `useOutlineAssistStore` + `useSelectionRewriteStore` + `useCostBudgetStore` | 独立面板/功能需独立 Store |
| 10 | §3.4 新增 P2-05 组件命名统一表 | 明确每个 Mention 组件的文件名和职责 |
| 11 | 文档头部增加文件扩展名声明（以项目现有 .ts/.js 为准） | 避免 JS/TS 混用导致工程不一致 |
| 12 | §3.1 路由 meta 从 `requiresAI: true` 细化为 `requiresAIWorkspace` + `requiresProviderConfigured`，成本/分析看板不要求 Provider 已配置 | 用户未配 AI 模型时仍可查看历史成本和分析数据 |
| 13 | §5 轮询端点补 P2-07 suggestion polling + P2-08 selection-rewrite status + P2-10 recompute/status | 原列表不完整 |
| 14 | §6 错误码从 8 个扩展到 18 个，按模块来源分组 + HTTP 映射原则 | 覆盖各模块已定义错误码 |
| 15 | **新增 §1**：分期落地策略（S1/S2/S3 表） + Feature Flag 体系（10 个 flag + 使用规则） | P2-11 作为集成收口文档必须有分期和开关控制 |
| 16 | §4.1 AIPanel 措辞从"不改内部逻辑"→"优先 props/slots/composable 扩展，必要时允许非破坏性扩展点" | 更实际的约束表述 |
| 17 | 附录删除文件数量统计（"后端新增 26/32 files"等），改为"以各模块详细设计为准"声明 | 数量已不可信，避免维护债务 |
| 18 | 端点索引表增加 Feature Flag 列 | 前端入口可用性需与 Flag 联动 |

---

## 附录 C：v2.3 → v2.4 变更摘要

| # | 变更 | 原因 |
|---|---|---|
| 1 | 新增 §2.6 AI 用量与预算 v1.3 冻结端点和查询契约 | 补齐 trend、unknown cost、严格 task scope |
| 2 | 将预算 PUT 和旧 AutoQueue 预算入口纳入真实 user_action、幂等与审计门 | 禁止旁路修改预算保护 |
| 3 | `P2_BUDGET_EXCEEDED` 固定为 HTTP 409，内部 `budget_exceeded` 不对外 | 统一公开/内部语义 |
| 4 | 补齐预算未知、查询失败、并发、审计和成本查询参数错误码 | warning/error 与 exceeded/unknown 分离 |
| 5 | 文件清单增加 LLMCallLog 只读查询 Port/Adapter 和预算幂等回执 | 对齐 DDD + 清洁架构 |
| 6 | P2-09 路由扩为 Cost Dashboard / Cost Budget / Cost Prices 三组，总计 12 组 | 给手动价格设置稳定落点 |
| 7 | 看板 Flag 只关闭看板；预算/价格设置和门控不随之关闭 | 防止用户无法调整已生效预算 |
| 8 | 冻结 GuardedLLMExecutor + LLMCallScope 为全部生产模型调用必经路径 | 消除可选预算依赖和 Provider 旁路 |
| 9 | 查询契约增加 usage/history 完整度，details 零或一 scope，task-cost 恰好一 scope | 对齐 unknown 与 retention 规则 |
| 10 | 预算、价格、AutoQueue 设置统一 UoW/审计/幂等文件边界 | 关闭部分写和崩溃窗口 |

---

## 附录 D：v2.4 → v2.5 变更摘要

| # | 变更 | 原因 |
|---|---|---|
| 1 | AutoQueue 作者入口统一显示“接着写”，内部路由、Store 与领域名保持不变 | 让非技术小说作者理解动作，同时避免重复建模 |
| 2 | `/auto-queues/start` 增加可选 0..60 字 `user_instruction`，透传既有 P2-01 会话 | 允许作者用一句话表达下一章意图 |
| 3 | 冻结写作意图的前后端双重长度校验及敏感日志边界 | 防止完整创作内容进入日志或通用任务载荷 |
