# 术语表

## 1. 目的

本术语表用于统一 InkTrace 重构设计中的核心概念，避免同一个词在不同文档、代码模块、页面文案和模型 prompt 中具有不同含义。

只要某个术语会影响：

- 代码结构
- 数据模型
- 状态语义
- 页面语义
- 工作流决策

就必须以本术语表为准。

---

## 2. 术语定义规则

每个术语的定义至少包含：

- 正式含义
- 不包含什么
- 在系统中的主要作用

如果某个术语与历史实现中的旧含义冲突，以本术语表为准。

---

## 3. 核心术语

### 3.1 AuthorAgent

`AuthorAgent` 是 InkTrace 的统一作者智能体入口。

它是决策与调度主体，不是第三个写作模型。  
它负责理解作者意图、判断当前小说状态、选择合适工作流、协调 Kimi 和 DeepSeek，并对任务结果进行组织与回写。

AuthorAgent 不直接负责生成最终正文，而是负责“让正确的能力在正确的时机被调用”。

### 3.2 StoryModel

`StoryModel` 是系统对一部小说当前整体结构理解的正式对象。

它包含：

- 主线与支线
- 人物图谱
- 世界设定摘要
- 当前推进状态
- 风格画像
- 风险点

Story Model 不是大纲原文，也不是某次分析 prompt 的原始输出全文。

### 3.3 PlotArc

`PlotArc` 是正式中层叙事推进单位。

它表达一条持续推进的叙事目标、冲突或关系演进线，并承担规划和校验中的中层结构角色。

PlotArc 不是章节摘要，不是大纲复制，也不是单次事件标签。

### 3.4 ChapterAnalysisMemory

`ChapterAnalysisMemory` 是对单章结构理解的正式分析对象。

它通常包含：

- 本章摘要
- 本章功能
- 冲突
- 角色推进
- 结构标签

### 3.5 ContinuationMemory

`ContinuationMemory` 指代用于后续续写的续写记忆对象。  
在当前文档体系中，正式对象名称为 `ChapterContinuationMemory`。

它表达：

- 本章遗留推进点
- 下一章承接点
- 必续要素
- 状态延续线索

### 3.6 MemoryView

`MemoryView` 是面向前端或作者展示的轻量结构视图对象。

它来自 Story Model、PlotArc、章节记忆等对象的汇总，但不是系统唯一事实来源。

### 3.7 ChapterPlan

`ChapterPlan` 是面向写作执行的章节计划对象。

它描述：

- 本章目标
- 目标 PlotArc
- 章节功能
- 情节点
- 风格与禁止事项

ChapterPlan 偏执行层，不等同于 `ChapterOutline`。

### 3.8 ChapterOutline

`ChapterOutline` 是章节结构或章节摘要层的大纲对象。

它可来自导入整理或章节分析。  
相比 `ChapterPlan`，它更偏结构描述而非执行指令。

### 3.9 StructuralDraft

`StructuralDraft` 是正文生成链中的结构稿。

它强调事件、节奏和章节结构已经成形，但语言可能尚未达到最终质量。

### 3.10 RewriteDraft

`RewriteDraft` 是改写任务产出的候选稿对象。

它可以是：

- 去模板化稿
- 风格改写稿
- 扩写稿
- 压缩稿

RewriteDraft 不是修订稿。

### 3.11 RevisionDraft

`RevisionDraft` 是根据问题单进行针对性修复后的修订稿。

它强调“按 issue 修”，而不是自由重写。

### 3.12 FinalDraft

`FinalDraft` 是通过写作、改写、修订与校验后，达到可确认标准的候选终稿。

它可能尚未正式生效，但已经是最接近正式正文的版本。

### 3.13 ValidationIssue

`ValidationIssue` 是结构化质量问题单对象。

它至少应包含：

- 问题类型
- 严重级别
- 目标对象
- 证据
- 修复建议
- 是否阻断

ValidationIssue 不是一段普通错误提示。

### 3.14 ValidationReport

`ValidationReport` 是某次校验任务的整体结果对象。

它包含 issue 列表、总体结论、可信度与是否允许进入下一阶段的判断。

### 3.15 Task

`Task` 是系统中的最小执行单元，用于驱动：

- 分析
- 规划
- 写作
- 改写
- 校验
- 修订

Task 不是页面动作，也不是模型调用本身。

### 3.16 Workflow

`Workflow` 是由多个任务按顺序或条件编排而成的正式流程。

例如：

- 导入工作流
- 重整工作流
- 写作工作流
- 改写工作流
- 校验修订工作流

### 3.17 WorkflowRun

`WorkflowRun` 是某次工作流执行实例。

它用于表示“这一条工作流本次怎么跑、跑到哪、结果如何”。

### 3.18 AgentRun

`AgentRun` 是某次智能体决策与调度运行实例。

它记录的是智能体一次完整决策链，而不是单步模型调用。

### 3.19 EffectiveVersion

`EffectiveVersion` 是当前对系统或作者来说“生效中”的版本。

生效版本不一定是最新创建版本，但必须是当前被系统消费或展示的版本。

### 3.20 PublishedVersion

`PublishedVersion` 是已被作者确认并视为正式对外或正式采用的稳定版本。

发布版本通常具有更高保护级别，不应被原地覆盖。

### 3.21 CandidateVersion

`CandidateVersion` 是尚未正式生效、等待审阅或确认的候选版本。

智能体产出的多数结果，默认应先进入候选版本。

### 3.22 LockedContent

`LockedContent` 是被作者或系统规则明确标记为不可自动修改的内容。

它可能是：

- 某个设定字段
- 某条 PlotArc 目标
- 某章正式正文
- 某个已发布版本

### 3.23 Ready State

`Ready` 是小说生命周期中的稳定可写作状态。

它表示：

- 小说已完成基本建模
- 当前结构结果足够支持续写或改写
- 允许进入写作链

Ready 不是“所有结构都完美”的意思，而是“具备进入写作行为的最低稳定条件”。

### 3.24 Strict Mode

`Strict Mode` 指关键任务中禁止低质量降级结果直接生效的运行模式。

典型用于：

- 全书分析
- PlotArc 抽取
- 一致性校验

### 3.25 Degraded Mode

`Degraded Mode` 指在允许范围内进行有限同职责降级的运行模式。

它不允许跨职责降级，例如：

- 分析任务不能降级到 DeepSeek
- 写作任务不能降级到 Kimi

### 3.26 Context Builder

`Context Builder` 是负责为某次模型调用装配执行上下文的模块或规则集合。

它决定：

- 取哪些对象
- 取多少
- token 不够时舍弃什么

### 3.27 Policy Profile

`Policy Profile` 是一组高层策略配置的正式档案。

它可定义：

- 写作档位
- 改写档位
- 校验档位
- 规划模式偏好
- 上下文预算策略

---

## 4. 禁止混用的概念

以下术语不能混用：

- `Outline` 与 `StoryModel`
- `ChapterOutline` 与 `ChapterPlan`
- `RewriteDraft` 与 `RevisionDraft`
- `MemoryView` 与事实层结构对象
- `Task` 与 `Workflow`
- `EffectiveVersion` 与 `PublishedVersion`
- `PlotArc` 与章节摘要

如果后续代码或页面中出现混用，应以本术语表为准进行重构。

---

## 5. 当前重构的术语统一要求

当前重构阶段，至少应统一以下命名口径：

- 使用 `AuthorAgent`，不再用模糊的“智能体流程”代指全部逻辑
- 使用 `StoryModel` 指代系统整体故事理解对象
- 使用 `PlotArc` 指代正式中层推进弧
- 使用 `ChapterPlan` 指代写作执行计划
- 使用 `ValidationIssue` 指代结构化问题单
- 使用 `EffectiveVersion / PublishedVersion / CandidateVersion` 表达版本关系

---

## 6. 待补充术语

后续可继续补充：

- CharacterProfile
- WorldRule
- ChapterContentVersion
- AssistantSuggestion
- OverviewSnapshot
- RevisionInstruction
- Trace
- ModelCallRecord
