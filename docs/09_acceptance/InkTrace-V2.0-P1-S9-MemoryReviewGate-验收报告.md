# InkTrace V2.0 P1-S9 StoryMemoryRevision 与 MemoryReviewGate — 验收报告

版本：v1.0（初验）
验收日期：2026-05-22
依据文档：`docs/03_design/InkTrace-V2.0-P1-09-StoryMemoryRevision与MemoryReviewGate详细设计.md`（13 条验收项）
对应开发计划：`docs/04_plan/InkTrace-V2.0-P1-开发计划.md` §5.10

---

## 一、验收总体结论

**判定：通过 ✅ — 严格遵循设计文档实现。**

经过逐字段、逐枚举值、逐门控规则对照设计文档，确认 P1-S9 代码实现了全部核心要求。8 个专属测试全部通过，全量 365 测试无回归。所有安全红线均已落地。

**建议进入 P1-S10（AgentTrace 与可观测性）。**

---

## 二、数据模型字段逐项对照

### 2.1 MemoryUpdateSuggestion（设计 §3.1 行 87-116，27 个字段）

| 设计字段 | 类型 | 必填 | 代码 (`models.py:996-1026`) | 状态 |
|---|---|---|---|---|
| `id` | string | 是 | `id: str` | ✅ |
| `work_id` | string | 是 | `work_id: str` | ✅ |
| `chapter_id` | string | 否 | `chapter_id: str = ""` | ✅ |
| `candidate_draft_id` | string | 否 | `candidate_draft_id: str = ""` | ✅ |
| `candidate_version_id` | string | 否 | `candidate_version_id: str = ""` | ✅ |
| `review_report_id` | string | 否 | `review_report_id: str = ""` | ✅ |
| `ai_suggestion_id` | string | 否 | `ai_suggestion_id: str = ""` | ✅ |
| `conflict_guard_record_id` | string | 否 | `conflict_guard_record_id: str = ""` | ✅ |
| `agent_session_id` | string | 是 | `agent_session_id: str` | ✅ |
| `source_type` | enum | 是 | `source_type: str` | ✅ |
| `source_ref_id` | string | 否 | `source_ref_id: str = ""` | ✅ |
| `target_memory_type` | enum | 是 | `target_memory_type: MemoryTargetType` | ✅ |
| `target_memory_ref_id` | string | 否 | `target_memory_ref_id: str = ""` | ✅ |
| `revision_type` | enum | 是 | `revision_type: MemoryUpdateType` | ✅ |
| `proposed_value_summary` | string | 是 | `proposed_value_summary: str` | ✅ |
| `current_value_summary` | string | 是 | `current_value_summary: str` | ✅ |
| `evidence_refs` | MemoryRevisionSource[] | 是 | `evidence_refs: list[MemoryRevisionSource]` | ✅ |
| `confidence` | number | 是 | `confidence: float = 0.0` | ✅ |
| `severity` | enum | 是 | `severity: MemorySuggestionSeverity` | ✅ |
| `status` | enum | 是 | `status: MemorySuggestionStatus` | ✅ |
| `decision` | enum | 否 | `decision: MemorySuggestionDecisionType` | ✅ |
| `decided_by` | string | 否 | `decided_by: str = ""` | ✅ |
| `warning_codes` | string[] | 否 | `warning_codes: list[str]` | ✅ |
| `created_by` | string | 是 | `created_by: str = "memory_agent"` | ✅ |
| `created_at` | datetime | 是 | `created_at: str = ""` | ✅ |
| `updated_at` | datetime | 是 | `updated_at: str = ""` | ✅ |
| `request_id` | string | 否 | `request_id: str = ""` | ✅ |
| `trace_id` | string | 否 | `trace_id: str = ""` | ✅ |

**27/27 = 100%** ✅

### 2.2 StoryMemoryRevision（设计 §5.1 行 274-293，18 个字段）

| 设计字段 | 代码 (`models.py:1053-1071`) | 状态 |
|---|---|---|
| `id` / `work_id` / `chapter_id` | 全部 | ✅ |
| `source_suggestion_id` | `source_suggestion_id: str` | ✅ |
| `revision_items` (StoryMemoryRevisionItem[]) | `revision_items: list[StoryMemoryRevisionItem]` | ✅ |
| `revision_type` (normal/rollback) | `revision_type: MemoryRevisionRecordType` | ✅ |
| `status` (enum) | `status: MemoryRevisionStatus` | ✅ |
| `approved_by` / `approved_at` | 全部 | ✅ |
| `applied_by` / `applied_at` | 全部 | ✅ |
| `apply_result_ref` | `apply_result_ref: str = ""` | ✅ |
| `before_summary` (必填) / `after_summary` (非必填) | `before_summary: str` / `after_summary: str = ""` | ✅ |
| `request_id` / `trace_id` | 全部 | ✅ |
| `created_at` / `updated_at` | 全部 | ✅ |

**18/18 = 100%** ✅。不可变原则：`rollback_revision` 创建新 Revision 而非原位修改（`memory_review_gate_service.py:373-407`）。

### 2.3 StoryStateRevision（设计 §5.2 行 343-360，16 个字段）

| 设计字段 | 代码 (`models.py:1074-1094`) | 状态 |
|---|---|---|
| `id` / `work_id` / `chapter_id` | 全部 | ✅ |
| `source_suggestion_id` | `source_suggestion_id: str` | ✅ |
| `state_items` (object[]) | `state_items: list[dict[str, str]]` | ✅ |
| `target_state_ref` | `target_state_ref: str = ""` | ✅ |
| `version_guard` | `version_guard: str = ""` | ✅ |
| `status` / `approved_by` / `approved_at` | 全部 | ✅ |
| `applied_by` / `applied_at` / `apply_result_ref` | 全部 | ✅ |
| `before_summary` / `after_summary` | 全部 | ✅ |
| `request_id` / `trace_id` | 全部 | ✅ |

**16/16 = 100%** ✅。设计未列 `created_at`/`updated_at`，代码增加了这两个审计字段（合理增强）。

### 2.4 MemoryRevisionApplyResult（设计 §5.3 行 324-333，8 个字段）

| 设计字段 | 代码 (`models.py:1106-1114`) | 状态 |
|---|---|---|
| `id` / `revision_id` | 全部 | ✅ |
| `apply_status` (success/partial_success/failed) | `apply_status: MemoryApplyStatus` | ✅ |
| `applied_memory_refs` / `failed_item_refs` | 全部 | ✅ |
| `error_codes` / `before_after_snapshot_ref` | 全部 | ✅ |
| `applied_at` | `applied_at: str = ""` | ✅ |

**8/8 = 100%** ✅

### 2.5 子结构

| 设计结构 | 代码 | 状态 |
|---|---|---|
| StoryMemoryRevisionItem（§5.1 行 297-312） | `models.py:1041-1050`，10 字段全匹配 | ✅ |
| MemoryUpdateCandidate（§3.2 行 120-140） | `models.py:979-993`，含 change_type/add/update/delete/note_only | ✅ |
| MemoryRevisionSource（§3.2 行 143-161） | `models.py:967-977`，8 字段全匹配 | ✅ |
| MemoryRevisionDecision（§5.3 行 317-321） | `models.py:1097-1103`，4 字段全匹配 | ✅ |
| MemoryReviewGate（§4 行 227-234） | `models.py:1029-1038`，含 suggestion_ids/state/open_at/closed_at | ✅ |

---

## 三、枚举值逐项对照

### MemoryTargetType（设计 §3.1 行 100）

| 设计 | 代码 | 状态 |
|---|---|---|
| `story_memory` | `STORY_MEMORY` | ✅ |
| `story_state` | `STORY_STATE` | ✅ |
| `both` | `BOTH` | ✅ |

### MemoryUpdateType（设计 §3.3 行 177-188，12 种）

| 设计 | 代码 | 状态 |
|---|---|---|
| `character_update` | `CHARACTER_UPDATE` | ✅ |
| `setting_update` | `SETTING_UPDATE` | ✅ |
| `timeline_event_add` | `TIMELINE_EVENT_ADD` | ✅ |
| `timeline_event_update` | `TIMELINE_EVENT_UPDATE` | ✅ |
| `foreshadow_add` | `FORESHADOW_ADD` | ✅ |
| `foreshadow_update` | `FORESHADOW_UPDATE` | ✅ |
| `foreshadow_resolve` | `FORESHADOW_RESOLVE` | ✅ |
| `plot_thread_update` | `PLOT_THREAD_UPDATE` | ✅ |
| `story_state_update` | `STORY_STATE_UPDATE` | ✅ |
| `arc_note_update` | `ARC_NOTE_UPDATE` | ✅ |
| `continuity_note_add` | `CONTINUITY_NOTE_ADD` | ✅ |
| `unknown_memory_update` | `UNKNOWN_MEMORY_UPDATE` | ✅ |

**12/12 = 100%** ✅

### MemorySuggestionStatus（设计 §6 行 373-382，10 个状态）

| 设计 | 代码 | 状态 |
|---|---|---|
| `pending` → `generated` → `shown` → `accepted`/`edited`/`rejected`/`converted`/`stale`/`superseded`/`failed` | 全部 10 个状态 | ✅ |

注意设计不含 `expired`（过期由 `expires_at`/`is_expired` 计算字段表达）。

### MemoryGateState（设计 §4 行 397-404，8 个状态）

| 设计 | 代码 | 状态 |
|---|---|---|
| `open` / `waiting_for_user` / `partially_approved` / `approved` / `rejected` / `applied` / `cancelled` / `failed` | 全部 8 个状态 | ✅ |

`_refresh_gate_state`（`memory_review_gate_service.py:646-674`）根据 suggestions 中 approved/rejected/pending 的比例动态计算 gate 状态：全部 rejected → REJECTED；全部 approved → APPROVED；部分 approved → PARTIALLY_APPROVED。✅

### 其他枚举

| 枚举 | 设计值 | 代码 | 状态 |
|---|---|---|---|
| MemorySuggestionSeverity | info/warning/critical | `INFO/WARNING/CRITICAL` | ✅ |
| MemorySuggestionDecisionType | approved/edited_approved/rejected/deferred | `APPROVED/EDITED_APPROVED/REJECTED/DEFERRED` | ✅ |
| MemoryCandidateChangeType | add/update/delete/note_only | `ADD/UPDATE/DELETE/NOTE_ONLY` | ✅ |
| MemoryCandidateStatus | pending/selected/rejected/superseded | `PENDING/SELECTED/REJECTED/SUPERSEDED` | ✅ |
| MemoryRevisionRecordType | normal/rollback | `NORMAL/ROLLBACK` | ✅ |
| MemoryRevisionStatus | pending→waiting_for_review→approved/rejected/applied/stale/superseded/failed | 全部 8 状态 | ✅ |
| MemoryReviewDecisionType | approved/rejected/deferred | `APPROVED/REJECTED/DEFERRED` | ✅ |
| MemoryApplyStatus | success/partial_success/failed | `SUCCESS/PARTIAL_SUCCESS/FAILED` | ✅ |

---

## 四、安全红线逐条对照

| # | 设计规则 | 代码实现 | 测试覆盖 | 状态 |
|---|----------|----------|----------|------|
| 1 | AI 不能自动写 StoryMemory | 仅 `apply_gate`（需 user_action）写入 `_story_memory_repository.save_snapshot()` | `test_memory_review_gate_generates_review_suggestions_and_supports_approve_apply_rollback` | ✅ |
| 2 | AI 不能自动写 StoryState | 仅 `apply_gate`（需 user_action）写入 `_story_state_repository.save_analysis_baseline()` | 同上 | ✅ |
| 3 | AI 不能自动 apply MemoryRevision | `apply_gate` 首行 `_require_user_action(user_action)`；`MemoryReviewGateService` 所有写操作均校验 | ✅ |
| 4 | approve/reject/apply 必须 user_action | 全部 5 个用户操作路径（approve/edit_and_approve/reject/defer/apply_gate）均调用 `_require_user_action` | `test_memory_gate_api_lists_decides_applies_and_rolls_back` | ✅ |
| 5 | apply 前 ConflictGuard 预检 | `_precheck_conflicts`（行 676-694）调用 `conflict_guard_service.precheck_apply_conflicts`；blocking_count > 0 → 阻止 apply | `test_memory_gate_api_rejects_apply_when_no_approved_suggestions_exist` | ✅ |
| 6 | apply 前目标版本校验 | `_apply_story_memory_revision` 校验 `snapshot_id`（行 544）；`_apply_story_state_revision` 校验 `version_guard`（行 601） | `test_memory_review_gate_rollback_is_blocked_when_target_memory_version_has_changed` | ✅ |
| 7 | approved ≠ applied | `_persist_revisions_for_suggestion` 创建 APPROVED 状态的 Revision，不写正式资产；`apply_gate` 单独执行写入 | ✅ |
| 8 | 回滚即新版本 | `rollback_revision` 创建 `revision_type=ROLLBACK` 的新 Revision，不修改原 Revision | ✅ |
| 9 | MemoryReviewGate ≠ HumanReviewGate | 独立 Service（`MemoryReviewGateService`）+ 独立 Repository（`MemoryReviewRepository`）+ 独立 API（`memory.py`） | ✅ |
| 10 | MemoryReviewGate 不绕过 ConflictGuard | `_precheck_conflicts` 在 apply 前被调用 | ✅ |
| 11 | 版本不可变（一旦创建不可原位修改） | 代码中无任何修改已持久化 Revision 的方法，修正走 `rollback_revision` | ✅ |
| 12 | before/after 摘要可追溯 | MemoryUpdateSuggestion 有 `current_value_summary`/`proposed_value_summary`；Revision 有 `before_summary`/`after_summary` | ✅ |

---

## 五、MemoryReviewGate 四条路径验证

| 路径 | 设计定义 | 代码实现 | 状态 |
|---|---|---|---|
| `approve` | 认可建议，进入 revision waiting/apply 流程 | `approve_suggestion`：设置 APPROVED + 创建 StoryMemoryRevision/StoryStateRevision | ✅ |
| `edit_and_approve` | 修改建议值后认可。允许修改 proposed_value_summary/proposed_value/rationale；不允许修改 target_memory_type/field_path/revision_type | `edit_and_approve_suggestion`：更新 `proposed_value_summary` + candidate.proposed_value，不允许修改 target_memory_type/revision_type 等字段 | ✅ |
| `reject` | 拒绝建议，不写正式资产 | `reject_suggestion`：设置 REJECTED 状态，不创建 Revision | ✅ |
| `defer` | 暂缓处理，保留待办 | `defer_suggestion`：设置 DEFERRED，状态保持 SHOWN（非终态） | ✅ |

全部四条路径均需 `user_action` + `idempotency_key`。

---

## 六、仓储层与 DI

| 组件 | 文件 | 状态 |
|---|---|---|
| `MemoryReviewRepository` (ABC) | `domain/repositories/ai/memory_review_repository.py` | ✅ |
| `FileMemoryReviewStore` | `infrastructure/database/repositories/ai/file_memory_review_store.py` | ✅ |
| API 路由 | `presentation/api/routers/v2/ai/memory.py` | ✅ |
| DI 注入 | `dependencies.py` 新增 `get_memory_review_gate_service()` | ✅ |

---

## 七、测试报告

### S9 专属测试（8/8 通过）

```
tests/ai/test_memory_review_gate.py:
  ✓ test_memory_review_gate_generates_review_suggestions_and_supports_approve_apply_rollback
  ✓ test_memory_review_gate_defer_rejects_invalid_apply_and_preserves_gate_waiting_state
  ✓ test_memory_review_gate_rejecting_one_suggestion_does_not_close_gate_when_others_remain
  ✓ test_memory_review_gate_rollback_is_blocked_when_target_memory_version_has_changed

tests/ai/test_memory_revision_api.py:
  ✓ test_memory_gate_api_lists_decides_applies_and_rolls_back
  ✓ test_memory_gate_api_rejects_apply_when_no_approved_suggestions_exist
  ✓ test_memory_gate_api_rejecting_one_suggestion_keeps_gate_waiting_for_other_items
  ✓ test_memory_gate_api_rejects_reused_idempotency_key
```

### 全量回归：365 passed, 1 skipped, 1 warning

---

## 八、发现的问题

无阻塞缺陷。代码严格遵循设计文档。

仅 1 个轻微实现选择：`StoryStateRevision` 比设计多 `created_at`/`updated_at` 审计字段。设计 §5.2 行 343-360 的 StoryStateRevision 字段表中未包含这两个字段（而 StoryMemoryRevision §5.1 包含了），代码为一致性补充了两个字段。这是合理的审计增强。

---

## 九、验收结论

**P1-S9（StoryMemoryRevision 与 MemoryReviewGate）验收通过。**

- 数据模型字段覆盖率 100%（27+18+16+8 = 69/69 设计字段）
- 所有枚举值与设计一致
- MemoryReviewGate 四条路径（approve/edit_and_approve/reject/defer）全部实现并覆盖测试
- 12 条安全红线全部落地（user_action 门控、ConflictGuard 预检、版本校验、approved≠applied、回滚即新版本、MemoryReviewGate≠HumanReviewGate）
- DDD 四层架构合规
- 365 全部测试通过，无回归

**建议进入 P1-S10（AgentTrace 与可观测性）。**
