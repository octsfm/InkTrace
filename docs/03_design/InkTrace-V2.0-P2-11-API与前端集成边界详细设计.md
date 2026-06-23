# InkTrace V2.0-P2-11 API 与前端集成边界详细设计

版本：v1.2 / P2 模块级详细设计候选冻结版
状态：候选冻结
所属阶段：InkTrace V2.0 P2 集成
设计范围：P2 全部 API 路由注册、前端路由与组件集成边界、Feature Flag 体系、分期落地策略

依据文档：

- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§7、§8）
- `docs/03_design/InkTrace-V2.0-P2-01~10-*.md`
- `docs/03_design/InkTrace-V2.0-P1-11-API与前端集成边界详细设计.md`

说明：本文档收口 P2 全部 **11 组 API 路由**和前端模块的集成边界，确保与 P1 现有路由和组件体系无冲突。本文档不写代码、不修改源码。

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

- `false` 的模块：前端不显示入口（按钮/Tab/路由）。后端**统一注册路由**，但返回 `503 Service Unavailable` + `error_code: "P2_FEATURE_DISABLED"`。前端据此统一处理（不区分 404 和 feature disabled），也方便灰度启用时只需改配置无需改代码。
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
    cost_budget,        # P2-09 预算配置（CostBudgetService + BudgetGuard）
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
app.include_router(cost_budget.router, prefix="/api/v2/ai")       # P2-09 v1.2 拆分
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
| 10 | Cost Budget | `/api/v2/ai/cost-budget` | P2-S3 | `enable_cost_dashboard` |
| 11 | Analysis Dashboard | `/api/v2/ai/analysis-dashboard` | P2-S3 | `enable_analysis_dashboard` |

> **端点数**不在此表中硬写——以各模块详细设计文档为准。P2-09（Cost Dashboard + Cost Budget）和 P2-10（Analysis Dashboard）在审查修订中已拆分路由，具体端点定义见 P2-09 v1.2 和 P2-10 v1.2。

### 2.3 通用规范

- 所有端点沿用 P0-11 定义的 `{ request_id, trace_id, status, data, error, polling_hint }` 格式。
- **caller_type=user_action 必检端点**（需要 Presentation 层校验调用方为用户真实操作，拒绝 agent/system 调用）：

| 端点 | 动作 | 原因 |
|---|---|---|
| `POST /multi-chapter/{id}/advance` | 推进多章续写 | 用户确认当前章后推进 |
| `POST /style-dna/{id}/confirm` | 确认风格画像 | 用户确认后才能生效 |
| `POST /style-dna/{id}/disable` | 禁用风格画像 | 用户操作 |
| `POST /auto-queues/{id}/confirm-continue` | 安全模式继续 | 用户逐章确认（不可被 Agent 自动推进） |
| `POST /opening/strategies/{strategy_id}/confirm` | 确认开篇策略 | P2-06 strategy confirm |
| `POST /opening/strategies/{strategy_id}/reject` | 拒绝开篇策略 | P2-06 strategy reject |
| `POST /outline-assist/*/apply` | 应用大纲辅助 | 用户确认大纲建议 |
| `POST /selection-rewrite/*/apply` | 应用选区改写 | 用户确认改写结果 |
| `POST /auto-queues/{id}/stop` | 手动停止队列 | 用户操作 |

> **注**：Opening Agent 不新增独立的正式正文 apply 端点。CandidateDraft 的 apply 仍走 P0/P1 标准 HumanReviewGate / CandidateDraft apply 链路，不在 P2-06 中额外暴露。Opening 的 user_action 校验只针对 strategy confirm/reject 操作。
**原则**：凡是会导致正式数据变更（apply/confirm/accept）或推进工作流越过用户确认门（advance/confirm-continue）的端点，必须校验 `caller_type=user_action`。

- API 层不承载业务逻辑，不直接访问 Provider/Repository/ModelRouter。

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

### 3.2 WritingStudio 内集成点

```
WritingStudio.vue
├── 顶部工具栏
│   └── [多章续写] 按钮                → MultiChapterPanel 弹窗
├── 中间编辑区 (PureTextEditor)
│   ├── MentionDetector                 → P2-05 内联 (composable)
│   ├── MentionPopup                    → P2-05 浮动 (组件)
│   └── SelectionToolbar                → P2-08 浮动
├── 右侧面板 (RightWorkspacePanel)
│   ├── [候选稿] tab (已有)
│   │   └── Citation 引用浮层          → P2-02 内联
│   ├── [自动续写] tab (新增)          → AutoQueuePanel
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
useAnalysisDashboardStore.js   // P2-10 分析看板数据
```

> P2-09 拆分为 `useCostDashboardStore`（只读聚合展示）和 `useCostBudgetStore`（预算表单编辑/提交），避免预算配置逻辑与成本展示逻辑耦合。

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

### 4.2 P1 API 不受影响

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
| `/opening/{id}/status` | P2-06 | 开篇分析进度 | 1.5-2s |
| `/style-dna/{id}` | P2-03 | 风格画像提取状态 | 3-5s（提取中） |
| `/api/v2/ai/suggestions/{suggestion_id}` | P2-07 | 大纲辅助建议生成状态 | 2-3s |
| `/selection-rewrite/{rewrite_id}` | P2-08 | 选区改写候选生成状态 | 2-3s |
| `/analysis-dashboard/recompute/status` | P2-10 | 大作品重算进度 | 5s |

### 5.2 策略说明

- **同步返回**的端点（如大部分 GET 查询、PUT 配置）不涉及轮询。
- **Style DNA `extract`**：`StyleDNAExtractionService.extract()` 直接调用 ModelRouter。P2 默认同步返回（阻塞等待 LLM 响应），超时由 HTTP 层处理（默认 60s）。若未来改为异步，则增加 `GET /style-dna/{id}/status` 轮询端点。
- **Selection Rewrite**（P2-08 v1.2）：异步模式，后台执行，不阻塞 HTTP。前端轮询 `GET /selection-rewrite/{rewrite_id}`。
- **Outline Assist**（P2-07）：`generate_*` 类操作为异步，前端轮询 `GET /api/v2/ai/suggestions/{suggestion_id}`（复用 P1 AI Suggestion 轮询机制）。
- SSE 作为可选增强（P2 不默认依赖）。
- 轮询终态停止：状态进入 completed / failed / cancelled / stopped 后前端停止轮询。

---

## 六、错误码统一

### 6.1 错误码映射原则

- 所有 P2 新增错误码前缀 `P2_`。
- 所有错误响应沿用 P0-11 格式：`{ error: { code, message, safe_message, data? } }`。
- HTTP 状态码映射：`P2_BUDGET_EXCEEDED` → `402`（推荐）或 `409`/`422` + stable `error_code`；`P2_CALLER_FORBIDDEN` → `403`；`P2_*_CONFLICT` → `409`；其余业务错误 → `400` 或 `422`。
- 各模块的具体错误码以模块详细设计为准；本文档只列跨模块通用错误码和映射原则。

### 6.2 跨模块通用错误码

| 错误码 | HTTP | 说明 | 来源模块 |
|---|---|---|---|
| `P2_CALLER_FORBIDDEN` | 403 | caller_type 校验失败（agent/system 调用 user_action 专属端点） | 全部 |
| `P2_FEATURE_DISABLED` | 503 | 该功能在当前版本未启用（Feature Flag = false） | 全部 |
| `P2_BUDGET_EXCEEDED` | 402 | 预算超限 | P2-09 |
| `P2_CITATION_UNVERIFIED` | 400 | Citation 未通过校验 | P2-02 |
| `P2_CITATION_SOURCE_HASH_MISMATCH` | 400 | Citation 源文本哈希与当前正文不一致 | P2-02 |
| `P2_STYLE_LOW_CONFIDENCE` | 200† | 风格画像低置信度（非错误，warning 级） | P2-03 |
| `P2_STYLE_NO_ACTIVE_PROFILE` | 200† | 无活跃 StyleProfile（降级展示） | P2-10 |
| `P2_COPYRIGHT_NOT_CONFIRMED` | 400 | 版权未确认 | P2-06 |
| `P2_IMITATION_RISK_HIGH` | 400 | 过度模仿风险高 | P2-06 |
| `P2_STRATEGY_NOT_CONFIRMED` | 400 | 开篇策略未确认 | P2-06 |
| `P2_RIGHTS_NOT_CONFIRMED` | 400 | 权利声明未确认 | P2-06 |
| `P2_SELECTION_EMPTY` | 400 | 选区为空 | P2-08 |
| `P2_SELECTION_CONFLICT` | 409 | 选区与其他版本冲突 | P2-08 |
| `P2_SELECTION_TEXT_MISMATCH` | 409 | 选区基准文本与当前正文不匹配 | P2-08 |
| `P2_TARGET_CONFLICT` | 409 | 目标章节冲突 | P2-07 |
| `P2_MULTI_CHAPTER_BLOCKED` | 409 | 某章审稿 blocking | P2-01 |
| `P2_AUTO_QUEUE_STOPPED` | 200 | 自动队列已停止（正常终态，含停止原因 data） | P2-04 |
| `P2_ANALYSIS_STALE` | 200† | 分析数据已过期（warning 级，非错误） | P2-10 |

> † 标记为 `200` 的错误码表示该状态不是 HTTP 层面的错误，而是业务 warning——响应 `status: "success"`，`error` 字段为空，warning 信息放在 `data.warning` 或 `data.note` 中。

### 6.3 P2_AUTO_QUEUE_STOPPED 错误码结构

停止原因放在 `error.data` 扩展字段（非 `error.message` 字符串）：

```json
{
  "error": {
    "code": "P2_AUTO_QUEUE_STOPPED",
    "message": "自动续写队列已停止",
    "safe_message": "自动续写队列已停止：{stop_reason_display}",
    "data": {
      "stop_reason": "budget_exceeded",
      "stop_severity": "budget",
      "suggested_action": "stop_queue",
      "generated_count": 5,
      "consumed_tokens": 350000,
      "stopped_at": "2025-06-09T15:30:00+08:00"
    }
  }
}
```

前端根据 `stop_reason` 做差异化展示（`budget_exceeded` → 调整预算；`user_manual_stop` → 继续队列；`blocking_review_consecutive` → 处理冲突）。

---

## 七、后端修改文件改动原因

| 文件 | 改动原因 |
|---|---|
| `domain/entities/ai/models.py` | P2-01~10 新增领域实体（AutoQueueConfig、CostBudget、AnalysisMetric 等），追加 dataclass 和枚举 |
| `application/services/ai/agent_runtime_service.py` | P2-04 注入 BudgetGuard 的 check 调用（可选）；P2-05 Mention 路由复用 AgentRuntime 查询能力 |
| `application/services/ai/agent_workflow.py` | P2-04 AutoContinuationQueueService 复用 P1 MultiChapterContinuationService；P2-06/07 委托 Planner Agent |
| `application/services/ai/tool_facade.py` | P2 各模块新增 Tool 白名单注册 |
| `application/services/ai/context_pack_service.py` | P2-03 Style DNA 层以 `OPTIONAL_LOWEST` 优先级注入 ContextPack 可选层（见 P2-03 §4.1）；P2-05 Mention 上下文可能作为 ContextPack 扩展源 |
| `application/services/v1/chapter_service.py` | P2-10 章节保存/确认后触发 `AnalysisMetricRefreshService.mark_stale` |
| `application/services/ai/style_dna_extraction_service.py` | P2-10 StyleProfile 变更后触发 `mark_stale` |
| `presentation/api/app.py` | 注册 P2 全部 11 个 router（含 P2-09 拆分的 cost_dashboard + cost_budget）；P2-02 新增 verify 写入口仍复用 citations router |

---

## 附录 A：P2 全部文件清单（以各模块详细设计为准）

> **注意**：以下清单从 P2-01~P2-10 各模块代码改动面汇总，以各模块设计文档为权威源。本文只列集成层感知的文件，不做独立统计。

### 后端新增

```
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
  cost_budget_service.py                 # P2-09 预算配置 CRUD + check
  budget_guard.py                        # P2-09 预算拦截器
  analysis_dashboard_query_service.py    # P2-10 只读查询
  analysis_metric_refresh_service.py     # P2-10 缓存写入
  analysis_dashboard_constants.py        # P2-10 STOP_WORDS_ZH / AI_SIGNAL_WORDS / CLIFFHANGER_WORDS

domain/entities/ai/
  cost_entities.py                       # P2-09 CostBudget, BudgetCheckResult, CostSummary, CostDetail
  analysis_entities.py                   # P2-10 AnalysisMetric + 各维度返回结构
  suggestion_payloads.py                 # P2-07 4 个 Payload dataclass [修改]

domain/validators/
  outline_suggestion_schemas.py          # P2-07 4 个 OutputValidator schema
  selection_rewrite_schema.py            # P2-08 选区改写 schema

domain/repositories/ai/
  multi_chapter_session_repository.py    # P2-01
  citation_link_repository.py            # P2-02
  style_profile_repository.py            # P2-03
  auto_queue_config_repository.py        # P2-04
  auto_queue_run_repository.py           # P2-04
  chapter_mention_repository.py          # P2-05
  opening_analysis_repository.py         # P2-06
  opening_strategy_repository.py         # P2-06
  imitation_risk_report_repository.py    # P2-06
  selection_rewrite_repository.py        # P2-08
  cost_budget_repository.py              # P2-09
  analysis_metric_repository.py          # P2-10

infrastructure/persistence/
  sqlite_multi_chapter_session_repo.py   # P2-01
  sqlite_citation_link_repo.py           # P2-02
  sqlite_style_profile_repo.py           # P2-03
  sqlite_auto_queue_config_repo.py       # P2-04
  sqlite_auto_queue_run_repo.py          # P2-04
  sqlite_chapter_mention_repo.py         # P2-05
  sqlite_opening_analysis_repo.py        # P2-06
  sqlite_opening_strategy_repo.py        # P2-06
  sqlite_imitation_risk_report_repo.py   # P2-06
  sqlite_selection_rewrite_repo.py       # P2-08
  sqlite_cost_budget_repo.py             # P2-09
  sqlite_analysis_metric_repo.py         # P2-10

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
  analysis_dashboard.py    # P2-10

presentation/api/routers/v2/
  mentions.py              # P2-05 prefix=/api/v2 (非 /api/v2/ai)
```

### 后端修改

```
domain/entities/ai/models.py
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

frontend/src/composables/
  useMentionDetector.js                # P2-05
  useSelectionRewrite.js               # P2-08

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
