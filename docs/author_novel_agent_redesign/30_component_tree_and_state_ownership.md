# 组件树与状态归属说明

## 1. 文档目标

本文件用于明确：

- 前端组件结构
- 每个组件归谁管理
- 状态归属在哪里
- 当前实现已经做到哪一层

核心目标是：

**避免状态散落、避免组件直接越级互相修改。**

## 2. 当前实现基线

本文件基于当前前端实现编写，重点对应：

- [NovelWorkspace.vue](/D:/Work/InkTrace/ink-trace/frontend/src/views/workspace/NovelWorkspace.vue)
- [WorkspaceWritingStudio.vue](/D:/Work/InkTrace/ink-trace/frontend/src/views/workspace/WorkspaceWritingStudio.vue)
- [WorkspaceSidebar.vue](/D:/Work/InkTrace/ink-trace/frontend/src/components/workspace/WorkspaceSidebar.vue)
- [WorkspaceCopilotPanel.vue](/D:/Work\\InkTrace\\ink-trace\\frontend\\src\\components\\workspace\\WorkspaceCopilotPanel.vue)
- [novelWorkspace.js](/D:/Work/InkTrace/ink-trace/frontend/src/stores/novelWorkspace.js)

当前前端已经具备：

1. `WorkspacePage` 级别的统一容器
2. Pinia store 作为共享状态中心
3. `Editor` 局部复杂状态集中在 `editor` 子状态里
4. Sidebar / Copilot / Writing Studio 通过共享状态协作

因此，这份文档不是从零定义，而是：

**对当前实现的组件树和状态归属做正式收口。**

## 3. 总体组件树

整体前端结构可抽象为：

```text
App
 ├── DashboardPage
 └── WorkspacePage
      ├── WorkspaceLayout
      │    ├── SidebarNav
      │    ├── SecondaryPanel
      │    ├── MainContent
      │    └── CopilotPanel
```

对应当前实现：

- `DashboardPage`：当前仍由旧列表页承接
- `WorkspacePage`：`NovelWorkspace.vue`
- `SidebarNav + SecondaryPanel`：当前由 `WorkspaceSidebar.vue` 合并承担
- `MainContent`：当前由 `router-view` 承载
- `CopilotPanel`：`WorkspaceCopilotPanel.vue`

## 4. Workspace 内组件树

结合当前实现，Workspace 内部组件树可描述为：

```text
WorkspaceLayout
 ├── SidebarNav
 ├── SecondaryPanel
 │    ├── ChapterTree
 │    ├── StructureNav
 │    └── TaskList
 │
 ├── MainContent
 │    ├── WritingView
 │    │    └── Editor
 │    │         ├── ParagraphNode
 │    │         ├── CandidateBlock
 │    │         ├── DiffBlock
 │    │         └── IssueMark
 │    │
 │    ├── OverviewView
 │    ├── StructureView
 │    ├── ChaptersView
 │    └── TasksView
 │
 └── CopilotPanel
      ├── ChatTab
      ├── ContextTab
      └── InspireTab
```

### 4.1 当前实现说明

当前还存在以下“合并态”：

- `WorkspaceSidebar.vue` 同时承担一级导航和章节树
- `WorkspaceWritingStudio.vue` 同时承担编辑器、候选稿区、diff 面板、issue 面板
- `WorkspaceCopilotPanel.vue` 已具备 `chat / context / inspire` 三 Tab，但 `chat` 仍是第一阶段占位形态

所以这份组件树既描述当前状态，也描述拆分方向。

## 5. 状态归属（核心）

### 5.1 全局状态（WorkspaceState）

```text
WorkspaceState {
  currentNovel
  currentView
  currentChapter
  currentObject
  currentTask
  contextSnapshot
  openDocuments
}
```

归属：

- `WorkspacePage`
- 当前实现中主要落在 `useNovelWorkspaceStore()`

说明：

- 当前 store 已有 `novel / chapters / project / organizeProgress / memoryView / activeArcs / copilotTab`
- 后续可逐步补齐为更正式的 `WorkspaceState`

### 5.2 EditorState

```text
EditorState {
  document
  selection
  candidates
  diffs
  issues
  saveState
}
```

当前实现中的近似对应：

- `editor.chapter`
- `editor.structuralDraft`
- `editor.detemplatedDraft`
- `editor.integrityCheck`
- `editor.dirty`
- `editor.saving`
- `editor.aiRunning`

归属：

- `Editor`
- 当前实现中由 `novelWorkspace` store 的 `editor` 子状态统一管理

### 5.3 CopilotState

```text
CopilotState {
  mode
  messages
  contextSnapshot
  activeTask
}
```

当前实现中的近似对应：

- `copilotTab`
- `activeArcs`
- `memoryView`
- `organizeProgress`

归属：

- `CopilotPanel`
- 当前实现中由 store + `WorkspaceCopilotPanel.vue` 共同消费

### 5.4 ChapterTreeState

```text
ChapterTreeState {
  nodes
  expandedKeys
  selectedKey
}
```

当前实现中的近似对应：

- `chapters`
- `currentChapterId`

归属：

- `ChapterTree`
- 当前实现中由 `WorkspaceSidebar.vue` 读取全局状态并派发事件

### 5.5 TaskPanelState

```text
TaskPanelState {
  runningTasks
  failedTasks
  history
  selectedTaskId
}
```

当前实现中的近似对应：

- `organizeProgress`
- `editor.chapterTask`

归属：

- `TasksView`

当前实现尚未形成完整统一的任务面板状态，这是下一阶段需要补强的重点。

## 6. 状态同步关系

当前和未来都必须满足以下同步关系：

### 6.1 章节树到工作区

`ChapterTree.selectedKey`  
-> `Workspace.currentChapter`

### 6.2 工作区到编辑器

`Workspace.currentChapter`  
-> `Editor.document`

当前实现对应：

- 路由 `chapterId`
- `workspace.loadEditorChapter(chapterId)`
- `editor.chapter.content`

### 6.3 Task 完成到 UI

`TaskCompleted`  
-> `Workspace.currentTask = null`  
-> 回流到 `Editor / IssuePanel / Structure`

当前实现对应：

- `runEditorAiAction()`
- 更新 `structuralDraft / detemplatedDraft / integrityCheck`

## 7. 单向数据流（必须遵守）

统一数据流必须是：

```text
用户操作
-> 组件触发事件
-> 更新 WorkspaceState
-> 触发 Task / 数据更新
-> 更新组件状态
```

禁止：

- 子组件直接改全局状态
- Copilot 直接改 Editor 文档

当前实现里，推荐继续保持：

- 组件通过 `workspace context` 调用统一方法
- store 负责实际状态更新

## 8. 组件通信方式

统一通过：

- Store
- 明确事件

例如：

- `ChapterSelected`
- `TaskCompleted`
- `IssueResolved`
- `DraftAccepted`

规则：

**优先 Store 驱动，事件总线只用于跨层广播，不作为主状态源。**

## 9. Editor 特殊规则

Editor 是组件树里最特殊的组件，必须单独约束。

### 9.1 编辑器内状态不等于后端状态

必须明确：

- Editor 当前文档不等于后端已保存版本
- Candidate / Diff / Issue 是 UI 层对象
- 正式数据只在确认后更新

### 9.2 保存状态

Editor 应有明确保存状态：

- `clean`
- `dirty`
- `saving`
- `save_failed`

当前实现中的近似字段：

- `dirty`
- `saving`

后续建议显式补出 `save_failed`

## 10. Copilot 与 Editor 关系

正确链路是：

`Copilot -> 触发 Task -> Task 产生结果 -> 结果注入 Editor`

禁止：

`Copilot -> 直接修改 Editor 文档`

当前实现基本已经遵守这条规则：

- Copilot 触发动作
- store 执行任务
- 写作台根据结果进行应用

## 11. 组件层级原则

统一原则如下：

1. `Workspace` 控制全局状态
2. 视图组件控制展示
3. `Editor` 控制局部复杂状态
4. `Copilot` 控制任务与交互状态
5. `Sidebar / ChapterTree` 控制导航状态

## 12. 文档结论

当前实现已经有了较好的雏形：

- `Workspace` 容器已存在
- 共享状态中心已存在
- `Writing` 已承担主要复杂交互
- `Copilot` 和 `Sidebar` 已经开始成形

这份文档的作用，是把当前这些实现收口成明确的组件树和状态边界，避免后续继续堆叠导致状态重新散掉。
