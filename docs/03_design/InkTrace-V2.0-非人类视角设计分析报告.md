# InkTrace V2.0 全量设计文档「非人类视角」分析报告

版本：v1.0
日期：2026-05-27
遍历范围：V2.0 全部设计文档（P0 11篇 + P1 11篇 + 需求1篇 + 概要1篇 + 架构1篇 + DESIGN 1篇 + 计划5篇 + 验收5篇），共 35+ 篇文档

---

## 一、问题总览

整个 V2.0 设计体系存在一个系统性的视角偏差：**设计以「五 Agent 安全协作系统」为主线，而非以「作者完成一章写作」为主线。** Agent 编排、状态机、门控管道是手段，帮助作者写作才是目的——但在所有设计中，手段成为了组织核心。

以下按 12 个维度展开。

---

## 二、十二大系统性偏差

### 偏差 1：技术术语污染了产品语言

| 技术术语 | 出现位置 | 作者应该看到的 |
|---|---|---|
| **ContextPack** | P0-06 全文, P0 总纲, P1-UI AI Tab, API 路由 | "写作上下文" / "AI 理解的故事背景" |
| **AgentSession** | P1-01 §5, P1-UI AI Tab, P1-11 API | "AI 写作任务" / "这次写作会话" |
| **PPAO** | P1-01 §4 全文, 总纲 §4.11, 概要设计 §5 | 作者不需要知道 AI 内部是"感知→规划→行动→观察"循环 |
| **blocked / degraded** | P0-06 §5, P0 总纲, 贯穿 P0/P1 全部文档 | "无法续写" / "部分信息缺失，但仍可尝试" |
| **stale / superseded** | P0-04, P0-09, P1-04, P1-06, 贯穿全部 | "可能已过期" / "已有新版本" |
| **side_effect_level** | P0-07 §5.3, P1-01 §8.4, P1-03 §3.5 | 纯内部权限概念，作者不应看到 |
| **caller_type** | P0-07 §6.2, P0-11 §7.1, P1-01 §8.4, P1-02 §8.4 | "谁发起的操作"的工程分类 |
| **idempotency_key** | P0-11 §8.2, P0-07 §8.1, P1-11 §6 | 防止重复提交的工程机制 |
| **formal_write / formal_write_forbidden** | P0-07, P1-01 §12.4, P1-03 §3.5 | 内部安全分级 |
| **safe_ref / content_ref / content_hash** | P1-01 §8.5, P1-10 §4.3 | 内部引用协议 |
| **model_role** (12个角色) | P0-01 §3.2, P0 总纲 §2.3 | 内部模型路由配置 |
| **placeholder** | P1-04 §10.2 | 数据库最小记录模式 |
| **ignored_late_result** | P1-01 §6.8, P1-06 §9.3 | 异步分布式系统的竞态条件处理 |
| **partial_success** | P1-01 §9.5, P1-02 §10 | 分布式事务的部分成功语义 |
| **progress_pct: 55** | P1-04 §3.2 | 作者不会用"进度百分比"描述故事阶段 |

**统计**: 至少 **35+ 个技术术语**直接出现在设计文档的核心概念、数据模型字段、API 路由中。其中仅 P1-UI §11.1 的"用户文案映射表"做了有限的翻译（将 Provider 映射为"模型服务"、ContextPack 映射为"写作上下文"），但翻译工作远未覆盖全局。

---

### 偏差 2：状态机泛滥——用系统生命周期替代作者认知模型

整个 V2.0 设计中定义了 **超过 15 个独立状态机**，总计 **超过 80 个状态值**：

| 实体 | 状态枚举 | 状态数 | 来源 |
|---|---|---|---|
| initialization_status | not_started / outline_analyzing / outline_completed / manuscript_analyzing / memory_building / state_building / vector_indexing / completed / failed / paused / cancelled / stale | **11** | P0-03 |
| AIJob | queued / running / paused / failed / cancelled / completed | **6** | P0-02 |
| AIJobStep | pending / running / paused / failed / skipped / completed | **6** | P0-02 |
| AgentSession | pending / running / waiting_for_user / paused / cancelling / cancelled / failed / completed / partial_success | **9** | P1-01 |
| AgentStep | pending / running / waiting_observation / waiting_user / succeeded / failed / skipped / cancelled / ignored_late_result | **9** | P1-01 |
| CandidateDraftStatus | pending_review / accepted / rejected / applied / stale / superseded | **6** | P0-09 |
| CandidateDraftVersion | generated / reviewing / review_completed / revision_requested / selected / accepted / rejected / applied / superseded / stale / failed | **11** | P1-06 |
| DirectionProposal | pending / generated / waiting_for_selection / selected / edited / stale / superseded / failed | **8** | P1-05 |
| ChapterPlan | pending / generated / waiting_for_confirmation / confirmed / edited / stale / superseded / failed | **8** | P1-05 |
| AIReviewStatus | completed / completed_with_warnings / failed / skipped / blocked | **5** | P0-10 |
| ArcStatus (x4层) | pending / ready / degraded / stale / failed / empty | **6×4** | P1-04 |
| MemoryUpdateSuggestion | (约10个状态) | **~10** | P1-09 |
| MemoryReviewGate | open / waiting_for_user / partially_approved / approved / rejected / applied / cancelled / failed | **8** | P1-09 |
| index_status (VectorRecall) | not_built / building / ready / degraded / stale / failed | **6** | P0-05 |
| AISuggestion | pending / accepted / rejected / edited / expired | **5** | P1-07 |

**核心问题**：这些状态机彼此之间存在联动传播关系（如 StoryMemory stale → Master Arc stale → Volume Arc stale → Sequence Arc stale），构成了一个复杂的状态依赖网络。作者不需要理解 80+ 个状态值的区别——作者只需要知道"AI 在帮我写吗？""写好了吗？""能看吗？"

---

### 偏差 3：门控管道将作者嵌入为系统流程中的决策节点

整个工作流设计了 **4 个独立用户确认门**，作者被当作 Pipeline 中的"human-in-the-loop 决策节点"：

```
DirectionSelection → PlanConfirmation → HumanReviewGate → MemoryReviewGate
```

**问题表现**:
- P1-02 §9.1：四个门控被严格定义为"语义隔离"、"业务对象不同"、"概念分离"
- P1-02 §13.2：规定了严格串行顺序——先 Conflict Guard，再 HumanReviewGate，再 MemoryReviewGate
- 一次"帮我写下一章"可能触发 **4 次等待确认**
- 没有任何"我相信 AI，一键到底"的快捷路径
- 设计出发点是系统安全正确性，而非作者操作效率

**作者视角应有的设计**: "我想让 AI 帮我写下一章" → AI 生成候选稿 → 我看一眼 → 决定用不用。中间的方向选择、计划确认、记忆更新确认应该是**可选、可跳过、可合并**的。

---

### 偏差 4：模型角色 (model_role) 12 路拆分——AI 分工成为用户负担

**位置**: P0-01 §3.2, P0 总纲 §2.3

系统将 AI 能力划分为 12 个 `model_role`：
```
outline_analyzer / manuscript_analyzer / memory_extractor / planner 
/ writing_task_builder / reviewer / writer / rewriter / polisher 
/ dialogue_writer / scene_generator / quick_trial_writer
```

这 12 个角色需要用户分别理解并配置 Provider 和模型。作者只关心两个问题：
1. "谁来帮我理解故事？"（分析模型）
2. "谁来帮我写？"（写作模型）

P1-11 §4.5 的 AI Settings 设计意识到了这个问题，做了"作者主路径"（仅暴露分析模型 Key + 写作模型 Key）和"高级折叠路径"（完整 5 role 配置）的区分。但这仍然说明**底层设计是以 5-12 个 role 为粒度**，上层 UI 做了一层翻译和折叠。

---

### 偏差 5：四层剧情轨道是 AI 约束系统，不是作者大纲工具

**位置**: P1-04 全文

P1-04 §2.4 自己承认了这一点：
> "四层剧情轨道不是故事大纲的另一种写法，而是结构化的叙事约束层"

这是一个**给 AI Agent 的约束系统**：
- 用于限制 Writer Agent 不偏离主线（arc_deviation 检测）
- 用于给 Planner Agent 提供方向推演依据
- 进入 ContextPack 作为最高优先级约束层
- 有 Token 裁剪优先级的严格排序

但在 UI 层面（P1-UI §7.4），它被放在"大纲 Tab"中展示给作者。作者看到的是一套系统内部的约束数据结构，而非自然的创作大纲。

特别是 `Immediate Window`（临近窗口）这个命名——这是滑动窗口算法的计算机术语，与叙事创作无关。

---

### 偏差 6：ToolFacade 将内部函数调用抽象暴露为"工具"

**位置**: P0-07 全文

整个 ToolFacade 概念（Tool Registry、ToolDefinition、ToolExecutionContext、permission_result 枚举、ToolAuditLog）是将内部 Service 方法调用包装为"Agent 可调用的工具"的门面模式。

- 30+ 个 Tool 名称（`get_story_memory_snapshot`、`create_candidate_draft`、`call_writer_model` 等）本质上是内部方法名的包装
- 5×30 的权限矩阵（5 个 Agent × 30 个 Tool × allow/deny/conditional）是 IAM 访问控制设计
- `caller_type` 的四值区分（user_action / agent / workflow_compat / system_maintenance）是系统内部调用来源分类

作者不需要知道 AI 是通过"调用名为 `call_writer_model` 的工具"来生成文本的。

---

### 偏差 7：错误码体系暴露了内部实现细节

贯穿 P0-11、P1-01、P1-11 等多个文档，**累计定义了 100+ 个错误码**：

| 错误码示例 | 暴露的内部概念 |
|---|---|
| `provider_timeout` / `provider_rate_limited` | Provider 层故障类型 |
| `tool_permission_denied` / `formal_write_forbidden` | ToolFacade 权限校验 |
| `output_validation_failed` | JSON Schema 校验 |
| `idempotency_conflict` | 幂等性机制 |
| `candidate_already_applied` | 状态机约束 |
| `review_context_token_budget_exceeded` | Token 预算管理 |

作者看到 `provider_rate_limited` 不会理解含义——应该翻译为"AI 服务繁忙，请稍后重试"。

---

### 偏差 8：数据模型字段渗透了系统追踪和审计概念

几乎所有核心实体的数据模型都包含了以下纯工程字段：

| 工程字段 | 出现位置 | 实际用途 |
|---|---|---|
| `request_id` / `trace_id` | 所有实体 | 分布式链路追踪 |
| `source_job_id` / `source_analysis_version` | P0-04 StoryMemory | 数据血缘追踪 |
| `version`（乐观锁版本号） | P0-09, P1-04, P1-09 | 并发控制 |
| `idempotency_key` | P0-07, P0-09, P0-11 | 幂等性保障 |
| `checksum` | P1-03, P1-07 | 数据完整性校验 |
| `confidence: 0~1` | P1-09 | ML 模型置信度分数 |
| `parent_version_id` | P1-06 | 版本链（git DAG 模式） |
| `selected_version_id / accepted_version_id / applied_version_id` | P1-06 | 三指针系统（git HEAD/staging/working tree 模式） |
| `built_by` / `last_updated_by` | P1-04 | 审计字段 |
| `progress_pct: 55` | P1-04 | 百分比进度 |

---

### 偏差 9：AgentTrace 是可观测性基础设施，不是产品功能

**位置**: P1-10 全文

AgentTrace 的完整设计（三层 Trace 视图、34 个事件类型、13 个审计事件、16 个可观测性指标、6 条告警规则、5 层数据留存策略）是一个 **APM (Application Performance Monitoring)** 系统设计。

P1-UI §17.1 将其标记为"三级信息，默认折叠"，说明设计者知道这对作者无用。但整个 P1-10 文档却用了 19 个章节来详细设计它——这反映了设计资源向工程可观测性倾斜，而非向作者体验倾斜。

---

### 偏差 10：实施清单本身就是工程治理产物

**位置**: P1-实施唯一依据清单.md

> "若实现阶段发现正式文档冲突，必须暂停实现并提交'文档冲突单'。冲突未在正式文档中修订前，不得以临时口头结论推进代码。"

这个文档暴露了系统复杂度已经高到**必须用正式变更控制流程来管理**——说明设计体系已经过于庞大，不同开发者可能产生理解偏差。

---

### 偏差 11：信息架构按系统模块划分，而非按写作心智模型

**位置**: P1-UI §7.1

右侧 6 个 Tab 的结构：
```
大纲 / 线索 / 伏笔 / 人物 / AI / 审阅
```

前四个 Tab 按**数据实体类型**划分（StoryMemory 的四个域），后两个按**系统能力**划分。

作者的写作心智模型是场景化的：
- "这一章涉及哪些人物？他们的状态是什么？"
- "之前埋的伏笔在这一章要回收吗？"
- "这一章在当前卷中的位置和目标是？"

当前设计把关联信息拆到四个独立 Tab，作者需要来回切换。

Agent 进度展示同样问题（P1-UI §12.1）：
```
● Memory Agent    ✓ 完成 (1.2s)
● Planner Agent   ✓ 完成 (3.5s)
◉ Writer Agent    运行中...
○ Reviewer Agent  等待中
○ Rewriter Agent  等待中
```
这是 DevOps 任务面板的展示方式，不是作者关心的进度信息。

---

### 偏差 12：安全边界设计以"禁止列表"为核心，而非以信任为基础

贯穿全部 P0/P1 文档的"禁止事项"和"安全边界"章节累计有 **80+ 条禁止规则**：

- P0-07：11 个 Forbidden Tools
- P1-01 §12：9 条 AgentRuntime 禁止行为
- P1-02 §17：21 条不做事项
- P1-06 §17：11 条安全边界
- P0 总纲 §1.7：14 条核心安全边界
- P1 总纲 §1.7：14 条扩展安全边界

理想的安全架构应该让"正确的事情自然发生，错误的事情自然不可能"。需要 80+ 条禁止规则来约束系统行为，说明架构的直观性存在问题。

---

## 三、优先级排序：最需要修正的 Top 10 问题

| 优先级 | 问题 | 影响面 | 建议方向 |
|---|---|---|---|
| **P0** | "blocked/degraded/ready" 三态作为产品状态暴露 | 作者每次续写都会看到 | 翻译为"无法续写 / 信息可能不足 / 可以续写" |
| **P0** | Context Pack 作为 UI 卡片标题 | AI Tab 核心卡片 | 改为"写作上下文"/"AI 对故事的理解" |
| **P0** | initialization 11 状态作为进度展示 | 初始化全程 | 合并为"未开始 / 分析中 / 已完成 / 失败"4 态 |
| **P0** | AgentSession/AgentStep/Agent 概念作为进度展示 | AI 进度面板 | 改为自然语言描述："AI 正在理解故事 / 正在构思方向 / 正在写作 / 正在审阅" |
| **P1** | 4 个独立确认门控无快捷路径 | 每次续写操作 | 提供"一键续写"模式：跳过方向选择+计划确认，直接生成候选稿 |
| **P1** | model_role 12 路拆分 | AI Settings 配置 | 作者主路径仅暴露"分析模型"+"写作模型"双入口，高级折叠其余 |
| **P1** | 四层轨道命名体系 | 大纲 Tab | 改为：全书主线 / 本卷脉络 / 近期段落 / 当前上下文 |
| **P1** | 80+ 状态值直接暴露 | 全局 | 建立状态→用户可读消息的翻译层，作者看不到原始枚举值 |
| **P2** | AgentTrace 作为产品功能 | 右侧面板 | 降级为纯开发者调试工具，不进入作者 UI |
| **P2** | 100+ 错误码体系 | API 响应 | 归类为用户可读的 10-15 种操作提示 |

---

## 四、根本原因

V2.0 设计从**需求规格**层面就已经被工程视角主导：

1. **需求规格说明书**（`docs/01_requirements`）大量混杂了实现策略（Provider 抽象、Model Router、Token 预算、PPAO 循环），将这些工程决策提升为"需求规则"
2. **概要设计说明书**（`docs/07_overview`）以 Clean Architecture 分层和 ToolFacade 隔离为核心组织方式，而非以作者写作流程为核心
3. **架构设计说明书**（`docs/02_architecture`）将子域划分（13 个子域）直接映射为功能模块，缺少从作者视角的聚合
4. **所有 P0/P1 详细设计**继承了这套工程语言体系，并在每个模块中细化了状态机、权限矩阵、错误码

根本症结：**"Agent 协作系统"的工程架构直接成为了产品的信息架构**。一个好的写作工具的信息架构应该源自"作者如何写作"，而不是"系统如何编排 Agent"。

---

## 五、遍历文档清单

### P0 设计文档 (docs/03_design/V2/)
| 文档 | 状态 |
|---|---|
| InkTrace-V2.0-P0-详细设计总纲.md | 已分析 |
| InkTrace-V2.0-P0-01-AI基础设施详细设计.md | 已分析 |
| InkTrace-V2.0-P0-02-AIJobSystem详细设计.md | 已分析 |
| InkTrace-V2.0-P0-03-初始化流程详细设计.md | 已分析 |
| InkTrace-V2.0-P0-04-StoryMemory与StoryState详细设计.md | 已分析 |
| InkTrace-V2.0-P0-05-VectorRecall详细设计.md | 已分析 |
| InkTrace-V2.0-P0-06-ContextPack详细设计.md | 已分析 |
| InkTrace-V2.0-P0-07-ToolFacade与权限详细设计.md | 已分析 |
| InkTrace-V2.0-P0-08-MinimalContinuationWorkflow详细设计.md | 已分析 |
| InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计.md | 已分析 |
| InkTrace-V2.0-P0-10-AIReview详细设计.md | 已分析 |
| InkTrace-V2.0-P0-11-API与集成边界详细设计.md | 已分析 |

### P1 设计文档 (docs/03_design/)
| 文档 | 状态 |
|---|---|
| InkTrace-V2.0-P1-详细设计总纲.md | 已分析 |
| InkTrace-V2.0-P1-01-AgentRuntime详细设计.md | 已分析 |
| InkTrace-V2.0-P1-02-AgentWorkflow详细设计.md | 已分析 |
| InkTrace-V2.0-P1-03-五Agent职责与编排详细设计.md | 已分析 |
| InkTrace-V2.0-P1-04-四层剧情轨道详细设计.md | 已分析 |
| InkTrace-V2.0-P1-05-方向推演与章节计划详细设计.md | 已分析 |
| InkTrace-V2.0-P1-06-多轮CandidateDraft迭代详细设计.md | 已分析 |
| InkTrace-V2.0-P1-07-AISuggestion详细设计.md | 已分析 |
| InkTrace-V2.0-P1-08-ConflictGuard详细设计.md | 已分析 |
| InkTrace-V2.0-P1-09-StoryMemoryRevision与MemoryReviewGate详细设计.md | 已分析 |
| InkTrace-V2.0-P1-10-AgentTrace与可观测性详细设计.md | 已分析 |
| InkTrace-V2.0-P1-11-API与前端集成边界详细设计.md | 已分析 |
| InkTrace-V2.0-P1-UI-界面与交互设计.md | 已分析 |
| InkTrace-V2.0-P1-实施唯一依据清单.md | 已分析 |

### 需求 / 架构 / 概要文档
| 文档 | 状态 |
|---|---|
| InkTrace-V2.0-需求规格说明书.md | 已分析 |
| InkTrace-V2.0-概要设计说明书.md | 已分析 |
| InkTrace-V2.0-架构设计说明书.md | 已分析 |
| InkTrace-DESIGN.md | 已分析 |
