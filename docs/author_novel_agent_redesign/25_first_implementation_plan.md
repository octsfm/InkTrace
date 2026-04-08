# 第一阶段实施计划

## 1. 计划目标

本计划用于把新的 UI 正式设计稿推进到可执行的第一阶段实现。

第一阶段不追求一次性完成全部 UI 重构，而是先搭出正确的产品骨架，并打通最小可运行闭环：

打开项目  
-> 进入工作区  
-> 打开章节  
-> 在新编辑器中续写  
-> 生成候选块  
-> 接受  
-> 触发审查  
-> 修一个 issue  
-> 保存成功

核心目标是：

**先把 InkTrace 从旧详情页 / 旧写作页 / 旧控制台入口里拉出来，建立新的 Dashboard -> Novel Workspace 主路径。**

## 2. 本阶段范围

第一阶段只做以下内容：

1. Dashboard 与 Novel Workspace 两层入口收口
2. Novel Workspace 四区布局稳定化
3. Writing 作为默认主视图
4. 左二栏对象导航基础版
5. 新写作台编辑器底座与章节打开 / 保存闭环
6. 候选块 / diff / issue 的第一版回流
7. 右侧 Copilot 区第一版
8. 基于旧后端接口的前端适配层

第一阶段明确不追求一次性完成：

- 完整复杂关系图
- 完整高级波浪线审查
- 完整全局命令系统
- 所有类型对象的 hover 卡片
- 复杂统计热力图

## 3. 实施原则

### 3.1 后端接口先保留

第一阶段以后端接口兼容为主，不先大改后端。

优先继续复用现有：

- `novelApi`
- `projectApi`
- `contentApi`
- `chapterEditorApi`

在前端增加适配层，把旧接口结果整理成新工作区对象模型。

### 3.2 新 UI 与旧页面并存

第一阶段不立刻删除旧页面，而是：

- 新增并优先导流到新工作区
- 保留旧 `NovelDetail`、旧 `NovelWrite`、旧 `ChapterEditor` 作为兼容入口
- 逐步削弱旧页面主路径地位

### 3.3 先搭主壳，再逐步替换内部能力

先确保：

- 导航对
- 工作区边界对
- 对象打开模型对
- 数据同步规则对

再逐步增强：

- 编辑器能力
- diff 能力
- issue 联动
- 结构可视化

## 4. 目标页面与工作区拆分

第一阶段前端目标结构：

- `Dashboard`
- `NovelWorkspace`
  - `Writing`
  - `Overview`
  - `Structure`
  - `Chapter Manager`
  - `Tasks & Audit`
  - `Settings`（可先占位）

### 4.1 Dashboard

第一阶段应具备：

- 小说列表
- 最近进入
- 新建小说入口
- 导入小说入口
- 继续写作主按钮

### 4.2 Novel Workspace

第一阶段应具备：

- 最左一级视图导航
- 左二对象导航
- 中央主内容区
- 右侧 Copilot 区
- 轻量顶部路径与状态区
- 可选底部状态栏基础能力

## 5. 默认导航规则

第一阶段就按正式规则执行：

- 从 Dashboard 点小说后直接进入 Workspace
- 默认优先进入 `Writing`
- 默认打开上次编辑位置
- 没有上次编辑位置则打开最近章节
- 没有可编辑章节时退回 `Overview`

不再默认进入旧详情页，也不再把详情页作为主跳板。

## 6. 第一阶段组件与模块清单

### 6.1 工作区壳层

- `NovelWorkspace`
- `WorkspacePrimaryNav`
- `WorkspaceObjectNav`
- `WorkspaceCopilotPanel`
- `WorkspaceTopBar`
- `WorkspaceStatusBar`

### 6.2 工作区子视图

- `WorkspaceWritingStudio`
- `WorkspaceOverview`
- `WorkspaceStructureStudio`
- `WorkspaceChapterManager`
- `WorkspaceTasksAudit`

### 6.3 共享状态层

需要建立统一的工作区状态层，至少管理：

- 当前小说
- 当前主视图
- 当前打开对象
- 当前章节
- 当前任务
- 当前上下文快照
- 当前候选块 / diff / issue 状态

### 6.4 适配层

新增适配层，把旧接口返回整理成：

- `WorkspaceNovelSummary`
- `WorkspaceChapterNode`
- `WorkspaceContextSnapshot`
- `WorkspaceTaskSummary`
- `WorkspaceDraftCandidate`
- `WorkspaceIssueSummary`

## 7. Writing Studio 第一阶段实现目标

第一阶段必须做到：

1. 可以打开章节
2. 可以看到章节标题与正文
3. 可以编辑正文
4. 可以保存正文
5. 可以在编辑器附近发起 AI 写作动作
6. 写作结果能以候选块方式回流
7. 审查结果能以 issue 列表方式回流
8. issue 可以定位正文

### 7.1 编辑器路线

第一阶段直接采用 TipTap / ProseMirror 作为正式编辑器底座，不再把 `textarea` 当中间阶段长期保留。

第一阶段编辑器先支持：

- 段落编辑
- 标题
- 选区
- 光标定位
- 候选块插入
- issue 锚点定位
- diff / 候选区域的基础装饰

### 7.2 候选块与 diff

第一阶段规则：

- 续写结果默认进入候选块
- 改写结果默认进入 diff 面板
- 候选块接受后才进入正式正文
- diff 未确认前不改变正式版本

### 7.3 issue 第一阶段

第一阶段先做到：

- issue 列表
- issue 定位正文
- issue 阻断等级展示
- issue 修复后重新审查入口

## 8. 左二对象导航区第一阶段

### 8.1 Writing 视图

左二栏先支持：

- 卷 / 章列表
- 当前章节高亮
- 搜索过滤
- 打开章节

### 8.2 Structure 视图

左二栏先支持：

- Story Model
- PlotArc
- 人物
- 世界观
- 风险点

### 8.3 Tasks 视图

左二栏先支持：

- 运行中
- 失败
- 已完成
- 审查

## 9. Copilot 第一阶段

右侧 Copilot 区先做三 Tab 结构：

- 对话
- 上下文
- 灵感

### 9.1 对话

先打通：

- 发送问题
- 展示回答
- 基于当前章节发起轻量协作

### 9.2 上下文

先展示：

- 当前章节
- 当前目标弧
- 当前焦点角色
- 当前阶段
- 当前任务快照

### 9.3 灵感

先展示静态或接口返回的建议卡片，不急着做复杂智能推荐引擎。

## 10. 任务与正文回流第一阶段

第一阶段必须严格按正式规则来：

- 写作完成 -> 候选块
- 改写完成 -> diff
- 审查完成 -> issue 列表 + 正文锚点
- 失败任务 -> 任务面板 + 恢复入口

## 11. 数据一致性第一阶段规则

第一阶段必须执行：

- 正式文本与候选文本分离
- 临时生成态不参与正式保存
- diff 未确认不写正式版本
- 阻断 issue 阻止正式提交
- 编辑器局部交互允许乐观更新
- 结构 / 任务 / 版本结果以后端确认结果为准

## 12. 跨工作区同步第一阶段规则

第一阶段至少打通以下同步：

- Writing 保存后，Chapter Manager 更新时间同步
- Writing 保存后，Overview 最近进度同步
- Tasks 审查结果更新后，Writing issue 状态同步
- Structure 更新后，Writing Context 下次刷新生效

## 13. 页面验收标准

### 13.1 导航层

- 可以从 Dashboard 进入新工作区
- 新工作区五个主视图可正常切换
- 默认落点符合写作优先规则

### 13.2 写作层

- 可以打开章节
- 可以编辑并保存
- 可以触发 AI 续写
- 可以看到候选块
- 可以接受候选块

### 13.3 审查层

- 可以触发审查
- 可以看到 issue 列表
- 可以从 issue 定位正文
- 可以修一个 issue 并重新保存

### 13.4 稳定性层

- 旧页面仍可访问
- 新工作区不依赖大规模后端重写
- 构建通过

## 14. 本阶段之后的下一步

第一阶段完成后，下一阶段优先继续：

1. 完善 TipTap 插件层
2. 强化 diff 编辑体验
3. 加 issue 行内装饰
4. 加命令面板
5. 强化 Structure 可视化
6. 收口旧详情页与旧写作页

## 15. 当前建议执行顺序

1. 更新 UI 主设计稿并冻结为正式基线
2. 对齐工作区路由与默认落点
3. 加固工作区共享状态层
4. 完成 Writing Studio 第一阶段闭环
5. 接入 issue / diff 第一版
6. 补 Dashboard 收口
7. 再开始削弱旧主路径
