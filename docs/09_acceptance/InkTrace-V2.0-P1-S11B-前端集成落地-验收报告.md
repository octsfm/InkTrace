# InkTrace V2.0 P1-S11B 前端集成落地 — 验收报告

版本：v1.0 / 2026-05-25
状态：验收通过
所属阶段：InkTrace V2.0 P1
验收范围：P1-S11a（API 集成边界落地）+ P1-S11b（前端集成落地）

## 一、验收总览

| 验收项 | 结果 |
|---|---|
| S11a: 三重门控 (caller_type + user_action + idempotency_key) | 通过 |
| S11a: API 层不直连 ToolFacade/Provider/Repository | 通过 |
| S11a: AgentTrace detail 权限控制 | 通过 |
| S11a: safe_message 规则落地 | 通过 |
| S11b: 前端 11 类入口最小可用流 | 通过 |
| S11b: 轮询主路径状态机与终态停止 | 通过 |
| S11b: SSE 可选增强与自动回退轮询 | 通过 |
| 后端 AI 测试 (384 cases) | 384 passed, 1 skipped |
| 后端 V1 回归 (141 cases) | 141 passed |
| 前端测试 (220 cases / 37 files) | 220 passed |
| 安全红线回归 | 通过 |

## 二、P1-S11a 逐项验收

### 2.1 三重门控 (caller_type + user_action + idempotency_key)

**验证范围**: 所有门控端点（6 组路由文件）

| 路由文件 | 门控端点 | 三重校验 |
|---|---|---|
| `continuation.py` | accept/reject/apply/select/rewrite | `_ensure_gate_request()` 完整校验 |
| `planning.py` | select_direction/confirm_plan/reject_plan | `_ensure_gate_request()` 完整校验 |
| `sessions.py` | start/pause/resume/cancel | `_ensure_gate_request()` 完整校验 |
| `memory.py` | approve/edit-approve/reject/defer/apply/rollback | `_reject_invalid_memory_request()` 完整校验 |
| `suggestions.py` | accept/dismiss/convert | `_reject_invalid_decision_request()` 完整校验 |
| `conflicts.py` | decide | `_reject_invalid_decision_request()` 完整校验 |

**三重校验逻辑**（以 `continuation.py:_ensure_gate_request` 为例）：
1. `caller_type != "user_action"` → 403 `caller_type_forbidden`
2. `not user_action` → 403 `action_not_allowed`
3. `idempotency_key` 为空 → 400 `idempotency_key_required`

**副作用写操作**（generate 类）也有 `_ensure_write_request()` 校验 caller_type + idempotency_key。

### 2.2 API 层不直连 ToolFacade/Provider/Repository

**验证依据**: `presentation/api/dependencies.py`

所有 API 路由通过 DI 函数获取 Application Service，调用链路严格遵守：
```
Presentation API → Application Service → Domain/Infrastructure
```

- `dependencies.py` 中定义的 DI 函数（`get_agent_runtime_service()`, `get_continuation_workflow()`, `get_planning_api_service()` 等）全部返回 Application Service 实例
- API 路由文件（`continuation.py`, `planning.py`, `sessions.py` 等）仅调用 `dependencies.get_*()` 获取 service，不 import `ToolFacade`/`Provider`/`Repository` 类
- `ToolFacade` 仅注入到 AgentRuntimeService（Agent 入口），不暴露给 API 层

### 2.3 AgentTrace detail 权限控制

**验证依据**: `traces.py:46-49` + `agent_trace_service.py:497-499`

```python
# traces.py - API 层
def get_agent_trace_detail_view(trace_id, request, detail=False, developer_mode=False):
    if not detail:
        raise ValueError("invalid_request")
    payload = service.get_detail_view(trace_id, developer_mode=developer_mode)

# agent_trace_service.py - Service 层
def get_detail_view(self, trace_id, *, developer_mode):
    if not developer_mode:
        raise ValueError("permission_denied")
```

- `?detail=true` 参数是必要条件但不是充分条件 —— 缺少则直接返回 `invalid_request`
- `developer_mode` 参数传入 service 层进行二次校验
- 前端 AIPanel.vue:578 仅在 `developerMode` 为 true 时显示"查看 Detail"按钮

### 2.4 safe_message 规则落地

**验证依据**: `response_utils.py`

- `SAFE_MESSAGE_MAP` 包含 21 条面向用户的中文安全消息
- `error_response()` 始终通过 `resolve_safe_message()` 包装错误消息
- 错误响应不泄露堆栈/Prompt/正文/API Key
- 相关测试: `test_response_utils.py::test_error_response_maps_safe_message_to_readable_text` 通过

## 三、P1-S11b 逐项验收

### 3.1 前端 11 类入口最小可用流

**验证依据**: `AIPanel.vue` + `RightWorkspacePanel.vue`

RightWorkspacePanel 三栏写作台包含 6 个标签，AIPanel.vue 内部按 `showAIMode` / `showReviewMode` 分模式展示：

| # | 入口 | 模式 | list | detail | action |
|---|---|---|---|---|---|
| 1 | Agent 进度面板 | AI | AgentSession 列表 | 详情 (status/stage/agent_type) | pause/resume/cancel |
| 2 | 方向推演面板 | AI | DirectionProposal 列表 | 选项详情 | select/generate plan |
| 3 | 章节计划面板 | AI | ChapterPlan 列表 | plan_items 展开 | confirm/reject |
| 4 | 候选稿版本面板 | Review | CandidateDraft 列表 | 版本链/内容/diff | accept/reject/apply/rewrite |
| 5 | 审稿报告展示 | Review | AIReview (via candidate) | 审稿结果 (issues/suggestions) | review_candidate_draft |
| 6 | AI 建议面板 | Review | AISuggestion 列表 | 建议详情 | accept/dismiss/convert |
| 7 | Conflict Guard | Review | Conflict 列表 (banner+per-draft) | 冲突详情 | decide(acknowledged/dismissed) |
| 8 | 记忆更新审批 | Review | MemoryGate 列表 | suggestions + revisions | approve/edit-approve/reject/defer/apply/rollback |
| 9 | Agent Trace 面板 | Review | Trace 列表 | steps + detail (仅 developer) | view steps/detail |
| 10 | Plot Arc 状态 | AI | arc 列表 | key_points 展开 | 查看详情 |
| 11 | Context Pack 预览 | AI | readiness + items | source_type/summary | build context pack |

**额外入口**: Writing Task 列表、Quick Trial、AI 设置/Provider 测试、初始化分析

### 3.2 轮询主路径状态机与终态停止

**验证依据**: `useAIJobPolling.js`

```javascript
// 核心轮询逻辑
const DEFAULT_TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled', 'partial_success'])

// 动态间隔: 从 polling_hint.next_interval_ms 读取，上限 maxIntervalMs (5s)
const resolveIntervalMs = () => {
    const hinted = Number(pollingHint.value?.next_interval_ms || 0)
    return Number.isFinite(hinted) && hinted > 0 ? Math.min(hinted, maxIntervalMs) : intervalMs
}

// 终态停止条件: terminalStatuses 匹配 或 polling_hint.stop === true
const scheduleNextFetch = () => {
    if (!jobId.value || isTerminal.value || pollingHint.value?.stop) return
    timer = setTimeout(() => { void fetchOnce() }, resolveIntervalMs())
}
```

- 默认轮询间隔 1s，上限 5s
- 支持后端 `polling_hint.next_interval_ms` 动态调整
- 终态自动停止，无需手动干预
- AIPanel.vue 中为 session 轮询使用独立 `sessionPolling` 实例

### 3.3 SSE 可选增强与自动回退

**验证依据**: `useAIJobPolling.js:74-105, 141-145`

```javascript
// SSE 仅在 sse.enabled 为 true 时尝试连接
const connectEventSource = () => {
    if (!sse?.enabled || !jobId.value) return  // 默认不启用
    try {
        eventSource = eventSourceFactory(buildUrl(jobId.value))
        transport.value = 'sse'
        eventSource.onerror = () => { fallbackToPolling() }  // 错误→回退
    } catch {
        fallbackToPolling()  // 异常→回退
    }
}

// start() 中 SSE 优先，失败/不可用自动回退
if (sse?.enabled) {
    connectEventSource()
    if (transport.value === 'sse') return  // SSE 连接成功
}
scheduleNextFetch()  // 回退到轮询
```

- 默认 transport = 'polling'，SSE 默认不启用
- SSE 连接失败/解析失败/错误均自动回退轮询
- SSE 关闭完全不影响主流程
- 相关前端测试: `useAIJobPolling.spec.js` 包含 SSE 回退场景测试，通过

## 四、测试结果

### 4.1 后端 AI 测试

```
======================== 384 passed, 1 skipped, 1 warning in 50.87s ========================
```

- 1 skipped: `test_real_provider_smoke` — 设计上需要真实 API Key，CI 环境跳过
- 1 warning: Pydantic serializer 类型转换警告（非功能性问题）

### 4.2 后端 V1 回归

```
============================= 141 passed in 9.88s =============================
```

V1 接口全部通过，无回归。

### 4.3 前端测试

```
Test Files  37 passed (37)
     Tests  220 passed (220)
```

关键测试覆盖：
- `AIPanel.spec.js` — AI 面板 12 个测试（settings/job polling/candidate/quick trial/versions/traces/suggestions/conflicts/plot arcs/planning）
- `useAIJobPolling.spec.js` — 轮询状态机 + SSE 回退测试
- V1 组件测试全部通过（ChapterSidebar/StatusBar/TimelinePanel 等）

## 五、安全红线回归

| 检查项 | 状态 |
|---|---|
| API 层不直连 Provider/ModelRouter/ToolFacade | 通过 |
| 门控动作必须有 caller_type=user_action + user_action=true + idempotency_key | 通过 |
| Agent 不能执行 user_action 专属动作 | 通过 (`test_tool_facade.py`) |
| Agent 不能 formal_write | 通过 (`test_tool_facade.py`) |
| API 响应不泄露完整正文/Prompt/API Key | 通过 (`test_p0_boundaries.py`) |
| AgentTrace detail 受权限控制 | 通过 |
| Quick Trial 不产生正式资产副作用 | 通过 |
| Context Pack 预览仅暴露 summary + layers preview | 通过 |
| SSE 默认关闭，轮询是主路径 | 通过 |

## 六、11 组 API 对齐检查

| 分组 | 路由前缀 | 路由文件 | 状态 |
|---|---|---|---|
| Agent Session | `/api/v2/ai/sessions` | `sessions.py` | 已实现 |
| Agent Trace | `/api/v2/ai/traces` | `traces.py` | 已实现 |
| Plot Arc | `/api/v2/ai/plot-arcs` | `plot_arcs.py` | 已实现 |
| Direction Proposal | `/api/v2/ai/directions` | `planning.py` | 已实现 |
| Chapter Plan | `/api/v2/ai/chapter-plans` | `planning.py` | 已实现 |
| Multi-round CandidateDraft | `/api/v2/ai/candidate-drafts` | `continuation.py` | 已实现 |
| AI Suggestion | `/api/v2/ai/suggestions` | `suggestions.py` | 已实现 |
| Conflict Guard | `/api/v2/ai/conflicts` | `conflicts.py` | 已实现 |
| Memory Revision | `/api/v2/ai/memory-gates` + `/api/v2/ai/memory-revisions` | `memory.py` | 已实现 |
| Context Pack | `/api/v2/ai/context-packs` | `context_pack.py` | 已实现 |
| Writing Task | `/api/v2/ai/writing-tasks` | `planning.py` | 已实现 |

## 七、待确认点

| 项目 | 说明 |
|---|---|
| `workflow_compat` caller_type | 当前保留，P1 收尾阶段确认是否移除 |
| Context Pack layers preview 分页 | 当前为 summary 级别预览，更完整层级展开作为后续增强 |
| Writing Task edit | 当前仅 list + detail + confirm，直接 edit 后置 |

## 八、验收结论

**P1-S11B（前端集成落地）及其前置 S11a（API 集成边界落地）验收通过。**

全部验收标准达标：
- API 层 11 组路由全部实现，三重门控落地
- 前端 11 类入口具备最小可用流（list + detail + action）
- 轮询主路径状态机完整，终态自动停止
- SSE 可选增强，不可用时自动回退轮询，不影响主流程
- 后端 384 AI 测试 + 141 V1 回归全部通过
- 前端 220 测试全部通过
- 安全红线（P0 边界、P1 门控、权限控制、脱敏规则）全部通过

**建议进入 P1-S12（E2E 联调与封板验收）。**
