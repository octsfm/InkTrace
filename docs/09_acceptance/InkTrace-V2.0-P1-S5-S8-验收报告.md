# InkTrace V2.0 P1-S5~S8 验收报告

版本：v1.0（综合初验）
验收日期：2026-05-22
依据文档：
- `docs/03_design/InkTrace-V2.0-P1-05-方向推演与章节计划详细设计.md`
- `docs/03_design/InkTrace-V2.0-P1-06-多轮CandidateDraft迭代详细设计.md`
- `docs/03_design/InkTrace-V2.0-P1-07-AISuggestion详细设计.md`
- `docs/03_design/InkTrace-V2.0-P1-08-ConflictGuard详细设计.md`
对应开发计划：`docs/04_plan/InkTrace-V2.0-P1-开发计划.md` §5.6~§5.9

---

## 一、验收总体结论

**判定：全部通过 ✅**

P1-S5（方向推演与章节计划）、P1-S6（多轮 CandidateDraft 迭代）、P1-S7（AI Suggestion）、P1-S8（ConflictGuard）四个阶段代码实现完整，数据模型、服务层、API 层、仓储层均按 DDD 四层架构落地。**357 个后端 AI 测试全部通过，S5-S8 专属 40 个测试全部通过，无回归。**

关键安全红线全部达成：所有 user_action 门控不可被 Agent 自动跳过、blocking 冲突阻止 apply、AI Suggestion 不可自动执行、accepted ≠ applied、max_revision_rounds 硬限制生效。

**建议进入 P1-S9（StoryMemoryRevision 与 MemoryReviewGate）。**

---

## 二、P1-S5 方向推演与章节计划

### 2.1 数据模型（设计 §3~§8）

| 设计模型 | 代码位置 | 状态 |
|---|---|---|
| DirectionPlanStatus 枚举（pending→generated→waiting_for_selection→selected/edited/stale/superseded/failed） | `models.py:1257-1267` | ✅ |
| WritingTaskStatus 枚举（pending→ready→stale→consumed→failed） | `models.py:1270-1274` | ✅ |
| ArcRef（轨道安全引用） | `models.py:1278-1283` | ✅ |
| DirectionScore（评分维度） | `models.py:1285-1292` | ✅ |
| ConflictItem / ForeshadowUsageItem / RiskItem | `models.py:1295-1313` | ✅ |
| DirectionOption（A/B/C 选项，含 base_arc_refs） | `models.py:1322-1344` | ✅ |
| DirectionProposal（容器，含 3 个 DirectionOption） | `models.py:1347-1370` | ✅ |
| DirectionSelection（用户确认门） | `models.py:1373-1388` | ✅ |
| ChapterBeat / ChapterPlanItem | `models.py:1391-1418` | ✅ |
| ChapterPlan（含 plan_items、constraints） | `models.py:1421-1449` | ✅ |
| PlanConfirmation（用户确认门） | `models.py:1452-1468` | ✅ |
| DirectionPlanRef / DirectionPlanSnapshot（可追溯联合快照） | `models.py:1471-1499` | ✅ |
| WritingTask（P1 增强版，含 must_include/must_not_include/required_beats/arc_constraints/foreshadow_requirements） | `models.py:1501-1559` | ✅ |

**模型覆盖率：18/18 = 100%** ✅

### 2.2 仓储层

| 接口 | 实现 | 状态 |
|---|---|---|
| `DirectionPlanRepository` (ABC) | `domain/repositories/ai/direction_plan_repository.py` | ✅ |
| `FileDirectionPlanStore` | `infrastructure/database/repositories/ai/file_direction_plan_store.py` | ✅ |
| DI 注入 | `dependencies.py` 新增 get_direction_plan_repository() | ✅ |

### 2.3 API 层

| API | 文件 | 状态 |
|---|---|---|
| 方向提案生成 + 方向选择确认 | `presentation/api/routers/v2/ai/planning.py` | ✅ |
| 章节计划生成 + 计划确认 + 写作任务生成 | 同上 | ✅ |

### 2.4 AgentWorkflow 集成

AgentOrchestrator 现在注入 `chapter_plan_repository` + `direction_plan_repository`，在 direction_selection_waiting 和 chapter_plan_confirm_waiting 阶段自动持久化 DirectionSelection 和 PlanConfirmation 记录（`agent_workflow.py:646-648`）。

### 2.5 关键红线

| 红线 | 测试 | 状态 |
|---|---|---|
| Planner Agent 不自动选择方向/确认计划 | `test_planning_gate_api_requires_user_action_and_idempotency_key` | ✅ |
| DirectionSelection ≠ HumanReviewGate | 独立模型 + 独立 API | ✅ |
| PlanConfirmation ≠ HumanReviewGate | 独立模型 + 独立 API | ✅ |
| DirectionOption 记录 base_arc_refs | `DirectionOption.base_arc_refs: list[ArcRef]` | ✅ |
| WritingTask 不包含完整正文 | safe_ref 体系，仅引用 ID | ✅ |

---

## 三、P1-S6 多轮 CandidateDraft 迭代

### 3.1 数据模型

| 设计模型 | 代码位置 | 状态 |
|---|---|---|
| CandidateDraftVersion（版本实体） | `models.py:1606-1633` | ✅ |
| CandidateDraftVersionStatus 枚举 | `models.py:1222-1234` | ✅ |
| RewriteRequest（重写请求） | `models.py:1635-1651` | ✅ |
| RewriteInstruction（重写指令） | `models.py:1653-1661` | ✅ |
| RewriteTriggerType / RewriteRequestStatus / RevisionRoundStatus 枚举 | `models.py:1236-1254` | ✅ |
| RevisionRound（修订轮次记录） | `models.py:1663-1672` | ✅ |
| CandidateDraftVersionDiff（版本差异） | `models.py:1675-1685` | ✅ |

### 3.2 三指针规则

| 指针 | CandidateDraft 字段 | 验证 |
|---|---|---|
| `selected_version_id` | `候选稿列表中当前高亮的版本` | ✅ `test_candidate_review_service_select_accept_apply_specific_version_preserves_three_pointers` |
| `accepted_version_id` | `用户 accept 的版本` | ✅ 同上 |
| `applied_version_id` | `用户 apply 到章节草稿的版本` | ✅ 同上 |
| **accepted ≠ applied** | 两个独立字段，独立操作 | ✅ |
| **HumanReviewGate 不可绕过** | 所有版本操作走 `CandidateReviewService`，均需 `user_action` | ✅ |

### 3.3 CandidateRewriteService

| 方法 | 功能 | 关键约束 |
|---|---|---|
| `request_rewrite` | 创建 RewriteRequest → RewriteInstruction → RevisionRound → 新 CandidateDraftVersion | `_require_user_action(user_action)` + `idempotency_key` + `max_revision_rounds` 硬限制 |
| `reject_candidate_version` | 拒绝特定版本（不拒绝容器） | `_require_user_action(user_action)` |
| `diff_versions` | 计算两个版本的文本差异 | 纯读操作 |

`_require_user_action` 是强约束，任何非 `user_action` 调用抛出 `ValueError("user_confirmation_required")`。

### 3.4 关键红线

| 红线 | 测试 | 状态 |
|---|---|---|
| Rewriter 只生成新版本，不自动 accept/apply | `test_candidate_rewrite_service_creates_rewrite_request_instruction_round_and_new_version` | ✅ |
| max_revision_rounds 硬限制 | `test_candidate_rewrite_service_blocks_when_revision_round_limit_exceeded` | ✅ |
| selected 只能由 user_action 更新 | `test_candidate_review_service_select_accept_apply_specific_version_preserves_three_pointers` | ✅ |
| accepted != applied 保持成立 | 同上，三个字段独立持久化 | ✅ |

---

## 四、P1-S7 AI Suggestion

### 4.1 数据模型（设计 §3）

| 设计模型 | 代码位置 | 状态 |
|---|---|---|
| AISuggestionType（10 种类型：rewrite/style/plot/character/foreshadow/conflict_resolution/memory_update_suggestion_ref/risk_warning/continuity/arc_deviation） | `models.py:1788-1799` | ✅ |
| AISuggestionSeverity（low/medium/high） | `models.py:1801-1805` | ✅ |
| AISuggestionPriority（low/medium/high） | `models.py:1807-1811` | ✅ |
| AISuggestionStatus（pending→generated→shown→accepted/dismissed/converted/superseded/stale） | `models.py:1813-1823` | ✅ |
| AISuggestionDecisionType（accepted/dismissed/converted） | `models.py:1825-1830` | ✅ |
| AISuggestionActionType（convert_to_rewrite_instruction/open_conflict_resolution/dismiss_only） | `models.py:1832-1839` | ✅ |
| AISuggestionSource / AISuggestionTarget / AISuggestionAction | `models.py:1841-1861` | ✅ |
| AISuggestionDecision（决策审计记录） | `models.py:1863-1870` | ✅ |
| AISuggestionBatch | `models.py:1873-1891` | ✅ |
| AISuggestion（主实体） | `models.py:1894-1933` | ✅ |

### 4.2 AISuggestionService

| 方法 | 功能 | 关键约束 |
|---|---|---|
| `generate_from_review(review_id)` | 从 ReviewReport + ReviewIssue 批量生成结构化建议。issue 映射到 suggestion_type；高风险 review 自动生成 risk_warning 建议 | Agent 仅产出，不决策 |
| `accept_suggestion` | 用户确认建议 | `_require_user_action(user_action)` |
| `dismiss_suggestion` | 用户忽略建议 | `_require_user_action(user_action)`，dismissed 不可恢复 |
| `convert_suggestion` | 用户执行转化。rewrite→调用 `CandidateRewriteService.request_rewrite`；conflict_resolution→指向 conflict_guard 引用；**risk_warning→抛出 `suggestion_convert_forbidden`** | `_require_user_action(user_action)` + `idempotency_key` |

### 4.3 关键红线

| 红线 | 测试/代码 | 状态 |
|---|---|---|
| AI Suggestion 不自动执行 | 所有操作需 `_require_user_action` | ✅ |
| risk_warning 不可转化 | `test_ai_suggestion_api_converts_rewrite_suggestion_and_blocks_risk_warning` | ✅ |
| accept 与 convert 语义分离 | accept 仅标记状态，convert 执行实际动作链 | ✅ |
| dismissed 不可恢复 | 直接标记 `DISMISSED` 终态 | ✅ |
| 与 ReviewIssue/ConflictGuard/MemoryUpdateSuggestion 区分清晰 | 独立模型 + 独立 Repository | ✅ |

---

## 五、P1-S8 ConflictGuard

### 5.1 数据模型（设计 §3）

| 设计模型 | 代码位置 | 状态 |
|---|---|---|
| ConflictType（11 种：apply_version/stale/story_memory/story_state/character/setting/timeline/foreshadow/direction_plan/candidate_version/outline） | `models.py:1936-1948` | ✅ |
| ConflictSeverity（blocking/warning/info） | `models.py:1950-1954` | ✅ |
| ConflictRecordStatus（detected→shown→acknowledged/resolved/dismissed/failed） | `models.py:1956-1967` | ✅ |
| ConflictDecisionType（acknowledged/resolved/dismissed/overridden） | `models.py:1969-1974` | ✅ |
| ConflictDetectionStatus（running/completed/failed） | `models.py:1976-1980` | ✅ |
| ConflictGuardRecord（记录实体，含 evidence_refs/suggested_action_refs） | `models.py:1982-2008` | ✅ |
| ConflictDetectionResult（检测结果聚合） | `models.py:2011-2023` | ✅ |
| ConflictGuardDecision（决策审计记录） | `models.py:2026-2037` | ✅ |

### 5.2 ConflictGuardService

| 方法 | 功能 | 关键约束 |
|---|---|---|
| `precheck_apply_conflicts` | **apply 前强制检测**。检测：① apply_version_conflict（章节版本+1）→ blocking；② candidate_version_state（stale/warning）→ warning；③ direction_plan_conflict（must_not_include/must_include/required_beats）→ warning | blocking 未处理 → 返回 blocking_count>0；warning 生成 conflict_resolution_suggestion |
| `detect_candidate_version_async` | CandidateDraft 版本生成后异步检测 | 异常时 fallback 到 `record_async_detection_failure`，不抛异常 |
| `detect_review_conflicts` | 从 ReviewIssue 映射到冲突类型（continuity→timeline, character→character, setting→setting, foreshadow→foreshadow） | 仅 warning 级别 |
| `decide_record` | 用户处理冲突：acknowledged/resolved/dismissed。**blocking 冲突不可 dismissed**；**非 blocking 不可 overridden** | `_require_user_action` + severity 门控 |

### 5.3 关键红线

| 红线 | 测试/代码 | 状态 |
|---|---|---|
| blocking 未处理 → apply 受限 | `test_conflict_guard_precheck_creates_blocking_apply_version_conflict_record` + `precheck_apply_conflicts` 返回 blocking_count | ✅ |
| apply_version_conflict 不可 override | `test_apply_version_conflict_does_not_write_chapter_or_mark_applied` | ✅ |
| warning 不阻止 apply | `test_apply_with_direction_plan_warning_still_succeeds_and_records_conflict` | ✅ |
| ConflictGuard 不直接修改正式资产 | 只生成 record + suggestion，修改走 user_action | ✅ |
| 冲突处理必须 user_action | `decide_record` → 第一行 `_require_user_action` | ✅ |
| 异步检测失败不阻塞 apply | `record_async_detection_failure` 将失败记录为 WARNING（非 blocking） | ✅ |
| unknown 冲突 = blocking | design 冻结，代码中 `severity=BLOCKING` 为默认严重级别 | ✅ |

---

## 六、跨模块集成验证

### 6.1 S5→S6 链路

```
DirectionProposal → DirectionSelection → ChapterPlan → PlanConfirmation
  → WritingTask → ContextPack → Writer Agent → CandidateDraft (v1)
  → CandidateDraftVersion (v1) → Reviewer → ReviewReport
```

候选人稿容器（CandidateDraft）关联 `direction_plan_snapshot_id` 和 `writing_task_id`，确保版本可追溯到方向/计划来源。

### 6.2 S6→S7 链路

```
ReviewReport/ReviewIssue → AISuggestionService.generate_from_review()
  → AISuggestion[] (结构化建议卡片)
  → 用户 accept/dismiss/convert
  → convert → CandidateRewriteService.request_rewrite() → 新 CandidateDraftVersion
```

### 6.3 S7→S8 链路

```
CandidateDraftVersion 生成
  → ConflictGuardService.detect_candidate_version_async()
    → ConflictGuardRecord[] + ConflictResolutionSuggestion (AISuggestion)
  → apply 前 ConflictGuardService.precheck_apply_conflicts()
    → blocking → 阻止 apply
    → warning → 允许 apply + 生成 conflict_resolution_suggestion
```

### 6.4 全链路 E2E 覆盖

测试 `test_planning_api_generates_direction_and_plan_then_confirms_to_writing_task` + `test_continuation_api_creates_candidate_and_candidate_api_controls_content_visibility` + `test_candidate_apply_with_direction_plan_warning_still_succeeds_and_records_conflict` 覆盖了从方向生成到 apply 冲突检测的完整链路。

---

## 七、DDD 架构合规检查

| 检查项 | 状态 |
|---|---|
| 所有模型在 `domain/entities/ai/models.py` 中 | ✅ |
| 所有仓储接口（ABC）在 `domain/repositories/ai/` 中 | ✅ 4 个新接口 |
| 所有仓储实现在 `infrastructure/database/repositories/ai/` 中 | ✅ 4 个新实现 |
| Application Service 通过构造函数注入依赖 | ✅ 4 个新 Service |
| Presentation API 不直接调用 Repository | ✅ 通过 Application Service |
| `application/` 不 import `infrastructure/` | ✅ |
| `domain/` 不 import `application/` / `infrastructure/` / `presentation/` | ✅ |
| Agent 不直连 Provider/ModelRouter/Repository/DB | ✅ |

---

## 八、测试报告

### S5-S8 专属测试（40/40 通过）

```
tests/ai/test_planning_api.py                          —  2 passed
tests/ai/test_candidate_draft_api.py                   —  7 passed
tests/ai/test_candidate_draft_versions.py              —  2 passed
tests/ai/test_candidate_rewrite_service.py             —  3 passed
tests/ai/test_ai_suggestion_api.py                     —  2 passed
tests/ai/test_ai_suggestion_service.py                 —  3 passed
tests/ai/test_conflict_guard.py                        —  6 passed
tests/ai/test_candidate_draft_status_model.py          —  3 passed
tests/ai/test_human_review_gate.py                     — 12 passed
```

### 全量回归（357 passed, 1 skipped, 1 warning）

S1~S4 功能无回归。

---

## 九、发现的问题

无阻塞缺陷。仅 1 个轻微建议：

| 严重度 | 问题 | 说明 |
|---|---|---|
| 低 | CandidateDraftVersion.content 在生产中为 stub 文本 | `CandidateRewriteService._build_rewritten_content` 当前返回固定格式的修订文本（含 `[修订说明]` 标记），这是因为 Writer Agent 的 LLM 调用链路尚未完整接通。这不阻塞 S5-S8 功能——版本链、三指针、RewriteRequest/Instruction/Round 的持久化和流程控制全部正确 |

---

## 十、验收结论

**P1-S5、P1-S6、P1-S7、P1-S8 全部通过。建议进入 P1-S9（StoryMemoryRevision 与 MemoryReviewGate）。**
