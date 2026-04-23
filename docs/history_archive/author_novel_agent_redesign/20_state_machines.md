# 状态机清单

## 1. 目的

本清单用于把 InkTrace 中所有正式状态机集中整理，统一状态名称、状态迁移、驱动者、可逆性和失败恢复路径。

状态机清单不是状态架构的替代，而是状态架构的落地表。  
状态架构讲原则，本清单讲具体状态集与迁移规则。

---

## 2. 使用规则

每一个正式状态机至少应明确：

- 状态列表
- 合法迁移
- 迁移驱动者
- 是否可逆
- 失败与恢复路径
- 前端展示解释

如果某个对象影响：

- 前端状态展示
- 工作流是否可继续
- 智能体是否可执行下一步
- 是否允许自动覆盖

那么该对象必须有正式状态机。

---

## 3. 小说生命周期状态机

### 3.1 状态列表

- `created`
- `imported`
- `analyzing`
- `modeled`
- `ready`
- `writing`
- `revising`
- `completed`

### 3.2 合法迁移

- `created -> imported`
- `imported -> analyzing`
- `analyzing -> modeled`
- `modeled -> ready`
- `ready -> writing`
- `writing -> ready`
- `ready -> revising`
- `revising -> ready`
- `ready -> completed`

### 3.3 失败与回退

- `analyzing` 失败可回退到 `imported`
- `writing` 失败可回退到 `ready`
- `revising` 失败可回退到 `ready`

### 3.4 驱动者

- 导入工作流
- 分析工作流
- 写作工作流
- 改写/修订工作流
- 作者显式完成动作

### 3.5 前端解释

- `ready` 表示已具备续写/改写能力
- `writing` 表示正在生成章节
- `revising` 表示正在执行改写或问题修复

---

## 4. 章节生命周期状态机

### 4.1 状态列表

- `created`
- `imported`
- `analyzed`
- `planned`
- `drafting`
- `reviewing`
- `confirmed`
- `published`
- `archived`

### 4.2 合法迁移

- `created -> imported`
- `imported -> analyzed`
- `analyzed -> planned`
- `planned -> drafting`
- `drafting -> reviewing`
- `reviewing -> confirmed`
- `confirmed -> published`
- `confirmed -> drafting`
- `published -> archived`

### 4.3 失败与回退

- `drafting` 失败回退到 `planned`
- `reviewing` 失败回退到 `drafting`

### 4.4 驱动者

- 导入整理
- 章节分析
- 章节规划
- 写作任务
- 校验任务
- 作者确认/发布动作

### 4.5 说明

- `confirmed` 表示章节正文已确认可作为正式正文
- `published` 表示章节已进入更强保护级别

---

## 5. 任务生命周期状态机

### 5.1 状态列表

- `pending`
- `queued`
- `running`
- `paused`
- `retrying`
- `degraded`
- `success`
- `failed`
- `cancelled`

### 5.2 合法迁移

- `pending -> queued`
- `queued -> running`
- `running -> paused`
- `paused -> running`
- `running -> retrying`
- `retrying -> running`
- `running -> degraded`
- `degraded -> running`
- `running -> success`
- `running -> failed`
- `running -> cancelled`

### 5.3 驱动者

- 任务调度器
- 智能体调度
- 系统错误恢复
- 作者取消/恢复动作

### 5.4 说明

- `degraded` 表示任务已进入受控降级执行路径
- `failed` 表示已无法继续，需人工或新任务介入

---

## 6. 智能体运行状态机

### 6.1 状态列表

- `idle`
- `observing`
- `deciding`
- `dispatching`
- `waiting`
- `blocked`
- `completed`
- `failed`

### 6.2 合法迁移

- `idle -> observing`
- `observing -> deciding`
- `deciding -> dispatching`
- `dispatching -> waiting`
- `waiting -> deciding`
- `waiting -> completed`
- `deciding -> blocked`
- `dispatching -> failed`
- `waiting -> failed`

### 6.3 驱动者

- AuthorAgent
- 工作流回调
- 用户输入

### 6.4 说明

- `blocked` 表示智能体因权限、锁定、低可信或缺少前置条件而中止推进
- `waiting` 表示等待任务结果，不应误认为系统卡死

---

## 7. PlotArc 生命周期状态机

### 7.1 状态列表

- `active`
- `dormant`
- `completed`
- `archived`

### 7.2 合法迁移

- `active -> dormant`
- `dormant -> active`
- `active -> completed`
- `completed -> archived`
- `dormant -> archived`

### 7.3 驱动者

- PlotArc 更新工作流
- 章节推进写回
- 重整工作流
- 作者显式调整

### 7.4 说明

- `completed` 不等于立即删除，仍应保留历史意义
- `archived` 表示不再参与当前结构判断

---

## 8. PlotArc 阶段迁移状态机

### 8.1 状态列表

- `setup`
- `early_push`
- `escalation`
- `crisis`
- `turning_point`
- `payoff`
- `aftermath`

### 8.2 合法迁移

- 原地不动
- 前进一步
- 在特殊说明下有限跨一级以上

### 8.3 默认禁止

- 无理由逆跳
- 连续跨两级以上推进

### 8.4 驱动者

- 章节推进分析
- PlotArc 更新任务
- 作者显式修正

---

## 9. 草稿生命周期状态机

### 9.1 状态列表

- `generated`
- `detemplated`
- `rewritten`
- `validated`
- `needs_revision`
- `candidate_final`
- `accepted`
- `rejected`

### 9.2 合法迁移

- `generated -> detemplated`
- `detemplated -> rewritten`
- `rewritten -> validated`
- `validated -> candidate_final`
- `validated -> needs_revision`
- `needs_revision -> rewritten`
- `candidate_final -> accepted`
- `candidate_final -> rejected`

### 9.3 驱动者

- 写作工作流
- 改写工作流
- 校验任务
- 作者确认

### 9.4 说明

- `accepted` 后通常会生成正式章节正文版本
- `rejected` 不应删除历史，只是失去候选资格

---

## 10. 正文版本状态机

### 10.1 状态列表

- `candidate`
- `effective`
- `published`
- `superseded`
- `archived`

### 10.2 合法迁移

- `candidate -> effective`
- `effective -> published`
- `effective -> superseded`
- `published -> superseded`
- `superseded -> archived`

### 10.3 驱动者

- 作者确认
- 提交动作
- 发布动作
- 新版本生效

### 10.4 说明

- `effective` 是当前系统默认消费版本
- `published` 是更强保护级别版本
- `superseded` 表示已被新版本替代，但仍保留追溯能力

---

## 11. StoryModel 版本状态机

### 11.1 状态列表

- `candidate`
- `effective`
- `superseded`
- `archived`

### 11.2 合法迁移

- `candidate -> effective`
- `effective -> superseded`
- `superseded -> archived`

### 11.3 说明

- 新分析结果不应直接覆盖旧有效版本
- 必须先形成候选，再切换生效版本

---

## 12. MemoryView 状态机

### 12.1 状态列表

- `stale`
- `building`
- `fresh`
- `failed`

### 12.2 合法迁移

- `stale -> building`
- `building -> fresh`
- `building -> failed`
- `fresh -> stale`

### 12.3 驱动者

- 视图刷新任务
- 重整任务
- 结构对象版本变更

### 12.4 说明

- `MemoryView` 是可重建对象，因此允许 `failed` 后继续重建

---

## 13. 锁定状态机

### 13.1 状态列表

- `unlocked`
- `locked`
- `locked_with_override_request`

### 13.2 合法迁移

- `unlocked -> locked`
- `locked -> unlocked`
- `locked -> locked_with_override_request`
- `locked_with_override_request -> locked`
- `locked_with_override_request -> unlocked`

### 13.3 驱动者

- 作者锁定/解锁
- 系统提交覆盖请求

### 13.4 说明

- `locked_with_override_request` 表示任务触碰到锁定内容，但只能等待确认

---

## 14. 失败与恢复通用规则

所有状态机应遵循以下通用规则：

1. 不允许从失败态静默跳到成功态  
2. 恢复必须标记恢复来源  
3. 可逆状态应有明确回退条件  
4. 不可逆状态必须在文档中标明  

---

## 15. 当前重构的优先落地状态机

当前重构应优先实现以下状态机：

1. 小说生命周期状态机  
2. 任务生命周期状态机  
3. PlotArc 生命周期与阶段状态机  
4. 草稿生命周期状态机  
5. 正文版本状态机  

章节状态机和锁定状态机可以在第二阶段继续强化。

---

## 16. 与其他文档的关系

- [状态架构](./04_state_architecture.md) 提供原则
- [版本架构](./13_version_architecture.md) 约束版本态
- [写作与改写架构](./10_writing_and_rewriting_architecture.md) 消费草稿状态机
- [PlotArc 架构](./06_plot_arc_architecture.md) 消费弧状态与阶段状态机
- [重构路线图](./21_refactor_roadmap.md) 决定先落地哪些状态机
