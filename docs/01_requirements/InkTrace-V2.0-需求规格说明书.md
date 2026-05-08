# InkTrace V2.0 最终需求规格说明书

版本：v2.0-final  
更新时间：2026-05-07  
主干来源：`docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`  
补充来源：`docs/01_requirements/InkTrace-V2.0-需求规格说明书_001.md`

***

## 1. 范围定位

InkTrace V2.0 是基于 V1.1 非 AI 创作工作台之上的长篇小说 AI 写作智能体工作台。

V2.0 的目标不是让 AI 自动写书，而是让 AI 在用户掌控下完成分析、规划、候选生成、审稿、修订和记忆更新建议，辅助作者完成长篇小说创作。

V2.0 中，AI 只能生成：

- 候选稿。
- 分析结果。
- 剧情方向建议。
- 章节计划。
- 审稿报告。
- 修订稿。
- 资产更新建议。
- Story Memory 更新建议。

所有进入正式正文、正式资产、正式记忆的变更，必须经过用户确认或明确授权。

明确授权必须是当前任务范围内的显式授权，不能作为 AI 长期自动覆盖正式正文、正式资产、正式记忆的通用许可。即使用户开启自动续写队列，自动队列也只能生成候选稿、审稿报告和修订建议，不等于授权 AI 自动合并正式正文。

***

## 2. V1.1 继承边界

V2.0 必须继承 V1.1 已落地能力和边界。

继承规则：

- 正式正文仍走 V1.1 Local-First 保存链路。
- 正式章节内容仍由用户编辑区草稿进入保存链路。
- V1.1 用户手动资产是正式资产。
- AI 结果默认进入候选稿区、AI 建议区、分析结果区或记忆建议区。
- AI 不得直接覆盖正式正文、正式资产或正式 Story Memory。
- 离线时 AI 能力不可用，但 V1.1 写作、保存、导入、导出能力不受影响。
- Workbench 与 Legacy 隔离继续有效，V2.0 AI 只基于 Workbench 数据工作。

***

## 3. V2.0 产品定位

### 3.1 核心定位

InkTrace V2.0 是长篇小说 AI 写作智能体工作台。

它不是：

- AI 自动写书工具。
- 无人化章节生成系统。
- 自动覆盖用户创作资产的分析系统。
- 单个“AI 续写”按钮。

它是：

- 以作品记忆为基础的 AI 写作辅助系统。
- 以 Human Review Gate 为门控的人机协作系统。
- 以多智能体协作为核心的受控工作流系统。
- 面向长篇小说一致性、连续性和可追溯性的创作工作台。

### 3.2 标准工作流

V2.0 主线工作流：

```text
作品初始化
  -> 大纲分析
  -> 正文分析
  -> 小说记忆构建
  -> 剧情方向推演
  -> 章节计划
  -> 续写
  -> 审稿
  -> 修订
  -> 用户确认
  -> 记忆更新建议
```

***

## 4. V2.0 分批交付

### 4.1 V2.0-P0：AI 初始化与单章受控续写

P0 是最小可交付闭环。

P0 包含：

- AI Settings。
- Provider 抽象。
- Model Router。
- Prompt Registry。
- Output Validator。
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

P0 的 Story Memory 初始构建只要求支持续写所需的最小可用记忆，不要求完成全部资产分析和完整剧情轨道。

P0 最小 Story Memory 包含：

- 章节摘要。
- 全书当前进度摘要。
- 主要角色状态。
- 当前 Story State。
- 基础伏笔候选。
- 基础设定事实。
- 向量索引。

P0 不包含：

- 自动连续续写。
- Opening Agent。
- 复杂分析看板。
- 复杂 Knowledge Graph。
- @ 引用系统。
- 多章自动队列。

### 4.2 V2.0-P1：智能体工作流与剧情轨道

P1 是 V2.0 核心完整版本。

P1 包含：

- Agent Workflow。
- Memory Agent。
- Planner Agent。
- Writer Agent。
- Reviewer Agent。
- Rewriter Agent。
- 四层剧情轨道。
- A/B/C 剧情方向推演。
- 章节计划。
- 多轮候选稿迭代。
- AI 建议区。
- Conflict Guard。
- Story Memory 更新建议与版本。
- 引用建议占位。
- Agent Trace。

### 4.3 V2.0-P2：增强能力

P2 是增强能力，不影响 V2.0 核心完成定义。

P2 包含：

- 多章续写。
- 受控自动连续续写队列。
- Style DNA。
- Citation Link。
- @ 标签引用系统。
- Opening Agent / 签约向开篇助手。
- 大纲辅助。
- 选区改写 / 润色。
- 成本看板。
- 分析看板。

***

## 5. 产品原则

- Human Review Gate：AI 可以生成建议和候选稿，但不能自动合并正文、覆盖资产、创建正式章节或改变作品主线。
- Context Pack 驱动：每次续写、改写、审稿、规划前必须组装上下文情报包。
- 受控智能体：每个 Agent 必须有明确职责、输入、输出、权限和执行轨迹。
- 分层记忆：章节摘要、阶段摘要、卷摘要、全书摘要共同支撑长篇记忆压缩。
- 剧情轨道：全文弧、卷/大段落弧、剧情波次、临近窗口必须共同约束 AI 输出。
- 失败隔离：AI 初始化或任务失败不得污染正式正文、正式资产或正式 Story Memory。
- 可追溯：AI 调用、Prompt、上下文、召回片段、候选稿、审稿结果和用户决策必须可追踪。
- 最小 P0：P0 只交付可闭环的最小 AI 写作流程，不把增强能力提前塞入核心闭环。

***

## 6. AI 边界与禁止行为

### R-AI-BOUNDARY-01 AI 不自动合并正式正文

- Rule：AI 生成正文不得未经用户确认进入正式正文。
- Behavior：
  - AI 正文输出必须进入 Candidate Draft。
  - 用户可接受、插入、替换、丢弃或重新生成候选稿。
  - 用户接受后，内容进入当前章节草稿区。
  - 后续保存继续走 V1.1 Local-First 保存链路。
- Edge Case：
  - 当前章节存在未保存草稿：接受候选稿前必须提示合并、插入或取消。
- Acceptance：
  - AI 生成候选稿时，正式章节内容不发生变化。

### R-AI-BOUNDARY-02 AI 不自动覆盖正式资产

- Rule：AI 不得自动覆盖用户维护的人物、伏笔、设定、时间线、大纲等正式资产。
- Behavior：
  - AI 提取和更新结果进入 AI 建议区。
  - 用户采纳后才进入正式资产。
  - 涉及用户手动维护资产时必须触发 Conflict Guard。
- Edge Case：
  - 无法判断资产是否由用户手动维护：默认按正式资产保护。
- Acceptance：
  - AI 提取人物后，不会自动修改正式人物卡。

### R-AI-BOUNDARY-03 AI 不自动创建正式章节

- Rule：AI 可以生成章节建议或候选稿，但不能未经确认自动创建正式章节。
- Behavior：
  - 多章续写生成候选稿序列。
  - 用户确认后才允许进入章节草稿或章节创建流程。
- Edge Case：
  - 自动续写队列完成多章生成：仍只保留候选稿，不创建正式章节。
- Acceptance：
  - 自动续写队列不会自动新增正式章节。

### R-AI-BOUNDARY-04 AI 不改变 Local-First

- Rule：V2.0 AI 不得改变 V1.1 正文保存链路。
- Behavior：
  - AI 不直接写入正式正文保存接口。
  - AI 不清理正文草稿缓存。
  - AI Provider 不可用时，用户仍可写作、保存、导入和导出。
- Edge Case：
  - AI 任务失败：不影响当前正文编辑与保存。
- Acceptance：
  - 断开 AI Provider 后，V1.1 写作主链路仍可用。

### R-AI-BOUNDARY-05 V2.0 不做无人化自动写书

- Rule：V2.0 可以执行受控自动续写队列，但正式内容仍必须有人确认。
- Behavior：
  - 自动队列只生成候选稿、审稿报告和修订建议。
  - 合并正文、覆盖资产、更新记忆均需要用户确认或明确授权。
- Edge Case：
  - 用户离开页面：自动队列按任务策略暂停或继续生成候选稿，但不得合并正文。
- Acceptance：
  - 无用户确认时，自动队列不会改变正式正文和正式资产。

***

## 7. 规则编号体系

- R-AI-INFRA-XX：AI 基础设施。
- R-AI-JOB-XX：AI 任务系统。
- R-AI-INIT-XX：作品 AI 初始化。
- R-AI-MEM-XX：Story Memory 与 Story State。
- R-AI-ARC-XX：剧情轨道系统。
- R-AI-CTX-XX：Context Pack。
- R-AI-AGENT-XX：智能体工作流。
- R-AI-PLAN-XX：方向推演与章节计划。
- R-AI-DRAFT-XX：候选稿与续写。
- R-AI-REVIEW-XX：审稿与修订。
- R-AI-ASSET-XX：AI 建议区与资产保护。
- R-AI-CITE-XX：引用追踪与 @ 标签。
- R-AI-CONFIG-XX：AI 设置、成本、隐私。
- R-AI-ENH-XX：增强能力。
- R-AI-BOUNDARY-XX：禁止行为。

每条需求格式：

- Rule：规则与意图。
- Behavior：用户可观察行为。
- Edge Case：边界与异常行为。
- Acceptance：可验证验收点。

***

## 8. V2.0 主线工作流

### R-AI-WF-01 标准主线工作流

- Rule：V2.0 主线工作流必须按受控步骤执行。
- Behavior：
  - 标准流程为：作品初始化 → 大纲分析 → 正文分析 → 小说记忆构建 → 剧情方向推演 → 章节计划 → 续写 → 审稿 → 修订 → 用户确认 → 记忆更新建议。
  - 用户确认前，AI 生成正文只存在于候选稿区。
  - 用户确认前，AI 生成资产变化只存在于 AI 建议区。
  - 用户确认后，正文候选稿进入当前章节草稿区。
- Edge Case：
  - 初始化未完成：正式续写入口不可用。
  - 用户取消候选稿：候选稿保留历史记录，但不得写入正式正文。
- Acceptance：
  - 单章续写流程中，AI 不能直接写入正式章节内容。

### R-AI-WF-02 Human Review Gate

- Rule：所有影响正式数据的 AI 结果必须经过人工确认门控。
- Behavior：
  - 正文候选稿需要用户接受后才能进入章节草稿。
  - 资产建议需要用户采纳后才能进入正式资产。
  - 记忆更新建议需要用户确认后才能形成正式 Memory Revision。
  - 明确授权只对当前任务、当前候选稿、当前建议或当前队列配置生效。
  - 明确授权不得被解释为永久自动合并、永久自动覆盖或跨任务通用许可。
- Edge Case：
  - 用户未决策：AI 结果保持 pending，不自动过期写入正式数据。
  - 自动续写队列运行中：队列只能继续生成候选稿、审稿报告和修订建议，不得将候选稿自动合并到正式正文。
- Acceptance：
  - 所有正式数据写入均可追踪到用户确认动作或明确授权记录。
  - 自动续写队列开启后，正式正文仍不会在用户确认前变化。

***

## 9. P0：AI 初始化与单章受控续写

### R-AI-INFRA-01 Provider 抽象

- Rule：系统必须提供统一 AI Provider 抽象，业务代码不得直接调用具体 Provider SDK。
- Behavior：
  - 支持 Kimi 与 DeepSeek Provider。
  - Provider 统一暴露 `chat(messages, options)`、`count_tokens(text)`、`get_model_info()`。
  - Provider 支持流式输出能力，但 P0 是否必须启用流式输出作为待确认项。
  - Provider 统一处理 token 计价、超时、重试和错误归一化。
  - Provider Key 未配置时，相关能力提示用户配置。
- Edge Case：
  - Provider 调用失败：返回结构化错误，不写入候选稿或正式数据。
- Acceptance：
  - 同一任务可通过配置切换 Provider，无需修改业务代码。

### R-AI-INFRA-02 Model Router

- Rule：业务代码必须按任务角色调用模型，不允许硬编码 provider。
- Behavior：
  - Kimi 默认负责分析、摘要、记忆抽取、规划、Writing Task、审稿。
  - DeepSeek 默认负责续写、改写、润色、对白、场景生成、修订。
  - writer、rewriter 默认路由到 DeepSeek。
  - memory_extractor、planner、reviewer 默认路由到 Kimi。
  - 路由配置可在 AI Settings 中调整。
- Edge Case：
  - 指定模型不可用：任务失败并提示用户配置，不自动切换到未知模型。
- Acceptance：
  - Writer Agent 与 Reviewer Agent 调用不同默认模型，调用日志可验证。

### R-AI-INFRA-03 Prompt Registry

- Rule：Prompt 模板必须独立管理，并绑定输入 schema、输出 schema、版本和启用状态。
- Behavior：
  - 每个 Agent 能力对应 prompt key。
  - Prompt 模板变更必须记录版本。
  - Prompt 输入与输出必须可测试。
  - 每类 Agent 至少保留一组 golden sample 用于回归验证。
- Edge Case：
  - Prompt 输出不符合 schema：进入 retry 或 failed，不得半结构化落库。
- Acceptance：
  - 每个结构化 AI 能力均能找到 prompt key、版本和 schema。

### R-AI-INFRA-04 Output Validator

- Rule：所有结构化 AI 输出必须经过 JSON Schema 校验。
- Behavior：
  - 校验成功后才允许进入分析结果、建议区或临时结果。
  - 校验失败最多重试指定次数。
  - 多次失败后任务进入 failed。
- Edge Case：
  - 输出包含额外未知字段：按 schema 策略拒绝或剔除，并记录 Agent Trace。
- Acceptance：
  - 构造非法 AI 输出时，系统拒绝落库并记录失败原因。

### R-AI-JOB-01 AI Job System

- Rule：长耗时 AI 能力必须通过 AI Job System 执行。
- Behavior：
  - 支持创建、开始、暂停、继续、取消、失败重试、结果查询。
  - 支持跳过失败章节、重新分析某章、重新构建记忆。
  - 任务状态必须包含 queued、running、paused、failed、cancelled、completed。
  - 大纲分析、正文分析、章节摘要、人物提取、伏笔提取、向量索引构建均显示进度。
- Edge Case：
  - 服务重启：运行中任务标记为 failed 或 paused，需要用户确认恢复。
  - 进度无法估算：显示当前步骤和已处理数量，不显示虚假百分比。
- Acceptance：
  - 100 万字正文分析任务可查看进度、可暂停、可继续、可失败重试。

### R-AI-INIT-01 两阶段初始化

- Rule：作品 AI 初始化必须分为大纲分析和正文分析两个阶段。
- Behavior：
  - 第一步执行大纲分析。
  - 大纲分析完成并落库后，才允许执行已有正文分析。
  - 正文分析必须参考大纲分析结果。
  - 初始化完成后才开放正式续写能力。
  - 快速试写允许在未完成初始化时基于当前章节和大纲生成临时候选稿，但必须标记为“上下文不足，非正式智能续写”。
- Edge Case：
  - 无作品大纲：允许用户跳过大纲分析，但正文分析标记为“缺少大纲参考”。
  - 正文为空：只完成大纲分析，不开放正文记忆能力。
  - 用户仅执行快速试写：不得更新 Story Memory，不得触发正式记忆建议，不得作为正式续写质量验收依据。
- Acceptance：
  - 未完成大纲分析时，系统拒绝开始标准正文分析。
  - 未完成初始化时，正式续写不可用；快速试写候选稿必须显示上下文不足标记。

### R-AI-INIT-06A Quick Trial 降级试写

- Rule：初始化未完成时，正式续写不可用；系统可提供 Quick Trial 作为非正式降级试写。
- Behavior：
  - Quick Trial 只能使用当前章节、当前选区、用户输入的大纲或作品原始大纲等临时上下文。
  - Quick Trial 生成结果只能进入 Candidate Draft 或临时候选区。
  - Quick Trial 必须显著标记：“上下文不足，非正式智能续写”。
  - Quick Trial 不等于初始化完成，不改变正式续写必须初始化完成的主规则。
  - Quick Trial 不绕过 Human Review Gate。
- Edge Case：
  - Quick Trial 不更新 Story Memory。
  - Quick Trial 不生成正式 Memory Update Suggestion。
  - Quick Trial 不更新正式 StoryState。
  - Quick Trial 不作为正式续写质量验收依据。
- Acceptance：
  - 未完成初始化时，正式续写按钮不可用或提示先初始化。
  - Quick Trial 若可用，生成结果必须带非正式标记，且不会改变正式记忆、正式资产、正式正文。

### R-AI-INIT-02 大纲分析

- Rule：大纲分析必须提取小说总地图，并独立落库。
- Behavior：
  - 分析小说主线、阶段结构、核心冲突、主要人物、势力、世界观、关键伏笔、预期结局方向。
  - 分析结果保存为 AI 大纲分析结果。
  - AI 大纲分析结果不得覆盖用户原始作品大纲。
- Edge Case：
  - 大纲内容过短：生成低置信度分析并提示用户补充。
- Acceptance：
  - 大纲分析完成后刷新页面，分析结果仍可查看，用户原始大纲不变。

### R-AI-INIT-03 正文分析

- Rule：正文分析必须按章节或分段处理已有正文，并对照大纲结果。
- Behavior：
  - 支持分析前 30 万字、100 万字或更多正文。
  - 生成章节摘要、阶段摘要、卷摘要、全书当前进度摘要。
  - 生成人物状态、剧情事件、时间线、伏笔、设定、地点、风格画像。
  - 判断正文写到大纲哪个阶段、哪些剧情完成、哪些偏离、哪些伏笔已出现或未出现。
- Edge Case：
  - 单章过长：按分段分析后合并摘要。
  - 单章分析失败：允许跳过失败章节并继续后续章节。
- Acceptance：
  - 正文分析完成后，每个已分析章节均有摘要、状态与进度记录。

### R-AI-MEM-01 Story Memory 初始构建

- Rule：正文分析后必须形成 P0 最小可用 Story Memory 初始版本。
- Behavior：
  - P0 最小可用记忆包含章节摘要、全书当前进度摘要、主要角色状态、当前 Story State、基础伏笔候选、基础设定事实、向量索引。
  - 阶段摘要、卷摘要、完整角色卡、完整事件、完整地点、完整风格画像和完整剧情轨道进入 P1 深化。
  - AI 提取结果先进入分析结果或建议，不直接覆盖 V1.1 正式资产。
- Edge Case：
  - AI 结果与用户资产冲突：进入 Conflict Guard。
- Acceptance：
  - 初始化完成后可查看 P0 最小 Story Memory，并可用于单章候选续写。

### R-AI-MEM-02 Story State 当前故事状态锁

- Rule：系统必须维护当前故事状态，防止 AI 写崩。
- Behavior：
  - 记录当前地点、在场角色、角色状态、境界/能力、阵营关系、当前剧情阶段、未解伏笔、禁止事项。
  - Story State 必须进入 Context Pack。
- Edge Case：
  - Story State 缺失：续写任务提示上下文不足。
- Acceptance：
  - 审稿能检查候选稿是否违反当前 Story State。

### R-AI-MEM-03 Vector Recall 初始索引

- Rule：P0 必须完成向量索引初始构建能力。
- Behavior：
  - 支持章节切片、Embedding、向量入库、索引更新、索引重建。
  - 记录 chunk 与章节、段落位置关系。
  - 续写、审稿、改写前可召回相关旧剧情片段。
- Edge Case：
  - 向量索引未完成：Context Pack 降级，不阻断非召回类分析。
- Acceptance：
  - 给定当前写作任务，可召回相关历史片段及来源章节。

### R-AI-CTX-01 Context Pack

- Rule：每次 AI 续写、改写、审稿、规划前必须组装 Context Pack。
- Behavior：
  - 包含当前章节 / 选区上下文。
  - 包含当前卷摘要和最近章节摘要。
  - 包含 Story State。
  - 包含 Writing Task。
  - 包含全书摘要、角色卡、设定、伏笔。
  - 包含 RAG 召回片段。
  - 包含四层剧情轨道。
  - Style DNA 作为可选层。
  - Context Pack 必须记录到 Agent Trace。
- Edge Case：
  - 不同 AI 操作组装层级不同；续写包含完整层，改写可只包含选区上下文、角色卡、Style DNA。
- Acceptance：
  - 任意候选稿可追踪到生成时使用的 Context Pack。

### R-AI-CTX-02 Context Pack Token 优先级

- Rule：上下文超限时必须按优先级裁剪。
- Behavior：
  - 优先级顺序：当前章节 / 选区上下文 > 当前卷摘要和最近章节摘要 > Story State > Writing Task > 全书摘要 / 角色卡 / 设定 > RAG 召回片段 > Style DNA。
  - Context Pack 总 token 不超过模型上限的 80%。
  - RAG 召回片段优先保留相关性最高的片段。
  - 四层剧情轨道单独执行保底规则。
- Edge Case：
  - 裁剪导致 Writing Task 不完整：禁止执行生成。
- Acceptance：
  - 超限时裁剪结果可解释且可追踪。

### R-AI-CTX-03 四层剧情轨道保底

- Rule：Context Pack 中四层剧情轨道必须按独立优先级保底。
- Behavior：
  - 临近窗口优先级最高。
  - 当前小段落弧其次。
  - 当前卷弧再次。
  - 全文弧可以压缩，但不能完全缺失。
- Edge Case：
  - Token 极限不足：保留 Master Arc 摘要和 Immediate Window 核心信息。
- Acceptance：
  - 构造超长轨道时，裁剪结果仍包含 Master Arc。

### R-AI-CTX-04 Context Pack 组装服务

- Rule：后端提供统一 Context Pack 组装服务，所有需要上下文的 AI 能力共用。
- Behavior：
  - 输入包括 work_id、operation_type、chapter_id、选区范围、目标模型。
  - 输出包括上下文文本、各层级 token 明细、是否发生裁剪、引用来源列表。
  - 多章续写场景按章独立组装 Context Pack。
- Edge Case：
  - 缺少关键上下文：返回 blocked 状态与缺失项。
- Acceptance：
  - 不同 operation_type 返回不同层级的上下文。

### R-AI-PLAN-01 Writing Task

- Rule：正式续写前必须生成 Writing Task。
- Behavior：
  - 包含写作目标、必须包含内容、禁止内容、情绪基调、目标字数、关联剧情轨道。
  - Writing Task 由 Planner Agent 生成，用户可编辑或确认。
  - Reviewer Agent 审稿时检查候选稿是否符合 Writing Task。
- Edge Case：
  - 用户跳过章节计划：系统仍必须生成最小 Writing Task。
- Acceptance：
  - Writer Agent 不能在无 Writing Task 的情况下生成正式候选稿。

### R-AI-DRAFT-01 单章候选续写

- Rule：P0 支持基于 Context Pack 与 Writing Task 生成下一章候选稿。
- Behavior：
  - Writer Agent 生成候选稿。
  - 候选稿进入 Candidate Draft。
  - 候选稿不修改正式正文。
  - 生成后触发基础审稿。
- Edge Case：
  - 生成中断：保留已生成片段为临时候选，不进入正式候选版本。
- Acceptance：
  - 下一章候选稿可完成生成、审稿、接受或丢弃流程。

### R-AI-DRAFT-02 Candidate Draft 交互

- Rule：候选稿区必须支持人工确认门控。
- Behavior：
  - 候选稿展示来源、生成时间、字数、审稿摘要、版本关系。
  - 用户可接受、编辑后接受、插入、替换、丢弃、重新生成。
  - 候选稿被丢弃后进入最近丢弃列表，默认保留 24 小时。
  - 用户拒绝候选稿时可选择轻量拒绝理由，拒绝理由写入 Agent Trace。
  - P0 至少支持保存 reject_reason_text，可为空。
  - P0 可选支持 reject_reason_code，枚举方向包括 off_topic、style_mismatch、logic_conflict、too_ai_like、too_long、too_short、bad_rhythm、user_other。
  - P0 不做拒绝理由统计分析；P1 可扩展 reason_code 统计、质量分析与 Prompt 优化闭环。
- Edge Case：
  - 候选稿合并时发生正文版本冲突：走现有 409 冲突处理流程。
  - 用户未填写拒绝理由：系统仍允许丢弃，并记录空理由。
- Acceptance：
  - 候选稿可接受、可编辑后接受、可丢弃、可重新生成，拒绝理由可追踪。
  - 用户丢弃或拒绝候选稿时，系统允许填写拒绝理由；P0 至少能保存 reject_reason_text，未填写时记录空理由。

### R-AI-REVIEW-01 AI 审稿基础能力

- Rule：候选稿生成后应由 Reviewer Agent 审稿。
- Behavior：
  - 审稿维度包括人物一致性、设定冲突、时间线冲突、伏笔误用、风格漂移、AI 味、Writing Task 完成度、四层剧情轨道偏离。
  - 审稿结果结构化输出并显示在候选稿区。
- Edge Case：
  - 审稿调用超时或失败：候选稿标记为未审稿，P0 中仍可由用户手动决定是否使用。
- Acceptance：
  - 候选稿生成后可查看审稿摘要和问题列表。

***

## 10. P1：智能体工作流与剧情轨道

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

### R-AI-AGENT-02 Agent 职责

- Rule：每个 Agent 必须有明确职责。
- Behavior：
  - Memory Agent：大纲分析、正文分析、章节摘要、人物状态、剧情事件、伏笔、设定、时间线、风格特征提取与更新建议。
  - Planner Agent：当前进度分析、A/B/C 方向推演、章节计划、Writing Task、续写约束。
  - Writer Agent：续写正文、整章候选稿、改写、扩写、润色、对白优化。
  - Reviewer Agent：人物一致性、设定冲突、时间线冲突、伏笔误用、风格漂移、AI 味、任务完成度检查。
  - Rewriter Agent：根据审稿问题修订候选稿、降 AI 味、调整节奏、强化钩子和悬念。
- Edge Case：
  - Agent 输出越过职责边界：系统拒绝进入下一步。
- Acceptance：
  - Agent Trace 中可区分每个 Agent 的输入、输出和职责。

### R-AI-AGENT-03 Agent 权限矩阵

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

### R-AI-AGENT-04 Agent Trace

- Rule：每次智能体执行必须记录执行轨迹。
- Behavior：
  - 记录 trace_id、Agent、模型、Prompt 版本、Context Pack、召回片段、输出、审稿结果、用户决策。
  - 记录用户拒绝候选稿的理由。
  - 默认不记录 API Key。
  - 正文与 Prompt 全文记录遵循隐私设置。
- Edge Case：
  - Trace 写入失败：AI 任务不得进入 completed。
- Acceptance：
  - 用户可查看候选稿对应的生成轨迹和拒绝原因。

### R-AI-ARC-01 四层剧情轨道

- Rule：系统必须形成全文弧、卷/大段落弧、剧情波次、临近窗口四层剧情轨道。
- Behavior：
  - 四层轨道均进入 Context Pack。
  - 每层轨道记录层级、状态、目标、冲突、章节范围、下一步推进方向。
  - 四层轨道用于 A/B/C 方向推演、章节计划、单章续写、多章续写、自动续写停止条件、审稿检查。
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

### R-AI-PLAN-02 后续方向推演

- Rule：系统必须基于大纲、已有正文记忆和四层剧情轨道生成 A/B/C 后续方向。
- Behavior：
  - 每个方向包含剧情概要、主要冲突、伏笔使用、风险点、未来 3-5 章预估。
  - 方向不能凭空发散，必须引用当前剧情轨道。
  - 方向推演属于沙盒推演，用户不确认则不产生候选稿。
- Edge Case：
  - 用户跳过沙盒模式：使用默认方向，即当前剧情自然延伸。
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

### R-AI-DRAFT-03 候选稿多轮迭代

- Rule：候选稿支持基于用户反馈多轮重新生成或修订。
- Behavior：
  - 用户可输入反馈，如“节奏加快”“多用短句”“减少心理描写”。
  - 用户可选择预设反馈标签。
  - 新候选稿记录 parent_draft_id。
  - 修订最大轮次默认 3 轮。
- Edge Case：
  - 连续多轮失败：提示用户调整 Writing Task 或 Context Pack。
- Acceptance：
  - 候选稿版本关系可查看，最多修订轮次生效。

### R-AI-REVIEW-02 Rewriter Agent 修订

- Rule：Rewriter Agent 只能基于审稿问题修订候选稿。
- Behavior：
  - 支持局部修订、降低 AI 味、调整节奏、强化钩子和悬念。
  - 修订稿作为新候选稿版本。
  - 修订最多执行 3 轮，超过后标记为需要人工处理。
- Edge Case：
  - 修订后仍有严重冲突：流程停止，等待用户决策。
- Acceptance：
  - 修订不会直接改正式正文。

### R-AI-ASSET-01 AI Suggestion Store

- Rule：AI 后处理得到的人物、事件、伏笔、设定、时间线、摘要等结果必须先进入 AI 建议区。
- Behavior：
  - 建议状态包括 pending、accepted、rejected、edited、expired。
  - 建议默认 7 天未处理后标记 expired。
  - 用户采纳后才写入正式资产或正式 Story Memory。
- Edge Case：
  - 原资产已被用户手动修改：建议标记为可能冲突。
- Acceptance：
  - AI 提取人物后，不会自动写入正式人物卡。

### R-AI-ASSET-02 引用建议占位

- Rule：P1 阶段 AI 可以生成引用建议，但不要求完成正文内 @ 高亮、联想和 `chapter_mentions` 持久化交互。
- Behavior：
  - Memory Agent 或 Reviewer Agent 可针对人物、地点、事件、伏笔生成引用建议。
  - 引用建议进入 AI 建议区。
  - 用户可采纳、拒绝或编辑引用建议。
  - 采纳后的引用建议只作为结构化建议结果保存，不改变正文内联显示。
- Edge Case：
  - 引用目标不存在或同名：建议标记为需要用户确认目标实体。
- Acceptance：
  - P1 可查看并处理引用建议；正文中 @ 联想、高亮、悬停和 mentions 持久化仍属于 P2。

### R-AI-ASSET-03 Conflict Guard

- Rule：AI 建议更新用户手动维护资产时，必须显示对比界面。
- Behavior：
  - 展示本地正式资产与 AI 建议差异。
  - 用户可采纳、拒绝、编辑后采纳。
  - 决策前不得覆盖正式资产。
- Edge Case：
  - 多个建议修改同一资产：按创建时间或用户选择逐条处理。
- Acceptance：
  - AI 建议不能静默覆盖人物、设定、伏笔、时间线。

### R-AI-MEM-04 Story Memory 版本与回滚

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

## 11. P2：增强能力

### R-AI-DRAFT-04 多章续写

- Rule：系统支持用户指定续写 3 章、5 章或续写到当前小剧情结束。
- Behavior：
  - 按章生成候选稿、审稿、用户确认、记忆更新建议。
  - 每章之间必须更新临近窗口和 Story State。
  - 每章候选稿独立展示，用户逐章确认。
- Edge Case：
  - 某章审稿严重失败：队列暂停，等待用户处理。
- Acceptance：
  - 多章续写不会一次性直接合并多章正式正文。

### R-AI-DRAFT-05 受控自动连续续写队列

- Rule：自动连续续写必须放在 P2，且必须受控执行。
- Behavior：
  - 用户设定目标章数、目标字数或停止条件。
  - 系统逐章生成候选稿。
  - 每章审稿。
  - 每章可修订。
  - 不自动合并正式正文。
  - 自动续写停止后，已生成候选稿仍保留在候选稿区。
- Edge Case：
  - 达到指定章数、达到指定字数、当前剧情阶段结束、审稿发现严重冲突、伏笔提前揭示、连续修订失败、成本上限、模型失败、用户手动停止时，队列必须中断。
- Acceptance：
  - 自动续写队列停止时保留已生成候选稿和停止原因。

### R-AI-ENH-01 Style DNA

- Rule：系统可提取文风指纹用于约束续写和改写。
- Behavior：
  - 用户可上传或指定标杆正文。
  - 系统提取词频、句式、段落节奏、对白比例、心理描写比例、叙述视角。
  - Style DNA 进入 Context Pack 底层。
  - 续写和改写目标是风格一致，不是克隆。
- Edge Case：
  - 标杆文本过短：标记低置信度。
  - 未配置 Style DNA：跳过此层。
- Acceptance：
  - 配置 Style DNA 后，续写 Context Pack 包含 Style DNA 层。

### R-AI-CITE-01 Citation Link

- Rule：AI 候选稿使用前文设定、伏笔、角色状态或历史事件时，应标记来源。
- Behavior：
  - 候选稿中可展示引用来源。
  - 用户可点击查看引用章节、摘要或资产。
  - 引用进入候选稿元数据，不污染正文纯文本。
- Edge Case：
  - 引用章节不存在：标记为未知来源，不阻断候选稿使用。
- Acceptance：
  - 候选稿可查看至少一条历史依据来源。

### R-AI-CITE-02 @ 标签引用系统

- Rule：正文支持 `@人物`、`@地点`、`@事件`、`@伏笔` 等引用。
- Behavior：
  - 输入 `@` 弹出联想菜单。
  - 联想结果最多展示 10 条。
  - 选中的 `@实体` 在正文中高亮显示。
  - 悬停显示资产摘要。
  - 保存时写入 `chapter_mentions`。
  - AI 后处理可生成 @ 引用建议，但用户确认后才正式建立。
- Edge Case：
  - 被引用资产被删除：正文中的 @ 标记保持显示，悬停提示已删除。
  - 同名实体：必须让用户选择目标实体。
- Acceptance：
  - @ 联想、高亮、悬停和持久化引用均可验证。

### R-AI-ENH-02 Opening Agent / 签约向开篇助手

- Rule：Opening Agent 负责签约向开篇辅助，不自动创建正式章节。
- Behavior：
  - 用户可导入某平台多部参考小说前 1-3 章。
  - 系统总结平台开篇规律、钩子、节奏、冲突、爽点、章节结尾悬念。
  - 基于用户自己的题材、大纲、主角设定生成原创前三章候选稿。
  - 检查过度模仿风险。
  - 对前三章候选稿进行签约向审稿。
- Edge Case：
  - 用户不导入参考小说：Opening Agent 可基于通用规则辅助生成。
  - 参考文本版权来源不明：提示用户确认使用权限。
- Acceptance：
  - Opening Agent 只输出候选稿，不自动创建正式章节。

### R-AI-ENH-03 大纲辅助

- Rule：AI 可辅助大纲润色、扩写、章节细纲建议和下一章 Writing Task 建议。
- Behavior：
  - 输出进入候选建议。
  - 用户确认后才写入大纲草稿或 AI 建议区。
- Edge Case：
  - 用户手写大纲已有内容：AI 建议不得自动覆盖。
- Acceptance：
  - AI 大纲建议默认不修改正式作品大纲。

### R-AI-ENH-04 选区改写 / 润色

- Rule：用户选中正文片段后，可触发受控改写能力。
- Behavior：
  - 支持扩写、重写、缩写、润色、对白优化、降低 AI 味。
  - 输出进入候选替换区。
  - 用户确认后才替换选区草稿。
- Edge Case：
  - 选区为空：不显示选区改写能力。
- Acceptance：
  - 改写结果不会自动替换正式正文。

### R-AI-ENH-05 成本看板与分析看板

- Rule：P2 可提供 AI 成本看板和创作分析看板。
- Behavior：
  - 成本看板展示 provider、model、role、tokens、耗时、错误、成本、用户是否采纳。
  - 分析看板可展示写作统计、节奏分析、对话占比、高频词、风格一致性、AI 痕迹检测。
- Edge Case：
  - 成本估算缺少官方价格：使用用户配置单价。
- Acceptance：
  - 用户可查看作品级 AI 使用成本和基础分析指标。

***

## 12. 总体验收标准

V2.0 总体验收：

- [ ] V1.1 Local-First 保存链路未被 AI 改写。
- [ ] AI 不自动合并正式正文。
- [ ] AI 不自动覆盖正式资产。
- [ ] AI 不自动创建正式章节。
- [ ] AI 初始化两阶段流程可用。
- [ ] 初始化完成后才开放正式续写能力。
- [ ] Context Pack 可组装、可裁剪、可追踪。
- [ ] Candidate Draft 可生成、审稿、确认、丢弃。
- [ ] Agent Trace 可追踪模型、Prompt、上下文、输出和用户决策。
- [ ] AI 建议区与 Conflict Guard 可阻止资产静默覆盖。

### P0 DoD

- [ ] AI Settings 可配置 Kimi 与 DeepSeek。
- [ ] Provider 抽象支持 Kimi 和 DeepSeek，可通过配置切换。
- [ ] Model Router 按任务角色调用模型。
- [ ] Prompt 模板独立于代码管理，并绑定 schema。
- [ ] Output Validator 拒绝非法结构化输出。
- [ ] AI Job System 支持长任务与进度展示。
- [ ] 大纲分析完成并独立落库。
- [ ] 正文分析必须在大纲分析后执行。
- [ ] Story Memory 初始版本可查看。
- [ ] 向量索引初始构建可完成。
- [ ] Context Pack 组装含必要层级，按优先级裁剪。
- [ ] Writing Task 每次续写前生成。
- [ ] 单章续写生成候选稿，不进入正式正文。
- [ ] 候选稿可接受、编辑后接受、丢弃、重新生成。
- [ ] 拒绝候选稿有理由选择并记录。
- [ ] 候选稿审稿摘要可见。

### P1 DoD

- [ ] 5 Agent 工作流完整可用。
- [ ] Agent 权限矩阵通过测试。
- [ ] Memory Agent 初始化两阶段分析完成。
- [ ] Planner Agent A/B/C 方向推演可用。
- [ ] Writer Agent 候选稿生成可用。
- [ ] Reviewer Agent 审稿覆盖核心维度。
- [ ] Rewriter Agent 修订可用。
- [ ] 四层剧情轨道可落库并进入 Context Pack。
- [ ] 章节计划可生成。
- [ ] 候选稿多轮迭代可用。
- [ ] AI 建议区支持采纳、编辑、拒绝、过期。
- [ ] Conflict Guard 冲突保护可用。
- [ ] Story Memory 更新有版本与回滚。
- [ ] Agent Trace 可查询执行轨迹。

### P2 DoD

- [ ] 多章续写按章生成候选稿。
- [ ] 自动连续续写队列具备停止条件。
- [ ] Style DNA 可进入 Context Pack。
- [ ] Citation Link 可追踪来源。
- [ ] @ 标签引用可联想、高亮、悬停、持久化。
- [ ] Opening Agent 签约开篇分析与候选稿生成可用。
- [ ] 大纲辅助输出不自动覆盖正式大纲。
- [ ] 选区改写结果不自动替换正文。
- [ ] 成本看板可展示 AI 用量与成本。

***

## 13. 验收矩阵

| 模块 | 正常场景 | 边界场景 | 异常场景 | 持久化/恢复 |
|---|---|---|---|---|
| AI 基础设施 | Provider 切换、Prompt 模板加载、Job 执行 | Key 未配置 | Provider 超时、重试失败 | 调用日志可查、成本可追踪 |
| AI 初始化 | 两阶段分析、进度展示、结果落库 | 无大纲、无正文、重新分析单章 | 分析中断、跳过失败章节 | 已完成阶段不重复执行 |
| Story Memory | 初始记忆构建、状态锁生成 | 章节过长、部分摘要缺失 | Memory 更新冲突 | 版本可查、可回滚 |
| Vector Recall | 切片、Embedding、Top-K 召回 | 索引未完成 | 索引构建失败 | 可重建索引 |
| Context Pack | 完整组装、按优先级裁剪 | Token 超限、Style DNA 缺失 | 缺关键上下文 blocked | Trace 可查看上下文 |
| 单章续写 | 生成候选稿、审稿、确认 | 生成中断、候选稿编辑后接受 | 模型失败、空输出 | 候选稿保留与恢复 |
| 智能体工作流 | 完整 5 Agent 流程 | 某 Agent 跳过或降级 | 审稿不通过次数超限 | Agent Trace 可查 |
| 审稿与修订 | 核心维度审稿、自动修订 | 无需修订、修订耗尽 | 审稿超时 | 修订版本关系可查 |
| 剧情轨道 | 四层轨道构建、进入 Context Pack | 不分卷作品、轨道缺层 | 轨道与正文冲突 | 刷新后轨道保持 |
| AI 建议区 | 建议分类展示、采纳、编辑、拒绝 | 建议过期、重复建议 | Conflict Guard 冲突 | 决策记录可查 |
| 自动续写 | 逐章生成候选稿 | 达到章数/字数/阶段结束 | 严重冲突、成本超限、模型失败 | 已生成候选稿保留 |
| @ 引用系统 | @ 联想、高亮、悬停 | 资产删除、同名实体 | mentions 写入失败 | 刷新后引用关联保持 |
| Opening Agent | 参考文分析、前三章候选稿 | 无参考文 | 过度模仿风险 | 候选稿与审稿报告保留 |

***

## 14. 默认参数与待确认项

### 14.1 默认参数

| 参数 | 默认值 |
|---|---|
| 分析/规划/审稿模型 | Kimi |
| 写作/修订模型 | DeepSeek |
| 全书摘要 token 上限 | 500 tokens |
| 卷摘要 token 上限 | 800 tokens |
| 阶段摘要 token 上限 | 1000 tokens |
| 章节摘要 token 上限 | 200 tokens |
| RAG 召回 Top-K | 5 |
| Context Pack 总 token 上限 | 模型上限的 80% |
| 候选稿最近丢弃保留时间 | 24 小时 |
| AI 建议过期时间 | 7 天 |
| 修订最大轮次 | 3 轮 |
| 自动续写连续修订失败阈值 | 3 次 |
| 章节后处理管道 | 默认串行 |
| @ 引用联想结果上限 | 10 条 |

### 14.2 待确认项

1. P0 是否必须支持流式输出，或先使用非流式返回。
2. Vector DB 采用本地 SQLite 扩展、独立本地库，还是文件型向量索引。
3. API Key 的最终存储方式。
4. 自动续写队列是否严格放入 P2，还是 P1 后期灰度。
5. Citation Link 以候选稿元数据实现，还是作为后续正文标注能力实现。
6. @ 引用系统先做 AI 建议态，还是直接支持正文交互。
7. Agent Trace 是否默认保存完整 Prompt 与完整 Context Pack，还是默认只保存摘要、hash 和引用 ID。
8. P0 审稿失败时，候选稿是否允许用户强制接受。
