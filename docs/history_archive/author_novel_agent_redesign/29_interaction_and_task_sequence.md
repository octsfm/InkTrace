# 交互与任务时序说明

## 1. 文档目标

本文件用于明确：

- 用户操作 -> 系统响应 -> UI 变化 -> 数据回流 的完整链路
- Task 生命周期与回流路径
- 现有实现中哪些链路已经存在
- 后续增强时哪些地方必须保持兼容

它的核心目标是避免出现这种情况：

**任务做完了，但 UI 不知道该怎么变。**

## 2. 当前实现基线

本文件基于当前前端实现编写，重点对应以下文件：

- [NovelWorkspace.vue](/D:/Work/InkTrace/ink-trace/frontend/src/views/workspace/NovelWorkspace.vue)
- [WorkspaceWritingStudio.vue](/D:/Work/InkTrace/ink-trace/frontend/src/views/workspace/WorkspaceWritingStudio.vue)
- [WorkspaceSidebar.vue](/D:/Work/InkTrace/ink-trace/frontend/src/components/workspace/WorkspaceSidebar.vue)
- [WorkspaceCopilotPanel.vue](/D:/Work/InkTrace/ink-trace/frontend/src/components/workspace/WorkspaceCopilotPanel.vue)
- [novelWorkspace.js](/D:/Work/InkTrace/ink-trace/frontend/src/stores/novelWorkspace.js)
- [router/index.js](/D:/Work/InkTrace/ink-trace/frontend/src/router/index.js)

当前已存在的实现基础包括：

1. `Workspace` 路由壳已存在。
2. `Writing / Overview / Structure / Chapters / Tasks` 五个主视图已存在。
3. `novelWorkspace` store 已经承担共享状态。
4. `Writing Studio` 已接入编辑器、候选稿、diff、issue 面板的第一版。
5. AI 动作已通过 store 中的 `runEditorAiAction()` 集中触发。

因此本文件不是纯理想稿，而是：

**在现有实现基础上的时序收口文档。**

## 3. 当前任务模型基线

当前实现里，严格意义上的前端 Task 实体还没有完全独立成统一 store 对象，但已经存在以下“任务影子”：

- `editor.aiRunning`
- `editor.chapterTask`
- `editor.structuralDraft`
- `editor.detemplatedDraft`
- `editor.integrityCheck`
- `organizeProgress`

这意味着现阶段的任务链已经存在，只是尚未完全抽象成统一 Task 模型。

本文件定义的时序规则，应视为：

- 对现有行为的解释
- 对下一步统一 Task 系统的约束

## 4. 写作主链路时序

这是当前最核心的交互时序。

### 4.1 时序

```text
用户打开章节
-> Editor 加载正文
-> 用户输入 / 编辑

用户触发续写（按钮 / slash / Copilot）
-> 创建 Task(type=writing)

TaskStarted
-> Copilot 显示运行状态
-> Editor 显示“生成中”状态

LLM 返回结果
-> TaskCompleted(type=writing)

-> 生成 CandidateBlock
-> 插入 Editor（候选态）

用户操作：
  接受
    -> DraftAccepted
    -> 合并进正文
    -> 触发 ChapterUpdated

  拒绝
    -> DraftRejected
    -> 删除 CandidateBlock
```

### 4.2 与现有实现的对应

当前实现中：

- 触发入口：`WorkspaceWritingStudio.vue` 的 `runAiAction('continue')`
- 任务执行：`novelWorkspace.js` 的 `runEditorAiAction('continue')`
- 回流载体：`editor.structuralDraft`
- UI 呈现：`DraftPreviewTabs.vue` + `diff / issue` 面板
- 接受动作：`applyDraftToEditor()`
- 保存动作：`saveEditorChapter()`

### 4.3 现阶段差距

当前实现已经具备“写作 -> 候选稿 -> 接受 -> 保存”基本链路，但还缺：

- 统一命名的 `Task(type=writing)` 对象
- 生成中占位块的正式可视化
- Copilot 任务模式的更明确状态展示

## 5. 改写（Rewrite）时序

### 5.1 时序

```text
用户选中一段文本
-> 点击“改写”

-> 创建 Task(type=rewrite)

TaskStarted
-> Copilot 进入 Task 模式

LLM 返回结果
-> TaskCompleted(type=rewrite)

-> 生成 DiffSession
-> Editor 显示 diff

用户操作：
  接受
    -> 替换原文本
    -> ChapterUpdated

  拒绝
    -> 关闭 diff
```

### 5.2 与现有实现的对应

当前实现里，“改写”已有雏形，但仍是章节级，不是严格的选区级：

- 触发入口：`runAiAction('rewrite')` / `runAiAction('optimize')`
- 结果回流：`editor.detemplatedDraft`
- 差异展示：`WorkspaceWritingStudio.vue` 中的 `diffRows`
- 接受路径：`applyDraftToEditor()`

### 5.3 现阶段差距

当前还没有真正的“选中文本 -> 局部改写 -> 局部 diff”链路。  
所以本阶段文档定义的 `rewrite` 时序，需区分两层：

1. 当前实现：整章级改写
2. 目标实现：选区级改写

## 6. 审查（Audit）时序

### 6.1 时序

```text
用户触发审查

-> 创建 Task(type=audit)

TaskStarted
-> Copilot 显示进度

LLM 返回结果
-> TaskCompleted(type=audit)

-> 生成 Issues[]
-> IssuePanel 更新
-> Editor 标记 IssueMark
```

### 6.2 与现有实现的对应

当前实现中：

- 触发入口：`runAiAction('analyze')`
- 回流对象：`editor.integrityCheck`
- 列表显示：`WorkspaceWritingStudio.vue` 的 `issueList`
- 风险说明：`riskNotes`

### 6.3 现阶段差距

当前已有 issue 列表，但还缺：

- 真正的 Editor 行内 `IssueMark`
- issue 与正文锚点的正式持久映射
- 审查任务在 Copilot 中的显式任务模式

## 7. Issue 修复时序

### 7.1 时序

```text
用户点击 Issue

-> Editor 定位锚点
-> 高亮问题区域

用户选择修复方式：
  手动修改
    -> ChapterUpdated
    -> IssueResolved

  AI 修复
    -> 创建 Task(type=fix)

TaskCompleted
-> 生成 TextPatch / Candidate / Diff
-> 用户确认后应用
-> IssueResolved
```

### 7.2 修复结果应用策略

这里必须补一条硬规则：

`fix -> TextPatch` 不能默认全部直接替换正文。  
应允许三种策略：

1. 自动应用
2. 候选应用
3. diff 应用

默认推荐：

- 低风险、短文本补丁：可自动应用
- 中高风险、长文本修复：优先候选或 diff

### 7.3 与现有实现的对应

当前实现中，Issue 修复链还未完全成型，现阶段主要依赖：

- 用户手动修改正文
- 再次触发审查

因此本节主要是下一阶段设计约束。

## 8. Structure 更新时序

### 8.1 时序

```text
用户触发结构分析

-> Task(type=structure)

TaskCompleted
-> 更新 StoryModel
-> 更新 PlotArc
-> 更新 ContextSnapshot
-> 标记 ContextChanged
```

### 8.2 延迟应用策略

为了避免打断当前写作，必须补一条规则：

如果当前用户正在 `Writing` 且正文处于高聚焦状态，则结构更新默认采用：

1. 更新后台结构数据
2. 标记 `pending structure refresh`
3. 在用户保存、切视图或显式刷新上下文后，再应用到当前 Context

### 8.3 与现有实现的对应

当前实现中：

- `loadStructure()` 会更新 `memoryView` 和 `activeArcs`
- `WorkspaceCopilotPanel` 已消费这些结构数据

但还没有正式的“写作中延迟应用结构变更”机制。

## 9. Task 状态机（统一）

统一 Task 状态机定义为：

```text
Created
-> Running
-> Completed
-> Failed
```

当前实现虽然尚未抽象出完整 Task store，但所有 AI 行为、整理任务和审查任务都应逐步向这套状态机收口。

## 10. Task 回流映射（关键）

统一回流映射如下：

- `writing` -> `CandidateBlock`
- `rewrite` -> `DiffSession`
- `audit` -> `Issues[]`
- `structure` -> `StructureUpdate`
- `fix` -> `TextPatch`
- `none` -> `No UI change`

这条映射是现有实现继续演进时必须保持稳定的规则。

## 11. UI 回流原则

### 11.1 核心原则

Task 不直接修改 UI 主状态。  
所有结果必须通过“中间层对象”进入 UI。

例如：

- `CandidateBlock`（写作）
- `DiffSession`（改写）
- `Issue`（审查）
- `StructureUpdate`（结构）
- `TextPatch`（修复）

### 11.2 对现有实现的意义

这条原则正好可以解释当前已经存在的模式：

- `structuralDraft`
- `detemplatedDraft`
- `integrityCheck`

它们本质上已经是中间层对象，只是命名和统一性还不够正式。

## 12. 失败时序规则

这部分在现有实现和未来统一任务系统里都必须明确。

### 12.1 通用失败链路

```text
TaskFailed
-> Copilot 退出运行态
-> Editor 清理生成中占位
-> Tasks 记录失败条目
-> UI 提供重试 / 恢复入口
```

### 12.2 当前实现对照

当前已有部分失败承接：

- `organizeProgress` 可以承接整理失败
- `errorMessage` 可承接工作区加载失败

但仍需后续补强：

- editor 级 AI 任务失败态
- rewrite / audit 的统一失败展示

## 13. 并发与冲突规则

### 13.1 Writing Task 运行中

- 禁止再次发起 `writing`
- 允许 issue 定位
- 允许浏览

### 13.2 Rewrite Task 运行中

- 禁止重复 rewrite 同一区域
- 允许取消

### 13.3 Audit

- 可并行（只读）
- 但不能直接覆盖正文

### 13.4 Structure 更新

- 延迟应用
- 不打断当前写作

## 14. 文档结论

当前前端实现已经具备了：

- 写作主链的第一版
- 改写主链的雏形
- 审查回流的第一版
- 结构数据回流的基础能力

本文件的作用，是把这些分散的实现正式收口成统一时序语言，供下一阶段继续演进。
