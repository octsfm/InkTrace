# InkTrace V2.0-P2-08 后端草稿与 Apply 冲突补充设计

版本：v0.1 / 待冻结草案
状态：待确认，不得直接作为实现依据
所属阶段：InkTrace V2.0 P2-S3 / P2-08
日期：2026-07-03

依据文档：

- `docs/03_design/InkTrace-V2.0-P2-08-选区改写详细设计.md`
- `docs/03_design/InkTrace-V2.0-P2-11-API与前端集成边界详细设计.md`
- `docs/04_plan/InkTrace-V2.0-P2-开发计划.md`
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`

---

## 一、补充设计目的

P2-08 现有正式设计已冻结了以下规则：

1. `POST /selection-rewrite` 与 `POST /apply` 都依赖 `draft_revision`。
2. `apply` 冲突策略要求后端读取“当前草稿内容”和“当前草稿 revision”。
3. `apply` 不直接写正式正文，仍由前端 Workbench Store 应用 patch，后续保存走 V1.1 Local-First。

但当前运行时架构中：

1. `edit_sessions` 仅保存 `last_open_chapter_id / cursor_position / scroll_top`。
2. 后端没有独立 `drafts` 表。
3. V1.1 现状中“当前草稿”实际只存在前端 Workbench Local-First 状态中。

因此，`P2-08` 现有设计缺少一个关键冻结决策：

> **后端在不持有服务端草稿正文的前提下，如何完成 rewrite/apply 冲突校验。**

本补充设计用于冻结该决策，避免实现阶段自行发明“服务端草稿模型”。

---

## 二、结论（建议冻结）

### 2.1 P2-08 初期不引入服务端 Draft 持久化

P2-08 初期版本：

1. **不新增服务端 `drafts` 表**。
2. **不把草稿正文持久化到 `edit_sessions`**。
3. **不引入云端草稿同步语义**。

理由：

1. 现有 V1.1 明确采用 Local-First，当前草稿权威源在前端 Workbench。
2. 若在 P2-08 临时引入服务端 draft，会实质扩展到“草稿同步模型”，超出当前模块范围。
3. 该能力更接近未来 P3 多端同步/云草稿能力，不应由 P2-08 实现阶段偷偷落地。

### 2.2 P2-08 冲突校验改为“客户端草稿快照契约”

P2-08 后端不主动读取服务端草稿正文，而是读取**前端请求携带的草稿快照元信息**完成校验。

冻结结论：

1. 前端 Workbench 仍是“当前草稿”的运行时来源。
2. 后端只基于请求中的草稿快照元信息做校验与 patch 生成。
3. 后端**不持久化完整草稿正文**，仅持久化必要快照字段。

---

## 三、DraftSnapshot 契约（新增冻结）

### 3.1 DraftSnapshot 定义

新增轻量契约 `DraftSnapshot`：

```json
{
  "draft_revision": 12,
  "draft_text_hash": "sha256(full_draft_text)",
  "draft_length": 5231,
  "range_text": "当前选区文本"
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `draft_revision` | int | 当前前端 Workbench 草稿版本号 |
| `draft_text_hash` | str | 当前整章草稿全文 SHA-256 |
| `draft_length` | int | 当前整章草稿全文长度 |
| `range_text` | str | 当前 `[start_pos, end_pos]` 区间文本 |

说明：

1. `draft_text_hash` 用于判断整章草稿是否发生过任意变化。
2. `range_text` 用于判断目标区间文本是否仍等于 `source_text`。
3. `draft_length` 用于替代“服务端读取当前 draft 后计算长度”的能力。
4. `range_text` 只在需要区间校验的请求中出现。

### 3.2 为什么不用完整 draft 正文

P2-08 初期不要求客户端上传完整草稿正文，原因如下：

1. 只做冲突检测和 patch 生成，不需要后端完整重建当前草稿。
2. 避免把完整正文作为 API 常规负载上传和记录。
3. 与“最小必要信息”原则更一致。

---

## 四、SelectionRewriteCandidate 扩展（补充冻结）

在原有 `SelectionRewriteCandidate` 基础上，新增两个持久化字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `draft_text_hash` | str | 创建 rewrite 时整章草稿全文哈希 |
| `draft_length` | int | 创建 rewrite 时整章草稿全文长度 |

说明：

1. `draft_revision` 仍保留，语义不变。
2. `draft_text_hash` 与 `draft_revision` 共同组成“草稿快照指纹”。
3. 不新增 `draft_text` 字段，不保存完整草稿正文。

---

## 五、API 补充冻结

### 5.1 POST `/api/v2/ai/selection-rewrite`

请求新增字段：

```json
{
  "work_id": "work_xxx",
  "chapter_id": "chapter_xxx",
  "chapter_revision": 3,
  "draft_revision": 12,
  "draft_text_hash": "sha256(full_draft_text)",
  "draft_length": 5231,
  "source_text": "原始选中文本",
  "source_hash": "sha256(source_text)",
  "start_pos": 42,
  "end_pos": 80,
  "mode": "rewrite"
}
```

冻结规则：

1. `draft_text_hash` 必传。
2. `draft_length` 必传。
3. `source_text` 仍代表当前选区文本。
4. `source_hash = sha256(source_text)` 规则不变。

### 5.2 POST `/api/v2/ai/selection-rewrite/{rewrite_id}/apply`

请求新增字段：

```json
{
  "final_text": "用户编辑后的文本或 null",
  "chapter_revision": 3,
  "draft_revision": 12,
  "draft_text_hash": "sha256(full_draft_text)",
  "draft_length": 5231,
  "range_text": "当前区间文本"
}
```

冻结规则：

1. `draft_text_hash` 必传。
2. `draft_length` 必传。
3. `range_text` 必传。
4. `final_text` 为空时沿用 `rewritten_text`。

---

## 六、后端校验规则修订（补充冻结）

### 6.1 rewrite 请求校验

将原“读取当前草稿内容”的表述改为“读取请求中的 DraftSnapshot 元信息”。

`POST /selection-rewrite` 校验改为：

| # | 校验项 | 规则 | 错误码 |
|---|---|---|---|
| 1 | 位置范围 | `start_pos >= 0` | `invalid_selection_range` |
| 2 | 位置范围 | `end_pos > start_pos` | `invalid_selection_range` |
| 3 | 位置范围 | `end_pos <= draft_length` | `invalid_selection_range` |
| 4 | 文本非空 | `source_text` 非空 | `selection_too_short` |
| 5 | 哈希匹配 | `sha256(source_text) == source_hash` | `source_hash_mismatch` |
| 6 | 草稿哈希非空 | `draft_text_hash` 非空 | `draft_snapshot_invalid` |

说明：

1. 初次 rewrite 创建时，后端**不再假设自己能读取当前草稿全文**。
2. 因此“`current_draft[start:end] == source_text`”这一条改为依赖客户端在 apply 前再次校验。
3. rewrite 阶段仍能通过 `draft_length + source_hash + source_text + range` 建立候选快照。

### 6.2 apply 冲突校验

`POST /apply` 校验改为：

```text
apply(rewrite_id, final_text, chapter_revision, draft_revision, draft_text_hash, draft_length, range_text)
  |
  |- 1. caller_type == "user_action"
  |- 2. candidate.status == PENDING
  |- 3. draft_revision == candidate.draft_revision
  |- 4. draft_text_hash == candidate.draft_text_hash
  |- 5. draft_length >= candidate.source_end_pos
  |- 6. range_text == candidate.source_text
  |- 7. 构造 patch
  |- 8. 返回 patch，candidate.status = APPLIED / CONFLICTED
```

对应错误码：

| 场景 | 错误码 |
|---|---|
| `draft_revision` 不一致 | `selection_conflict` |
| `draft_text_hash` 不一致 | `selection_conflict` |
| `draft_length < source_end_pos` | `selection_conflict` |
| `range_text != source_text` | `selection_text_mismatch` |

说明：

1. `draft_revision` 和 `draft_text_hash` 任一不一致，均表示草稿快照已变化。
2. `range_text` 不一致表示目标区间原文已变化。
3. `selection_text_mismatch` 仍保留，语义更明确：**目标区间文本与候选基线文本不一致**。

---

## 七、与 Local-First 的职责边界（补充冻结）

P2-08 初期职责边界冻结如下：

### 7.1 前端 Workbench 负责

1. 维护当前草稿全文。
2. 维护 `draft_revision` 递增。
3. 计算 `draft_text_hash`。
4. 在 rewrite/apply 请求时提供 DraftSnapshot。
5. 接收 patch 后替换当前草稿并进入现有保存链路。

### 7.2 后端 SelectionRewriteService 负责

1. 验证 `caller_type=user_action`。
2. 保存候选快照字段：`draft_revision / draft_text_hash / draft_length / source_text / range`。
3. 在 apply 时执行保守冲突校验。
4. 返回 patch。
5. 更新 candidate 状态。

### 7.3 后端明确不负责

1. 不保存完整草稿正文。
2. 不维护服务端草稿权威版本。
3. 不进行云端草稿同步。
4. 不直接写正式正文。

---

## 八、数据与日志边界（补充冻结）

### 8.1 允许持久化

允许持久化：

1. `draft_revision`
2. `draft_text_hash`
3. `draft_length`
4. `source_text`
5. `source_hash`
6. `context_before / context_after`

### 8.2 禁止持久化

禁止新增持久化：

1. 完整草稿正文
2. 完整章节正文镜像
3. 完整客户端 Workbench DraftSnapshot 正文

### 8.3 禁止日志记录

日志中禁止记录：

1. 完整 `source_text` 以外的全文草稿内容
2. 完整 `final_text`
3. 完整 `context_before + context_after + source_text` 拼接后的大段正文

允许日志中记录：

1. `rewrite_id`
2. `chapter_id`
3. `draft_revision`
4. `draft_text_hash` 前 8 位
5. 错误码

---

## 九、测试补充冻结

在原有 `P2-08` 测试矩阵基础上，追加以下测试：

| # | 用例 | 预期 |
|---|---|---|
| N1 | rewrite 请求缺少 `draft_text_hash` | 400 `draft_snapshot_invalid` |
| N2 | rewrite 请求 `end_pos > draft_length` | 400 `invalid_selection_range` |
| N3 | apply 时 `draft_text_hash` 变化 | 409 `selection_conflict` |
| N4 | apply 时 `draft_revision` 未变但 `range_text` 变化 | 409 `selection_text_mismatch` |
| N5 | apply 时 `draft_length < source_end_pos` | 409 `selection_conflict` |
| N6 | apply 成功仅返回 patch，不写正式正文 | `chapter.content` 不变 |

---

## 十、实现影响面（供冻结后使用）

若本补充设计被确认冻结，则 `P2-08` 实现需同步调整：

1. `SelectionRewriteCandidate` 实体追加 `draft_text_hash / draft_length`。
2. `selection_rewrite_candidates` 表追加两列：
   - `draft_text_hash TEXT NOT NULL DEFAULT ''`
   - `draft_length INTEGER NOT NULL DEFAULT 0`
3. `POST /selection-rewrite` 请求模型追加：
   - `draft_text_hash`
   - `draft_length`
4. `POST /apply` 请求模型追加：
   - `draft_text_hash`
   - `draft_length`
   - `range_text`
5. 前端 `useSelectionRewriteStore` 在 create/apply 时计算并上传上述字段。

---

## 十一、待确认项

以下项目需人工确认后，方可把本草案并入正式冻结文档：

1. `draft_text_hash + draft_revision + draft_length` 是否足够作为 P2-08 初期冲突快照。
2. `range_text` 不一致时是否继续使用 `selection_text_mismatch`，还是统一并入 `selection_conflict`。
3. 是否需要在 `GET /selection-rewrite/{id}` 响应中回传 `draft_revision / draft_text_hash` 供前端自检。
4. 本补充设计确认后，是否直接回写进：
   - `docs/03_design/InkTrace-V2.0-P2-08-选区改写详细设计.md`
   - `docs/03_design/InkTrace-V2.0-P2-11-API与前端集成边界详细设计.md`

---

## 十二、建议裁决

建议采用以下最小冻结方案：

1. **不引入服务端草稿持久化。**
2. **以客户端 DraftSnapshot 元信息完成 rewrite/apply 冲突校验。**
3. **仅追加 `draft_text_hash / draft_length / range_text` 三类字段，不上传完整草稿正文。**
4. **保持 apply 只返回 patch，不修改 V1.1 Local-First 主保存链。**

该方案对现有架构侵入最小，且不会把 P2-08 意外扩展成“云端草稿同步”项目。
