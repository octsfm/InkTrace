# InkTrace V2.0 需求规格说明书

版本：v2.0\
更新时间：2026-05-07\
范围定位：在 V1.1 非 AI 创作工作台、纯文本写作链路与结构化写作资产已具备的基础上，接入受控 AI 智能体能力，形成长篇小说 AI 写作智能体工作台。

InkTrace V2.0 是长篇小说 AI 写作智能体工作台，不是 AI 自动写书工具。AI 只能生成候选结果、分析结果和更新建议；所有进入正式正文、正式资产、正式记忆的变更，必须经过用户确认或明确授权。

***

## 1. 阶段关系

- V1：稳定纯文本写作底座。
- V1.1：非 AI 创作工作台，完成作品、章节、Local-First、结构化资产沉淀。
- V2.0：基于 Workbench 数据接入受控 AI 智能体系统。

V2.0 必须继承 V1.1 已有边界：

- 正式正文仍由 V1.1 Local-First 保存链路负责。
- V1.1 用户手动资产为正式资产。
- V2.0 AI 结果默认进入候选稿、建议区、分析结果或记忆建议，不得直接覆盖正式数据。

***

## 2. 交付批次（V2.0）

### 2.1 V2.0-P0：AI 初始化与单章受控续写（必须交付）

交付范围：

- AI 基础设施。
- AI Job System。
- 大纲分析。
- 正文分析。
- Story Memory 初始构建。
- 向量索引初始构建。
- Context Pack。
- Writing Task。
- 单章候选续写。
- 候选稿人工确认门控。
- AI 审稿基础能力。

### 2.2 V2.0-P1：智能体工作流与剧情轨道（必须交付）

交付范围：

- Agent Workflow。
- Memory / Planner / Writer / Reviewer / Rewriter Agent。
- 四层剧情轨道。
- A/B/C 剧情方向推演。
- 章节计划。
- 多轮候选稿迭代。
- AI 建议区。
- Conflict Guard。
- Story Memory 更新建议与版本。

### 2.3 V2.0-P2：增强能力（可选交付）

交付范围：

- 多章续写。
- 受控自动连续续写队列。
- Style DNA。
- Citation Link。
- @ 标签引用系统。
- Opening Agent。
- 大纲辅助。
- 选区改写/润色。
- 成本看板与分析看板。

交付说明：

- V2.0-P0 可单独提测与验收。
- V2.0-P1 完成后才视为 V2.0 核心版本完成。
- V2.0-P2 是否交付不影响 V2.0 核心完成定义。

***

## 3. 目标与原则

### 3.1 目标

- AI 带着整本小说的长期记忆辅助作者续写、改写、审稿、修订和规划。
- AI 生成内容必须先成为候选稿或建议，用户确认后才进入正式数据。
- 通过多受控智能体协作完成长篇小说工作流，而不是提供单个 AI 按钮。
- 在长篇场景下维护人物、设定、伏笔、时间线、剧情阶段和文风一致性。
- AI 能力不可破坏 V1.1 的写作稳定性、Local-First 保存链路和手动资产边界。

### 3.2 产品原则

- Human Review Gate：AI 可以生成建议和候选稿，但不能自动合并正文、覆盖资产、创建正式章节或改变作品主线。
- Context Pack 驱动：每次续写、改写、审稿、推演前必须组装上下文情报包。
- 受控智能体：每个 Agent 必须有明确职责、输入、输出、权限和可追踪执行记录。
- 分层记忆：章节摘要、阶段摘要、卷摘要、全书摘要共同支撑长篇记忆压缩。
- 剧情轨道：全文弧、卷/大段落弧、剧情波次、临近窗口必须共同约束续写。
- 失败隔离：AI 初始化或任务失败不得污染正式正文、正式资产或正式 Story Memory。
- 可追溯：AI 调用、Prompt、上下文、召回片段、候选稿、审稿结果和用户决策必须可追踪。

### 3.3 模型分工原则

- Kimi：负责分析、摘要、记忆抽取、规划、写作任务生成、审稿。
- DeepSeek：负责续写、改写、润色、对白、场景生成、修订。
- Model Router 按任务角色路由模型，业务代码不得硬编码 Provider。

### 3.4 AI 边界

V2.0 明确禁止：

- AI 自动合并正式正文。
- AI 自动覆盖正式资产。
- AI 自动创建正式章节。
- AI 自动改变作品主线。
- AI 绕过 V1.1 Local-First 正文保存链路。
- AI 无人化自动写书。

***

## 4. 规则编号体系与书写格式

### 4.1 编号体系

- R-AI-INFRA-XX：AI 基础设施
- R-AI-JOB-XX：AI 任务系统
- R-AI-INIT-XX：作品 AI 初始化
- R-AI-MEM-XX：Story Memory 与 Story State
- R-AI-ARC-XX：剧情轨道系统
- R-AI-CTX-XX：Context Pack
- R-AI-AGENT-XX：智能体工作流
- R-AI-PLAN-XX：方向推演与章节计划
- R-AI-DRAFT-XX：候选稿与续写
- R-AI-REVIEW-XX：审稿与修订
- R-AI-ASSET-XX：AI 建议区与资产保护
- R-AI-CONFIG-XX：AI 设置、成本、隐私
- R-AI-ENH-XX：增强能力
- R-AI-BOUNDARY-XX：禁止行为

### 4.2 每条需求格式

每条需求统一写成：

- Rule：规则与意图
- Behavior：用户可观察行为
- Edge Case：边界与异常行为
- Acceptance：可验证验收点

***

## 5. V2.0 主线工作流

### R-AI-WF-01 标准主线工作流

- Rule：V2.0 主线工作流必须按受控步骤执行，禁止 AI 跳过人工确认直接改变正式数据。
- Behavior：
  - 标准流程为：作品初始化 → 大纲分析 → 正文分析 → 小说记忆构建 → 剧情方向推演 → 章节计划 → 续写 → 审稿 → 修订 → 用户确认 → 记忆更新。
  - 用户确认前，AI 生成的正文只存在于候选稿区。
  - 用户确认前，AI 提取的人物、事件、伏笔、设定、时间线只存在于 AI 建议区。
  - 用户确认后，正文候选稿进入当前章节草稿区，并继续由 V1.1 Local-First 保存链路处理。
- Edge Case：
  - 初始化未完成：不开放正式续写能力。
  - 用户取消候选稿：候选稿保留历史记录，但不得写入正式正文。
- Acceptance：
  - 从续写到确认的完整流程中，AI 不直接写入正式章节内容。

***

## 6. V2.0-P0：AI 基础设施与初始化

### R-AI-INFRA-01 Provider 抽象

- Rule：系统必须提供统一 AI Provider 抽象，业务代码不得直接调用具体 Provider SDK。
- Behavior：
  - 支持 Kimi 与 DeepSeek Provider。
  - Provider 统一暴露文本生成、流式输出、token 估算、超时、重试、错误归一化能力。
  - Provider Key 未配置时，相关能力提示用户配置。
- Edge Case：
  - Provider 调用失败：返回结构化错误，不写入候选稿或正式数据。
- Acceptance：
  - 同一写作任务可通过配置切换 Provider，无需修改业务代码。

### R-AI-INFRA-02 Model Router

- Rule：业务代码必须按任务角色调用模型。
- Behavior：
  - writer、rewriter 默认路由到 DeepSeek。
  - memory_extractor、planner、reviewer 默认路由到 Kimi。
  - 路由配置可在 AI Settings 中调整。
- Edge Case：
  - 指定模型不可用：任务失败并提示用户，不自动使用未知模型。
- Acceptance：
  - Writer Agent 与 Reviewer Agent 调用不同默认模型，调用日志可验证。

### R-AI-INFRA-03 Prompt Registry

- Rule：Prompt 模板必须独立管理，并绑定输入 schema、输出 schema、版本和启用状态。
- Behavior：
  - 每个 Agent 能力对应 prompt key。
  - Prompt 模板变更必须记录版本。
  - Prompt 输入与输出必须可测试。
- Edge Case：
  - Prompt 输出不符合 schema：进入重试或 failed 状态，不得半结构化落库。
- Acceptance：
  - 每个结构化 AI 能力均能找到对应 prompt key、版本和 schema。

### R-AI-INFRA-04 Output Validator

- Rule：所有结构化 AI 输出必须经过 JSON Schema 校验。
- Behavior：
  - 校验成功后才允许进入分析结果、建议区或临时结果。
  - 校验失败最多重试指定次数。
  - 多次失败后任务进入 failed。
- Edge Case：
  - 输出包含额外未知字段：按 schema 策略拒绝或剔除，并记录 trace。
- Acceptance：
  - 构造非法 AI 输出时，系统拒绝落库并记录失败原因。

### R-AI-JOB-01 AI Job System

- Rule：长耗时 AI 能力必须通过 AI Job System 执行。
- Behavior：
  - 支持创建、开始、暂停、继续、取消、失败重试、结果查询。
  - 支持跳过失败章节、重新分析某章、重新构建记忆。
  - 任务状态必须包含 queued、running、paused、failed、cancelled、completed。
- Edge Case：
  - 服务重启：运行中任务标记为 failed 或 paused，需要用户确认恢复。
- Acceptance：
  - 大纲分析、正文分析、向量索引构建均可查看任务状态和进度。

### R-AI-INIT-01 两阶段初始化

- Rule：作品 AI 初始化必须分为大纲分析和正文分析两个阶段。
- Behavior：
  - 第一阶段分析作品大纲。
  - 大纲分析完成并落库后，才允许执行正文分析。
  - 第二阶段分析已有正文，并对照大纲判断当前进度、偏离和已完成剧情。
- Edge Case：
  - 无作品大纲：允许用户跳过大纲分析，但正文分析标记为“缺少大纲参考”。
  - 正文为空：只完成大纲分析，不开放正文记忆能力。
- Acceptance：
  - 未完成大纲分析时，系统拒绝开始标准正文分析。

### R-AI-INIT-02 大纲分析

- Rule：大纲分析必须提取小说总地图。
- Behavior：
  - 提取主线、阶段结构、核心冲突、主要人物、势力、世界观、关键伏笔、预期结局方向。
  - 分析结果落库为 AI 大纲分析结果，不覆盖用户手写作品大纲。
- Edge Case：
  - 大纲内容过短：生成低置信度分析并提示用户补充。
- Acceptance：
  - 大纲分析完成后刷新页面，分析结果仍可查看。

### R-AI-INIT-03 正文分段分析

- Rule：正文分析必须按章节或分段处理长篇正文。
- Behavior：
  - 支持分析前 30 万字、100 万字或更多正文。
  - 生成章节摘要、阶段摘要、卷摘要、全书当前进度摘要。
  - 对照大纲判断正文写到哪个阶段、哪些剧情完成、哪些偏离、哪些伏笔已出现或未出现。
- Edge Case：
  - 单章过长：按分段分析后合并摘要。
  - 单章分析失败：允许跳过失败章节并继续后续章节。
- Acceptance：
  - 正文分析完成后，每个已分析章节均有摘要和进度记录。

### R-AI-INIT-04 初始化进度提示

- Rule：初始化长任务必须显示细粒度进度。
- Behavior：
  - 显示大纲分析、正文切分、章节摘要、人物提取、伏笔提取、向量索引构建进度。
  - 显示当前阶段、已完成数量、失败数量、预计剩余工作。
- Edge Case：
  - 进度无法估算：显示当前步骤和已处理数量，不显示虚假百分比。
- Acceptance：
  - 100 万字初始化过程中用户能看到当前执行阶段。

### R-AI-INIT-05 初始化完成门槛

- Rule：只有初始化完成后才开放正式续写能力。
- Behavior：
  - 必须完成大纲分析、正文分析、Story Memory、向量索引、当前 Story State。
  - 未完成时，续写入口置灰或提示“请先完成 AI 初始化”。
- Edge Case：
  - 用户选择跳过大纲分析：系统以降级状态开放受限能力，并明确提示上下文质量受限。
- Acceptance：
  - 未完成初始化时无法生成正式续写候选稿。

***

## 7. Story Memory、Story State 与向量召回

### R-AI-MEM-01 Story Memory 长期记忆

- Rule：系统必须维护小说长期记忆。
- Behavior：
  - 维护章节摘要、阶段摘要、卷摘要、全书摘要。
  - 维护角色卡、角色状态、设定、事件、伏笔、地点、风格画像。
  - AI 提取结果先进入建议或记忆更新建议，不直接覆盖正式资产。
- Edge Case：
  - AI 与用户手动资产冲突：进入 Conflict Guard。
- Acceptance：
  - 续写前可查看当前作品已有 Story Memory。

### R-AI-MEM-02 Story State 当前故事状态锁

- Rule：系统必须维护当前故事状态，防止 AI 写崩。
- Behavior：
  - 记录当前地点、在场角色、角色状态、境界/能力、阵营关系、当前剧情阶段、未解伏笔、禁止事项。
  - Story State 进入 Context Pack。
- Edge Case：
  - Story State 缺失：续写任务必须提示上下文不足。
- Acceptance：
  - 审稿能检查候选稿是否违反当前 Story State。

### R-AI-MEM-03 Recursive Summary 分层摘要

- Rule：系统必须通过分层摘要支撑长篇压缩记忆。
- Behavior：
  - 章节摘要合并为阶段摘要。
  - 阶段摘要合并为卷摘要。
  - 卷摘要合并为全书当前进度摘要。
- Edge Case：
  - 章节更新后：相关上级摘要标记为待更新。
- Acceptance：
  - 修改章节后，对应摘要链路可识别需要重算。

### R-AI-MEM-04 Vector Recall 历史剧情召回

- Rule：系统必须支持基于本地 Embedding 与 Vector DB 的历史剧情召回。
- Behavior：
  - 支持章节切片、Embedding、向量入库、索引更新、索引重建。
  - 记录 chunk 与章节、段落位置关系。
  - 续写、审稿、改写前可召回相关旧剧情片段。
- Edge Case：
  - 向量索引未完成：Context Pack 降级，不阻断非召回类分析。
- Acceptance：
  - 给定当前写作任务，可召回相关历史片段及来源章节。

### R-AI-MEM-05 Memory 版本与回滚

- Rule：Story Memory 每次正式更新必须形成版本。
- Behavior：
  - 用户采纳 AI 记忆更新建议后生成 memory revision。
  - 记录变更来源、Agent Trace、用户决策。
  - 支持查看最近更新与回滚最近一次记忆更新。
- Edge Case：
  - 回滚后：依赖该版本的未执行任务标记为需要重新确认。
- Acceptance：
  - 采纳 AI 建议后可查看记忆变更记录并回滚。

***

## 8. 剧情轨道系统

### R-AI-ARC-01 四层剧情轨道

- Rule：系统必须形成全文弧、卷/大段落弧、剧情波次、临近窗口四层剧情轨道。
- Behavior：
  - 四层轨道均进入 Context Pack。
  - 每层轨道记录层级、状态、目标、冲突、章节范围、下一步推进方向。
- Edge Case：
  - 某一层缺失：续写前提示轨道不完整，但全文弧不得缺失。
- Acceptance：
  - 任意续写任务可查看其使用的四层轨道内容。

### R-AI-ARC-02 Master Arc 全文弧

- Rule：全文弧记录全书级主线约束。
- Behavior：
  - 记录终极目标、最终冲突、最终 BOSS、主角长期动机、终局伏笔、当前主线阶段。
- Edge Case：
  - 全文弧过长：可压缩，但不得从 Context Pack 中移除。
- Acceptance：
  - 审稿能判断候选稿是否偏离全文弧。

### R-AI-ARC-03 Volume / Act Arc

- Rule：卷/大段落弧记录当前阶段约束。
- Behavior：
  - 记录当前卷或阶段的核心矛盾、阶段目标、主要敌人、高潮节点、收束条件、当前阶段位置。
- Edge Case：
  - 当前章节跨阶段：标记过渡状态。
- Acceptance：
  - 续写任务能引用当前卷弧目标和收束条件。

### R-AI-ARC-04 Sequence Arc

- Rule：剧情波次记录 10-20 章级别的小剧情循环。
- Behavior：
  - 记录目标、冲突、关键事件、反转点、爽点、预计收束章节。
- Edge Case：
  - 小弧结束：Planner Agent 必须提示进入下一小弧或生成新小弧建议。
- Acceptance：
  - 自动续写可选择续写到当前小弧结束。

### R-AI-ARC-05 Immediate Window

- Rule：临近窗口必须记录最近上下文。
- Behavior：
  - 记录前 10 章摘要、前 3 章精简内容、当前章节上下文、角色情绪、动作轨迹、场景细节、上一章钩子。
- Edge Case：
  - 作品章节少于 10 章：使用全部已有章节。
- Acceptance：
  - Context Pack 中临近窗口优先级最高。

### R-AI-ARC-06 剧情轨道 Token 优先级

- Rule：剧情轨道超限裁剪必须遵循优先级。
- Behavior：
  - 优先级：临近窗口 > 当前 Sequence Arc > 当前 Volume / Act Arc > Master Arc。
  - Master Arc 可以短，但不能缺。
- Edge Case：
  - Token 极限不足：保留 Master Arc 摘要和 Immediate Window 核心信息。
- Acceptance：
  - 构造超长轨道时，裁剪结果仍包含 Master Arc。

***

## 9. Context Pack 与 Writing Task

### R-AI-CTX-01 Context Pack

- Rule：每次 AI 续写、改写、审稿前必须组装 Context Pack。
- Behavior：
  - 包含当前章节/选区上下文、摘要、Story State、角色、设定、伏笔、召回片段、四层剧情轨道、Writing Task。
- Edge Case：
  - 缺少关键上下文：任务进入 blocked，提示用户补齐或降级执行。
- Acceptance：
  - 任意候选稿可追踪到生成时使用的 Context Pack。

### R-AI-CTX-02 Token 优先级

- Rule：上下文超限时必须按优先级裁剪。
- Behavior：
  - 优先级：当前章节/选区上下文 > 当前卷摘要和最近章节摘要 > Story State > Writing Task > 全书摘要/角色卡/设定 > RAG 召回片段 > Style DNA。
  - 四层剧情轨道按 R-AI-ARC-06 单独执行保底规则。
- Edge Case：
  - 裁剪导致 Writing Task 不完整：禁止执行生成。
- Acceptance：
  - 超限时裁剪结果可解释且可追踪。

### R-AI-CTX-03 Attention Filter

- Rule：系统必须根据当前任务动态过滤无关信息。
- Behavior：
  - 根据当前章节、选区、Writing Task 过滤无关角色、地点、设定和召回片段。
  - 过滤结果写入 Agent Trace。
- Edge Case：
  - 过滤后信息不足：回退到更宽松召回策略。
- Acceptance：
  - 同一作品不同章节生成的 Context Pack 内容不同。

### R-AI-PLAN-01 Writing Task

- Rule：正式续写前必须生成 Writing Task。
- Behavior：
  - 包含本次写作目标、必须包含内容、禁止内容、情绪基调、目标字数、关联剧情轨道。
  - Writing Task 由 Planner Agent 生成，用户可编辑或确认。
- Edge Case：
  - 用户跳过章节计划：系统仍必须生成最小 Writing Task。
- Acceptance：
  - Writer Agent 不能在无 Writing Task 的情况下生成正式候选稿。

***

## 10. 智能体工作流

### R-AI-AGENT-01 Agent Workflow

- Rule：标准智能体流程为 Memory Agent → Planner Agent → Writer Agent → Reviewer Agent → Rewriter Agent → 用户确认 → Memory Agent 更新建议。
- Behavior：
  - 每个 Agent 输入输出必须结构化。
  - 每个 Agent 执行必须记录 Agent Trace。
  - 用户可中止流程。
- Edge Case：
  - Reviewer 发现严重冲突：流程停止，候选稿标记为 blocked。
- Acceptance：
  - 单章续写可完整跑通规划、写作、审稿、修订、确认、记忆建议。

### R-AI-AGENT-02 Agent 权限矩阵

- Rule：每个 Agent 必须有明确权限。
- Behavior：
  - Memory Agent：可读正文/资产，可写分析结果和更新建议，不可写正式正文。
  - Planner Agent：可读 Memory/Arc，可写方向建议、章节计划和 Writing Task。
  - Writer Agent：可写候选稿，不可写正式正文。
  - Reviewer Agent：可写审稿报告，不可改候选稿。
  - Rewriter Agent：可写修订候选稿，不可合并正文。
  - Opening Agent：可写开篇候选稿和审稿报告，不可写正式章节。
- Edge Case：
  - Agent 尝试越权写入：系统拒绝并记录安全事件。
- Acceptance：
  - 自动化测试可验证 Agent 无权直接修改正式正文。

### R-AI-AGENT-03 Agent Trace

- Rule：每次智能体执行必须记录执行轨迹。
- Behavior：
  - 记录 trace_id、Agent、模型、Prompt 版本、Context Pack、召回片段、输出、审稿结果、用户决策。
  - 默认不记录 API Key。
  - 正文与 Prompt 全文记录遵循隐私设置。
- Edge Case：
  - Trace 写入失败：AI 任务不得进入 completed。
- Acceptance：
  - 用户可查看候选稿对应的生成轨迹。

***

## 11. 方向推演、章节计划与续写

### R-AI-PLAN-02 后续方向推演

- Rule：系统必须基于大纲、已有正文记忆和四层剧情轨道生成 A/B/C 后续方向。
- Behavior：
  - 每个方向包含剧情概要、主要冲突、伏笔使用、风险点、未来 3-5 章预估。
  - 方向不能凭空发散，必须引用当前剧情轨道。
- Edge Case：
  - 轨道信息不足：标记方向置信度低。
- Acceptance：
  - 每个方向均可看到依据的剧情轨道摘要。

### R-AI-PLAN-03 用户选择剧情方向

- Rule：用户必须选择或编辑方向后，系统才能生成章节计划。
- Behavior：
  - 用户可选择 A/B/C 之一。
  - 用户可要求重新生成方向。
  - 用户可手动编辑方向摘要。
- Edge Case：
  - 用户取消方向选择：不生成章节计划。
- Acceptance：
  - 未选择方向时无法进入章节计划生成。

### R-AI-PLAN-04 章节计划生成

- Rule：方向确认后，系统生成后续 3-5 章章节计划。
- Behavior：
  - 每章包含章节目标、关键事件、冲突推进、伏笔安排、禁止事项。
  - 章节计划进入 Writing Task 的上游约束。
- Edge Case：
  - 用户指定仅规划下一章：只生成单章计划。
- Acceptance：
  - 下一章 Writing Task 能引用对应章节计划。

### R-AI-DRAFT-01 Candidate Draft 候选稿机制

- Rule：AI 生成正文不得直接进入正式正文，必须进入候选稿区。
- Behavior：
  - 候选稿支持接受、插入、替换、丢弃、重新生成。
  - 候选稿保留生成来源、版本关系和审稿状态。
  - 用户接受候选稿后，内容进入当前章节草稿区，由 Local-First 保存链路处理。
- Edge Case：
  - 接受候选稿时当前正文有未保存草稿：按正文草稿合并提示处理，不直接覆盖。
- Acceptance：
  - AI 续写完成后，数据库正式章节内容不会在用户接受前变化。

### R-AI-DRAFT-02 单章续写

- Rule：系统支持根据选定方向、章节计划和 Context Pack 生成下一章候选稿。
- Behavior：
  - 生成前必须存在 Writing Task。
  - 生成后进入 Reviewer Agent 审稿。
- Edge Case：
  - 生成中断：保留已生成片段为临时候选，不进入正式候选版本。
- Acceptance：
  - 下一章候选稿可完成生成、审稿、确认流程。

### R-AI-DRAFT-03 多章续写

- Rule：系统支持用户指定续写 3 章、5 章或续写到当前小剧情结束。
- Behavior：
  - 按章生成候选稿、审稿、用户确认、记忆更新建议。
  - 每章之间必须更新临近窗口和 Story State。
- Edge Case：
  - 某章审稿严重失败：队列暂停，等待用户处理。
- Acceptance：
  - 多章续写不会一次性直接合并多章正式正文。

### R-AI-DRAFT-04 自动连续续写队列

- Rule：自动连续续写必须受控执行，并有明确停止条件。
- Behavior：
  - 用户设定目标章数、目标字数或停止条件。
  - 系统逐章生成候选稿，不自动合并正式正文。
  - 到达停止条件后暂停。
- Edge Case：
  - 成本上限、模型失败、严重冲突、连续修订失败、伏笔提前揭示、用户停止均必须中断队列。
- Acceptance：
  - 自动续写队列停止时保留已生成候选稿和失败原因。

### R-AI-DRAFT-05 候选稿多轮迭代

- Rule：候选稿支持基于用户反馈多轮重新生成或修订。
- Behavior：
  - 用户可输入反馈，如“节奏加快”“多用短句”“减少心理描写”。
  - 新候选稿记录 parent_draft_id。
- Edge Case：
  - 连续多轮失败：提示用户调整 Writing Task 或 Context Pack。
- Acceptance：
  - 候选稿版本关系可查看。

***

## 12. 审稿、修订与质量控制

### R-AI-REVIEW-01 AI Review 候选稿审稿

- Rule：候选稿生成后必须进行 AI 审稿。
- Behavior：
  - Reviewer Agent 检查人物一致性、设定冲突、时间线冲突、伏笔误用、风格漂移、AI 味、任务完成度。
  - 审稿必须检查候选稿是否偏离 Master Arc、Volume / Act Arc、Sequence Arc、Immediate Window。
- Edge Case：
  - 审稿模型不可用：候选稿标记为未审稿，不允许进入自动连续队列下一步。
- Acceptance：
  - 每个正式候选稿都有审稿状态。

### R-AI-REVIEW-02 Rewriter Agent 修订

- Rule：Rewriter Agent 只能基于审稿问题修订候选稿。
- Behavior：
  - 支持局部修订、降低 AI 味、调整节奏、强化钩子和悬念。
  - 修订稿作为新候选稿版本。
- Edge Case：
  - 修订后仍有严重冲突：流程停止，等待用户决策。
- Acceptance：
  - 修订不会直接改正式正文。

### R-AI-REVIEW-03 Output Quality Validator

- Rule：AI 生成与审稿结果必须通过基础质量校验。
- Behavior：
  - 检查空输出、重复段落、明显截断、schema 错误、字数严重偏离。
  - 不合格输出进入 retry 或 failed。
- Edge Case：
  - 重试后仍失败：保留失败记录和 trace。
- Acceptance：
  - 空候选稿不能进入候选稿区。

***

## 13. AI 建议区与资产保护

### R-AI-ASSET-01 AI Suggestion Store

- Rule：AI 后处理得到的人物、事件、伏笔、设定、时间线、摘要等结果必须先进入 AI 建议区。
- Behavior：
  - 建议状态包括 pending、accepted、rejected、edited、expired。
  - 用户采纳后才写入正式资产或正式 Story Memory。
- Edge Case：
  - 原资产已被用户手动修改：建议标记为可能冲突。
- Acceptance：
  - AI 提取人物后，不会自动写入正式人物卡。

### R-AI-ASSET-02 Conflict Guard

- Rule：AI 建议更新用户手动维护资产时，必须显示对比界面。
- Behavior：
  - 展示本地正式资产与 AI 建议差异。
  - 用户可采纳、拒绝、编辑后采纳。
  - 决策前不得覆盖正式资产。
- Edge Case：
  - 多个建议修改同一资产：按创建时间或用户选择逐条处理。
- Acceptance：
  - AI 建议不能静默覆盖人物、设定、伏笔、时间线。

### R-AI-ASSET-03 V1.1 资产优先级

- Rule：V1.1 用户手动资产是正式资产，AI 资产默认不是正式资产。
- Behavior：
  - AI 提取结果默认进入建议区。
  - 用户采纳后才进入正式资产表或 Story Memory。
  - AI 不得降低或删除用户手动维护资产。
- Edge Case：
  - AI 建议与正式资产冲突：以正式资产为准。
- Acceptance：
  - 用户手动人物卡不会被 AI 自动改写。

***

## 14. AI 设置、成本、隐私与日志

### R-AI-CONFIG-01 AI Settings

- Rule：系统必须提供 AI 配置能力。
- Behavior：
  - 支持 Kimi Key、DeepSeek Key、连接测试、模型角色配置、temperature、max tokens、timeout、预算、本地 Embedding 开关。
  - Key 未配置时，对应能力不可用。
- Edge Case：
  - 连接测试失败：保存配置但标记不可用。
- Acceptance：
  - 用户可配置 writer 使用 DeepSeek，reviewer 使用 Kimi。

### R-AI-CONFIG-02 成本与限流

- Rule：AI 调用必须记录用量并支持预算上限。
- Behavior：
  - 记录 provider、model、role、tokens、耗时、错误、成本、用户是否采纳。
  - 支持单作品初始化预算上限、单次自动续写队列预算上限、月度预算上限。
  - 超预算必须暂停并等待用户确认。
- Edge Case：
  - 模型失败或超时不得无限重试。
- Acceptance：
  - 超过预算后自动续写队列暂停。

### R-AI-CONFIG-03 隐私与日志脱敏

- Rule：系统不得在日志中泄露敏感内容。
- Behavior：
  - 用户 API Key 本地加密存储或按平台安全机制存储。
  - 后端日志不得记录 API Key、完整正文、完整草稿、完整 Prompt。
  - Agent Trace 默认记录摘要、hash、引用 ID 与必要片段。
  - 导出诊断日志必须脱敏。
- Edge Case：
  - 用户开启详细调试日志：必须二次确认并显示风险提示。
- Acceptance：
  - 普通日志中搜索不到 API Key 和完整正文。

***

## 15. V2.0-P2 增强能力

### R-AI-ENH-01 Style DNA

- Rule：系统可提取文风指纹用于约束续写和改写。
- Behavior：
  - 支持上传或指定标杆正文。
  - 提取词频、句式、段落节奏、对白比例、心理描写比例、叙述视角。
- Edge Case：
  - 标杆文本过短：标记低置信度。
- Acceptance：
  - 续写 Context Pack 可包含 Style DNA。

### R-AI-ENH-02 Citation Link

- Rule：AI 候选稿使用前文设定、伏笔、角色状态或历史事件时，应标记来源。
- Behavior：
  - 用户可点击查看引用章节、摘要或资产。
  - 引用进入候选稿元数据，不污染正文纯文本。
- Edge Case：
  - 来源不确定：标记为低置信度引用。
- Acceptance：
  - 候选稿可查看至少一条历史依据来源。

### R-AI-ENH-03 @ 标签引用系统

- Rule：正文可支持 `@人物`、`@地点`、`@事件`、`@伏笔` 等引用建议。
- Behavior：
  - AI 后处理可生成 @ 引用建议。
  - 用户确认后才进入正式引用。
- Edge Case：
  - 同名实体：必须让用户选择目标实体。
- Acceptance：
  - @ 引用不会自动改变正文正式内容。

### R-AI-ENH-04 选区改写/润色

- Rule：用户选中正文片段后，可触发受控改写能力。
- Behavior：
  - 支持扩写、重写、缩写、润色、对白优化、降低 AI 味。
  - 输出进入候选替换区，用户确认后才替换选区草稿。
- Edge Case：
  - 选区为空：不显示选区改写能力。
- Acceptance：
  - 改写结果不会自动替换正式正文。

### R-AI-ENH-05 大纲辅助

- Rule：AI 可辅助大纲润色、扩写、章节细纲建议和下一章 Writing Task 建议。
- Behavior：
  - 输出进入候选建议，用户确认后才写入大纲草稿或建议区。
- Edge Case：
  - 用户手写大纲已有内容：AI 建议不得自动覆盖。
- Acceptance：
  - AI 大纲建议默认不修改正式作品大纲。

### R-AI-ENH-06 Opening Agent

- Rule：Opening Agent 负责签约向开篇辅助，不自动创建正式章节。
- Behavior：
  - 可分析平台参考小说前 1-3 章，总结开篇规律、钩子、节奏、冲突、爽点。
  - 可辅助生成用户原创前三章候选稿。
  - 可审查开篇候选稿的钩子、主角目标、冲突提前量、爽点密度、章节结尾悬念、平台文感、过度模仿风险。
- Edge Case：
  - 参考文本版权来源不明：提示用户确认使用权限。
- Acceptance：
  - Opening Agent 生成内容只进入候选稿，不创建正式章节。

### R-AI-ENH-07 轻量结构化故事事实

- Rule：V2.0 初期只做轻量结构化事实，不优先做复杂 Knowledge Graph。
- Behavior：
  - 记录角色关系、阵营关系、物品归属、地点事件、伏笔状态等。
  - 不做复杂多跳推理和图谱可视化。
- Edge Case：
  - 事实冲突：进入 AI 建议区和 Conflict Guard。
- Acceptance：
  - 轻量事实可用于 Context Pack 过滤与审稿。

***

## 16. 明确禁止

### R-AI-BOUNDARY-01 AI 不自动合并正式正文

- Rule：AI 生成内容不能未经确认直接写入正式正文。
- Behavior：
  - AI 正文输出只进入候选稿区。
  - 用户接受后进入当前章节草稿区。
  - 正式保存仍由 V1.1 Local-First 保存链路处理。
- Acceptance：
  - AI 生成候选稿时，正式章节内容不变。

### R-AI-BOUNDARY-02 AI 不自动覆盖资产

- Rule：AI 不能自动覆盖用户维护的人物、伏笔、设定、时间线等资产。
- Behavior：
  - AI 修改建议进入建议区。
  - 用户确认后才写入正式资产。
- Acceptance：
  - AI 提取结果不会静默改变正式资产表。

### R-AI-BOUNDARY-03 AI 不自动创建正式章节

- Rule：AI 可以生成章节建议或候选稿，但不能未经确认自动创建正式章节。
- Behavior：
  - 多章续写生成的是候选稿序列。
  - 用户确认后才进入章节草稿或创建流程。
- Acceptance：
  - 自动续写队列不会自动新增正式章节。

### R-AI-BOUNDARY-04 AI 不改变 Local-First

- Rule：V2.0 AI 不得改变 V1.1 正文写作保存链路。
- Behavior：
  - 离线时 AI 不可用。
  - 写作、保存、导入、导出等 V1.1 能力不受 AI 状态影响。
- Acceptance：
  - AI Provider 不可用时，用户仍可正常写作并保存。

### R-AI-BOUNDARY-05 V2.0 不做无人化自动写书

- Rule：V2.0 可以做自动续写队列，但正式内容仍必须有人确认。
- Behavior：
  - 自动队列只生成候选稿、审稿、修订建议。
  - 合并正文、覆盖资产、更新记忆均需要用户确认或明确授权。
- Acceptance：
  - 无用户确认时，自动队列不会改变正式正文和正式资产。

***

## 17. 总体验收标准

V2.0-P0 验收：

- [ ] AI Settings 可配置 Kimi 与 DeepSeek。
- [ ] Model Router 按任务角色调用模型。
- [ ] AI Job System 支持初始化长任务。
- [ ] 大纲分析完成并落库。
- [ ] 正文分析必须在大纲分析后执行。
- [ ] Story Memory、Story State、向量索引完成后才开放续写。
- [ ] Context Pack 可追踪。
- [ ] 单章续写生成候选稿，不写正式正文。
- [ ] 候选稿可审稿、可接受、可丢弃。
- [ ] 接受候选稿后进入章节草稿区，并走 Local-First 保存。

V2.0-P1 验收：

- [ ] Agent Workflow 可完整跑通。
- [ ] Agent 权限矩阵通过测试。
- [ ] 四层剧情轨道可落库并进入 Context Pack。
- [ ] A/B/C 方向基于剧情轨道生成。
- [ ] 用户选择方向后生成章节计划。
- [ ] Reviewer Agent 检查剧情轨道偏离。
- [ ] AI 建议区可采纳、拒绝、编辑。
- [ ] Conflict Guard 防止覆盖用户资产。
- [ ] Story Memory 更新有版本与回滚。

V2.0-P2 验收：

- [ ] 多章续写按章生成候选稿。
- [ ] 自动续写队列具备停止条件。
- [ ] Style DNA 可进入 Context Pack。
- [ ] Citation Link 可追踪来源。
- [ ] 选区改写结果不自动替换正文。
- [ ] Opening Agent 不创建正式章节。

***

## 18. 待确认项

1. V2.0-P0 是否包含流式输出，或先使用非流式返回。
2. Vector DB 采用本地 SQLite 扩展、独立本地库，还是文件型向量索引。
3. AI Settings 中 API Key 的最终存储方式。
4. 自动续写队列是否进入 V2.0-P1，还是保留在 V2.0-P2。
5. Citation Link 是否以候选稿元数据实现，还是作为后续正文标注能力实现。
