# 状态架构

## 1. 目标

状态架构用于定义系统中所有正式状态，以及各类状态如何被驱动、如何流转、何时可逆、何时必须阻断。

这份文档不讨论“任务怎么执行”，而讨论“系统当前处于什么阶段、是否允许进入下一步”。

没有统一状态架构，会直接导致：

- 前端无法判断当前该展示什么
- 工作流无法判断是否允许进入下一步
- 智能体无法判断小说是否具备续写条件
- 失败恢复缺少稳定依据

## 2. 设计原则

1. 状态必须少而正式，不能把临时提示文案当状态
2. 状态必须区分领域状态与运行状态
3. 状态流转必须由明确驱动者触发
4. 任意长任务失败后，必须能回到上一个稳定状态
5. `ready` 是进入写作链、改写链、续写链的统一入口状态

## 3. 状态分类

系统至少存在四类正式状态：

1. 小说状态
2. 章节状态
3. 任务状态
4. 智能体运行状态

另有一类辅助状态：

5. 草稿状态

PlotArc 生命周期状态在 [20_state_machines.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/20_state_machines.md) 中单独细化。

## 4. 小说状态

### 4.1 小说正式状态

- `created`
  已创建项目，但尚未导入正文、大纲或草稿。
- `imported`
  已导入基础内容，但尚未完成结构分析。
- `analyzing`
  正在执行结构分析、建模或重整。
- `modeled`
  已完成 Story Model 构建，但尚未通过完整可写校验。
- `ready`
  已具备续写、改写、规划、写作的前提条件。
- `writing`
  正在生成新章节或自动创作正文。
- `revising`
  正在执行改写、修订或问题单回环。
- `completed`
  小说已完成，默认不再自动推进。
- `blocked`
  因关键错误、关键依赖缺失或低可信结构结果而被阻断。

### 4.2 小说稳定状态

以下状态是稳定状态，可以作为失败回退点：

- `created`
- `imported`
- `modeled`
- `ready`
- `completed`
- `blocked`

以下状态是非稳定状态，只代表过程：

- `analyzing`
- `writing`
- `revising`

### 4.3 小说状态标准流转

标准初始化路径：

`created -> imported -> analyzing -> modeled -> ready`

标准写作路径：

`ready -> writing -> ready`

标准修订路径：

`ready -> revising -> ready`

完成路径：

`ready -> completed`

异常路径：

- `analyzing -> blocked`
- `writing -> blocked`
- `revising -> blocked`

### 4.4 小说状态驱动者

- 导入服务驱动：`created -> imported`
- 分析工作流驱动：`imported -> analyzing -> modeled`
- 就绪校验驱动：`modeled -> ready`
- 写作工作流驱动：`ready -> writing -> ready`
- 改写/修订工作流驱动：`ready -> revising -> ready`
- 用户确认或系统判断驱动：`ready -> completed`
- 关键失败规则驱动：`* -> blocked`

### 4.5 小说状态禁止规则

- `created` 不允许直接进入 `ready`
- `imported` 不允许直接进入 `writing`
- `modeled` 不允许直接进入 `writing`，必须先通过可写校验进入 `ready`
- `blocked` 不允许自动恢复到 `ready`，必须通过显式恢复动作或成功重跑关键任务

## 5. 章节状态

### 5.1 章节正式状态

- `empty`
  章节位已创建，但无有效内容。
- `imported`
  章节原文已导入。
- `analyzed`
  已完成章节分析与章节记忆提取。
- `planned`
  已完成章节计划，但尚未生成正文。
- `drafting`
  正在生成结构稿或正文。
- `draft`
  已生成草稿，但尚未通过校验或确认。
- `reviewing`
  正在做一致性校验或质量检查。
- `revising`
  正在根据问题单修订。
- `confirmed`
  章节正文已确认，可作为后续续写依据。
- `published`
  章节正式发布，不允许被自动覆盖。
- `archived`
  章节不再参与活跃写作链，但保留历史记录。

### 5.2 章节状态流转

典型路径：

`empty -> imported -> analyzed -> planned -> drafting -> draft -> reviewing -> confirmed -> published`

修订路径：

`draft -> reviewing -> revising -> draft`

历史归档路径：

`published -> archived`

### 5.3 章节状态约束

- `confirmed` 之后不得被自动覆盖，只能生成新版本
- `published` 之后不得被智能体直接改写
- `analyzed` 之前不应进入正式规划链
- `drafting`、`reviewing`、`revising` 属于非稳定状态

## 6. 任务状态

### 6.1 任务正式状态

- `pending`
  已创建，等待执行。
- `queued`
  已入队，等待调度。
- `running`
  正在执行。
- `paused`
  已暂停，可恢复。
- `cancelling`
  正在取消。
- `cancelled`
  已取消。
- `failed`
  执行失败。
- `degraded`
  主路径失败后，以降级策略完成。
- `success`
  成功完成。

### 6.2 任务状态规则

- 所有长任务必须至少支持 `pending / running / success / failed`
- 所有后台任务必须支持 `paused / cancelled`
- 只有允许降级的任务可以进入 `degraded`
- `failed` 不等于自动结束，必须记录是否可重试

### 6.3 任务状态补充字段

每个任务除了状态，还必须具备：

- `progress_total`
- `progress_current`
- `retry_count`
- `last_error`
- `resume_token`
- `degraded_reason`

## 7. 智能体运行状态

### 7.1 智能体正式状态

- `idle`
  当前没有活动运行。
- `loading_context`
  正在装配本次运行上下文。
- `reasoning`
  正在做理解、分析、判断。
- `dispatching`
  正在下发子任务或工作流。
- `waiting_task`
  正在等待异步任务完成。
- `validating`
  正在汇总校验结果。
- `blocked`
  因关键依赖缺失或失败而阻断。
- `completed`
  当前一次运行已完成。
- `failed`
  当前一次运行失败。

### 7.2 设计要求

- 智能体运行状态不等于小说状态
- 智能体状态反映的是“本次 agent run”，而不是小说长期生命周期
- 同一本小说可以在 `ready` 状态下多次进入 `reasoning -> dispatching -> completed`

## 8. 草稿状态

### 8.1 草稿正式状态

- `generated`
- `detemplated`
- `validated`
- `revision_requested`
- `finalized`
- `superseded`

### 8.2 草稿作用

草稿状态用于区分：

- 结构稿
- 去模板化稿
- 校验后可提交稿
- 被新稿替代的旧稿

草稿状态不直接驱动小说生命周期，但会影响章节状态和版本生效规则。

## 9. 状态转移驱动者

系统中的状态变化只能由以下四类驱动者触发：

1. 用户动作
2. 工作流步骤完成
3. 智能体决策
4. 系统规则引擎

### 9.1 用户动作可驱动

- 导入
- 启动分析
- 启动续写
- 确认章节
- 发布章节
- 锁定内容
- 恢复任务
- 取消任务

### 9.2 工作流可驱动

- 任务开始
- 任务成功
- 任务失败
- 任务暂停
- 任务恢复
- 任务降级完成

### 9.3 智能体可驱动

- 请求分析
- 请求规划
- 请求改写
- 请求修订

但智能体不得越过权限边界直接改变已锁定内容的最终状态。

## 10. 可逆与不可逆状态

### 10.1 可逆状态

- `analyzing`
- `writing`
- `revising`
- `pending`
- `queued`
- `paused`
- `draft`
- `reviewing`

这些状态失败后必须可回退到上一个稳定状态。

### 10.2 不可逆状态

- `completed`
- `published`

这两类状态不可被自动逆转，只能通过显式新版本机制覆盖，而不是直接状态倒退。

### 10.3 条件可逆状态

- `blocked`
- `failed`

它们不能被静默恢复，但可以通过“修复依赖 + 显式恢复任务”重新进入执行链。

## 11. 前端展示规则

前端不得直接根据原始任务状态拼 UI 文案，必须基于统一状态映射表展示。

### 11.1 概览页只关心

- 小说状态
- 当前活动任务
- 是否可写
- 是否被阻断

### 11.2 任务页关心

- 任务状态
- 进度
- 重试次数
- 最后错误
- 是否可恢复

### 11.3 写作页关心

- 小说是否为 `ready`
- 当前目标章节是否允许进入写作
- 当前是否存在未完成修订

## 12. 持久化要求

以下状态必须持久化：

- 小说状态
- 章节状态
- 任务状态
- 任务进度
- 最后错误
- 阻断原因

以下状态可以作为运行态缓存，但建议可恢复：

- 智能体本次运行状态
- 上下文装配中间态

## 13. 当前实现对照要求

当前仓库后续重构时，必须满足：

1. 小说状态不能再与整理进度文案混用
2. 章节状态不能只靠正文是否存在判断
3. 任务状态必须显式持久化，不能只留在内存
4. 智能体运行状态必须独立于工作流状态

## 14. 待补充内容

后续需要在 [20_state_machines.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/20_state_machines.md) 中进一步给出：

- 状态机转移图
- 非法转移表
- 各转移的驱动事件
- 各转移的恢复策略
