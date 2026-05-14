# InkTrace V2.0 P0 实现一致性修复方案（严格对齐冻结设计）

## 一、文档目的与约束

### 1.1 目的
本方案用于修复“当前代码实现”与已冻结文档体系之间的差距，目标是达到“严格按设计执行”的一致性标准，并为后续 P1 详细设计推进提供可信基线。

### 1.2 约束（必须遵守）
1. 不重做架构，不扩大 P0 范围。
2. 所有修复以以下文档为唯一权威：
   - `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`
   - `docs/07_overview/InkTrace-V2.0-概要设计说明书.md`
   - `docs/02_architecture/InkTrace-V2.0-架构设计说明书.md`
   - `docs/03_design/V2/InkTrace-V2.0-P0-01` ~ `P0-11`
   - `docs/04_plan/InkTrace-V2.0-P0-开发计划.md`
3. 不提前产品化 P1/P2 能力。
4. 所有行为边界（user_action、formal_write、HumanReviewGate、QuickTrial 隔离）不得弱化。

---

## 二、差距分级与处置策略

### 2.1 阻塞项（Blocker）
- B1：P0-07 ToolFacade 主路径未落地（必须先修）

### 2.2 主要项（Major）
- M1：CandidateDraft 状态枚举未对齐 P0-09
- M2：AIReview 状态枚举未对齐 P0-10
- M3：P0-11 caller_type 规则未贯穿 API -> Service -> 审计
- M4：关键写入路径 idempotency_key 规则未贯穿
- M5：ContextPack / VectorRecall 的降级口径停留在 stub 级别，未完全落实 P0-05 / P0-06 的受控边界

### 2.3 次要项（Minor）
- N1：AI Settings 测连错误信息脱敏不足
- N2：v2 AI 路由错误码/状态码映射分散，统一性不足

---

## 三、修复总顺序（强制执行顺序）

1. 阶段 A：先修 B1（ToolFacade 落地）。
2. 阶段 B：再修 M1/M2（状态口径）。
3. 阶段 C：再修 M3/M4（caller_type + idempotency 贯穿）。
4. 阶段 D：再修 M5（ContextPack/VectorRecall 受控化）。
5. 阶段 E：收口 N1/N2（脱敏与错误统一）。
6. 阶段 F：补测试与回归，按 P0 开发计划 S1~S10 验收。

---

## 四、详细修复方案（逐项落地）

## 4.1 B1：ToolFacade 主路径落地（对齐 P0-07）

### 对齐文档
- `docs/03_design/V2/InkTrace-V2.0-P0-07-ToolFacade与权限详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-08-MinimalContinuationWorkflow详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-11-API与集成边界详细设计.md`

### 当前问题
- 续写、审阅、候选稿动作多由 Workflow/Service 直接编排，未形成“受控 Tool 门面 + 权限策略 + 统一封装 + 审计”主路径。

### 修复动作
1. 增加 CoreToolFacade / ToolRegistry / ToolPermissionPolicy / ToolResultEnvelope / ToolError 组件。
2. 将以下能力迁移为“必须通过 ToolFacade 调用”：
   - `build_context_pack`
   - `run_writer_step`
   - `validate_writer_output`
   - `save_candidate_draft`
   - `review_candidate_draft`
   - AIJob 进度类工具（受限）
3. 强制 caller_type + side_effect_level 校验：
   - `user_action` 专属操作不可由 `workflow/agent/system` 触发。
   - `formal_write` 全禁。
4. 将 v2 API 层触发路径统一接入 Application -> ToolFacade（禁止 API 旁路）。

### 目标文件（方向）
- `application/services/ai/*`（编排层改为调 ToolFacade）
- `presentation/api/routers/v2/ai/*`（调用边界统一）
- 新增/补齐 ToolFacade 相关模块目录（按架构分层）

### 验收标准
1. 任一 AI 编排动作未经过 ToolFacade 即失败。
2. `accept/reject/apply` 仅 `user_action` 可通过。
3. ToolResult 必须统一 envelope，错误必须结构化。
4. 审计日志存在且不含完整正文/Prompt/API Key。

---

## 4.2 M1：CandidateDraft 状态机口径对齐（对齐 P0-09）

### 对齐文档
- `docs/03_design/V2/InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计.md`

### 当前问题
- 代码仍以 `generated` 为核心状态，未严格采用冻结口径：
  - `pending_review`
  - `accepted`
  - `rejected`
  - `applied`
  - `stale`
  - `superseded`

### 修复动作
1. 统一 CandidateDraftStatus 枚举为 P0-09 正式口径。
2. 保留历史术语仅作为兼容映射，不得作为正式状态向外暴露。
3. 明确：`accepted != applied`；`pending_review` 才是默认保存态。
4. 校正 API DTO 与前端展示字段，避免混用旧状态。

### 验收标准
1. list/get/API/测试中不再以 `generated` 作为正式业务状态。
2. apply 成功前状态不能变为 `applied`。
3. rejected 不可 apply；applied 不可重复 apply。

---

## 4.3 M2：AIReview 状态口径对齐（对齐 P0-10）

### 对齐文档
- `docs/03_design/V2/InkTrace-V2.0-P0-10-AIReview详细设计.md`

### 当前问题
- AIReview 结果状态命名与冻结文档不一致。

### 修复动作
1. 统一 AIReviewStatus 至冻结口径：
   - `completed`
   - `completed_with_warnings`
   - `failed`
   - `skipped`
   - `blocked`
2. 明确 warning 与 error 的语义分层：
   - `stale_candidate_warning`、`degraded_candidate_warning` 为 warning，不转 failed。
3. 保证 AIReviewResult 不改变 CandidateDraft.status。

### 验收标准
1. AIReview failed 不阻断 HumanReviewGate 的 accept/reject/apply。
2. AIReview 不自动 accept/reject/apply。

---

## 4.4 M3：caller_type 贯穿修复（对齐 P0-07/P0-11）

### 对齐文档
- `docs/03_design/V2/InkTrace-V2.0-P0-07-ToolFacade与权限详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-11-API与集成边界详细设计.md`

### 当前问题
- 多数接口依赖 `user_action: bool`，未形成统一 `caller_type` 策略矩阵。

### 修复动作
1. API 请求层明确携带或推断 caller_type。
2. Application/ToolExecutionContext 保持 caller_type 透传。
3. 权限矩阵统一约束：
   - accept/apply/reject 仅 `user_action`
   - review 默认仅 `user_action`（workflow 受限）
   - quick_trial 为 `quick_trial` 且不可写正式资产
4. 禁止前端伪造 workflow/system。

### 验收标准
1. caller_type 在 API 日志、ToolAudit、Job 记录可追溯。
2. 任意 caller_type 越权动作返回明确 `permission_denied`。

---

## 4.5 M4：idempotency_key 贯穿修复（对齐 P0-09/P0-11）

### 对齐文档
- `docs/03_design/V2/InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-11-API与集成边界详细设计.md`

### 当前问题
- 关键写入 API 幂等规则不完整。

### 修复动作
1. 强制幂等：
   - `save_candidate_draft`（内部）
   - `save_quick_trial_as_candidate`
   - `apply_candidate_to_draft`（建议强制）
2. 重复请求行为统一：
   - 参数摘要一致 -> `duplicate_request` + 返回既有 ref
   - 参数摘要冲突 -> `idempotency_conflict`
3. 日志仅记录 key hash，不记录原文。

### 验收标准
1. retry/resume 不重复创建 CandidateDraft 或重复 apply。
2. 幂等冲突不产生副作用。

---

## 4.6 M5：ContextPack/VectorRecall 受控化修复（对齐 P0-05/P0-06）

### 对齐文档
- `docs/03_design/V2/InkTrace-V2.0-P0-05-VectorRecall详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-06-ContextPack详细设计.md`

### 当前问题
- VectorRecall 主要以 unavailable stub 表达，query_text/allow_stale_vector/过滤规则等边界未完整实现。

### 修复动作
1. ContextPackService 通过 VectorRecallService（非直连 VectorStore）获取 RAG 结果。
2. 落实 query_text 构建失败分支：`degraded + rag_skipped`，不可 blocked。
3. 落实 allow_stale_vector -> RecallQuery.allow_stale 映射和限制规则。
4. 完整执行 AttentionFilter / trim_reason / filter_reason 枚举口径。

### 验收标准
1. VectorRecall 不可用时默认 degraded，不单独 blocked。
2. StoryMemory/StoryState 仍为 blocked 主因。
3. ContextPackSnapshot 持久化策略与失败边界符合文档。

---

## 4.7 N1：错误信息脱敏收口（对齐 P0-01/P0-11）

### 修复动作
1. AI Settings 测连失败 message 只保留 safe_message + error_code + ref。
2. 严禁原始异常携带 API key/请求正文落日志。

### 验收标准
- 普通日志与 API 返回不含完整 API Key/Prompt/正文。

---

## 4.8 N2：错误码与状态码统一收口（对齐 P0-11）

### 修复动作
1. v2 AI routers 统一 error envelope。
2. 统一 warning 与 error 的语义边界。
3. `request_id/trace_id` 全链路一致。

### 验收标准
- 同类错误在不同路由响应语义一致。

---

## 五、测试补齐清单（必须新增/修订）

## 5.1 ToolFacade 与权限
1. 未注册 tool -> `tool_not_found`
2. 禁用 tool -> `tool_disabled`
3. caller_type 越权 -> `tool_permission_denied`
4. formal_write -> `formal_write_forbidden`

## 5.2 CandidateDraft / HumanReviewGate
1. 默认状态为 `pending_review`
2. `accepted != applied`
3. apply 仅 user_action
4. version 冲突 -> `chapter_version_conflict`
5. 幂等重复 -> `duplicate_request`
6. 幂等冲突 -> `idempotency_conflict`

## 5.3 AIReview
1. 状态口径：completed / completed_with_warnings / failed / skipped / blocked
2. review failed 不阻断 HumanReviewGate
3. review 不改变 CandidateDraft.status

## 5.4 API 一致性
1. caller_type 贯穿
2. idempotency_key hash 记录
3. error envelope 一致
4. 日志与响应脱敏

## 5.5 ContextPack / VectorRecall
1. query_text 失败 -> degraded + rag_skipped
2. VectorRecall unavailable -> degraded
3. required over budget -> blocked
4. optional trimmed -> degraded/warning

---

## 六、执行完成判定（出闸条件）

满足以下全部条件才可判定“与冻结设计严格一致”：
1. Blocker（ToolFacade）已落地并接入主链路。
2. CandidateDraft / AIReview 状态口径完成统一。
3. caller_type + idempotency_key 在 API -> Service -> 审计全链路贯穿。
4. ContextPack / VectorRecall 受控边界与 P0-05/P0-06 对齐。
5. 安全脱敏与错误统一通过回归测试。
6. P0 开发计划 S1~S10 对照表无 blocker/major 未关闭项。

---

## 七、风险与回归控制

1. 迁移状态枚举时需做兼容映射，避免历史数据不可读。
2. ToolFacade 接入时先做灰度路径，避免一次性替换导致主链路中断。
3. apply 幂等化后必须验证“重复点击/重放请求”不会重复写正文。
4. QuickTrial 与正式 Job 隔离回归必须单独验证。

---

## 八、与 P1 的关系

1. 本方案仅修复 P0 一致性，不提前实现 P1 生产能力。
2. P1-01/P1-02/P1-03 仍保持“设计冻结优先、实现后置”。
3. 修复完成后，P1 实现可建立在稳定且合规的 P0 基线之上。
