# InkTrace V1.1 架构设计文档（非 AI 创作工作台）

版本：v1.1  
更新时间：2026-04-29  
对应需求：[InkTrace-V1.1-需求规格说明书（非AI写作增强）.md](file:///workspace/docs/InkTrace-V1.1-%E9%9C%80%E6%B1%82%E8%A7%84%E6%A0%BC%E8%AF%B4%E6%98%8E%E4%B9%A6%EF%BC%88%E9%9D%9EAI%E5%86%99%E4%BD%9C%E5%A2%9E%E5%BC%BA%EF%BC%89.md)

---

## 1. 架构目标与阶段关系

### 1.1 阶段关系（不再混用 AI 语义）

- V1：稳定纯文本写作底座
- V1.1：非 AI 创作工作台（写作体验收口 + 结构化写作资产沉淀）
- V2：基于结构化资产接入 AI 能力（只在 V2 接入 AI）

### 1.2 V1.1 的交付批次

- V1.1-A：写作体验与数据闭环收口（可单独提测）
- V1.1-B：非 AI 写作组织能力（完成后才视为 V1.1 完整完成）
- V1.1-C：体验偏好增强（可选交付，不影响 V1.1 完整性定义）

### 1.3 核心设计原则

- 正文区优先：中间正文区只呈现“标题输入框 + 正文 + 必要状态”
- Non‑AI Boundary：V1.1 禁止任何正文生成/分析/推荐；结构化资产全部由用户手写维护
- Local‑First（仅限正文）：正文输入立即写本地缓存，debounce(2–3s) 同步服务端，成功清缓存
- 显式保存（结构化资产）：V1.1‑B 资产采用“显式保存 + expected_version 乐观锁”
- 原子提交：章节调序与时间线调序均采用“单次提交映射列表 + 后端单事务写入”

---

## 2. 总体系统架构（分域隔离）

当前代码库仍包含旧 AI 工作台（novel/workspace/copilot 等）。V1.1 采用“并行新域”方式落地：

- **Legacy 域**：保留现有 `/novels`、`/novel/:id` 等路由与旧 API（不在 V1.1 继续扩展）
- **Workbench 域（V1.1）**：新增 `/works`、`/works/:id` 以及 `/api/v1/*` API，作为 V1.1 的唯一依赖

目标是实现“软隔离”：
- 用户默认进入 Workbench
- Legacy 仅用于历史兼容或开发期回溯

---

## 3. 后端架构（FastAPI + SQLite）

### 3.1 分层结构

后端按四层分离（保持现有工程风格，新增子域目录，不改动旧域）：

- Presentation（API 路由）
- Application（服务编排）
- Domain（实体/值对象/领域异常）
- Infrastructure（SQLite 持久化实现）

建议新增目录（示例命名，可按实际工程习惯调整，但保持域隔离）：

- `presentation/api/routers/v1/`：V1.1 Workbench API（works/chapters/sessions/io/outlines/timeline/foreshadows/characters）
- `application/services/v1/`：V1.1 Workbench Service
- `domain/entities/v1/`：V1.1 Workbench Entity（避免复用旧 AI 语义实体）
- `infrastructure/persistence/sqlite_v1/`：V1.1 Workbench Repo（或复用既有 sqlite repo 命名体系）

### 3.2 API 命名与版本策略

- V1.1 Workbench API 统一前缀：`/api/v1`
- Legacy API 维持现状（不在本文档范围扩展）

### 3.3 数据库（SQLite）与事务策略

统一要求：

- 所有表含 `created_at`、`updated_at`
- 需要冲突控制的资源含 `version`（int，从 1 开始）
- 所有“重排”接口采用单事务写入；失败回滚，避免半成功状态

#### 3.3.1 V1.1-A 核心表

**works**
- `id` uuid pk
- `title` text
- `author` text nullable
- `created_at` / `updated_at`

**chapters**
- `id` uuid pk
- `work_id` uuid fk
- `title` text nullable（仅存用户标题，不存“第X章”前缀）
- `content` text
- `word_count` int
- `order_index` int（唯一顺序依据，从 1 连续）
- `version` int（乐观锁）
- `created_at` / `updated_at`

**edit_sessions**
- `work_id` uuid pk
- `last_open_chapter_id` uuid nullable
- `cursor_position` int
- `scroll_top` int
- `updated_at`

#### 3.3.2 V1.1-B 结构化资产表

**work_outlines**
- `id` uuid pk
- `work_id` uuid unique
- `content_text` text
- `content_tree_json` json nullable
- `version` int
- `created_at` / `updated_at`

**chapter_outlines**
- `id` uuid pk
- `chapter_id` uuid unique
- `content_text` text
- `content_tree_json` json nullable
- `version` int
- `created_at` / `updated_at`

**timeline_events**
- `id` uuid pk
- `work_id` uuid
- `order_index` int（从 1 连续）
- `title` text
- `description` text
- `chapter_id` uuid nullable（关联章节）
- `created_at` / `updated_at`

**foreshadows**
- `id` uuid pk
- `work_id` uuid
- `status` text（open|resolved）
- `title` text
- `description` text
- `introduced_chapter_id` uuid nullable
- `resolved_chapter_id` uuid nullable
- `created_at` / `updated_at`

**characters**
- `id` uuid pk
- `work_id` uuid
- `name` text
- `description` text
- `aliases` json array nullable
- `created_at` / `updated_at`

### 3.4 关键业务流程（后端）

#### 3.4.1 更新章节（title + content 同次提交）

- 输入：`chapter_id`、`title?`、`content?`、`expected_version`、`force_override?`
- 处理：
  - 查询章记录
  - 校验 `chapter.version == expected_version`，不匹配返回 409（除非 force_override）
  - 更新 `title/content/word_count`，`version += 1`，写入 `updated_at`
- 输出：最新 Chapter DTO

#### 3.4.2 新建章节（默认追加到末尾）

前端默认规则为“追加末尾”，后端提供两种能力：

- `POST /api/v1/works/{work_id}/chapters`：
  - 支持 `after_chapter_id`（用于未来“在此章后新增”二级操作）
  - 若未传 `after_chapter_id`，后端默认追加到末尾（计算 max(order_index)+1）
  - 新章默认 `title=null`（前端展示 `第X章`），避免写入“第X章”到 title

#### 3.4.3 章节调序（原子提交）

- `PUT /api/v1/works/{work_id}/chapters/reorder`
- 入参：`[{ id, order_index }]`（或前端传 id list，后端映射为连续 order_index）
- 后端必须单事务：
  - 校验：数量一致、都属于 work、order_index 连续唯一
  - 批量 update
  - commit/rollback

#### 3.4.4 Timeline 调序（原子提交）

- `PUT /api/v1/works/{work_id}/timeline/reorder`
- 入参：`[{ id, order_index }]`
- 后端单事务写入（同章节调序）

#### 3.4.5 删除规则（安全优先）

- 删除章节：
  - chapter_outlines：随章节删除（一对一）
  - timeline_events.chapter_id：置空
  - foreshadows.introduced_chapter_id/resolved_chapter_id：置空
  - work_outlines：不受影响
- 删除作品：
  - 级联删除 works 下 chapters/edit_session
  - 级联删除 work_outlines/timeline_events/foreshadows/characters

---

## 4. 前端架构（Vue3 + Pinia + Element Plus）

### 4.1 路由与页面

V1.1 Workbench 新路由：

- `/works`：书架（WorksList）
- `/works/:id`：写作页（WritingStudio）

Legacy 路由保持（不扩展）：
- `/novels`、`/novel/:id` 等

### 4.2 组件拆分（写作页极简优先）

**WorksList**
- WorkCard（卡片 + `(...)` 菜单：重命名/改作者/删除）
- CreateWorkModal（新建作品）
- ImportTxtModal（Web 上传导入）

**WritingStudio**
- ChapterSidebar（章节列表 + 搜索 + 跳转第 N 章 + 新章）
- ChapterTitleInput（居中标题输入框，B2）
- PureTextEditor（纯文本正文输入）
- StatusBar（轻量状态：保存中/已同步/离线/冲突）
- WorkbenchDrawer（右侧抽屉容器：Outline/Timeline/Foreshadow/Character）

### 4.3 状态域与 Store 拆分

建议将 V1.1 Store 与 Legacy Store 分离命名，避免互相污染：

- `useWorkStoreV1`：作品列表、当前作品信息（title/author）
- `useChapterStoreV1`：章节列表、activeChapterId、chapter drafts（内存态）
- `useSaveQueueStoreV1`：正文 Local‑First 队列（pendingQueue、saveStatus、retry/409）
- `useWorkbenchAssetsStoreV1`：结构化资产编辑状态（Outline/Timeline/Foreshadow/Character）
  - V1.1-B 默认显式保存，不进入正文队列

### 4.4 Local‑First 设计边界（只覆盖正文）

**正文（V1.1-A）**

- localStorage LRU key：`draft:{workId}:{chapterId}`
- payload：`{ chapterId, content, title, version, cursorPosition, scrollTop, timestamp }`
- queue：按 timestamp 合并后串行回放（已有设计可复用）

**结构化资产（V1.1-B）**

- 离线暂存：允许用 localStorage 暂存当前编辑内容（例如 `asset_draft:{type}:{id}`）
- 不进入自动回放队列：联网后不自动提交，必须用户手动点击“保存”

### 4.5 409 冲突处理复用策略

- 正文冲突：复用现有“覆盖/放弃”弹窗模型
- 结构化资产冲突：同样采用 expected_version → 409 → 覆盖/放弃，但 UI 更轻量（可直接在抽屉内提示）

### 4.6 抽屉容器（V1.1-B）交互与焦点

- 同一时间只允许一个抽屉打开
- 打开/关闭抽屉不主动改变正文焦点
- 用户主动点击抽屉输入框时允许焦点进入抽屉
- 关闭抽屉不强制抢回正文焦点（但可提供快捷键返回正文）

---

## 5. 测试与验收（与 DoD 对齐）

### 5.1 V1.1-A

- 写作页极简布局：正文不被挤压
- 新建章节追加末尾 + 自动聚焦
- 搜索/跳转第 N 章与激活项可见
- Web 上传导入（空文件/无章节标记/编码/大小）与导出格式选项
- Local‑First：断网可写、联网回放、409 冲突处理

### 5.2 V1.1-B

- 显式保存与 expected_version 乐观锁
- Timeline 原子调序提交
- 删除章节后引用置空策略

---

## 6. 与 V2 的衔接约束（架构层）

- V1.1 不包含 AI 调用入口、Prompt、模型配置与密钥管理
- V2 只能读取 V1.1 结构化资产，不得直接覆盖手写资产
- V2 若生成内容，必须写入“候选草稿/候选建议”表或草稿区，由用户确认后再写入正文

