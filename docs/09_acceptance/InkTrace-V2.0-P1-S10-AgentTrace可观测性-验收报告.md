# InkTrace V2.0 P1-S10 AgentTrace 与可观测性 — 验收报告

版本：v1.0（初验）
验收日期：2026-05-22
依据文档：`docs/03_design/InkTrace-V2.0-P1-10-AgentTrace与可观测性详细设计.md`（16 条验收项）
对应开发计划：`docs/04_plan/InkTrace-V2.0-P1-开发计划.md` §5.11

---

## 一、验收总体结论

**判定：通过 ✅ — 遵循设计文档实现，核心能力完整。**

7 个专属测试全部通过。数据模型、事件记录、脱敏安全、降级策略、告警方向均已落地。存在 2 个设计要求的"全量事件类型枚举"和"独立 Metrics/Alerts 存储"未完全覆盖（见问题清单），但不影响核心 Trace 功能。

**建议进入 P1-S11a（API 集成边界落地）。**

---

## 二、数据模型逐项对照

### 2.1 AgentTrace（Session 级视图，设计 §4.2 行 83-96）

| 设计字段 | 代码 (`models.py:478-497`) | 状态 |
|---|---|---|
| `trace_id` / `session_id` | ✅ | ✅ |
| `workflow_type` / `agent_sequence` | ✅ | ✅ |
| `total_steps` / `result_summary` / `result_refs` | ✅ (`result_ref_ids`) | ✅ |
| `total_elapsed_ms` / `total_tokens` | ✅ | ✅ |
| `warning_codes` | ✅ | ✅ |

**Session 层全部字段落地。** ✅

### 2.2 AgentTraceEvent（设计 §5.2 行 133-147）

| 设计字段 | 代码 (`models.py:500-513`) | 状态 |
|---|---|---|
| `event_id` / `trace_id` / `session_id` / `step_id` | ✅ | ✅ |
| `event_type` (enum) / `event_stage` (enum) | ✅ (`event_type: str` + `event_stage: TraceEventStage`) | ✅ |
| `event_time` / `level` / `summary` | ✅ | ✅ |
| `safe_refs` / `payload_digest` | ✅ | ✅ |
| `request_id` / `correlation_id` | ✅ | ✅ |

**全部 13 字段落地。** ✅

### 2.3 AgentStepTrace（设计 §5.3 行 150-164）

| 设计字段 | 代码 (`models.py:516-529`) | 状态 |
|---|---|---|
| `step_trace_id` / `trace_id` / `step_id` | ✅ | ✅ |
| `agent_type` / `action` / `attempt_no` | ✅ | ✅ |
| `status` / `started_at` / `ended_at` | ✅ | ✅ |
| `duration_ms` / `warning_codes` / `error_code` | ✅ | ✅ |

**全部 12 字段落地。** ✅

### 2.4 ToolCallTrace（设计 §5.4 行 167-182）

| 设计字段 | 代码 (`models.py:532-544`) | 状态 |
|---|---|---|
| `tool_trace_id` / `trace_id` / `step_id` | ✅ | ✅ |
| `tool_name` / `caller_type` / `side_effect_level` | ✅ | ✅ |
| `permission_result` (allow/deny/conditional_allow) | ✅ (`ToolPermissionResult`) | ✅ |
| `call_status` (started/succeeded/failed/timeout/cancelled/ignored_late_result) | ✅ (`ToolCallTraceStatus`) | ✅ |
| `duration_ms` / `error_code` | ✅ | ✅ |
| `safe_input_digest` / `safe_output_digest` | ✅ | ✅ |
| `tool_audit_log_ref` | ❌ 缺失字段 | ⚠️ |

**12/13 字段落地（缺 `tool_audit_log_ref`）。**

### 2.5 ObservationTrace（设计 §5.5 行 185-197）

| 设计字段 | 代码 (`models.py:548-558`) | 状态 |
|---|---|---|
| `observation_trace_id` / `trace_id` / `step_id` | ✅ | ✅ |
| `observation_type` / `decision_hint` / `decision_source` | ✅ | ✅ |
| `is_blocking` / `warning_codes` / `summary` / `safe_refs` | ✅ | ✅ |

**全部 10 字段落地。** ✅

### 2.6 LLMCallTraceView（设计 §5.6 行 200-214）

| 设计字段 | 代码 (`models.py:561-573`) | 状态 |
|---|---|---|
| `llm_call_log_ref` / `trace_id` / `step_id` | ✅ | ✅ |
| `prompt_ref` / `model_role` / `provider` / `model` | ✅ | ✅ |
| `context_pack_ref` / `output_schema_key` | ✅ | ✅ |
| `token_count` / `elapsed_ms` / `content_hash` | ✅ | ✅ |

**全部 12 字段落地。LLMCallLog 为真源，Trace 仅做关联投影。** ✅

### 2.7 UserDecisionTrace（设计 §5.7 行 217-228）

| 设计字段 | 代码 (`models.py:576-586`) | 状态 |
|---|---|---|
| `decision_trace_id` / `trace_id` / `session_id` | ✅ | ✅ |
| `decision_type` (11 种) / `target_entity_type` / `target_entity_id` | ✅ | ✅ |
| `decided_by` / `decision_note` / `decided_at` | ✅ | ✅ |

**全部 9 字段落地。** ✅

---

## 三、枚举值对照

| 枚举 | 设计值 | 代码 | 状态 |
|---|---|---|---|
| `TraceLevel` | info/warning/error/critical | `INFO/WARNING/ERROR/CRITICAL` | ✅ |
| `TraceEventStage` | perception/planning/action/observation/orchestration/audit | 全部 6 个 | ✅ |
| `AgentTraceStatus` | running/waiting_for_user/completed/partial_success/failed/cancelled | 全部 6 个 | ✅ |
| `ToolPermissionResult` | allow/deny/conditional_allow | 全部 3 个 | ✅ |
| `ToolCallTraceStatus` | started/succeeded/failed/timeout/cancelled/ignored_late_result | 全部 6 个 | ✅ |
| `TraceAlertScope` | step/session/workflow/system | 全部 4 个 | ✅ |
| `TraceAlertType` | timeout_spike/failure_spike/blocked_spike/retry_exhausted/queue_backlog/audit_write_failed | 全部 6 个 | ✅ |
| `TraceAlertStatus` | open/acknowledged/resolved/muted | 全部 4 个 | ✅ |

---

## 四、安全红线逐条对照

| # | 设计规则 | 代码实现 | 状态 |
|---|---|---|---|
| 1 | 不记录完整 Prompt/ContextPack/正文/API Key | `safe_refs` + `payload_digest` 仅含脱敏摘要，无完整正文字段 | ✅ |
| 2 | 只记录 safe_ref/content_ref/excerpt 与摘要 | `safe_refs: list[str]` / `payload_digest: dict` / `summary: str` | ✅ |
| 3 | 错误信息采用 safe_message，不外泄堆栈 | `AgentTraceEvent.summary` 仅记录 safe_message | ✅ |
| 4 | cancelled 后迟到结果只记 ignored_late_result | `call_status` 枚举含 `IGNORED_LATE_RESULT` | ✅ |
| 5 | duplicate_ignored 判重键生效 | `_maybe_record_duplicate_terminal` 按 trace_id+step_id+attempt_no+event_type 判重 | ✅ |
| 6 | 普通用户默认不显示 Detail Trace | `get_detail_view(developer_mode=True)` 强制校验 | ✅ |
| 7 | Audit-level Event 写入失败 → fail-safe 阻断 | `_save_event_safely(critical=True, high_risk_user_action=True)` → 抛异常 | ✅ |
| 8 | 普通 Trace 写入失败不阻断主流程 | `_save_event_safely(critical=False)` → 降级 + 告警，不抛异常 | ✅ |
| 9 | 清理 Trace 不删业务真源 | `cleanup_expired_details` 仅清 detail 层（ToolCall/Observation/LLMCallView） | ✅ |
| 10 | Detail Trace 默认保留 90 天可配置 | `detail_retention_days: int = 90` 构造函数参数 | ✅ |
| 11 | request_id/trace_id/session_id/step_id 贯穿 | 所有 Trace 模型均含 `trace_id`/`session_id`/`step_id` | ✅ |
| 12 | LLMCallTraceView 以 LLMCallLog 为真源 | `record_llm_call` 接收 `LLMCallLog`，只保存投影字段 | ✅ |

---

## 五、发现的问题

### 问题 1（中）：event_type 使用自由字符串，未定义完整枚举

**设计要求**（行 258-311）：34 种 Trace 事件类型 + 13 种审计事件类型 = 47 种事件类型有明确命名。

**当前实现**：`AgentTraceEvent.event_type: str` 使用自由字符串。代码中实际触发的事件类型约 25 种（通过 `record_session_event`、`record_step_event`、`record_tool_call`、`record_observation`、`record_audit_event` 等方法动态传入），未定义完整枚举约束。

**影响**：事件类型拼写错误无法在编译/类型检查时发现；新增事件类型无集中管控清单。

**修复方向**：定义 `TraceEventType(StrEnum)` 枚举，包含设计文档中列出的 34+13 种事件类型。

### 问题 2（低）：ToolCallTrace 缺少 `tool_audit_log_ref` 字段

设计 §5.4 行 182 明确要求 ToolCallTrace 包含 `tool_audit_log_ref: string`（ToolAuditLog 引用）。当前模型 `models.py:532-544` 缺少此字段。

### 问题 3（低）：Metrics 存储为内存模型，无独立指标系统

设计 §11 定义了 16 个最小指标和标签方向。当前 `TraceMetricPoint` 模型和 `_emit_metric` 方法将指标写入 Trace 的 JSON 文件存储（作为 Trace 聚合的一部分），而非独立的时序指标系统。考虑到 P1-10 设计文档 §1 声明"不冻结具体存储引擎实现细节"，这属于可接受的实现选择。

### 问题 4（低）：部分事件类型未在代码中显式触发

设计文档中定义的 47 种事件类型中，代码实际触发约 25 种。未触发的类型主要属于边缘场景（`session_cancelling`、`policy_blocked`、`queue_backlog`、`retry_exhausted` 等），可在对应业务场景补充时追加。

---

## 六、代码集成验证

| 集成点 | 状态 |
|---|---|
| `AgentRuntimeService` → `AgentTraceService` | ✅ 通过 `dependencies.py` DI 注入 |
| `AgentOrchestrator` → `AgentTraceService` | ✅ `agent_workflow.py` 中调用 `record_workflow_event` / `record_user_decision` |
| `CandidateReviewService` → `AgentTraceService` | ✅ accept/reject/apply 时记录 `UserDecisionTrace` |
| `MemoryReviewGateService` → `AgentTraceService` | ✅ approve/edit_approve/reject/defer/apply/rollback 全链路记录 |
| `ToolFacade` → `AgentTraceService` | ✅ `record_tool_call` 记录每次工具调用 |
| `LLMCallLogger` → `AgentTraceService` | ✅ `record_llm_call` 投影 LLMCallLog |
| API 查询 | ✅ `traces.py` 路由 + 结构化查询（filter by work_id/chapter_id/status/step_id/event_type/event_stage/time_range） |
| 前端展示 | ✅ `AIPanel.vue` 展示 Session Trace 摘要 + Step 列表 |

---

## 七、测试报告

### S10 专属测试（7/7 通过）

```
✓ test_agent_trace_service_records_runtime_and_workflow_events_with_metrics
✓ test_agent_trace_service_records_tool_denied_and_llm_projection_in_detail_view
✓ test_agent_trace_service_keeps_first_terminal_event_and_records_duplicate_ignored
✓ test_agent_trace_service_cleans_old_detail_traces_but_keeps_session_and_audit_data
✓ test_agent_trace_service_supports_filtered_query_and_alert_resolution
✓ test_agent_trace_service_degrades_on_normal_write_failure_but_blocks_critical_audit
✓ test_agent_trace_api_lists_summary_and_protects_detail
```

### 全量回归：372 passed, 2 failed（2 个为 P0 已有问题，非 S10 引入）

---

## 八、验收结论

**P1-S10（AgentTrace 与可观测性）验收通过。**

- 全部 7 个核心模型落地（AgentTrace/AgentTraceEvent/AgentStepTrace/ToolCallTrace/ObservationTrace/LLMCallTraceView/UserDecisionTrace）
- 12 条安全红线全部落地（脱敏、迟到忽略、判重键、降级不阻断主流程、审计失败 fail-safe、Detail 权限控制、90 天留存可配置）
- 6 个业务模块已集成 Trace 记录（Runtime/Workflow/ToolFacade/CandidateReview/MemoryReviewGate/LLMCallLogger）
- API 层支持结构化查询 + Detail 权限控制 + 前端摘要展示

**4 个问题均不阻塞（1 中 + 3 低），建议进入 P1-S11a。**
