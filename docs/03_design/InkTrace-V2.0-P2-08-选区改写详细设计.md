# InkTrace V2.0-P2-08 选区改写与润色详细设计

版本：v1.2 / P2 模块级详细设计候选冻结版（二次修订）
状态：候选冻结（二次修订）
所属阶段：InkTrace V2.0 P2-S2
设计范围：选区改写/润色（扩写、重写、缩写、润色、对白优化、降 AI 味）

依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`（R-AI-ENH-04）
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§4.8）
- `docs/03_design/V2/InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计.md`

说明：选区改写不是独立 Agent，通过轻量级 ContextPack + Writer/Rewriter Model 实现。结果进入候选替换区，用户确认后由前端 Workbench Store 替换编辑器草稿，后续保存走 V1.1 Local-First。本文档不写代码、不修改源码。

**v1.3 修订记录（2026-07-03）：**
1. 冻结 P2-08 初期不引入服务端 Draft 持久化，继续保持 V1.1 Local-First 草稿权威在前端 Workbench。（补充问题 13）
2. 新增 `DraftSnapshot` 契约：`draft_text_hash`、`draft_length`、`range_text`，用于 rewrite/apply 冲突校验。（补充问题 13）
3. 修订 §3.3 / §3.4：后端不再“读取当前草稿正文”，改为校验客户端上传的草稿快照元信息。（补充问题 13）
4. 扩展 `SelectionRewriteCandidate` 与 DDL：新增 `draft_text_hash`、`draft_length`。（补充问题 13）
5. 扩展测试矩阵与安全边界，明确不上传、不持久化完整草稿正文。（补充问题 13）

**v1.2 修订记录（2026-06-09）：**
1. §2.3 SelectionRewriteCandidate 扩展：新增 chapter_revision、draft_revision、source_hash、source_text、context_before、context_after、applied_text、edited_before_apply、error_code、error_message。（问题 1+5）
2. §2.2 状态机扩展：新增 GENERATING、FAILED、CONFLICTED、EXPIRED。（问题 8）
3. §3.1 API 请求扩展 chapter_revision/draft_revision/source_hash，§3.3 后端校验规则冻结（6 项）。（问题 1+2）
4. §3.4 apply 冲突策略冻结：保守策略——仅 draft_revision 未变 + source_text 完全匹配时允许 apply，否则 409 selection_conflict。（问题 3）
5. §3.1 apply 方法新增 final_text 参数支持"编辑后接受"，§3.5 补充交互流程。（问题 4）
6. §3.6 apply 与 Local-First 对齐：apply 返回 patched_text + patch_range，由前端 Workbench Store 替换编辑器草稿，不绕过后端 draft API。（问题 9）
7. §1.2 改写模式表扩展：新增 prompt_key、OutputValidator、模式约束。（问题 7+12）
8. §4.2 DDL 扩展：匹配新增字段，source_text 恢复持久化（含 hash 双校验）。（问题 6）
9. §3.2 选区长度限制：2-3000 字。（问题 11）
10. §8 安全边界措辞修正："选区不泄露"→"最小必要上下文"。（问题 10）

**v1.1 修订记录（2026-06-09）：** 异步模式、source_text 不持久化、Repository 初版等，以 v1.2 为准。

---

## 一、文档定位与设计范围

### 1.1 文档定位

P2-08 覆盖选区改写/润色子系统的完整设计。核心原则：**改写结果不自动替换正文，用户确认后由前端 Workbench Store 替换编辑器草稿，后续保存走 V1.1 Local-First。**

### 1.2 六种改写模式

| 模式 | model_role | prompt_key | OutputValidator | 约束 |
|------|-----------|-----------|----------------|------|
| expand | writer | `selection_expand_v1` | `selection_rewrite_schema` | 输出字数 1.5-3× 原文 |
| rewrite | writer | `selection_rewrite_v1` | `selection_rewrite_schema` | 完全重写，保留核心事件 |
| abbreviate | writer | `selection_abbreviate_v1` | `selection_rewrite_schema` | 输出字数 30%-80% 原文 |
| polish | rewriter | `selection_polish_v1` | `selection_rewrite_schema` | 核心事件/人物/事实不变 |
| dialogue_opt | rewriter | `selection_dialogue_opt_v1` | `selection_rewrite_schema` | 不改变对白事实，仅优化口吻 |
| de_ai | rewriter | `selection_de_ai_v1` | `selection_rewrite_schema` | 不改变剧情事实，仅降低模板化表达 |

**OutputValidator 输出结构**：
```python
{
    "rewritten_text": str,
    "diff_summary": str,
    "risk_notes": list[str]
}
```
校验失败沿用 P0 OutputValidator 重试策略（max_retry=2）；最终失败不创建 candidate，或 candidate 标记 FAILED。

### 1.3 选区长度限制（冻结）

| 规则 | 限制 |
|------|------|
| 最小选区 | 2 字（中文）/ 5 字符（英文） |
| 最大选区 | 3000 字 |
| 超限 | 返回 400 `selection_too_long` / `selection_too_short` |

---

## 二、领域模型

### 2.1 SelectionRewriteMode 枚举

```python
class SelectionRewriteMode(StrEnum):
    EXPAND = "expand"
    REWRITE = "rewrite"
    ABBREVIATE = "abbreviate"
    POLISH = "polish"
    DIALOGUE_OPT = "dialogue_opt"
    DE_AI = "de_ai"
```

### 2.2 SelectionRewriteStatus 枚举

```python
class SelectionRewriteStatus(StrEnum):
    GENERATING = "generating"    # AI 生成中（异步模式下前端轮询）
    PENDING = "pending"          # 已生成，等待用户决策
    APPLIED = "applied"          # 用户已应用
    REJECTED = "rejected"        # 用户拒绝
    FAILED = "failed"            # 生成失败（LLM 错误 / OutputValidator 失败）
    CONFLICTED = "conflicted"    # apply 时选区已变化，不能安全替换
    EXPIRED = "expired"          # 草稿版本变化过大或候选过期
```

**状态流转**：
```
POST /rewrite → GENERATING
GENERATING + LLM 成功 → PENDING
GENERATING + LLM 失败 → FAILED
PENDING + apply 成功 → APPLIED
PENDING + apply 冲突 → CONFLICTED
PENDING + reject → REJECTED
PENDING + 草稿版本严重偏离 → EXPIRED
```

**EXPIRED 触发规则（冻结）**：

| 触发条件 | P2-08 实施 |
|------|------|
| candidate 创建超过 24 小时且 status=PENDING | **实现**：定时清理或 GET 查询时判定 |
| chapter_revision / draft_revision 已变化超过 3 次 | **预留**：P2-08 初期版本偏离只返回 CONFLICTED |
| 用户手动清理当前章节候选项 | **实现**：前端提供"清除历史改写"按钮 |

P2-08 初期最小实现：24 小时过期 + 手动清理。版本偏离不自动 EXPIRED，仅 apply 时返回 CONFLICTED。

### 2.3 SelectionRewriteCandidate

| 字段 | 类型 | 说明 |
|---|---|---|
| rewrite_id | str | 主键 `srw_{uuid_hex_12}` |
| chapter_id | str | 所属章节 |
| work_id | str | 作品 ID |
| rewrite_mode | SelectionRewriteMode | 改写模式 |
| source_text | str | 原始选中文本（用于 apply 时文本匹配校验） |
| source_hash | str | SHA-256(source_text)，双校验用 |
| source_start_pos | int | 选区起始字符位置（基于 draft_revision 时的快照） |
| source_end_pos | int | 选区结束字符位置 |
| rewritten_text | str | AI 生成的改写结果 |
| applied_text | str | 实际应用的文本（编辑后接受时 ≠ rewritten_text） |
| word_count_before | int | 改写前字数 |
| word_count_after | int | 改写后字数 |
| diff_summary | str | 差异摘要 |
| status | SelectionRewriteStatus | 状态 |
| model_role | str | 使用的模型角色 |
| chapter_revision | int | 生成改写时的章节 revision（V1.1 乐观锁版本号） |
| draft_revision | int | 生成改写时的草稿 revision |
| draft_text_hash | str | 生成改写时整章草稿全文 SHA-256 |
| draft_length | int | 生成改写时整章草稿全文长度 |
| edited_before_apply | bool | 用户是否编辑后才接受 |
| context_before | str | 选区前 100 字快照（apply 冲突时辅助定位） |
| context_after | str | 选区后 100 字快照 |
| error_code | str | 失败/冲突时的错误码 |
| error_message | str | 失败/冲突时的错误信息 |
| request_id | str | 请求 ID |
| trace_id | str | 追踪 ID |
| created_at | str | 创建时间 |
| applied_at | str | 应用时间 |

---

## 三、服务接口

### 3.1 SelectionRewriteService

```python
class SelectionRewriteService:
    def __init__(
        self,
        *,
        rewrite_repository: SelectionRewriteRepository,
        model_router: ModelRouter,
        context_pack_service: ContextPackService,
        chapter_service: ChapterService,
        trace_service,
    ) -> None: ...

    async def rewrite(
        self,
        *,
        work_id: str,
        chapter_id: str,
        chapter_revision: int,         # 章节版本号
        draft_revision: int,           # 草稿版本号
        draft_text_hash: str,          # 当前整章草稿全文哈希
        draft_length: int,             # 当前整章草稿全文长度
        source_text: str,
        source_hash: str,              # SHA-256(source_text)，后端校验
        start_pos: int,
        end_pos: int,
        mode: SelectionRewriteMode,
        caller_type: str = "user_action",
    ) -> SelectionRewriteCandidate: ...
    # 异步模式：创建 AIJob → 立即返回 candidate(status=GENERATING)
    # AIJob 内部：调用 Writer/Rewriter → OutputValidator → 写入 rewritten_text → status=PENDING

    async def get_candidate(self, rewrite_id: str) -> SelectionRewriteCandidate: ...

    async def apply(
        self,
        rewrite_id: str,
        *,
        final_text: str | None = None,    # null → 使用 rewritten_text；非 null → 用户编辑后的文本
        chapter_revision: int,             # 当前章节 revision
        draft_revision: int,               # 当前草稿 revision
        draft_text_hash: str,              # 当前整章草稿全文哈希
        draft_length: int,                 # 当前整章草稿全文长度
        range_text: str,                   # 当前 [start_pos, end_pos] 区间文本
        caller_type: str = "user_action",
    ) -> SelectionRewriteCandidate: ...
    # apply 不直接修改后端草稿（见 §3.6），返回 patched_text + patch_range 供前端 Workbench Store 替换

    async def reject(self, rewrite_id: str) -> SelectionRewriteCandidate: ...
```

### 3.2 选区长度验证

```python
MIN_SELECTION_LENGTH = 2       # 字
MAX_SELECTION_LENGTH = 3000    # 字

async def _validate_selection(self, source_text: str) -> None:
    if len(source_text) < MIN_SELECTION_LENGTH:
        raise ValidationError(400, "selection_too_short")
    if len(source_text) > MAX_SELECTION_LENGTH:
        raise ValidationError(400, "selection_too_long")
```

### 3.3 DraftSnapshot 与后端校验规则（冻结）

**冻结结论**：P2-08 初期不引入服务端 Draft 持久化。当前草稿权威源仍为前端 Workbench Local-First 状态；后端只接收客户端上传的 `DraftSnapshot` 元信息完成 rewrite/apply 校验。

`DraftSnapshot` 最小字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `draft_revision` | int | 当前前端草稿 revision |
| `draft_text_hash` | str | 当前整章草稿全文 SHA-256 |
| `draft_length` | int | 当前整章草稿全文长度 |
| `range_text` | str | apply 时当前区间文本 |

POST /selection-rewrite 时后端必须执行以下校验，任一项失败拒绝请求：

| # | 校验项 | 规则 | 错误码 |
|---|--------|------|--------|
| 1 | 位置范围 | `start_pos >= 0` | `invalid_selection_range` |
| 2 | 位置范围 | `end_pos > start_pos` | `invalid_selection_range` |
| 3 | 位置范围 | `end_pos <= draft_length` | `invalid_selection_range` |
| 4 | 草稿快照 | `draft_text_hash` 非空 | 400 `draft_snapshot_invalid` |
| 5 | 哈希匹配 | `sha256(source_text) == source_hash` | 400 `source_hash_mismatch` |
| 6 | 非空 | `source_text` 不为空字符串 | `selection_too_short` |

校验通过后，后端保存 `chapter_revision` / `draft_revision` / `draft_text_hash` / `draft_length` 快照到 candidate，供 apply 时冲突检测。

### 3.4 apply 冲突策略（冻结）

**P2-08 初期采用最保守策略：仅当草稿快照未变化且选区文本完全匹配时允许 apply。**

```
apply(rewrite_id, final_text, chapter_revision, draft_revision, draft_text_hash, draft_length, range_text)
  │
  ├─ 1. 校验 caller_type == "user_action"（否则 403）
  │
  ├─ 2. 校验 candidate.status == PENDING（否则 400）
  │
  ├─ 3. 校验草稿快照
  │     → draft_revision != candidate.draft_revision → 409 selection_conflict
  │     → draft_text_hash != candidate.draft_text_hash → 409 selection_conflict
  │     → draft_length < candidate.source_end_pos → 409 selection_conflict
  │
  ├─ 4. 校验当前区间文本
  │     → range_text != candidate.source_text → 409 selection_text_mismatch
  │
  ├─ 5. 确定最终文本：
  │     final_text 非空 → applied_text = final_text, edited_before_apply = true
  │     final_text 为空 → applied_text = rewritten_text, edited_before_apply = false
  │
  ├─ 6. 构造 patch：{ range: [start_pos, end_pos], replacement: applied_text }
  │
  ├─ 7. 返回 patch 给前端，由 Workbench Store 替换编辑器草稿
  │
  └─ 8. candidate.status = APPLIED / CONFLICTED, applied_at = now()
```

**APPLIED 标记语义（冻结）**：服务端 apply 成功后立即标记 APPLIED——表示用户已确认应用决策，**不代表草稿已成功持久化**。草稿持久化状态仍以 V1.1 Local-First 保存状态为准。若前端 Workbench Store 应用 patch 失败，前端应调用错误恢复流程并提示用户手动重试。P2-08 不引入 apply_ack 双向确认机制。

**职责边界（冻结）**：

1. 前端 Workbench 负责维护当前草稿全文、`draft_revision`、`draft_text_hash` 与 `draft_length`。
2. 后端 SelectionRewriteService 只保存候选快照字段并执行冲突校验，不持久化完整草稿正文。
3. P2-08 初期不新增 `drafts` 表，不把完整草稿正文写入 `edit_sessions`。

**冲突响应**：
```json
{
  "error": "selection_conflict",
  "message": "原文已被修改，请重新选区改写",
  "candidate_id": "srw_xxx",
  "detail": {
    "original_start_pos": 42,
    "original_end_pos": 80,
    "current_text_preview": "当前区间文本前50字..."
  }
}
```

### 3.5 "编辑后接受"交互流程

```
用户点击 [编辑后接受]
  → Diff 弹窗中 rewritten_text 变为可编辑
  → 用户修改文本后点击确认
  → 前端调用 POST /apply { final_text: "用户编辑后的文本", chapter_revision, draft_revision, draft_text_hash, draft_length, range_text }
  → 后端按 §3.4 校验 → 位置匹配 → applied_text = final_text, edited_before_apply = true
```

### 3.6 apply 与 V1.1 Local-First 对齐（冻结）

**apply 不直接修改后端草稿存储。** 与 V1.1 Local-First 架构对齐：

```
apply 返回:
  {
    rewrite_id: str,
    status: "applied",
    patch: {
      range: [start_pos, end_pos],
      replacement: str,          # applied_text
    }
  }

前端 Workbench Store 接收后:
  1. 在当前编辑器草稿中替换 [range] 为 replacement
  2. 触发 V1.1 Local-First 自动保存 / 用户手动保存链路
  3. 后端不直接调用 update_official_content 或绕过前端草稿状态
```

**不改 V1.1 保存链路**：apply 只是生成了一个 patch，前端 Store 负责应用和保存，与 V1.1 现有流程一致。P2-08 初期也**不扩展为云端 Draft 同步能力**。

### 3.7 选区 ContextPack（轻量版）

```python
async def _build_selection_context(
    self, chapter_id, source_text, start_pos, end_pos
) -> ContextPack:
    """
    最小必要上下文：
      选区文本 + 前后各 500 字环境 + Style DNA（若有）
      + 当前 Story State（角色在场、地点）
      + 当前章节摘要、相关角色卡
    总 Token 预算：~1500-2000
    不发送整章/整书内容。
    """
```

---

## 四、Repository 接口与持久化

### 4.1 SelectionRewriteRepository

```python
class SelectionRewriteRepository(ABC):
    @abstractmethod
    async def save(self, candidate: SelectionRewriteCandidate) -> SelectionRewriteCandidate: ...

    @abstractmethod
    async def get_by_id(self, rewrite_id: str) -> SelectionRewriteCandidate | None: ...

    @abstractmethod
    async def update(self, candidate: SelectionRewriteCandidate) -> SelectionRewriteCandidate: ...

    @abstractmethod
    async def get_by_chapter(self, chapter_id: str) -> list[SelectionRewriteCandidate]: ...

    @abstractmethod
    async def get_pending_by_chapter(self, chapter_id: str) -> list[SelectionRewriteCandidate]: ...
```

### 4.2 持久化表 DDL

```sql
CREATE TABLE IF NOT EXISTS selection_rewrite_candidates (
    rewrite_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    rewrite_mode TEXT NOT NULL,                -- expand / rewrite / abbreviate / polish / dialogue_opt / de_ai
    source_text TEXT NOT NULL DEFAULT '',       -- 原始选中文本（用于 apply 校验）
    source_hash TEXT NOT NULL DEFAULT '',       -- SHA-256(source_text)
    source_start_pos INTEGER NOT NULL DEFAULT 0,
    source_end_pos INTEGER NOT NULL DEFAULT 0,
    rewritten_text TEXT NOT NULL DEFAULT '',
    applied_text TEXT DEFAULT '',
    word_count_before INTEGER DEFAULT 0,
    word_count_after INTEGER DEFAULT 0,
    diff_summary TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'generating', -- generating / pending / applied / rejected / failed / conflicted / expired
    model_role TEXT NOT NULL DEFAULT '',
    chapter_revision INTEGER NOT NULL DEFAULT 0,
    draft_revision INTEGER NOT NULL DEFAULT 0,
    draft_text_hash TEXT NOT NULL DEFAULT '',
    draft_length INTEGER NOT NULL DEFAULT 0,
    edited_before_apply INTEGER DEFAULT 0,      -- bool
    context_before TEXT DEFAULT '',             -- 选区前 100 字快照
    context_after TEXT DEFAULT '',              -- 选区后 100 字快照
    error_code TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    request_id TEXT DEFAULT '',
    trace_id TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    applied_at TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_rewrite_chapter ON selection_rewrite_candidates(chapter_id);
CREATE INDEX IF NOT EXISTS idx_rewrite_chapter_status ON selection_rewrite_candidates(chapter_id, status);
CREATE INDEX IF NOT EXISTS idx_rewrite_work ON selection_rewrite_candidates(work_id);
```

---

## 五、API 设计

**异步模式（冻结）**：选区改写调用 LLM，耗时 5-20 秒。POST /selection-rewrite 立即返回 `rewrite_id`，前端轮询。

```
POST   /api/v2/ai/selection-rewrite
  Request:  {
              work_id: str,
              chapter_id: str,
              chapter_revision: int,           # 必传，apply 时校验
              draft_revision: int,             # 必传，apply 时校验
              draft_text_hash: str,            # 必传，当前整章草稿全文哈希
              draft_length: int,               # 必传，当前整章草稿全文长度
              source_text: str,
              source_hash: str,                # SHA-256(source_text)
              start_pos: int,
              end_pos: int,
              mode: str
            }
  Note:     后端执行 §3.3 六项校验 → 创建 AIJob → 创建 SelectionRewriteCandidate(status=GENERATING)
            → 保存 chapter_revision/draft_revision/draft_text_hash/draft_length 快照 → 立即返回 rewrite_id
  Response: { rewrite_id, status: "generating" }
  或 400 invalid_selection_range / source_hash_mismatch / selection_too_long / selection_too_short / draft_snapshot_invalid

GET    /api/v2/ai/selection-rewrite/{rewrite_id}
  Note:     前端轮询，status=GENERATING→loading, PENDING→Diff弹窗, FAILED→错误+重试
  Response: { rewrite_id, rewritten_text, word_count_before, word_count_after,
              diff_summary, status, source_start_pos, source_end_pos }

POST   /api/v2/ai/selection-rewrite/{rewrite_id}/apply
  Request:  {
              final_text: str | null,          # null→使用 rewritten_text
              chapter_revision: int,
              draft_revision: int,
              draft_text_hash: str,
              draft_length: int,
              range_text: str
            }
  Note:     后端执行 §3.4 冲突策略 → 返回 patch 供前端 Store 替换
  Response: { rewrite_id, status: "applied",
              patch: { range: [int, int], replacement: str } }
  或 409 selection_conflict / selection_text_mismatch / 400 status_not_pending / 403 caller_type_forbidden

POST   /api/v2/ai/selection-rewrite/{rewrite_id}/reject
  Response: { rewrite_id, status: "rejected" }
```

---

## 六、前端交互

### 6.1 SelectionToolbar

选中文本后，在选区上方/下方浮动工具栏：

```
┌──────────────────────────────────────────┐
│ [扩写] [重写] [缩写] [润色] [对白优化] [降AI味] │
└──────────────────────────────────────────┘
```

选区不满足长度限制（<2 或 >3000 字）时工具栏不显示。

### 6.2 Diff 弹窗（SelectionRewriteDiffModal.vue）

```
┌─────────────────────────────────────┐
│  改写结果预览                       │
│  ─────────────────────────────────  │
│  原文           │  改写结果         │
│  "他走进房间"   │  "他缓步走进昏暗  │
│                 │   的房间，空气中  │
│                 │   弥漫着..."      │
│  ─────────────────────────────────  │
│  字数：4 → 28  |  模式：扩写       │
│                                     │
│  [编辑后接受] [直接接受] [拒绝]    │
└─────────────────────────────────────┘
```

[编辑后接受]：rewritten_text 变为可编辑文本框 → 用户修改 → 确认 → POST /apply { final_text }

---

## 七、测试策略

| # | 用例 | 验证点 |
|---|---|---|
| T1 | 选区扩写 | rewritten_text 字数 > source_text 字数（1.5-3×） |
| T2 | 选区缩写 | rewritten_text 字数 < source_text 字数（30%-80%） |
| T3 | 润色不变内容 | 核心含义不变，表达优化 |
| T4 | 用户接受后返回 patch | apply 返回 { patch: { range, replacement } }，前端 Store 替换草稿 |
| T5 | 接受后不直接写入正式章节 | chapter.content 不变（需手动保存） |
| T6 | 选区为空不触发 | 无选区时工具栏不显示 |
| T7 | Agent 不能调用 apply | caller_type=agent 被拒绝 |
| T8 | 选区外内容不变 | patch.range 之外内容无变化 |
| T9 | apply 前原文已修改 → 409 | draft_revision 不匹配或 source_text 不匹配 → selection_conflict |
| T10 | source_hash 校验失败 | sha256(source_text) ≠ source_hash → 400 source_hash_mismatch |
| T11 | 编辑后接受 | apply({ final_text: "用户编辑版" }) → applied_text = final_text, edited_before_apply = true |
| T12 | 选区超长 | source_text > 3000 字 → 400 selection_too_long |
| T13 | 选区过短 | source_text < 2 字 → 400 selection_too_short |
| T14 | draft 位置文本不匹配 | `range_text ≠ source_text` → 409 selection_text_mismatch（冲突类，非参数错误） |
| T15 | OutputValidator 失败 | schema 校验失败 → 重试 → 最终失败 → status=FAILED |
| T16 | rewrite 缺少草稿快照 | `draft_text_hash` 为空 → 400 `draft_snapshot_invalid` |
| T17 | apply 时整章草稿哈希变化 | `draft_text_hash` 不一致 → 409 `selection_conflict` |
| T18 | apply 时整章长度不足 | `draft_length < source_end_pos` → 409 `selection_conflict` |

---

## 八、安全边界

| 约束 | 实施 |
|---|---|
| 不自动替换正文 | apply 返回 patch，由前端 Store 替换编辑器草稿，不直接写后端正式章节 |
| Agent 不能 apply | caller_type 校验，非 user_action → 403 |
| 最小必要上下文 | ContextPack 仅发送选区 + 前后各 500 字 + Story/Style 信息，不发送整章/整书 |
| 不改变选区外内容 | patch 仅覆盖 [start_pos, end_pos] |
| 选区长度限制 | 2-3000 字，超限拒绝 |
| apply 前双重校验 | `draft_revision / draft_text_hash / range_text` 任一不通过 → 409 |
| source_hash 校验 | POST 时后端校验 sha256(source_text) == source_hash |
| 不持久化完整草稿正文 | P2-08 初期只保存 `draft_revision / draft_text_hash / draft_length`，不新增服务端 Draft 正文存储 |
| 模式约束 | expand 1.5-3× / abbreviate 30%-80% / polish 事实不变 / de_ai 剧情不变 |

---

## 九、代码改动面

```
新增：
  application/services/ai/selection_rewrite_service.py
  domain/repositories/ai/selection_rewrite_repository.py
  infrastructure/persistence/sqlite_selection_rewrite_repo.py
  domain/validators/selection_rewrite_schema.py        # OutputValidator schema
  presentation/api/routers/v2/ai/selection_rewrite.py
  frontend/src/components/workspace/SelectionRewriteToolbar.vue
  frontend/src/components/workspace/SelectionRewriteDiffModal.vue

数据库迁移：
  新增表 selection_rewrite_candidates

修改：
  domain/entities/ai/models.py              # 追加 SelectionRewriteCandidate, SelectionRewriteMode, SelectionRewriteStatus
  application/services/ai/prompt_service.py # 新增 6 个 selection_* prompt_key
  presentation/api/app.py                   # 注册路由

不改：
  application/services/v1/chapter_service.py   # V1.1 保存链路不动
  application/services/ai/tool_facade.py
```
