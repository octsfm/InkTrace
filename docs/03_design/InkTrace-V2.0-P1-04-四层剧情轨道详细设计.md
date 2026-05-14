# InkTrace V2.0-P1-04 四层剧情轨道详细设计

版本：v1.1 / P1 模块级详细设计候选冻结版
状态：候选冻结
所属阶段：InkTrace V2.0 P1
设计范围：四层剧情轨道（Master Arc / Volume Arc / Sequence Arc / Immediate Window）的数据模型、状态机、构建策略、降级规则、Agent 读取边界、ContextPack 集成

合并说明：本文档以 `_001.md` v1.0 为主版本（与 P1 总纲一致的 Master / Volume / Sequence / Immediate Window 四层正式命名），吸收无后缀旧稿中的 quality_level、placeholder 占位模板、UI 展示边界等具体设计，经命名统一、状态体系统一、裁剪规则统一后形成。`_001.md` 和无后缀旧稿均被完全吸收，不再单独维护。

依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`
- `docs/07_overview/InkTrace-V2.0-概要设计说明书.md`
- `docs/02_architecture/InkTrace-V2.0-架构设计说明书.md`
- `docs/03_design/InkTrace-V2.0-P1-详细设计总纲.md`
- `docs/03_design/InkTrace-V2.0-P1-01-AgentRuntime详细设计.md`
- `docs/03_design/InkTrace-V2.0-P1-02-AgentWorkflow详细设计.md`
- `docs/03_design/InkTrace-V2.0-P1-03-五Agent职责与编排详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-04-StoryMemory与StoryState详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-06-ContextPack详细设计.md`

说明：本文档只冻结 P1 四层剧情轨道设计。不写代码，不生成开发计划，不拆开发任务，不处理 Git。P0 详细设计正式路径为 `docs/03_design/V2/InkTrace-V2.0-P0-...`，不视为错误路径。

---

## 一、文档定位与设计范围

### 1.1 文档定位

本文档是 InkTrace V2.0-P1 的第四个模块级详细设计文档，仅覆盖 P1 四层剧情轨道系统。

P1-04 的目标是冻结四层轨道的数据模型、状态机、构建策略、降级规则，以及轨道与 StoryMemory / StoryState / ContextPack / 五 Agent / Direction Proposal / Conflict Guard 的边界关系。

本文档是 P1-05（方向推演与章节计划）、P1-06（多轮 CandidateDraft）、P1-08（ConflictGuard）、P1-11（API/前端集成）的输入基线。

### 1.2 设计范围

本模块覆盖：

- Master Arc（全文弧）：数据结构、字段、构建来源、维护者、状态机。
- Volume Arc（卷弧）：数据结构、字段、构建来源、维护者、状态机。
- Sequence Arc（序列弧）：数据结构、字段、构建来源、维护者、状态机。
- Immediate Window（临近窗口）：数据结构、字段、构建来源、动态组装规则。
- 四层轨道之间的父子关系与继承规则。
- 四层轨道的统一状态机（ArcStatus）与 quality_level 体系。
- 轨道缺失时的 blocked / degraded / ready 判定规则。
- 轨道 stale 时的处理规则。
- 初始化阶段轨道的生成与占位策略（placeholder / minimal / complete 三级质量体系）。
- 轨道与 StoryMemory / StoryState 的读写边界。
- 轨道与 ContextPack 的集成规则（source_type、priority、裁剪顺序、required 标记）。
- 轨道与 Memory Agent / Planner Agent / Writer Agent / Reviewer Agent / Rewriter Agent 的读写边界。
- 轨道与 Direction Proposal / ChapterPlan 的约束关系。
- 轨道与 Conflict Guard 的冲突检测方向。
- 轨道与 P1-UI / DESIGN.md 的展示关系。

### 1.3 不覆盖范围

P1-04 不覆盖：

- Direction Proposal 算法（属于 P1-05）。
- ChapterPlan 完整数据结构（属于 P1-05）。
- Conflict Guard 完整规则矩阵（属于 P1-08）。
- StoryMemory Revision 数据结构（属于 P1-09）。
- API / DTO / 前端集成细节（属于 P1-11）。
- 剧情轨道可视化拖拽面板（属于 P2）。
- 剧情轨道图谱/关系图（属于 P2）。
- 轨道的自动检测和自动重新分析（属于 P2）。
- 跨作品轨道对比分析（属于 P2）。
- 正文 token streaming。
- AI 自动 apply / 自动写正式正文。
- 不写代码。

### 1.4 与 P1 总纲的关系

P1 总纲 §6 已冻结四层轨道的定义、职责边界、数据来源、保底策略。P1-04 必须直接继承以下冻结结论：

1. 四层轨道为：Master Arc → Volume Arc → Sequence Arc → Immediate Window。
2. Master Arc 缺失 → ContextPack blocked。
3. Volume / Sequence / Immediate Window 缺失 → ContextPack degraded + warning_codes。
4. Master Arc 由 Memory Agent 在初始化时构建，Planner Agent 维护。
5. Volume Arc 由 Planner Agent 在方向选择后构建/更新。
6. Sequence Arc 由 Planner Agent 在章节计划中构建/维护。
7. Immediate Window 由 ContextPack 构建时动态组装，不持久化。
8. 四层轨道全部进入 ContextPack 作为最高优先级约束层。
9. Token 裁剪优先级：Immediate Window（最高保留）→ Sequence Arc → Volume Arc → Master Arc（最后裁剪，可压缩不可缺失）。
10. 轨道偏离 → Conflict Guard warning 或 blocking（视偏离程度，P1-08 冻结）。
11. P1 只做结构化轨道与上下文供给，不做可视化面板。

---

## 二、四层剧情轨道总体模型

### 2.1 四层轨道定义

| 层级 | 名称 | 覆盖范围 | 核心语义 | 持久化 |
|---|---|---|---|---|
| L1 | Master Arc（全文弧） | 全书 | 终极目标、最终冲突、主线阶段、终局约束 | 是 |
| L2 | Volume Arc（卷弧） | 当前卷/大段落（通常 10-30 章） | 阶段目标、核心矛盾、高潮节点、收束条件 | 是 |
| L3 | Sequence Arc（序列弧） | 10-20 章 | 剧情波次目标、关键事件、反转点、爽点 | 是 |
| L4 | Immediate Window（临近窗口） | 前 10 章摘要 + 当前章 | 近期上下文、角色当前状态、场景细节、上一章钩子 | 否（每次构建时动态组装） |

### 2.2 命名冲突与映射说明

旧稿中曾出现 `Master / Volume / Chapter / Scene` 四层命名。本版统一为与 P1 总纲一致的正式口径，旧稿中的 Chapter Arc 和 Scene Arc 按以下方式处理：

| 旧稿名称 | 最终正式处理 |
|---|---|
| Master Arc | 保留，作为 L1 正式层 |
| Volume Arc | 保留，作为 L2 正式层 |
| Chapter Arc | **不作为正式持久化轨道层**。其语义（章节目标/冲突/节拍）并入 Sequence Arc 与 P1-05 ChapterPlan 的映射关系。Sequence Arc 的 `key_events` 可表达章级约束，ChapterPlan 的 `chapter_goal` / `required_beats` 可表达章节级计划 |
| Scene Arc | **不作为正式持久化轨道层**。其语义（场景节拍/情绪/视角）并入 Immediate Window 的 `scene_details` / `SceneMoment` 子结构。不单独进入 P1-04 四层层级树 |

如果后续 P2 需要引入独立的 Chapter 级或 Scene 级持久化轨道，以 P2 设计为准。

### 2.3 命名对齐说明

P1 总纲 §6.1 使用 `Volume/Act Arc`、`Sequence Arc`、`Immediate Window` 作为正式名称。本文档简称为 `Volume Arc`、`Sequence Arc`、`Immediate Window`，语义完全一致，不引入新的层级名称。

### 2.4 四层轨道的设计哲学

四层剧情轨道不是"故事大纲的另一种写法"，而是**结构化的叙事约束层**：

- **Master Arc** 回答"这个故事最终要到达哪里"——是所有 Agent 的叙事北极星。
- **Volume Arc** 回答"当前阶段要完成什么"——是 Writer Agent 的阶段边界。
- **Sequence Arc** 回答"接下来 10-20 章的具体剧情循环"——是 Planner Agent 和 Writer Agent 的近期约束。
- **Immediate Window** 回答"刚刚发生了什么、现在是什么状态"——是 Writer Agent 的直接上下文。

四层轨道从宏观到微观逐层收敛，下层不能违背上层，上层通过下层落地。

### 2.5 核心原则

1. Master Arc 缺失默认 blocked。
2. Volume / Sequence / Immediate Window 缺失默认 degraded，必须带 warning_codes。
3. 轨道是结构化文本与引用，不是复杂知识图谱。
4. 轨道读取与交接走 safe_ref / result_ref，不透传完整正文。
5. 轨道状态不自动修复，不自动写正式正文。
6. 占位轨道（placeholder）不等于 ready，不得在 ContextPack 中伪装为有效数据。

---

## 三、Master Arc 详细设计

### 3.1 职责

Master Arc 是全书级别的主线轨道，定义作品从开篇到终局的核心叙事方向。

它不替代用户大纲，而是从用户大纲 + StoryMemory 中**提取**出的结构化主线约束，供 Agent 在执行写作/规划/审稿任务时参照。

### 3.2 数据模型

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `master_arc_id` | string | 是 | 唯一标识，如 `ma_{work_id}` |
| `work_id` | string | 是 | 所属作品 ID |
| `arc_title` | string | 是 | 主线标题，max 100 字符 |
| `arc_logline` | string | 是 | 主线一句话摘要，max 200 字符 |
| `status` | ArcStatus | 是 | 轨道状态 |
| `quality_level` | enum | 是 | 内容质量：placeholder / minimal / complete |
| `version` | int | 是 | 版本号（自增，每次更新 +1） |
| `ultimate_goal` | string | 是 | 终极目标（主角最终要达成什么），max 500 字符 |
| `final_conflict` | string | 是 | 最终冲突（主角 vs 什么），max 500 字符 |
| `protagonist_motivation` | string | 是 | 主角长期动机（驱动全书行动的核心原因），max 300 字符 |
| `current_stage` | string | 是 | 当前主线阶段描述（如"第二幕中段：主角深入敌营"），max 300 字符 |
| `stage_position` | object | 否 | 结构化阶段位置：`{ "act": 2, "stage": "mid", "progress_pct": 55 }` |
| `endgame_foreshadows` | string[] | 是 | 终局伏笔列表（指向终局的关键伏笔 ID 或描述） |
| `main_antagonist` | string | 是 | 主要对手/阻力（可为人、势力、环境、命运），max 200 字符 |
| `core_theme` | string | 是 | 核心主题（1-2 句话），max 300 字符 |
| `tone_direction` | string | 否 | 全书基调方向（如"悬疑渐进的沉郁→终局的高昂"），max 200 字符 |
| `hard_constraints` | string[] | 否 | 强约束（不得违背的叙事边界） |
| `key_milestones` | string[] | 否 | 关键里程碑 |
| `forbidden_outcomes` | string[] | 否 | 禁止的叙事结果（如"主角不能死亡""不能揭示XX身份"） |
| `source_initialization_id` | string | 是 | 来源初始化 ID |
| `source_outline_ref` | string | 否 | 来源大纲引用 |
| `source_refs` | string[] | 否 | 来源引用列表（大纲/正文/分析记录） |
| `warning_codes` | string[] | 否 | 风险码 |
| `built_from_text_inference` | bool | 否 | 是否从正文推断（无用户大纲时为 true） |
| `stale_status` | string | 是 | fresh / stale |
| `stale_reason` | string | 否 | stale 原因 |
| `built_by` | string | 是 | 构建者：memory_agent / planner_agent / user_edited |
| `last_updated_by` | string | 是 | 最后更新者 |
| `created_at` | string | 是 | 创建时间 |
| `updated_at` | string | 是 | 更新时间 |
| `request_id` | string | 否 | 请求追溯 ID |
| `trace_id` | string | 否 | 全链路追踪 ID |

### 3.3 构建来源

Master Arc 由 **Memory Agent** 在初始化阶段构建，来源包括：
1. 用户作品大纲（`OutlineAnalysisResult`）
2. 已确认章节的正文分析结果（`ChapterAnalysisResult`）
3. 初始 StoryMemory 的 `global_summary` 和 `plot_threads`
4. 用户手动输入的 Master Arc（如果用户提供）

构建优先级：用户手动输入 > Memory Agent 从大纲提取 > 从正文推断。

当无用户大纲时，Master Arc 仍可从正文推断构建，但标记 `built_from_text_inference = true`，初始状态为 `degraded`（warning: `master_arc_inferred_without_outline`）。

### 3.4 维护者

- **初始化**：Memory Agent 构建初始版本（`built_by = memory_agent`）。
- **后续维护**：Planner Agent 在方向推演和章节计划更新时，如果发现正文进展与 Master Arc 出现重大偏差，生成 Master Arc 更新建议（`built_by = planner_agent`，需用户确认）。
- **用户手动编辑**：`built_by = user_edited`（P1 支持通过 UI 编辑，但非 P1 核心交互）。

### 3.5 读取要求

1. Writer / Planner Agent 必须可读取 Master Arc 摘要。
2. ContextPack 裁剪时，Master Arc 摘要不得被裁剪到不可用的程度（至少保留 `ultimate_goal` + `current_stage`，约 100 tokens）。

---

## 四、Volume Arc 详细设计

### 4.1 职责

Volume Arc 是当前卷/大段落（通常 10-30 章）的阶段轨道。它定义当前阶段的叙事边界——从哪里开始、要达成什么、在哪里收束。

一个作品可以有多个 Volume Arc（每个卷一个），但同一时间只有一个"当前生效"的 Volume Arc。

### 4.2 数据模型

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `volume_arc_id` | string | 是 | 唯一标识，如 `va_{work_id}_{volume_no}` |
| `work_id` | string | 是 | 所属作品 ID |
| `master_arc_id` | string | 是 | 关联的 Master Arc ID |
| `volume_no` | int | 是 | 卷序号（1, 2, 3...） |
| `volume_title` | string | 否 | 卷标题，max 100 字符 |
| `status` | ArcStatus | 是 | 轨道状态 |
| `quality_level` | enum | 是 | 内容质量：placeholder / minimal / complete |
| `version` | int | 是 | 版本号 |
| `core_conflict` | string | 是 | 本卷核心矛盾，max 500 字符 |
| `stage_goal` | string | 是 | 本卷阶段目标（主角在本卷结束时要达到什么状态），max 500 字符 |
| `main_opposition` | string | 是 | 本卷主要阻力/对手，max 200 字符 |
| `climax_description` | string | 是 | 本卷高潮节点描述，max 500 字符 |
| `resolution_condition` | string | 是 | 本卷收束条件（什么事件发生后本卷结束），max 300 字符 |
| `stage_turning_points` | string[] | 否 | 本卷阶段转折点 |
| `stage_open_loops` | string[] | 否 | 本卷未闭环线索 |
| `current_position` | string | 否 | 当前在本卷中的位置描述，max 200 字符 |
| `chapter_range` | object | 是 | 章节范围：`{ "from_chapter": 1, "to_chapter_estimate": 15 }` |
| `key_characters` | string[] | 是 | 本卷关键角色 |
| `foreshadow_planted` | string[] | 否 | 本卷新埋伏笔 |
| `foreshadow_resolved` | string[] | 否 | 本卷回收的伏笔 |
| `forbidden_items` | string[] | 否 | 本卷禁止出现的叙事元素 |
| `derived_from_direction_id` | string | 否 | 从哪个 DirectionProposal 生成 |
| `source_refs` | string[] | 否 | 来源引用列表 |
| `warning_codes` | string[] | 否 | 风险码 |
| `stale_status` | string | 是 | fresh / stale |
| `stale_reason` | string | 否 | stale 原因 |
| `built_by` | string | 是 | 构建者 |
| `last_updated_by` | string | 是 | 最后更新者 |
| `created_at` | string | 是 | 创建时间 |
| `updated_at` | string | 是 | 更新时间 |

### 4.3 构建来源

Volume Arc 由 **Planner Agent** 在用户选择方向后构建，来源包括：
1. 用户选择的 DirectionProposal 摘要
2. Master Arc 约束
3. 当前 StoryState 的 `current_position_summary`
4. 用户手动输入的卷结构（如果有）

### 4.4 维护者

- **构建**：Planner Agent（`built_by = planner_agent`）。
- **更新**：每次章节计划更新或方向推演时，Planner Agent 评估 Volume Arc 是否需要刷新。
- **用户手动编辑**：`built_by = user_edited`。

### 4.5 多卷管理

一个作品可以有多个 Volume Arc（每个卷一个）。当前生效的 Volume Arc 通过 `chapter_range` 与当前章节位置匹配确定。当章节进展超出 `chapter_range.to_chapter_estimate` 时，触发新 Volume Arc 的构建建议。

### 4.6 缺失策略

Volume Arc 缺失不直接 blocked，默认 degraded，返回 `volume_arc_missing`。

---

## 五、Sequence Arc 详细设计

### 5.1 职责

Sequence Arc 是 10-20 章级别的剧情波次轨道。它定义了一个剧情循环（通常包含"铺垫→发展→高潮→收束"）的具体路径。

一个 Volume 内通常包含 1-2 个 Sequence。

### 5.2 数据模型

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `sequence_arc_id` | string | 是 | 唯一标识，如 `sa_{work_id}_{seq_no}` |
| `work_id` | string | 是 | 所属作品 ID |
| `volume_arc_id` | string | 是 | 关联的 Volume Arc ID |
| `master_arc_id` | string | 是 | 关联的 Master Arc ID（冗余，便于直接查询） |
| `seq_no` | int | 是 | 序列序号（在当前 Volume 内） |
| `status` | ArcStatus | 是 | 轨道状态 |
| `quality_level` | enum | 是 | 内容质量：placeholder / minimal / complete |
| `version` | int | 是 | 版本号 |
| `sequence_goal` | string | 是 | 本序列目标（这 10-20 章要完成什么），max 500 字符 |
| `key_events` | SequenceEvent[] | 是 | 关键事件列表（按顺序） |
| `turning_points` | string[] | 是 | 反转点（剧情走向发生变化的节点），max 3 个 |
| `climax_chapter_estimate` | int | 否 | 预估高潮所在章节号 |
| `satisfaction_beats` | string[] | 否 | 爽点/满足感节点（读者情绪高点） |
| `resolution_chapter_estimate` | int | 是 | 预估收束章节号 |
| `chapter_range` | object | 是 | `{ "from_chapter": 11, "to_chapter_estimate": 25 }` |
| `foreshadow_arrangement` | string[] | 否 | 本序列内的伏笔安排 |
| `forbidden_items` | string[] | 否 | 本序列禁止的叙事元素 |
| `required_beats` | string[] | 否 | 必须出现的节拍（章级约束方向） |
| `derived_from_chapter_plan_id` | string | 否 | 从哪个 ChapterPlan 生成 |
| `source_refs` | string[] | 否 | 来源引用列表 |
| `warning_codes` | string[] | 否 | 风险码 |
| `stale_status` | string | 是 | fresh / stale |
| `stale_reason` | string | 否 | stale 原因 |
| `built_by` | string | 是 | 构建者 |
| `last_updated_by` | string | 是 | 最后更新者 |
| `created_at` | string | 是 | 创建时间 |
| `updated_at` | string | 是 | 更新时间 |

### 5.3 SequenceEvent

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `event_id` | string | 是 | 事件 ID |
| `event_order` | int | 是 | 事件序号 |
| `event_name` | string | 是 | 事件名称，max 100 字符 |
| `description` | string | 是 | 事件描述，max 300 字符 |
| `event_type` | string | 是 | setup / development / climax / resolution / twist |
| `estimated_chapter` | int | 否 | 预估发生在第几章 |
| `involved_characters` | string[] | 否 | 涉及角色 |
| `foreshadow_triggers` | string[] | 否 | 触发/揭示的伏笔 |
| `arc_impact` | string | 否 | 对主线的影响描述，max 200 字符 |

### 5.4 构建来源

Sequence Arc 由 **Planner Agent** 在章节计划确认后构建，来源包括：
1. 用户确认的 ChapterPlan
2. Volume Arc 约束
3. Master Arc 约束
4. 当前 StoryState

### 5.5 维护者

- **构建**：Planner Agent（`built_by = planner_agent`）。
- **更新**：每次章节计划更新时评估是否需要刷新。
- 当章节进展超出 `chapter_range.to_chapter_estimate` 时，触发新 Sequence Arc 的构建。

### 5.6 缺失策略

Sequence Arc 缺失默认 degraded，返回 `sequence_arc_missing`；Writer 可在策略允许下继续。

---

## 六、Immediate Window 详细设计

### 6.1 职责

Immediate Window 是"刚刚发生了什么 + 现在是什么状态"的近期上下文窗口。它是 Writer Agent 的直接上下文来源，确保 AI 生成的内容与最近章节保持连贯。

**Immediate Window 不持久化**——每次 ContextPack 构建时从 StoryMemory 动态组装。

### 6.2 数据结构

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `window_id` | string | 是 | 本次构建的唯一 ID（如 `iw_{context_pack_id}`） |
| `work_id` | string | 是 | 所属作品 ID |
| `context_pack_id` | string | 是 | 关联的 ContextPack ID |
| `status` | ArcStatus | 是 | 本次构建的状态 |
| `quality_level` | enum | 否 | 本次构建质量：minimal / complete（不持久化，仅描述当前窗口质量） |
| `recent_chapters_summary` | ChapterContextItem[] | 是 | 前 10 章摘要（每章 1-2 句） |
| `recent_3_chapters_detail` | ChapterContextItem[] | 是 | 前 3 章精简内容（每章 3-5 句） |
| `current_chapter_context` | CurrentChapterContext | 是 | 当前章节上下文 |
| `previous_chapter_hook` | string | 是 | 上一章结尾钩子，max 300 字符 |
| `character_current_states` | CharacterMoment[] | 是 | 当前出场角色的即时状态 |
| `active_plot_threads` | string[] | 是 | 当前活跃的剧情线索 |
| `scene_details` | SceneMoment[] | 否 | 当前场景细节（仅当章节包含明确场景切换时。此字段吸收旧稿 Scene Arc 的场景级语义） |
| `stale_status` | string | 是 | fresh / stale（由 StoryMemory/StoryState 的 stale 状态决定） |
| `assembled_at` | string | 是 | 组装时间 |

### 6.3 子结构

**ChapterContextItem**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `chapter_id` | string | 是 | 章节 ID |
| `chapter_no` | int | 是 | 章节序号 |
| `title` | string | 是 | 章节标题 |
| `summary` | string | 是 | 摘要（1-3 句），max 200 字符 |
| `key_event` | string | 否 | 本章关键事件，max 100 字符 |

**CurrentChapterContext**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `chapter_id` | string | 是 | 当前章节 ID |
| `chapter_no` | int | 是 | 当前章节序号 |
| `title` | string | 是 | 章节标题 |
| `content_summary` | string | 是 | 已写内容概要（非全文），max 500 字符 |
| `writing_position` | string | 是 | 写作位置描述（如"章节中段，主角刚进入灯塔"），max 200 字符 |
| `unresolved_in_chapter` | string[] | 否 | 本章内尚未解决的线索 |

**CharacterMoment**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `character_name` | string | 是 | 角色名 |
| `current_status` | string | 是 | 当前状态摘要（如"在灯塔内部探索"），max 100 字符 |
| `emotional_state` | string | 否 | 当前情绪，max 50 字符 |
| `location` | string | 否 | 当前位置 |
| `last_action` | string | 否 | 最近动作，max 100 字符 |

**SceneMoment**（吸收旧稿 Scene Arc 的场景节拍语义）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `location` | string | 是 | 场景地点 |
| `time_of_day` | string | 否 | 时间 |
| `atmosphere` | string | 否 | 氛围，max 100 字符 |
| `characters_present` | string[] | 是 | 在场角色 |
| `emotional_tone` | string | 否 | 情绪基调，max 50 字符 |
| `pov_hint` | string | 否 | 视角提示 |
| `reveal_points` | string[] | 否 | 信息揭示点 |

### 6.4 构建来源

Immediate Window 在每次 ContextPack 构建时动态组装，来源为：
1. StoryMemory 的 `chapter_summaries`（取最近 10 章）
2. StoryState 的 `current_position_summary`、`active_characters`、`active_locations`
3. 当前章节的 `content`（仅取标题 + 结构摘要，不取全文）

### 6.5 持久化规则

Immediate Window **不持久化**。每次 ContextPack 构建时重新组装。其 `window_id` 与 `context_pack_id` 绑定，仅在 ContextPackSnapshot 的上下文中存在。

### 6.6 缺失策略

Immediate Window 缺失/空 → **degraded**，不 blocked。因为 Immediate Window 不持久化，缺失属于预期内的降级情况。SceneMoment 子结构为空时不影响 Immediate Window 的整体可用性。

---

## 七、四层轨道关系与继承规则

### 7.1 层级关系

```text
Master Arc（全书）
  └── Volume Arc #1（卷1）
  │     └── Sequence Arc #1（序列1）
  │     └── Sequence Arc #2（序列2）
  └── Volume Arc #2（卷2）
        └── Sequence Arc #3（序列3）
        └── Sequence Arc #4（序列4）

Immediate Window（每次 ContextPack 构建时动态组装，不属于持久化层级树）
```

### 7.2 继承/约束规则

| 规则编号 | 规则 | 说明 |
|---|---|---|
| ARC-INHERIT-01 | 下层不得违背上层 | Sequence Arc 的 `sequence_goal` 必须在 Volume Arc 的 `stage_goal` 范围内；Volume Arc 的 `stage_goal` 必须服务于 Master Arc 的 `ultimate_goal` |
| ARC-INHERIT-02 | 上层约束必须在下层可追踪 | Volume Arc 的 `foreshadow_planted` 应在 Sequence Arc 的 `foreshadow_arrangement` 中找到对应安排 |
| ARC-INHERIT-03 | `forbidden_items` 逐层累加 | 下层继承上层的 `forbidden_items`，并可追加本层的禁止项。下层新增细节通过 `source_refs` 与 `warning_codes` 保留可解释性 |
| ARC-INHERIT-04 | `chapter_range` 连续不重叠 | 同一 Volume 内的 Sequence 的 `chapter_range` 必须连续且不重叠 |
| ARC-INHERIT-05 | 上层 stale 时下层默认 stale | Master Arc stale → 所有 Volume/Sequence Arc stale；Volume Arc stale → 其下 Sequence Arc stale |
| ARC-INHERIT-06 | Immediate Window 独立判定 | Immediate Window 的 stale 由当前 StoryMemory/StoryState 的 stale 状态独立判定，不继承上层轨道 stale |
| ARC-INHERIT-07 | 强约束冲突时上层优先 | Master Arc 的 `hard_constraints` 优先级高于 Volume/Sequence 的约束。局部表达细节下层优先（如 Sequence 对本序列最具体）。不自动执行冲突合并，由 ConflictGuard / user_action 处理 |

### 7.3 冲突时的仲裁

当 Planner Agent 或 Reviewer Agent 发现下层轨道与上层轨道不一致时：
- 记录为 ArcDeviation（轨道偏离）。
- 偏离类型和严重程度由 Conflict Guard（P1-08）处理。
- P1-04 只负责提供轨道数据供 Conflict Guard 对比，不负责裁决。

---

## 八、轨道状态机与生命周期

### 8.1 ArcStatus 统一枚举

四层轨道统一使用以下状态枚举（此枚举为 P1-04 正式状态体系）：

| 状态 | 含义 | ContextPack 影响 | 适用层级 |
|---|---|---|---|
| `pending` | 尚未构建或构建中 | 不可用于 ContextPack | L1-L4 |
| `ready` | 已构建，数据有效 | 可作为 ContextPack 有效输入 | L1-L4 |
| `degraded` | 已构建但数据不完整或有警告 | ContextPack 标记 degraded + warning_codes | L2-L4 |
| `stale` | 底层 StoryMemory/StoryState 过期导致轨道可能不准确 | ContextPack 标记 degraded（L1 stale 时 blocked） | L1-L4 |
| `failed` | 构建失败 | 不可用于 ContextPack | L1-L4 |
| `empty` | 无可提取内容（如无大纲无正文） | 不可用于 ContextPack | L1-L4 |

### 8.2 quality_level（内容质量，与 ArcStatus 正交）

quality_level 描述轨道内容的**完整度**，与 ArcStatus（生命周期状态）正交：

| quality_level | 含义 | 判定条件 |
|---|---|---|
| `placeholder` | 占位：关键字段缺失或仅有机推断值 | 初始化未完成、信息不足、仅有机推断 |
| `minimal` | 最小可用：必填字段满足，可用于降级场景 | 必填字段齐全但可选字段不足 |
| `complete` | 完整：大部分字段已填充，可稳定用于 ContextPack / Agent | 必填字段齐全 + 关键可选字段已填充 |

规则：
- `quality_level` 不替代 ArcStatus。ArcStatus 表示生命周期状态（能不能用），quality_level 表示内容质量（好用不好用）。
- `placeholder` 轨道不得标记为 `ready`（必须为 `degraded` 或 `pending`）。
- 初始化完成后可从 `placeholder` → `minimal`；Planner Agent / Memory Agent 后续补充数据后可升级为 `complete`。
- `placeholder` 轨道在 ContextPack 中必须附带 `arc_placeholder_only` warning。

### 8.3 旧状态映射

旧稿中曾出现 `draft / active / stale / archived` 状态命名。对应关系如下：

| 旧状态 | 正式 ArcStatus | 说明 |
|---|---|---|
| draft | pending | 初建未启用 |
| active | ready | 可用于 ContextPack 与 Agent 读取 |
| stale | stale | 语义一致，直接采用 |
| archived | 不进入 P1-04 主状态 | 归档属于 P2 或版本归档能力，不在 P1 范围 |

### 8.4 状态流转

```text
pending ──────→ ready ──────→ stale ──→ ready（重新分析/刷新）
   │               │             │
   └──→ failed     └──→ degraded └──→ failed（无法恢复）
   │               │             │
   └──→ empty      └──→ ready（补充数据后）
```

### 8.5 生命周期触发事件

| 事件 | 影响的轨道层 | 动作 |
|---|---|---|
| 初始化完成 | Master Arc | Memory Agent 构建初始 Master Arc（quality_level 至少 minimal） |
| 用户选择方向 | Volume Arc | Planner Agent 构建/更新当前 Volume Arc |
| 用户确认章节计划 | Sequence Arc | Planner Agent 构建/更新当前 Sequence Arc |
| ContextPack 构建 | Immediate Window | ContextPackService 动态组装 |
| StoryMemory/StoryState stale | 全部持久化层 | 对应轨道标记为 stale |
| 重新分析完成 | 全部持久化层 | 对应轨道从 stale → ready |
| 章节进展超出范围 | Volume/Sequence Arc | 触发新轨道构建建议 |
| 用户手动编辑 | 任意层 | 更新对应轨道，`built_by = user_edited` |
| apply 候选稿或手动改稿 | Volume/Sequence Arc | 相关轨道可标记 stale |

---

## 九、blocked / degraded / ready 判定规则

### 9.1 ContextPack readiness 由四层轨道状态联合判定

ContextPack 构建时，读取四层轨道的状态，按以下规则判定最终 readiness：

### 9.2 判定规则表

| Master Arc | Volume Arc | Sequence Arc | Immediate Window | ContextPack 结果 |
|---|---|---|---|---|
| ready | ready | ready | ready | **ready** |
| ready | ready | ready | degraded/empty | **degraded**（warning: `immediate_window_degraded`） |
| ready | ready | degraded/empty | ready | **degraded**（warning: `sequence_arc_missing`） |
| ready | degraded/empty | degraded/empty | ready | **degraded**（warning: `volume_arc_missing` + `sequence_arc_missing`） |
| ready | degraded/empty | degraded/empty | degraded/empty | **degraded**（多个 warning） |
| degraded/stale | * | * | * | **degraded**（如 stale + 可恢复） |
| **pending / failed / empty** | * | * | * | **blocked**（reason: `master_arc_missing`） |

多层轨道质量为 `placeholder` 时，追加 warning `arc_placeholder_only`。

### 9.3 规则优先级

1. **Master Arc 规则优先**：Master Arc 处于 `pending` / `failed` / `empty` → **blocked**，无论其他层状态如何。
2. **Stale 规则**：Master Arc stale → **degraded**（非 blocked，因为 Master Arc 数据仍存在仅过期）。Volume/Sequence stale → **degraded** + warning。
3. **Degraded 累积**：多层 degraded 时，所有 warning_codes 累积，ContextPack 标记为 **degraded**。
4. **Immediate Window 特殊处理**：Immediate Window 缺失/空 → **degraded**，不 blocked。因为 Immediate Window 不持久化，缺失属于预期内的降级情况。
5. **quality_level 规则**：`placeholder` 轨道不导致 blocked（除非 Master Arc 为 placeholder 且无有效替代），但追加 `arc_placeholder_only` warning。
6. **不因占位轨道误判 ready**：即使所有层都存在记录，若关键层仅为 `placeholder`，不得判定为 fully ready。

### 9.4 warning_codes 枚举

| warning_code | 含义 | 触发条件 |
|---|---|---|
| `master_arc_stale` | Master Arc 过期 | Master Arc stale_status = stale |
| `master_arc_inferred_without_outline` | Master Arc 从正文推断 | built_from_text_inference = true 且无用户大纲 |
| `volume_arc_missing` | Volume Arc 缺失 | Volume Arc 状态为 pending / empty / failed |
| `volume_arc_stale` | Volume Arc 过期 | Volume Arc stale_status = stale |
| `volume_arc_degraded` | Volume Arc 数据不完整 | Volume Arc 状态为 degraded |
| `sequence_arc_missing` | Sequence Arc 缺失 | Sequence Arc 状态为 pending / empty / failed |
| `sequence_arc_stale` | Sequence Arc 过期 | Sequence Arc stale_status = stale |
| `sequence_arc_degraded` | Sequence Arc 数据不完整 | Sequence Arc 状态为 degraded |
| `immediate_window_empty` | 临近窗口为空 | 无前文章节摘要可组装 |
| `immediate_window_stale` | 临近窗口过期 | 底层 StoryMemory/StoryState stale |
| `immediate_window_partial` | 临近窗口不完整 | 仅有部分章节的摘要数据 |
| `arc_placeholder_only` | 关键层仅为占位 | 轨道 quality_level = placeholder |
| `arc_conflict_pending` | 轨道层级冲突待处理 | 上下层约束不一致且未处理 |
| `arc_trimmed` | 轨道内容被裁剪 | ContextPack Token 紧张时轨道内容被压缩 |

### 9.5 强制 blocked 条件

以下条件任一满足，ContextPack 强制 blocked：

1. `master_arc_id` 不存在（从未构建过 Master Arc）
2. Master Arc.status ∈ { `pending`, `failed`, `empty` }
3. 初始化未完成（继承 P0 ContextPack blocked 规则）
4. StoryMemory 不存在（继承 P0 ContextPack blocked 规则）
5. StoryState 不存在（继承 P0 ContextPack blocked 规则）

---

## 十、初始化与轨道占位策略

### 10.1 初始化完成后的轨道生成

初始化完成后，Memory Agent 按以下顺序构建轨道：

1. **Master Arc**：从 `OutlineAnalysisResult` + `ChapterAnalysisResult` 提取。如果用户有大纲，优先从大纲提取；如果无大纲，从正文推断（标注 `built_from_text_inference = true`）。构建完成后 status 为 `ready` 或 `degraded`（取决于数据完整度），quality_level 至少为 `minimal`。
2. **Volume Arc #1**：初始化为 `pending` 状态。等待 Planner Agent 在首次方向选择后构建。可以创建一个最小占位记录（`volume_no = 1, status = pending, quality_level = placeholder, chapter_range: { from_chapter: 1, to_chapter_estimate: null }`）。
3. **Sequence Arc #1**：初始化为 `pending` 状态。等待 Planner Agent 在首次章节计划确认后构建。不创建占位记录。
4. **Immediate Window**：不预生成，首次 ContextPack 构建时动态组装。

### 10.2 占位模板

初始化完成前或信息不足时，可按以下最小模板创建占位：

| 轨道层 | placeholder 最小模板 |
|---|---|
| Master Arc | `arc_title` + `arc_logline` + `ultimate_goal`（三字段构成最小可识别主线）。quality_level = placeholder，status = degraded |
| Volume Arc | `stage_goal`（单字段）。quality_level = placeholder，status = pending |
| Sequence Arc | `sequence_goal`（单字段）。quality_level = placeholder，status = pending |
| Immediate Window | 不预创建占位（每次构建时动态组装，无内容则返回 empty + `immediate_window_empty`） |

### 10.3 占位轨道的使用限制

1. 占位轨道（quality_level = placeholder）必须标注 `quality_level=placeholder` 与对应的 warning。
2. 占位轨道不得标记为 `ready`。
3. 初始化完成后可从 placeholder 升级为 minimal / complete。
4. 不因占位轨道存在而误判为 fully ready。若仅有占位轨道且关键层不足，ContextPack 返回 degraded 或 blocked。

### 10.4 无大纲情况

当作品没有用户大纲时：
- Master Arc 仍可构建（从正文推断），但标记 `built_from_text_inference = true`，初始 status 为 `degraded`，quality_level 为 `minimal`（warning: `master_arc_inferred_without_outline`）。
- Volume Arc 仍需 Planner Agent 在方向选择后构建。
- 无大纲不影响其他层的构建。

### 10.5 初始化失败情况

初始化失败（`InitializationStatus = failed`）时，所有轨道层均不构建。继承 P0 规则：初始化未完成 → ContextPack blocked。

---

## 十一、与 StoryMemory / StoryState 的关系

### 11.1 关系定位

1. StoryMemory / StoryState 是事实与状态基线。
2. 四层轨道是"叙事推进结构层"。
3. 轨道可引用 Memory/State 摘要，不替代其存储语义。

### 11.2 数据来源关系

```text
StoryMemory                  StoryState
    │                             │
    ├── global_summary            ├── current_position_summary
    ├── chapter_summaries         ├── active_characters
    ├── characters                ├── active_locations
    ├── plot_threads              ├── unresolved_threads
    ├── locations                 ├── continuity_notes
    └── ...                       └── ...
    │                             │
    └────────┬────────────────────┘
             │
    ┌────────▼────────┐
    │  Memory Agent    │  提取 + 结构化
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Master Arc       │  长期持久化
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Planner Agent    │  基于 Master Arc + StoryMemory + StoryState
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Volume Arc       │  长期持久化
    │ Sequence Arc     │  长期持久化
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ ContextPack      │  动态组装 Immediate Window
    └─────────────────┘
```

### 11.3 联动原则

1. Memory/State 关键变更后，相关轨道可标记 stale。
2. 轨道更新不自动写回正式 StoryMemory/StoryState。
3. 记忆更新采纳仍经 MemoryReviewGate（P1-09）。
4. StoryMemory 的 stale 标记传播到轨道：StoryMemory stale → Master Arc stale → Volume Arc stale → Sequence Arc stale。

### 11.4 StoryState 更新对轨道的影响

StoryState 反映当前写作位置和角色状态。每次 StoryState 刷新后：
1. Immediate Window 在下次 ContextPack 构建时自动反映最新 StoryState。
2. Volume/Sequence Arc 的 `current_position` 字段由 Planner Agent 在章节计划更新时同步刷新。

---

## 十二、与 ContextPack 的关系

### 12.1 轨道在 ContextPack 中的位置

四层轨道作为 ContextPack 的**最高优先级约束层**进入上下文。在 `ContextPackSnapshot.context_items` 中，轨道数据以对应的 `source_type` ContextItem 形式存在。

### 12.2 各层在 ContextPack 中的表达

| 轨道层 | source_type | priority | required | token_estimate 方向 | 摘要字段 |
|---|---|---|---|---|---|
| Master Arc | `plot_arc_master` | 1（最高） | true | ~200 tokens | `ultimate_goal` + `current_stage` + `core_theme` |
| Volume Arc | `plot_arc_volume` | 2 | true | ~250 tokens | `core_conflict` + `stage_goal` + `climax_description` |
| Sequence Arc | `plot_arc_sequence` | 3 | true | ~300 tokens | `sequence_goal` + `key_events` 摘要（前 5 个） |
| Immediate Window | `plot_arc_immediate` | 4 | true | ~500 tokens | `recent_chapters_summary` + `current_chapter_context` + `character_current_states` |

### 12.3 Token 裁剪优先级

当 ContextPack 总 token 超出预算时，按以下顺序裁剪：

1. **最后裁剪**：Master Arc（可压缩摘要，不可完全删除。压缩后至少保留 `ultimate_goal` + `current_stage`，约 100 tokens）。
2. **倒数第二裁剪**：Volume Arc（可压缩为 `core_conflict` + `stage_goal`，约 150 tokens）。
3. **倒数第三裁剪**：Sequence Arc（可压缩为 `sequence_goal` + 前 3 个 `key_events`，约 200 tokens）。
4. **优先保留**：Immediate Window（Writer Agent 直接上下文，尽量不裁剪）。

裁剪后必须返回 warning_codes（如 `arc_trimmed`）。

### 12.4 轨道缺失时的 ContextPack 行为

| 条件 | ContextPack.status | blocked_reason / degraded_reason |
|---|---|---|
| Master Arc 缺失 | **blocked** | `master_arc_missing` |
| Master Arc ready + Volume Arc 缺失 | **degraded** | warning: `volume_arc_missing` |
| Master Arc ready + Sequence Arc 缺失 | **degraded** | warning: `sequence_arc_missing` |
| Immediate Window 空 | **degraded** | warning: `immediate_window_empty` |
| 关键层仅为 placeholder | **degraded** | warning: `arc_placeholder_only` |

---

## 十三、与五 Agent 的关系

### 13.1 Memory Agent

**读取权限**：读取全部四层轨道（检查一致性）；读取 StoryMemory / StoryState（提取轨道更新所需信息）。

**写入权限**：**只能写入 Master Arc**（构建初始版本、生成更新建议）。不能写入 Volume Arc / Sequence Arc（属于 Planner Agent）。不能写入 Immediate Window（不持久化）。

**使用轨道的方式**：
- 在初始化阶段：从 OutlineAnalysisResult + ChapterAnalysisResult 构建 Master Arc。
- 在记忆更新阶段：评估新内容是否需要更新 Master Arc（生成 MemoryUpdateSuggestion 而非直接修改）。
- 读取轨道与记忆差异，生成轨道相关 memory suggestions。

### 13.2 Planner Agent

**读取权限**：读取全部四层轨道（作为方向推演和章节计划的约束输入）。

**写入权限**：**写入 Volume Arc**（构建/更新）、**写入 Sequence Arc**（构建/更新）。可建议 Master Arc 更新，但需用户确认。若 Master Arc 缺失，不得进入可执行规划阶段。

**使用轨道的方式**：
- 方向推演时：以 Master Arc 为边界，在当前 Volume Arc 约束下生成 A/B/C 方向。
- 章节计划时：基于 Volume Arc + Sequence Arc 生成 ChapterPlan，确保不偏离轨道。
- 轨道更新：方向确认后更新 Volume Arc；章节计划确认后更新 Sequence Arc。

### 13.3 Writer Agent

**读取权限**：通过 ContextPack 间接读取全部四层轨道（Writer Agent 不直接访问轨道数据）。

**写入权限**：**无**。Writer Agent 不能修改任何轨道数据。

**使用轨道的方式**：
- ContextPack 中的轨道数据作为 Writer Prompt 的最高优先级约束层。
- Writer Agent 在生成 CandidateDraft 时必须遵守 Master Arc 的 `forbidden_outcomes` 和 Volume/Sequence Arc 的 `forbidden_items`。
- 轨道 degraded 时可在策略允许下继续，并透传 warning。

### 13.4 Reviewer Agent

**读取权限**：通过 ContextPack 或直接读取四层轨道（用于审稿时的轨道偏离检查）。

**写入权限**：**无**。Reviewer Agent 不能修改任何轨道数据。

**使用轨道的方式**：
- 审稿时对比 CandidateDraft 内容与四层轨道，检测轨道偏离。
- 输出轨道偏离提示，不自动修复。
- 轨道偏离标记为 `arc_deviation` 类型的 ReviewIssue，提交给 Conflict Guard（P1-08）处理。

### 13.5 Rewriter Agent

**读取权限**：通过 ContextPack 间接读取轨道数据；可读取 ReviewReport 中的 `arc_deviation` 问题。

**写入权限**：**无**。Rewriter Agent 不能修改任何轨道数据。

**使用轨道的方式**：修订时参照 ReviewReport 中的轨道偏离问题，基于 Reviewer 反馈与轨道约束修订候选版本。不直接更改轨道状态机。

### 13.6 Agent 轨道权限总表

| Agent | 读 Master | 读 Volume | 读 Sequence | 读 Immediate | 写 Master | 写 Volume | 写 Sequence | 写 Immediate |
|---|---|---|---|---|---|---|---|---|
| Memory Agent | ✓ | ✓ | ✓ | ✓ | 仅建议 | ✗ | ✗ | ✗ |
| Planner Agent | ✓ | ✓ | ✓ | ✓ | 建议（需确认） | ✓ | ✓ | ✗ |
| Writer Agent | 间接 | 间接 | 间接 | 间接 | ✗ | ✗ | ✗ | ✗ |
| Reviewer Agent | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Rewriter Agent | 间接 | 间接 | 间接 | 间接 | ✗ | ✗ | ✗ | ✗ |

---

## 十四、与 Direction Proposal / ChapterPlan 的关系

### 14.1 方向推演

Direction Proposal（P1-05）的生成必须基于四层轨道：
- **Master Arc** 约束方向的上限（不能推出与终极目标矛盾的方向）。
- **Volume Arc** 约束方向的当前阶段边界。
- **Sequence Arc** 约束方向的近期可行性。
- **Immediate Window** 提供方向推演的上下文起点。

Planner Agent 在生成 A/B/C 方向时，必须在每个 DirectionProposal 中记录引用的轨道摘要（`base_arc_refs` 字段）。方向不得脱离当前轨道语义凭空发散。

### 14.2 章节计划

ChapterPlan（P1-05）的生成必须基于四层轨道：
- 每个 ChapterPlan 项的 `chapter_goal` 必须在 Sequence Arc 的 `sequence_goal` 范围内。
- `key_events` 必须与 Sequence Arc 的 `key_events` 对齐。
- `forbidden_items` 必须包含 Volume Arc 和 Sequence Arc 的 `forbidden_items`。
- `foreshadow_arrangement` 必须与 Volume Arc 的 `foreshadow_planted` / `foreshadow_resolved` 对齐。
- ChapterPlan 应显式关联本章对应的轨道约束（引用 Sequence Arc 的 `required_beats`）。

PlanConfirmation 前不得自动进入 Writer。ChapterPlan 结构细节由 P1-05 冻结。

### 14.3 方向/计划确认后的轨道更新

- 用户选择方向后：Planner Agent 构建/更新 Volume Arc。
- 用户确认章节计划后：Planner Agent 构建/更新 Sequence Arc。

---

## 十五、与 ConflictGuard 的关系

### 15.1 输入关系

四层轨道为 ConflictGuard 提供"轨道一致性约束输入"，用于识别：
1. 轨道偏离（`arc_deviation`）。
2. 上下层约束冲突（`arc_constraint_conflict`）。
3. 推进顺序冲突（`arc_sequence_conflict`）。

### 15.2 轨道偏离检测方向

P1-04 定义轨道偏离的**检测维度**（具体规则矩阵由 P1-08 冻结）：

| 偏离维度 | 检测方式 | 严重程度方向 |
|---|---|---|
| `arc_deviation_master` | CandidateDraft 内容违背 Master Arc 的 `ultimate_goal` 或 `forbidden_outcomes` 或 `hard_constraints` | blocking |
| `arc_deviation_volume` | CandidateDraft 内容超出 Volume Arc 的 `stage_goal` 范围 | warning / blocking |
| `arc_deviation_sequence` | CandidateDraft 内容与 Sequence Arc 的 `key_events` 矛盾 | warning |
| `arc_deviation_immediate` | CandidateDraft 与 Immediate Window 的近期上下文明显断裂 | warning |
| `arc_deviation_tone` | CandidateDraft 基调与 Volume Arc 或 Master Arc 的 tone 方向严重不符 | warning |
| `arc_constraint_conflict` | 下层轨道约束与上层硬约束不一致 | warning / blocking |
| `arc_sequence_conflict` | Sequence Arc 之间的推进顺序存在矛盾 | warning |

### 15.3 处理边界

1. P1-04 只定义触发点与输入关系。
2. blocking/warning 规则矩阵由 P1-08 冻结。
3. 轨道冲突不自动修复，需 user_action 处理。
4. Reviewer Agent 审稿时，对比 CandidateDraft 与四层轨道，生成 `arc_deviation_*` 类型的 ReviewIssue。Conflict Guard 读取 ReviewIssue 后按 P1-08 规则判定。

---

## 十六、与 UI / DESIGN.md 的关系

### 16.1 右侧工作区各 Tab 中的轨道展示

| UI Tab | 展示内容 | 数据来源 |
|---|---|---|
| 大纲 Tab | 作品大纲区域展示 Master Arc（`ultimate_goal` + `current_stage` + `core_theme`）；当前章节目标区域展示 Volume Arc（`stage_goal`）+ Sequence Arc（`sequence_goal`）；P1 章节计划区域展示 Sequence Arc（`key_events` 精简 5 条） | Master / Volume / Sequence Arc 摘要 |
| 线索 Tab | 当前章节相关线索对应 Immediate Window 的 `active_plot_threads`；未闭合线索对应 Volume Arc 的 `stage_open_loops` | Immediate Window + Volume Arc |
| 伏笔 Tab | 待回收伏笔对应 Volume Arc 的 `foreshadow_planted` + `foreshadow_resolved`；风险提示对应 ConflictGuard 标记的伏笔冲突 | Volume Arc + ConflictGuard |
| 人物 Tab | 当前出场人物状态摘要对应 Immediate Window 的 `character_current_states`；关键角色对应 Volume Arc 的 `key_characters` | Immediate Window + Volume Arc |
| AI Tab | 轨道状态标签（绿色 ready / 橙色 degraded / 红色 blocked / 灰色 pending）+ ContextPack readiness 摘要 | ArcStatus |
| 审阅 Tab | 轨道偏离问题以 ReviewIssue 形式展示（不以原始轨道 diff 形式展示） | Reviewer Agent → ReviewIssue |

### 16.2 视觉与信息边界

1. 普通用户界面展示摘要，不展示完整轨道 JSON 原始结构。
2. 不展示轨道的 `version` / `built_by` / `last_updated_by` / `stale_reason` 等技术字段。
3. 轨道状态需统一映射 DESIGN.md 状态色语义：ready→绿色、degraded→橙色、blocked/failed→红色、pending→灰色。
4. 不展示完整 Prompt、完整 ContextPack 内容、API Key。
5. 轨道偏离检测结果在审阅 Tab 中以 ReviewIssue 卡片形式展示，不以原始轨道 diff 形式展示。

---

## 十七、P1-04 不做事项清单

P1-04 不做：

- 不设计轨道可视化拖拽面板（属于 P2）。
- 不设计轨道关系图谱/剧情结构图（属于 P2）。
- 不实现轨道的自动检测和自动重新分析（属于 P2）。
- 不实现轨道的跨作品对比分析（属于 P2）。
- 不设计 Direction Proposal 算法（属于 P1-05）。
- 不设计 ChapterPlan 完整数据结构（属于 P1-05）。
- 不设计 Conflict Guard 完整规则矩阵（属于 P1-08）。
- 不设计 StoryMemory Revision 数据结构（属于 P1-09）。
- 不设计 API / DTO / 前端集成细节（属于 P1-11）。
- 不设计轨道的手动编辑完整 UX（P1 支持最小编辑，完整 UX 属于 P2）。
- 不引入第五层轨道（Chapter 级独立持久化轨道）或第六层（Scene 级独立持久化轨道）。
- 不设计轨道的多语言支持。
- 不设计轨道的导入/导出功能。
- 不设计复杂知识图谱/关系图谱引擎。
- 不设计自动连续续写队列。
- 不写代码。

---

## 十八、P1-04 验收标准

- [ ] 四层轨道（Master / Volume / Sequence / Immediate Window）数据模型完整且字段定义清楚
- [ ] 四层轨道最小字段可落地且可追踪
- [ ] ArcStatus 枚举覆盖所有状态：pending / ready / degraded / stale / failed / empty
- [ ] quality_level 体系（placeholder / minimal / complete）与 ArcStatus 正交且定义清楚
- [ ] 轨道之间的父子关系与继承规则（ARC-INHERIT-01 ~ 07）明确
- [ ] Master Arc 缺失 → ContextPack blocked
- [ ] Volume / Sequence / Immediate Window 缺失 → ContextPack degraded + 具体 warning_codes
- [ ] warning_codes 枚举完整（至少 14 个：含 arc_placeholder_only / arc_trimmed / arc_conflict_pending）
- [ ] 初始化阶段轨道占位策略明确（Master Arc 构建为 minimal、Volume Arc 最小占位、Sequence Arc 待定、Immediate Window 不预创建）
- [ ] 占位模板（placeholder 最小字段）明确且不伪装为 ready
- [ ] 每个 Agent 对四层轨道的读写权限清晰（13.6 权限总表）
- [ ] ContextPack 中轨道的 Token 裁剪优先级明确（Immediate Window 优先保留 → Master Arc 最后裁剪不可缺失）
- [ ] 轨道 stale 传播规则明确
- [ ] Immediate Window 不持久化规则明确
- [ ] 与 StoryMemory/StoryState 关系不混淆
- [ ] 与 Direction Proposal / ChapterPlan 的约束关系方向明确
- [ ] 与 Conflict Guard 的偏离检测维度方向明确（7 个维度）
- [ ] UI 展示方向与 P1-UI §7 / DESIGN.md 对齐
- [ ] 旧稿 Chapter/Scene 命名已映射到正式口径
- [ ] 不引入 P2 能力
- [ ] P1-05 / P1-08 / P1-11 可以基于本文档进行各自的详细设计

---

## 十九、P1-04 待确认点

1. **Volume Arc 的多卷管理**：一个作品有多个 Volume Arc 时，是否需要 `is_current` 标记字段还是通过 `chapter_range` 匹配？当前设计通过 `chapter_range` 匹配，无需额外标记。
2. **Sequence Arc 的数量上限**：一个 Volume 内是否限制 Sequence Arc 数量？当前设计不设硬上限，但通常 1-2 个。是否需要在 P1-04 中定义上限？
3. **Master Arc 的 `stage_position` 结构**：`{ act, stage, progress_pct }` 是否足够表达阶段位置？是否需要增加 `stage_name` 字段？
4. **Immediate Window 的章节数量**：当前设计为"前 10 章摘要 + 前 3 章详情"。ContextPack Token 预算紧张时是否自动缩小为"前 5 章 + 前 1 章"？
5. **轨道版本回滚**：P1 是否支持轨道的手动回滚（类似 StoryMemory Revision 回滚）？当前设计不包含，是否需要预留 `previous_version_ref` 字段？
6. **用户手动编辑轨道的交互**：P1-UI 中大纲 Tab 的"编辑"按钮是否允许用户直接修改轨道字段（如 `ultimate_goal`、`core_conflict`）？还是仅允许编辑作品大纲文本？
7. **Master Arc 从正文推断的可靠性标记**：当无用户大纲时，Master Arc 标记 `built_from_text_inference = true` + `master_arc_inferred_without_outline` warning。是否需要在前端提示用户"此主线是从正文推断的，建议手动确认"？
8. **Sequence Arc 与 ChapterPlan 的粒度关系**：Sequence Arc 覆盖 10-20 章，ChapterPlan 覆盖 3-5 章。一个 Sequence Arc 内可能有多轮 ChapterPlan。Sequence Arc 更新时是否需要保留历史 ChapterPlan 引用列表？
9. **Conflict Guard 中 `arc_deviation` 的 warning/blocking 判定**：当前文档只给方向（§15.2），具体规则由 P1-08 冻结。P1-04 是否需要在数据模型中预留 `deviation_tolerance_level` 字段？
10. **Immediate Window 的 `scene_details` 字段**：当前设计为可选。什么条件下填充场景细节（SceneMoment）？是否依赖 StoryMemory 中有场景级别的分析数据？
11. **Master Arc stale 是 blocked 还是 degraded**：当前设计为 degraded（因为数据仍存在仅过期）。是否在某些严重过期场景下应 blocked？
12. **Volume Arc 缺失时 Planner Agent 是否强制降级**：当前设计为 degraded，Planner 可在策略允许下继续。是否需要强制 Planner 在方向推演前等待 Volume Arc 就绪？
13. **quality_level 从 placeholder 到 minimal 的阈值**：字段满足率达到多少可升级？当前设计不设硬性阈值，以"必填字段齐全"为 minimal 条件。是否需要定义具体字段清单？
14. **轨道 token 预算配额**：是否需要在 ContextPack 的 `max_context_tokens` 中为四层轨道保留固定配额（如 800 tokens 保底）？

---

## 附录 A：四层轨道字段速查表

| 层级 | ID 前缀 | 持久化 | 构建者 | 维护者 | 关键字段 |
|---|---|---|---|---|---|
| Master Arc | `ma_` | 是 | Memory Agent | Planner Agent（建议）/ Memory Agent（建议） | `ultimate_goal` / `final_conflict` / `current_stage` / `endgame_foreshadows` / `forbidden_outcomes` / `hard_constraints` / `quality_level` |
| Volume Arc | `va_` | 是 | Planner Agent | Planner Agent | `core_conflict` / `stage_goal` / `climax_description` / `resolution_condition` / `chapter_range` / `stage_open_loops` |
| Sequence Arc | `sa_` | 是 | Planner Agent | Planner Agent | `sequence_goal` / `key_events` / `turning_points` / `climax_chapter_estimate` / `chapter_range` / `required_beats` |
| Immediate Window | `iw_` | 否 | ContextPackService（动态） | 无（每次重建） | `recent_chapters_summary` / `current_chapter_context` / `character_current_states` / `previous_chapter_hook` / `scene_details` |

## 附录 B：P1-04 与 P1 总纲对照

| P1 总纲 §6 冻结结论 | P1-04 落点 |
|---|---|
| 四层轨道定义：Master / Volume/Act / Sequence / Immediate Window | §2.1 / §3-6 |
| Master Arc 缺失 → ContextPack blocked | §9.2 / §9.5 |
| Volume / Sequence / Immediate Window 缺失 → degraded + warning_codes | §9.2 / §9.4 |
| Master Arc 由 Memory Agent 在初始化时构建 | §3.3 / §10.1 |
| Volume Arc 由 Planner Agent 在方向选择后构建/更新 | §4.3 / §14.3 |
| Sequence Arc 由 Planner Agent 在章节计划中构建/维护 | §5.4 / §14.3 |
| Immediate Window 由 ContextPack 构建时动态组装，不持久化 | §6.4 / §6.5 |
| 四层轨道全部进入 ContextPack 作为最高优先级约束层 | §12.1 |
| Token 裁剪优先级：Immediate Window 最高 → Sequence → Volume → Master Arc 最后 | §12.3 |
| 轨道偏离 → Conflict Guard warning/blocking | §15.2 |
| P1 只做结构化轨道与上下文供给 | §17 |
| 轨道可视化拖拽面板 / 自动检测 / 跨作品对比 → P2 | §17 |

## 附录 C：旧稿命名映射表

| 旧稿名称 | 旧稿状态体系 | 最终正式处理 |
|---|---|---|
| Master Arc | — | **保留**为 L1 正式层 |
| Volume Arc | — | **保留**为 L2 正式层 |
| Chapter Arc | — | **不作为正式持久化轨道层**。其语义（章节目标/冲突/节拍）并入：① Sequence Arc 的 `required_beats` / `key_events`（章级约束）；② P1-05 ChapterPlan 的 `chapter_goal` / `required_beats`（章节计划）。不单独进入 P1-04 四层层级树 |
| Scene Arc | — | **不作为正式持久化轨道层**。其语义（场景节拍/情绪/视角/信息揭示）并入 Immediate Window 的 `scene_details` / `SceneMoment` 子结构。不单独进入 P1-04 四层层级树 |
| draft（旧状态） | draft | 映射为 ArcStatus.`pending` |
| active（旧状态） | active | 映射为 ArcStatus.`ready` |
| stale（旧状态） | stale | 直接采用 ArcStatus.`stale` |
| archived（旧状态） | archived | 不进入 P1-04 主状态体系（P2 或版本归档能力） |
