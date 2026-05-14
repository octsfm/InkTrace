---
version: "v2.0"
name: "InkTrace-DESIGN"
description: "InkTrace V2.0 P1 视觉系统与组件规范（awesome-design-md 工程格式）"
colors:
  background: "#FFFFFF"
  appBackground: "#FAFAFA"
  panelBackground: "#FAFBFC"
  border: "#E5E5E5"
  borderStrong: "#D0D0D0"
  textPrimary: "#1F2933"
  textSecondary: "#667085"
  textMuted: "#9E9E9E"
  primary: "#4F7CFF"
  primarySoft: "rgba(79,124,255,0.10)"
  aiAccent: "#7C8DFF"
  success: "#4CAF50"
  warning: "#FF9800"
  error: "#EF5350"
  info: "#5B8DEF"
  disabled: "#D0D5DD"
typography:
  family:
    primary: '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif'
    mono: '"JetBrains Mono", "SFMono-Regular", monospace'
  scale:
    text-xs: "11px"
    text-sm: "13px"
    text-base: "15px"
    text-md: "16px"
    text-lg: "18px"
    text-xl: "20px"
    text-2xl: "24px"
spacing:
  base: "4px"
  tokens: ["space-1","space-2","space-3","space-4","space-5","space-6","space-8","space-10","space-12"]
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
shadows:
  card: "0 1px 3px rgba(0,0,0,0.04)"
  buttonPrimary: "0 1px 2px rgba(79,124,255,0.20)"
  dialog: "0 4px 24px rgba(0,0,0,0.12)"
  drawer: "-4px 0 24px rgba(0,0,0,0.10)"
  sheet: "0 -4px 24px rgba(0,0,0,0.10)"
layout:
  topBar: "56px"
  leftSidebar: "260-300px"
  rightPanelCollapsed: "48px"
  rightPanelExpanded: "360px"
  rightPanelWide: "420px"
  bottomBar: "32px"
components:
  base: ["Button","Card","StatusBadge","Tabs","Input","Textarea","Dialog","Modal","Toast","Drawer","Sheet"]
  business: ["WorkspaceLayout","TopStatusBar","ChapterSidebar","PureTextEditor","RightWorkspacePanel","AITab","ReviewTab","CandidateDraftCard","CandidateDraftCompareView","AIReviewCard","DirectionProposalCard","ChapterPlanList","AgentSessionCard","ConflictGuardBanner","ConflictResolveCard","MemoryUpdateSuggestionCard","ApplyConfirmDialog","BottomStatusBar"]
status:
  states: ["ready","completed","running","waiting_for_user","degraded","blocked","failed","idle","stale","pending_review","accepted","rejected","applied","superseded"]
---

# InkTrace-DESIGN

版本：v2.0  
状态：正式版  
合并来源：DESIGN.md v1.0 + DESIGN_001.md v1.0  
所属阶段：InkTrace V2.0 P1  
格式：awesome-design-md 工程格式

## 如何使用本文档（Agent 指引）

本文档是 InkTrace 的设计系统工程文件。

**AI coding agent 在实现任何 UI 之前，必须：**
1. 阅读本文档全文
2. 同时阅读 `P1-UI-界面与交互设计.md`（信息架构）
3. 同时阅读 `P1-11-API与前端集成边界.md`（数据接口）

**实现时强制要求：**
- 所有颜色必须使用附录 A 的 CSS 变量，禁止硬编码色值
- 所有尺寸（间距/圆角/字号）必须使用对应 Token，禁止魔法数字
- 所有状态必须使用第七章的统一状态色板
- 所有业务组件必须遵守第六章的硬性约束
- 实现完成后，必须对照第十二章验收标准逐项自查

## 目录
- [一、文档定位](#一文档定位)
- [二、整体风格方向](#二整体风格方向)
- [三、设计 Token](#三设计-token)
- [四、布局规范](#四布局规范)
- [五、基础组件规范](#五基础组件规范)
- [六、业务组件规范](#六业务组件规范)
- [七、状态视觉规范](#七状态视觉规范)
- [八、交互动效规范](#八交互动效规范)
- [九、可访问性与可读性](#九可访问性与可读性)
- [十、禁止风格](#十禁止风格)
- [十一、与 P1-UI / P1-11 的关系](#十一与-p1-ui--p1-11-的关系)
- [十二、验收标准](#十二验收标准)
- [仍需确认点](#仍需确认点)
- [附录 A：CSS 变量速查表](#附录-acss-变量速查表)
- [附录 B：硬性红线快速检查清单](#附录-b硬性红线快速检查清单)

---

## 一、文档定位

DESIGN.md 是给 AI coding agent / 前端实现使用的设计系统文件，负责视觉系统、组件规范、布局规范和状态表达规范。

它不是第二份交互文档：
- `P1-UI` 定义“信息架构与交互流程”。
- 本文档定义“视觉 Token 与组件实现规范”。

---

## 二、整体风格方向

1. Notion 主视觉。
- 白底、极浅灰背景、轻边框、柔和卡片、大留白、低干扰。

2. Linear 状态流。
- 用于 AI 任务、AgentSession、CandidateDraft（候选稿）、ReviewIssue、ConflictGuard。

3. Mintlify 资料阅读。
- 用于大纲、线索、伏笔、人物、StoryMemory 摘要、ReviewReport。

---

## 三、设计 Token

### 3.1 颜色 Token

| 语义 | 色值 | 用途 |
|---|---|---|
| background | #FFFFFF | 正文编辑器、主内容背景 |
| appBackground | #FAFAFA | 应用背景 |
| panelBackground | #FAFBFC | 左侧栏、右侧栏背景 |
| border | #E5E5E5 | 卡片、面板边框 |
| borderStrong | #D0D0D0 | 输入框、重点边框 |
| textPrimary | #1F2933 | 主文本 |
| textSecondary | #667085 | 次要文本 |
| textMuted | #9E9E9E | 弱提示 |
| primary | #4F7CFF | 主操作、选中态、链接 |
| primarySoft | rgba(79,124,255,0.10) | AI 高亮、选中背景 |
| aiAccent | #7C8DFF | AI 标识、AI 卡片边框 |
| success | #4CAF50 | ready / completed / applied |
| warning | #FF9800 | degraded / warning / waiting_for_user |
| error | #EF5350 | blocked / failed / conflict |
| info | #5B8DEF | running / in_progress |
| disabled | #D0D5DD | 禁用态 |

### 3.2 字体与字号

1. 字体族。
- 中文优先：`PingFang SC`, `Hiragino Sans GB`, `Microsoft YaHei`, `Noto Sans SC`, sans-serif。
- 英文/数字回退：`Inter`, `SF Pro Text`, sans-serif。
- 等宽（仅开发者模式）：`JetBrains Mono`, `SFMono-Regular`, monospace。

2. 字号层级语义。
- Display、H1、H2、H3、Body-M、Body-S、Caption。

3. 字重建议。
- 700：主标题。
- 600：区域标题、按钮文本。
- 500：强调。
- 400：正文。

### 3.3 字体语义名与 Token 映射表

| 语义名 | Token | 像素值 | 用途 |
|---|---|---|---|
| Display | `--text-2xl` | 24px | 书架页主标题 |
| H1 | `--text-xl` | 20px | 页面主标题 |
| H2 | `--text-lg` | 18px | 区域标题 |
| H3 | `--text-md` | 16px | 卡片标题 |
| Body-M | `--text-base` | 15px | 常规正文 |
| Body-S | `--text-sm` | 13px | 说明文本 |
| Caption | `--text-xs` | 11px | 状态与辅助信息 |

### 3.4 间距 Token（8pt 系统）

- `space-1 = 4px`
- `space-2 = 8px`
- `space-3 = 12px`
- `space-4 = 16px`
- `space-5 = 20px`
- `space-6 = 24px`
- `space-8 = 32px`
- `space-10 = 40px`
- `space-12 = 48px`

### 3.5 圆角 / 阴影 / 边框 Token

1. 圆角。
- `radius-xs = 6px`
- `radius-sm = 8px`
- `radius-md = 12px`
- `radius-lg = 16px`
- `radius-xl = 20px`
- `radius-pill = 999px`

2. 阴影。
- `shadow-xs`、`shadow-sm`、`shadow-md`。

3. 边框。
- `border-default`
- `border-strong`
- `border-focus`
- `border-ai`

---

## 四、布局规范

### 4.1 桌面端

- 顶部状态栏：56px。
- 左侧章节栏：260-300px。
- 中间编辑器：主自适应区域（`flex-grow` 主体）。
- 右侧工作区：折叠 48px、展开 360px、宽屏可 420px。
- 底部状态条：32px。

### 4.2 中屏与小屏

1. 中等屏幕。
- 左栏可折叠。
- 右栏默认折叠。
- AI/审阅走抽屉。

2. 小屏幕/移动端。
- 左栏抽屉。
- 右栏 Sheet 或全屏二级页。
- 不并列三栏，正文优先。

### 4.3 布局硬性红线

1. AI 工作区不得覆盖正文编辑器。  
2. AI 不得作为正文编辑器下方的大面板长期存在。  
3. 正文编辑器始终是写作台最大视觉区域。  
4. AI 能力统一收纳到右侧可折叠工作区的 AI / 审阅 Tab。  
5. P0 AI Panel 不再继续扩展。  

---

## 五、基础组件规范

### 5.1 Button

用途：主操作、次操作、危险操作、文本操作。  
样式：高度 32/36/40，圆角 `--radius-sm`，主按钮用 `--color-primary`。  
状态：default / hover / active / disabled / loading。

**实现检查点（agent 自查）：**
- [ ] primary 是否使用 `--color-primary`，未硬编码颜色
- [ ] disabled 是否为 `opacity: 0.40` + `cursor: not-allowed`
- [ ] loading 状态宽度是否稳定无抖动
- [ ] blocked 场景下 apply 是否禁用并附带原因提示

### 5.2 Card

用途：承载任务摘要、状态、门控动作。  
样式：边框 `--color-border`，圆角 `--radius-md`，内边距 16。

**实现检查点（agent 自查）：**
- [ ] 卡片边框是否统一用 `--color-border`
- [ ] 状态卡是否通过左侧状态线区分状态
- [ ] `accepted` 与 `applied` 左侧状态线是否可区分
- [ ] 卡片内部是否避免 JSON/日志直出

### 5.3 StatusBadge

用途：状态统一表达。  
样式：胶囊，文字+图标，按状态色映射。

**实现检查点（agent 自查）：**
- [ ] 状态是否同时包含颜色+图标+文字
- [ ] `waiting_for_user` 是否使用 warning 语义
- [ ] `blocked` 是否使用 error 语义
- [ ] `pending_review/accepted/applied` 是否语义分离

### 5.4 Tabs

用途：右侧工作区分层。  
样式：顶部标签，active 强调，new badge 支持。

**实现检查点（agent 自查）：**
- [ ] 右侧是否至少含“大纲/线索/伏笔/人物/AI/审阅”六个 Tab
- [ ] Tab 切换是否不影响中间编辑器输入
- [ ] 新内容徽标是否可显示/可清除
- [ ] 窄屏下是否可切换为抽屉/Sheet

### 5.5 Input / Textarea

用途：搜索、标题、说明输入。  
样式：默认 `--border-strong`，focus 使用 `--border-focus`。

**实现检查点（agent 自查）：**
- [ ] focus 态是否清晰可见
- [ ] error 态是否显示 safe_message
- [ ] disabled/readonly 是否视觉可辨
- [ ] 移动端触控区域是否 >= 44x44

### 5.6 Dialog / Modal

用途：短确认（apply、冲突、危险操作）。  
规则：不承载长期流程。

**实现检查点（agent 自查）：**
- [ ] apply 前是否存在确认对话框或等价强提示
- [ ] Dialog 是否仅用于短流程
- [ ] Escape 是否可关闭（非强制流程除外）
- [ ] blocking 冲突时是否先提示再限制动作

### 5.7 Toast

用途：非阻塞反馈。  
规则：2-4 秒自动消失，错误信息展示 safe_message。

**实现检查点（agent 自查）：**
- [ ] 错误 toast 是否只显示 safe_message
- [ ] 成功 toast 是否不遮挡编辑器核心区域
- [ ] 同时多条消息是否堆叠有序
- [ ] 是否没有暴露内部错误堆栈

### 5.8 Drawer / Sheet

用途：中小屏承载右侧工作区。  
规则：平板 Drawer，手机 Sheet/全屏二级页。

**实现检查点（agent 自查）：**
- [ ] 小屏是否不会与编辑区并列三栏
- [ ] Drawer/Sheet 打开后是否仍可明确返回编辑器
- [ ] 关闭操作是否明确可达
- [ ] 动画是否轻量不掉帧

---

## 六、业务组件规范

### 6.1 WorkspaceLayout
- 三栏主框架。
- 中间编辑器永远优先。

**实现检查点（agent 自查）：**
- [ ] 中间区域是否为主 `flex-grow`
- [ ] 左右侧是否独立折叠
- [ ] 顶部与底部高度是否稳定

### 6.2 TopStatusBar
- 显示作品状态、初始化状态、ContextPack readiness、同步状态。

**实现检查点（agent 自查）：**
- [ ] 状态项是否可扫描
- [ ] 是否避免放置复杂表单
- [ ] 是否支持全局关键操作入口

### 6.3 ChapterSidebar
- 章节树、搜索、新建、高亮、同步。

**实现检查点（agent 自查）：**
- [ ] 当前章节是否高亮清晰
- [ ] 搜索是否即时过滤
- [ ] 窄屏是否切换抽屉

### 6.4 PureTextEditor
- 标题、正文、工具、字数、阅读时长。

**实现检查点（agent 自查）：**
- [ ] 编辑区是否始终最大视觉区域
- [ ] CandidateDraft（候选稿）未 apply 前是否不覆盖正文
- [ ] 沉浸模式是否可隐藏侧栏

### 6.5 RightWorkspacePanel
- 承载六个 Tab 的统一入口。

**实现检查点（agent 自查）：**
- [ ] AI 与审阅是否都在右侧工作区
- [ ] 是否支持折叠/展开
- [ ] 是否不在底部扩展 AI 大面板

### 6.6 AITab
- AI Settings、初始化、ContextPack、续写、Quick Trial、AgentSession 摘要。

**实现检查点（agent 自查）：**
- [ ] 是否只展示用户可理解摘要
- [ ] 是否隐藏完整 Prompt/JSON/日志
- [ ] 是否有 degraded/blocked 明确提示

### 6.7 ReviewTab
- CandidateDraft（候选稿）、AIReview、ConflictGuard、MemoryReviewGate 入口。

**实现检查点（agent 自查）：**
- [ ] 人审门与记忆门是否视觉分离
- [ ] Conflict 卡片是否先于 apply 风险展示
- [ ] 是否不混成单一大杂烩面板

### 6.8 CandidateDraftCard
- 显示状态、摘要、来源与动作。
- 操作统一术语：accept / reject / apply。

**实现检查点（agent 自查）：**
- [ ] `accepted` 与 `applied` 是否视觉可区分
- [ ] apply 是否为显式用户动作
- [ ] 是否有 `pending_review/stale/superseded` 表达
- [ ] apply 前是否不改正文

### 6.9 CandidateDraftCompareView
- 候选稿与当前草稿差异视图。

**实现检查点（agent 自查）：**
- [ ] 差异视图是否可读
- [ ] 是否不自动合并
- [ ] 是否在 apply 前提供明确确认

### 6.10 AIReviewCard
- 展示审阅摘要、维度分布、Issue 列表。

**实现检查点（agent 自查）：**
- [ ] 是否仅辅助审阅
- [ ] 是否无自动 accept/reject/apply 按钮
- [ ] review 失败时是否不阻断人工流程

### 6.11 DirectionProposalCard
- A/B/C 方向、风险、收益、选择。

**实现检查点（agent 自查）：**
- [ ] 是否要求用户显式选择方向
- [ ] 是否未与 HumanReviewGate 混淆
- [ ] 是否支持“稍后选择”状态

### 6.12 ChapterPlanList
- 章节计划条目与确认动作。

**实现检查点（agent 自查）：**
- [ ] PlanConfirmation 是否独立呈现
- [ ] 是否支持计划摘要快速浏览
- [ ] 是否不混入候选稿裁决动作

### 6.13 AgentSessionCard
- 当前 Agent、Step、状态、warning、checkpoint 摘要。

**实现检查点（agent 自查）：**
- [ ] 普通模式是否只显示摘要
- [ ] 详细 trace 是否默认折叠
- [ ] 是否未展示完整 Prompt/原始日志

### 6.14 ConflictGuardBanner
- warning / blocking 状态横幅。

**实现检查点（agent 自查）：**
- [ ] blocking 是否有强视觉阻断
- [ ] warning 与 blocking 是否区分明确
- [ ] 是否给出“下一步处理动作”入口

### 6.15 ConflictResolveCard
- 冲突对象、原因、影响范围、处理动作。

**实现检查点（agent 自查）：**
- [ ] 是否无自动修复按钮
- [ ] 是否要求用户显式处理
- [ ] 是否支持继续/返回修改/取消

### 6.16 MemoryUpdateSuggestionCard
- 记忆更新建议、影响范围、确认/拒绝/稍后。

**实现检查点（agent 自查）：**
- [ ] 是否与 HumanReviewGate 分离
- [ ] 是否不自动写入正式 StoryMemory
- [ ] 是否可“稍后处理”

### 6.17 ApplyConfirmDialog
- apply 前确认目标、版本、风险。

**实现检查点（agent 自查）：**
- [ ] 是否显示目标章节与版本基线
- [ ] 是否明确冲突风险
- [ ] 用户取消是否不产生副作用

### 6.18 BottomStatusBar
- 字数、阅读时长、同步、轻量 AI 状态。

**实现检查点（agent 自查）：**
- [ ] 高度是否保持 32px
- [ ] 是否未扩展为 AI 大面板
- [ ] 状态信息是否简洁可扫描

### 6.19 组件依赖关系

| 业务组件 | 依赖的基础组件 |
|---|---|
| WorkspaceLayout | Card, Tabs, Drawer/Sheet |
| TopStatusBar | StatusBadge, Button |
| ChapterSidebar | Input, Button, StatusBadge |
| PureTextEditor | Input/Textarea, Toast, Dialog |
| RightWorkspacePanel | Tabs, Card, Drawer/Sheet |
| AITab | Card, Button, StatusBadge, Toast |
| ReviewTab | Card, Tabs, StatusBadge, Button |
| CandidateDraftCard | Card, StatusBadge, Button, Dialog |
| CandidateDraftCompareView | Card, Tabs, Button |
| AIReviewCard | Card, StatusBadge, Button |
| DirectionProposalCard | Card, Button, StatusBadge |
| ChapterPlanList | Card, Button, Tabs |
| AgentSessionCard | Card, StatusBadge, Button |
| ConflictGuardBanner | StatusBadge, Button |
| ConflictResolveCard | Card, Button, Dialog |
| MemoryUpdateSuggestionCard | Card, StatusBadge, Button |
| ApplyConfirmDialog | Dialog, Button, StatusBadge |
| BottomStatusBar | StatusBadge |

---

## 七、状态视觉规范

统一状态：
- ready
- completed
- running
- waiting_for_user
- degraded
- blocked
- failed
- idle
- stale
- pending_review
- accepted
- rejected
- applied
- superseded

状态表现规则：
1. 颜色使用 `--color-success / --color-warning / --color-error / --color-info / --color-text-muted`。  
2. 必须包含图标与文字。  
3. `accepted` 与 `applied` 必须双重区分（文案+视觉）。

---

## 八、交互动效规范

1. 动效原则。
- 轻量、克制、低干扰。
- 不影响输入性能。

2. 动效范围。
- hover/focus：120-150ms。
- Drawer/Sheet：200ms。
- waiting_for_user：轻呼吸。
- running：轻旋转。
- apply 成功：短暂高亮后淡出。

3. 禁止。
- 复杂、长时、闪烁、炫技动效。

---

## 九、可访问性与可读性

1. 状态表达必须“颜色+图标+文字”。  
2. 错误必须有 safe_message。  
3. 移动端触控区 >= 44x44。  
4. 键盘可操作，焦点可见。  
5. 长文本阅读需舒适行高与段距。

---

## 十、禁止风格

1. 黑客控制台风。  
2. 霓虹 AI 科幻风。  
3. 大面积暗色默认主题。  
4. 复杂渐变。  
5. 厚重阴影。  
6. 后台管理表格风主导写作页。  
7. AI 日志终端风。  
8. 在写作区下方继续扩展 AI Panel。

## 风格参考边界

本设计采用 Notion + Linear + Mintlify 混合方向，但有明确边界：

| 参考来源 | 借鉴什么 | 不借鉴什么 |
|---------|---------|----------|
| Notion | 白底灰背景、轻边框、大留白、卡片节奏 | Notion 的数据库 UI、拖拽块、斜线命令 |
| Linear | 紧凑状态列表、状态图标、颜色克制、任务卡片 | Linear 的暗色主题、侧边深色导航 |
| Mintlify | 文档式段落排版、标题层级、折叠阅读 | Mintlify 的品牌绿色、文档站导航结构 |

**禁止**：直接照搬任何参考品牌的完整视觉风格、颜色体系、Logo 或专有元素。

---

## 十一、与 P1-UI / P1-11 的关系

1. P1-UI 定义信息架构与交互。  
2. DESIGN.md 定义视觉系统与组件规范。  
3. P1-11 API 与前端集成边界必须同时参考 P1-UI 和 DESIGN.md。

额外强约束：  
**前端开发者和 AI coding agent 在开始任何页面实现前，必须同时阅读 P1-UI、DESIGN.md、P1-11 三份文档，不得只读其中一份。**

---

## 十二、验收标准

### 🔴 强制（发布阻断）
- [ ] 三栏写作台实现完整，中间编辑器为最大视觉区域
- [ ] AI 工作区不覆盖正文编辑器
- [ ] P0 AI Panel 未继续扩展，AI 能力全部收纳右侧 Tab
- [ ] CandidateDraft（候选稿）在 apply 前不覆盖正文
- [ ] `accepted` 与 `applied` 视觉可区分
- [ ] AIReview 无自动 accept/reject/apply 按钮
- [ ] ConflictGuard blocking 未处理时 apply 必须禁用
- [ ] API Key 未在 UI 中任何位置显示
- [ ] 未显示完整 Prompt / 完整 ContextPack / 完整 JSON / Tool 调用日志 / LLM 原始日志
- [ ] 未引入 P2 UI 能力（自动连续续写队列、Style DNA、Citation Link、@ 引用、成本看板、分析看板）

### 🟡 重要（发布前处理）
- [ ] 颜色、字体、间距、圆角、阴影、边框 Token 使用一致
- [ ] 基础组件规范与业务组件规范已按本文档落地
- [ ] 右侧工作区六个 Tab 职责清楚且可切换
- [ ] 状态表达遵循“颜色+图标+文字”
- [ ] 错误提示统一 safe_message
- [ ] 移动端触控区满足 44x44
- [ ] 小屏抽屉/Sheet 响应式可用

### 🟢 建议（可推迟）
- [ ] Tab 新内容徽标节奏优化
- [ ] AgentSession 摘要信息密度优化
- [ ] CandidateDraft 对比阅读排版优化
- [ ] 审阅与门控卡片信息折叠策略优化

### 验收补充（来自硬性 UI 红线）
- [ ] AI 工作区不得覆盖正文编辑器
- [ ] AI 不得作为正文编辑器下方的大面板长期存在
- [ ] 正文编辑器始终是写作台最大视觉区域
- [ ] AI 能力统一收纳到右侧可折叠工作区的 AI / 审阅 Tab
- [ ] P0 AI Panel 不再继续扩展
- [ ] 普通用户默认不看到完整 Prompt、完整 ContextPack、完整 JSON、Tool 调用日志、LLM 原始日志
- [ ] API Key 不得以任何形式显示
- [ ] CandidateDraft 应用前不得直接覆盖正文
- [ ] AIReview 不得出现“自动接受 / 自动拒绝 / 自动应用”按钮
- [ ] ConflictGuard blocking 未处理时，apply 视觉上必须被限制
- [ ] 不引入 P2 UI 能力：自动连续续写队列、Style DNA、Citation Link、@ 引用、成本看板、分析看板

---

## 仍需确认点

1. 右侧工作区默认宽度是 320、360 还是 400。  
2. AI Tab 和审阅 Tab 是否分开，还是 AI Tab 内包含审阅。  
3. CandidateDraft 预览是右侧栏展示，还是打开中间对比视图。  
4. apply 是否需要二次确认弹窗。  
5. Direction Proposal 是否以卡片横排还是列表展示。  
6. ChapterPlan 是否允许在右侧栏直接编辑。  
7. AgentTrace 是否普通用户可见，还是只在开发者模式可见。  
8. 移动端是否优先只保留正文编辑器。  
9. 右侧“纲/线/伏/人/AI/审阅”是否支持用户自定义排序。  
10. P0 当前 AI Panel 是否在 P1 前端重构时完全移除，还是保留为开发者调试入口。

---

## 附录 A：CSS 变量速查表

```css
:root {
  /* === 背景 === */
  --color-bg-primary: #FFFFFF;
  --color-bg-app: #FAFAFA;
  --color-bg-panel: #FAFBFC;
  --color-bg-hover: #F5F5F5;
  --color-bg-active: rgba(79,124,255,0.06);
  --color-bg-ai-highlight: rgba(124,141,255,0.10);

  /* === 文本 === */
  --color-text-primary: #1F2933;
  --color-text-secondary: #667085;
  --color-text-muted: #9E9E9E;
  --color-text-inverse: #FFFFFF;

  /* === 边框 === */
  --color-border: #E5E5E5;
  --color-border-strong: #D0D0D0;
  --color-border-focus: #4F7CFF;

  /* === 品牌/语义 === */
  --color-primary: #4F7CFF;
  --color-primary-soft: rgba(79,124,255,0.10);
  --color-ai-accent: #7C8DFF;
  --color-ai-accent-soft: rgba(124,141,255,0.10);
  --color-success: #4CAF50;
  --color-success-soft: rgba(76,175,80,0.10);
  --color-warning: #FF9800;
  --color-warning-soft: rgba(255,152,0,0.10);
  --color-error: #EF5350;
  --color-error-soft: rgba(239,83,80,0.10);
  --color-info: #5B8DEF;
  --color-info-soft: rgba(91,141,239,0.10);
  --color-disabled: #D0D5DD;

  /* === 字体 === */
  --font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", -apple-system, BlinkMacSystemFont, sans-serif;
  --font-family-mono: "JetBrains Mono", "Fira Code", "SF Mono", "Consolas", monospace;

  /* === 字号 === */
  --text-xs: 0.6875rem;   /* 11px */
  --text-sm: 0.8125rem;   /* 13px */
  --text-base: 0.9375rem; /* 15px */
  --text-md: 1rem;        /* 16px */
  --text-lg: 1.125rem;    /* 18px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */

  /* === 行高 === */
  --leading-tight: 1.25;
  --leading-normal: 1.6;
  --leading-relaxed: 1.8;
  --leading-loose: 2.0;

  /* === 间距（4px 基准）=== */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  /* === 圆角 === */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* === 阴影 === */
  --shadow-card: 0 1px 3px rgba(0,0,0,0.04);
  --shadow-button-primary: 0 1px 2px rgba(79,124,255,0.20);
  --shadow-dialog: 0 4px 24px rgba(0,0,0,0.12);
  --shadow-drawer: -4px 0 24px rgba(0,0,0,0.10);
  --shadow-sheet: 0 -4px 24px rgba(0,0,0,0.10);
}
```

## 附录 B：硬性红线快速检查清单

实现任何页面前，逐项确认：

### 布局红线
- [ ] AI 工作区未覆盖正文编辑器
- [ ] 正文编辑器是写作台最大视觉区域（CSS flex-grow 保证）
- [ ] 底部状态条高度 ≤ 32px，未扩展为大面板
- [ ] AI 能力全部收纳在右侧工作区 Tab 内

### 安全红线
- [ ] API Key 输入使用 type="password"，无明文展示
- [ ] 用户界面不展示完整 Prompt / 完整 JSON / LLM 原始日志
- [ ] AIReview 卡片无 [自动裁决] 按钮
- [ ] ConflictGuard blocking 状态下 apply 按钮已 disabled
- [ ] CandidateDraft 应用前未直接覆盖正文

### 状态红线
- [ ] 所有状态同时使用颜色 + 图标 + 文字标签（无纯色状态）
- [ ] accepted 与 applied 视觉可区分（单线 vs 双线左边框）
- [ ] 禁用状态使用 opacity: 0.40，不只是改变颜色

### P1 范围红线
- [ ] 未引入 P2 能力（自动队列 / Style DNA / Citation Link / 成本看板）
- [ ] 未在正文编辑器下方新增 AI Panel
