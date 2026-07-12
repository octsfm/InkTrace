# InkTrace V2.0-P2-09 AI 用量与预算详细设计

版本：v1.3 / P2 模块级详细设计冻结版（普通作者人本化裁决）
状态：冻结生效
所属阶段：产品分期 P2-S3 / 开发计划执行批次 S4
设计范围：AI 用量与预计费用查询、预算保护、预算拦截、作者可读的状态与明细

依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`（R-AI-ENH-05）
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§4.9）
- `docs/07_overview/InkTrace-V2.0-概要设计说明书.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-02-AIJobSystem详细设计.md`（LLMCallLog）
- `docs/03_design/InkTrace-V2.0-P1-02-AgentWorkflow详细设计.md`（AgentTrace）
- `docs/03_design/InkTrace-V2.0-P2-04-自动续写队列详细设计.md`（AutoQueueConfig / StopCondition）
- `docs/03_design/InkTrace-V2.0-P2-11-API与前端集成边界详细设计.md`
- `docs/03_design/InkTrace-V2.0-P2-12-UI集成与交互设计说明书.md`
- `docs/03_design/InkTrace-DESIGN.md`（视觉 Token、作者语言、基础组件与可访问性）

> 冻结口径：页面面向普通小说作者，名称统一为“**AI 用量与预算**”。作者首先看到“花了多少、还剩多少、现在能不能继续”；Token、模型名称、模型服务等技术信息只在次级明细中出现。

---

## 一、定位、范围与硬边界

### 1.1 页面必须先回答的三个问题

1. 这个月的已知预计费用是多少？
2. 预算还剩多少？
3. 当前预算是“未到上限、接近上限、已到上限、没有保护，还是暂时无法确认”？

“预计费用”不是服务商账单。页面必须固定说明：

> 根据每次使用时保存的价格估算，可能与 AI 服务商的最终账单略有不同。

### 1.2 领域边界

| 能力 | 边界 |
|---|---|
| 成本事实 | `LLMCallLog` 是唯一权威源；不新建 `cost_records` |
| 成本查询 | 纯只读；不写事实、不调用 ModelRouter 或 Provider |
| 预算配置 | 受控写；不得写正文、CandidateDraft、StoryMemory 或正式资产 |
| 预算判断 | `BudgetGuard` 只返回判断；由 AIJob/Agent/AutoQueue 调用方执行 block/pause/stop |
| 用户采用状态 | 从 UserDecisionTrace/业务对象只读投影；不写回 LLMCallLog |
| 采用率 | 不在 P2-09 汇总；`adoption_rate` 归 P2-10 |

### 1.3 不得越过的确认门

- 预算调整不能替代 DirectionSelection、PlanConfirmation、HumanReviewGate 或 MemoryReviewGate。
- 提高或关闭预算后，不得自动恢复 Job、Session 或 AutoQueueRun；必须由用户回到原功能再次明确继续。
- BudgetGuard 不得伪造 `user_action`，不得自动 accept/reject/apply CandidateDraft。
- 已生成 CandidateDraft 在预算停止后必须保留，未 apply 不得进入正式正文。

---

## 二、成本事实、范围关联与采用状态

### 2.1 贯穿调用链的 LLMCallScope

所有会产生作品内容、分析结果或候选稿的生产模型调用，在进入 ModelRouter 前都必须由服务端创建并贯穿以下不可变上下文：

```python
@dataclass(frozen=True)
class LLMCallScope:
    work_id: str
    job_id: str
    session_id: str | None = None
    step_id: str | None = None
    run_id: str | None = None
    adoption_target_ref: str | None = None
```

- `work_id`、`job_id` 对所有作品级生产调用必填；`session_id/step_id/run_id` 在对应流程存在时必填。
- 会产出可由用户决定的结果时，必须在首次调用前预分配稳定的 `adoption_target_ref`；同一结果的 retry 共用它。Planner/Reviewer 等没有独立采用对象时为 `None`。
- Provider 连接测试属于 `diagnostic`，不创建作品内容，可无 work/job scope，且明确排除在作品预算与看板外。除该连接测试外，不得用“内部调用”绕过 scope。
- Scope 只保存引用，不保存完整 Prompt、ContextPack、正文或候选稿。

### 2.2 LLMCallLog 最小事实字段

| 字段 | 用途 | 冻结裁决 |
|---|---|---|
| `request_id` | 单次 Provider attempt 唯一标识 | 每次 retry 分别记录 |
| `work_id` / `job_id` | 作品与 AIJob 范围 | 新生产记录必填 |
| `session_id` / `step_id` / `run_id` | 精确执行范围 | 适用时由 LLMCallScope 直接写入 |
| `adoption_target_ref` | 关联可决策结果 | 适用时直接写入；不靠时间或文本猜测 |
| `trace_id` | 审计关系 | 只保存引用 |
| `prompt_key` / `model_role` | 功能和 AI 分工 | 内部聚合；界面只显示中文映射 |
| `provider_name` / `model_name` | 模型服务与模型名称 | 次级明细 |
| `provider_call_state` | `succeeded` / `failed` | 只要请求已发给 Provider 就必须留事实 |
| `usage_status` | `known` / `unknown` | 缺失不得伪造为 0 |
| `usage` | 输入/输出/总 AI 用量 | 仅 `usage_status=known` 时参与数值合计 |
| `estimated_cost` | 六位小数 Decimal 字符串或 null | 仅 `cost_status=known` 时可使用 |
| `cost_currency` | 本次费用币种或空字符串 | `cost_status=known` 时必填；实际账单必须使用账单币种 |
| `cost_status` | `known` / `unknown` | 区分真 0 与未知 |
| `cost_source` | `provider_reported` / `price_snapshot` / `unknown` | 说明费用依据 |
| `price_snapshot_json` | 调用前精确报价快照 | 有效报价或明确 unknown；不能替代实际账单币种 |
| `status` / `error_code` | 调用结果 | 界面不显示原始错误码 |
| `started_at` / `finished_at` | 时间与耗时 | ISO 8601 带时区 |
| `canonical_digest` | 不可变事实摘要 | 用于幂等与冲突检测 |

本地校验、门控、Prompt 构建等在请求发给 Provider **之前**失败时，只记录 `AIJobAttempt`，不创建 LLMCallLog，因此是可证明的零调用。请求一旦发出，usage 或账单信息缺失都属于 unknown，不能当作零。

### 2.3 权威存储、追加写与故障处置

1. SQLite `llm_call_logs` 是成本事实的唯一权威存储；现有 JSONL 降级为可选诊断/导出副本，查询与预算不得读取 JSONL 作为事实源。
2. 写入顺序为“SQLite insert-if-absent 提交 → 可选追加 JSONL”。禁止 `ON CONFLICT UPDATE` 覆盖成本字段。
3. `canonical_digest = SHA-256(JCS(canonical_fact))`；canonical_fact 覆盖 v2 表中除 `error_message` 外的全部不可变持久事实，包括 request/scope 引用与 scope_status、prompt/schema/context snapshot 引用、role/provider/model、provider_call_state/status/error_code、attempt_no、usage_status/unavailable_reason/三个用量值、费用状态/来源/规范化 Decimal/`cost_currency`/价格快照、elapsed_ms 与起止时间。它不含 Prompt、正文、JSONL/诊断元数据。相同 `request_id + canonical_digest` 重放幂等返回；相同 request_id 但摘要不同，报内部 `llm_call_log_conflict` 并保护性暂停后续预算调用。
4. Provider 已返回但 SQLite 事实写入失败时，返回 `P2_LLM_USAGE_AUDIT_FAILED`；对应 Job/Session 不得标 completed，返回结果不得生成 CandidateDraft 或进入正式资产链路，后续预算调用保持阻断直到修复。
5. `AIJobAttempt` 若显示 Provider 已发出但没有完整 LLMCallLog，预算完整度为 unknown。恢复任务先补写或人工处置该缺口，不得默认为未消费。
6. 上线迁移只允许一次性把历史 JSONL reconcile 到 SQLite：新事实可插入，完全相同可跳过，冲突记录进隔离报告；绝不覆盖 SQLite 既有事实。

JSONL 追加失败只写脱敏运维 warning，不回滚已经提交的 SQLite 权威事实，也不影响该结果继续；这与 SQLite 权威写失败的阻断语义严格区分。

### 2.4 存量记录与 AgentTrace

- `estimated_cost=0.0` 且 `price_snapshot_json={}` 的旧记录一律视为 `cost_status=unknown`，不得显示“¥0.00”或“免费”。
- 旧记录只有在“usage 完整 + 调用时价格快照完整”，或 Provider 明确返回实际费用时，才可迁为 `known`。
- work/job/run 只能通过不可变且唯一的 trace/session/step 关系补齐；无法唯一关联时标记 `scope_status=unknown`，不得猜测。
- AgentTrace 只补工作流、Agent 类型、阶段和旧范围关系，不替代 token、费用、模型、耗时等 LLMCallLog 事实。
- 删除所有“通过当前模型价格回算历史”的 fallback；历史价格未知就是未知。

### 2.5 用户采用状态

`CostDetail` 通过 `UserDecisionQueryPort.get_states(refs)` 批量读取逐条投影，但不汇总采用率：

| adoption_state | `user_adopted` | 作者文案 | 定义 |
|---|---:|---|---|
| `adopted` | `true` | 已实际使用 | 明确 apply 到目标或 convert 成正式后续任务 |
| `saved` | `null` | 已先留着 | 只有 accept，尚未 apply/convert；不得冒充已采用 |
| `not_adopted` | `false` | 已放弃 | 明确 reject/dismiss |
| `pending` | `null` | 待决定 | 有可决策结果但用户尚未决定 |
| `not_applicable` | `null` | 无需决定 | planner/reviewer 等无独立采用动作 |
| `unknown` | `null` | 记录不完整 | 历史关系不完整或不能唯一关联 |

采用状态不写回 LLMCallLog；`CostSummary`、趋势和预算判断均不计算 `adoption_rate`。

### 2.6 自动续写预算的唯一来源

- `auto_queue` 的唯一可编辑事实源是 P2-04 `AutoQueueConfig`：`budget_limit_tokens`、`budget_alert_threshold`、`stop_on_budget_exceeded`、`config_revision`。不得在 `cost_budgets` 保存第二份。
- `AutoQueueBudgetPolicyPort` 冻结为 `get_policy(work_id)` 与 `update_budget_fields(work_id, expected_revision, patch)`；写方法只从 `CostControlMutationUnitOfWorkPort.auto_queue_budget` 取得事务绑定实例，Adapter 只更新上述预算字段，不覆盖队列模式、目标章数等其他配置。
- P2-04 配置入口与 P2-09 预算入口复用同一用户门、幂等、审计与 `CostControlMutationUnitOfWorkPort`，保证配置和回执原子提交。
- RUNNING 期间使用 `AutoQueueRun.budget_policy_snapshot_json.current`。用户明确恢复预算暂停/停止时才读取最新 config，检查通过后替换 current 并把旧值追加到 history；保存预算本身绝不自动继续。

---

## 三、预计费用规则

### 3.1 调用时价格快照

每次调用完成时一次性写入不可变快照：

```json
{
  "input_price_per_1m": "2.000000",
  "output_price_per_1m": "8.000000",
  "currency": "CNY",
  "pricing_source": "provider_catalog",
  "captured_at": "2026-07-11T14:30:00+08:00"
}
```

金额与单价在 Domain/API 中统一使用 `Decimal`，API 序列化为最多六位小数的十进制字符串；禁止 float。SQLite 以规范化 TEXT 保存并在 Adapter 中用 Decimal 计算，旧 REAL 只允许通过十进制字符串迁移。舍入采用 `ROUND_HALF_UP` 到六位小数，界面展示可再按币种格式化，但不得反写事实。

### 3.2 价格来源与解析顺序

`PriceResolverService` 属 Application 层，依赖可替换 Port，不进入 Domain：

```python
@dataclass(frozen=True)
class PriceQuote:
    provider_name: str
    model_name: str
    currency: str
    input_price_per_1m: Decimal
    output_price_per_1m: Decimal
    pricing_source: Literal["provider_catalog", "manual_work", "manual_global"]
    captured_at: str
    official_pricing_url: str | None = None

@dataclass(frozen=True)
class ProviderBilling:
    amount: Decimal
    currency: str
    source: Literal["provider_reported"] = "provider_reported"

class ProviderPriceCatalogPort(Protocol):
    def find_quote(self, provider_name: str, model_name: str) -> PriceQuote | None: ...
    def official_pricing_url(self, provider_name: str) -> str | None: ...

class ModelPricePolicyRepository(Protocol):
    def find_exact(self, scope_type: str, work_id: str | None,
                   provider_name: str, model_name: str) -> ModelPricePolicy | None: ...
    def get_by_id(self, policy_id: str) -> ModelPricePolicy | None: ...
    def save(self, policy: ModelPricePolicy,
             expected_updated_at: str | None) -> ModelPricePolicy: ...

@dataclass(frozen=True)
class ResolvedModelBinding:
    work_id: str
    model_role: str
    provider_name: str
    model_name: str
    route_revision: str

@dataclass(frozen=True)
class WorkModelInventorySnapshot:
    routing_revision: str
    affected_work_ids: tuple[str, ...]
    bindings: tuple[ResolvedModelBinding, ...]

class WorkModelInventoryPort(Protocol):
    def capture_for_work(self, work_id: str) -> WorkModelInventorySnapshot: ...
    def capture_works_inheriting_global_price(
        self, provider_name: str, model_name: str
    ) -> WorkModelInventorySnapshot: ...
    def assert_revision(self, routing_revision: str) -> None: ...
```

冻结优先级：

1. 调用后若 `LLMResponse.billing` 明确给出本次实际费用与币种：`estimated_cost=billing.amount`、`cost_currency=billing.currency`、`cost_source=provider_reported`。此时调用前报价仍可留在 `price_snapshot_json` 供追溯，但查询和汇总绝不能拿报价币种覆盖实际账单币种。
2. 否则使用该 Provider attempt 调用前捕获的 `ProviderPriceCatalogPort` 官方精确 provider/model 报价。
3. 官方报价缺失时，使用作品级手动精确 provider/model 价格。
4. 再无则使用全局手动精确 provider/model 价格。
5. 仍无匹配则费用 unknown；禁止模糊匹配、跨模型套价或使用当前价格回算历史。

`ProviderPriceCatalogPort` 可以由本地受版本控制的官方目录 Adapter 实现，不允许 Domain 直接调用 Provider SDK。手动价格只影响保存之后的新调用；历史 unknown 永不回填。

`LLMResponse.billing` 是可选结构化载体。Provider Adapter 只有在上游明确返回本次账单金额与币种时才填；不得从余额变化、套餐或当前价猜测。调用前预算不能依赖尚不存在的实际费用，只能使用精确 resolved attempt 的 PriceQuote 做保守投影。

### 3.3 手动价格策略

```python
@dataclass(frozen=True)
class ModelPricePolicy:
    policy_id: str
    scope_type: Literal["global", "work"]
    work_id: str | None
    provider_name: str
    model_name: str
    currency: str
    input_price_per_1m: Decimal
    output_price_per_1m: Decimal
    enabled: bool
    inherit_global: bool
    updated_at: str
```

- 只允许 provider/model 精确匹配。作品记录 `inherit_global=true` 时恢复跟随全局；否则作品记录优先，`enabled=false` 表示该作品明确禁用此手动价格且不回退。global 记录不得设置 inherit_global。
- 单价允许真 0，但必须由用户明确保存并审计；空值不是 0。
- 正在启用的月度金额预算必须能为该作品当前模型解析到同币种价格。禁用/修改最后一个可用价格导致无法判断预算时，返回 422，不改变设置；用户可先关闭月度保护（需二次确认）再改。
- 设置入口固定为现有 SettingsCenter 的 `/settings?section=ai-cost`（作品上下文可追加 `work_id`），section 名称“AI 费用与预算”；其中手动价格子区叫“费用估算”，属于“更多设置”。输入标签为“每 100 万 AI 输入用量”“每 100 万 AI 输出用量”，并解释输入含 AI 阅读的内容、输出含 AI 生成的内容。
- 历史费用 unknown 的页面不能暗示补价格后会恢复；提示“新价格只用于之后的使用，过去缺失的费用不会倒算”。

“当前模型”不是由前端猜测：`WorkModelInventoryPort` 从版本化 ModelRoleConfig/AI Settings 读取作品所有可能进入生产路由的 primary/retry/fallback 精确 binding。作品级价格变更检查该作品；global 价格变更必须枚举仍继承该 global policy 且启用月度预算的全部受影响作品。服务在 proposed policy overlay 上模拟解析，任一当前 binding 缺价或币种不一致即返回 `422 P2_PRICE_REQUIRED_FOR_ACTIVE_BUDGET`，资源保持不变。

该交叉校验与预算/价格写受同一 `CostPolicyMutationCoordinator` 保护：先锁定 global 或 work scope，捕获 `routing_revision`，再在 CostControlMutation UoW 的一致读快照中读取受影响预算/价格并校验；提交前调用 `model_inventory.assert_revision()`。revision 变化时作品写返回对应 `P2_BUDGET_CONFLICT/P2_PRICE_CONFLICT`，global 写整体回滚，不允许部分作品生效。若 AI Settings 不是 SQLite 存储，其 Adapter 也必须使用同一协调锁与 revision 校验；不得用“先查文件、后无校验写 SQLite”的方式制造竞态。AI Settings 的模型路由变更同样走该协调器，不能把启用中的月度预算静默变成不可判断；真实 Provider attempt 仍会再次 fail-safe 门控。

### 3.4 known / unknown 与真零

`cost_status=known` 必须同时有非空 `cost_currency`，并满足以下之一：

1. usage 已知，输入/输出单价、币种、来源和捕获时间完整，可按快照计算；此时 `cost_currency=price_snapshot_json.currency`；或
2. Provider 明确返回本次实际费用及币种；此时 `cost_currency=LLMResponse.billing.currency`。

否则必须为 `unknown`，公开 API 的 `estimated_cost` 返回 `null`、`currency` 返回 `null`，权威行的 `cost_currency` 为空字符串。Provider 调用失败、usage 缺失、快照缺失或价格缺失都不能自动解释为 0。只有 Provider 明确报告 0 费用，或 usage 已知且调用时精确单价确为 0，才是 `known + "0.000000"`。

快照计算式：

```text
estimated_cost = max(input_tokens, 0) × input_price_per_1m / 1_000_000
               + max(output_tokens, 0) × output_price_per_1m / 1_000_000
```

### 3.5 历史不可回算

- 历史汇总只读已经捕获的费用事实。
- 当前模型价格变化不得覆盖、修补或回算旧记录。
- 旧记录未知时，页面显示“这次使用没有保留当时的价格，系统不会用现在的价格倒推”。

### 3.6 多币种

- CNY、USD 等币种不得直接相加。
- 汇总和趋势统一返回 `costs_by_currency: [{ currency, amount }]`。
- 只有一个币种时可显示单一金额；多个币种时分别显示，例如“¥2.35 + US$0.18”。
- 成本预算必须带 `currency`。适用范围内存在其他币种或未知费用时，成本预算判断为 `indeterminate`，不得按 0 继续放行。

### 3.7 完整度

费用完整度 `cost_completeness`：

| 值 | 定义 | 作者文案 |
|---|---|---|
| `complete` | 有调用且全部费用已知 | 显示预计费用 |
| `partial` | 部分费用未知 | “已知预计费用…，另有 N 次无法计算” |
| `unknown` | 有调用但全部费用未知 | “费用无法计算” |
| `empty` | 范围内无调用 | “这个月还没有使用过 AI 功能” |

用量完整度 `usage_completeness` 独立返回 `complete/partial/unknown/empty`，并带 `known_usage_call_count`、`unknown_usage_call_count`。token 预算只要适用范围出现 unknown usage 或“Provider 已发出但日志缺失”的 attempt，就为 indeterminate；不得用已知部分继续放行。

---

## 四、DDD + 清洁架构拆分

### 4.1 Domain Port

现有 `LLMCallLogRepository.append()` 是写 Port，只负责追加事实，不扩入查询职责。

新增 Port：

```python
class CostBudgetRepository(Protocol):
    def get_by_id(self, budget_id: str) -> BudgetPolicy | None: ...
    def find_by_scope(self, work_id: str,
                      budget_type: BudgetType) -> BudgetPolicy | None: ...
    def list_enabled_monthly(self, work_ids: tuple[str, ...]) -> list[BudgetPolicy]: ...
    def save(self, policy: BudgetPolicy,
             expected_updated_at: str | None) -> BudgetPolicy: ...

class LLMCallLogCostQueryPort(Protocol):
    def aggregate(self, filters: CostFactFilter, *, group_by: CostGroupBy) -> CostAggregate: ...
    def page(self, filters: CostFactFilter, *, limit: int, offset: int) -> CostDetailPage: ...
    def trend(self, filters: CostFactFilter, *, bucket: CostBucket,
              timezone: str) -> CostTrend: ...
    def usage(self, filters: CostFactFilter) -> CostUsage: ...

class UserDecisionQueryPort(Protocol):
    def get_states(self, refs: list[str]) -> dict[str, AdoptionState]: ...

class AutoQueueBudgetPolicyPort(Protocol):
    def get_policy(self, work_id: str) -> BudgetPolicy | None: ...
    def update_budget_fields(self, work_id: str, expected_revision: int,
                             patch: AutoQueueBudgetPatch) -> BudgetPolicy: ...

@dataclass(frozen=True)
class AutoQueueBudgetPatch:
    limit_tokens: int
    alert_threshold: Decimal
    enabled: bool

class TokenEstimatorPort(Protocol):
    def estimate_input_tokens(self, llm_request: LLMRequest,
                              resolved: "ResolvedModelAttempt") -> int: ...

class LLMCallLogReconciliationPort(Protocol):
    def reconcile(self, filters: CostFactFilter) -> UsageReconciliationResult: ...

class BudgetAuditPort(Protocol):
    def ensure_operation_trace(self, trace_id: str, work_id: str,
                               operation_ref: str,
                               workflow_type: str = "cost_control_settings") -> str: ...
    def append_pre_event(self, trace_ref: str, safe_event: BudgetAuditEvent) -> str: ...
    def append_post_event(self, trace_ref: str, safe_event: BudgetAuditEvent) -> str: ...

class CostPolicyMutationCoordinatorPort(Protocol):
    def lock(self, scope_keys: tuple[str, ...]) -> ContextManager[None]: ...

@dataclass(frozen=True)
class BudgetAuditEvent:
    event_key: str
    operation: str
    resource_ref: str
    user_id: str
    old_value_hash: str
    new_value_hash: str
    safe_summary: str

@dataclass(frozen=True)
class CostControlMutationReceipt:
    receipt_id: str
    key_hash: str
    request_fingerprint: str
    operation: str
    resource_kind: str
    resource_ref: str
    trace_id: str
    pre_event_ref: str
    post_event_ref: str | None
    old_value_hash: str
    new_value_hash: str
    safe_summary: str
    result_snapshot: dict
    audit_status: Literal["completed", "completion_pending"]
    created_at: str
    updated_at: str
    expires_at: str

class CostControlMutationReceiptWriter(Protocol):
    """只存在于同一 UoW 内，不是可独立提交的 Repository。"""
    def get_by_key_hash(self, key_hash: str) -> CostControlMutationReceipt | None: ...
    def insert_pending(self, receipt: CostControlMutationReceipt) -> None: ...
    def mark_completed(self, receipt_id: str, post_event_ref: str) -> None: ...

class CostControlMutationUnitOfWorkPort(Protocol):
    budgets: CostBudgetRepository
    prices: ModelPricePolicyRepository
    model_inventory: WorkModelInventoryPort
    auto_queue_budget: AutoQueueBudgetPolicyPort
    auto_queue_configs: AutoQueueConfigRepository
    receipts: CostControlMutationReceiptWriter
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

`CostBudgetRepository.save`、`ModelPricePolicyRepository.save`、`AutoQueueBudgetPolicyPort.update_budget_fields`、`AutoQueueConfigRepository.update_if_revision` 和 ReceiptWriter 的写方法只允许通过同一个 UoW 的事务绑定实例调用；普通依赖装配只暴露查询方法，禁止独立 commit。`model_inventory` 在 UoW 中只读并校验 routing revision，不保存 AI Settings；跨存储一致性由 `CostPolicyMutationCoordinatorPort` 的共享锁与 revision 复核保证。

`BudgetAuditPort` 的幂等键固定为 `trace_ref + event_key`：同键且规范化事件 payload 相同必须返回首次 `event_ref`，不得重复追加；同键但 payload 不同必须报审计冲突并停止，不得覆盖原事件。pre/post payload 都只包含上面的安全字段及其 hash。

`CostFactFilter` 规则：

- `work_id` 必填。
- 时间使用 `[start_at, end_at)` 半开区间。
- `job_id/session_id/run_id` 最多一个；details 允许零个或一个，task-cost 要求恰好一个。
- status/provider/model/role 可选。
- BudgetGate 也必须构造完整 CostFactFilter：monthly 使用 work_id + Asia/Shanghai 月窗；initialization/auto_queue 使用 work_id + 唯一 scope。任何 scope 都先校验属于 work_id，禁止只凭资源 ID 查询。

Infrastructure 提供 `SQLiteLLMCallLogCostQueryAdapter` 和 SQLite UoW Adapter。查询 Adapter 只能 SELECT，不得写库、读 API Key 或调用 ModelRouter/Provider。`ProviderPriceCatalogPort` 与 `ModelPricePolicyRepository` 见 §3.2；所有具体实现均在 Infrastructure。

### 4.2 Application Service

| 服务 | 职责 | 禁止 |
|---|---|---|
| `CostDashboardQueryService` | 编排成本查询 Port 和采用状态投影 | 写事实、查正文、调 Provider |
| `CostBudgetService` | 查询有效预算，执行预算受控变更，返回回执 | 修改 AIJob/Queue 状态 |
| `CostPricePolicyService` | 查询/保存/停用手动精确价格，复用用户门/UoW/审计 | 回算历史、修改 Provider 密钥配置 |
| `CostUsageReconciliationService` | 只凭持久化 Attempt/Provider 元数据/一致 JSONL 修复用量事实缺口并重查 | 猜测 usage、套当前价格、自动恢复任务 |
| `PriceResolverService` | 按冻结优先级解析本次价格并生成快照 | 回算历史、写业务资产 |
| `BudgetGateService` | 加载预算、用量、价格与投影，调用纯 Domain BudgetGuard | 自己发起 Provider 调用、伪造 user_action |
| `GuardedLLMExecutor` | 所有生产 ModelRouter 调用的唯一预算包装入口；门控→调用→事实落库→调用后门控 | 绕过 ModelRouter、返回未落日志的模型结果 |

`BudgetGuard` 是纯 Domain Service：

```python
BudgetGuard.evaluate(
    policy: BudgetPolicy,
    usage: CostUsage,
    projection: UsageProjection,
    phase: BudgetPhase,
    execution_kind: ExecutionKind,
) -> BudgetCheckResult
```

它不注入 Repository/Query Port/Provider，不读取时钟或环境，不持久化，也不改变 Job/Session/Run。`BudgetGateService` 才负责 I/O，并汇总为 `BudgetGateResult`。

`CostBudgetService` 对 `initialization/monthly` 使用 `CostBudgetRepository`，对 `auto_queue` 使用 `AutoQueueBudgetPolicyPort`；两者向 API 返回统一的 `BudgetPolicy`。`CostPricePolicyService` 使用 `ModelPricePolicyRepository`，与预算服务共用 CostControlMutation UoW/Audit，但二者不互相调用。

### 4.3 统一模型调用入口（不得旁路）

ModelRouter 仍拥有 model_role 路由、Provider retry 与 fallback 策略，但不能反向依赖 P2 成本领域类型。`ResolvedModelAttempt`、`AttemptGuardDecision`、`RoutedLLMResult` 与 `ProviderAttemptGuardPort` 下沉到 P0 Core 的 `application/ports/ai/provider_attempt_guard_port.py`；P2 只提供实现：

```python
class BudgetProviderAttemptGuard(ProviderAttemptGuardPort):
    def before_attempt(self, request: LLMRequest,
                       resolved: ResolvedModelAttempt) -> AttemptGuardDecision: ...
    def after_logged_attempt(self, resolved: ResolvedModelAttempt,
                             response: LLMResponse,
                             call_log: LLMCallLog) -> AttemptGuardDecision: ...
    def budget_result(self, decision_ref: str) -> BudgetGateResult: ...

@dataclass(frozen=True)
class GuardedLLMExecutionResult:
    response: LLMResponse
    call_log_ref: str
    after_gate: BudgetGateResult
    further_provider_calls_allowed: bool
```

生产路径调用 `GuardedLLMExecutor.execute(request, scope) -> GuardedLLMExecutionResult`；它构造带 scope 的 `BudgetProviderAttemptGuard`，再调用 `ModelRouter.generate(request, attempt_guard=guard) -> RoutedLLMResult`。Router 对首选、Provider retry 和 fallback 每次都按以下顺序执行：解析精确 provider/model → before_attempt 按该模型价格投影 → Provider 调用 → SQLite LLMCallLog 权威写 → after_logged_attempt → 决定返回或进入下一 attempt。每次 attempt 使用新 request_id，并单独计费/门控；fallback 绝不能沿用首选模型价格。

Core Router 只读取通用 `AttemptGuardDecision.may_proceed/control/reason_code/decision_ref`，不 import `BudgetGateResult`、BudgetGuard 或任何 P2 模块。`BudgetProviderAttemptGuard` 在内存中按 decision_ref 保存完整 BudgetGateResult；Router 返回后，由外层 GuardedLLMExecutor 取回并组装 GuardedLLMExecutionResult。decision_ref 只用于同进程控制关联，不写用户界面，也不得含预算值、Prompt 或正文。

`attempt_guard` 对所有生产 `generate` 必填，不能传 None；连接测试使用独立 `ModelRouter.test_connection()`，不进入生产 generate。Provider 已返回而权威日志失败时立即终止 retry/fallback，不把未记账结果交给调用方。

`after_logged_attempt` 是不可丢失的控制信号：

- `further_provider_calls_allowed` 只能由服务端按 Router 返回的通用 after decision 与对应 `after_gate.allowed` 交叉校验计算，调用方不得覆盖；两者不一致按 fail-safe false 并记录脱敏诊断。若为 false，Router 立即禁止 retry/fallback，Application 也禁止本 use case 后续 Reviewer、Rewriter 或下一章节的任何 Provider 调用。
- 不得仅因调用后超限/无法核算而抛弃已成功且已落权威日志的响应。调用方可继续完成本地 schema 校验；校验通过时把本 attempt 的结果安全保存为 CandidateDraft/result_ref，再按 `after_gate.action` 停止或暂停。它仍不得 apply 或写正式正文。
- 若当前响应本身无效，本地校验可以失败，但不得为“修复输出”再发 Provider 请求；任务按停止/暂停状态保留诊断引用。
- `after_gate` 为 warning/allow 时才可依照原流程进入后续 attempt/step；它不替代 HumanReviewGate、MemoryReviewGate 或其他业务门。

下列生产路径只允许调用 `GuardedLLMExecutor.execute(llm_request, llm_call_scope)`，不得直接调用 ModelRouter/Provider：

| 路径族 | 必须携带的范围 |
|---|---|
| 初始化、作品分析、重新分析 | work_id + job_id；有 step 时加 step_id |
| P0 续写、审稿、SelectionRewrite、作品内 Quick Trial | work_id + job_id；可决策结果加 adoption_target_ref |
| AgentRuntime Planner/Writer/Reviewer/Memory/Conflict | work_id + job_id + session_id + step_id；Writer 可加 adoption_target_ref |
| 多章续写与 AutoQueue 下游全部调用 | 上述字段 + run_id |
| OutlineAssist、Opening、StyleDNA 等 P2 助手 | work_id + job_id；适用时加 session/step/adoption_target_ref |

Provider 连接测试是唯一明确排除项：它只验证连接，不产生作品结果，不参与作品预算或成本看板；仍遵守现有安全日志规则。Application composition root 必须注入 GuardedLLMExecutor，禁止把预算依赖标为 optional。

### 4.4 依赖方向

```text
Presentation → Application Service → Domain Port/Domain Service
Infrastructure Adapter ─────────────→ Domain Port
```

Domain 不依赖 SQLite、FastAPI、Provider SDK 或前端 DTO。预算查询失败不得被 Presentation 层改写成 `ready/allowed`；Provider、价格目录和存储 Adapter 均可替换。

---

## 五、三级预算与判定规则

### 5.1 三类预算

| budget_type | 作者名称 | 唯一事实源 | 统计范围 | 上限 |
|---|---|---|---|---|
| `initialization` | 整理整本作品 | `cost_budgets` | 单个 initialization `job_id` | token |
| `auto_queue` | 一次自动续写 | P2-04 `AutoQueueConfig` | 单个 `AutoQueueRun.run_id` | token |
| `monthly` | 每月预计费用 | `cost_budgets` | `work_id` + Asia/Shanghai 自然月 | cost + currency |

界面把“每月预计费用”作为默认、最容易理解的保护；“整理整本作品”和“一次自动续写”的 AI 用量上限放入“更多保护”。每种类型只展示真正需要填写的一个上限，不把金额和 Token 两套字段同时丢给作者。“0 代表不限”只属于内部契约，界面用“预算保护已关闭”表达。

### 5.2 精确统计窗口

- `monthly`：`work_id` + Asia/Shanghai 月初到下月月初的半开区间。每次真实 Provider attempt 都计入；retry 不合并。
- `initialization`：只统计当前 `job_id`，不累计作品历次初始化。调用前按“已用实际 token + 本次 projected_tokens”检查，调用后按事实 usage 校正。
- `auto_queue`：只统计当前 `run_id` 下生成、审稿、修订和 retry 的全部调用，不跨 run。

### 5.3 服务端用量投影

客户端不得提交 `projected_tokens` 或 `projected_cost`。每次生产调用由 `GuardedLLMExecutor` 在服务端计算：

1. Router 先得到本 attempt 的 `ResolvedModelAttempt`；`TokenEstimatorPort` 再根据内存中的 Domain `LLMRequest` 和精确模型估算输入用量，估算内容不得写日志。
2. 每个预算保护下的 `LLMRequest.max_tokens` 必须由服务端确定且 `> 0`，不能让 Provider 使用无界默认值。
3. `projected_tokens = estimated_input_tokens + LLMRequest.max_tokens`；`UsageProjection.max_output_tokens` 是该字段的规范化副本。
4. 月度金额投影使用 `PriceResolverService.resolve_before_attempt(resolved)` 返回的精确价格和币种；价格缺失或与预算币种不一致则该月度判断为 indeterminate。
5. 调用前按“当前事实 + 本 attempt 投影”检查；调用并成功写入 LLMCallLog 后，再按真实 usage/cost 检查。Provider retry/fallback 进入下一 attempt 前重新解析、重新投影、重新门控。

边界冻结：真实调用前 `current + projection <= limit` 允许，只有 `> limit` 才阻止；当当前事实刚好等于上限时为 `at_limit`，`exceeded=false`，但所有生产调用的投影都为正，因此页面明确提示下一次调用会被阻止。提醒阈值在 `ratio >= alert_threshold` 时触发。

### 5.4 BudgetGateService 时机

```python
check_before_call(context: BudgetContext, request: LLMRequest) -> BudgetGateResult
check_after_call(context: BudgetContext, call_log: LLMCallLog) -> BudgetGateResult
check_current_status(context: BudgetContext) -> BudgetGateResult
```

- `check_current_status` 只看当前事实，供 GET 状态接口和页面使用，不能代替真实调用前投影。
- initialization 与 monthly 同时适用时返回全部 `results`；auto_queue 运行再叠加其 run 预算。不得只返回第一个而隐去其他状态。
- AutoQueue 每章完成后把 `BudgetGateResult` 交给 StopConditionEvaluator；Evaluator 不自行查询预算。

### 5.5 判定、动作与汇总

| 阶段 | determination | alert_level | action | 含义 |
|---|---|---|---|---|
| 任意 | `determined` | `normal` | `allow` | 无启用预算或未到提醒阈值 |
| 调用前 | `determined` | `warning` | `warn` | 接近上限，本次投影仍未超过 |
| 当前状态 | `determined` | `at_limit` | `block` | 当前事实刚好等于上限；不是已超额，但正数投影的新调用无法开始 |
| 调用前 | `determined` | `exceeded` | `block` | 当前事实加投影确定超过上限 |
| 调用后 | `determined` | `exceeded` | `stop_after_current_step` | AutoQueue 确定超限，当前安全小步后停止 |
| 调用后 | `determined` | `exceeded` | `pause_after_current_step` | 其他长流程确定超限，当前安全小步后暂停 |
| 调用前 | `indeterminate` | `unknown` | `block` | 保护事实或投影无法可靠核算 |
| 调用后 | `indeterminate` | `unknown` | `pause_after_current_step` | 已运行任务当前安全小步后暂停 |

无预算或预算 disabled 返回 `determined + allow + usage_ratio=null + reason_code=no_enabled_budget`。warning 不是 error，`allowed=true`。`indeterminate` 也不是 exceeded：原因只允许 `budget_usage_unknown`、`budget_price_unknown`、`budget_currency_mismatch`、`budget_check_failed`。

`BudgetGateResult` 先保留每类预算的独立结果，并分别计算 `has_determined_exceeded` 与 `has_indeterminate`；两者可同时为 true，unknown 不能抹掉另一条已经确定超限的事实。动作优先级：任一确定超限先按执行类型 block/pause/stop；仅在没有确定超限时，indeterminate 才按调用前 block/调用后 pause；否则 warning→warn，其余 allow。总体 determination 在存在任一 unknown 时仍为 indeterminate，供 UI 表达“还有一项无法确认”，但 `exceeded/has_determined_exceeded` 仍真实保留。`allowed` 只表示这次具体投影是否准入，不代表 Provider、模型配置或其他业务门控已 ready。

### 5.6 与状态机的映射

- 调用前确定超限：拒绝发起 Provider 请求，对外返回 `409 P2_BUDGET_EXCEEDED`。
- 调用后确定超限：本 attempt 已成功消费且权威日志已落库，不得改写成 409。同步用例在本地校验并保存出可交付 CandidateDraft/result 后，返回 `success`，或仅在还存在未完成子任务时返回 `partial_success`；`partial_success` 必须同时携带非空 `result_ref`、`budget_status` 与安全的 `next_action`。后台用例通过 200 状态查询返回 stopped/paused 及 result_ref/stop_record。
- 内部确定超限：`status_reason/stop_reason = budget_exceeded`。
- 仅 AutoQueue 的确定超限映射 `StopCondition.BUDGET_EXCEEDED`，流程 `RUNNING → STOPPING → STOPPED`。已在途 attempt 完成日志与本地校验后可保留其 CandidateDraft，但此后不得为本章 Reviewer/修订或下一章再发任何 Provider 调用。
- 用量/价格未知、币种不一致或查询失败：Job/Session/Run 进入既有 `paused/blocked` 安全路径，使用对应内部 reason；不得标成 BUDGET_EXCEEDED。
- 提高预算后只解除下一次准入阻断，不自动改变 paused/stopped 状态。

P2-04 v1.1 已同步：`StopEvaluationResult.should_pause` 默认 false。BudgetGateResult 为 indeterminate 时，Evaluator 返回 `should_stop=False, should_pause=True, condition=None`；AutoQueueService 转入既有 PAUSED，不创建 BUDGET_EXCEEDED StopRecord。确定超限仍走 `should_stop=True + StopCondition.BUDGET_EXCEEDED`。

### 5.7 用量缺口修复与无法修复时的出口

用户点击“重新检查并尝试修复”时，`CostUsageReconciliationService` 调用 `LLMCallLogReconciliationPort`：

1. 只修复“Provider 已发出但整条 SQLite LLMCallLog 缺失”的情况：从同 request_id 的持久化 AIJobAttempt、Provider 已保存的脱敏 usage 元数据或完整 JSONL 事实重建 canonical fact，并以 insert-if-absent 补整行。
2. 若同 request_id 已存在 `usage_status=unknown` 的不可变行，P2 不允许 update，也不新增暗中覆盖它的 correction；该行永久保持 unknown。JSONL digest 与既有行完全相同时也没有新增信息。此时返回 `resolved=false + remaining_unknown_count`，进入作者出口。
3. 找不到可重建完整行的确定证据时同样 unresolved；不得猜用量、套当前价格或把 unknown 改成 0。
4. 修复成功只解除“缺整行”问题，不自动恢复 Job/Session/Run；仍由用户回到原功能明确继续。
5. 无法修复时按范围给作者出口：月度金额保护可“等到下月重新统计”或二次确认关闭；初始化可“结束这次整理并重新开始”；AutoQueue 可“结束这次自动续写并重新开始”。若月度保护同时存在，结束单次任务不会消除本月 unknown，界面必须继续说明。
6. 可提供“导出安全诊断信息”，只含 request/trace hash、时间、错误码和版本，不含正文、Prompt、ContextPack、候选稿、API Key 或原始 ID 明文。

---

## 六、领域契约与持久化

### 6.1 枚举与查询值对象

以下均为 Domain 枚举，不得在 Router/前端自造近似字符串：

| 枚举 | 允许值 |
|---|---|
| `CostStatus` | known / unknown |
| `UsageStatus` | known / unknown |
| `ProviderCallState` | succeeded / failed |
| `CostSource` | provider_reported / price_snapshot / unknown |
| `ScopeStatus` | known / unknown |
| `CostCompleteness` / `UsageCompleteness` | complete / partial / unknown / empty |
| `HistoryCompleteness` | complete / retention_limited |
| `CostGroupBy` | provider / model / role / feature |
| `CostBucket` | day |
| `AdoptionState` | adopted / saved / not_adopted / pending / not_applicable / unknown |
| `BudgetType` | initialization / auto_queue / monthly |
| `BudgetDetermination` | determined / indeterminate |
| `BudgetAlertLevel` | normal / warning / at_limit / exceeded / unknown |
| `BudgetAction` | allow / warn / block / pause_after_current_step / stop_after_current_step |
| `BudgetPhase` | current_status / before_call / after_call |
| `ExecutionKind` | single_job / long_running_job / auto_queue |

```python
@dataclass(frozen=True)
class CostScope:
    scope_type: Literal["job", "session", "run"]
    scope_ref_id: str

@dataclass(frozen=True)
class CostFactFilter:
    work_id: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    scope: CostScope | None = None
    statuses: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()

@dataclass(frozen=True)
class CostUsage:
    known_tokens: int
    known_usage_call_count: int
    unknown_usage_call_count: int
    usage_completeness: UsageCompleteness
    costs_by_currency: list[CurrencyAmount]
    known_cost_call_count: int
    unknown_cost_call_count: int
    cost_completeness: CostCompleteness

@dataclass(frozen=True)
class CostAggregate:
    usage: CostUsage
    breakdowns: list[CostBreakdown]

@dataclass(frozen=True)
class CostTrendPoint:
    date: str
    usage: CostUsage

@dataclass(frozen=True)
class CostTrend:
    start_at: datetime
    end_at: datetime
    timezone: str
    bucket: CostBucket
    points: list[CostTrendPoint]

@dataclass(frozen=True)
class UsageReconciliationResult:
    resolved: bool
    repaired_count: int
    remaining_unknown_count: int
    next_actions: tuple[str, ...]
```

### 6.2 CostSummary

```python
@dataclass
class CurrencyAmount:
    currency: str
    amount: str  # 规范化 Decimal 字符串，最多六位小数

@dataclass
class CostBreakdown:
    key: str
    label: str
    known_tokens: int
    call_count: int
    costs_by_currency: list[CurrencyAmount]
    known_usage_call_count: int
    unknown_usage_call_count: int
    known_cost_call_count: int
    unknown_cost_call_count: int
    usage_completeness: str
    cost_completeness: str

@dataclass
class CostSummary:
    known_tokens: int
    call_count: int
    costs_by_currency: list[CurrencyAmount]
    known_usage_call_count: int
    unknown_usage_call_count: int
    known_cost_call_count: int
    unknown_cost_call_count: int
    usage_completeness: str
    cost_completeness: str
    history_completeness: str  # complete / retention_limited
    retention_start_at: str | None
    by_provider: list[CostBreakdown]
    by_model: list[CostBreakdown]
    by_role: list[CostBreakdown]
```

`known_tokens` 只合计 usage 已知的调用，必须与 unknown 计数并列展示；禁止把 unknown 当 0。`history_completeness=retention_limited` 时页面说明“这里只保留从 {date} 开始的记录”，不得标成完整历史。

### 6.3 CostDetail

```python
@dataclass
class CostDetail:
    record_id: str
    feature_label: str
    provider_name: str
    model_name: str
    model_role: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: str | None
    currency: str | None
    cost_status: str
    usage_status: str
    duration_ms: int
    status: str
    safe_status_message: str
    started_at: str
    user_adopted: bool | None
    adoption_state: str
    scope_status: str

@dataclass
class CostDetailPage:
    records: list[CostDetail]
    total: int
    limit: int
    offset: int
```

内部 ID 可用于 API 关联，但用户界面不得显示 record/job/session/run/trace/work/budget ID、原始 prompt_key 或 error_code。

### 6.4 BudgetPolicy 与作者输入提示

| 字段 | 说明 |
|---|---|
| `budget_id` | initialization/monthly 的内部 ID；界面不显示 |
| `work_id` | 作品或 `global` |
| `budget_type` | initialization / auto_queue / monthly |
| `limit_tokens` | token 类预算上限 |
| `limit_cost` / `currency` | monthly 预算上限；金额为 Decimal 字符串 |
| `alert_threshold` | 0.0~1.0；界面提供 70%/80%/90% 白话选项 |
| `enabled` | 是否启用 |
| `inherit_global` | 作品级记录是否恢复跟随全局；global/auto_queue 固定 false |
| `source` | `work` / `global` / `auto_queue_config` / `none` |
| `override_state` | `work_override` / `explicit_disabled` / `inherit_global` / `none` |
| `source_ref` | 继承的预算 ID/config revision；仅用于并发校验，界面不显示原值 |
| `updated_at` | 并发校验基线 |
| `usage_hint` | 可选：sample_count、recent_median_tokens、suggested_limit_tokens |

```python
@dataclass(frozen=True)
class BudgetPolicy:
    budget_id: str
    work_id: str
    budget_type: BudgetType
    limit_tokens: int | None
    limit_cost: Decimal | None
    currency: str | None
    alert_threshold: Decimal
    enabled: bool
    inherit_global: bool
    source: str
    override_state: str
    source_ref: str | None
    updated_at: str
    usage_hint: dict | None = None
```

有效预算解析顺序：无作品记录或作品记录 `inherit_global=true` 时读取 global；作品记录 `inherit_global=false` 时优先，哪怕 `enabled=false`，也表示“只对本作品关闭保护”而不回退。作者可用 PUT [改回默认设置] 把 inherit_global 设回 true，无需物理删除。

token 类上限在 UI 以“万 AI 用量”输入，提交时转为正整数 token。若同一范围最近最多 5 次完整记录存在，`usage_hint` 取中位数，建议值为 `median × 1.5` 后向上取整到 1000；必须标注“参考建议”，用户可改。没有完整历史时不猜默认值，只建议先完成一次操作或先使用月度金额保护。AI 用量包括读取和生成，不等于小说字数。

### 6.5 BudgetContext、BudgetCheckResult 与 BudgetGateResult

```python
@dataclass(frozen=True)
class BudgetContext:
    work_id: str
    job_type: str
    phase: BudgetPhase
    execution_kind: ExecutionKind
    job_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None

@dataclass(frozen=True)
class UsageProjection:
    input_tokens: int = 0
    max_output_tokens: int = 0
    projected_cost: CurrencyAmount | None = None

@dataclass
class BudgetCheckResult:
    allowed: bool
    exceeded: bool
    determination: BudgetDetermination
    budget_type: BudgetType
    scope_type: str
    scope_ref_id: str
    known_tokens: int
    unknown_usage_call_count: int
    projected_tokens: int
    limit_tokens: int
    costs_by_currency: list[CurrencyAmount]
    limit_cost: str | None
    currency: str | None
    usage_ratio: str | None  # Decimal 比例字符串
    alert_level: BudgetAlertLevel
    action: BudgetAction
    reason_code: str
    suggested_action: str
    message: str

@dataclass
class BudgetGateResult:
    allowed: bool
    exceeded: bool  # 兼容别名，等于 has_determined_exceeded
    has_determined_exceeded: bool
    has_indeterminate: bool
    determination: BudgetDetermination
    alert_level: BudgetAlertLevel
    action: BudgetAction
    reason_code: str
    results: list[BudgetCheckResult]
```

`exceeded` 为 P2-04 StopConditionEvaluator 的兼容属性；只有确定超限才为 true。`suggested_action` 只允许 `adjust_budget/check_price/align_currency/retry_budget_check/reconcile_usage/return_to_feature` 等冻结提示键，前端必须映射为中文，不得显示原值；禁止再使用未定义的 `action_suggestion`。

### 6.6 cost_budgets 与 model_price_policies

`cost_budgets` 只保存 initialization/monthly，auto_queue 不入此表：

```sql
CREATE TABLE IF NOT EXISTS cost_budgets (
    budget_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL DEFAULT 'global',
    budget_type TEXT NOT NULL CHECK(budget_type IN ('initialization','monthly')),
    budget_limit_tokens INTEGER NOT NULL DEFAULT 0,
    budget_limit_cost TEXT NOT NULL DEFAULT '0.000000',
    currency TEXT NOT NULL DEFAULT '',
    alert_threshold TEXT NOT NULL DEFAULT '0.8',
    enabled INTEGER NOT NULL DEFAULT 1,
    inherit_global INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(work_id, budget_type)
);

CREATE TABLE IF NOT EXISTS model_price_policies (
    policy_id TEXT PRIMARY KEY,
    scope_type TEXT NOT NULL CHECK(scope_type IN ('global','work')),
    work_id TEXT NOT NULL DEFAULT 'global',
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    currency TEXT NOT NULL,
    input_price_per_1m TEXT NOT NULL,
    output_price_per_1m TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    inherit_global INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(scope_type, work_id, provider_name, model_name)
);
```

- enabled 的 initialization 必须 `budget_limit_tokens > 0`。
- enabled 的 monthly 必须 `budget_limit_cost > 0` 且 currency 非空。
- P2 不提供物理删除预算 API；关闭保护使用 `enabled=false`，保留恢复和审计能力。
- global 与 auto_queue 记录禁止 inherit_global；作品级预算/手动价格允许 `inherit_global=true` 恢复跟随默认设置，保留原记录和审计。
- SQLite Adapter 必须把 TEXT 解析为 Decimal 后校验：金额/单价非负；alert_threshold 在 `(0,1]`。禁止 SQL/float 近似比较承担领域判断。

### 6.7 成本控制幂等回执

预算、价格和 AutoQueue 预算字段共用持久化回执，由 `CostControlMutationUnitOfWorkPort` 与目标资源在同一 SQLite 事务内写入。不得以独立 ReceiptRepository 分步保存。

```sql
CREATE TABLE IF NOT EXISTS cost_control_mutation_receipts (
    receipt_id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    request_fingerprint TEXT NOT NULL,
    operation TEXT NOT NULL,
    resource_kind TEXT NOT NULL,
    resource_ref TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    pre_event_ref TEXT NOT NULL,
    post_event_ref TEXT,
    old_value_hash TEXT NOT NULL,
    new_value_hash TEXT NOT NULL,
    safe_summary TEXT NOT NULL,
    result_snapshot_json TEXT NOT NULL,
    audit_status TEXT NOT NULL CHECK(audit_status IN ('completed','completion_pending')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
```

`key_hash` 使用单向 SHA-256；result snapshot 只含可安全重放的设置结果。回执至少保留 365 天，过期清理不得早于相应写操作审计的安全保留要求。任何字段都不得含 API Key、Prompt、ContextPack、正文、候选稿、原始 decision_note 或原始 Idempotency-Key。

### 6.8 llm_call_logs v2 权威表与重建迁移

冻结目标结构（旧表的 `estimated_cost REAL` 不再作为最终结构）：

```sql
CREATE TABLE llm_call_logs_v2 (
    request_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL DEFAULT '',
    job_id TEXT NOT NULL DEFAULT '',
    trace_id TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    step_id TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    adoption_target_ref TEXT NOT NULL DEFAULT '',
    scope_status TEXT NOT NULL CHECK(scope_status IN ('known','unknown')),
    prompt_key TEXT NOT NULL DEFAULT '',
    prompt_version TEXT NOT NULL DEFAULT '',
    model_role TEXT NOT NULL DEFAULT '',
    provider_name TEXT NOT NULL DEFAULT '',
    model_name TEXT NOT NULL DEFAULT '',
    provider_call_state TEXT NOT NULL CHECK(provider_call_state IN ('succeeded','failed')),
    status TEXT NOT NULL,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    attempt_no INTEGER NOT NULL DEFAULT 1,
    usage_status TEXT NOT NULL CHECK(usage_status IN ('known','unknown')),
    usage_unavailable_reason TEXT NOT NULL DEFAULT '',
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost TEXT,
    cost_currency TEXT NOT NULL DEFAULT '',
    cost_status TEXT NOT NULL CHECK(cost_status IN ('known','unknown')),
    cost_source TEXT NOT NULL CHECK(cost_source IN ('provider_reported','price_snapshot','unknown')),
    price_snapshot_json TEXT NOT NULL DEFAULT '{}',
    context_pack_snapshot_id TEXT NOT NULL DEFAULT '',
    output_schema_key TEXT NOT NULL DEFAULT '',
    canonical_digest TEXT NOT NULL,
    elapsed_ms INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    CHECK(
        (cost_status = 'known' AND estimated_cost IS NOT NULL AND cost_currency <> '')
        OR
        (cost_status = 'unknown' AND estimated_cost IS NULL AND cost_currency = '')
    )
);

CREATE INDEX idx_llm_cost_work_time ON llm_call_logs(work_id, started_at);
CREATE INDEX idx_llm_cost_work_job ON llm_call_logs(work_id, job_id);
CREATE INDEX idx_llm_cost_work_session ON llm_call_logs(work_id, session_id);
CREATE INDEX idx_llm_cost_work_run ON llm_call_logs(work_id, run_id);
CREATE INDEX idx_llm_cost_adoption ON llm_call_logs(adoption_target_ref);
CREATE INDEX idx_llm_cost_trace ON llm_call_logs(trace_id);
```

SQLite 迁移必须在维护事务/文件锁内执行：

1. 将旧表只读备份为 `llm_call_logs_legacy_backup`，创建 v2 临时表；不直接 ALTER REAL→TEXT。
2. 由迁移 Adapter 逐行规范化：旧金额用 `Decimal(str(value))` 转六位字符串；空快照旧 0 为 cost unknown/null；旧 `cost_status=known` 仅在快照含有效 currency 时把它迁入 `cost_currency`，否则降为 unknown/null，绝不猜币种；usage 任一必需值缺失为 usage unknown；无法唯一补 work/job/run 的 scope_status=unknown，禁止猜测。
3. 计算 canonical_digest 后 insert；校验总行数、request_id 唯一性、已知/未知计数与金额抽样。任一校验失败整体回滚，旧表保持权威。
4. 校验通过后原子交换表名，再创建索引；新 Store 改为 SQLite 先提交的 insert-if-absent。相同 digest 返回既有行，不同 digest 写安全冲突隔离记录并 fail-safe，永不 UPDATE 原行。
5. 最后执行一次 JSONL→SQLite reconcile：只补整行缺失；既有 request_id 相同 digest 跳过，不同 digest 隔离。备份表需经人工验收和至少一个发布周期后才可清理。

新生产记录由 Application 强制 work_id/job_id 非空；DDL 的空默认仅为承载无法补齐的历史行，并必须配 `scope_status=unknown`。

---

## 七、成本控制写入的用户门、幂等与审计

### 7.1 强制用户门

所有预算和手动价格变更，包括 P2-04 旧 auto queue 配置入口中的预算字段，必须同时满足：

- `caller_type=user_action`
- `user_action=true`
- 非空 `user_id`
- 非空 `Idempotency-Key`
- 预算保存 `confirm_budget_change=true`；手动价格保存 `confirm_price_change=true + confirm_manual_price_source=true`
- 禁用预算保护时额外 `confirm_disable=true`

Agent、workflow、system 调用一律 403。普通保存不弹二次确认；点击保存本身就是明确确认。关闭预算保护必须二次确认。任何保存只改变设置，不得自动创建/恢复 AIJob、AgentSession 或 AutoQueueRun。

### 7.2 请求指纹

指纹包含：operation、资源自然键、全部规范化新值、`user_id`、规范化 decision_note。不得包含 request_id、trace_id 或原始 Idempotency-Key。

- 同 key + 同指纹：返回首次回执，不重复写。
- 同 key + 不同指纹：`409 P2_IDEMPOTENCY_CONFLICT`。
- 更新必须携带 `expected_updated_at`（AutoQueue 使用 `expected_config_revision`）；基线变化返回 409，不覆盖另一窗口的新设置。
- 从 global 默认预算创建作品级覆盖时，请求还必须携带 `inherited_from_budget_id + inherited_from_updated_at`；默认设置已变化则返回 `409 P2_BUDGET_CONFLICT`，先刷新再决定。
- 创建/恢复作品级手动价格继承时同理携带 `inherited_from_policy_id + inherited_from_updated_at`；全局价格已变化返回 `409 P2_PRICE_CONFLICT`。

### 7.3 审计顺序

1. 校验用户门、参数、幂等回放和并发基线。
2. `BudgetAuditPort` 适配现有 `AgentTraceService.ensure_operation_trace(trace_id, work_id, operation_ref, workflow_type="cost_control_settings")`；无需伪造 AgentSession。
3. 写入最小化 pre `user_decision_recorded` 审计事件并取得 `pre_event_ref`。失败返回 `503 P2_BUDGET_AUDIT_WRITE_FAILED`，任何设置不得改变。
4. 在一个 `CostControlMutationUnitOfWorkPort` 事务中写目标预算/价格/完整 AutoQueueConfig 和 `audit_status=completion_pending` 的回执；任一步失败全部回滚。
5. 事务提交后，以 receipt_id 派生的确定性事件键写 post 审计；成功取得 `post_event_ref` 后，开启一个新的短事务，只调用事务绑定 ReceiptWriter 的 `mark_completed(receipt_id, post_event_ref)`，再提交。该短事务绝不再次保存预算、价格或 AutoQueueConfig。
6. 若 post 事件追加或 `mark_completed` 失败，资源已经保存，响应不得谎称资源写入失败或重复写；回执保持 `completion_pending`，返回首次结果与 `audit_completion_pending=true`。相同 key 重放先读取首次 result snapshot，只幂等取得/补写同一个 post event，再用新的短事务补 `completed`；不得再次改变资源。即使 post 事件已经存在但上次状态提交失败，也依靠 `trace_ref + event_key + payload` 返回原 `event_ref`，不会产生重复事件。

数据库枚举固定保存 `completed/completion_pending`；API 布尔值只按 `audit_completion_pending = (audit_status == "completion_pending")` 计算，不把布尔名称写入表。

审计只记录 user_id、资源引用、操作、旧值/新值 hash 和安全摘要；不得记录 API Key、完整 Prompt、ContextPack、正文、候选稿、完整价格目录或原始幂等键。

---

## 八、查询时间与参数

### 8.1 月份

- API `month` 格式 `YYYY-MM`；不传表示全部历史。
- UI 默认当前月，并且必须显式传当前 month，避免“默认当前月/默认全部”歧义。
- 后端按 Asia/Shanghai 把月份转换为 `[月初, 下月月初)`；不得用字符串前 7 位直接截取带时区时间。
- 全部历史受 P0-02 保留策略影响，响应必须返回 `history_completeness` 与 `retention_start_at`，不得把已清理前的数据说成完整历史。

### 8.2 任务范围

`details` 允许 `job_id/session_id/run_id` 零个或一个：零个表示查看所选时间内全作品明细。`task-cost` 必须恰好一个：

- task-cost 都不传：`400 P2_COST_SCOPE_REQUIRED`
- 任一接口传多个：`422 P2_COST_SCOPE_CONFLICT`
- 目标不存在或不属于 work_id：`404 P2_COST_SCOPE_NOT_FOUND`，避免跨作品枚举

### 8.3 分页

- details 默认 `started_at DESC`。
- `limit` 默认 50，范围 1~100；`offset >= 0`。
- details 支持与 summary 相同的 `month`，切换月份后不得混入其他月份。

### 8.4 趋势日期

- `from`、`to` 是用户看到的**包含首尾两天**的 `YYYY-MM-DD`。
- 后端以 Asia/Shanghai 转换为 `[from 00:00, to + 1 day 00:00)`；`from > to` 拒绝。
- 最多 366 个自然日。页面选中月份时传该月首日和末日，不使用滚动 30 天混入相邻月份。

---

## 九、API 冻结

所有响应沿用 P0-11 通用 envelope。以下只列 `data`。

### 9.1 AI 用量查询（只读）

```text
GET /api/v2/ai/cost-dashboard/summary?work_id=&month=
  → CostSummary

GET /api/v2/ai/cost-dashboard/trend?work_id=&from=&to=&granularity=day
  → {
      range: { from, to, timezone: "Asia/Shanghai", granularity: "day" },
      history_completeness, retention_start_at,
      points: [{
        date, known_tokens, call_count, costs_by_currency,
        known_usage_call_count, unknown_usage_call_count,
        known_cost_call_count, unknown_cost_call_count,
        usage_completeness, cost_completeness
      }]
    }

GET /api/v2/ai/cost-dashboard/details?work_id=&month=&job_id=&session_id=&run_id=&limit=50&offset=0
  → { records: [CostDetail], total, limit, offset,
      history_completeness, retention_start_at }

GET /api/v2/ai/cost-dashboard/task-cost?work_id=&job_id=&session_id=&run_id=
  → { records: [CostDetail], summary: CostSummary,
      history_completeness, retention_start_at }
```

趋势规则：P2 只支持 day；from/to 都不传时默认最近 30 个自然日，传时必须同时传；最大 366 天。真正无调用的缺失日期可补 empty 零点；有调用但 usage/费用未知时不得补成 0，也不能跨币种相加。页面切换月份时必须传所选月起止日期。

### 9.2 预算保护

```text
GET /api/v2/ai/cost-budget?work_id=
  → { budgets: [BudgetPolicy] }

PUT /api/v2/ai/cost-budget
  Headers: Idempotency-Key
  Request: {
    budget_id?, work_id, budget_type,
    limit_tokens?, limit_cost?, currency?, alert_threshold?, enabled,
    expected_updated_at?, expected_config_revision?,
    inherited_from_budget_id?, inherited_from_updated_at?, inherit_global?,
    caller_type, user_action, user_id,
    confirm_budget_change, confirm_disable?, decision_note?
  }
  → { budget: BudgetPolicy, receipt_id, audit_completion_pending }

GET /api/v2/ai/cost-budget/check?work_id=&job_type=&job_id=&session_id=&run_id=
  → BudgetGateResult（只表示当前事实，不接收客户端投影）

POST /api/v2/ai/cost-budget/reconcile-usage
  Headers: Idempotency-Key
  Request: { work_id, job_id?, session_id?, run_id?, user_id,
             caller_type: "user_action", user_action: true }
  → { resolved, repaired_count, remaining_unknown_count,
      next_actions: [wait_next_month/close_monthly_budget/restart_job/restart_auto_queue/export_safe_diagnostics] }
```

P2 不提供 DELETE。恢复保护走 PUT `enabled=true`，关闭保护走 PUT `enabled=false + confirm_disable=true`；作品级“改回默认设置”走 PUT `inherit_global=true`，是普通保存，不等于关闭保护。

### 9.3 费用估算设置

```text
GET /api/v2/ai/cost-prices?work_id=&provider_name=&model_name=
  → {
      effective_quote?, official_quote?, manual_policy?,
      effective_source, official_pricing_url?, future_only: true
    }

PUT /api/v2/ai/cost-prices
  Headers: Idempotency-Key
  Request: {
    policy_id?, scope_type, work_id?, provider_name, model_name,
    currency, input_price_per_1m, output_price_per_1m, enabled,
    expected_updated_at?, inherit_global?,
    inherited_from_policy_id?, inherited_from_updated_at?,
    caller_type, user_action, user_id,
    confirm_price_change, confirm_manual_price_source,
    decision_note?
  }
  → { price_policy: ModelPricePolicy, receipt_id, audit_completion_pending }
```

不提供 DELETE；禁用或恢复全局继承都走 PUT。价格只接受非负 Decimal 字符串和精确 provider/model，保存后只影响新调用。读取和编辑入口固定为 `/settings?section=ai-cost`。

### 9.4 Feature Flag

`enable_cost_dashboard` 只控制 AI 用量看板入口和 `/cost-dashboard/*` 只读查询。false 时该组路由返回 `503 P2_FEATURE_DISABLED`，前端隐藏作品内看板入口。

预算门控不受看板开关影响：已启用预算始终继续保护所有生产调用；`/cost-budget` 与 `/cost-prices` 必须保留在 SettingsCenter 可读写，避免用户在看板关闭时无法调整已生效保护。历史查看不要求当前 Provider 或 API Key 已配置。

---

## 十、错误码

| 错误码 | HTTP | 语义 |
|---|---:|---|
| `P2_BUDGET_EXCEEDED` | 409 | 调用前确定新 attempt 会超过用户设置的预算上限 |
| `P2_BUDGET_USAGE_UNKNOWN` | 409 | 预算用量无法可靠核算，保护性暂停/阻止 |
| `P2_BUDGET_PRICE_UNKNOWN` | 409 | 启用金额预算但本次价格无法解析 |
| `P2_BUDGET_CURRENCY_MISMATCH` | 409 | 调用价格币种与启用金额预算不一致 |
| `P2_BUDGET_CHECK_FAILED` | 503 | 预算查询失败，可重试 |
| `P2_BUDGET_NOT_FOUND` | 404 | 预算不存在或不属于作品 |
| `P2_BUDGET_VALIDATION_FAILED` | 422 | 上限、币种或阈值不合法 |
| `P2_BUDGET_CHANGE_CONFIRMATION_REQUIRED` | 400 | 缺少保存确认，或关闭保护时缺少二次确认 |
| `P2_BUDGET_CONFLICT` | 409 | expected_updated_at 已过期 |
| `P2_BUDGET_AUDIT_WRITE_FAILED` | 503 | 写前审计失败，预算未改变 |
| `P2_PRICE_VALIDATION_FAILED` | 422 | 价格、币种或 provider/model 不合法 |
| `P2_PRICE_CONFLICT` | 409 | 价格设置基线已过期 |
| `P2_PRICE_REQUIRED_FOR_ACTIVE_BUDGET` | 422 | 变更会使启用中的月度保护无法判断 |
| `P2_PRICE_SOURCE_CONFIRMATION_REQUIRED` | 400 | 手填价格前未确认已按官方来源核对及误差影响 |
| `P2_COST_SCOPE_REQUIRED` | 400 | 缺少 job/session/run 范围 |
| `P2_COST_SCOPE_CONFLICT` | 422 | 同时提供多个任务范围 |
| `P2_COST_SCOPE_NOT_FOUND` | 404 | 任务范围不存在或不属于作品 |
| `P2_COST_RANGE_INVALID` | 422 | 时间范围非法或超过 366 天 |
| `P2_COST_QUERY_FAILED` | 503 | 只读成本查询失败 |
| `P2_CALLER_FORBIDDEN` | 403 | 非用户调用预算写端点 |
| `P2_USER_ACTION_REQUIRED` | 403 | user_action 不是 true |
| `P2_IDEMPOTENCY_KEY_REQUIRED` | 400 | 缺少幂等键 |
| `P2_IDEMPOTENCY_CONFLICT` | 409 | 同一幂等键对应不同请求 |
| `P2_LLM_USAGE_AUDIT_FAILED` | 503 | Provider 结果的用量事实未能安全落库；结果不得进入候选/正式链路 |
| `P2_USAGE_RECONCILE_FAILED` | 503 | 用量缺口修复服务失败，原 unknown 与暂停状态保持 |

公开 API 不返回裸 `budget_exceeded`；它只作为内部 stop/status reason。warning 通过成功响应的 `alert_level=warning` 表达，不使用错误码。

---

## 十一、作者界面冻结

### 11.1 信息层级

页面按以下顺序：

1. 标题“AI 用量与预算”、作品名、更新时间、刷新按钮。
2. 月份切换。
3. 当前月的三个首要答案：“本月预计费用”“本月费用预算还剩”“本月预算状态”。第三张卡只说“目前未到上限/接近上限/已到上限/未设置保护/暂时无法确认”；GET 没有下一次调用投影，禁止说“可以开始新操作”，更不得承诺 Provider 和其他门控已就绪。
4. 切到历史月份后，三卡改为“{YYYY 年 M 月}预计费用 / AI 用量 / 使用次数”；历史预算没有版本快照，不显示“当月剩余预算”。
5. “预算保护”。
6. “用量趋势”。
7. 默认折叠的“费用花在哪里”（模型分工/模型名称/模型服务）。
8. 默认折叠的“查看使用明细”。

页面不以 Provider、Model、Token 开场。用户主动展开后，严格按 `InkTrace-DESIGN.md` 映射为“模型服务”“模型名称”“模型分工”“AI 用量”。

预算保护区始终显示**当前有效设置**，并明确标注“只影响现在和之后的 AI 操作”；即使用户正在查看历史月份，也不得把当前预算与历史费用描述成同一个时期。顶部“预算还剩”只指 monthly；initialization/auto_queue 分别在预算保护区展示，禁止把三种不同单位强行合成一个剩余额度。

### 11.2 预算名称与设置

| 内部类型 | 作者名称 | 说明 |
|---|---|---|
| initialization | 整理整本作品 | 导入或重新分析整本作品时最多使用多少 AI 用量 |
| auto_queue | 一次自动续写 | 一次自动续写最多使用多少 AI 用量 |
| monthly | 每月预计费用 | 这本作品每月最多预计花费多少 |

提醒阈值用“提前一些（70%）/一般（80%）/快到上限时（90%）”。保存前说明：

> 达到上限后，新的 AI 操作会暂停，已经生成的内容不会删除。

预算写入等待服务端确认后再更新页面，不做乐观覆盖。失败时保留原设置并显示“预算没有保存成功，原来的设置还在”。

- 月度金额表单优先展示，币种由当前可解析价格提供且仍可选择；当前模型存在缺价或多币种时，明确说明“暂时不能用一个金额准确保护全部 AI 使用”，引导“完善费用信息”或改用“更多保护”中的 AI 用量上限，不静默选择币种。
- token 类表单以“万 AI 用量”展示，说明“包括 AI 阅读和生成的内容，不等于小说字数”。有 `usage_hint` 时展示“最近一次通常约…，参考上限…”；无历史时不填猜测值。
- `source=work` 显示“这本作品的设置”，同时提供 [改回默认设置]；`source=global` 显示“默认设置”，作品页只提供 [为这本作品单独设置]，不得直接编辑全局值。两种切换都回传继承基线并保留审计，不物理删除。
- SettingsCenter 带 `work_id` 时顶部固定写“正在设置：{作品名}”；不带 work_id 才进入“所有作品的默认设置”，显示常驻说明“会影响所有仍在使用默认设置的作品”，保存按钮明确叫“保存默认设置”。不得靠用户猜测当前范围。
- 预算并发冲突时服务端最新值立即回填，页面保留用户尚未保存的草稿，焦点移到提示：“预算刚刚在别处改过，已刷新最新设置。请看一眼后再保存。”不得自动用草稿覆盖最新值。

### 11.3 状态文案

| 场景 | 冻结文案 |
|---|---|
| 接近月度上限 | “这个月已经用了 {percent}%，快到你设置的上限了。真正开始下一次 AI 操作时，系统会再检查这次预计用量。” |
| 月度正常 | “目前还没有到你设置的费用上限。真正开始下一次 AI 操作时，系统会再按那次预计用量检查。” |
| 月度刚好到上限 | “这个月刚好用到你设置的费用上限。还没有超出，但新的 AI 操作需要先调整预算。” |
| 月度超限 | “这个月已经到你设置的费用上限。新的 AI 操作先停一下；已经开始的这次 AI 操作会先完成，之后不再继续。” |
| 接近队列上限 | “这次自动续写已经用了 {percent}%，快到你设置的上限了。” |
| 队列超限 | “这次自动续写已在当前章节完成后停下，已经生成的候选稿都还在。” |
| 接近整理作品上限 | “这次整理作品已经用了 {percent}%，快到你设置的上限了。” |
| 整理作品超限 | “整理作品已暂停，已经完成的结果会保留。” |
| 当前月费用记录不完整 | “这个月有些使用没有留下完整费用。为了避免继续增加费用，新的 AI 操作先停一下；你的写作内容不受影响。” |
| 新调用缺少价格 | “这个 AI 模型还没有可用的费用信息，所以暂时不能判断金额预算。”按钮“完善费用信息” |
| 费用币种不一致 | “这本作品使用的 AI 有不同费用单位，当前月度金额上限暂时无法准确比较。”按钮“调整月度预算/AI 设置”“继续保持暂停”；关闭月度保护需二次确认 |
| 预算查询失败 | “预算状态暂时没有加载出来。新的 AI 操作先停一下，请稍后重新检查。” |
| 未设置预算 | “目前没有设置预算保护。你仍可使用 AI，但系统不会在费用接近上限时替你停下。” |
| 预算保护已关闭 | “这项预算保护已关闭。AI 使用不会受这个上限限制。” |
| 预算已提高 | “预算已更新。请回到刚才的 AI 功能，确认后继续。” |

自动续写明确继续后，若新预算检查通过，页面提示“已按新的预算继续”；若仍不通过，提示“新的预算仍不够完成下一步，自动续写还保持停止”，不得出现保存后立即反复启停。

用量 unknown 的主按钮为“重新检查并尝试修复”。若仍无法修复，不得无限只给重试：按 §5.7 显示“等到下月/结束并重新开始/关闭对应保护（需确认）/导出安全诊断信息”等适用出口，并明确已有写作内容不会丢失。

从被预算拦住的功能进入设置时，前端创建 `BudgetReturnContext`（allowlist route_name、work_id、可选 job/session/run ref、中文 feature_label、focus_target），存于 sessionStorage 并只在同作品使用；禁止接受任意 return URL。设置页固定显示 [返回{中文功能名}]，回到原面板/任务并聚焦“继续/重试”按钮，但绝不自动点击。直接打开设置或 return context 失效时只显示 [返回写作]，不得使用含糊的“回到刚才”。ReturnContext 不写预算回执或日志，不含正文/Prompt/Key。

关闭预算保护二次确认：

> 关闭预算保护后，AI 功能将不再受这个上限限制，可能产生更多费用。确定要关闭吗？

### 11.4 空态、失败与未知费用

- 无记录：当前月显示“这个月还没有使用过 AI 功能”，历史月显示“{YYYY 年 M 月}没有 AI 使用记录”；费用/趋势区显示空态，但预算保护区仍显示并可预先设置。
- 无预算：“还没有设置预算。设置后，系统会在接近上限时提醒你。”并提供“设置预算”。
- 加载失败：“AI 用量暂时没有加载出来，你的写作内容不受影响。”并提供“重新加载”。
- 刷新时保留旧数据并显示“正在更新用量”，不让页面闪空。
- 费用 unknown 显示“费用无法计算”，绝不显示 0 元或免费。
- 历史缺价只说明“过去的费用不会用现在的价格倒算”；不显示“补价格即可恢复”。当前月因此无法判断金额预算时，提供“等待下月重新开始统计”与需二次确认的“关闭月度金额保护”，不诱导误操作。
- 当前或未来模型缺价时才显示“完善费用信息”，进入 `/settings?section=ai-cost`。预算查询失败只显示“重新检查”，不能混用价格入口。

### 11.5 费用估算设置

SettingsCenter “AI 费用与预算”同时保留预算保护入口；带 work_id 编辑该作品，不带 work_id 编辑所有作品默认值并常驻提示影响范围。“费用估算”子区默认折叠在“更多设置”中，只在官方价格缺失时引导作者填写：

1. 选择模型服务和模型名称（从现有模型配置读取，不手输内部 ID）。
2. 优先显示 Adapter 维护的 allowlist HTTPS [查看官方价格说明]；不接受用户输入跳转网址。没有可信官方链接时提示“不要猜价格，可先不用月度金额保护”。
3. 按官方页面选择币种，填“每 100 万 AI 输入用量”和“每 100 万 AI 输出用量”；显示最近一次完整用量的只读估算预览，帮助发现小数点/单位错误，但不写回历史。
4. 保存区固定提示“新价格只用于之后的使用，过去缺失的费用不会倒算；填错会让预计费用和金额预算不准确”，并要求勾选“我已按官方价格说明核对”。
5. 保存走真实 user_action、幂等和审计；关闭手动价格不物理删除。作者找不到可靠价格时，主操作是“暂不手填”，不是催促猜一个数字。

价格并发冲突时与预算一致：刷新最新服务端值、保留未保存草稿并聚焦 alert：“费用信息刚刚在别处改过，已刷新最新设置。请核对后再保存。”不得自动重放旧草稿。

官方精确报价存在时优先展示只读说明，不要求小白重复填写。页面不暴露 provider SDK、price snapshot、per-token 算式或 API Key。

### 11.6 明细展示边界

允许显示：中文功能名、模型名称、模型服务、模型分工、输入/输出/总 AI 用量、耗时、时间、成功/失败安全文案、单次预计费用、采用状态。

不得显示：record/job/session/run/trace/work/budget ID、原始 prompt_key/error_code、price_snapshot_json、pricing_source、caller_type、user_action、idempotency_key、HTTP 状态码或内部 action/status 枚举。

### 11.7 无障碍与窄屏

- 标题使用明确 h1/h2 层级；月份按钮有“上一个月/下一个月”可读名称。
- 进度条同时提供文字百分比和具体用量，不能只靠红黄绿；`role=progressbar`，`aria-valuemin=0`、`aria-valuemax=100`、`aria-valuenow=min(percent,100)`，`aria-valuetext` 读真实结果，例如“已用 120%，超过上限 20%”。
- `usage_ratio=null` 时不渲染 progressbar，也绝不播报 0%；改用 `role=status` 或阻断时 `role=alert` 的“暂时无法确认用量”文字。
- 趋势图同时提供文字摘要或可访问数据表。
- Modal 打开后圈定焦点，支持 Esc 关闭，关闭后焦点回原按钮；所有操作支持键盘和清晰焦点框。
- Modal/Drawer 有未保存输入时，Esc、关闭按钮和遮罩点击先提示“还有未保存的修改，确定离开吗？”；选择继续编辑返回原字段，确认离开才丢弃草稿。
- 字段错误通过 `aria-describedby` 关联到对应输入；校验失败聚焦第一个无效字段，保存/并发失败聚焦页面内 alert。
- 加载与保存成功使用 `aria-live=polite`；超限、阻断和保存失败使用 `role=alert`/assertive。Toast 不能是唯一反馈。
- 窄屏卡片纵向排列；明细使用逐条卡片或明确可滚动表格；操作目标不小于约 44px。

---

## 十二、代码改动面与测试门槛

### 12.1 预期改动面

```text
application/ports/ai/provider_attempt_guard_port.py      # P0 Core 通用门控 Port/DTO
domain/entities/ai/cost_entities.py
domain/entities/ai/models.py                         # LLMCallLog 补 job/run/cost status/source
domain/services/ai/budget_guard.py                   # 预算核心规则的 Domain Service
domain/repositories/ai/llm_call_log_cost_query_port.py
domain/repositories/ai/llm_call_log_reconciliation_port.py
domain/repositories/ai/cost_budget_repository.py
domain/repositories/ai/user_decision_query_port.py
domain/repositories/ai/auto_queue_budget_policy_port.py
domain/repositories/ai/provider_price_catalog_port.py
domain/repositories/ai/model_price_policy_repository.py
domain/repositories/ai/work_model_inventory_port.py
domain/repositories/ai/cost_policy_mutation_coordinator_port.py
domain/repositories/ai/cost_control_mutation_uow_port.py
domain/repositories/ai/budget_audit_port.py
domain/repositories/ai/token_estimator_port.py
application/services/ai/cost_dashboard_query_service.py
application/services/ai/cost_budget_service.py
application/services/ai/cost_price_policy_service.py
application/services/ai/cost_usage_reconciliation_service.py
application/services/ai/price_resolver_service.py
application/services/ai/budget_gate_service.py
application/services/ai/budget_provider_attempt_guard.py
application/services/ai/guarded_llm_executor.py
application/services/ai/model_router.py                    # 必需 attempt guard + resolved attempt
application/services/ai/llm_call_logger.py
application/services/ai/stop_condition_evaluator.py      # 区分 exceeded 与 indeterminate
application/services/ai/auto_queue_service.py            # indeterminate 走既有 PAUSED
infrastructure/persistence/sqlite_llm_call_log_cost_query_adapter.py
infrastructure/persistence/sqlite_llm_call_log_reconciliation_adapter.py
infrastructure/database/repositories/ai/file_llm_call_log_store.py # SQLite first, JSONL optional replica
infrastructure/persistence/sqlite_cost_budget_repo.py
infrastructure/persistence/sqlite_model_price_policy_repo.py
infrastructure/persistence/sqlite_cost_control_mutation_uow.py
infrastructure/persistence/ai_settings_work_model_inventory_adapter.py
infrastructure/locking/cost_policy_mutation_coordinator.py
infrastructure/ai/pricing/provider_price_catalog_adapter.py
infrastructure/ai/tokenization/model_token_estimator_adapter.py
infrastructure/ai/audit/agent_trace_budget_audit_adapter.py
presentation/api/routers/v2/ai/cost_dashboard.py
presentation/api/routers/v2/ai/cost_budget.py
presentation/api/routers/v2/ai/cost_prices.py
frontend/src/views/CostDashboard.vue
frontend/src/stores/useCostDashboardStore.js
frontend/src/stores/useCostBudgetStore.js
frontend/src/stores/useAICostSettingsStore.js
frontend/src/components/settings/AICostSettings.vue
```

此外，所有生产模型调用的 Application Service/Composition Root 都需把直接 ModelRouter 调用替换为 `GuardedLLMExecutor` 注入；只改一个 Agent 或一个 Router 不算完成。auto_queue 预算只通过 Adapter 修改既有 AutoQueueConfig，不新增第二份表。

### 12.2 TDD 最小矩阵

| 类型 | 必测 |
|---|---|
| 正常 | 单币种完整费用、价格解析优先级、三类预算正常/提醒/超限、趋势补空日、采用状态投影 |
| 错误 | 查询/价格/审计失败、并发与继承基线冲突、global 价格影响作品校验失败、模型路由 revision 竞态、幂等冲突、无效月份/范围、日志冲突 |
| 边界 | 真 0、旧 0 unknown、本地失败零调用、Provider 已发出 usage 缺失、实际账单币种覆盖报价币种、混币种、等于上限、月末时区、366 天、retry 分别计入 |
| 权限/门控 | agent/system 写设置 403；缺 user_action/user_id/key/确认均拒绝；提高预算不自动恢复；所有生产路径经过 GuardedLLMExecutor |
| 原子/恢复 | pre audit 失败不写；资源+receipt 同事务；post 失败返回 completion_pending；post 已存在但 mark_completed 失败时同 key 只补状态、不重复事件/资源 |
| 日志安全 | SQLite insert-only；相同摘要幂等、不同摘要冲突；落库失败不产 CandidateDraft；JSONL 失败不影响权威事实 |
| Feature Flag | 看板关闭时历史入口隐藏，但预算继续执行且预算/价格设置仍可访问 |
| 保留 | 当前月和活跃 job/run 不被清理；全历史受限时返回 retention_limited |
| 前端/无障碍 | 月份语义、global/work 徽标、冲突草稿保留、万用量换算、progressbar/Modal/aria-live |
| 安全红线 | 不读/记录完整正文、Prompt、ContextPack、Key、候选稿；不写正式资产；BudgetGuard 纯判断 |
| 回归 | P2-04 `BUDGET_EXCEEDED` 只接确定超限；after_gate 阻止任何后续 Provider 调用但保留已落日志的有效 CandidateDraft/result_ref；unknown/check_failed 只 pause；P0/P1 门控语义不变 |

实现必须先写失败测试，再写最小实现，再重构；相关后端、前端、构建与 CI 关键检查必须通过后才可宣称完成。

---

## 附录：v1.2 → v1.3 变更摘要

| # | 变更 | 原因 |
|---|---|---|
| 1 | 候选冻结升级为冻结生效，页面改名“AI 用量与预算” | 面向普通小说作者 |
| 2 | 删除当前价格回算 fallback；增加 known/unknown 和完整度 | 防止把未知费用当 0 |
| 3 | 汇总改为 `costs_by_currency` | 不跨币种错误相加 |
| 4 | 恢复逐条采用状态，仍不计算 adoption_rate | 对齐上位需求并保持子域边界 |
| 5 | 新增独立只读 LLMCallLog Cost Query Port | 保持命令/查询职责和清洁架构 |
| 6 | 补 trend API、details month 和严格 task scope | 关闭 UI/API 契约缺口 |
| 7 | auto_queue 预算复用 P2-04 AutoQueueConfig | 消除双事实源 |
| 8 | 统一 BudgetGuard 与 StopCondition 的确定/不确定映射 | blocked 不伪装 ready，unknown 不伪装 exceeded |
| 9 | 仅调用前准入拒绝固定 `409 P2_BUDGET_EXCEEDED`；调用后用 success/带 result_ref 的 partial_success/后台状态，内部保留 `budget_exceeded` | 不把已完成且已记账的 attempt 伪装成失败 |
| 10 | 预算写加入 user_action、幂等、并发和审计门；移除物理 DELETE | 防误触、防越权、可恢复 |
| 11 | 重排页面信息层级并冻结白话文案、空态与无障碍要求 | 降低普通作者理解成本 |
| 12 | 新增 LLMCallScope、usage 完整度和 SQLite 追加写故障规则 | 让 job/run/采用关系可追溯，未知不冒充零 |
| 13 | 拆分 Application BudgetGateService 与纯 Domain BudgetGuard，并冻结统一 GuardedLLMExecutor | 落实 DDD/Clean 并堵住模型调用旁路 |
| 14 | 冻结手动价格实体、解析优先级、设置页和未来生效语义 | 让小白可恢复费用估算且不篡改历史 |
| 15 | 预算/价格/AutoQueue 配置共用原子 UoW、操作 Trace 与 completion_pending 回放 | 关闭崩溃窗口和双写风险 |
| 16 | 看板 flag 只控制看板，预算保护与设置始终可用 | 防止关闭入口后用户被既有预算锁住 |
| 17 | 接入 P0-02 retention 完整度和当前月/活跃范围保护 | 避免清理任务破坏预算判断 |
