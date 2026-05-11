# InkTrace V2.0 P0 S0 开发基线报告

## 一、结论摘要

- 是否可以进入 S1：可以进入 S1，但需注意当前 frontend 未提交改动仍未隔离；S3/S5/S6 阶段细化文档路径已统一，P0 AI 后端落点已确认。
- 阻塞问题：无设计文档缺失阻塞；工程管理层面仍需避免 frontend 未提交改动混入 P0 开发提交。
- 需要先修复的问题：建议将现有 frontend 改动提交、stash、另开分支保存，或由当前负责人明确保留；这些改动与 P0 S1 AI 基础设施无关，不建议混入 P0 提交。
- 建议开发分支：`feature/v2-p0`，建议从干净的 `master` 或 `main` 创建。

### 1.1 本次工程整理结果

| 检查项 | 处理结果 |
|---|---|
| S3/S5/S6 阶段细化文档路径 | 已统一为 `docs/04_plan/InkTrace-V2.0-P0-S3S5S6-阶段细化.md` |
| `V2_0` 旧路径引用 | 全仓搜索未发现旧文件名引用 |
| frontend 未提交改动 | 已检查，属于文件首行不可见字符变化，与 P0 S1 AI 基础设施无关；本次未提交、未 stash、未删除，建议单独处理或隔离 |
| P0 AI 后端落点 | 已确认统一使用根目录 `application / domain / infrastructure / presentation / tests` 分层，不散落到 `backend/src` |
| 建议分支 | 仍建议创建 `feature/v2-p0` |
| 是否可以进入 S1 | 可以进入 S1，但建议先隔离 frontend 未提交改动 |

## 二、S0-01 设计文档冻结确认

### 2.1 P0 开发依据文档清单

本次 S0 检查确认以下无后缀正式文档存在，可作为 P0 开发依据：

| 类型 | 文档 |
|---|---|
| 需求 | `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md` |
| 概要设计 | `docs/07_overview/InkTrace-V2.0-概要设计说明书.md` |
| 架构设计 | `docs/02_architecture/InkTrace-V2.0-架构设计说明书.md` |
| P0 总纲 | `docs/03_design/InkTrace-V2.0-P0-详细设计总纲.md` |
| P0-01 | `docs/03_design/InkTrace-V2.0-P0-01-AI基础设施详细设计.md` |
| P0-02 | `docs/03_design/InkTrace-V2.0-P0-02-AIJobSystem详细设计.md` |
| P0-03 | `docs/03_design/InkTrace-V2.0-P0-03-初始化流程详细设计.md` |
| P0-04 | `docs/03_design/InkTrace-V2.0-P0-04-StoryMemory与StoryState详细设计.md` |
| P0-05 | `docs/03_design/InkTrace-V2.0-P0-05-VectorRecall详细设计.md` |
| P0-06 | `docs/03_design/InkTrace-V2.0-P0-06-ContextPack详细设计.md` |
| P0-07 | `docs/03_design/InkTrace-V2.0-P0-07-ToolFacade与权限详细设计.md` |
| P0-08 | `docs/03_design/InkTrace-V2.0-P0-08-MinimalContinuationWorkflow详细设计.md` |
| P0-09 | `docs/03_design/InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计.md` |
| P0-10 | `docs/03_design/InkTrace-V2.0-P0-10-AIReview详细设计.md` |
| P0-11 | `docs/03_design/InkTrace-V2.0-P0-11-API与集成边界详细设计.md` |
| 开发计划 | `docs/04_plan/InkTrace-V2.0-P0-开发计划.md` |

阶段细化文档已统一为正式路径：

- `docs/04_plan/InkTrace-V2.0-P0-S3S5S6-阶段细化.md`

开发计划要求中的路径同样为：

- `docs/04_plan/InkTrace-V2.0-P0-S3S5S6-阶段细化.md`

当前仓库不再保留旧 `V2_0` 文件名；全仓搜索未发现旧路径引用。

### 2.2 被忽略的历史 / 草稿 / `_001` 文档清单

P0 开发依据只使用无后缀正式文档。以下文档应作为历史、草稿或备份忽略，不进入开发依据链路：

| 文档 | 处理口径 |
|---|---|
| `docs/01_requirements/InkTrace-V2.0-需求规格说明书_001.md` | 历史 / 草稿，忽略 |
| `docs/03_design/InkTrace-V2.0-P0-06-ContextPack详细设计_001.md` | 历史 / 草稿，忽略 |
| `docs/03_design/InkTrace-V2.0-P0-08-MinimalContinuationWorkflow详细设计_001.md` | 历史 / 草稿，忽略 |
| `docs/03_design/InkTrace-V2.0-P0-09-CandidateDraft与HumanReviewGate详细设计_.md` | 异常后缀草稿，忽略 |
| `docs/03_design/InkTrace-V2.0-P0-10-AIReview详细设计_001.md` | 历史 / 草稿，忽略 |
| `docs/03_design/InkTrace-V2.0-P0-11-API与集成边界详细设计_001.md` | 历史 / 草稿，忽略 |

### 2.3 缺失文档

| 文档 | 状态 | 是否阻塞 S1 |
|---|---|---|
| 无 | P0 总纲、P0-01 至 P0-11、开发计划、S3/S5/S6 阶段细化文档均存在 | 否 |

P0 总纲与 P0-01 至 P0-11 无后缀详细设计文档均存在。

## 三、S0-02 开发分支确认

### 3.1 当前 Git 状态

| 项目 | 结果 |
|---|---|
| 当前分支 | `master` |
| 工作区是否干净 | 否 |
| 是否已创建 P0 开发分支 | 未创建 |
| 建议分支 | `feature/v2-p0` |

当前未提交改动如下：

```text
M frontend/src/components/workspace/ChapterTitleInput.vue
M frontend/src/components/workspace/PureTextEditor.vue
M frontend/src/components/workspace/StatusBar.vue
M frontend/src/components/workspace/__tests__/ChapterSidebar.spec.js
M frontend/src/components/workspace/__tests__/StatusBar.spec.js
```

### 3.2 分支建议

- 不建议在当前脏工作区直接开始 S1。
- 建议先确认上述 frontend 改动归属；若与 P0 无关，应先由当前负责人提交、暂存或另行处理。
- 建议从干净的 `master` 或 `main` 创建 `feature/v2-p0`。
- 本次 S0 未创建分支，只输出建议。

### 3.3 frontend 未提交改动处理结论

本次检查发现上述 5 个 frontend 改动均为文件首行不可见字符数量变化，未涉及 AI 基础设施、Provider、ModelRouter、AIJob、P0 API 或后端分层。处理结论如下：

- 当前未提交 frontend 改动与 P0 S1 AI 基础设施无关。
- 本次未提交、未 stash、未删除这些改动，避免误处理他人或其他任务的工作。
- 建议优先单独清理或提交这些不可见字符变化；如需要进入 P0 开发分支，建议先 stash 或另开分支保存。
- 不建议把这些 frontend 改动纳入 P0 S1 提交。

### 3.4 是否可以进入 S1 开发

结论：可以进入 S1，但需注意风险。

进入 S1 前建议先完成：

1. 处理当前 frontend 未提交改动，避免 P0 分支混入无关变更。
2. 从干净的 `master` 或 `main` 创建 `feature/v2-p0`。
3. S1 开发时按已确认的根目录分层落点组织 AI 后端模块。

## 四、S0-03 当前项目结构梳理

### 4.1 当前项目结构摘要

项目当前同时存在根目录分层与 `backend/src` 分层。

| 区域 | 路径 | 观察 |
|---|---|---|
| 前端 | `frontend/` | Vue / Pinia 前端，已有 workspace 编辑器、API 客户端、组件测试 |
| 后端主分层 | `application/`、`domain/`、`infrastructure/`、`presentation/` | 当前 V1.1 Workbench 保存链路主要落在此处 |
| 后端备用 / 第二套分层 | `backend/src/` | 存在 application / domain / infrastructure / presentation 骨架，但与当前 V1.1 路由链路不是同一主路径 |
| API Route | `presentation/api/routers/v1/` | 已有 works / chapters / sessions / outlines 等 V1.1 路由 |
| Application Service | `application/services/v1/` | 已有 Work、Chapter、Session、IO、WritingAssets 等服务 |
| Domain Entity | `domain/entities/` | 已有 Work、Chapter、EditSession、WritingAssets 等实体 |
| Repository Port | `domain/repositories/` | 已有 workbench、chapter_repository 等接口方向 |
| Infrastructure Repository | `infrastructure/database/repositories/` | 已有 WorkRepo、ChapterRepo、EditSessionRepo 等 SQLite 实现 |
| DB Schema | `infrastructure/database/v1/models.py` | V1.1 core schema，包含 works、chapters、edit_sessions 等表 |
| 测试 | `tests/`、`frontend/src/**/__tests__` | 后端与前端测试均已存在 |
| 配置 | `application/config/`、根目录 `config.py` | 已有应用配置入口 |
| Prompt | `application/prompts/` | 已有 prompts 目录，可作为 P0 PromptRegistry 落点之一 |

### 4.2 是否已有分层

| 分层 | 当前状态 |
|---|---|
| presentation | 已存在，主路径为 `presentation/api/routers/v1/` |
| application | 已存在，主路径为 `application/services/v1/` |
| domain | 已存在，包含 entities / repositories / services / value_objects |
| infrastructure | 已存在，包含 database / file / persistence / templates |

当前项目结构满足 P0 详细设计要求的分层方向，但存在根目录分层与 `backend/src` 分层并存的结构风险。

### 4.3 P0 AI 后端落点确认

本次工程整理确认：P0 AI 后端统一使用当前根目录分层，而不是把 AI 模块散落到 `backend/src`。确认落点如下：

```text
application/services/ai/
application/prompts/ai/
domain/entities/ai/
domain/repositories/ai/
domain/services/ai/
domain/value_objects/ai/
infrastructure/ai/providers/
infrastructure/database/repositories/ai/
presentation/api/routers/v2/ai/
tests/ai/
```

除非团队后续明确决定迁移主后端结构，否则 P0 AI 模块不落入 `backend/src`，也不在 P0 开发中同时维护两套 AI 后端落点。

### 4.4 S1 AI 基础设施建议新增 / 修改目录

S1 AI 基础设施建议优先落在：

| 类型 | 建议目录 | 说明 |
|---|---|---|
| AI Settings / ModelRoleConfig Entity | `domain/entities/ai/` | 放置 AI 设置、模型角色配置、调用日志等领域对象 |
| Provider / ModelRouter Port | `domain/repositories/ai/` 或 `domain/services/ai/` | 放置接口边界，避免业务服务硬编码 Provider |
| AI 基础设施 Application Service | `application/services/ai/` | 放置 AISettingsService、ModelRouterService、PromptRegistry、OutputValidation 等应用服务 |
| Prompt 模板 | `application/prompts/ai/` | 延续现有 prompts 目录，集中管理模板 |
| Provider Adapter | `infrastructure/ai/providers/` | 后续实现 Kimi / DeepSeek / mock provider adapter |
| LLMCallLog / Settings Repo | `infrastructure/database/repositories/ai/` | 后续持久化实现落点 |
| API | `presentation/api/routers/v2/ai/` | P0-11 API 方向可落在 v2/ai 路由下 |
| 测试 | `tests/ai/` | 单元测试与集成边界测试 |

### 4.5 不建议修改的既有目录

| 目录 / 文件 | 不建议修改原因 |
|---|---|
| `frontend/src/components/workspace/` | 当前已有未提交改动，S0 / S1 AI 后端基础设施不应混入编辑器 UI 改动 |
| `presentation/api/routers/v1/` | V1.1 保存链路应保持稳定；P0 AI API 建议新增 v2/ai 路由，不直接改动 V1 正文保存语义 |
| `application/services/v1/chapter_service.py` | 后续 apply 接入需谨慎复用，不应在 S1 AI 基础设施阶段修改 |
| `infrastructure/database/v1/models.py` | S0 不生成迁移；后续新增 AI 表应在明确阶段处理 |
| `backend/src/` | 除非团队决定迁移主后端结构，否则不建议 P0 AI 模块散落到第二套结构 |

## 五、S0-04 Local-First 保存链路确认

### 5.1 Local-First 保存链路调用路径

当前 V1.1 章节正文保存链路为：

```text
frontend 编辑器输入
  -> useSaveStateStore.writeLocalDraft / flushDraft
  -> v1ChaptersApi.update(chapterId, { title, content, expected_version })
  -> PUT /api/v1/chapters/{chapter_id}
  -> presentation/api/routers/v1/chapters.py:update_chapter
  -> application/services/v1/chapter_service.py:ChapterService.update_chapter
  -> infrastructure/database/repositories/chapter_repo.py:ChapterRepo.save
  -> SQLite chapters 表
```

冲突处理路径为：

```text
expected_version 与 chapter.version 不一致
  -> ChapterService.update_chapter 抛出 version_conflict
  -> API 返回 409
  -> frontend useSaveStateStore.markConflict
  -> VersionConflictModal 展示冲突处理
```

### 5.2 Work / Chapter / Session / Draft 相关模型位置

| 模型 / 概念 | 当前位置 |
|---|---|
| Work Entity | `domain/entities/work.py` |
| Chapter Entity | `domain/entities/chapter.py` |
| EditSession Entity | `domain/entities/edit_session.py` |
| Work / Chapter DB Schema | `infrastructure/database/v1/models.py` |
| Chapter Repository | `infrastructure/database/repositories/chapter_repo.py` |
| Chapter Application Service | `application/services/v1/chapter_service.py` |
| Chapter API | `presentation/api/routers/v1/chapters.py` |
| 前端本地草稿队列 | `frontend/src/stores/useSaveStateStore.js` |
| 前端 V1 API 客户端 | `frontend/src/api/works.js` |

当前没有独立的后端 Draft 表。V1.1 的“草稿区”主要表现为：

- 前端本地缓存草稿：`localCache` 中的 `draft:{workId}:{chapterId}`。
- 后端章节正文：`chapters.content`，通过 `expected_version` 乐观锁保存。

### 5.3 版本冲突检测字段

| 字段 | 位置 | 说明 |
|---|---|---|
| `version` | `chapters.version` / `Chapter.version` | 当前最主要的 content_version / chapter_revision 等价字段 |
| `expected_version` | `ChapterUpdateRequest.expected_version` | 前端保存时提交，用于乐观锁 |
| `updated_at` | Work / Chapter / EditSession | 可用于展示或辅助判断，但当前冲突判定主要靠 `version` |
| `force_override` | `ChapterUpdateRequest.force_override` | 现有覆盖保存开关，P0 apply 默认不应静默使用 |

当前未发现 `content_hash` 字段；P0-05 / P0-09 如需 content_hash，后续阶段需要新增或在应用层计算。

### 5.4 apply_candidate_to_draft 推荐接入点

P0-09 的 `apply_candidate_to_draft` 建议接入现有 V1.1 Local-First 保存链路：

- Application 层优先复用 `ChapterService.update_chapter` 的版本冲突检测与保存行为。
- API 层可通过 P0-11 的 CandidateDraft API 调用 P0-09 Application Service，再由该服务进入 V1.1 章节保存链路。
- 前端如通过 HumanReviewGate 应用候选稿，应继续尊重 `expected_version` / `base_content_version`，不得绕过 409 冲突处理。

### 5.5 CandidateDraft apply 应写入的位置

CandidateDraft apply 应写入“章节草稿区 / 正文草稿”，即当前 V1.1 章节内容保存链路管理的 `chapters.content`。它不应直接写入：

- confirmed chapter analysis。
- StoryMemorySnapshot。
- StoryState analysis_baseline。
- VectorIndex。
- ContextPack。

apply 成功后，章节变更如何触发 stale / reanalysis / reindex，应由 P0-03 / P0-04 / P0-05 或后续实现承接。

### 5.6 append / replace_selection / insert_at_cursor 支持情况

| apply_mode | 当前链路支持情况 | S1 后续建议 |
|---|---|---|
| `append_to_chapter_end` | 可通过应用层先拼接完整 content，再调用 `update_chapter` 保存 | 需要在 CandidateDraftService 中基于当前 content / version 生成新 content |
| `replace_selection` | 后端保存接口不直接支持 selection_range；只能保存完整 content | 需要在 apply 层校验 selection_range，并生成完整 content 后保存 |
| `insert_at_cursor` | 后端保存接口不直接支持 cursor_position；只能保存完整 content | 需要在 apply 层校验 cursor_position，并生成完整 content 后保存 |
| `replace_chapter_draft` | 当前可技术上覆盖完整 content，但 P0-09 / P0-11 默认不支持整章静默覆盖 | 不应作为 P0 默认能力 |

### 5.7 当前缺口 / 风险

- 当前后端没有独立 CandidateDraft 表、状态机、审计日志。
- 当前 chapters 表没有明确 `confirmed` 字段；`ChapterStatus` 在实体中存在 DRAFT / PUBLISHED，但 active v1 schema 默认不持久化 status，Repository 读取时统一返回 DRAFT。
- 当前没有 `content_hash` 字段。
- 当前 replace_selection / insert_at_cursor 需要在 apply 层完成内容变换，保存接口只接收完整 content。
- 当前 force_override 存在，但 P0 apply 默认不得静默覆盖用户正文。

## 六、S0-05 Work / Chapter 数据结构确认

### 6.1 Work 字段摘要

| 字段 | 来源 | 说明 |
|---|---|---|
| `id` | `domain/entities/work.py` / `works.id` | work_id |
| `title` | Work entity / DB | 作品标题 |
| `author` | Work entity / DB | 作者 |
| `word_count` | Work entity / DB | 当前字数 |
| `created_at` | Work entity / DB | 创建时间 |
| `updated_at` | Work entity / DB | 更新时间 |

### 6.2 Chapter 字段摘要

| 字段 | 来源 | 说明 |
|---|---|---|
| `id` | `Chapter.id` / `chapters.id` | chapter_id |
| `work_id` | `Chapter.work_id` / `chapters.work_id` | 所属作品 |
| `title` | Chapter entity / DB | 章节标题 |
| `content` | Chapter entity / DB | 章节正文内容 |
| `order_index` | Chapter entity / DB | 章节顺序；API 同时暴露 `chapter_number` |
| `version` | Chapter entity / DB | 乐观锁版本，可作为 P0 content_version / chapter_revision 最小等价字段 |
| `word_count` | DB / entity 派生 | 章节字数 |
| `created_at` | Chapter entity / DB | 创建时间 |
| `updated_at` | Chapter entity / DB | 更新时间 |
| `status` | Chapter entity | 实体层存在 DRAFT / PUBLISHED，但 active v1 schema 默认未持久化 |
| `summary` | Chapter entity 可选字段 | active v1 repository 当前未从主 schema 读取 |
| `characters_involved` | Chapter entity 可选字段 | active v1 repository 当前未从主 schema 读取 |

### 6.3 confirmed chapters 判定建议

当前实现没有稳定持久化的 `confirmed` 状态。P0 初始化读取 confirmed chapters 建议采用以下最小策略：

1. 默认将已通过 V1.1 保存链路持久化到 `chapters` 表、属于当前 work_id、按 `order_index` 排序的章节作为 P0 confirmed chapters 候选输入。
2. 空章节仍可被读取，但 P0-03 / P0-05 应按冻结设计记录 warning，不应创建有效 chunk 或正式分析结果。
3. CandidateDraft、Quick Trial、临时候选区、未保存本地草稿不得写入 `chapters` 表；因此默认不会被初始化读取为 confirmed chapters。
4. 如果后续新增 confirmed / draft / published 明确状态，应优先使用该状态作为 confirmed 判定来源。
5. 在当前 schema 下，`ChapterStatus.PUBLISHED` 不能作为可靠 confirmed 判定，因为 active v1 schema 默认没有 `status` 列，`ChapterRepo._row_to_entity` 固定返回 DRAFT。

### 6.4 P0 初始化读取 confirmed chapters 的推荐接口

推荐入口：

```text
ChapterService.list_chapters(work_id)
  -> ChapterRepo.list_by_work(work_id)
  -> chapters 按 order_index 升序返回
```

后续 P0-03 初始化服务应通过 Application Service 或受控 RepositoryPort 读取章节，不应直接绕过现有保存链路访问前端本地草稿。

### 6.5 CandidateDraft / Quick Trial 排除策略

当前 CandidateDraft / Quick Trial 尚未实现。P0 后续实现时必须保持：

- CandidateDraft 存储在独立候选稿结构中，不属于 `chapters` confirmed 正文。
- Quick Trial 默认只返回 transient output，不写 CandidateDraft，不写 `chapters`。
- Quick Trial 只有用户明确“保存为候选稿”后，才进入 P0-09 CandidateDraft 流程，仍不进入 confirmed chapters。
- CandidateDraft 只有用户 accept 并 apply，且通过 V1.1 Local-First 保存链路写入章节草稿区后，才可能通过后续 reanalysis / reindex 影响正式上下文。

### 6.6 现有字段是否满足 P0-03 / P0-04 / P0-09

| 需求 | 当前满足情况 | 说明 |
|---|---|---|
| `work_id` / `chapter_id` / `chapter_order` | 基本满足 | `work_id`、`id`、`order_index` 已存在 |
| 正文内容字段 | 满足 | `chapters.content` |
| 版本冲突 | 基本满足 | `version` + `expected_version` + 409 `version_conflict` |
| `content_hash` | 不满足 | 后续 VectorIndex / Embedding 需要新增或应用层计算 |
| `content_version` / `chapter_revision` | 部分满足 | 可先映射到 `version`，但命名和语义需在 P0 实现中统一 |
| confirmed chapters 显式状态 | 不满足 | active schema 无 confirmed 状态；需最小判定策略或新增状态设计 |
| CandidateDraft 状态机 | 不满足 | 后续 P0-09 实现新增 |
| StoryMemory / StoryState 数据结构 | 不满足 | 后续 P0-04 实现新增 |
| VectorIndex 数据结构 | 不满足 | 后续 P0-05 实现新增 |
| initialization_status | 不满足 | 后续 P0-03 / P0-02 实现新增 |

## 七、S0-06 风险点登记

| 风险 | 影响 | 缓解措施 | 是否阻塞 S1 |
|---|---|---|---|
| Provider 稳定性 | 初始化、续写、审阅可能 timeout / rate_limited / unavailable | S1 严格按 P0-01 ProviderPort、retry、timeout、LLMCallLog、safe error 实现；先接 mock / test double | 否 |
| 初始化成本 | 全书分析、章节分析和向量构建可能耗时高、成本高 | 按 P0-03 分 Step、可取消、可 retry；VectorIndex 失败可降级；普通日志不记录正文 | 否 |
| ContextPack token 超预算 | Writer Prompt 超限，导致续写失败或上下文质量下降 | 按 P0-06 TokenBudgetPolicy、required / optional 裁剪、trim_reason 落地 | 否 |
| VectorRecall 可降级实现 | VectorIndex failed / stale 可能影响正式续写体验 | 按 P0-05 / P0-06 让 RAG 层 degraded，不阻断 StoryMemory / StoryState 完整路径 | 否 |
| apply 版本冲突 | CandidateDraft 应用时覆盖用户最新编辑 | 复用 `expected_version` / `version_conflict`；apply 前校验 `base_content_version`；禁止静默 force_override | 是，需在 P0-09 / P0-11 实现时重点控制 |
| Local-First 保存链路接入风险 | AI apply 可能绕过现有前端本地草稿和 409 冲突体验 | P0 apply 只进入 V1.1 保存链路；不直接写正式正文；冲突返回 `chapter_version_conflict` | 是，需在 P0-09 实现前确认调用路径 |
| 日志误记敏感内容 | 正文、Prompt、CandidateDraft、API Key 泄露 | 统一 safe refs、trace_id、audit log；普通日志不记录完整正文 / Prompt / API Key | 否，但需贯穿所有阶段 |
| CandidateDraft 状态机实现风险 | accepted / applied 混淆会导致未确认 AI 输出进入正式正文 | P0-09 状态机作为权威；accepted != applied；HumanReviewGate 必须 user_action | 否，但需测试覆盖 |
| S3 / S5 / S6 跨模块边界风险 | Initialization、Workflow、CandidateDraft、API 容易交叉写入非本模块资产 | 按阶段细化执行；使用 Application Service / ToolFacade 边界；避免直接 Repo / Provider 调用 | 否 |
| 现有代码结构与 P0 分层设计不匹配 | 根目录分层与 `backend/src` 并存，可能导致重复实现 | 已确认 P0 AI 后端统一使用根目录分层；`backend/src` 暂不作为 P0 AI 落点 | 否 |
| S3/S5/S6 计划文档命名不一致 | 后续自动化或人工引用可能找不到文档 | 已统一为 `docs/04_plan/InkTrace-V2.0-P0-S3S5S6-阶段细化.md`，旧 `V2_0` 引用为空 | 否 |
| 当前工作区存在 frontend 未提交改动 | P0 分支可能混入无关 UI 改动 | 进入 S1 前提交、暂存或确认保留这些改动 | 是，工程管理层面阻塞 |
| confirmed chapters 判定不显式 | 初始化可能把不应分析的内容当作正式章节，或漏读章节 | P0 最小策略使用 `chapters` 已保存内容；后续可补 confirmed status；CandidateDraft / Quick Trial 独立存储 | 否，但需在 S1/S3 明确 |
| replace_selection / insert_at_cursor 缺少后端原生接口 | apply 逻辑需要自行拼接完整 content，容易出错 | 在 CandidateDraftService 中实现定位校验、版本校验、完整 content 生成，再调用现有保存接口 | 否，但需测试覆盖 |

## 八、进入 S1 前必须确认的问题

1. 当前 `frontend/src/components/workspace/*` 和相关测试的未提交改动是否由当前负责人提交、stash、另开分支保存或清理；进入 P0 S1 前不应混入 P0 提交。
2. 创建 `feature/v2-p0` 前是否需要先保持工作区干净。
3. P0 AI 后端实现落点已确认统一使用根目录 `application / domain / infrastructure / presentation / tests` 分层；后续若迁移到 `backend/src`，需单独决策。
4. S1 是否先以 mock / fake Provider 验证 ProviderPort、ModelRouter、PromptRegistry、OutputValidation、LLMCallLog 边界，再接真实 Kimi / DeepSeek。
5. `model_role` 默认映射与 AI Settings 的初始配置来源应按 P0-01 落地，不应在业务服务、Workflow、ToolFacade 或 API 层硬编码 Provider。
6. CandidateDraft apply 是否统一通过 `ChapterService.update_chapter` 进入 V1.1 保存链路，而不是新增正文直写通道。
7. confirmed chapters 的 P0 最小判定是否接受“已持久化到 chapters 表的章节”为初始依据，并把空章节作为 warning 处理。
8. 是否需要在后续迁移中补充 `content_hash`、AI 相关状态表、CandidateDraft 表和审计表；S0 不生成迁移。

## 九、S1 开发落点建议

S1 应只进入 AI 基础设施，不实现 Provider / ModelRouter 的完整业务使用链路以外功能。建议落点如下：

| S1 内容 | 建议落点 |
|---|---|
| AI Settings / ModelRoleConfig | `domain/entities/ai/`、`application/services/ai/ai_settings_service.py` |
| ProviderPort / Provider Adapter 边界 | `domain/services/ai/` 或 `domain/repositories/ai/`、`infrastructure/ai/providers/` |
| ModelRouter | `application/services/ai/model_router.py` |
| PromptRegistry | `application/services/ai/prompt_registry.py`、`application/prompts/ai/` |
| OutputValidation | `application/services/ai/output_validation_service.py` |
| LLMCallLog / safe logging | `domain/entities/ai/llm_call_log.py`、`infrastructure/database/repositories/ai/` |
| AI Settings API | `presentation/api/routers/v2/ai/settings.py` 或等价 v2/ai 路由 |
| 测试 | `tests/ai/` |

S1 不建议修改：

- `frontend/src/components/workspace/` 当前未提交文件。
- V1.1 `PUT /api/v1/chapters/{chapter_id}` 保存语义。
- `ChapterService.update_chapter` 的冲突处理语义。
- P0 详细设计文档。
- 数据库迁移文件。

S1 推荐优先建立以下安全基线：

1. 业务服务只提交 `model_role`，不硬编码 Kimi / DeepSeek。
2. API Key 只允许写入 / 更新，不允许读取明文。
3. Provider timeout / rate_limited / unavailable 按 P0-01 retry；auth failed 不 retry。
4. LLMCallLog / 普通日志不记录完整正文、完整 Prompt、API Key。
5. 输出校验失败按 P0-01 规则重试，禁止无限重试。
6. 所有 AI 调用贯穿 `request_id` / `trace_id`。

