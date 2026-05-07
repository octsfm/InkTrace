# InkTrace 项目现状报告

> 生成时间：2026-05-07
> 版本：V1.1（完整落地）

---

## 1. 项目概述

**InkTrace**（墨迹）是一个面向长篇小说的辅助写作工作台，定位为**作者代理工作系统（Author Agent Work System）**。项目采用 C/S 架构（桌面客户端 + Web 前端 + Python 后端），以 Local-First 为核心理念，提供离线优先的写作体验。

项目当前处于 **V1.1 完整封版**阶段。V1.1 是在 V2 AI 接入前的纯文本写作工作台封版版本，完成了写作体验收口、数据闭环增强与结构化写作资产沉淀。V1.1 明确禁止 AI 入口，所有新增功能均落在 Workbench 域，与 Legacy AI 域完全隔离。

---

## 2. 技术栈

### 后端

| 技术 | 用途 | 版本 |
|---|---|---|
| Python | 运行时语言 | 3.11+ |
| FastAPI | Web 框架 | >=0.104.0 |
| Uvicorn | ASGI 服务器 | >=0.24.0 |
| SQLAlchemy | ORM 框架 | 2.0+ |
| SQLite | 数据库引擎 | WAL 模式 |
| Pydantic | 数据校验 | >=2.5.0 |

### 前端

| 技术 | 用途 |
|---|---|
| Vue 3 | 前端框架（Composition API + `<script setup>`） |
| Pinia | 状态管理（5 个独立 Store） |
| Vue Router | 路由管理 |
| Element Plus | UI 组件库 |
| Axios | HTTP 客户端 |
| Vite | 构建工具 |
| Vitest | 单元测试框架 |
| @vue/test-utils | 组件测试工具 |

### 桌面端

| 技术 | 用途 |
|---|---|
| Electron | 桌面壳 |
| electron-builder | 打包分发 |

---

## 3. 架构总览

### 3.1 分层架构（DDD 四层）

```
┌─────────────────────────────────────────────────┐
│              Presentation (API)                  │
│   /api/v1/* routers + schemas + error handlers  │
├─────────────────────────────────────────────────┤
│              Application (Services)              │
│   WorkService / ChapterService / SessionService  │
│   IOService / WritingAssetService                │
├─────────────────────────────────────────────────┤
│               Domain (Entities)                  │
│   Work / Chapter / EditSession / WritingAsset    │
│   + Repository Interfaces + Value Objects        │
├─────────────────────────────────────────────────┤
│           Infrastructure (Database)              │
│   SQLAlchemy ORM / Repositories / SQLite WAL     │
└─────────────────────────────────────────────────┘
```

### 3.2 V1.1 核心域

V1.1 新增 **Workbench (工作台) 域**，与 Legacy AI 域完全隔离：

- **Workbench 域**（V1.1 新增）：
  - `presentation/api/routers/v1/` — 路由层
  - `application/services/v1/` — 服务层
  - `frontend/src/views/` (WorksList, WritingStudio) + `components/workspace/` — 前端
  - `frontend/src/stores/` (useWorkspaceStore, useChapterDataStore, useSaveStateStore, useWritingAssetStore, usePreferenceStore) — 前端状态
  - `infrastructure/database/repositories/` — 仓储实现
  - 严格禁止引用 Legacy Store/UI/API/Service

- **Legacy AI 域**（V1 遗留/冻结）：
  - AI Agent 编排 (`agent_mvp/`)
  - AI 写作服务 (`writing_service_v2`, `chapter_ai`, `continuation_writer` 等)
  - AI 实体（Arc, Character, Worldview, Foreshadow 等）
  - LLM 客户端 (`infrastructure/llm/`)
  - 前端旧 Store (`stores/novelWorkspace.js`, `stores/workspace.js`)

### 3.3 数据库（8 表）

| 表 | 用途 | 乐观锁 |
|---|---|---|
| `works` | 作品 | — |
| `chapters` | 章节 | `version` |
| `edit_sessions` | 编辑会话 | — |
| `work_outlines` | 全书大纲 | `version` |
| `chapter_outlines` | 章节细纲 | `version` |
| `timeline_events` | 时间线事件 | `version` |
| `foreshadows` | 伏笔 | `version` |
| `characters` | 人物 | `version` |

### 3.4 Local-First 保存链路

```
用户输入 → 内存更新 → 本地缓存 (localStorage) → debounce 2-3s → API 同步 → 清理缓存
                                                                  ↓ 失败
                                                        指数退避重试 / 离线队列
                                                                  ↓ 409
                                                        冲突弹窗（覆盖 / 放弃 / 取消）
```

---

## 4. V1.1 实现状态

### 总体进度：**全部完成**（7/7 阶段，~70+ 任务）

| 阶段 | 内容 | 状态 | 前置条件 |
|---|---|---|---|
| Stage 0 | 基线校准与隔离检查 | **已完成** | — |
| Stage 1 | V1.1-A 后端收口 | **已完成** | Stage 0 |
| Stage 2 | V1.1-A 前端收口 | **已完成** | Stage 1 |
| Stage 3 | V1.1-B 后端结构化资产 | **已完成** | Stage 2 |
| Stage 4 | V1.1-B 前端结构化资产 | **已完成** | Stage 3 |
| Stage 5 | 稳定性与验收 | **已完成** | Stage 4 |
| Stage 6 | V1.1-C 可选增强 | **已完成** | Stage 5 |

### 4.1 V1.1-A：写作体验与数据闭环收口

| 模块 | 组件/文件 | 状态 |
|---|---|---|
| **书架页** | WorksList.vue, WorkCard.vue, CreateWorkModal.vue | **完成** |
| **写作页** | WritingStudio.vue（三段式布局） | **完成** |
| **章节侧栏** | ChapterSidebar.vue（虚拟滚动、搜索、跳转、新建、拖拽排序草案） | **完成** |
| **章节标题** | ChapterTitleInput.vue（展示"第X章"，保存不写前缀） | **完成** |
| **正文编辑器** | PureTextEditor.vue（纯文本 textarea，拦截富文本粘贴） | **完成** |
| **状态条** | StatusBar.vue（saving/synced/offline/conflict/error） | **完成** |
| **Header** | WritingStudio 内嵌（作品名、重命名） | **完成** |
| **Workspace Store** | useWorkspaceStore（会话管理） | **完成** |
| **Chapter Store** | useChapterDataStore（章节数据） | **完成** |
| **Save Store** | useSaveStateStore（保存状态机、离线回放） | **完成** |
| **本地缓存** | useLocalCache composable + utils/localCache.js（LRU 淘汰，10MB 上限） | **完成** |
| **TXT 导入** | ImportModal.vue + io_service.py（编码识别、分章、20MB 上限） | **完成** |
| **TXT 导出** | ExportTxtModal.vue（含 include_titles / gap_lines 选项） | **完成** |
| **版本冲突** | VersionConflictModal.vue（覆盖 / 放弃 / 取消） | **完成** |
| **后端服务** | WorkService, ChapterService, SessionService, IOService | **完成** |
| **后端 API** | `/api/v1/works/*`, `/api/v1/chapters/*`, `/api/v1/sessions/*`, `/api/v1/io/*` | **完成** |

### 4.2 V1.1-B：结构化写作资产

| 模块 | 组件/文件 | 状态 |
|---|---|---|
| **AssetRail** | AssetRail.vue（4 图标入口） | **完成** |
| **AssetDrawer** | AssetDrawer.vue（单抽屉、单 Tab、dirty 切换保护） | **完成** |
| **全书大纲面板** | OutlinePanel.vue（content_text 编辑 + content_tree_json 缓存） | **完成** |
| **章节细纲面板** | OutlinePanel.vue 内嵌（切章自动加载） | **完成** |
| **时间线面板** | TimelinePanel.vue（CRUD、排序、章节引用） | **完成** |
| **伏笔面板** | ForeshadowPanel.vue（open/resolved、章节引用） | **完成** |
| **人物面板** | CharacterPanel.vue（name/aliases/description、搜索） | **完成** |
| **资产冲突弹窗** | AssetConflictModal.vue（覆盖/放弃/取消） | **完成** |
| **资产 Store** | useWritingAssetStore（读取、编辑、显式保存、冲突） | **完成** |
| **后端服务** | WritingAssetService（5 类资产 CRUD + 乐观锁） | **完成** |
| **后端 API** | `/api/v1/works/{id}/outline`, `/timeline-events`, `/foreshadows`, `/characters` | **完成** |
| **后端仓储** | 6 个 Repository（work_repo, chapter_repo, edit_session_repo, outline_asset_repo, timeline_event_repo, foreshadow_repo, character_repo） | **完成** |

### 4.3 V1.1-C：体验偏好增强（可选）

| 模块 | 组件/文件 | 状态 |
|---|---|---|
| **专注模式** | FocusModeToggle.vue | **完成** |
| **写作偏好** | WritingPreferencePanel.vue（字体、字号、行距、主题） | **完成** |
| **今日新增字数** | 内嵌于 StatusBar / PureTextEditor | **完成** |
| **立即同步** | ManualSyncButton.vue | **完成** |
| **偏好 Store** | usePreferenceStore（localStorage 持久化） | **完成** |

---

## 5. 项目指标

### 5.1 统计数据

| 维度 | 数量 |
|---|---|
| **Python 源文件** | 182 文件（~17,946 行） |
| **Vue 组件** | 26 文件（~8,078 行） |
| **JS 源文件** | ~5,400+ 文件（含 node_modules 依赖） |
| **后端 V1.1 服务** | 5 个服务（~900+ 行） |
| **后端 V1.1 API** | 10 个 Router 文件 |
| **前端 Store** | 5 个 (useWorkspaceStore / useChapterDataStore / useSaveStateStore / useWritingAssetStore / usePreferenceStore) |
| **前端组件** | 22 个 Vue 组件 |
| **Python 测试** | 37 个文件（含 34 个 `test_v1_*`） |
| **前端测试** | 32 个 `.spec.js` 文件 |
| **设计文档** | 4 份（需求/架构/详细设计/界面交互） |
| **开发计划** | 1 份（7 阶段 ~70+ 任务） |

### 5.2 测试覆盖

- **后端测试**：涵盖所有 V1.1 服务、仓储、路由、数据模型、Schema 校验、乐观锁冲突、TXT 导入导出边界
- **前端测试**：涵盖所有组件渲染与交互、Store 逻辑、本地缓存、路由守卫

### 5.3 数据口径

| 口径 | 规则 |
|---|---|
| `word_count` | 服务端按 `text_metrics.py` 重算（去空白有效字符数） |
| `title` | 后端统一存空字符串，不存 NULL |
| `order_index` | 唯一排序依据，连续正整数 |
| `version` | 资源级自增，冲突返回 409 |
| aliases | JSON array，服务端 trim、去重、去空 |
| `content_tree_json` | Schema 白名单校验 |
| 时间格式 | ISO 8601 统一时区 |

---

## 6. 设计偏差记录

以下为审计过程中发现的与详细设计文档之间的偏差：

| 偏差描述 | 严重性 | 影响 | 处理建议 |
|---|---|---|---|
| `infrastructure/database/v1/models.py` 和 `session.py` 未实际运行 | 低 | 无功能影响，无法通过代码评审发现 | 建议清理到 `v1/` 目录或确认其用途 |
| Repository 路径为 `infrastructure/database/repositories/` 而非设计文档的 `v1/repositories/` | 低 | 架构命名偏差，不影响功能 | 下个版本统一整理 |
| 无 `base_repository.py` 基类 | 低 | 乐观锁逻辑内联在各 Service 中，可维护性略低 | 下个版本可提取 |
| Work 实体缺少 `version` 字段 | 低 | 作品暂不支持乐观锁，扩展时需补充 | 后续需要时补充 |

---

## 7. 后续规划

### V2 AI 接入

当前 V1.1 已完成非 AI 创作工作台的封版目标。下一阶段 V2 将在 Workbench 域基础上扩展 AI 能力，预计方向包括：

- AI 续写与扩写
- AI 大纲生成
- AI 角色/世界观辅助构建
- 基于结构化资产的智能分析
- 提示词（Prompt）工程接入

### 技术债务

- 清理 `infrastructure/database/v1/` 下的未使用文件
- 统一 Repository 命名路径
- 提取 BaseRepository 基类
- 清理 Legacy AI 域中的死代码

---

## 8. V1.1 封版检查清单

- [x] Workbench 与 Legacy 隔离通过
- [x] `/api/v1/*` API 清单全部可用
- [x] 正文 Local-First 保存链路通过
- [x] 切章、刷新、离线、409 不丢字
- [x] TXT 导入导出闭环通过
- [x] AssetDrawer 单抽屉、单 Tab 约束通过
- [x] Outline / Timeline / Foreshadow / Character 全部可 CRUD
- [x] 结构化资产显式保存与 409 冲突通过
- [x] 删除章节引用清理通过
- [x] textMetrics / aliases / content_tree_json schema 口径通过
- [x] Timeline 完整映射提交与单事务写入通过
- [x] 无 AI 入口、无自动生成、无自动分析、无自动抽取
- [x] V1.1-A/B/C DoD 全部通过
