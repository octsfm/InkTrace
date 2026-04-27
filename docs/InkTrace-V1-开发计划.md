# InkTrace V1 开发计划

更新时间：2026-04-27
依据文档：需求规格说明书 v1.1 / 架构设计文档 / 详细设计文档 / 界面与交互设计文档

---

## 一、总体策略

### 1.1 现状说明

现有代码库存在大量 AI 工作流遗留代码（agent_mvp、Arc 剧情弧、LLM 客户端、向量存储、角色/世界观管理等），需要先清理再构建 V1 纯文本写作功能。

### 1.2 开发原则

- **分阶段交付**：P0 可用 → P1 稳定 → P2 收口，每个阶段可独立验收。
- **先清理后建设**：遗留系统清理作为独立任务，不影响新功能工期估算。
- **增量可测试**：每个模块完成后立即编写测试，缩短反馈周期。
- **前后端并行**：前端独立开发（Mock 数据），减少对后端的阻塞。

### 1.3 工作量估算

| 阶段 | 估算工时 | 交付物 |
|------|----------|--------|
| Stage 0: 遗留清理 | 2-3 天 | 干净的项目基线 |
| Stage 1: P0 基础设施 | 5-7 天 | 可用的写作工具核心链路 |
| Stage 2: P1 稳定性增强 | 3-5 天 | 冲突处理、重试、容量控制 |
| Stage 3: P2 功能收口 | 2-3 天 | 导入导出闭环、边界优化 |
| **合计** | **12-18 天** | |

---

## 二、Stage 0：遗留系统清理（2-3天）

### 2.1 后端清理

| 任务 | 涉及文件/目录 | 说明 |
|------|--------------|------|
| 0-1 移除 AI Agent 相关代码 | `application/agent_mvp/` 整个目录 | 编排器、策略、工具、模型路由等 |
| 0-2 移除 AI 写作服务 | `application/services/` 中相关文件 | `arc_planning`, `chapter_ai`, `continuation_writer`, `rag_*`, `writing_service_v2` 等 |
| 0-3 移除应用层 DTO | `application/dto/` | 重构为新的 v1 DTO |
| 0-4 移除 domain 层 AI 实体 | `domain/entities/` 中相关文件 | `arc`, `character`, `worldview`, `foreshadow`, `technique`, `template` 等 |
| 0-5 移除 domain 层 AI 仓储接口 | `domain/repositories/` 中相关文件 | 与实体对应的 repository 接口 |
| 0-6 移除基础设施层实现 | `infrastructure/persistence/` | `sqlite_*_repo.py` 中除基础表外的实现 |
| 0-7 移除基础设施层 LLM | `infrastructure/llm/` 整个目录 | LLM 客户端、工厂 |
| 0-8 移除安全模块 | `infrastructure/security/` 等 | 加密 API Key 相关文件及 `config_encryption_service.py` |
| 0-9 清理旧路由 | `presentation/api/routers/` | 清理 AI 相关路由 |
| 0-10 清理测试文件 | `tests/unit/` 和 `tests/integration/` | 保留与 v1 相关的测试，移除 AI 测试 |

### 2.2 前端清理

| 任务 | 涉及文件/目录 | 说明 |
|------|--------------|------|
| 0-11 移除 workspace 复杂组件 | `frontend/src/components/workspace/` | 保留基础布局组件，移除多数 AI 悬浮组件 |
| 0-12 移除 story 相关组件 | `frontend/src/components/story/` 整个目录 | `ArcListPanel`, `ChapterTaskCard` 等 |
| 0-13 移除非 v1 页面 | `frontend/src/views/workspace/` 部分页面 | `SettingsPanel`, `StructureStudio`, `TasksAudit` 等 |
| 0-14 移除设定页面 | `frontend/src/views/` 下对应目录 | `character/`, `worldview/` 等 |
| 0-15 移除旧 stores | `frontend/src/stores/` | 移除 `workspace.js`, `novelWorkspace.js` |
| 0-16 清理路由 | `frontend/src/router/index.js` | 只保留书架和写作页路由 |

### 2.3 清理原则

- **不做大重构**：只删旧业务，不重构旧文件。
- **允许最小修复**：为了保证删除后项目仍可启动，允许做最小量的编译/导入修复（如删除路由注册、移除依赖注入绑定）。
- **保留工具类**：已成熟的工具函数可复用。
- **每删一批跑一次测试**：保证删除后项目仍可启动。

---

## 三、Stage 1：P0 基础功能实现（5-7天）

### 3.1 后端核心（2-3天）

#### 3.1.1 数据库与基础设施

| 任务 | 文件名 | 说明 |
|------|--------|------|
| 1-1 数据库连接配置 | `infrastructure/database/session.py` | SQLite + WAL 模式，配置 `busy_timeout` 防止死锁 |
| 1-2 数据模型定义 | `domain/entities/work.py` | Work 实体（id, title, author, created_at, updated_at） |
| 1-3 数据模型定义 | `domain/entities/chapter.py` | Chapter 实体（含 version 乐观锁字段、order_index） |
| 1-4 数据模型定义 | `domain/entities/edit_session.py` | EditSession（last_open_chapter_id, cursor_position, scroll_top） |
| 1-5 ORM 映射 | `infrastructure/database/models.py` | SQLAlchemy ORM 定义（**仅需3个核心表：works, chapters, edit_sessions**） |
| 1-6 Repository 实现 | `infrastructure/database/repositories/` | `WorkRepo`, `ChapterRepo`, `EditSessionRepo` |

#### 3.1.2 业务服务层

| 任务 | 文件名 | 说明 |
|------|--------|------|
| 1-7 WorkService | `application/services/v1/work_service.py` | 创建（含静默创建第1章 R-CH-04）、列表、删除 |
| 1-8 ChapterService | `application/services/v1/chapter_service.py` | CRUD、乐观锁保存（R-SAVE-04）、原子调序（R-CH-05） |
| 1-9 SessionService | `application/services/v1/session_service.py` | 编辑会话记录和恢复 |
| 1-10 IOService | `application/services/v1/io_service.py` | TXT 导入（R-DATA-03）、导出（R-DATA-04） |

#### 3.1.3 API 路由层

| 任务 | 路由文件 | API |
|------|---------|-----|
| 1-11 WorksRouter | `presentation/api/routers/v1/works.py` | `GET/POST /api/v1/works`, `GET/DELETE /api/v1/works/{id}` |
| 1-12 ChaptersRouter | `presentation/api/routers/v1/chapters.py` | `GET/POST /api/v1/works/{wid}/chapters`, `PUT/DELETE /api/v1/chapters/{id}`, `PUT /api/v1/works/{wid}/chapters/reorder` |
| 1-13 SessionsRouter | `presentation/api/routers/v1/sessions.py` | `GET/PUT /api/v1/works/{id}/session` |
| 1-14 IORouter | `presentation/api/routers/v1/io.py` | `POST /api/v1/io/import`, `GET /api/v1/io/export/{work_id}` |

### 3.2 前端核心（3-4天）

#### 3.2.1 项目基础设施

| 任务 | 说明 |
|------|------|
| 1-15 新建 Pinia Stores | **必须拆分为三部分**：`useWorkspaceStore`（上下文会话）、`useChapterDataStore`（数据读写）、`useSaveStateStore`（保存状态机与离线回放） |
| 1-16 本地缓存工具 | `utils/localCache.js`，实现 LRU 淘汰（10MB 上限） |
| 1-17 API 层 | `api/index.js`，封装 Axios 请求，拦截器处理 409 冲突 |

#### 3.2.2 书架页 WorksList（1天）

| 任务 | 说明 |
|------|------|
| 1-18 WorksList 页面 | 顶部大按钮（新建、导入），下方卡片列表 |
| 1-19 WorkCard 组件 | 作品封面、名称、字数、更多操作菜单 `(...)` |
| 1-20 ImportModal 组件 | TXT 文件导入弹窗 |
| 1-21 空态/加载态/错误态 | 首次打开的空书架引导界面等 |

#### 3.2.3 写作页 WritingStudio（2-3天）

| 任务 | 说明 |
|------|------|
| 1-22 WritingStudio 布局 | 经典三段式：左侧章节列表 + 中间宽边距编辑区 + 右侧预留图标栏（V1必须隐藏面板） |
| 1-23 ChapterSidebar 组件 | 虚拟滚动列表（500+ 章），左标题右字数，Hover 浮现重命名/删除，拖拽排序 |
| 1-24 PureTextEditor 组件 | textarea 纯文本，严格拦截 paste（R-EDIT-04），右下角字数统计（R-EDIT-02） |
| 1-25 StatusBar 组件 | 顶部 Header 右侧显示三态（已同步/保存中/离线黄条）（R-UI-02） |
| 1-26 切章保护逻辑 | 处于“保存中”阻断切换，防丢字兜底逻辑 |
| 1-27 会话恢复 | 切换或打开作品恢复最后编辑章节、光标、滚动位置（R-EDIT-01） |
| 1-28 自动保存链路 | 防抖输入 → 本地缓存 → API 同步 |

### 3.3 P0 集成验收标准 (DoD)

- [ ] 可从书架创建并打开作品，创建后自动存在第1章
- [ ] 可完成章节新建/删除/改名/调序/切换
- [ ] 章节编号始终与 `order_index` 一致
- [ ] 新建章节默认插入当前章节后方
- [ ] 删除当前章节后焦点按“下优先、上兜底”迁移
- [ ] 正文持续可编辑，字数统计口径正确
- [ ] 标题与正文每次 flush 同步提交
- [ ] 切章前内容进入可恢复状态
- [ ] 自动保存生效，切换/关闭/重启后可恢复章节、光标、滚动位置
- [ ] 编辑器仅支持纯文本粘贴

---

## 四、Stage 2：P1 稳定性增强（3-5天）

### 4.1 乐观锁冲突处理（1天）

| 任务 | 参考文档 |
|------|---------|
| 2-1 前端 409 冲突弹窗 | 界面设计 4.1 节：版本冲突弹窗（阻断式，必须决策覆盖或放弃） |
| 2-2 覆盖/放弃决策流程 | 架构设计 5.1 节 |
| 2-3 force_override 接口支持 | 详细设计 2.2.1 节，带 `force_override=true` 覆盖后端 |

### 4.2 保存重试与离线回放（1天）

| 任务 | 参考文档 |
|------|---------|
| 2-4 指数退避重试 | 后台按指数退避自动重试，失败达到上限保留手动重试入口 |
| 2-5 离线回放**串行优化** | `useSaveStateStore.replayOfflineDrafts` 必须按 timestamp 排序且 **串行请求** |
| 2-6 状态灯完善 | 三态流转完整覆盖所有路径，离线黄条准确触发 |

### 4.3 本地缓存容量控制（1天）

| 任务 | 参考文档 |
|------|---------|
| 2-7 LRU 淘汰完整实现 | `utils/localCache.js`，基于 `QuotaExceededError` 和 10MB 软上限 |
| 2-8 缓存一致性保障 | 仅在收到后端 200 OK 并对齐 version 后，才删除对应的本地草稿 |

### 4.4 虚拟列表优化（1天）

| 任务 | 参考文档 |
|------|---------|
| 2-9 虚拟滚动实现 | R-UI-01，500+ 章流畅渲染，无白屏 |
| 2-10 拖拽排序兼容 | 拖拽后可见区与真实顺序一致 |

### 4.5 P1 集成验收

- [ ] 并发编辑时触发版本冲突弹窗
- [ ] 覆盖/放弃决策后数据正确
- [ ] 断网后写作不中断，联网后**按顺序串行**自动回放
- [ ] 本地缓存不超过 10MB，超限淘汰最旧数据
- [ ] 500 章列表流畅滚动

---

## 五、Stage 3：P2 功能收口（2-3天）

### 5.1 TXT 导入增强（1天）

| 任务 | 参考文档 |
|------|---------|
| 3-1 导入兜底 | R-DATA-03：无章节标记时全本按单章入库 |
| 3-2 空文件导入 | Edge Case：创建单章空内容 |
| 3-3 导入顺序校正 | 正则分章 + 提取前言，重新计算连续的 `order_index` |

### 5.2 TXT 导出闭环（0.5天）

| 任务 | 参考文档 |
|------|---------|
| 3-4 导出实现 | R-DATA-04：按 `order_index` 顺序拼接导出为 txt |
| 3-5 无章节时导出 | Edge Case：导出空文本文件 |

### 5.3 长章节软上限提示（0.5天）

| 任务 | 参考文档 |
|------|---------|
| 3-6 20 万字软提示 | R-EDIT-03：顶部显示警告提示，不阻断输入 |
| 3-7 超限后编辑保障 | 可继续编辑/保存/切章，不能发生卡死 |

### 5.4 P2 集成验收

- [ ] TXT 导入在任意输入下均可完成
- [ ] 作品可随时导出 `.txt`
- [ ] 20 万字章节显示软提示，且输入不卡死

---

## 六、项目结构与目录规划 (对齐当前仓库)

为了“只删不改”，保持根目录的领域驱动层级结构，但接口集中到 `v1`：

### 6.1 后端目录结构

```
/workspace
├── presentation/
│   └── api/
│       └── routers/
│           └── v1/
│               ├── works.py         # 作品 CRUD
│               ├── chapters.py      # 章节 CRUD + 调序
│               ├── sessions.py      # 编辑会话
│               └── io.py            # 导入导出
├── application/
│   └── services/
│       └── v1/
│           ├── work_service.py      # 作品服务
│           ├── chapter_service.py   # 章节服务（含乐观锁）
│           ├── session_service.py   # 会话服务
│           └── io_service.py        # 导入导出服务
├── domain/
│   └── entities/
│       ├── work.py
│       ├── chapter.py
│       └── edit_session.py
└── infrastructure/
    └── database/
        ├── session.py              # 数据库连接 + WAL 配置
        ├── models.py               # SQLAlchemy ORM (仅包含3张核心表)
        └── repositories/
            ├── work_repo.py
            ├── chapter_repo.py
            └── edit_session_repo.py
```

### 6.2 前端目录结构

```
/workspace/frontend/src/
├── router/
│   └── index.js                   # 仅保留书架 + 写作页路由
├── api/
│   └── index.js                   # 封装 API (/api/v1/) + 409拦截
├── stores/
│   ├── useWorkspaceStore.js       # 上下文会话管理
│   ├── useChapterDataStore.js     # 章节数据读写
│   └── useSaveStateStore.js       # 保存状态机与串行回放
├── utils/
│   └── localCache.js              # LRU 缓存工具
├── views/
│   ├── WorksList.vue              # 书架页
│   └── WritingStudio.vue          # 写作页主布局
└── components/
    ├── works/
    │   ├── WorkCard.vue           # 作品卡片
    │   └── ImportModal.vue        # 导入弹窗
    └── writing/
        ├── ChapterSidebar.vue     # 左侧：虚拟滚动章节列表
        ├── PureTextEditor.vue     # 中央：纯文本编辑器
        └── StatusBar.vue          # 顶部：状态指示器
```