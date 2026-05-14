# InkTrace V2.0 DESIGN 系统与组件规范

版本：v1.0 / P1 视觉系统与组件规范候选冻结版  
状态：候选冻结  
所属阶段：InkTrace V2.0 P1

---

## 一、文档定位

`InkTrace-DESIGN.md` 是 InkTrace V2.0 的视觉系统与组件规范文档，面向 AI coding agent 与前端实现者，定义以下内容：

1. 视觉系统（颜色、排版、间距、圆角、边框、阴影、状态语义）。
2. 布局规范（三栏写作台、顶部状态栏、底部轻量状态条、响应式规则）。
3. 基础组件规范（Button、Card、Badge、Tabs、Input、Dialog、Toast、Drawer/Sheet）。
4. 业务组件规范（写作台、AI 工作区、候选稿、人审门、审阅、门控卡片）。
5. 状态表达规范（ready/degraded/blocked/running/waiting_for_user 等统一视觉语义）。

本文件不替代 `docs/03_design/InkTrace-V2.0-P1-UI-界面与交互设计.md`。P1-UI 负责信息架构与交互流程，DESIGN.md 负责视觉与组件落地规范。

---

## 二、整体风格方向

采用 **Notion + Linear + Mintlify** 的混合方向：

1. Notion 主视觉（写作主场）。
- 白底、极浅灰背景、轻边框、柔和卡片、大留白。
- 降低视觉噪音，支持长时间沉浸写作。

2. Linear 状态流（任务与状态表达）。
- 用于 AI 任务、AgentSession、CandidateDraft、ReviewIssue、ConflictGuard。
- 强调“紧凑可扫描、状态明确、动作明确”。

3. Mintlify 资料阅读（结构化阅读区）。
- 用于大纲、线索、伏笔、人物、StoryMemory 摘要、ReviewReport。
- 强化标题层级、段落节奏、折叠式阅读体验。

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
- 等宽（仅开发者模式片段）：`JetBrains Mono`, `SFMono-Regular`, monospace。

2. 字号层级。
- Display：28/34（书架页标题）。
- H1：24/32（页面主标题）。
- H2：20/28（区域标题）。
- H3：16/24（卡片标题）。
- Body-M：14/22（正文默认）。
- Body-S：13/20（说明文本）。
- Caption：12/18（状态、时间、辅助信息）。

3. 字重建议。
- 700：主标题。
- 600：区块标题、按钮文本。
- 500：正文强调。
- 400：普通正文。

### 3.3 间距 Token（8pt 系统）

- `space-1 = 4px`
- `space-2 = 8px`
- `space-3 = 12px`
- `space-4 = 16px`
- `space-5 = 20px`
- `space-6 = 24px`
- `space-8 = 32px`
- `space-10 = 40px`
- `space-12 = 48px`

### 3.4 圆角 Token

- `radius-xs = 6px`
- `radius-sm = 8px`
- `radius-md = 12px`
- `radius-lg = 16px`
- `radius-xl = 20px`
- `radius-pill = 999px`

### 3.5 阴影 Token

- `shadow-xs = 0 1px 2px rgba(16,24,40,0.04)`
- `shadow-sm = 0 2px 8px rgba(16,24,40,0.06)`
- `shadow-md = 0 6px 20px rgba(16,24,40,0.10)`

说明：优先边框表达层级，阴影仅作弱辅助，不使用厚重投影。

### 3.6 边框 Token

- `border-default = 1px solid #E5E5E5`
- `border-strong = 1px solid #D0D0D0`
- `border-focus = 1px solid #4F7CFF`
- `border-ai = 1px solid #7C8DFF`

### 3.7 状态色与语义

- 成功类：`success`。
- 进行中：`info`。
- 等待确认/降级：`warning`。
- 阻塞/失败：`error`。
- 未激活/只读：`textMuted` + `disabled`。

---

## 四、布局规范

### 4.1 桌面端主布局

```text
顶部状态栏（56px）
左侧章节栏（260-300px） | 中间正文编辑器（主自适应区域） | 右侧资料/AI工作区（折叠48px，展开360px，宽屏420px）
底部轻量状态条（32px）
```

### 4.2 区域尺寸

1. 顶部状态栏：56px。  
2. 左侧章节栏：260-300px。  
3. 中间正文编辑器：自适应主区域（永远最大）。  
4. 右侧工作区：
- 折叠：48px。
- 展开：360px。
- 宽屏（>= 1600px）：可扩展到 420px。  
5. 底部状态条：32px（轻量，不承载大型面板）。

### 4.3 响应式策略

1. 中等屏幕（约 1024-1279px）。
- 左栏可折叠。
- 右栏默认折叠。
- AI/审阅改为抽屉打开。
- 优先保障中间编辑器宽度。

2. 小屏幕/移动端（<1024px）。
- 左侧章节列表改抽屉。
- 右侧资料/AI 改底部 Sheet 或全屏二级页。
- 不同时展示三栏，正文优先。

### 4.4 硬性布局红线

1. AI 工作区不得覆盖正文编辑器。  
2. AI 不得作为正文编辑器下方的大面板长期存在。  
3. 正文编辑器始终是写作台最大视觉区域。  
4. AI 能力统一收纳到右侧可折叠工作区的 AI / 审阅 Tab。  
5. P0 AI Panel 不再继续扩展。

---

## 五、基础组件规范

### 5.1 Button

1. 用途。
- 主操作（Primary）、次操作（Secondary）、危险操作（Danger）、文本操作（Text）。

2. 样式。
- 高度：32/36/40px。
- 圆角：8px。
- 主按钮：`primary` 背景，白字。
- 次按钮：白底 + `border-default`。

3. 状态。
- default / hover / active / disabled / loading。

4. 禁用规则。
- blocked 条件下的 apply 按钮必须 disabled，并展示原因提示。

### 5.2 Card

1. 用途。
- 承载任务块、摘要信息、门控动作。

2. 样式。
- 背景 `background`。
- 边框 `border-default`。
- 圆角 12-16px。
- 内边距 16px。

3. 状态。
- normal / selected / warning / error / success。

### 5.3 StatusBadge

1. 用途。
- 展示统一状态：ready/running/degraded/blocked 等。

2. 样式。
- 胶囊形（`radius-pill`）。
- 文案 + 图标。
- 颜色遵循第七章状态映射。

3. 禁止。
- 不能只用颜色，必须有文字标签。

### 5.4 Tabs

1. 用途。
- 右侧工作区分层信息承载。

2. 样式。
- 顶部横向标签，当前 Tab 使用 `primary` 下划线或背景。

3. 状态。
- default / active / disabled / has-badge（新内容徽标）。

### 5.5 Input / Textarea

1. 用途。
- 搜索、标题编辑、简短说明输入。

2. 样式。
- 边框 `border-strong`。
- focus 使用 `border-focus` + 轻微外发光。

3. 状态。
- default / focus / error / disabled / readonly。

### 5.6 Dialog / Modal

1. 用途。
- 短确认：apply 确认、版本冲突提示、危险操作确认。

2. 规范。
- 只承载短流程。
- 不承载长期任务流（AI 全流程、审阅全流程）。

### 5.7 Toast

1. 用途。
- 非阻塞反馈：保存成功、apply 成功、任务失败 safe_message。

2. 规范。
- 展示 2-4 秒自动消失。
- 错误 Toast 必须显示 safe_message。

### 5.8 Drawer / Sheet

1. 用途。
- 中小屏承载右侧工作区内容。

2. 规范。
- Drawer 用于平板。
- Bottom Sheet 用于移动端。
- 打开时不遮蔽长期编辑语义（可关闭恢复编辑焦点）。

---

## 六、业务组件规范

### 6.1 WorkspaceLayout
- 职责：实现“左-中-右+顶+底”稳定框架。
- 规则：中间编辑区宽度优先，左右均可折叠。

### 6.2 TopStatusBar
- 内容：作品名、初始化状态、ContextPack readiness、同步状态、全局操作。
- 风格：轻量信息条，不承载大面积操作表单。

### 6.3 ChapterSidebar
- 内容：章节树、搜索、新建、字数、当前章节高亮、同步状态。
- 规则：窄屏进入抽屉，不挤压中间编辑器。

### 6.4 PureTextEditor
- 内容：标题、正文、基础编辑工具、字数、预计阅读时长。
- 规则：始终主舞台；CandidateDraft 应用前不得被覆盖。

### 6.5 RightWorkspacePanel
- Tab：大纲 / 线索 / 伏笔 / 人物 / AI / 审阅。
- 规则：统一承载 AI 与资料工作流，不回流到底部大面板。

### 6.6 AITab
- 卡片：AI Settings、初始化、ContextPack、续写、Quick Trial、AgentSession 摘要。
- 只显示可理解摘要，不显示完整 Prompt/完整 JSON/原始日志。

### 6.7 ReviewTab
- 卡片：CandidateDraft、AIReview、ConflictGuard、MemoryReviewGate 入口。
- 区分门控动作，避免混成单一杂糅面板。

### 6.8 CandidateDraftCard
- 显示：标题、来源、时间、状态、摘要、warning。
- 操作：预览、接受、拒绝、应用（按权限和状态显示）。
- 视觉：
  - `pending_review`：中性/橙色提示。
  - `accepted`：蓝/绿强调“已接受，未应用”。
  - `applied`：绿色完成态。

### 6.9 CandidateDraftCompareView
- 显示：候选稿与当前草稿差异。
- 规则：只做预览/确认，不自动覆盖正文。

### 6.10 AIReviewCard
- 显示：总体结论、维度评分、Issue 列表、severity。
- 明确：AIReview 仅辅助审阅，不自动裁决。

### 6.11 DirectionProposalCard
- 显示：A/B/C 方向摘要、风险、收益。
- 操作：用户选择与确认。
- 规则：DirectionSelection 不是 HumanReviewGate。

### 6.12 ChapterPlanList
- 显示：章节计划条目、状态、确认入口。
- 规则：PlanConfirmation 独立于 HumanReviewGate。

### 6.13 AgentSessionCard
- 显示：当前 Agent、当前 Step、状态、warning、错误摘要、checkpoint 摘要。
- 规则：普通用户看摘要，详细 trace 仅折叠区或开发者模式。

### 6.14 ConflictGuardBanner
- 状态：warning / blocking。
- 规则：blocking 未处理时，apply 视觉上必须限制（禁用+说明）。

### 6.15 ConflictResolveCard
- 显示：冲突对象、原因、影响范围、可处理动作。
- 规则：不自动修复，必须用户显式处理。

### 6.16 MemoryUpdateSuggestionCard
- 显示：记忆更新建议、影响对象、确认/拒绝/稍后。
- 规则：MemoryReviewGate 仅处理记忆更新，不等于 HumanReviewGate。

### 6.17 ApplyConfirmDialog
- 用途：apply 前二次确认与风险提示。
- 必含：目标章节、版本基线、冲突风险说明、用户确认动作。

### 6.18 BottomStatusBar
- 内容：字数、阅读时长、同步状态、轻量 AI 状态摘要。
- 规则：不承载大型 AI 控制面板。

---

## 七、状态视觉规范

| 状态 | 颜色 | 图标建议 | 展示语义 |
|---|---|---|---|
| ready | success | 绿点/对勾 | 可用，已就绪 |
| completed | success | 对勾 | 任务完成 |
| running | info | 旋转中指示 | 任务进行中 |
| waiting_for_user | warning | 时钟/暂停 | 等待用户动作 |
| degraded | warning | 感叹号 | 可继续但有风险 |
| blocked | error | 禁止符 | 已阻断，需处理 |
| failed | error | 错误叉号 | 执行失败 |
| idle | textMuted | 空心点 | 暂未开始 |
| stale | warning | 过期标记 | 上下文或结果可能过期 |
| pending_review | warning | 待审图标 | 待人工审阅 |
| accepted | info | 勾选框 | 已接受但未应用 |
| rejected | textMuted | 关闭图标 | 已拒绝 |
| applied | success | 绿勾 | 已应用到章节草稿 |
| superseded | textMuted | 替换图标 | 已被新版本替代 |

说明：`accepted` 与 `applied` 必须视觉明显区分。

---

## 八、交互动效规范

### 8.1 动效原则

1. 轻量、克制、低干扰。  
2. 不影响输入性能。  
3. 状态反馈优先于装饰。

### 8.2 动效细则

1. hover。
- 按钮/卡片：150ms 透明度或背景微变化。

2. focus。
- 输入组件：120ms 边框高亮过渡。

3. running。
- 状态图标轻旋转（线性 1.2s 循环），不使用复杂骨骼动画。

4. waiting_for_user。
- badge 轻呼吸（透明度 0.8-1.0，周期 1.8s）。

5. apply 成功。
- 编辑器中插入内容区域短暂高亮（2-3 秒后淡出）。

6. Tab 新内容徽标。
- 点状徽标淡入，不弹跳。

7. Drawer/Sheet 开关。
- 200ms ease-out 位移动画。

### 8.3 禁止

- 大范围复杂动画。
- 持续闪烁。
- 影响光标输入的重渲染动画。

---

## 九、可访问性与可读性

1. 状态不能只靠颜色，必须有文字与图标。  
2. 错误提示必须展示 safe_message。  
3. 移动端触控目标最小 44x44px。  
4. 支持键盘导航与焦点可见性。  
5. 长文本阅读需保证行高与段间距，避免视觉疲劳。  
6. 关键按钮文案语义明确：
- 接受（Accept）
- 应用到草稿（Apply to Draft）
- 拒绝（Reject）
不得混淆。

---

## 十、禁止风格

以下视觉或交互风格禁止进入 InkTrace P1：

1. 黑客控制台风。  
2. 霓虹 AI 科幻风。  
3. 大面积暗色主题作为默认。  
4. 复杂渐变背景。  
5. 厚重阴影层叠。  
6. 后台管理表格风主导写作页。  
7. AI 日志终端风直接暴露给普通用户。  
8. 在写作区下方继续扩展 AI Panel。

---

## 十一、与 P1-UI / P1-11 的关系

1. P1-UI：定义信息架构与交互流程。  
2. DESIGN.md：定义视觉系统与组件规范。  
3. P1-11：定义 API 与前端集成边界时，必须同时参考 P1-UI 与 DESIGN.md。

约束：
- P1-11 不得脱离 P1-UI 与 DESIGN.md 单独发明前端状态模型。
- 前端状态名、门控语义、视觉状态必须三者一致。

---

## 十二、验收标准

1. 能直接指导实现三栏写作台。  
2. AI 工作区不覆盖正文编辑器。  
3. P0 AI Panel 不继续扩展。  
4. 右侧工作区 Tabs（大纲/线索/伏笔/人物/AI/审阅）职责清楚。  
5. 颜色、字体、间距、圆角、阴影、边框规范明确。  
6. 基础组件规范明确并可复用。  
7. 业务组件规范明确并可映射到实现。  
8. 状态色与状态文案语义统一。  
9. CandidateDraft 的 accepted ≠ applied 视觉区分明确。  
10. AIReview 明确为辅助审阅，不自动裁决。  
11. ConflictGuard blocking 状态下 apply 视觉限制明确。  
12. 不引入 P2 UI 能力（自动连续续写、Style DNA、Citation Link、@ 引用、成本看板、分析看板）。  
13. P1-11 可直接引用本规范与 P1-UI 对齐开发。

---

## 硬性 UI 红线（实现前置检查清单）

1. AI 工作区不得覆盖正文编辑器。  
2. AI 不得作为正文编辑器下方的大面板长期存在。  
3. 正文编辑器始终是写作台最大视觉区域。  
4. AI 能力统一收纳到右侧可折叠工作区的 AI / 审阅 Tab。  
5. P0 AI Panel 不再继续扩展。  
6. 普通用户默认不看到完整 Prompt、完整 ContextPack、完整 JSON、Tool 调用日志、LLM 原始日志。  
7. API Key 不得以任何形式显示。  
8. CandidateDraft 应用前不得直接覆盖正文。  
9. AIReview 不得出现“自动接受 / 自动拒绝 / 自动应用”按钮。  
10. ConflictGuard blocking 未处理时，apply 视觉上必须被限制。  
11. 不引入 P2 UI 能力：自动连续续写队列、Style DNA、Citation Link、@ 引用、成本看板、分析看板。

---

## 仍需确认点

1. 右侧工作区默认宽度最终定为 360px 还是 400px。  
2. AI Tab 与审阅 Tab 是否允许用户自定义合并视图。  
3. CandidateDraft 对比默认放右侧还是可切换到中间全宽对比。  
4. apply 是否全场景强制二次确认。  
5. 移动端是否保留独立“审阅”二级页，还是并入 AI 页签。  
6. AgentTrace 在普通模式是否显示“摘要级一行信息”。
