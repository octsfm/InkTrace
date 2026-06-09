# InkTrace V2.0-P2-05 @ 标签引用系统详细设计

版本：v1.2 / P2 模块级详细设计候选冻结版（二次修订）
状态：候选冻结（二次修订）
所属阶段：InkTrace V2.0 P2-S2
设计范围：正文 @ 标签引用系统（联想、高亮、悬停、持久化）

依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`（R-AI-CITE-02）
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§4.5）
- `docs/03_design/InkTrace-V2.0-P2-02-CitationLink详细设计.md`

说明：本文档冻结 @ 标签引用子系统设计。正文存储方案采用**方案 A（位置映射）**：正文保持纯文本，mentions 独立存储在 `chapter_mentions` 表，前端渲染层做高亮。

**v1.2 修订记录（2026-06-09）：**
1. §2.1-2.3 枚举代码块拆分闭合（MentionSource / MentionStatus / MentionEntityType 各自独立代码块），修正编号为 2.1-2.5。
2. 从 MentionStatus 中移除 PENDING——AI 建议待采纳状态由 AISuggestion.status=pending 管理，不写入 chapter_mentions 表。
3. §7.4 保存时全量重建策略修正：已有 mention 的 entity_id 不可变，同名实体消歧结果受保护；仅对新增 @文本触发联想/消歧。
4. §6.1 ChapterMentionRepository.replace_by_chapter 改为全量提交 + 后端 diff/upsert（非物理 DELETE + INSERT），保证 mention_id 跨保存稳定。
5. §7.5 新增"区间唯一性冻结规则"：禁止完全重复、禁止交叉重叠、允许相邻、不支持嵌套 mention。
6. GET /api/v2/mentions/{id}/summary 响应新增 entity_name_snapshot、entity_current_name、status 字段，支持实体更名后的 stale 展示。
7. §5.3 新增关键约束：所有样式差异均为渲染层表现，不写入正文、不影响导出。
8. §4.5 MentionTooltip 更新为支持更名/删除状态的三种展示样式。

**v1.1 修订记录（2026-06-09）：**
1. 新增第七章"位置同步策略"（原前言描述升级为正式章节），明确方案 A1（保存时全量重建），补充编辑时实时维护、保存时全量重建流程、后端校验规则、位置失效降级展示。
2. 第五章新增 §5.3"两种来源的渲染差异"和 §5.4"MentionHighlight 渲染逻辑"，明确 user_input 与 ai_suggestion 的 start_pos 语义差异、渲染样式差异、保存行为差异。
3. 第四章 §4.4 MentionHighlight 扩展为两种来源的双模式渲染说明。
4. 第九章测试策略新增 T9-T14 共 6 个测试用例，覆盖位置同步、渲染差异、ai_suggestion broken 等场景。
5. 章节编号修正：第七章 → 位置同步策略（新），第八章 → API 设计，第九章 → 测试策略，第十章 → 代码改动面。

---

## 一、文档定位与设计范围

### 1.1 文档定位

P2-05 覆盖正文 @ 标签引用系统的完整设计。这是 P2 中**唯一涉及 V1.1 编辑器（PureTextEditor）深度改造**的子系统。

核心原则（来自 P2 架构 §4.5 已冻结）：**正文保持纯文本，@ 引用关系独立存储，前端渲染层做高亮，不把特殊标记写入正文内容。**

### 1.2 设计范围

- ChapterMention 领域模型与 MentionSource 枚举。
- MentionService：关联想查询、mentions CRUD。
- 前端 MentionDetector / MentionPopup / MentionHighlight / MentionTooltip 组件设计。
- AI @ 引用建议流程（进入 AI Suggestion Store）。
- 同名实体消歧策略。
- 实体删除后的 mention 降级策略。
- API 端点。
- 测试策略。

### 1.3 不覆盖范围

- Citation Link 系统（属于 P2-02）。
- PureTextEditor 核心编辑逻辑（属于 P0，本模块仅 hook 进去）。

---

## 二、领域模型

### 2.1 MentionSource 枚举

```python
class MentionSource(StrEnum):
    USER_INPUT = "user_input"          # 用户手动 @
    AI_SUGGESTION = "ai_suggestion"    # AI 建议采纳后建立
```

### 2.2 MentionStatus 枚举

**仅用于已建立的 ChapterMention 记录。AI 建议待采纳状态不在此枚举中，属于 `AISuggestion.status=pending`（见 P1-07），不写入 `chapter_mentions` 表。**

```python
class MentionStatus(StrEnum):
    ACTIVE = "active"                  # 位置有效，实体有效，正常渲染
    BROKEN = "broken"                  # 正文编辑导致位置失效
    STALE = "stale"                    # 实体名称已变更
    INACTIVE_ENTITY = "inactive_entity"  # 实体被删除/归档
```

### 2.3 MentionEntityType 枚举

```python
class MentionEntityType(StrEnum):
    CHARACTER = "character"
    LOCATION = "location"
    EVENT = "event"
    FORESHADOW = "foreshadow"
```

### 2.4 ChapterMention

| 字段 | 类型 | 说明 |
|---|---|---|
| mention_id | str | 主键 `m_{uuid_hex_12}` |
| chapter_id | str | 所属章节 |
| work_id | str | 所属作品（冗余，方便跨章查询） |
| entity_type | MentionEntityType | 实体类型 |
| entity_id | str | 实体 ID |
| entity_name_snapshot | str | **快照**：mention 创建时的实体名称。实体后续改名不影响展示。悬停时通过 API 动态解析 entity_current_name，不依赖此字段 |
| start_pos | int | 正文中起始字符位置 |
| end_pos | int | 正文中结束字符位置 |
| source | MentionSource | 来源 |
| ai_suggestion_id | str | 关联 AI Suggestion ID |
| status | MentionStatus | 当前状态（active/broken/stale/inactive_entity）。PENDING 不在此列——AI 建议待采纳状态由 AISuggestion.status=pending 管理，不写入 chapter_mentions 表 |
| is_active | bool | 保留字段，status=active 时=true，其余=false |
| validation_detail | str | 校验详情 |
| created_at | str | 创建时间 |
| updated_at | str | 更新时间 |

### 2.5 MentionSuggestion

前端联想返回值（非持久化）。

| 字段 | 类型 | 说明 |
|---|---|---|
| entity_type | str | 类型 |
| entity_id | str | ID |
| entity_name | str | 名称 |
| match_type | str | "prefix" / "fuzzy" |
| last_used_at | str | 最近使用时间 |
| summary_preview | str | 一句话摘要（≤60字符） |

---

## 三、服务接口

### 3.1 MentionService

```python
class MentionService:
    def __init__(
        self,
        *,
        mention_repository: ChapterMentionRepository,          # 新增
        character_repository: CharacterRepository,             # 复用 V1.1
        writing_asset_service: WritingAssetService,            # 复用 V1.1
        ai_suggestion_service: AISuggestionService | None,    # 复用 P1
    ) -> None: ...

    # ── 联想查询 ──
    async def suggest(
        self, work_id: str, query: str,
        entity_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[MentionSuggestion]: ...

    # ── mentions CRUD ──
    async def replace_mentions(
        self, chapter_id: str, mentions: list[ChapterMention]
    ) -> list[ChapterMention]: ...
    # 【冻结】全量提交 + 后端 diff/upsert：
    #   已存在 mention_id → UPDATE；新增 → INSERT；未提交旧 mention → 标记 broken。
    #   不物理删除，保证 mention_id 跨保存稳定。

    async def get_by_chapter(self, chapter_id: str) -> list[ChapterMention]: ...

    async def get_summary(self, mention_id: str) -> MentionSummary: ...

    # ── 清理 ──
    async def mark_entity_deleted(
        self, entity_type: str, entity_id: str
    ) -> None: ...
    # 【冻结触发来源】当 Character/Location/Foreshadow/Event 被删除或归档时，
    # 由对应资产服务（WritingAssetService）在删除用例中调用此方法。
    # 不删除 mention 记录——将 status→INACTIVE_ENTITY, is_active→false。
    # 前端 tooltip 显示"实体已删除"。历史数据仍可追溯。
```

### 3.2 联想搜索策略

```python
async def suggest(self, work_id, query, entity_types=None, limit=10):
    """
    1. 前缀匹配：entity_name LIKE 'query%'，按最近使用时间排序
    2. 模糊补齐：结果 < limit → 编辑距离 ≤2 的模糊匹配补足
    3. 【冻结】只返回 active 实体：deleted/archived/disabled 不出现在联想中。
       历史 mention 指向已删除实体的，仅在 tooltip 中降级展示。
    4. 按 entity_types 过滤
    5. 同名实体处理：返回所有同名候选项，让用户选择目标
    6. 返回 MentionSuggestion 列表
    """
```

### 3.3 同名实体消歧

当 `suggest` 返回的同名实体 > 1 时，前端联想菜单展示：
```
张三（人物·主角）
张三（人物·配角·第3章出场）
```
用户选择具体实体后，`entity_id` 确定。

---

## 四、前端架构

### 4.1 组件树

```
PureTextEditor (P0 - 扩展)
├── @MentionDetector      # 检测 @ 输入
├── @MentionPopup         # 联想菜单（浮动定位）
├── @MentionHighlight     # 行内高亮渲染
└── @MentionTooltip       # 悬停资产卡片
```

### 4.2 MentionDetector

```
触发时机：用户输入 '@' 字符
- compositionstart 时暂停检测（中文输入法激活）
- compositionend 后再检查光标前文本是否为 @
- 中文输入法候选期间不触发 popup
防抖：300ms
取消：Escape / 点击其他地方 / 输入空格 / 输入法激活
```

### 4.3 MentionPopup

```
位置：光标正下方，浮动定位
内容：
  👤 人物
    张三 — 主角，当前位于长安城
    张三丰 — 配角，武当掌门
  📍 地点
    长安城 — 都城
  📅 事件
    ...
最多 10 条，按类型分组。
键盘：↑↓ 选择，Enter 确认，Escape 关闭。
```

### 4.4 MentionHighlight

**user_input 来源**（正文中含 @ 符号）：
```html
<span class="mention mention--user mention--character" data-mention-id="m_xxx">
  @张三
</span>
```
样式：蓝色半透明背景 + 蓝色实线下划线，与普通文本明确区分。

**ai_suggestion 来源**（正文中无 @ 符号，纯文本实体名）：
```html
<span class="mention mention--ai mention--character" data-mention-id="m_xxx">
  张三
</span>
```
样式：紫色虚线下划线，无背景色——区分于用户手动 @，表示这是 AI 建议的引用标记。

详细渲染逻辑见 §5.3-5.4。

### 4.5 MentionTooltip

```
触发：mouseenter（延迟 500ms）
内容：GET /api/v2/mentions/{mention_id}/summary
      ┌──────────────────────────────────┐
      │ 人物：张三                       │
      │ 主角，当前位于长安城             │
      │ 状态：怒气                       │
      │ 最后更新：2026-06-08             │
      │ [查看完整人物卡]                 │
      └──────────────────────────────────┘

      若 entity_name_snapshot ≠ entity_current_name（实体已更名）：
      ┌──────────────────────────────────┐
      │ 人物：张三（已更名：张三 → 张三丰）│
      │ ...                              │
      └──────────────────────────────────┘

      若 status=inactive_entity（实体已删除）：
      ┌──────────────────────────────────┐
      │ 人物：张三（实体已删除）          │
      │ 该 mention 已失效，历史数据仅供追溯│
      └──────────────────────────────────┘
```

### 4.6 useMentionStore（Pinia）

```typescript
// 前端 mentions 状态管理
interface MentionState {
  mentions: Map<string, ChapterMention[]>  // chapter_id → mentions
  suggestions: MentionSuggestion[]
  popupVisible: boolean
  popupPosition: { x: number; y: number }
  activeQuery: string
}

// Actions: fetchSuggestions, saveMentions, insertMention, removeMention
```

---

## 五、AI @ 引用建议

### 5.1 生成路径

```
Memory Agent / Reviewer Agent 分析/审稿
→ 生成 @ 引用建议
→ AISuggestionType = "mention_suggestion"（P1 已预留 citation_placeholder）
→ AI Suggestion Store（status=pending）
→ 用户查看、采纳或拒绝
→ 采纳后自动建立 chapter_mentions 记录
```

### 5.2 采纳后的行为

- 建立 `ChapterMention`（source=ai_suggestion）。
- **AI 建议采纳的 mention 建立规则（冻结）**：
  1. AI Suggestion 若包含有效正文位置（start_pos/end_pos/context_text），用户采纳时直接建立 ChapterMention（source=ai_suggestion，status=active）。
  2. AI Suggestion 若仅含实体引用而不含位置，采纳后 `AISuggestion.status=pending`——不建立 ChapterMention（AI 建议的 pending 状态由 AISuggestion 表管理，不写入 chapter_mentions）。用户需手动点击"插入到当前位置"或"关联选中文本"后才建立 ChapterMention（source=ai_suggestion，status=active）。
  3. AI 生成的 mention suggestion 本身不自动建立 ChapterMention——必须经过用户明确的"采纳"操作。

### 5.3 两种来源的渲染差异（关键）

`user_input` 和 `ai_suggestion` 两类 mention 在正文中的存在方式根本不同，MentionHighlight 必须区分处理：

| 维度 | source=user_input | source=ai_suggestion |
|------|-------------------|---------------------|
| **正文中的文本** | 包含 `@张三`（含 @ 符号） | 不包含 @，正文就是纯文本 `张三` |
| **start_pos 指向** | `@` 符号的位置 | 实体名称首字符（`张`）的位置 |
| **end_pos 指向** | `@张三` 之后（含 @） | 实体名称尾字符之后（不含 @） |
| **高亮覆盖范围** | `@张三` 整体 | `张三` 纯文本 |
| **视觉样式** | 蓝色实线背景 + 实线下划线 | 蓝色虚线下划线（无背景色），区分于用户手动 @ |
| **保存时重建** | 正则 `/@(\S+)/g` 扫描 | AI 建议的 mention **不会被保存时扫描重建**——它们由采纳流程写入，`start_pos`/`end_pos` 由 AI 分析时确定（基于采纳时的正文版本）。编辑后若位置失效，标记为 `broken`。 |

**为什么两类 mention 的 start_pos 语义不同：**
- `user_input`：正文里有显式的 `@` 触发符，mention 区间覆盖 `@` + 实体名，这是用户可见的完整标记。
- `ai_suggestion`：正文是纯文本，没有 `@`。AI 分析时识别"第 42 个字符处的 `张三` 是一个人物引用"，start_pos=42 指向 `张` 而非 `@`。采纳后高亮直接渲染在实体名原文上。

**保存时的行为差异：**
- `user_input` 的 mentions 在每次保存时被全量重建（见第七章位置同步策略），因为正文中的 `@` 是权威来源。
- `ai_suggestion` 的 mentions **不参与保存时重建**——它们由 AI 建议采纳流程单独管理。若用户编辑了 AI 建议 mention 所在的文本区域，该 mention 标记为 `broken`，前端仍保留记录但不渲染高亮。用户可手动删除或重新关联。

**⚠️ 关键约束：所有样式差异均为渲染层表现**
- `mention--user` 的蓝色实线背景、`mention--ai` 的紫色虚线下划线均为前端 CSS 渲染效果。
- **不写入正文 content 字段**——正文始终保持纯文本。
- **不影响导出**——TXT/Markdown 导出时不带任何 mention 标记，仅输出纯文本。
- 前端不得将 `<span class="mention">` 等 HTML 写回正文存储。

### 5.4 MentionHighlight 渲染逻辑

```typescript
// MentionHighlight 组件渲染伪代码
function renderMention(mention: ChapterMention, bodyText: string) {
  const text = bodyText.slice(mention.start_pos, mention.end_pos)

  if (mention.source === 'user_input') {
    // 正文包含 @ 符号，高亮 @实体名 整体
    return `<span class="mention mention--user" data-mention-id="${mention.mention_id}">${text}</span>`
    // CSS: .mention--user { background: rgba(59,130,246,0.15); border-bottom: 1px solid #3b82f6; }
  }

  if (mention.source === 'ai_suggestion') {
    // 正文无 @，高亮实体名原文
    return `<span class="mention mention--ai" data-mention-id="${mention.mention_id}">${text}</span>`
    // CSS: .mention--ai { border-bottom: 1px dashed #8b5cf6; }  无背景色，虚线区分
  }
}
```

---

## 六、Repository 接口与持久化

### 6.1 ChapterMentionRepository

```python
class ChapterMentionRepository(ABC):
    @abstractmethod
    async def replace_by_chapter(
        self, chapter_id: str, mentions: list[ChapterMention]
    ) -> list[ChapterMention]: ...
    # 全量提交 + 后端 diff/upsert（非物理 DELETE + INSERT）：
    #   1. 已存在 mention_id 的记录 → UPDATE（start_pos, end_pos, status, updated_at）
    #   2. 新增 mention（无对应 mention_id）→ INSERT
    #   3. 本次未提交的旧 mention → 标记 status=broken（不物理删除，保留历史引用）
    # 动机：保证 mention_id 跨保存稳定，避免 Tooltip、AI Suggestion 关联、引用统计断裂。

    @abstractmethod
    async def get_by_chapter(
        self, chapter_id: str
    ) -> list[ChapterMention]: ...

    @abstractmethod
    async def mark_entity_deleted(
        self, entity_type: str, entity_id: str
    ) -> None: ...
    # 批量标记 is_active=false

    @abstractmethod
    async def get_by_entity(
        self, entity_type: str, entity_id: str
    ) -> list[ChapterMention]: ...
    # 反向查询：哪些章节引用了此实体
```

### 6.2 持久化表

```sql
CREATE TABLE IF NOT EXISTS chapter_mentions (
    mention_id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    work_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL DEFAULT '',
    entity_name_snapshot TEXT NOT NULL DEFAULT '',
    start_pos INTEGER NOT NULL DEFAULT 0,
    end_pos INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'user_input',
    ai_suggestion_id TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    is_active INTEGER NOT NULL DEFAULT 1,
    validation_detail TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mentions_chapter ON chapter_mentions(chapter_id);
CREATE INDEX IF NOT EXISTS idx_mentions_entity ON chapter_mentions(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_work ON chapter_mentions(work_id);
```

---

## 七、位置同步策略

### 7.1 核心问题

正文保持纯文本，mentions 独立存储 `start_pos` / `end_pos`。用户每次编辑正文（插入、删除、粘贴）都会导致字符位置偏移，如果不做同步，已存储的 mentions 位置会指向错误的文字。

这不是边缘情况——这是每次编辑都会发生的正常行为。

### 7.2 策略选择：方案 A1（保存时全量重建）

选择 **方案 A1**：保持位置存储，但保存时重新计算全量 mentions 位置。

**放弃方案 A2（锚点文本匹配）**：存储 `anchor_text`（如 `@张三`）而非绝对位置，渲染时动态搜索。缺点：同一章节多次出现同一实体时，无法区分哪个 mention 对应哪个出现位置，消歧复杂度高。

### 7.3 编辑时实时维护（前端编辑器）

前端编辑器在用户编辑过程中实时维护内存中的 mentions 位置映射，保证编辑体验流畅（高亮不跳变）：

1. **插入文本**：插入位置 < `mention.start_pos` → `mention.start_pos`/`end_pos` 同步右移（偏移量 = 插入长度）。插入位置在 mention 区间内 → mention 标记为 `dirty`（需重新确认该 mention 是否仍然有效）。
2. **删除文本**：删除区间完全在 mention 前方 → `mention.start_pos`/`end_pos` 左移。删除区间完全覆盖 mention → 删除该 mention。删除区间部分覆盖 mention → mention 标记为 `broken`。
3. **粘贴文本**：等同于先插入（粘贴内容）再处理。粘贴区间后的所有 mentions 位置同步右移。

### 7.4 保存时全量重建（关键）

**核心原则：「重建完整 mentions 列表」= 重建位置列表和提交 payload；不是丢弃已有 entity_id 后按名称重新匹配。entity_id 以已确认的 mention 为权威来源。**

**前端在每次 Local-First 保存事件中，必须执行以下流程：**

```
用户触发保存（Ctrl+S / 自动保存定时器）
  │
  ├─ 1. 保存正文到后端（V1.1 现有保存链路，不变）
  │
  └─ 2. 正文保存成功后，重建 mentions：
        │
        ├─ 2a. 提取当前 mention store 中所有已有 mention，
        │      根据正文 diff / 区间文本校验，更新其 start_pos/end_pos
        │      （实体名在区间内仍存在 → 更新位置；不存在 → 标记 broken）
        │
        ├─ 2b. 重新扫描当前正文全文，识别所有 @实体名 出现位置
        │      正则：/@(\S+?)(?=\s|$|[，。！？；：、""''）\)】\-—])/g
        │
        ├─ 2c. 匹配已有 mention 与扫描结果：
        │      - 文本区间匹配到的 @实体名 → 复用已有 entity_id（保留同名消歧结果）
        │      - 扫描到新 @实体名（无对应已有 mention）→ 调用 suggest API 解析 entity_name → entity_id
        │        （对同名实体，suggest 返回多项，前端弹出消歧选择）
        │
        ├─ 2d. 构建完整 mentions 列表（已有 mention 保留原 entity_id + mention_id）
        │
        └─ 2e. PUT /api/v2/chapters/{chapter_id}/mentions
               全量提交，后端 diff/upsert
```

**关键约束：**
- **已有 mention 的 entity_id 不可变**：即使正文扫描到同名文本，必须保留原 entity_id，除非用户在前端主动重新选择目标实体。
- 步骤 2 不依赖上次保存的 mentions 位置——完全从当前正文重新扫描 + 已有 mention 的 entity_id 锚定。
- 步骤 2 与步骤 1 的 `chapter_revision` 保持一致，防止基于旧版本正文重建 mentions 导致冲突。
- 若步骤 2 的 PUT 失败（如 409 冲突），前端本地缓存 mentions 列表，下次保存时重试。
- P2-05 初期不修改 V1.1 正文保存链路——mentions 通过独立 API 单独保存。
- **同名实体消歧结果受保护**：用户之前选择了「张三（人物·主角）」（entity_id=c_01）而非「张三（人物·配角）」（entity_id=c_15），保存重建时必须保留 c_01，不能因重新扫描而回退到模糊匹配。

### 7.5 后端校验

保存 mentions 时后端执行以下校验，任一项失败返回 400：

| 校验项 | 规则 | 错误码 |
|--------|------|--------|
| 位置范围 | `start_pos >= 0`, `end_pos > start_pos`, `end_pos <= len(chapter.content)` | `invalid_mention_range` |
| 区间不重叠 | 同一 `chapter_id` 下 mention 区间不得交叉重叠（见下方冻结规则） | `overlap_mentions` |
| 文本匹配 | mention 区间文本应包含 `@entity_name` 或 `entity_name` | `text_mismatch` |
| 实体有效 | `entity_id` 必须存在且 `entity_type` 匹配 | `invalid_entity` |
| 重复禁止 | 同一 `chapter_id` 下，不允许 `(start_pos, end_pos, entity_id)` 三元组完全相同的重复 mention | `duplicate_mention` |

**区间唯一性冻结规则（同一 `chapter_id` 下）：**

1. **禁止完全重复**：不允许两条 mention 的 `(start_pos, end_pos, entity_id)` 完全相同。
2. **禁止交叉重叠**：设有 mention A `[a_start, a_end)` 和 mention B `[b_start, b_end)`，不允许 `a_start < b_start < a_end < b_end` 或 `b_start < a_start < b_end < a_end`。
3. **允许相邻**：`a_end == b_start`（A 紧邻 B 之前）合法。
4. **不支持嵌套 mention**：不允许 `a_start < b_start < b_end <= a_end`（大区间包小区间）。@ 标签引用不支持嵌套语义。

上述规则全部在前端提交时由后端校验，校验失败返回 400 及具体错误码。前端也应在本地做预校验以减少无效请求。

### 7.6 位置失效的降级展示

| 状态 | 含义 | 前端渲染 |
|------|------|----------|
| `active` | 位置有效，实体有效 | 正常蓝色高亮 |
| `broken` | 编辑导致位置失效（区间文本不再匹配） | 不高亮，tooltip 显示"mention 已失效" |
| `stale` | 实体名称已变更 | 仍高亮，tooltip 显示"实体已更名：原名 → 新名" |
| `inactive_entity` | 实体已删除/归档 | 灰色高亮，tooltip 显示"实体已删除" |

---

## 八、API 设计

### 8.1 端点

```
GET    /api/v2/mentions/suggest?work_id=&q=&types=&limit=10
  Response: { suggestions: [{ entity_type, entity_id, entity_name,
              match_type, last_used_at, summary_preview }] }

GET    /api/v2/chapters/{chapter_id}/mentions
  Response: { mentions: [...] }

PUT    /api/v2/chapters/{chapter_id}/mentions
  Request:  {
              chapter_revision: int,
              mentions: [{
                mention_id: str | null,       # 有值→update；null/空→insert
                entity_type: str,
                entity_id: str,
                entity_name_snapshot: str,    # 实体当前名称快照
                start_pos: int,
                end_pos: int,
                source: str,                  # "user_input" | "ai_suggestion"
                ai_suggestion_id: str | null,
                status: str | null            # 通常省略，由后端根据校验结果设置
              }]
            }
  Response: { mentions: [...] } 或 409 mention_conflict
  Note:     全量提交（replace_mentions），后端执行 diff/upsert（非物理 DELETE + INSERT）：
               mention_id 有值 → UPDATE；mention_id 为空 → INSERT；
               本次未提交的旧 mention → 标记 broken。
            【冻结保存模式】采用独立保存：正文走 V1.1 Local-First，mentions 通过此 API 单独保存。
            前端在正文保存成功后立即调用此 API。若 mentions 保存失败，前端本地缓存重试。
            必须带 chapter_revision 校验防止并发冲突。
            P2-05 初期不修改 V1.1 保存链路——不将 mentions 嵌入章节正文保存流程。
            chapter_revision 必须等于当前章节 revision，不一致返回 409（与 V1.1 乐观锁一致）。
            后端校验规则：
            1. start_pos >= 0, end_pos > start_pos, end_pos <= len(chapter.content)
            2. mention 区间必须满足 §7.5 区间唯一性冻结规则（禁止重复、禁止交叉、允许相邻、不支持嵌套）
            3. mention 区间文本应包含 @entity_name 或 entity_name
            4. entity_id 必须存在且 entity_type 匹配
            校验失败返回 400 invalid_mention_range / invalid_entity / overlap_mentions / duplicate_mention

GET    /api/v2/mentions/{mention_id}/summary
  Response: { entity_type, entity_id,
              entity_name_snapshot,    # mention 创建时的实体名称快照
              entity_current_name,     # 实体当前名称（动态解析），若不同于 snapshot → status=stale
              summary_text,
              status,                  # active / broken / stale / inactive_entity
              is_active,
              last_updated }
  Note:     entity_name_snapshot 与 entity_current_name 不一致时，前端 tooltip 展示
            "张三（已更名：原名 → 新名）"，帮助用户识别 stale 状态的 mention。
```

---

## 九、测试策略

| # | 用例 | 验证点 |
|---|---|---|
| T1 | @ 前缀匹配 | 输入"张"→返回以"张"开头的实体 |
| T2 | 模糊匹配补足 | 前缀匹配不足 10 条→模糊匹配补齐 |
| T3 | 选择 mention 后保存 | mentions 持久化到 chapter_mentions |
| T4 | 悬停摘要查询 | GET /summary 返回正确摘要 |
| T5 | 同名实体消歧 | 同名实体全部展示，用户选择后 entity_id 确定 |
| T6 | 实体删除后 mention 降级 | is_active=false，悬停提示"已删除" |
| T7a | AI suggestion 生成不自动建立 mention | AI 生成的 mention suggestion 不建立 ChapterMention 记录 |
| T7b | 采纳含位置的 AI 建议 | AI Suggestion 包含有效 start_pos/end_pos → 用户采纳 → 建立 ChapterMention |
| T7c | 采纳不含位置的 AI 建议 | AI Suggestion 仅含实体引用不含位置 → 采纳后 AISuggestion.status=pending，不建立 ChapterMention；用户选择位置后才建立 ChapterMention |
| T8 | 正文保持纯文本 | 保存后章节 content 字段不含特殊标记 |
| T9 | 保存时全量重建 mentions | 正文编辑后保存 → 前端重新扫描正文 @ 出现位置 → PUT 全量提交 → 后端 diff/upsert 更新位置，已有 mention_id 保留 |
| T10 | 保存后位置偏移被修正 | 在第 10 字符处插入文字 → 原第 42 字符处的 @张三 移到第 44 字符处 → 保存后 mention.start_pos=44 |
| T11 | user_input mention 渲染 | 正文含 @张三 → 高亮覆盖 @张三 整体 → 蓝色实线样式 |
| T12 | ai_suggestion mention 渲染 | 正文纯文本"张三"无 @ → 高亮仅覆盖"张三" → 紫色虚线样式 |
| T13 | ai_suggestion mention 编辑后 broken | 用户编辑了 AI 建议 mention 所在文本 → mention 标记 broken → 不渲染高亮 |
| T14 | 保存时 user_input 重建不覆盖 ai_suggestion | 保存重建只扫描 @ 触发符 → ai_suggestion 的 mentions 不受影响 |

---

## 十、代码改动面

```
新增：
  application/services/ai/mention_service.py
  domain/repositories/ai/chapter_mention_repository.py
  infrastructure/persistence/sqlite_chapter_mention_repo.py
  presentation/api/routers/v2/ai/mentions.py
  frontend/src/components/workspace/AtMentionPopup.vue
  frontend/src/components/workspace/AtMentionHighlight.vue
  frontend/src/stores/mention.ts               # Pinia store（状态管理 + API 调用）

修改：
  frontend/src/components/workspace/PureTextEditor.vue  # hook MentionDetector
  domain/entities/ai/models.py  # 追加 ChapterMention, MentionSource 等
  presentation/api/app.py       # 注册 mentions 路由

不改：
  application/services/v1/chapter_service.py  # 编辑保存链路不动
  application/services/ai/tool_facade.py
```
