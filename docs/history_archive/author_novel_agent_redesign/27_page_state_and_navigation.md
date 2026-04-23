# 页面状态与导航规则

## 1. 文档目标

本文件用于明确：

- 页面之间如何切换
- Workspace 内状态如何流转
- 默认路径与异常路径
- 自动跳转与禁止跳转规则
- 离开保护与切换保护规则

它回答的不是“页面长什么样”，而是：

**页面在系统运行时到底如何移动。**

## 2. 全局页面状态模型

系统只有两层页面状态：

```text
Dashboard
  -> Workspace
```

规则：

1. `Dashboard` 是唯一外部入口。
2. 进入某本小说后，进入 `Workspace`。
3. `Workspace` 内部不再通过“离开当前系统再进入另一个系统”的方式工作，而是通过视图状态切换。

## 3. Workspace 内状态模型

Workspace 不再跳页面，而是状态切换。

```text
WorkspaceState
  ├── currentNovel
  ├── currentView
  ├── currentChapter
  ├── currentObject
  ├── currentTask
  ├── currentContextSnapshot
  └── openDocuments
```

各字段定义：

- `currentNovel`：当前正在工作的小说
- `currentView`：当前主视图
- `currentChapter`：当前章节对象
- `currentObject`：当前中央工作对象
- `currentTask`：当前主任务
- `currentContextSnapshot`：当前 AI 上下文快照
- `openDocuments`：当前已打开对象集合

## 4. 主视图状态（currentView）

`currentView` 的正式枚举为：

- `Writing`
- `Overview`
- `Structure`
- `Chapters`
- `Tasks`
- `Settings`

规则：

1. 任意时刻只能有一个 `currentView`。
2. 主视图切换不销毁 `Workspace`。
3. 主视图切换后，`currentNovel` 必须保持稳定。

## 5. 当前对象状态（currentObject）

为了避免“当前对象”概念漂移，必须明确 `currentObject` 的正式类型。

`currentObject` 允许取值为以下对象之一：

- `chapter`
- `story_model`
- `plot_arc`
- `character`
- `world_rule`
- `task`
- `diff_session`

规则：

1. 中央区域始终绑定一个明确的 `currentObject`。
2. 不允许中央区域处于“既没有对象、又没有明确空状态”的模糊状态。
3. `currentObject` 的类型必须和 `currentView` 保持一致。

例如：

- `Writing` -> 优先 `chapter` 或 `diff_session`
- `Structure` -> `story_model / plot_arc / character / world_rule`
- `Tasks` -> `task`

## 6. 进入流程（入口状态图）

标准进入路径如下：

```text
打开系统
-> Dashboard
-> 选择小说
-> 进入 Workspace
   -> 如果有 lastEditedChapter -> Writing(该章节)
   -> 否则如果有章节 -> Writing(最近章节)
   -> 否则 -> Overview
```

规则：

1. 进入某本小说后，默认优先进入 `Writing`。
2. 只有在没有可写章节时，才退回 `Overview`。
3. 不再以“小说详情页”作为默认中转层。

## 7. Workspace 内切换规则

### 7.1 主导航切换

操作：

点击导航栏图标  
-> 更新 `currentView`  
-> 不销毁 `Workspace`  
-> 保持 `currentNovel`

补充规则：

- 尽量保留当前已打开对象上下文
- 主导航切换是“视角切换”，不是“系统重进”

### 7.2 章节点击

操作：

点击章节树节点  
-> `currentChapter` 更新  
-> `currentObject = chapter`  
-> `currentView` 强制切换为 `Writing`  
-> 编辑器定位

### 7.3 issue 点击

操作：

点击 issue  
-> 如果不在 `Writing`，切换到 `Writing`  
-> 打开相关章节  
-> 定位到锚点  
-> 高亮问题区域

规则：

- issue 点击允许切到 `Writing`
- 但不应导致跨系统跳转

### 7.4 Task 完成

`TaskCompleted` 事件发生后，根据任务类型回流：

- 写作 -> 候选块
- 改写 -> diff
- 审查 -> issue
- 结构更新 -> Structure 视图刷新

规则：

- 任务完成不等于强制跳页
- 结果优先回流到当前工作上下文

## 8. 自动跳转规则

### 8.1 允许的自动跳转

仅允许以下场景：

- 用户主动点击跳转
- 当前对象不存在
- 用户执行明确动作，例如“查看正文”“查看结构”
- issue 点击后为定位正文而切入 `Writing`

### 8.2 禁止的自动跳转

禁止以下行为：

- 任务完成后强制跳页
- AI 执行后自动把用户带离当前工作区
- issue 触发整页跳转
- 审查结果自动顶掉正文视图

## 9. 页面状态优先级

页面状态优先级用于定义：当多个页面意图冲突时，哪一个优先保住当前焦点。

建议优先级如下：

1. `Writing`
2. `改写 / diff`
3. `issue 定位`
4. `Structure`
5. `Overview`
6. `Tasks`

规则：

- 任何时候都优先保护 `Writing` 的连续性
- 其他视图默认是辅助视图

## 10. 并发状态冲突规则

### 10.1 正在生成中

当系统处于“写作生成中”时：

- 禁止新的写作任务
- 允许 issue 定位
- 允许浏览性操作
- 允许取消当前任务

### 10.2 改写中

当系统处于“改写中”时：

- 禁止重复改写同一目标
- 允许取消
- 允许只读浏览

### 10.3 审查中

当系统处于“审查中”时：

- 允许继续浏览
- 不应阻止轻量写作
- 但不应自动覆盖正文

## 11. 离开保护规则

为了避免用户在关键状态下误切换，需要定义离开保护。

### 11.1 未保存编辑

如果当前章节存在未保存修改：

- 切章节时应提示
- 切视图时应提示
- 关闭工作区时应提示

### 11.2 正在生成

如果当前处于写作生成中：

- 离开 `Writing` 应提示
- 允许用户明确中断
- 不允许静默丢弃任务

### 11.3 存在阻断 issue

如果存在阻断 issue：

- 允许切换到其他视图
- 但提交正式版本时必须阻止
- UI 应持续给出风险提示

## 12. 页面最小闭环状态流

最小可运行页面闭环如下：

```text
Dashboard
-> Workspace(Writing)
-> 打开章节
-> 发起续写
-> 生成候选块
-> 接受
-> 发起审查
-> 生成 issue
-> 修复
-> 保存
```

这条状态流用于定义：

- 第一阶段 UI 是否可用
- 页面切换逻辑是否正确
- 工作区内回流机制是否闭环

## 13. 页面状态设计原则

1. `Workspace` 内优先走状态切换，不走页面重建。
2. `Writing` 是默认落点和优先保护对象。
3. 自动跳转必须极少，且必须有明确理由。
4. 任务结果优先回流当前工作对象，而不是跳出当前工作流。
5. 所有离开行为都必须考虑未保存、生成中、阻断 issue 三类风险状态。
