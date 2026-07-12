# InkTrace V2.0 项目现状汇报

> **历史快照**：本文记录 2026-05-18 的阶段状态。当前状态请以 [`../PROJECT_STATUS_CURRENT.md`](../PROJECT_STATUS_CURRENT.md) 为准。

> 汇报日期：2026-05-18 | 当前分支：`feature/v2-p0` | 作者：开发团队

---

## 一、项目概述

**InkTrace** 是一个面向长篇小说创作的 AI 辅助写作系统，定位为"作者与智能体协作写小说的 IDE"。系统采用双模型协同策略：**Kimi（DeepSeek 系）负责理解/分析/规划/控制，DeepSeek 负责写作/续写/改写/润色**。

### 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | Python 3.13 + FastAPI + Pydantic v2 |
| 前端框架 | Vue 3 + Vite + Pinia + Element Plus |
| 桌面打包 | Electron + electron-builder（Windows/macOS） |
| 数据库 | SQLite（aiosqlite 异步驱动） |
| 向量存储 | ChromaDB |
| AI 接入 | OpenAI 兼容 API（Kimi / DeepSeek） |
| 测试 | pytest（后端）+ Vitest + jsdom（前端） |

---

## 二、架构概况

### 2.1 分层架构（Clean Architecture / DDD）

```
┌─────────────────────────────────────────────────┐
│                   Presentation                   │
│         FastAPI 路由（V1 REST + V2 AI）           │
├─────────────────────────────────────────────────┤
│                  Application                     │
│     用例编排 / Prompt 构建 / Workflow 调度        │
├─────────────────────────────────────────────────┤
│                    Domain                        │
│     实体 · 值对象 · 仓储接口 · 领域服务             │
├─────────────────────────────────────────────────┤
│                Infrastructure                    │
│   SQLite 持久化 · 文件 I/O · ChromaDB · AI Provider │
└─────────────────────────────────────────────────┘
```

数据流向：`Presentation → Application → Domain ← Infrastructure`

### 2.2 V2.0 核心架构决策

InkTrace V2.0 将系统分为两大子系统：

- **InkTrace Core**：领域模型 + 应用服务 + Tool Facade（受控入口）
- **InkTrace Agent**：AI 编排层（Agent Runtime / 工作流 / 五 Agent）

**关键约束：**
- Agent 只能通过 **Core Tool Facade** 调用 Core 能力，不得直接访问数据库或领域模型
- AI 输出经 **CandidateDraft / AI Suggestion / MemoryUpdateSuggestion** 隔离层 + 人工确认门控
- **Local-First 保存链路**不被 V2.0 改变
- 三个独立门控：**HumanReviewGate**（正文）、**ConflictGuard**（冲突）、**MemoryReviewGate**（记忆）

### 2.3 代码模块规模

| 模块 | 关键文件数 | 说明 |
|------|-----------|------|
| `presentation/api/routers/v1/` | 10 | V1 REST API（作品/章节/会话/大纲/时间线/伏笔/人物） |
| `presentation/api/routers/v2/ai/` | 10 | V2 AI API（初始化/续写/审阅/上下文包/任务管理） |
| `application/services/v1/` | 9 | V1 业务服务 |
| `application/services/ai/` | 21 | AI 服务层（Agent Runtime / 工作流 / 审阅 / 记忆管理） |
| `domain/entities/` | 6 + ai/models.py | 领域实体（~50 个 AI 相关模型） |
| `domain/repositories/` | 22 | 仓储接口（含 15 个 AI 仓储） |
| `domain/services/` | 9 | 领域服务 |
| `infrastructure/` | 20+ | 持久化实现 + AI Provider |
| `frontend/src/` | 60+ | Vue 3 前端组件/视图/Store/API |

---

## 三、开发阶段与进度

### 3.1 整体路线图

```
V1.0 ──────► V1.1 ──────► V2.0 P0 ──────► V2.0 P1 ──────► V2.0 P2
(已交付)     (已封版)     (已冻结)        (当前阶段)       (规划中)
```

### 3.2 V1.1 — 已完成（纯文本写作工作台）

- Stage 0-1 已确认完成
- Stage 2-5 基本完成，部分收口中
- 能力：作品管理、章节编辑、大纲/时间线/伏笔/角色资产管理、TXT 导入导出、乐观锁并发控制

### 3.3 V2.0 P0 — 已冻结（AI 基础闭环）

**完成时间：** 2026-05-12

**P0 涵盖 11 个模块**（S0-S10），已全部冻结：

| 阶段 | 模块 | 状态 |
|------|------|------|
| S1 | AI 基础设施（Provider / ModelRouter / Prompt Registry） | ✅ 已交付 |
| S2 | AI Job System（长任务生命周期管理） | ✅ 已交付 |
| S3 | 初始化流程（大纲分析 + 正文分析） | ✅ 已交付 |
| S4 | StoryMemory 与 StoryState（最小可用记忆） | ✅ 已交付 |
| S5 | Vector Recall（向量索引与 Top-K 召回） | ✅ 已交付 |
| S6 | ContextPack（最小上下文包） | ✅ 已交付 |
| S7 | ToolFacade 与权限控制 | ✅ 已交付 |
| S8 | Minimal Continuation Workflow（单章续写编排） | ✅ 已交付 |
| S9 | CandidateDraft 与 HumanReviewGate | ✅ 已交付 |
| S10 | AI Review（基础审稿能力） | ✅ 已交付 |

**P0 核心交付物：**
- AI 基础设施层完整可用（Provider 注册、模型路由、Prompt 模板管理）
- 长任务异步执行框架（Job → Step → Attempt 三级状态机）
- 故事初始化分析（两阶段：大纲分析 + 正文分析）
- 最小上下文包构建（blocked / degraded / ready 三态）
- 单章受控续写闭环（候选稿隔离 + 人工确认门控）

### 3.4 V2.0 P1 — 当前阶段（完整智能体工作流）

**设计冻结：** 2026-05-14  
**开发计划封版：** 2026-05-15  
**当前进度：** S1 实施中（Agent Runtime 核心落地）

**P1 涵盖 13 个模块**（S0-S12）：

| 阶段 | 模块 | 状态 |
|------|------|------|
| S0 | 基线与封板确认 | 🔲 待开始 |
| S1 | **AgentRuntime 核心落地** | 🟡 实施中 |
| S2 | AgentWorkflow 编排落地 | 🔲 待开始 |
| S3 | 五 Agent 职责与权限落地 | 🔲 待开始 |
| S4 | 四层剧情轨道落地 | 🔲 待开始 |
| S5 | 方向推演与章节计划落地 | 🔲 待开始 |
| S6 | 多轮 CandidateDraft 迭代落地 | 🔲 待开始 |
| S7 | AI Suggestion 落地 | 🔲 待开始 |
| S8 | ConflictGuard 落地 | 🔲 待开始 |
| S9 | MemoryRevision / MemoryReviewGate 落地 | 🔲 待开始 |
| S10 | AgentTrace / 可观测性落地 | 🔲 待开始 |
| S11a | API 集成边界落地 | 🔲 待开始 |
| S11b | 前端集成落地 | 🔲 待开始 |
| S12 | E2E 联调与封板验收 | 🔲 待开始 |

**P1 设计文档（14 份，全部候选冻结）：**

| 编号 | 文档 | 内容 |
|------|------|------|
| 总纲 | P1 详细设计总纲 | 所有 P1 模块的设计范围与边界 |
| P1-01 | AgentRuntime 详细设计 | AgentSession / AgentStep / PPAO 循环 / 状态机 |
| P1-02 | AgentWorkflow 详细设计 | WorkflowStage / Transition / Decision / Checkpoint |
| P1-03 | 五 Agent 职责与编排详细设计 | Memory / Planner / Writer / Reviewer / Rewriter |
| P1-04 | 四层剧情轨道详细设计 | Master Arc / Volume Act / Sequence / Immediate Window |
| P1-05 | 方向推演与章节计划详细设计 | A/B/C 方向提案 / DirectionSelection / ChapterPlan |
| P1-06 | 多轮 CandidateDraft 迭代详细设计 | 候选稿版本链 / 审稿-修订循环 |
| P1-07 | AI Suggestion 详细设计 | 建议层模型 / 状态机 / 转化规则 |
| P1-08 | ConflictGuard 详细设计 | 冲突检测与阻断 / 冲突类型 / 严重度 |
| P1-09 | StoryMemoryRevision 与 MemoryReviewGate | 记忆更新建议 / 审批门控 / 版本化 |
| P1-10 | AgentTrace 与可观测性详细设计 | 追踪 / 审计 / 指标 / 告警 |
| P1-11 | API 与前端集成边界详细设计 | 11 组 API 分组 / DTO 规则 / 轮询 SSE 策略 |
| UI | 界面与交互设计 | 三栏布局 / 右侧工作区 / 门控卡片 |
| — | 实施唯一依据清单 | P1 实施正式依据索引 |

---

## 四、代码落地情况

### 4.1 代码量统计

| 维度 | 数据 |
|------|------|
| feature/v2-p0 分支领先 master 提交数 | **24 个提交** |
| 变更文件数 | **300 个文件** |
| 净增加代码行数 | **+72,895 行** |
| 测试文件数（后端） | **50+ 个测试文件** |
| 测试文件数（前端） | **32 个测试文件** |

### 4.2 核心代码模块状况

**已完整实现的模块（P0）：**

| 模块 | 主要文件 | 代码规模 |
|------|---------|----------|
| AI Provider 注册 | `infrastructure/ai/providers/openai_compatible_provider.py` | 完整 |
| 模型路由 | `application/services/ai/model_router.py` | 完整 |
| Prompt 注册表 | `application/services/ai/prompt_registry.py` | 完整 |
| AI Job 系统 | `application/services/ai/ai_job_service.py` + `ai_job_runner.py` | 406 行 |
| 故事初始化 | `application/services/ai/initialization_service.py` | 385 行 |
| 上下文包构建 | `application/services/ai/context_pack_service.py` | 471 行 |
| 续写工作流 | `application/services/ai/continuation_workflow.py` | 381 行 |
| AI 审阅 | `application/services/ai/ai_review_service.py` | 完整 |
| 候选稿管理 | `application/services/ai/candidate_review_service.py` | 完整 |
| 输出验证 | `application/services/ai/output_validation_service.py` | 完整 |
| LLM 调用日志 | `application/services/ai/llm_call_logger.py` | 完整 |
| Tool Facade | `application/services/ai/tool_facade.py` | 完整 |
| 故事记忆/状态 | `application/services/ai/story_memory_service.py` + `story_state_service.py` | 完整 |

**正在实施中的模块（P1-S1）：**

| 模块 | 主要文件 | 当前状态 |
|------|---------|----------|
| Agent Runtime | `application/services/ai/agent_runtime_service.py` | 🟡 331 行新增改动（未提交） |
| Agent 领域模型 | `domain/entities/ai/models.py` | 🟡 15 行新增 |
| Agent Runtime 测试 | `tests/ai/test_agent_runtime_service.py` | 🟡 2510 行新增 |

### 4.3 前端 AI 集成情况

| 组件/模块 | 文件 | 状态 |
|-----------|------|------|
| AI 控制面板 | `AIPanel.vue`（440 行新组件） | ✅ 已交付 |
| AI 任务轮询 | `useAIJobPolling.js`（组合式函数） | ✅ 已交付 |
| 写作工作区集成 | `WritingStudio.vue`（已改造） | ✅ 已交付 |

### 4.4 测试覆盖

**后端测试（tests/ai/）覆盖 P0 全部模块：**

- AI Provider 注册表测试
- 模型路由测试
- Prompt 注册表测试
- 输出验证测试
- LLM 调用日志测试
- AI Job 仓库 + 运行器 + 服务 + API 测试
- 初始化服务 + API 测试
- 快速试测服务 + API 测试
- 续写服务测试
- 上下文包服务 + API 测试
- AI 审阅服务 + API 测试
- 候选草稿 + API + 状态模型测试
- 人工审阅门控测试
- Tool Facade 测试
- Agent Runtime 服务测试（**当前在扩展中，+2510 行**）
- P0 边界测试 + 回归测试 + E2E 测试
- 真实 Provider 集成测试 + 冒烟测试

**前端测试：** 32 个测试文件覆盖所有核心组件、Store、API 层和工具函数。

---

## 五、Git 提交历史（feature/v2-p0 分支）

### 5.1 开发节奏

| 日期 | 提交数 | 里程碑 |
|------|--------|--------|
| 2026-05-11 | 8 | S0 分支创建，P0 S1-S10 冲刺实施 |
| 2026-05-12 | 5 | P0 冻结，P1 设计总纲冻结 |
| 2026-05-13 | 2 | P1-01 / P1-02 详细设计 |
| 2026-05-14 | 4 | P1 设计子模块完成，偏差修正 |
| 2026-05-15 | 5 | P1 设计冻结，开发计划封版，P1-S1 初始实施 |

### 5.2 完整提交记录

```
083fdbe  2026-05-15  P1-S1 实施一部分
99fcab0  2026-05-15  P1 开发计划封版
6896703  2026-05-15  P1 详细设计封版
f4489a3  2026-05-15  P1-09 封板
44d1275  2026-05-15  P1-07 设计封版
6d86cdf  2026-05-14  P1-05 设计封版
ab2378f  2026-05-14  设计偏差补充修正
2285a4f  2026-05-14  设计偏差补充修正
7ad2976  2026-05-13  P1-02 详细设计
596b0f3  2026-05-13  P1-01 冻结设计
e5304f4  2026-05-12  P1 详细设计总纲冻结
ea5506e  2026-05-12  P0 冻结
a68db83  2026-05-12  P0 冻结
b301a0d  2026-05-12  S10 第一版完成
28cf878  2026-05-12  S8 验收完成
2d8add3  2026-05-11  S6 验收完成
6a49acc  2026-05-11  S4 完成
a9e6e63  2026-05-11  S4: 实现最小上下文包构建
d21305f  2026-05-11  S3: 实现最小初始化分析
379b98f  2026-05-11  S2: 实现最小 AI Job 系统
da7d61e  2026-05-11  S1 完成
20ec9a0  2026-05-11  S1: 实现最小 AI 基础设施
2a44f39  2026-05-11  准备开发
225efef  2026-05-11  S0: 统一阶段文档路径并更新基线报告
```

---

## 六、当前未提交工作（截至 2026-05-18）

| 文件 | 改动量 | 说明 |
|------|--------|------|
| `application/services/ai/agent_runtime_service.py` | +331 行 | Agent Runtime 核心服务实现 |
| `tests/ai/test_agent_runtime_service.py` | +2510 行 | Agent Runtime 测试用例扩展 |
| `domain/entities/ai/models.py` | +15 行 | Agent 相关领域模型补充 |
| `docs/03_design/...P1-03-五Agent职责与编排详细设计.md` | 修订 | 设计文档微调 |
| `frontend/src/components/workspace/ChapterTitleInput.vue` | 修订 | 前端微调 |
| `frontend/src/components/workspace/PureTextEditor.vue` | 修订 | 前端微调 |
| `frontend/src/components/workspace/StatusBar.vue` | 修订 | 前端微调 |
| `frontend/.../__tests__/ChapterSidebar.spec.js` | 修订 | 测试微调 |
| `frontend/.../__tests__/StatusBar.spec.js` | 修订 | 测试微调 |

---

## 七、关键风险与关注点

### 7.1 当前关注

1. **P1-S1 AgentRuntime 是核心枢纽**：作为整个 P1 Agent 工作流的基础运行时，其设计与实现质量直接影响后续 11 个模块。当前处于实施中途，需重点关注状态机实现的正确性和 PPAO（Perceive-Plan-Act-Observe）循环的完整性。

2. **P0 联调验证尚未闭环**：P0 代码实现完成但缺少系统级验收记录（docs/06_validation/ 下无 V2.0 验收文档），建议在 P1 推进前或并行进行 P0 E2E 验收。

3. **前端 AI 交互仅完成基础框架**：AIPanel 和 AIJobPolling 已交付，但 P1 涉及的复杂交互（建议卡、门控面板、方向推演 UI、Agent 步骤可视化等）均未开始。

### 7.2 架构风险

- **Agent 与 Core 单向依赖**是架构红线，需在 P1 实施中持续通过代码审查和测试门控确保不出现反向依赖。
- **三套门控机制**（HumanReviewGate / ConflictGuard / MemoryReviewGate）需确保语义不混淆、UI 不重叠。

---

## 八、下一步计划

| 优先级 | 事项 | 说明 |
|--------|------|------|
| P0 | 完成 P1-S1 AgentRuntime 核心实现 | 当前未提交改动的收尾与提交 |
| P0 | P0 系统级 E2E 验收 | 补充验收文档，确认 P0 闭环可用 |
| P1 | 推进 P1-S2 AgentWorkflow 编排 | 依赖 S1 完成 |
| P1 | P1-S3 五 Agent 职责落地 | Memory / Planner / Writer / Reviewer / Rewriter |
| P2 | 前端 AI 交互升级 | 门控 UI / 建议卡 / Agent 步骤可视化 |

---

## 附录：文档索引

| 类别 | 路径 | 关键文件 |
|------|------|----------|
| 需求 | `docs/01_requirements/` | `InkTrace-V2.0-需求规格说明书.md` |
| 架构 | `docs/02_architecture/` | `InkTrace-V2.0-架构设计说明书.md` |
| 概要设计 | `docs/07_overview/` | `InkTrace-V2.0-概要设计说明书.md` |
| P0 详细设计 | `docs/03_design/V2/` | 12 份模块设计文档 |
| P1 详细设计 | `docs/03_design/` | 14 份模块设计文档 |
| P0 开发计划 | `docs/04_plan/` | `InkTrace-V2.0-P0-开发计划.md` |
| P1 开发计划 | `docs/04_plan/` | `InkTrace-V2.0-P1-开发计划.md` |
