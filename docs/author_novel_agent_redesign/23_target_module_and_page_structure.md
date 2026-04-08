# 目标模块与页面结构

## 1. 目标

本文档用于把重构蓝图转化为更接近实施的模块边界图，明确未来后端模块划分、前端页面划分以及它们之间的关系。

它不是最终代码目录强制规定，但应作为新的主干组织参考。

---

## 2. 后端目标结构

后端应围绕“作者智能体 + 领域对象 + 工作流 + 模型调用”组织，而不是围绕历史页面接口组织。

建议的主干模块如下：

### 2.1 `agent`

职责：

- `AuthorAgent` 主入口
- 用户意图解析
- 状态判断
- 任务选择
- 工作流调度

建议包含：

- `author_agent_service`
- `agent_decision_engine`
- `agent_action_router`

### 2.2 `domain`

职责：

- 正式领域对象
- 聚合根
- 领域规则

建议包含：

- novel
- chapter
- story_model
- plot_arc
- draft
- validation_issue
- version

### 2.3 `memory`

职责：

- 章节记忆
- 全书结构记忆
- 续写连接记忆
- 视图构建

建议包含：

- `chapter_memory_service`
- `story_memory_service`
- `continuation_memory_service`
- `memory_view_builder`

### 2.4 `workflow`

职责：

- 导入工作流
- 接手工作流
- 写作工作流
- 改写工作流
- 校验修订工作流

建议包含：

- `import_workflow`
- `reorganize_workflow`
- `writing_workflow`
- `rewriting_workflow`
- `validation_workflow`

### 2.5 `planning`

职责：

- PlotArc 选择
- 章节规划
- 目标选择

建议包含：

- `arc_selection_service`
- `chapter_planning_service`
- `planning_policy_service`

### 2.6 `writing`

职责：

- 结构稿生成
- 续写生成
- 去模板化
- 风格改写
- 修订写作

建议包含：

- `structural_writing_service`
- `continuation_writing_service`
- `rewrite_service`
- `revision_writing_service`

### 2.7 `validation`

职责：

- 一致性校验
- issue list 生成
- 阻断判断

建议包含：

- `validation_service`
- `issue_builder`
- `quality_gate_service`

### 2.8 `models`

职责：

- Kimi / DeepSeek 路由
- prompt 构建
- 上下文装配
- 模型摘要记录

建议包含：

- `model_role_router`
- `prompt_registry`
- `context_builder`
- `model_call_recorder`

### 2.9 `tasks`

职责：

- 任务创建
- 任务调度
- 任务状态机
- 失败/恢复

### 2.10 `observability`

职责：

- trace
- 事件日志
- 结果比较
- 调试快照

---

## 3. 后端目标层次关系

建议的调用关系为：

`presentation/api -> agent -> workflow -> planning/writing/validation/memory/models -> domain/repository`

关键约束：

- API 不直接拼业务链
- agent 不直接写数据库细节
- workflow 不直接变成巨型业务垃圾桶
- models 层不承担业务决策

---

## 4. 前端目标页面结构

建议前端正式收口为以下页面：

### 4.1 概览台 `NovelOverview`

职责：

- 小说当前状态
- 最近进展
- 下一步建议
- 快速入口

### 4.2 结构台 `NovelStructure`

职责：

- Story Model
- PlotArc
- 人物/世界设定
- 风险点

### 4.3 章节台 `NovelChapters`

职责：

- 章节列表
- 单章入口
- 章节分析摘要
- 版本状态

### 4.4 写作台 `NovelWritingStudio`

职责：

- 章节计划
- 候选稿
- issue list
- 改写/修订
- 正式提交

### 4.5 任务台 `NovelTasks`

职责：

- 导入、重整、分析、校验等任务状态与控制

### 4.6 设置台 `NovelSettings`

职责：

- 小说级策略
- 模型设置
- 写作与改写策略

---

## 5. 前端共享能力层

除了页面外，应有共享的前端能力层：

### 5.1 `composables`

用于：

- 任务状态订阅
- 请求取消
- 页面轻量加载
- 智能体入口状态管理

### 5.2 `stores`

用于：

- 当前小说上下文
- 当前任务摘要
- 当前写作会话

### 5.3 `components`

建议按能力拆分：

- structure
- chapter
- writing
- task
- common

---

## 6. 页面间导航关系

建议的主导航逻辑：

- 概览台作为入口
- 从概览台进入结构台、章节台、写作台、任务台
- 任务台不再作为隐藏逻辑存在，而是正式入口

章节台与写作台之间应形成高频联动：

- 从章节进入写作
- 从写作回到章节
- 从结构建议跳转到写作

---

## 7. 旧页面到新页面的映射

### 7.1 旧 `NovelDetail`

拆分到：

- `NovelOverview`
- `NovelStructure`
- `NovelTasks`
- 部分章节入口到 `NovelChapters`

### 7.2 旧 `NovelWrite`

演化为：

- `NovelWritingStudio`

### 7.3 旧 `ChapterEditor`

保留为：

- 单章编辑器

但应成为章节台或写作台的子入口，而不是承担全局结构职责。

---

## 8. 首批实施建议

如果开始真正编码，建议优先新建：

### 后端

1. `agent`
2. `workflow`
3. `memory`
4. `validation`

### 前端

1. `NovelOverview`
2. `NovelTasks`
3. `NovelStructure`

原因：

- 先把入口、任务和结构台搭起来，能最快摆脱旧详情页

---

## 9. 不建议的做法

- 继续在旧 `NovelDetail` 上堆功能
- 继续让单个 service 同时承担 agent、workflow、planning、writing 多重职责
- 继续让前端页面直接适配后端历史结构，而不是按新对象重建

---

## 10. 当前重构落地要求

当前至少应以本结构作为：

- 新模块创建参考
- 新页面创建参考
- 旧链迁移落点参考

后续如需调整，必须与：

- 领域架构
- 工作流架构
- 前端交互架构

保持一致。

---

## 11. 与其他文档的关系

- [资产盘点与迁移清单](./22_asset_inventory_and_migration_map.md) 决定哪些能力迁到这些模块
- [前端交互架构](./16_frontend_interaction_architecture.md) 决定页面职责
- [工作流架构](./03_workflow_architecture.md) 决定 workflow 模块形态
- [重构路线图](./21_refactor_roadmap.md) 决定创建顺序
