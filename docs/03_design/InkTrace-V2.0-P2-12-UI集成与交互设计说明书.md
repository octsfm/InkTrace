# InkTrace V2.0-P2-12 UI 集成与交互设计说明书

版本：v1.1 / P2 模块级详细设计候选冻结版
状态：候选冻结
所属阶段：InkTrace V2.0 P2 集成
设计范围：P2 全部前端入口、组件布局、交互状态、用户确认规范、Feature Flag 显示规则

依据文档：

- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`
- `docs/03_design/InkTrace-V2.0-P2-01~11-*.md`
- 现有 V1.1 Workbench / WritingStudio / RightWorkspacePanel / PureTextEditor 实现

说明：本文档是 P2 UI/UE 集成的收口文档。不替代各模块详细设计中的前端章节，不写代码实现，不新增 P2-01~P2-11 之外的功能。所有设计基于现有 V1.1 Workbench 界面风格做增量扩展。

---

## 一、文档定位与设计目标

### 1.1 本文档管什么

| 覆盖 | 不覆盖 |
|---|---|
| UI 入口位置（按钮、Tab、路由） | 后端领域模型 |
| 组件容器类型（Panel / Drawer / Modal / Popover / Toolbar） | API 请求/响应结构细节 |
| 交互状态（loading / empty / failed / stale / warning 等） | 数据库表结构 |
| 用户确认规范（哪些需确认、哪些不需要） | Store 内部实现 |
| Feature Flag 显示规则 | Service 层逻辑 |
| 用户可见中文文案 | — |

### 1.2 设计原则

1. **增量不推翻**：基于现有 V1.1 Workbench / WritingStudio / RightWorkspacePanel / PureTextEditor 继续设计，不重做。
2. **优先复用**：优先使用现有组件、布局、颜色、按钮样式、提示样式。
3. **操作短路径**：常用功能 1~2 步完成，危险操作才需二次确认。
4. **中文优先**：用户可见文案尽量使用中文白话，不夹杂英文（代码名、接口名、状态枚举除外）。
5. **写作优先**：AI 功能是"写作助手"，不是"后台管理系统"。界面应是明亮、简洁的写作工具风格。
6. **确认不滥**：常用动作不过度确认；危险动作才弹二次确认。
7. **AI 不自动写正文**：所有 AI 产出必须经用户确认后才进入正式数据或编辑器草稿。

### 1.3 核心约束

- 不破坏 PureTextEditor 核心编辑能力。
- 不破坏 V1.1 Local-First 草稿保存链路。
- CandidateDraft、AISuggestion、SelectionRewrite、OutlineAssist、Opening 等都必须经过用户确认。
- 成本看板、分析看板不触发 LLM 调用。
- P2 UI 通过 Feature Flag 分期启用。
- P1 组件优先通过 props / slots / composable / Store 扩展。

---

## 二、总体布局设计

### 2.1 WritingStudio P2 扩展布局

```
┌──────────────────────────────────────────────────────────────────┐
│  顶部工具栏                                                        │
│  [作品名] [大纲] [人物] [时间线] [伏笔] ... | [多章续写] [开篇助手] │
├────────────────┬─────────────────────────────────┬───────────────┤
│                │                                 │ 右侧面板       │
│  左侧章节列表   │      PureTextEditor             │ ┌───────────┐ │
│  (Chapter      │      (编辑区)                    │ │ 候选稿     │ │
│   Sidebar)     │                                  │ │ (V1.1已有)│ │
│                │  ┌─ MentionPopup（@ 触发时浮动）─┐ │ ├───────────┤ │
│                │  └──────────────────────────────┘ │ │ AI助手     │ │
│                │  ┌─ SelectionToolbar ────────────┐ │ │ (P2 新增) │ │
│                │  │ （选中文本时浮动）              │ │ │自动续写   │ │
│                │  └──────────────────────────────┘ │ │ │大纲辅助   │ │
│                │                                  │ │ │开篇助手   │ │
│                │                                  │ │ ├───────────┤ │
│                │                                  │ │ 更多…     │ │
│                │                                  │ │ └───────────┘ │
├────────────────┴─────────────────────────────────┴───────────────┤
│  状态栏                                                           │
│  字数: 3,200 | 章节: 3/12 | 自动续写: 等待确认 | 上次保存: 1分钟前 │
└──────────────────────────────────────────────────────────────────┘

独立页面（非 WritingStudio 内嵌）：
  /works/:workId/cost          → CostDashboard.vue
  /works/:workId/analysis      → AnalysisDashboard.vue
  StyleDNA 配置入口             → 设置页中的"风格画像"入口，具体路由以现有设置路由体系为准
                                  （建议 /works/:workId/style 或 /settings/ai/style-dna，
                                   以 P2-11 路由注册确认为准）
```

### 2.2 右侧面板 Tab 控制策略（冻结）

#### 核心规则

1. **P2 不改变 V1.1 既有 Tab 的优先级和位置**。V1.1 已有的人物、设定、时间线、伏笔等 Tab 保持不变。
2. P2 新增的 AI 功能入口**统一收敛到"AI 助手"聚合 Tab**，不分散插入主 Tab 列表。
3. 若 V1.1 已有 Tab 数量达到上限，P2 功能默认进入"AI 助手"内部子视图或"更多"菜单，**不强行挤占主 Tab 位**。

#### 推荐布局

| Tab 类型 | 内容 | 说明 |
|---|---|---|
| **V1.1 固定 Tab** | 候选稿、人物、设定、时间线、伏笔等 | 不受 P2 影响，保持原有位置 |
| **AI 助手（P2 新增聚合 Tab）** | 自动续写、大纲辅助、开篇助手 | 内部子 Tab 或下拉切换。Feature Flag 控制整个聚合 Tab 的可见性 |
| **"更多"菜单** | 低频或溢出功能 | 若"AI 助手"中所有子功能对应的 Feature Flag 均为 false，则"AI 助手"Tab 本身也隐藏 |
| **独立页面** | 成本看板、分析看板 | 不在右侧面板中 |

#### 显示条件

- Feature Flag=false 的功能在 AI 助手内部不可见。
- 若 AI 助手内部所有子功能的 Flag 均为 false，整个"AI 助手"Tab 隐藏。
- 小屏幕下（宽度 < 1200px），AI 助手退化为工具栏下拉菜单入口。

---

## 三、P2-S1 UI 集成

### 3.1 多章续写（MultiChapter）

**入口**：顶部工具栏"多章续写"按钮（图标 + 文字，Feature Flag 控制）。

**容器**：`MultiChapterPanel` — 从右侧滑入的 Drawer（宽 420px），不遮挡编辑区主体。

**布局**（运行中）：
```
┌─ 多章续写 ───────────────────────── [✕] ─┐
│                                            │
│  进度：■■■■■□□□□□  5 / 10 章             │
│  字数：25,000 / 50,000                      │
│                                            │
│  ┌ 章节状态 ──────────────────────────┐   │
│  │ ✅ 第1章  3,200字  已生成           │   │
│  │ ✅ 第2章  2,800字  已生成           │   │
│  │ 🔄 第3章  生成中…                  │   │
│  │ ⏳ 第4章  等待中                   │   │
│  └────────────────────────────────────┘   │
│                                            │
│  当前章节需要你确认：                        │
│  [查看候选稿]  [确认并继续]  [停止续写]      │
└────────────────────────────────────────────┘
```

**状态与文案**：

| 内部状态 | 用户看到 | 可用操作 |
|---|---|---|
| `generating` | "正在生成第 N 章" | 停止 |
| `waiting_review` | "第 N 章已生成，需要你确认" | 查看候选稿、确认并继续 |
| `blocked` | "当前结果需要你处理" | 查看详情、跳过、停止 |
| `completed` | "全部章节已生成" | 查看所有候选稿 |
| `failed` | "第 N 章生成失败" | 重试、跳过、停止 |

**约束**：
- 不自动应用候选稿到正文。用户必须手动进入候选稿区 apply。
- 停止后已生成的候选稿全部保留。
- "[查看候选稿]"点击后：切换到右侧面板"候选稿"Tab，自动滚动到当前章节对应的候选稿。不弹出新窗口。

---

### 3.2 CitationLink（引用校验）

**入口**：候选稿正文中带下划线的引用标记。无独立入口按钮。

**容器**：`CitationPopover` — 点击引用标记时弹出小气泡（宽 320px）。

**状态与文案**：

| 内部状态 | 用户看到 | 视觉效果 |
|---|---|---|
| `verified` | "已找到来源" | 绿色小勾 + 灰色下划线 |
| `low_confidence` | "可信度较低，请简单看一下" | 黄色小感叹号 + 虚线下划线 |
| `source_missing` | "暂时找不到来源" | 灰色小问号 + 虚线下划线 |
| `unverified` | "尚未检查" | 无特殊标记 |

**约束**：
- 低置信**不阻断**候选稿展示，仅做温和提示。
- 不弹出 Modal 打断阅读。

---

### 3.3 StyleDNA（风格画像）

**入口**：设置页中的"风格画像"入口，具体路由以现有设置路由体系为准（建议 `/works/:workId/style` 或 `/settings/ai/style-dna`，以 P2-11 路由注册确认为准）。非 WritingStudio 内嵌面板。

**容器**：`StyleDNAConfigPanel` — 独立页面内的卡片式布局。

**流程**：导入样本 → 分析中 → 查看结果 → 确认启用（3 步）。

**状态与文案**：

| 内部状态 | 用户看到 | 可用操作 |
|---|---|---|
| `none` | "尚未配置风格画像" | 导入样本 |
| `extracting` | "正在分析你的风格样本…" | 取消 |
| `pending_confirm` | "分析完成，请确认是否启用" | 确认启用、放弃 |
| `active` | "已启用为当前作品风格参考" | 禁用、重新提取 |
| `disabled` | "已停用，不再参与生成" | 重新启用 |

**约束**：
- 未确认的风格画像**不能**注入 ContextPack。
- 低置信度（<500 字）时展示明确提示，但不阻止用户确认启用。
- 同一作品同时只有一个 ACTIVE 风格画像。

---

### 3.4 自动续写队列（AutoQueue）

**入口**：右侧面板"AI 助手"聚合 Tab → "自动续写"子视图（Feature Flag 控制）。

**容器**：`AutoQueuePanel` — 右侧面板内的卡片式布局。

**布局**（未启动时）：
```
┌─ 自动续写 ───────────────────────────────┐
│                                           │
│  模式：[安全模式 ▾]                        │
│  安全模式：每章完成后暂停，等你确认后继续     │
│  连续模式：审稿通过后自动继续，无需每章确认   │
│                                           │
│  目标章节数：[___10___]                    │
│                                           │
│  [开始自动续写]                             │
└──────────────────────────────────────────┘
```

**停止通知示例**：
```
预算已超出：🛑 预算已超出 · 已使用 520K / 预算 500K token
          已生成 4 章候选稿，自动续写已暂停。
          [提高预算]  [关闭预算检查]

连续 blocking：🛑 队列已停止 · 连续 2 章审稿发现严重冲突
              已生成 5 章候选稿，保留在候选稿区。
              [查看冲突详情]  [继续队列]  [放弃队列]

手动停止：🛑 你已手动停止队列 · 已生成 3 章候选稿
          [继续队列]  [放弃队列]
```

**约束**：
- 安全模式必须等用户确认后才能继续。
- 停止后不删除已生成的候选稿。
- 连续候选模式也必须在 blocking 时暂停。

---

## 四、P2-S2 UI 集成

### 4.1 @Mention（实体引用）

**入口**：编辑器内输入 `@` 触发。无独立 UI 入口。

**容器**：
- `MentionPopup` — 输入 `@` 后在光标附近弹出建议列表（宽 280px）。
- `MentionHighlight` — 已插入的 Mention 在正文中以浅蓝底色 + 虚线下划线高亮。
- `MentionTooltip` — Hover 已插入 Mention 时弹出信息浮层。

**空状态**：
```
┌─ 没有找到相关角色或设定 ──────────────────┐
│  试试其他关键词，或 [新建角色]               │
└──────────────────────────────────────────┘
```

**约束**：
- 不直接触发 LLM 调用。
- "[新建角色]"点击后：若 V1.1 已有角色创建入口（如右侧人物面板的"添加角色"），则跳转到该入口（不重复造轮子）；若不存在，弹出轻量侧边小表单（非 MentionPopup 内嵌），创建完成后自动回到编辑器，新建角色出现在下次 @ 建议列表中。不在 MentionPopup 内承载复杂表单。
- 弹窗按 Esc 可关闭，不打断用户正常输入。

---

### 4.2 开篇助手（Opening Agent）

**入口**：顶部工具栏"开篇助手"按钮，或右侧面板"AI 助手"→"开篇助手"。

**容器**：`OpeningAgentWizard` — 全屏 Modal（宽 720px），分步骤展示。

**流程**：导入参考 → 分析开篇特点 → 选择策略 → 风险确认 → 生成候选稿。

**约束**：
- 版权确认 checkbox 在步骤 1 和步骤 4 各出现一次，两处逻辑一致：**未勾选时"下一步"（步骤 1）和"生成候选稿"（步骤 4）按钮均 disabled**。
- 策略未确认**不能**生成正式候选。
- 模仿风险分级处理：
  - **warning 级**（低/中风险）：允许用户确认后继续，按钮显示"了解风险，继续生成"。
  - **high/blocking 级**（`P2_IMITATION_RISK_HIGH`）：**不允许**生成，提示"存在较高的模仿风险，建议返回修改策略后再生成"。显示"返回修改"按钮。
- Opening 生成的候选稿走 CandidateDraft + HumanReviewGate 标准链路，不直接写入正式正文。

---

### 4.3 大纲辅助（Outline Assist）

**入口**：右侧面板"AI 助手"聚合 Tab → "大纲辅助"子视图（Feature Flag 控制）。

**容器**：`OutlineAssistPanel` + 内嵌 `SuggestionCard` 列表。

**模式切换**：[润色] [扩写] [章节细纲] [写作建议]

**accept ≠ apply 区分**：
- "采纳" = 将建议标记为"已采纳"（暂存），不写正式大纲。
- "应用" = 将已采纳的建议写入正式大纲 → 弹出轻量 **Popconfirm** 确认："确定要将 N 条建议应用到大纲吗？这将会修改正式大纲内容。" → 确认后写入 → toast："已应用 N 条建议"。

**约束**：
- `accept` 是轻量操作，不二次确认。
- `apply` 会修改正式大纲，必须弹 Popconfirm 确认（不是 toast）。
- 成功应用后 toast（2 秒自动消失）。
- 大纲被外部修改后提示"大纲已被修改，建议可能已不适用"。

---

### 4.4 选区改写（Selection Rewrite）

**入口**：用户在编辑器中选中文本后，浮动工具栏自动出现。

**容器**：
- `SelectionRewriteToolbar` — 选中文末浮动（宽 320px）：[扩写] [重写] [缩写] [润色] [对白优化] [降低 AI 味]
- `SelectionRewriteDiffModal` — 查看 Diff 结果的全屏 Modal（宽 800px）。

**约束**：
- 应用只写入 Workbench Store（编辑器草稿），不直接写后端正式正文。
- 后续保存走 V1.1 Local-First 链路。
- 原文被修改后必须检测冲突（`source_hash` 不匹配 → `conflicted`）。
- 冲突时**不替换**草稿，显示"原文已变化，请重新选择"。
- 撤销在 **Store 层做内存回滚**（恢复应用前的草稿快照），不调用后端 API。5 秒内若触发 V1.1 自动保存，自动保存的是改写后草稿；撤销回滚到应用前快照，与 V1.1 已有 undo 逻辑一致。

---

## 五、P2-S3 独立看板页面

### 5.1 成本看板（CostDashboard）

**路由**：`/works/:workId/cost`。不要求 Provider 可用（纯只读聚合）。

**布局**：总 Token / 总成本 / 调用次数 三卡片 → 月度切换 → 按角色/模型/服务商分布 → Token 趋势图 → 预算配置（进度条 + 编辑）+ 调用明细分页表。

**预算状态展示**：

| 用量区间 | 进度条颜色 | 提示文案 |
|---|---|---|
| 0% ~ 80% | 🟢 绿色 | 无额外提示 |
| 80% ~ 100% | 🟡 黄色 | "接近预算上限" |
| > 100% | 🔴 红色 | "预算已超出，新 AI 任务已暂停" + [提高预算] [关闭预算检查] |

---

### 5.2 分析看板（AnalysisDashboard）

**路由**：`/works/:workId/analysis`。不要求 Provider 可用（纯本地统计分析）。

**布局**：6 个 Tab（写作统计 / 节奏分析 / 对白分析 / 高频词 / 风格一致性 / AI 使用分析）。

**AI 使用分析 Tab 免责声明**（必须展示）：
```
┌─ AI 使用分析 ───────────────────────────────┐
│  ⓘ AI 常见词汇仅统计出现频率，不代表文本      │
│    一定由 AI 生成。数据仅供参考。              │
│  ─────────────────────────────────────────  │
│  候选稿采纳率：68%                           │
│  ...                                        │
└─────────────────────────────────────────────┘
```

**风格一致性 — 无 StyleProfile 时**：展示降级版统计一致性，提示"尚未配置风格画像，当前结果基于全书文本统计，仅供参考。[前往配置]"

**约束**：
- 不触发 LLM 调用。
- 无 StyleProfile 时展示降级版，不显示"无法分析"。
- stale 时展示黄色提示条 + "点击重新统计"按钮。

---

## 六、统一交互状态规范

所有 P2 组件的交互状态使用统一的中文文案和 UI 表现：

| 内部状态 | 用户看到的中文 | UI 表现 | 可用按钮 | 允许重试 | 阻断流程 |
|---|---|---|---|---|---|
| `loading` | 正在加载… | 骨架屏 / 浅色 spinner | — | — | 否 |
| `polling` | 正在生成，请稍等 | 进度条 + 当前步骤文案 | 取消（如支持） | — | 否 |
| `empty` | 暂无数据 | 空状态插图 + 引导文案 | 引导操作按钮 | — | 否 |
| `failed` | 生成失败，可以重试 | 红色提示条 | 重试、取消 | ✅ 是 | 否 |
| `warning` | 提示信息 | 温和黄色提示条 | 查看详情、忽略 | — | 否 |
| `stale` | 数据可能已过期 | 黄色提示条 + 刷新按钮 | 刷新 | — | 否 |
| `conflicted` | 原文已变化，请重新选择 | 橙色提示条 | 重新选择、取消 | — | 是 |
| `feature_disabled` | 这个功能暂未开启 | 空状态页面 | 返回 | — | 是 |
| `budget_exceeded` | 预算已超出 | 红色提示条 + 用量详情 | 提高预算、关闭检查 | — | 是 |
| `low_confidence` | 结果可信度较低，请简单看一下 | 温和黄色标记 | 确认使用、放弃 | — | 否 |
| `waiting_user_action` | 等待你确认 | 蓝色提示条 + 高亮确认按钮 | 确认、拒绝、修改 | — | 是 |
| `applying` | 正在应用… | 按钮 loading 态 | — | — | 否 |
| `applied` | 已应用 | 绿色 toast（2s 自动消失） | 撤销（如支持） | — | 否 |
| `rejected` | 已拒绝 | 灰色 toast（2s 自动消失） | — | — | 否 |
| `disabled` | 已停用 | 灰色标签 | 重新启用 | — | 否 |

**通用规则**：
- `failed` 状态**必须**提供重试入口。
- `waiting_user_action` 状态**必须**高亮确认按钮。
- 轮询到终态（completed / failed / stopped / cancelled）后**停止轮询**。

---

## 七、用户确认与防误触规范

### 7.1 必须用户确认的动作

| 动作 | 确认级别 | 确认方式 | 说明 |
|---|---|---|---|
| apply candidate draft | 沿用 P1 既有流程 | P2 不新增确认。若 P0/P1 HumanReviewGate 已有确认，则沿用；若候选稿会覆盖已有正文，显示差异预览 | 不破坏已有链路 |
| apply outline suggestion | 轻量确认 | apply 时弹 Popconfirm："确定要将 N 条建议应用到大纲吗？" | accept 不确认，apply 需确认 |
| apply selection rewrite | 普通确认 | 点击即执行（用户已在 Diff 弹窗中看到变化） | — |
| confirm style profile | 普通确认 | 点击即执行（用户已查看分析结果） | — |
| confirm opening strategy | 普通确认 | 点击即执行 | — |
| auto queue confirm continue | 普通确认 | 点击即执行（安全模式核心操作） | 每章 1 次点击 |
| reject candidate / reject strategy | 普通确认 | 点击即执行 | 拒绝不危险 |
| **stop auto queue** | **二次确认** | 弹窗："确定要停止自动续写吗？已生成的候选稿会保留。" | 中断长任务 |
| **disable budget check** | **二次确认** | 弹窗："关闭预算检查后，AI 功能将不再受预算限制。确定要关闭吗？" | 可能产生费用 |

### 7.2 防误触规则

1. **loading 态禁用重复点击**：所有提交类按钮在 loading 状态时 `disabled + spinner`。
2. **二次确认弹窗**：标题清晰说明后果，取消按钮在左、确认按钮在右。
3. **toast 提示**：操作后反馈（绿色成功 / 红色失败），2 秒自动消失。**Toast 不做确认用**（确认必须用 Modal 或 Popconfirm）。
4. **撤销入口**：SelectionRewrite 应用后提供"撤销" toast 按钮（5 秒内可撤销）。撤销在 Store 层做内存回滚，不调用后端 API。5 秒内若触发自动保存，自动保存的是改写后草稿；撤销回滚到应用前快照，与 V1.1 已有 undo 逻辑一致。
5. **危险按钮**：停止队列、关闭预算、删除风格画像等不可逆操作用红色按钮。

---

## 八、Feature Flag 与入口控制

### 8.1 Flag 清单

| Flag | 阶段 | false 时行为 |
|---|---|---|
| `enable_multi_chapter` | P2-S1 | 隐藏顶部"多章续写"按钮 |
| `enable_citation_link` | P2-S1 | 候选稿正文中的引用标记不显示 |
| `enable_style_dna` | P2-S1 | 隐藏设置中"风格画像"入口 |
| `enable_auto_queue` | P2-S1 | 隐藏"AI 助手"中"自动续写"子视图 |
| `enable_mentions` | P2-S2 | 输入 @ 不触发建议弹窗 |
| `enable_opening_agent` | P2-S2 | 隐藏"开篇助手"入口 |
| `enable_outline_assist` | P2-S2 | 隐藏"AI 助手"中"大纲辅助"子视图 |
| `enable_selection_rewrite` | P2-S2 | 选中文本不出现浮动工具栏 |
| `enable_cost_dashboard` | P2-S3 | 隐藏成本看板路由入口 |
| `enable_analysis_dashboard` | P2-S3 | 隐藏分析看板路由入口 |

### 8.2 FeatureDisabled 页面

直接访问未启用功能的路由时显示：
```
┌─ 这个功能暂未开启 ─────────────────────────┐
│            🔒                               │
│    当前版本还不能使用这个功能。                │
│    你可以先使用其他写作功能。                  │
│            [返回写作]                         │
└────────────────────────────────────────────┘
```

### 8.3 后端返回 P2_FEATURE_DISABLED 时的前端处理

| 场景 | 前端行为 |
|---|---|
| 页面入口（路由访问） | 跳转 FeatureDisabled 页面 |
| 按钮操作（如点击"开始自动续写"） | 显示 toast："这个功能暂未开启" |
| API 调用（非用户直接触发） | 静默忽略，不弹错误提示 |
| 所有场景 | **不显示原始错误码** `P2_FEATURE_DISABLED`，统一用中文文案 |

---

## 九、组件与 Store 映射

| 模块 | 页面/组件 | Store | API 基础路径 | Feature Flag | 用户入口 |
|---|---|---|---|---|---|
| P2-01 MultiChapter | `MultiChapterPanel`（Drawer） | `useMultiChapterStore` | `/api/v2/ai/multi-chapter` | `enable_multi_chapter` | 顶部工具栏按钮 |
| P2-02 CitationLink | `CitationPopover`（气泡） | 复用 CandidateDraft Store | `/api/v2/ai/citations` | `enable_citation_link` | 候选稿正文引用标记 |
| P2-03 StyleDNA | `StyleDNAConfigPanel`（独立页） | `useStyleDNAStore` | `/api/v2/ai/style-dna` | `enable_style_dna` | 设置页入口 |
| P2-04 AutoQueue | `AutoQueuePanel`（右侧子视图） | `useAutoQueueStore` | `/api/v2/ai/auto-queues` | `enable_auto_queue` | AI 助手 → 自动续写 |
| P2-05 Mention | `MentionPopup` / `MentionHighlight` / `MentionTooltip` | `useMentionStore` | `/api/v2/mentions` | `enable_mentions` | 编辑器输入 @ |
| P2-06 Opening | `OpeningAgentWizard`（Modal） | `useOpeningStore` | `/api/v2/ai/opening` | `enable_opening_agent` | 工具栏按钮 / AI 助手 |
| P2-07 OutlineAssist | `OutlineAssistPanel`（右侧子视图） | `useOutlineAssistStore` | `/api/v2/ai/outline-assist` | `enable_outline_assist` | AI 助手 → 大纲辅助 |
| P2-08 SelectionRewrite | `SelectionRewriteToolbar` / `SelectionRewriteDiffModal` | `useSelectionRewriteStore` | `/api/v2/ai/selection-rewrite` | `enable_selection_rewrite` | 选中文本浮动工具栏 |
| P2-09 CostDashboard | `CostDashboard.vue`（独立页） | `useCostDashboardStore` + `useCostBudgetStore` | `/api/v2/ai/cost-dashboard` + `/api/v2/ai/cost-budget` | `enable_cost_dashboard` | 导航 / 设置入口 |
| P2-10 AnalysisDashboard | `AnalysisDashboard.vue`（独立页） | `useAnalysisDashboardStore` | `/api/v2/ai/analysis-dashboard` | `enable_analysis_dashboard` | 导航 / 设置入口 |

---

## 十、与 V1.1 Local-First 的兼容边界

### 10.1 数据写入路径

```
用户操作 → UI 组件 → Store → API（user_action）→ Service → Database
                                    ↑
                       所有正式写入必经 Presentation API
                                    ↑
                   caller_type = user_action 校验
```

### 10.2 各模块接入规则

| 模块 | 写入路径 | 兼容说明 |
|---|---|---|
| SelectionRewrite | Workbench Store（编辑器草稿）→ Local-First 保存 | 只改草稿，不改正式正文 |
| CandidateDraft apply | HumanReviewGate → V1.1 保存链路 | 走标准路径 |
| OutlineAssist apply | Outline Service → WritingAssetService | 通过 V1.1 大纲保存链路 |
| Opening apply | CandidateDraft + HumanReviewGate | 走标准候选稿链路 |
| StyleDNA | 独立表（`style_profiles`） | 不接触正文 |
| CostDashboard | 只读 `llm_call_logs` | 不写任何数据 |
| AnalysisDashboard | 只读 chapters + `analysis_metrics` 缓存 | 缓存写入不接触正文 |

### 10.3 不破坏的 V1.1 行为

- 离开保护（未保存提示）。
- 脏状态标记。
- 自动保存。
- 版本冲突弹窗（VersionConflictModal）。
- Workbench Store 是编辑器草稿状态的唯一入口。

---

## 十一、最简操作路径

| 功能 | 步骤数 | 路径 |
|---|---|---|
| 选区改写 | 4 步 | 选中文本 → 点模式按钮 → 查看 Diff → 应用 |
| 大纲辅助 | 4 步 | 选大纲节点 → 点模式 → 采纳建议 → 应用 |
| 自动续写 | 3+N 步 | 设章节数 → 开始 → 逐章确认 |
| 多章续写 | 3 步 | 点按钮 → 设参数 → 启动 |
| Opening Agent | 3 步 | 导入参考 → 选策略 → 生成候选稿 |
| StyleDNA | 3 步 | 导入样本 → 查看结果 → 启用 |
| 成本看板 | 2 步 | 打开页面 → 查看用量 |
| 分析看板 | 2 步 | 打开页面 → 查看统计 |
| @Mention | 2 步 | 输入 @ → 选实体 |

---

## 十二、验收标准

| # | 验收项 | 验证方式 |
|---|---|---|
| 1 | Feature Flag=false 时，所有对应入口隐藏 | 手动切换 flag |
| 2 | 直接访问未启用功能路由时显示"这个功能暂未开启" | 手动测试 |
| 3 | Provider 未配置时仍可打开成本看板 | 手动测试 |
| 4 | Provider 未配置时仍可打开分析看板 | 手动测试 |
| 5 | 发起 AI 调用类功能时检查 Provider 可用性，不可用时提示"请先配置 AI 模型" | 手动测试 |
| 6 | SelectionRewrite 原文变化后显示"原文已变化，请重新选择"，不替换草稿 | 自动化测试 |
| 7 | SelectionRewrite 应用后走 V1.1 Local-First 保存 | 手动测试 |
| 8 | OutlineAssist accept 不自动写入大纲 | 手动测试 |
| 9 | OutlineAssist apply 时弹 Popconfirm 确认，确认后写入正式大纲 | 自动化测试 |
| 10 | AutoQueue 安全模式下每章暂停在"等待你确认"，不自动继续 | 自动化测试 |
| 11 | AutoQueue 预算超限后显示"预算已超出" + 操作按钮 | 自动化测试 |
| 12 | CitationLink 低置信度不阻断候选稿展示 | 手动测试 |
| 13 | StyleDNA 未确认时不注入 ContextPack | 自动化测试 |
| 14 | Opening Agent 版权未确认时"下一步"和"生成候选稿"按钮均 disabled | 手动测试 |
| 15 | AnalysisDashboard stale 时显示黄色提示条 + "点击重新统计"按钮 | 自动化测试 |
| 16 | CostDashboard 预算超限时进度条红色 + 操作按钮 | 自动化测试 |
| 17 | MentionPopup 按 Esc 可关闭，不打断输入 | 手动测试 |
| 18 | RightWorkspacePanel 使用"AI 助手"聚合 Tab，不新增多个独立 P2 Tab | 手动测试 |
| 19 | P1 候选稿 accept/apply/reject 流程不受 P2 影响 | 回归测试 |
| 20 | 所有用户可见文案为中文白话（按钮、提示、状态文案不出现英文技术术语） | 代码审查 + UI 走查 |
| 21 | 不出现 Job / Trace / Session / error_code / caller_type 等技术词在用户可见文案中 | 代码审查 + UI 走查 |
| 22 | 危险操作（停止队列、关闭预算）弹出二次确认弹窗 | 手动测试 |
| 23 | 普通操作（采纳建议、确认继续）不弹二次确认 | 手动测试 |
| 24 | 轮询到终态后停止轮询 | 自动化测试 |
| 25 | failed 状态提供明确重试入口 | 手动测试 |
| 26 | 所有提交类按钮在 loading 时 disabled + spinner，不可重复点击 | 自动化测试 |
| 27 | P2 新增组件在颜色、按钮、间距、圆角、提示样式上与 V1.1 Workbench 保持一致 | UI 走查 |
| 28 | P2 功能入口不遮挡正文编辑区域，编辑器输入、选择、滚动不受影响 | UI 走查 |

---

## 附录：v1.0 → v1.1 变更摘要

| # | 变更 | 原因 |
|---|---|---|
| 1 | 结构调整："统一交互状态规范"从 §3 移至 §6（P2-S1/S2/S3 之后） | 先看功能集成再看统一规范更自然 |
| 2 | §2.2 右侧面板改为"AI 助手"聚合 Tab（自动续写 + 大纲辅助 + 开篇助手），P2 不改变 V1.1 既有 Tab 优先级 | 冻结更稳的 Tab 控制策略 |
| 3 | §4.2 Opening Agent 模仿风险分 warning 级（允许继续）+ high/blocking 级（不允许生成） | 与 P2_IMITATION_RISK_HIGH 错误码一致 |
| 4 | §4.3/§7.1 OutlineAssist apply 确认方式从"toast 确认"改为"Popconfirm 确认" | Toast 是操作后提示，不适合做确认 |
| 5 | §7.1 CandidateDraft apply 从"点击即执行"改为"沿用 P0/P1 HumanReviewGate 既有流程，P2 不新增确认" | 不破坏已有链路 |
| 6 | §2.1 StyleDNA 路由从硬编码 `/settings/style-dna` 改为"以现有设置路由体系为准" | 避免与现有路由体系冲突 |
| 7 | §9 组件映射表补"API 基础路径"列 | 对齐提示词要求的表格结构 |
| 8 | §8.3 新增后端返回 P2_FEATURE_DISABLED 时的前端处理（页面跳转/toast/静默忽略） | API 级禁用时前端行为明确 |
| 9 | §5.2 分析看板 AI 使用分析 Tab 补免责声明："AI 常见词汇仅统计出现频率，不代表文本一定由 AI 生成" | 避免误导用户 |
| 10 | §12 验收标准补 3 条（#26~28）：按钮 loading 防重复、UI 风格一致性、编辑器区域不遮挡 | UI 风格不回归类验收 |
