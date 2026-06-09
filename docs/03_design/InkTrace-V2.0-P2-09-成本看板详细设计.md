# InkTrace V2.0-P2-09 成本看板详细设计

版本：v1.2 / P2 模块级详细设计候选冻结版
状态：候选冻结
所属阶段：InkTrace V2.0 P2-S3
设计范围：AI 成本追踪、预算配置、预算拦截与告警系统

依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`（R-AI-ENH-05）
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§4.9）
- `docs/03_design/V2/InkTrace-V2.0-P0-02-AIJobSystem详细设计.md`（LLMCallLog 定义）
- `docs/03_design/InkTrace-V2.0-P1-02-AgentWorkflow详细设计.md`（AgentTrace 定义）
- `docs/03_design/InkTrace-V2.0-P2-04-自动续写队列详细设计.md`（§2.4 StopCondition #7）

说明：**LLMCallLog 是成本事实的唯一权威源**。成本看板拆分为三个服务：`CostDashboardQueryService`（纯只读聚合）、`CostBudgetService`（预算配置管理）、`BudgetGuard`（预算拦截器）。预算配置可写，成本事实不另建表。本文档不写代码、不修改源码。

---

## ⚠️ P2-09 开发前置条件（冻结）

P0 `LLMCallLog` 实体和 `llm_call_logs` 表必须补齐以下字段，否则 P2-09 成本聚合准确性降低：

| 字段 | 用途 | 当前 P0 状态 |
|---|---|---|
| `work_id` | 按作品聚合成本 | ❌ 缺失，当前只能通过 `trace_id` → `AgentTrace.work_id` 间接关联 |
| `session_id` | 按 AgentSession 聚合 | ❌ 缺失（`llm_call_logger.record` 已接收参数但未写入实体） |
| `step_id` | 按 AgentStep 关联 | ❌ 缺失 |
| `estimated_cost` | 调用实际成本 | ❌ 缺失，当前 LLMCallLog / LLMUsage 均无此字段 |
| `price_snapshot_json` | 调用时价格快照（JSON 字符串，结构见 §3.2） | ❌ 缺失 |

**降级路径**：若 P0 在 P2-09 启动时仍未补齐，P2-09 只能通过 `trace_id` JOIN `agent_traces` 获取 `work_id`，并通过 `ModelRouter` 当前配置计算成本（**禁止用当前价格回算历史**，见 §3.1）。降级模式需在 CostDashboardQueryService 初始化时显式传入 `fallback_mode=True` 并在日志中 warn。成本数字在降级模式下标记为估算值（`estimated: true`）。

> **向后任务排期提示**：此前置条件应在 P2-S3 开发计划中作为 P0 反向补字段任务显式列出，避免遗漏。

---

## 一、文档定位与设计范围

P2-09 覆盖 AI 成本追踪、三级预算体系、预算拦截、超限告警。本模块自身不产生新 AI 调用。

**核心约束**：
- **成本事实只读**：不新建成本记录表，所有成本数据来自 `llm_call_logs`。
- **预算配置可写**：预算阈值、告警阈值可增删改。
- **预算拦截独立**：BudgetGuard 供 AIJobService / AutoQueueService 等调用方在启动 AI 前检查。
- **不承载业务规则**：CostDashboardQueryService 只做聚合展示，BudgetGuard 只做准入判断。

---

## 二、数据源

### 2.1 LLMCallLog 最小字段依赖

成本看板完全依赖 P0 `llm_call_logs`，至少需要以下字段。若 P0 当前表不满足，列为 `【待补】`。

| 字段 | llm_call_logs 列 / 来源 | 用途 | P0 状态 |
|---|---|---|---|
| call_id | `id` / `request_id` | 记录唯一标识 | ✅ `LLMCallLog.request_id` |
| work_id | `work_id` | 按作品聚合 | ⚠️【待补】P0 `LLMCallLog` 当前无 `work_id` 字段。需在 P0 补字段或通过 `trace_id` → `AgentTrace.work_id` 关联 |
| session_id | `session_id` | 按 AgentSession 聚合（`llm_call_logger.record` 已接收但未写入实体） | ⚠️【待补】`LLMCallLog` 实体当前无 `session_id`，需补字段 |
| provider_name | `provider_name` | 按 Provider 聚合 | ✅ |
| model_name | `model_name` | 按 Model 聚合 | ✅ |
| model_role | `model_role` | 按角色聚合（Kimi/DeepSeek） | ✅ |
| input_tokens | `usage.input_tokens` | 输入 token 数 | ✅ `LLMUsage.input_tokens` |
| output_tokens | `usage.output_tokens` | 输出 token 数 | ✅ `LLMUsage.output_tokens` |
| total_tokens | `usage.total_tokens` | 总 token 数 | ✅ `LLMUsage.total_tokens` |
| estimated_cost | — | 本次调用估算成本 | ❌【待补】P0 当前无此字段。P2-09 实现前必须在 `LLMCallLog` 或 `LLMUsage` 中补 `estimated_cost` 和 `price_snapshot_json` |
| price_snapshot_json | — | 调用时价格快照 | ❌【待补】见 §3.1 |
| duration_ms | `(finished_at - started_at)` 计算 | 调用耗时 | ✅ 可计算 |
| status | `status` | 成功/失败 | ✅ `LLMCallStatus` |
| error_code | `error_code` | 失败错误码 | ✅ |
| started_at | `started_at` | 时间范围过滤 | ✅ |
| trace_id | `trace_id` | 关联 AgentTrace | ✅ |
| step_id | `step_id` | 关联 AgentStepTrace | ⚠️【待补】同 `session_id` |

> **待补字段汇总**：P2-09 实现前，P0 `LLMCallLog` 需补充 `work_id`、`session_id`、`step_id`、`estimated_cost`、`price_snapshot_json`。若 P0 不变更，P2-09 需通过 JOIN `agent_traces` 获取 `work_id` 并自行外挂成本计算。

### 2.2 AgentTrace 的定位

`agent_traces` 只用于补充分组维度（`workflow_type`、`agent_type`、`session_id`），不替代 `llm_call_logs` 作为成本事实源。

| 规则 | 说明 |
|---|---|
| 成本事实源 | `llm_call_logs` |
| AgentTrace 用途 | 按 `workflow_type` / `agent_type` / `phase` 分组展示 |
| 数字不一致时 | 以 `llm_call_logs` 为准 |
| AgentTrace 不做成本审计 | Trace 可能因 session cancel / restart 存在不完整数据 |

### 2.3 adoption_rate 处理

**P2-S3 不实现 `adoption_rate`**。

原因：
- 采纳率来自 `candidate_drafts.status` / `ai_suggestions.status` 等业务对象，不属于 `llm_call_logs` 或 `agent_traces`。
- 成本看板不应混入业务效果分析，后者属于分析看板（P2-10 或后续）。

`CostSummary` 中不设 `adoption_rate` 字段。若后续版本需要，建议在分析看板模块独立实现。

---

## 三、成本计算规则

### 3.1 核心原则

| 规则 | 说明 |
|---|---|
| 优先使用 LLMCallLog.estimated_cost | `estimated_cost` 由 LLMCallLogger 在记录时写入，作为调用时实际成本 |
| 禁止用"当前模型价格"回算历史成本 | 模型价格可能变化，回算会导致历史数据失真 |
| 失败调用是否计费 | 取决于 Provider：大多数 Provider 对失败调用不计费，但 `provider_auth_failed` 等错误可能仍计费。P2-09 按 `estimated_cost` 取值，若 Provider 返回 0 则记为 0 |
| 缓存 token | 若 Provider 返回 `cache_read_input_tokens` / `cache_creation_input_tokens`，P2-09 初期按 `total_tokens` 统一展示，不拆缓存维度 |

### 3.2 price_snapshot_json 结构

每次 LLM 调用时，在 `LLMCallLog` 中写入调用时的价格快照（JSON 字符串），供成本计算和历史审计使用：

```json
{
  "input_price_per_1k": 0.002,
  "output_price_per_1k": 0.008,
  "currency": "CNY",
  "pricing_source": "model_router_config",
  "captured_at": "2025-06-09T14:30:00+08:00"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| input_price_per_1k | float | 每 1000 输入 token 价格 |
| output_price_per_1k | float | 每 1000 输出 token 价格 |
| currency | str | 货币单位，`CNY` / `USD` |
| pricing_source | str | 价格来源：`model_router_config` / `provider_api` / `manual` |
| captured_at | str | 快照时间（ISO 8601） |

### 3.3 estimated_cost 计算规则

`LLMCallLogger.record()` 在写入时计算 `estimated_cost`：

```
estimated_cost = max(input_tokens, 0) * input_price_per_1k / 1000
               + max(output_tokens, 0) * output_price_per_1k / 1000
```

- 若 `usage` 为 `None`（调用失败无返回），`estimated_cost` = 0（或 Provider 返回的实际费用）。
- `input_price_per_1k` / `output_price_per_1k` 从 `ModelRouter` 的当前配置读取。
- 写入 `price_snapshot_json` 保存快照。

**P2-09 不重新计算历史价格**。若 `estimated_cost` 缺失（存量数据），聚合时跳过该记录（不估算，不补齐）。

---

## 四、服务拆分

原单一 `CostDashboardService` 拆分为三个职责清晰的服务：

```
CostDashboardQueryService   ← 纯只读聚合，https://api/v2/ai/cost-dashboard/*
CostBudgetService           ← 预算配置 CRUD + 检查，https://api/v2/ai/cost-budget/*
BudgetGuard                 ← 预算拦截器，供其他服务注入调用
```

### 4.1 CostDashboardQueryService（纯只读聚合）

```python
class CostDashboardQueryService:
    """纯只读聚合服务。不写任何数据，不调用 AI Provider，不承载业务规则。"""
    def __init__(
        self,
        *,
        llm_call_log_repository,     # 复用 P0
        agent_trace_repository,      # 复用 P1（仅补充分组维度）
    ) -> None: ...

    # 聚合查询（实时，从 LLMCallLog GROUP BY）
    async def get_work_cost(self, work_id: str, *, month: str | None = None) -> CostSummary: ...
    async def get_task_cost(self, job_id: str | None = None,
                            session_id: str | None = None,
                            run_id: str | None = None) -> list[CostDetail]: ...
    async def get_details(self, *, work_id: str, job_id: str | None = None,
                          limit: int = 50, offset: int = 0) -> CostDetailPage: ...
```

**不再有 `get_monthly_cost`**——月度过滤通过 `get_work_cost(work_id, month="YYYY-MM")` 实现。

**`get_task_cost` 参数明确**：
- `job_id`：AIJob ID（P0）
- `session_id`：AgentSession ID（P1）
- `run_id`：AutoQueueRun ID（P2-04）
- 三者互斥，按优先级：`job_id` > `session_id` > `run_id`
- 至少传一个，否则返回空

### 4.2 CostBudgetService（预算配置管理）

```python
class CostBudgetService:
    """预算配置管理服务。预算配置可写，但只写 cost_budgets 表，不写成本事实。"""
    def __init__(
        self,
        *,
        budget_repository,            # 新增：cost_budgets 表读写
        llm_call_log_repository,      # 复用 P0：check_budget 需要聚合当前用量
    ) -> None: ...

    async def get_budgets(self, work_id: str) -> list[CostBudget]: ...
    async def upsert_budget(self, budget: CostBudget) -> CostBudget: ...
    async def delete_budget(self, budget_id: str) -> None: ...
    async def check_budget(self, work_id: str) -> BudgetCheckResult: ...
```

**`check_budget` 放在 CostBudgetService**：
- 它需要读取 `cost_budgets` 表获取阈值 + 通过 `llm_call_log_repository` 聚合当前用量。
- 返回 `BudgetCheckResult` 供 BudgetGuard 或其他调用方使用。

**`upsert_budget` 幂等语义**（继承 v1.1 §4.6）：
- `budget_id` 由服务端生成（`bgt_{uuid_hex_12}`）。
- `UNIQUE(work_id, budget_type)` 保证同一作品的同一预算类型只有一条记录。
- 首次配置不传 `budget_id`，服务端自动生成；传了则按 `budget_id` 或 `(work_id, budget_type)` 匹配更新。

### 4.3 BudgetGuard（预算拦截器）

```python
class BudgetGuard:
    """预算拦截器。供 AIJobService / AgentRuntimeService / AutoQueueService 等调用方
       在启动 AI 能力前检查预算。不持久化状态，不写数据库。"""
    def __init__(self, *, budget_service: CostBudgetService) -> None: ...

    async def check_before_ai_job_start(self, work_id: str,
                                         job_type: str) -> BudgetCheckResult: ...
    async def check_after_llm_call(self, work_id: str) -> BudgetCheckResult: ...
    async def check_auto_queue_budget(self, run_id: str) -> BudgetCheckResult: ...
```

**`job_type` 映射**（哪些 Job 类型受哪些预算约束）：

| job_type (P0) | 受初始化预算约束 | 受队列预算约束 | 受月度预算约束 |
|---|---|---|---|
| `ai_initialization` | ✅ | ❌ | ✅ |
| `continuation` | ❌ | ✅（通过 P2-04 队列） | ✅ |
| `candidate_review` | ❌ | ❌ | ✅ |
| `quick_trial` | ❌ | ❌ | ✅ |
| `outline_analysis` | ✅ | ❌ | ✅ |
| `manuscript_analysis` | ✅ | ❌ | ✅ |

---

## 五、三级预算体系与超限行为

### 5.1 预算级别

| 级别 | budget_type | 配置粒度 | 拦截器方法 | 超限行为 |
|---|---|---|---|---|
| 作品初始化预算 | `initialization` | 单次初始化 max_tokens | `check_before_ai_job_start(job_type=ai_initialization)` | 拒绝启动初始化 Job；返回 `BudgetCheckResult(action=block)` |
| 单次自动续写预算 | `auto_queue` | 单次队列 max_tokens | `check_auto_queue_budget(run_id)` | 触发 P2-04 `StopCondition.BUDGET_EXCEEDED`；不删除已生成 CandidateDraft |
| 月度预算 | `monthly` | 每月 max_cost | `check_before_ai_job_start`（所有 job_type） | 拒绝启动新的 AIJob；已运行的 Job 允许当前 step 完成后停止 |

### 5.2 超限行为细化

#### 月度预算超限（`monthly`）

| 场景 | 行为 |
|---|---|
| 新 AIJob 启动 | BudgetGuard 返回 `action=block`，AIJobService 拒绝创建，返回 HTTP 402 |
| 已运行的 AIJob | 不强杀。当前 AgentStep 允许完成（已消费 token 不可回收），但不启动下一个 step。Job 进入 `paused`，`status_reason = budget_exceeded` |
| Quick Trial | 同样受月度预算约束。超限后拒绝启动 |
| 大纲辅助 / 选区改写 | 通过统一 BudgetGuard 检查，不单独豁免 |
| 用户恢复 | 用户可手动提高预算上限 → 恢复被暂停的 Job；或关闭预算检查（`enabled=false`）后恢复 |

> **HTTP 402 说明**：HTTP 402 为预算超限推荐状态码。若项目统一错误模型不使用 402，可映射为 `409 Conflict` 或 `422 Unprocessable Entity` + `error_code = "budget_exceeded"`，但 `error_code` 必须稳定为 `budget_exceeded`，以确保前端和 P2-04 StopConditionEvaluator 能统一识别。

#### 初始化预算超限（`initialization`）

| 场景 | 行为 |
|---|---|
| 启动初始化 | BudgetGuard 返回 `action=block`，InitializationWorkflow 拒绝启动 |
| 初始化进行中 | 在每章分析 step 前检查。超限时 `AIJobStep.status = paused`，`status_reason = budget_exceeded` |
| 恢复 | 用户可提高预算后 retry，或 skip 剩余章节 |

#### 自动续写预算超限（`auto_queue`）

| 场景 | 行为 |
|---|---|
| P2-04 每章完成后 | `StopConditionEvaluator.evaluate()` 内部调用 `budget_service.check_budget()` → 若超限则返回 StopCondition.BUDGET_EXCEEDED |
| 停止后 | AutoQueueRun → STOPPING → STOPPED，写入 StopRecord。**不删除已生成 CandidateDraft** |
| 恢复 | 用户提高预算后可继续队列（`POST /resume`） |

### 5.3 BudgetGuard 调用时机总结

```
1. AI 调用前（预检查）：
   → AIJobService.create_job() / start_job()
   → AgentRuntimeService.create_session()
   → AutoContinuationQueueService.start()
   → InitializationWorkflow.start()
   调用 BudgetGuard.check_before_ai_job_start(work_id, job_type)
   → action=block → 拒绝启动（402 / 422）

2. AI 调用后（事后检查）：
   → LLMCallLogger.record() 写入后
   → AgentRuntimeService.run_next_step() 完成后
   调用 BudgetGuard.check_after_llm_call(work_id)
   → alert_level=warning/exceeded → 触发前端告警通知

3. 自动续写队列每章完成后：
   → StopConditionEvaluator.evaluate()
   调用 BudgetGuard.check_auto_queue_budget(run_id)
   → action=stop_after_current_step → 触发 BUDGET_EXCEEDED 停止条件
```

---

## 六、领域模型

### 6.1 CostBudget

| 字段 | 类型 | 说明 |
|---|---|---|
| budget_id | str | 主键，格式 `bgt_{uuid_hex_12}`，服务端生成 |
| work_id | str | 作品 ID（`"global"` = 全局默认预算） |
| budget_type | str | `initialization` / `auto_queue` / `monthly` |
| budget_limit_tokens | int | Token 上限（0 = 不限） |
| budget_limit_cost | float | 成本上限（0.0 = 不限） |
| alert_threshold | float | 告警阈值（0.0~1.0，如 0.8 = 用量达 80% 时告警） |
| enabled | bool | 是否启用 |
| created_at | str | 创建时间（ISO 8601） |
| updated_at | str | 更新时间（ISO 8601） |

**`work_id = "global"` 语义**：
- 作为无作品级配置时的**全局默认预算**。
- 查询时优先按 `work_id = 具体作品ID` 匹配 → 无则 fallback 到 `work_id = "global"`。
- `UNIQUE(work_id, budget_type)` 确保同一作品的同一预算类型只有一条记录。

### 6.2 cost_budgets 表 DDL

```sql
CREATE TABLE IF NOT EXISTS cost_budgets (
    budget_id          TEXT PRIMARY KEY,
    work_id            TEXT NOT NULL DEFAULT 'global',  -- 'global' 或具体 work_id
    budget_type        TEXT NOT NULL CHECK(budget_type IN ('initialization','auto_queue','monthly')),
    budget_limit_tokens INTEGER DEFAULT 0,               -- 0 = 不限
    budget_limit_cost  REAL DEFAULT 0.0,                  -- 0.0 = 不限
    alert_threshold    REAL DEFAULT 0.8 CHECK(alert_threshold >= 0.0 AND alert_threshold <= 1.0),
    enabled            INTEGER DEFAULT 1,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cost_budgets_work_type
    ON cost_budgets(work_id, budget_type);

CREATE INDEX IF NOT EXISTS idx_cost_budgets_work
    ON cost_budgets(work_id);
```

### 6.3 CostSummary

```python
@dataclass
class ProviderCost:
    provider_name: str
    total_tokens: int
    total_cost: float
    call_count: int

@dataclass
class ModelCost:
    model_name: str
    total_tokens: int
    total_cost: float
    call_count: int

@dataclass
class RoleCost:
    model_role: str
    total_tokens: int
    total_cost: float
    call_count: int

@dataclass
class CostSummary:
    total_tokens: int
    total_cost: float
    call_count: int
    by_provider: dict[str, ProviderCost]
    by_model: dict[str, ModelCost]
    by_role: dict[str, RoleCost]
    # 注意：P2-S3 不含 adoption_rate。采纳率属于业务效果分析，归属分析看板（P2-10 或后续）。
```

### 6.4 CostDetail

```python
@dataclass
class CostDetail:
    record_id: str                 # llm_call_log request_id
    job_id: str                    # AIJob ID
    session_id: str                # AgentSession ID（如有）
    provider_name: str
    model_name: str
    model_role: str
    prompt_key: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    duration_ms: int
    status: str                    # succeeded / failed
    error_code: str
    started_at: str                # ISO 8601
    trace_id: str
```

### 6.5 BudgetCheckResult

```python
@dataclass
class BudgetCheckResult:
    allowed: bool                             # 是否允许继续
    budget_type: str = ""                     # 触发的预算类型
    budget_id: str = ""                       # 触发的预算 ID
    current_tokens: int = 0                   # 当前累计 token
    limit_tokens: int = 0                     # Token 上限
    current_cost: float = 0.0                 # 当前累计成本
    limit_cost: float = 0.0                   # 成本上限
    usage_ratio: float = 0.0                  # 用量比率（current/limit，取 token 和 cost 中较大的比率）
    alert_level: str = "normal"               # normal / warning / exceeded
    action: str = "allow"                     # allow / warn / block / stop_after_current_step
    message: str = ""                         # 人类可读消息
```

**`action` 取值与调用方行为**：

| action | 含义 | 触发条件 | 调用方行为 |
|---|---|---|---|
| `allow` | 允许 | 未超限且未触发告警阈值 | 正常执行 |
| `warn` | 允许但告警 | `usage_ratio >= alert_threshold` 但未超限 | 执行 + 前端展示告警 |
| `block` | 阻止 | 超限（初始化预算 / 月度预算） | 拒绝创建新 Job/Session（HTTP 402） |
| `stop_after_current_step` | 当前步完成后停止 | 超限（队列预算） | P2-04 触发 BUDGET_EXCEEDED；其他调用方在 step 完成后暂停 |

**`alert_level` 取值**：

| alert_level | 含义 |
|---|---|
| `normal` | 用量低于告警阈值 |
| `warning` | 用量超过告警阈值，但未超限 |
| `exceeded` | 用量已超限 |

---

## 七、告警状态与去重

### 7.1 告警策略

P2-09 **不持久化告警记录**，不新增 `cost_alerts` 表。

| 规则 | 说明 |
|---|---|
| 告警展示 | 前端实时展示当前预算用量进度条和告警状态（normal / warning / exceeded） |
| 不去重 | 不在后端做通知去重。前端自行控制告警提示频率（如一个 session 内同一预算类型只弹一次 toast） |
| 不推送 | 不通过 WebSocket / SSE / 系统通知推送告警。用户进入成本看板页面时主动刷新 |
| 事后审计 | 告警历史可通过 `check_budget` 调用日志（AgentTrace / 普通日志）事后回溯 |

### 7.2 前端告警展示规则

| 用量区间 | 进度条颜色 | 提示 |
|---|---|---|
| 0% ~ alert_threshold | 绿色 | 无 |
| alert_threshold ~ 100% | 黄色 | "用量已达 {percent}%，接近预算上限" |
| > 100% | 红色 | "预算已超限：{message}"，展示 `action_suggestion` 建议操作 |

---

## 八、聚合维度与时间范围

### 8.1 时间参数

| 参数 | 格式 | 默认值 | 说明 |
|---|---|---|---|
| `month` | `YYYY-MM`（ISO 8601 年月） | 当前月 | 按 `llm_call_logs.started_at` 前 7 位过滤（`substr(started_at, 1, 7)`） |
| 时区 | — | 系统默认（后端 `Asia/Shanghai`） | 前端传递的 month 已按用户本地时区截取，后端不做时区转换 |
| 不限时间 | 不传 `month` | — | 查询全部历史汇总 |

P2-S3 **不支持 `day` / `week` 粒度**。仅支持按月汇总和全部历史。

### 8.2 task_id 明确化

`get_task_cost` 的参数统一为三个互斥字段，不使用泛化的 `task_id`：

| 参数 | 类型 | 来源 |
|---|---|---|
| `job_id` | str | AIJob.id（P0-02） |
| `session_id` | str | AgentSession.id（P1-01） |
| `run_id` | str | AutoQueueRun.run_id（P2-04） |

优先级：`job_id` > `session_id` > `run_id`。至少传一个，否则返回空列表。

### 8.3 明细列表

```
GET /api/v2/ai/cost-dashboard/details?work_id=&job_id=&limit=50&offset=0
```

- 默认按 `started_at DESC` 排序。
- 支持分页（`limit` / `offset`）。
- 不限制时间范围（如需按月份过滤，传 `month` 到 summary 端点）。

---

## 九、API 设计

### 9.1 成本看板（只读聚合）

路由前缀：`/api/v2/ai/cost-dashboard`

```
GET  /api/v2/ai/cost-dashboard/summary?work_id=&month=
  Query:
    work_id  (required)  作品 ID
    month    (optional)  月度过滤，格式 YYYY-MM；不传则查询全部历史
  Response: { total_tokens, total_cost, call_count,
              by_provider: { provider_name: { total_tokens, total_cost, call_count } },
              by_model:    { model_name:    { total_tokens, total_cost, call_count } },
              by_role:     { model_role:    { total_tokens, total_cost, call_count } } }

GET  /api/v2/ai/cost-dashboard/details?work_id=&job_id=&session_id=&run_id=&limit=50&offset=0
  Query:
    work_id    (required)  作品 ID
    job_id     (optional)  AIJob ID
    session_id (optional)  AgentSession ID
    run_id     (optional)  AutoQueueRun ID
    limit      (optional)  每页条数，默认 50
    offset     (optional)  偏移量，默认 0
  Response: {
    records: [{ record_id, job_id, session_id, provider_name, model_name, model_role,
                prompt_key, input_tokens, output_tokens, total_tokens,
                estimated_cost, duration_ms, status, error_code, started_at, trace_id }],
    total: int, limit: int, offset: int
  }

GET  /api/v2/ai/cost-dashboard/task-cost?job_id=&session_id=&run_id=
  Query: (至少传一个)
    job_id     (optional)  AIJob ID
    session_id (optional)  AgentSession ID
    run_id     (optional)  AutoQueueRun ID
  Response: { records: [CostDetail] }
```

### 9.2 预算配置

路由前缀：`/api/v2/ai/cost-budget`

```
GET  /api/v2/ai/cost-budget?work_id=
  Response: { budgets: [{ budget_id, work_id, budget_type,
              budget_limit_tokens, budget_limit_cost, alert_threshold,
              enabled, created_at, updated_at }] }

PUT  /api/v2/ai/cost-budget
  Description: upsert（幂等写入）。首次配置不传 budget_id，服务端自动生成。
  Request:  { budget_id?, work_id, budget_type, budget_limit_tokens,
              budget_limit_cost, alert_threshold?, enabled? }
  Response: { budget_id, work_id, budget_type, ... }

DELETE /api/v2/ai/cost-budget/{budget_id}
  Response: 204 No Content

GET  /api/v2/ai/cost-budget/check?work_id=
  Description: 检查该作品所有预算状态。
  Response: { results: [{ allowed, budget_type, budget_id, current_tokens, limit_tokens,
              current_cost, limit_cost, usage_ratio, alert_level, action, message }] }

GET  /api/v2/ai/cost-budget/check?work_id=&job_type=
  Description: 检查该作品是否能启动指定类型的 AI 任务。
  Response: { allowed, budget_type, alert_level, action, message }
```

---

## 十、安全边界

| 约束 | 实施 |
|---|---|
| API Key 不入看板 | 聚合查询不关联 `ai_settings` 表 |
| 完整正文不入看板 | `LLMCallLog` 不存正文 |
| LLMCallLog 为唯一成本事实源 | 不另建 `cost_records` 表；AgentTrace 仅补充分组维度 |
| 成本事实只读 | `CostDashboardQueryService` 只有 SELECT |
| 预算配置可写 | `CostBudgetService` 写入 `cost_budgets` 表，不写成本事实 |
| 预算拦截只判断不执行 | `BudgetGuard` / `check_budget` 只返回结果，由调用方决定如何处理 |
| 告警不持久化 | 不在后端记录告警历史；前端自行控制展示频率 |

---

## 十一、前端 CostDashboard.vue 设计概要

### 11.1 页面定位

`CostDashboard.vue` 是成本看板主视图，作为独立路由页面（非 RightWorkspacePanel Tab），从设置导航或自动续写面板中的"成本"入口跳转进入。

### 11.2 主要区块

```
┌──────────────────────────────────────────────────────────┐
│  💰 AI 成本看板                                          │
│  ─────────────────────────────────────────────────────── │
│                                                          │
│  ┌──────┐ ┌──────┐ ┌──────┐                            │
│  │总Token│ │总成本│ │调用次数│   ← 汇总卡片行             │
│  │ 120K  │ │¥2.35 │ │  45  │                            │
│  └──────┘ └──────┘ └──────┘                            │
│                                                          │
│  ┌─ 月度筛选 ──────────────────────────────────────┐    │
│  │ [← 2025-06 →]                                    │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ 按角色分布 ─┐ ┌─ 按模型分布 ─┐ ┌─ 按 Provider ─┐   │
│  │ Kimi  60K   │ │ DeepSeek 80K │ │ deepseek 70K  │   │
│  │ DeepSeek 60K│ │ Kimi    40K  │ │ openai   45K  │   │
│  └─────────────┘ └──────────────┘ └───────────────┘   │
│                                                          │
│  ┌─ Token 消耗趋势（近 30 天）─────────────────────┐    │
│  │  📈 折线图 / 柱状图                               │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ 预算配置 ──────────────────────────────────────┐    │
│  │ 初始化:  [████████░░]🟡80%  200K/250K    [编辑]  │    │
│  │ 队列:    [██████░░░░]🟢60%  300K/500K    [编辑]  │    │
│  │ 月度:    [██████████]🔴超限 ¥5.20/¥5.00  [编辑]  │    │
│  │ 月度超限：新 AI 任务已暂停。 [提高预算] [关闭检查] │    │
│  │                                         [新建预算] │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ 调用明细 ──────────────────────────────────────┐    │
│  │ 时间        模型          角色    Token  成本 状态│    │
│  │ 06-09 14:30 deepseek-chat writer 3500  ¥0.02  ✅ │    │
│  │ 06-09 14:28 kimi-k2       planner 2100  ¥0.01  ✅ │    │
│  │ 06-09 14:25 deepseek-chat reviewer 1800 ¥0.01  ✅ │    │
│  │                              [加载更多...]         │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### 11.3 关键交互

| 交互 | 说明 |
|---|---|
| 月度切换 | 左右箭头切换月份，默认显示当前月 |
| 预算编辑 | 点击「编辑」弹出 Modal，修改 `budget_limit_tokens` / `budget_limit_cost` / `alert_threshold` |
| 新建预算 | 点击「新建预算」选择 `budget_type` 后弹出表单；首次配置走 `PUT` upsert |
| 告警提示 | 🟡 用量超过 `alert_threshold`，进度条变黄；🔴 超限变红，展示建议动作按钮 |
| 超限操作 | 月度超限：展示「提高预算」「关闭检查」按钮；初始化/队列超限：展示对应操作项 |
| 明细列表 | 分页加载，按 `started_at` 倒序 |

### 11.4 数据刷新

成本看板**不是实时面板**：
- 汇总数据进入页面时加载一次，切换月份时重新加载。
- 明细列表支持手动刷新和翻页。
- 预算配置编辑后即时更新（乐观更新 + 服务端确认）。
- 不启用 WebSocket / SSE 推送。
- 告警状态通过轮询 `/budget/check` 更新（可由 AutoQueuePanel 等面板按需调用）。

---

## 十二、代码改动面

```
新增：
  application/services/ai/cost_dashboard_query_service.py  # CostDashboardQueryService
  application/services/ai/cost_budget_service.py            # CostBudgetService
  application/services/ai/budget_guard.py                   # BudgetGuard
  domain/entities/ai/cost_entities.py                       # CostBudget, BudgetCheckResult, CostSummary, CostDetail
  domain/repositories/ai/cost_budget_repository.py          # CostBudgetRepository (ABC)
  infrastructure/persistence/sqlite_cost_budget_repo.py     # SqliteCostBudgetRepository
  presentation/api/routers/v2/ai/cost_dashboard.py          # /api/v2/ai/cost-dashboard/*
  presentation/api/routers/v2/ai/cost_budget.py             # /api/v2/ai/cost-budget/*
  frontend/src/views/CostDashboard.vue

需修改（P0 补字段）：
  domain/entities/ai/models.py                              # LLMCallLog 补 work_id, session_id, step_id, estimated_cost, price_snapshot_json
  application/services/ai/llm_call_logger.py                 # record() 计算 estimated_cost + 写入 price_snapshot_json
  domain/entities/ai/models.py                              # LLMUsage 补 estimated_cost, price_snapshot_json（若不放 LLMCallLog）

注册路由：
  presentation/api/app.py                                   # 注册 cost-dashboard + cost-budget 路由
```

### 不改动文件

```
application/services/v1/*          # V1 写作链路不受影响
application/services/ai/agent_workflow.py      # P1 不直接依赖 BudgetGuard
application/services/ai/agent_runtime_service.py  # P1 可注入 BudgetGuard，但非强制
```

---

## 附录：v1.1 → v1.2 变更摘要

| # | 变更 | 原因 |
|---|---|---|
| 1 | 服务拆分为 CostDashboardQueryService + CostBudgetService + BudgetGuard | 解决"只读聚合系统"与"预算可写"的语义冲突 |
| 2 | 新增 §2.1 LLMCallLog 最小字段依赖表 + 待补字段清单 | 明确数据源依赖，避免实现时发现字段缺失 |
| 3 | 新增 §3 成本计算规则 + price_snapshot_json | 定义 estimated_cost 来源，禁止用当前价格回算历史成本 |
| 4 | DDL 保留（§6.2），补充 `UNIQUE INDEX` | 与 P2-04~P2-08 的 DDL 规范对齐 |
| 5 | 新增 §5.3 BudgetGuard 调用时机矩阵 | 明确 check 的三个时机：AI 前/后/队列每章后 |
| 6 | §5.2 超限行为从语义描述细化为场景-行为对照表 | 月度/初始化/队列三种预算各自的精确行为 |
| 7 | 移除 adoption_rate | 采纳率需要 CandidateDraft/Suggestion 数据，不属于成本数据源 |
| 8 | §2.2 明确 AgentTrace 只补充分组、以 LLMCallLog 为准 | 避免两源数据不一致时的歧义 |
| 9 | §8 明确 month=YYYY-MM、task_id 拆为 job_id/session_id/run_id | 消除模糊参数定义 |
| 10 | §6.5 BudgetCheckResult 增加 allowed/alert_level/action 字段 | 对齐 BudgetGuard 实际需求 |
| 11 | §7 告警去重策略（不持久化，前端自行控制） | 避免过度设计 |
| 12 | 服务拆分使"看板"与"预算控制"边界清晰 | CostDashboardQueryService 承载业务规则约束解除 |
