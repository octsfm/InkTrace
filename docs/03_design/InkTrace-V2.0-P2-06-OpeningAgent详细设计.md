# InkTrace V2.0-P2-06 Opening Agent 详细设计

版本：v2.0 / P2 模块级详细设计冻结版
状态：冻结生效
所属阶段：InkTrace V2.0 P2-S2
产品内名称：开篇助手

依据：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`（R-AI-ENH-02）
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§4.6）
- `docs/03_design/InkTrace-V2.0-P2-06-OpeningAgent人本化重设计提案.md`
- `docs/03_design/InkTrace-V2.0-P2-11-API与前端集成边界详细设计.md`
- `docs/03_design/InkTrace-V2.0-P2-12-UI集成与交互设计说明书.md`

## 一、范围与目标

开篇助手帮助普通小说作者把故事想法整理成三个可选开篇方向，并生成原创的前三章候选稿。用户不需要理解 AI 或工程术语。

P2-S2 范围包含：

- 默认无参考作品的完整可用路径。
- 可选灵感参考分析。
- 三个开篇方向及用户确认。
- 前三章逐章 CandidateDraft 生成。
- Reviewer 独立审稿。
- 生成前策略相似风险与生成后稿件原创性风险。
- 逐章 HumanReviewGate 与 Local-First apply。

明确不做：

- 不承诺签约、流量或商业成绩。
- 不仿写指定作品。
- 不生成超过三章。
- 不创建或覆盖正式 Chapter。
- 不自动 apply，不提供一键应用三章。
- 不保存完整参考原文。
- P2 初期不提供高原创性风险 override。

## 二、用户流程

普通作者只感知四步：

```text
说说你的故事 → 选择开篇方向 → 生成前三章候选稿 → 逐章阅读与决定
```

### 2.1 说说你的故事

最少收集：

- 这是一个什么故事。
- 主角现在最想要什么。
- 希望读者看完第三章时期待什么。

自动读取当前作品已有题材、简介、大纲、人物和设定；界面只提示“已参考你现有的大纲和人物设定”，不展示 ContextPack。

### 2.2 可选灵感参考

- 无参考作品是正式主路径。
- 最多 3 部，每部最多前 3 章、30,000 汉字。
- 用户必须确认有权用于个人创作分析。
- 超限要求用户裁剪，不静默截断。
- 分析只产出结构化特点和避免相似点，不展示仿写入口。

### 2.3 选择开篇方向

每批生成三个差异明确的方向，每个包含：名称、百字说明、前三章一句话安排、优点、风险。用户可选择、修改、换一批或自写方向。

确认方向不等于生成正文。只有真实用户确认的方向才能进入候选稿生成。

### 2.4 逐章生成与审阅

- chapter_no 只能是 1、2、3。
- 一章成功后再生成下一章。
- 每章独立 CandidateDraft，独立 Reviewer 报告和原创性报告。
- 某章失败时保留已完成章节，可重试失败章节。
- 用户停止时保留已生成候选稿。
- `partial_success` 必须至少存在一个有效 `candidate_draft_id`。

## 三、Application Use Case

采用分段短用例，不维持跨用户确认的长生命周期 AIJob。

| Use Case | 输入 | 结果 |
|---|---|---|
| `prepare_opening_brief` | work_id、三个白话回答 | OpeningBrief |
| `import_opening_references` | brief_id、版权确认、参考文本 | OpeningReferenceSession + 短分析任务 |
| `generate_opening_directions` | brief_id | OpeningDirectionBatch（3 个方向） |
| `confirm_opening_direction` | direction_id、user_action | confirmed OpeningDirection |
| `revise_opening_direction` | direction_id、用户要求 | 新版本 Direction |
| `generate_opening_drafts` | confirmed direction_id | OpeningDraftBatch + 逐章 CandidateDraft |
| `stop_opening_draft_batch` | batch_id、user_action | stopped batch，保留结果 |

模型调用仍必须经过 ModelRouter，候选稿仍必须经过 ContextPack、WritingTask、Writer 与 CandidateDraftService。OpeningAgentService 只编排，不直接访问 Provider 或 Repository 实现。

## 四、业务状态机

```text
collecting_brief
→ preparing_directions
→ waiting_direction_choice
→ checking_strategy_risk
→ ready_to_generate
→ generating_drafts
→ partially_ready / waiting_draft_review
→ completed
```

允许从任一运行阶段进入：

- `blocked`：需要用户先处理明确问题。
- `failed`：本次任务失败，可按幂等规则重试。
- `cancelled`：用户取消短任务。
- `stopped`：用户停止分章生成，保留已有结果。

用户确认期间状态保存在领域对象中，不保持 AIJob running/paused。应用重启后从领域状态恢复，不重跑已完成步骤。

## 五、领域模型

### 5.1 OpeningBrief

- brief_id、work_id、story_premise、protagonist_desire、third_chapter_expectation。
- source_outline_version、source_asset_versions。
- status、created_at、updated_at。

### 5.2 OpeningReferenceSession

- reference_session_id、brief_id、work_id。
- reference_summaries（标题、章节数、字数、范围、hash、分析摘要）。
- copyright_confirmed_at、rights_text_version。
- temporary_secret_ref（只在未完成分析时存在，不返回前端）。
- status、expires_at、created_at。

### 5.3 OpeningDirectionBatch / OpeningDirection

- batch_id、brief_id、work_id、status。
- direction_id、name、summary、chapter_goals[1..3]、advantages、risks。
- revision_no、parent_direction_id、status。
- `confirmed_direction_id` 是批次唯一确认结果。

Direction 状态：`proposed → confirmed / rejected / superseded`。只有 user_action 可进入 confirmed。

### 5.4 OpeningDraftBatch

- draft_batch_id、work_id、brief_id、direction_id。
- per_chapter_results：chapter_no、status、candidate_draft_id、review_id、originality_report_id、error_code。
- status、result_refs、created_at、updated_at。

### 5.5 OriginalityReport

- report_id、work_id、brief_id、direction_id、draft_batch_id。
- candidate_draft_id、candidate_version_id（策略级检查时为空）。
- check_stage：`strategy` / `draft`。
- risk_level：`low` / `medium` / `high`。
- evidence_summary、revision_suggestions、status、created_at。

所有对象版本化保留，不按 work_id 覆盖旧主键。历史 CandidateDraft 必须能追溯到当时的 Brief、Direction 和 OriginalityReport。

## 六、风险双门控

### 6.1 策略相似风险

发生在生成前，对比已确认 Direction 与参考分析摘要：

- low/medium：可继续，medium 展示具体调整建议。
- high：后端返回 `P2_OPENING_STRATEGY_SIMILARITY_BLOCKED`，不得开始生成。

### 6.2 稿件原创性风险

发生在每章 CandidateDraft 保存后：

- low/medium：进入正常 HumanReviewGate，medium 显示修改建议。
- high：保留候选稿，metadata 关联报告；CandidateDraft apply 后端返回 `P2_OPENING_DRAFT_ORIGINALITY_REVIEW_REQUIRED`。
- 用户可按建议重写，重写版本重新检查。
- P2 初期不允许忽略 high 后强制 apply。

## 七、参考文本安全

完整参考文本禁止进入：

- 通用 AIJob.context。
- OpeningAnalysis/业务表。
- API response。
- AgentTrace、LLMCallLog、普通日志和错误日志。

跨请求临时存储必须通过 Domain/Application 定义的 `TemporarySensitiveTextStore` Port，Infrastructure 实现满足：

- 本地加密。
- 不可猜测 reference_session_id。
- 默认 TTL 30 分钟。
- 分析完成立即删除。
- 成功、失败、取消均清理。
- 应用启动时清理过期残留。
- 清理失败只写安全审计摘要，不写原文。

持久化仅保存标题、字数、范围、不可逆 hash、结构化特点和分析摘要。

## 八、权限与门控

- Opening Agent 无 formal_write 权限。
- Agent 可创建 Brief 建议、Direction 建议、CandidateDraft、Review 和 OriginalityReport。
- Agent 不得确认 Direction、停止用户任务、accept/reject/apply CandidateDraft。
- `confirm_opening_direction`、`stop_opening_draft_batch` 必须校验 `caller_type=user_action`、`user_action=true`、user_id、idempotency_key。
- CandidateDraft apply 继续走 P0/P1 HumanReviewGate 和 V1.1 Local-First。
- brief、direction、batch、work 必须进行同作品归属校验。

## 九、API

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

所有端点沿用 P0-11 通用响应。生成类 POST 返回短任务引用和 polling_hint；GET 返回业务安全摘要，不返回完整参考文本。

旧 `/import-reference`、`/analyze`、`/strategies/*`、`/generate` 和按 work 查询长 Job 状态的方案废止，不实现兼容旁路。

## 十、错误码

- `P2_OPENING_BRIEF_NOT_READY`
- `P2_OPENING_REFERENCE_LIMIT_EXCEEDED`
- `P2_COPYRIGHT_NOT_CONFIRMED`
- `P2_OPENING_DIRECTION_NOT_CONFIRMED`
- `P2_OPENING_DIRECTION_STALE`
- `P2_OPENING_STRATEGY_SIMILARITY_BLOCKED`
- `P2_OPENING_DRAFT_ORIGINALITY_REVIEW_REQUIRED`
- `P2_OPENING_DRAFT_BATCH_NOT_RUNNING`
- `P2_CALLER_FORBIDDEN`
- `P2_FEATURE_DISABLED`

warning 与 error 不混用。每个错误返回 safe_message 和 next_action，不向普通用户显示错误码。

## 十一、TDD 验收矩阵

1. 无参考作品完成 Brief→三个方向→确认→三章候选稿。
2. 未确认方向不能生成。
3. agent/system 伪造 user_action 被拒绝。
4. 每章独立 CandidateDraft，不创建或修改正式 Chapter。
5. 第二章失败时第一章保留，结果为有 result_ref 的 partial_success。
6. 用户停止生成后保留已完成候选稿。
7. 参考数量、章节和字数超限被后端拒绝。
8. 未确认版权不能导入参考；无参考路径不要求版权确认。
9. 完整参考文本不进入数据库、context、response、Trace 或日志。
10. 分析完成、失败、取消、进程重启均能清理临时参考文本。
11. 策略 high 在生成前阻断。
12. 稿件 high 保留 CandidateDraft 但后端阻断 apply；重写后重新检查。
13. 普通界面不出现 Agent、Job、Session、Prompt、Token 等术语。
14. 历史 CandidateDraft 不产生 Brief/Direction/Report 悬空引用。
15. 重复请求不重复创建 DirectionBatch、DraftBatch 或 CandidateDraft。

## 十二、代码改动边界

允许新增：Opening 领域对象与 Repository Ports、OpeningAgentService、TemporarySensitiveTextStore Adapter、Opening Router、Prompt/Output Schema、前后端测试与现有向导重构。

只允许追加：ToolFacade Opening Tool 注册和权限行、ModelRole/AgentType/TraceEvent 枚举、API Router 注册、feature flag 接线。

禁止修改：P0/P1 CandidateDraft 状态机语义、HumanReviewGate 核心安全规则、AgentRuntime PPAO 循环、V1.1 正式章节保存边界。
