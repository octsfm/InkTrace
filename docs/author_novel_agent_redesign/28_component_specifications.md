# 核心组件规格说明

## 1. 文档目标

本文件用于定义核心 UI 组件的：

- 数据结构
- 行为
- 生命周期
- 与系统状态关系

它回答的是：

**Workspace 里最关键的组件到底是什么、怎么动、如何与状态系统联动。**

## 2. Workspace 全局状态

所有核心组件共享同一套工作区状态。

```text
WorkspaceState {
  currentNovel
  currentView
  currentChapter
  currentObject
  currentTask
  currentContextSnapshot
  openDocuments
}
```

规则：

1. 组件不应各自维护脱离全局的核心工作状态。
2. 当前小说、章节、任务、上下文必须通过统一状态源传递。
3. 组件可以有局部 UI 状态，但不能重新定义全局业务状态。

## 3. 章节树组件（ChapterTree）

### 3.1 数据结构

```text
ChapterNode {
  id
  title
  parentId
  order
  status
  updatedAt
}
```

### 3.2 行为

- 点击 -> 打开章节
- 搜索过滤
- 折叠 / 展开
- 拖拽排序

### 3.3 事件

- `ChapterSelected`
- `ChapterReordered`
- `ChapterCreated`

### 3.4 规则

- 当前章节必须高亮
- 排序后必须反映到章节管理视图
- 章节树是导航组件，不承担正文编辑逻辑

## 4. 编辑器组件（Editor）

### 4.1 技术基座

建议采用：

- TipTap
- ProseMirror

### 4.2 文档结构

```text
Doc
 ├ Paragraph
 ├ Heading
 ├ CandidateBlock
 ├ IssueMark
 ├ DiffBlock
```

### 4.3 编辑器状态

编辑器必须能表达以下状态：

- 正式文本
- 候选块
- 临时生成
- issue 标记

### 4.4 行为

- 编辑
- 插入 AI 内容
- 选区操作
- 定位

### 4.5 插件

建议插件层包括：

- `candidate plugin`
- `issue plugin`
- `diff plugin`

### 4.6 正式数据边界

必须明确：

- 编辑器当前文档不等于已保存版本
- `CandidateBlock / DiffBlock / IssueMark` 是编辑器表现层对象
- 这些对象不直接等于正式领域模型中的正文版本

也就是说：

**Editor 显示的是“当前工作态”，不是天然的“最终落库态”。**

## 5. 候选块组件（CandidateBlock）

### 5.1 数据结构

```text
Candidate {
  id
  content
  sourceTaskId
  status
}
```

### 5.2 生命周期

```text
生成
-> 展示
-> 接受 / 拒绝
-> 删除
```

### 5.3 行为

- `Accept`
- `Reject`
- `PartialAccept`

### 5.4 规则

- 不写入正式文本
- 不参与保存
- 必须用户确认

## 6. issue 面板（IssuePanel）

### 6.1 数据结构

```text
Issue {
  id
  type
  severity
  message
  anchor
  status
}
```

### 6.2 行为

- 点击 -> 定位正文
- 修复 -> 状态更新
- 过滤

### 6.3 锚点系统

```text
EditorPosition
-> 映射 issue
-> 高亮
```

### 6.4 规则

- issue 面板是正文问题入口，不是孤立列表
- 每个 issue 都应该有可定位锚点
- issue 修复后必须同步刷新编辑器标记

## 7. Copilot 组件

### 7.1 模式

- `Chat`
- `Task`
- `ReadOnly`

### 7.2 数据结构

```text
CopilotState {
  mode
  messages
  contextSnapshot
  activeTask
}
```

### 7.3 行为

- 发送消息
- 启动任务
- 显示状态

### 7.4 规则

- 任务模式优先
- context 冻结
- 不脱离章节

## 8. Task 组件

### 8.1 状态机

```text
Created
-> Running
-> Completed
-> Failed
```

### 8.2 数据结构

```text
Task {
  id
  type
  status
  progress
  resultType
  result
}
```

### 8.3 resultType

为了避免 `result` 语义过于模糊，必须补一个明确的结果类型：

- `candidate`
- `diff`
- `issues`
- `structure_update`
- `none`

### 8.4 回流

- 写作 -> `Candidate`
- 改写 -> `Diff`
- 审查 -> `Issue`
- 结构更新 -> `Structure` 视图刷新

### 8.5 规则

- Task 是运行对象，不是最终展示对象
- Task 完成后必须回流到对应 UI 载体

## 9. 事件模型（统一）

统一事件包括：

- `ChapterUpdated`
- `TaskStarted`
- `TaskCompleted`
- `TaskFailed`
- `IssueResolved`
- `DraftAccepted`
- `DraftRejected`
- `ContextChanged`

这些事件用于：

- 状态同步
- UI 刷新
- 日志埋点
- 调试追踪

## 10. 数据一致性规则

统一规则：

- UI 不等于数据持久化
- Candidate 不等于正式文本
- Diff 未确认不等于更新版本

这条规则必须在所有组件层成立，不能只停留在页面层。

## 11. 撤销机制

统一分三层：

- 编辑器级 undo
- 任务级回滚
- 版本级恢复

组件层要求：

- Editor 支持编辑器级撤销
- Task / Candidate / Diff 支持任务级撤销入口
- 历史版本组件支持版本恢复

## 12. 组件设计原则

1. 组件必须服务统一的 WorkspaceState。
2. 组件的表现层对象不能冒充正式领域对象。
3. 候选、diff、issue、task 都必须有清晰生命周期。
4. 组件之间的联动优先通过统一事件，而不是彼此直接耦合。
