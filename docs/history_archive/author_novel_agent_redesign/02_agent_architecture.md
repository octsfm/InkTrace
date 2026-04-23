# 智能体架构

## 1. 文档目标

智能体架构用于定义真正的作者智能体 `AuthorAgent` 应该是什么、负责什么、不负责什么，以及它如何与工作流、任务、记忆、模型和前端协作。

当前系统的主链更接近 workflow orchestration，而不是完整作者智能体。  
这份文档的作用，就是把“智能体”从口号落到正式架构层。

## 2. 当前代码现状判断

### 2.1 现状结论

目前代码库中的 `application/agent_mvp/` 目录，代表的是：

**MVP 阶段的脚本执行器，而不是蓝图里那个能长期协作、能自主判断、能挂起恢复的作者智能体。**

### 2.2 现状依据

重点体现在：

- [orchestrator.py](/D:/Work/InkTrace/ink-trace/application/agent_mvp/orchestrator.py)
- [tools.py](/D:/Work/InkTrace/ink-trace/application/agent_mvp/tools.py)

其中：

1. `AgentOrchestrator` 当前既负责决策，也直接串工具执行。
2. `_plan_next_action()` 仍然是写死的流程逻辑，本质上是：
   - 先 `RAGSearchTool`
   - 再 `WritingGenerateTool`
3. 工具层内部仍然承载大量模型调用、恢复、降级和 fallback 逻辑。
4. Agent 当前输入上下文非常薄，只接近“goal 驱动的执行器”，不像“长期理解作品的编辑合伙人”。

因此，当前 `agent_mvp` 的定位应被明确为：

**过渡期 MVP 能力层，而不是最终 AuthorAgent 的正式实现。**

## 3. 智能体的正式定义

`AuthorAgent` 不是单次请求封装，也不是多个按钮背后的服务拼装。

它是一个持续工作的决策层，负责：

- 理解小说当前状态
- 理解作者当前意图
- 判断当前是否满足执行条件
- 决定接下来该做什么
- 选择要触发哪个 workflow
- 汇总结果并向作者解释

一句话：

> AuthorAgent 负责组织创作闭环，而不是亲自完成所有文本生成。

## 4. 智能体职责边界

### 4.1 智能体负责

- 意图理解
- 状态判断
- 条件检查
- 工作流选择
- 任务触发
- 风险阻断
- 结果解释
- 下一步建议

### 4.2 智能体不负责

- 直接写正文
- 直接调用底层写作工具生成最终文本
- 直接替代数据库写入服务
- 越过权限和锁定规则修改内容
- 把 workflow 内部步骤暴露为用户必须理解的概念

### 4.3 模型职责仍然保持双模型分工

- `Kimi`：理解、分析、规划、控制、校验
- `DeepSeek`：写作、续写、改写、润色

智能体本身不是第三个写作模型，而是：

**决策与调度层。**

## 5. 核心架构原则

后续正式智能体架构必须严格遵守一句话：

**Agent decides, workflows execute, tasks persist, models produce.**

拆开就是：

- Agent 决定现在该做什么
- Workflow 负责这件事怎么执行
- Task 负责持久化、暂停、恢复和追踪
- Model 只负责输出分析或文本

## 6. 角色剥离：让 Agent 只做大脑，把手脚交给 Workflow

### 6.1 当前问题

现在的 [orchestrator.py](/D:/Work/InkTrace/ink-trace/application/agent_mvp/orchestrator.py) 既当裁判又当运动员。

它内部已经写死了“先调 RAG，再调 Writing”的流水线，这说明：

- Agent 在自己写 workflow
- Tool 在自己做恢复和降级
- 决策层、执行层、模型层还没有分开

### 6.2 目标架构

正式形态应改成：

- Agent 只接收作者意图和当前状态
- Agent 判断当前目标和前置条件
- Agent 决定要触发哪个 workflow
- Workflow 再去执行分析、规划、写作、校验等步骤

例如：

作者说：“帮我推进一下剧情。”

Agent 不应该直接去调写作工具。  
它应该：

1. 查看当前 StoryModel
2. 查看当前 PlotArc
3. 判断当前弧是否适合推进
4. 得出决策：“当前高潮弧铺垫不够，先触发【铺垫改写 workflow】”

## 7. 引入 AgentContextBuilder

### 7.1 当前问题

当前 Agent 运行只依赖非常轻的上下文，更像无记忆问答机器人。

### 7.2 目标架构

必须在 Agent 启动前引入独立的 `AgentContextBuilder`，由它装配完整决策上下文。

### 7.3 至少需要装配的内容

- 当前小说的主线推进状态
- 当前 active PlotArc
- 当前焦点角色状态
- 当前章节和最近章节摘要
- 当前 StoryModel
- 当前未解决 issue
- 当前锁定规则
- 当前自治模式 `autonomy_mode`
- 当前生效版本信息

### 7.4 作用

没有 `AgentContextBuilder`，Agent 就无法成为真正的“小说编辑合伙人”，只能继续停留在“拿到一句 goal 就执行”的阶段。

## 8. 引入 IntentClassifier 与 ConditionGatekeeper

### 8.1 当前问题

如果用户输入直接透传到底层工具，系统就会退化成“自然语言按钮面板”。

### 8.2 目标架构

Agent 的第一步必须先做：

1. 意图分类 `IntentClassifier`
2. 条件检查 `ConditionGatekeeper`

### 8.3 意图分类

至少分类为四类：

- 分析
- 续写
- 改写
- 辅助

### 8.4 状态守门

分类后必须经过状态守门员检查，例如：

- 小说是否处于 `ready`
- 是否存在阻断 issue
- 是否缺少关键 StoryModel
- 是否触碰锁定规则
- 是否允许当前章节被改写

### 8.5 典型例子

如果用户说：“帮我写大结局。”  
但系统发现：

- 关键坑没填
- 存在阻断 issue
- 大结局被锁定

那么 Agent 应该：

- 驳回直接执行
- 或给出修复建议

而不是无脑生成。

## 9. 引入自治模式与挂起/恢复机制

### 9.1 当前问题

当前 `agent_mvp` 本质上还是一波流执行器，中途无法真正挂起、等待、恢复。

### 9.2 目标架构

在 Agent 上下文中引入 `autonomy_mode`。

建议至少三档：

#### `assist_only`

- 只给建议
- 不自动触发 workflow

#### `guided_execute`

- Agent 先生成执行计划
- 将计划投递给前端 Copilot / Inspire
- 等待用户确认后执行

#### `auto_run`

- Agent 直接向任务 / 事件系统投递 workflow
- 自己进入监听状态
- 等待任务结果、问题单或失败信息返回

### 9.3 额外状态

除了 `suspend / resume`，还建议明确：

- `awaiting_user_confirmation`
- `blocked`

因为很多真实场景不是简单暂停，而是：

- 缺用户确认
- 缺前置条件
- 触发锁定规则冲突

## 10. 输出重构：从“给文本”变成“给决策单”

### 10.1 当前问题

当前 [orchestrator.py](/D:/Work/InkTrace/ink-trace/application/agent_mvp/orchestrator.py) 的 `run()` 更像返回执行结果，而不是智能体结果。

### 10.2 目标架构

Agent 的 `run()` 不应直接返回正文。  
它应返回结构化 `AgentResponse`。

### 10.3 建议的 AgentResponse

至少包括：

- `decision`
- `explanation`
- `workflow_request`
- `required_actions`
- `blocking_issues`
- `confidence`
- `autonomy_mode`
- `suspend_reason`

### 10.4 字段含义

#### `decision`

决定做什么，例如：

- 触发哪个 workflow
- 先阻断
- 先修复
- 先分析

#### `explanation`

给前端 Copilot 的解释文案，例如：

“因为反派动机不足，我建议先补一段背景铺垫，再推进高潮弧。”

#### `workflow_request`

正式交给 workflow 层的执行请求。

#### `required_actions`

要求前端进行的 UI 变化，例如：

- 高亮正文某段
- 展示确认面板
- 打开 diff 视图

#### `blocking_issues`

当前阻止继续执行的条件列表。

## 11. 智能体运行阶段

一个标准 Agent Run 至少分为：

1. 装配上下文
2. 理解意图
3. 检查条件
4. 选择 workflow
5. 投递任务
6. 监听结果
7. 输出决策单

### 11.1 装配上下文

通过 `AgentContextBuilder` 拉取：

- StoryModel
- PlotArc
- 锁定规则
- 当前版本
- 当前 issue

### 11.2 理解意图

通过 `IntentClassifier` 判断作者要做什么。

### 11.3 检查条件

通过 `ConditionGatekeeper` 判断能不能做。

### 11.4 选择 workflow

智能体决定：

- 应走哪类 workflow
- 是否允许执行
- 是否要进入挂起 / 等待确认

### 11.5 投递任务

由智能体触发 workflow / task，而不是页面直接拼接口。

### 11.6 监听结果

等待：

- 成功结果
- 问题单
- 失败原因
- 恢复建议

### 11.7 输出决策单

最终向前端或上层系统返回结构化结果。

## 12. 智能体与工作流关系

智能体与工作流的关系必须严格分层：

- 智能体负责判断和调度
- 工作流负责执行
- 任务负责持久化
- 模型负责分析或生成

如果 Agent 自己继续把 workflow 写死在 orchestrator 里，那么它就仍然只是脚本执行器。

## 13. 智能体与记忆关系

智能体不直接承担长期记忆存储，但必须能够稳定读写记忆链路。

### 13.1 智能体读取

- Story Memory
- Chapter Memory
- Continuation Memory
- 当前版本
- 锁定规则

### 13.2 智能体写回

智能体本身不直接写 raw memory。  
写回应通过 workflow / writeback service 完成，例如：

- 分析结果写回
- PlotArc 写回
- 问题单写回

## 14. 智能体与权限边界

智能体必须服从以下规则：

- 不得主动修改已锁定人物设定
- 不得主动覆盖已确认章节
- 不得绕过发布与确认机制
- 不得在低可信分析结果上直接启动写作

## 15. 当前重构要求

后续重构必须满足：

1. 建立统一智能体入口
2. 页面不再直接等价于模型调用
3. 智能体必须基于状态、版本、上下文、锁定规则做判断
4. 智能体不越权
5. 智能体输出必须是“决策单”，而不是直接正文
6. `application/agent_mvp/` 明确视为过渡层，不再被误解为最终 AuthorAgent

## 16. 与其他文档的依赖

本架构强依赖：

- [03_workflow_architecture.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/03_workflow_architecture.md)
- [04_state_architecture.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/04_state_architecture.md)
- [08_execution_context_architecture.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/08_execution_context_architecture.md)
- [17_permission_and_control_boundary_architecture.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/17_permission_and_control_boundary_architecture.md)

## 17. 后续待细化内容

后续还需要继续细化：

- `AuthorAgentService` 接口契约
- `AgentContextBuilder` 契约
- `IntentClassifier` 契约
- `ConditionGatekeeper` 契约
- `AgentResponse` 数据结构
- `guided_execute / auto_run` 的挂起与恢复规则
