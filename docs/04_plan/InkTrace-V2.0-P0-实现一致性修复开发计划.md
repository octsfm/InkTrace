# InkTrace V2.0 P0 实现一致性修复开发计划

## 一、计划定位

本计划用于落实《P0 实现一致性修复方案》，目标是在不扩大 P0 范围、不提前实现 P1/P2 能力的前提下，使当前代码实现与已冻结文档体系达到“严格一致”。

权威依据：
- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`
- `docs/07_overview/InkTrace-V2.0-概要设计说明书.md`
- `docs/02_architecture/InkTrace-V2.0-架构设计说明书.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-01` ~ `P0-11`
- `docs/04_plan/InkTrace-V2.0-P0-开发计划.md`
- `docs/04_plan/InkTrace-V2.0-P0-实现一致性修复方案.md`

## 二、范围与边界

### 2.1 本计划覆盖
1. ToolFacade 受控入口补齐与主链路接入。
2. CandidateDraft / AIReview 状态口径收敛。
3. caller_type 与 idempotency_key 全链路贯穿。
4. ContextPack / VectorRecall 受控降级边界补齐。
5. 错误码与日志脱敏一致性收口。
6. 测试补齐与全链路回归。

### 2.2 本计划不覆盖
1. 不新增 P1/P2 能力。
2. 不新增 Agent Runtime/Agent Workflow 生产链路。
3. 不实现 token streaming。
4. 不改造前端产品形态（仅做接口兼容与必要回归）。

## 三、里程碑与阶段

| 里程碑 | 目标 | 完成标准 |
|---|---|---|
| M0 | 基线确认 | 现状差距清单冻结、测试基线可重复 |
| M1 | ToolFacade 主路径落地 | 编排动作全部走受控工具入口 |
| M2 | 状态口径统一 | CandidateDraft/AIReview 状态与 P0 文档一致 |
| M3 | caller_type + idempotency 贯穿 | 关键写操作权限和幂等规则统一 |
| M4 | ContextPack/VectorRecall 边界收口 | blocked/degraded/ready 与查询失败分支一致 |
| M5 | 安全与错误统一 | 脱敏、错误 envelope、审计一致 |
| M6 | 验收关闭 | Blocker/Major 全部关闭，回归通过 |

## 四、阶段任务拆分

## 阶段 A（Blocker）：ToolFacade 主路径落地

### A1 核心组件
1. 建立/完善 CoreToolFacade、ToolRegistry、ToolPermissionPolicy、ToolResultEnvelope、ToolError。
2. 明确 P0 白名单工具及 side_effect_level。

### A2 主链路接入
1. MinimalContinuationWorkflow 改为通过 ToolFacade 调用：
   - build_context_pack
   - run_writer_step
   - validate_writer_output
   - save_candidate_draft
2. AIReview 调用改为受控工具路径。

### A3 权限边界
1. caller_type 权限检查落地。
2. user_action 专属操作禁止 workflow/agent/system 触发。
3. formal_write 永久禁止。

### A阶段验收
1. 任意关键动作绕过 ToolFacade 失败。
2. Tool 审计日志可追溯，且不含敏感明文。

---

## 阶段 B（Major）：状态口径统一

### B1 CandidateDraft 状态统一（对齐 P0-09）
1. 正式状态：pending_review / accepted / rejected / applied / stale / superseded。
2. 旧状态兼容映射仅用于迁移，禁止对外继续暴露。

### B2 AIReview 状态统一（对齐 P0-10）
1. completed / completed_with_warnings / failed / skipped / blocked。
2. warning 与 error 语义分层。

### B阶段验收
1. API、Service、测试统一使用新口径。
2. accepted != applied 严格成立。

---

## 阶段 C（Major）：caller_type 与 idempotency_key 贯穿

### C1 caller_type
1. API -> Application -> ToolExecutionContext -> AuditLog 全链路透传。
2. 前端不可伪造 workflow/system。

### C2 idempotency_key
1. save_candidate_draft（内部）强制幂等。
2. save_quick_trial_as_candidate 强制幂等。
3. apply_candidate_to_draft 强制或等价 apply_request_id。
4. duplicate_request / idempotency_conflict 语义统一。

### C阶段验收
1. 重试/重放不产生重复副作用。
2. 幂等冲突不落新数据。

---

## 阶段 D（Major）：ContextPack / VectorRecall 边界收口

### D1 VectorRecall 接入边界
1. ContextPackService 仅通过 VectorRecallService 受控调用。
2. 禁止直连 VectorStorePort。

### D2 query_text 与 degraded 分支
1. query_text 构造失败 -> degraded + rag_skipped。
2. VectorRecall 不可用/失败/无结果 -> degraded（非单独 blocked）。

### D3 预算与过滤
1. required over budget -> blocked。
2. optional trim -> degraded/warning。
3. trim_reason/filter_reason 枚举收口。

### D阶段验收
1. ContextPack 状态判定与 P0-06 一致。
2. 不伪造 ready。

---

## 阶段 E（Minor）：安全与错误统一收口

### E1 脱敏
1. AI Settings 测连错误信息仅输出 safe_message/ref。
2. 普通日志不得记录完整正文/Prompt/API Key。

### E2 错误规范
1. v2 AI 全路由统一 error envelope。
2. warning / status 与 error 分离。

### E阶段验收
1. API 响应与日志均无敏感泄露。
2. 同类错误码跨路由语义一致。

---

## 阶段 F：测试补齐与全链路回归

### F1 必测清单
1. ToolFacade 权限矩阵。
2. CandidateDraft 状态机与 apply 冲突。
3. AIReview 状态与不阻断门控。
4. caller_type 越权拒绝。
5. idempotency duplicate/conflict。
6. ContextPack blocked/degraded/ready 关键分支。

### F2 回归范围
1. `tests/ai/` 全量。
2. v2 AI API 路由测试。
3. 关键 v1 Local-First 保存链路回归（避免 apply 接入破坏）。

### F阶段验收
1. Blocker/Major 全关闭。
2. 回归通过，无新增高风险回归缺陷。

## 五、任务优先级

| 优先级 | 任务 |
|---|---|
| P0 | 阶段 A（ToolFacade） |
| P0 | 阶段 B（状态口径） |
| P0 | 阶段 C（caller_type + 幂等） |
| P1 | 阶段 D（ContextPack/Recall收口） |
| P2 | 阶段 E（脱敏与错误统一） |
| P0 | 阶段 F（回归收口） |

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| ToolFacade 接入改动面大 | 主链路中断风险 | 分阶段切换 + 双路径短期兼容 + 逐步开关 |
| 状态枚举变更影响历史数据 | 读取失败/显示混乱 | 增加兼容映射与数据迁移脚本（如需要） |
| 幂等规则收紧影响现有调用 | 调用失败增加 | 提前补齐调用端 idempotency_key 生成策略 |
| ContextPack 规则收紧导致 blocked 增多 | 用户体验波动 | 增强 degraded 提示与可恢复路径 |
| 错误脱敏过度影响排障 | 定位效率下降 | 保留 debug_ref + trace_id + 安全 detail_ref |

## 七、质量门禁

每阶段完成前必须满足：
1. 单元测试与集成测试通过。
2. 不引入 formal_write 旁路。
3. 不引入 user_action 伪造通道。
4. 不暴露 API Key / 完整正文 / 完整 Prompt。

## 八、完成定义（DoD）

满足以下全部条件才可宣告“P0 实现与冻结设计严格一致”：
1. ToolFacade 主路径生效。
2. CandidateDraft / AIReview 状态口径与 P0-09/P0-10 完全一致。
3. caller_type + idempotency_key 贯穿到 API/Service/Audit。
4. ContextPack / VectorRecall 关键规则与 P0-05/P0-06 一致。
5. 错误与日志脱敏符合 P0-01/P0-11。
6. `tests/ai` 及关键回归通过，Blocker/Major 为 0。

## 九、实施建议顺序（执行视角）

1. 先完成阶段 A，再开始阶段 B/C。
2. B 与 C 可局部并行，但对外 API 口径变更统一在同一发布窗口。
3. D 放在 B/C 之后，避免状态和权限规则未稳时放大复杂度。
4. E/F 作为收尾，不得跳过。

## 十、与后续 P1 的衔接

1. 本计划完成后，P1 才具备稳定实现基线。
2. 若本计划未完成，不建议进入 P1 代码实现。
3. P1 设计可继续推进，但实现应等待本计划关闭 Blocker/Major。
