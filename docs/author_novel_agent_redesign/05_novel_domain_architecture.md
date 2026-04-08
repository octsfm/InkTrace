# 小说领域架构

## 1. 目标

小说领域架构用于定义 InkTrace 中与小说创作直接相关的正式领域对象、对象边界、对象关系与 ownership 规则。

它回答的不是“页面上展示什么”，也不是“某次任务怎么执行”，而是：

- 系统里到底有哪些正式小说对象
- 哪些是源数据，哪些是派生数据
- 哪些对象是核心资产，哪些只是运行结果
- 哪些对象之间构成聚合与引用关系

领域架构是整个作者智能体系统的事实底座。  
没有稳定的领域模型，后续的状态、版本、工作流、写作、校验都只能在漂浮概念上工作。

---

## 2. 设计原则

### 2.1 源数据与派生数据分离

小说原文、章节原文、大纲原文属于源数据。  
Story Model、PlotArc、MemoryView、章节分析、章节计划等属于结构化派生数据。

源数据不应被派生过程静默覆盖；派生数据应可重建。

### 2.2 核心资产与运行态分离

小说、章节、设定、PlotArc、正文版本属于核心资产。  
任务进度、临时上下文、模型摘要、临时候选稿属于运行态或中间态。

### 2.3 正式对象必须可命名、可引用、可版本化

只要某个对象会影响：

- 创作结果
- 结构理解
- 后续写作路径
- 用户信任

它就必须是正式领域对象，而不是随意塞在某个 JSON 结构里的临时字段。

### 2.4 作者作品资产优先

小说领域架构首先服务“作品资产”的长期稳定性，而不是服务模型调用方便。  
对象建模必须先站在“长期作品管理”的视角，而不是“单次 prompt 装配”的视角。

---

## 3. 领域对象分层

系统中的小说领域对象可以分为六层：

1. 作品源对象
2. 结构理解对象
3. 写作生产对象
4. 校验与修订对象
5. 视图与摘要对象
6. 运行与任务对象

其中 1 至 4 属于小说领域主干，5 是展示与辅助层，6 是运行支撑层。

---

## 4. 作品源对象

### 4.1 Novel

`Novel` 是小说项目的顶层聚合根，代表一部作品本体。

它至少包含：

- `novel_id`
- 标题、简介、作者侧元信息
- 小说生命周期状态
- 当前有效版本引用
- 所属项目与策略引用

`Novel` 不直接内嵌所有重型结构对象，而是维护对章节、Story Model、PlotArc、版本集合的关系。

### 4.2 Chapter

`Chapter` 是小说正文层的基本组织单位，是源文本与正式正文版本的承载体。

它至少包含：

- `chapter_id`
- `novel_id`
- 顺序号
- 标题
- 源正文
- 当前有效正文版本引用
- 当前状态

章节是领域主对象，不只是数据库行。  
章节上的分析、计划、草稿、问题单都应与 `Chapter` 明确关联。

### 4.3 Outline

`Outline` 是小说的大纲资产，可分为：

- 原始大纲
- 结构化大纲
- 章节级大纲

大纲对象不等同于 Story Model。  
大纲是创作意图资产，Story Model 是结构理解资产。

### 4.4 CharacterProfile

`CharacterProfile` 表示人物设定对象。

它至少应包括：

- 基础身份
- 关系角色
- 性格与行为约束
- 成长方向
- 当前状态摘要
- 是否被锁定的字段

人物对象属于核心资产，允许被结构分析更新，但关键字段允许作者锁定。

### 4.5 WorldRule

`WorldRule` 表示世界观与规则对象。

它可涵盖：

- 力量体系
- 社会秩序
- 地理/势力结构
- 禁忌与规则
- 已确认世界设定

这类对象通常变化较慢，但一旦被违反，会直接造成“设定飞掉”。

---

## 5. 结构理解对象

### 5.1 StoryModel

`StoryModel` 是系统对一部小说整体结构理解的正式对象。

它不是某一次 prompt 的输出原文，而是可被系统长期消费的结构化故事模型。

Story Model 至少应包含：

- 主线与支线
- 人物图谱
- 世界设定摘要
- 当前阶段与推进状态
- 核心冲突
- 未完成目标与悬念
- 风格画像
- 风险点

Story Model 是“系统理解小说”的中心对象。

### 5.2 PlotArc

`PlotArc` 是正式中层叙事推进对象，属于 Story Model 的关键组成，但应作为独立领域对象存在。

PlotArc 不是章节摘要，也不是大纲复制。  
它承担“叙事推进单位”的角色，并直接驱动：

- 续写规划
- 写作目标选择
- 长线一致性校验

### 5.3 ChapterAnalysisMemory

`ChapterAnalysisMemory` 是系统对单章结构理解的正式结果对象。

它用于表达：

- 本章摘要
- 本章冲突
- 本章功能
- 本章角色推进
- 本章结构标签

### 5.4 ChapterContinuationMemory

`ChapterContinuationMemory` 是系统为后续续写准备的续写记忆对象。

它表达的是：

- 本章遗留推进点
- 必续要素
- 角色状态延续
- 下一章连接点

### 5.5 ChapterOutline

`ChapterOutline` 是章节级计划或结构意图对象。  
它既可能来自导入整理，也可能来自智能体规划。

它与 `ChapterPlan` 不完全相同：

- `ChapterOutline` 偏结构与摘要
- `ChapterPlan` 偏执行层的写作计划

---

## 6. 写作生产对象

### 6.1 ChapterPlan

`ChapterPlan` 是一次写作任务的正式计划对象，描述：

- 本章目标
- 目标 PlotArc
- 章节功能
- 关键情节点
- 风格约束
- 禁止事项

### 6.2 StructuralDraft

`StructuralDraft` 是 DeepSeek 按计划生成的结构稿。  
它强调“事件与结构已成形”，不要求语言已达到终稿标准。

### 6.3 RewriteDraft

`RewriteDraft` 是改写类结果的正式对象，包括：

- 去模板化稿
- 风格改写稿
- 扩写稿
- 压缩稿
- 目标化重写稿

### 6.4 RevisionDraft

`RevisionDraft` 是根据问题单生成的修订稿。  
它强调“对已知问题进行针对性修复”，而不是自由改写。

### 6.5 FinalDraft

`FinalDraft` 是通过写作与修订链后，达到可确认标准的候选终稿对象。

它仍然可能未正式生效，但已经是最接近正式正文的候选版本。

### 6.6 ChapterContentVersion

`ChapterContentVersion` 是章节正式正文版本对象，用于保存：

- 原始正文版本
- 作者手工修改版本
- AI 生成生效版本
- 发布版本

它是章节正文版本系统的主对象。

---

## 7. 校验与修订对象

### 7.1 ValidationIssue

`ValidationIssue` 是一致性与质量问题单对象。

它不是一段自由文本，而是正式结构化对象，应至少包含：

- 问题类型
- 严重等级
- 目标对象
- 证据
- 修复建议
- 是否阻断

### 7.2 ValidationReport

`ValidationReport` 表示某次校验的整体结果对象。

它可以包含：

- issue 列表
- 总体结论
- 可信度
- 是否允许进入下一阶段

### 7.3 RevisionInstruction

`RevisionInstruction` 是从问题单转换而来的修订指令对象，供 DeepSeek 修订时使用。

---

## 8. 视图与摘要对象

### 8.1 MemoryView

`MemoryView` 是面向前端和作者的轻量结构视图对象。

它可以来自 Story Model、PlotArc、章节记忆等正式对象的汇总，但它自身不是唯一事实来源。

### 8.2 AssistantSuggestion

`AssistantSuggestion` 是智能体面向作者输出的建议对象，例如：

- 下一步推荐动作
- 推荐推进哪条弧
- 推荐使用的规划模式
- 推荐原因

### 8.3 OverviewSnapshot

`OverviewSnapshot` 是概览页使用的聚合摘要对象，例如：

- 当前状态
- 最近进度
- 最近整理时间
- 当前活跃弧摘要

这类对象属于可重建派生视图。

---

## 9. 运行与任务对象

### 9.1 Task

`Task` 是系统执行单元，用于驱动分析、写作、改写、校验等行为。

### 9.2 WorkflowRun

`WorkflowRun` 是一条完整工作流的运行实例对象。

### 9.3 AgentRun

`AgentRun` 是一次智能体决策与调度运行实例对象。

### 9.4 ModelCallRecord

`ModelCallRecord` 是一次模型调用的可回溯记录对象。

这些对象支撑系统运行，但不属于小说作品资产本体。

---

## 10. 聚合关系建议

### 10.1 Novel 作为顶层聚合根

`Novel` 应作为作品顶层聚合根，聚合：

- 章节集合
- 大纲集合
- Story Model 版本集合
- PlotArc 集合
- 当前策略引用

### 10.2 Chapter 作为局部聚合根

`Chapter` 可作为章节局部聚合根，聚合：

- 章节分析记忆
- 续写记忆
- 章节计划
- 草稿集合
- 正文版本集合
- 问题单集合

### 10.3 StoryModel 与 PlotArc 的关系

Story Model 是全局结构理解对象。  
PlotArc 是 Story Model 中最重要、且需要独立管理的中层推进对象。

两者不是父子内嵌 JSON 的轻量关系，而应是：

- 逻辑上从属
- 存储上可独立版本化
- 使用上可分别消费

---

## 11. Ownership 规则

领域对象需要明确 ownership：

- 小说、章节、正文版本的最终 ownership 属于作者
- Story Model、PlotArc、章节分析、问题单等结构对象由系统维护，但允许作者修正或锁定关键部分
- 派生视图由系统负责重建，不属于核心 ownership 决策对象

换句话说：

- 作者拥有作品
- 系统维护理解层
- 智能体在授权范围内生成候选内容

---

## 12. 不变量

领域架构必须明确以下核心不变量：

1. 源正文不被分析流程静默覆盖  
2. 已确认正文必须通过版本系统修改  
3. PlotArc 必须绑定到章节或章节区间，不允许完全游离  
4. Story Model 必须可回溯到章节工件，而不是只保留最终摘要  
5. MemoryView 不是事实源，只是展示视图  
6. 问题单必须关联到明确目标对象  

---

## 13. 当前重构落地要求

在当前重构中，至少需要明确落地以下正式领域对象：

- Novel
- Chapter
- Outline
- CharacterProfile
- WorldRule
- StoryModel
- PlotArc
- ChapterAnalysisMemory
- ChapterContinuationMemory
- ChapterPlan
- StructuralDraft
- RewriteDraft
- FinalDraft
- ChapterContentVersion
- ValidationIssue
- MemoryView

---

## 14. 与其他文档的关系

- [PlotArc 架构](./06_plot_arc_architecture.md) 细化 PlotArc 对象本身
- [版本架构](./13_version_architecture.md) 定义对象版本规则
- [存储架构](./14_storage_architecture.md) 定义对象的持久化形态
- [状态架构](./04_state_architecture.md) 定义对象在生命周期中的状态变化
- [术语表](./19_glossary.md) 提供术语统一口径

---

## 15. 待解决问题

1. CharacterProfile 与 Story Model 中人物状态摘要的边界如何划分  
2. ChapterOutline 与 ChapterPlan 是否需要完全分离为两个正式对象  
3. Story Model 是否应拆成“结构事实层”和“解释层”两部分  
4. 小说导入为短篇或无章节文本时，Chapter 对象是否允许退化为单章结构  
