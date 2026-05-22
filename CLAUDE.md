# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InkTrace 是一个面向长篇小说创作的作者智能体工作系统——"作者与智能体协作写小说的 IDE"。后端 Python/FastAPI，前端 Vue 3 + Vite + Pinia + Element Plus。

核心设计：**Kimi（DeepSeek 系）负责理解/分析/规划/控制，DeepSeek（非 Kimi）负责写作/续写/改写/润色**。Kimi 决定故事往哪走，DeepSeek 把它写出来。

## Commands

### Backend
```bash
pip install -r requirements.txt     # 安装 Python 依赖
python main.py                      # 启动后端服务 (127.0.0.1:9527)
pytest tests/                       # 运行全部后端测试
pytest tests/test_v1_xxx.py -v      # 运行单个测试文件
pytest tests/test_v1_xxx.py::test_name -v  # 运行单个测试用例
pytest -k "keyword" -v              # 按关键词筛选测试
```

### Frontend
```bash
cd frontend && npm install           # 安装前端依赖
cd frontend && npm run dev           # 启动开发服务器 (localhost:3000)
cd frontend && npm run build         # 生产构建
cd frontend && npm test              # 运行全部前端测试 (vitest)
cd frontend && npx vitest run src/xxx.spec.js  # 运行单个测试文件
cd frontend && npx vitest run -t "test name"   # 按名称运行单个测试
```

### Full Stack
```powershell
.\start-all.bat                      # 一键启动前后端
.\stop.bat                           # 停止前后端
.\scripts\build_and_smoke.bat        # 构建 + 冒烟测试
.\scripts\stage5_acceptance.bat      # Stage 5 验收测试
.\scripts\stage6_acceptance.bat      # Stage 6 验收测试
```

### Desktop Build
```bash
npm run build:win      # Windows 桌面打包 (electron-builder)
npm run build:mac      # macOS 桌面打包
```

### Database Migrations
```bash
python migrations/migrate_structured_story_data.py
```

## Architecture

### 分层架构（Clean Architecture / DDD）

后端遵循领域驱动设计，四层职责分明：

```
presentation/    → API 层（FastAPI 路由、中间件、异常处理、依赖注入）
application/     → 应用服务层（编排用例、prompt 构建、workflow 调度）
domain/          → 领域层（实体、值对象、仓储接口、领域服务、常量/枚举）
infrastructure/  → 基础设施层（SQLite 持久化、文件 I/O、ChromaDB 向量存储）
```

数据流向：`presentation → application → domain ← infrastructure`

**V1 接口**（当前主力）位于 `presentation/api/routers/v1/`，对应 `application/services/v1/`。  
**重构版 DDD 接口**（正在演进）位于 `backend/`，包含 `backend/src/domain/`（纯 DDD 领域模型）和 `backend/src/presentation/`。

### 核心文档目录

```
docs/
├── 01_requirements/   # 需求
├── 02_architecture/   # 架构设计
├── 03_design/         # 详细设计
├── 04_plan/           # 开发计划
├── 05_tasks/          # 任务追踪
├── 06_validation/     # 验收记录
└── 07_overview/       # 总览
```

### V1 API 路由

所有 V1 路由注册在 `presentation/api/routers/v1/`，公共前缀 `/api/v1`：
- `works` — 作品 CRUD
- `chapters` — 章节 CRUD、排序、发布
- `sessions` — 编辑会话（乐观锁 409 冲突）
- `io` — 导入/导出（TXT、大纲导入）
- `outlines` — 大纲资产管理
- `timeline` — 时间线事件管理
- `foreshadows` — 伏笔管理
- `characters` — 人物管理
- `health` — 健康检查

### V1 服务层

`application/services/v1/` 包含核心业务逻辑：
- `work_service.py` / `chapter_service.py` / `session_service.py` — 作品-章节-会话主链路
- `io_service.py` — 导入/导出
- `writing_asset_service.py` — 写作资产（人物/伏笔/大纲/时间线）
- `text_metrics.py` — 字数/文本度量
- `content_tree_schema.py` — 内容树结构定义

### Domain 领域层

`domain/entities/` — 核心实体：`Work` (作品)、`Chapter` (章节)、`EditSession` (编辑会话)、`Novel` (小说)、`Outline` (大纲)、`WritingAsset` (写作资产)  
`domain/repositories/` — 仓储接口  
`domain/services/` — 领域服务：`WritingEngine` (写作引擎)、`ConsistencyChecker` (一致性检查)、`PlotAnalyzer` (剧情分析)、`StyleAnalyzer` (风格分析)  
`domain/value_objects/` — 值对象：`CharacterState`、`Embedding`、`StyleProfile`、`WritingConfig`  
`domain/constants/` — 枚举与常量

### Infrastructure 基础设施

`infrastructure/database/` — SQLite 数据库会话与仓储实现  
`infrastructure/persistence/` — 新版 SQLite 持久化（`sqlite_chapter_repo.py` 等，基于 aiosqlite）  
`infrastructure/file/` — 文件导入导出（`txt_parser.py`、`txt_exporter.py`、`markdown_exporter.py`）

### Frontend 架构

```
frontend/src/
├── api/              # Axios HTTP 请求封装
├── components/       # Vue 组件
│   ├── works/        # 作品列表相关（卡片、创建、导入、导出弹窗）
│   └── workspace/    # 写作工作区（编辑器、侧栏、资产面板、时间线等）
├── composables/      # 组合式函数
├── constants/        # 常量与枚举标签
├── layouts/          # 布局组件
├── router/           # Vue Router 路由配置
├── stores/           # Pinia 状态管理
├── utils/            # 工具函数
└── views/            # 页面视图
    ├── novel/        # 小说导入
    └── works/        # 作品列表 & 写作工作室
```

### 关键设计约束

- **乐观锁并发**: Chapter/Session 通过 `version` 字段实现乐观锁，并发更新返回 409 冲突
- **排序原子性**: Timeline/Chapter 排序通过完整映射提交 + 单事务写入保证原子性
- **双模型协同**: 系统固定使用两类模型（Kimi 负责理解/规划/控制，DeepSeek 负责生成/改写）
- **Local-First 保存**: 前端本地草稿 + 服务端持久化，冲突弹窗处理版本分歧
- **Story Model**: 人物图谱、世界观规则、PlotArc、风格画像等构成小说的可持续结构模型

### 代码实现要求：DDD + Clean Architecture + TDD

所有代码实现必须严格遵循以下三条方法论，不可偏废。

#### 1. DDD（领域驱动设计）

**核心原则：领域层是系统的心脏，不依赖任何外部框架或基础设施。**

| 要求 | 说明 |
|---|---|
| **实体与值对象分离** | 实体有唯一标识（ID）和生命周期；值对象无 ID，通过属性值判等。实体放在 `domain/entities/`，值对象放在 `domain/value_objects/` |
| **仓储接口定义在领域层** | Repository 抽象（ABC）定义在 `domain/repositories/`，由 `infrastructure/` 实现。Application 层只依赖接口，不依赖具体存储 |
| **领域服务不含基础设施代码** | 领域服务（`domain/services/`）只包含纯业务规则，不调用数据库、HTTP、文件系统 |
| **聚合根控制访问** | 对聚合内部实体的修改必须通过聚合根。不跨聚合直接引用，通过 ID 引用 |
| **Ubiquitous Language** | 代码命名（类名、方法名、变量名）必须使用业务术语，与设计文档和需求文档保持一致。禁止技术术语渗透到领域层 |
| **禁止贫血模型** | 实体和值对象应包含业务行为方法，不只是 getter/setter 数据容器 |

**模块依赖方向（严格遵守）：**
```
presentation → application → domain ← infrastructure
```
- `domain` 不依赖任何其他层
- `application` 只依赖 `domain`
- `infrastructure` 实现 `domain` 中定义的仓储接口
- `presentation` 调用 `application` 中的服务
- **任何层不得反向依赖**

#### 2. Clean Architecture（清洁架构）

**核心原则：依赖规则指向内层。内层不知道外层的存在。**

| 要求 | 说明 |
|---|---|
| **四层物理隔离** | 代码必须放在对应的四层目录中：`presentation/` → `application/` → `domain/` → `infrastructure/`。不允许跨层放置 |
| **依赖注入（DI）** | Application Service 通过构造函数接收 Repository 接口（`domain/repositories/` 中定义的 ABC），从不直接 import 具体实现类。DI 组装在 `presentation/api/dependencies.py` 完成 |
| **用例驱动设计** | 每个 Application Service 的方法对应一个业务用例。方法命名体现用例意图：`create_*`、`start_*`、`complete_*`、`cancel_*` |
| **接口适配** | Presentation 层负责将 HTTP 请求转换为 Application 层的入参（DTO → 领域对象），将 Application 层返回值转换为 HTTP 响应（领域对象 → DTO） |
| **不做 ORM 绑定** | 领域实体不继承数据库基类，不包含数据库映射装饰器。持久化映射在 Infrastructure 层处理 |
| **跨层通信走接口** | Application 层调用 Infrastructure 层必须通过 `domain/repositories/` 中定义的接口。不允许 Application 层直接 import `infrastructure/` 下的任何类 |

**具体规则：**
- `application/services/` 中任何文件**不得** `import` 自 `infrastructure/`
- `application/services/` 中任何文件**不得** `import` 自 `presentation/`
- `domain/` 中任何文件**不得** `import` 自 `application/`、`infrastructure/`、`presentation/`
- Agent/Service 不得直接调用 Provider SDK、ModelRouter、Database Adapter——必须通过 ToolFacade 或 Repository 接口

#### 3. TDD（测试驱动开发）

**核心原则：先写测试，再写实现。测试是需求的可执行表达。**

| 要求 | 说明 |
|---|---|
| **Red-Green-Refactor 循环** | ① 先写一个失败的测试（Red）→ ② 写最少代码使测试通过（Green）→ ③ 重构代码消除重复、改善结构（Refactor）。严禁跳过第①步 |
| **测试金字塔** | 大量单元测试（domain/application 层）+ 适度集成测试（API 层）+ 少量 E2E 测试（全链路）。不依赖真实 AI Provider 进行单元测试——使用 Stub/Fake/Mock |
| **每个用例至少一个正向测试** | 每个 Application Service 的 public 方法至少有 1 个正向（happy path）测试用例 |
| **每个门控至少一个反向测试** | 每个 user_action 门控、安全边界（formal_write forbidden、agent 不能 auto-apply 等）至少 1 个反向（sad path）测试用例 |
| **测试隔离性** | 测试不依赖数据库——文件存储（JSON file store, tmp_path）实现即可。测试之间不共享状态 |
| **测试命名规范** | `test_{模块}_{场景描述}_{预期结果}`。如 `test_agent_orchestrator_cancel_from_direction_waiting_enters_cancelled` |
| **验收前全量通过** | 每个阶段完成后，对应 `tests/` 目录下全部测试必须 100% 通过，且不能有 `skipped` 或 `xfail` 标记的故意跳过项（除非设计文档明确标注为延后功能） |
| **禁止"先写实现后补测试"** | 测试必须在实现代码之前或同步编写，不得在实现完成后补充"覆盖性测试" |

#### 4. 验收检查清单（每次实现完成后自查）

在提交代码前，逐条确认：

- [ ] 所有新模型是否放在 `domain/entities/` 下，且不 import 任何基础设施代码？
- [ ] 所有新仓储接口是否放在 `domain/repositories/` 下（ABC），实现在 `infrastructure/` 下？
- [ ] Application Service 是否通过构造函数注入依赖（DI），不直接 new 具体实现？
- [ ] Presentation API 是否不直接调用 Repository/ToolFacade/Provider？
- [ ] 每个 Application Service 的 public 方法是否有正向测试？
- [ ] 每个安全门控（user_action 专属、formal_write forbidden 等）是否有反向测试？
- [ ] 测试是否全部通过？（`pytest tests/` 无失败）
- [ ] 是否有任何 `import` 违反了分层依赖方向？

### 测试分布

- **后端测试**: `tests/` 按模块组织（pytest），`conftest.py` 提供隔离数据库 fixture。AI 模块测试在 `tests/ai/` 下，V1 接口测试在 `tests/test_v1_*.py`
- **前端测试**: 散布在 `src/**/__tests__/*.spec.js`（vitest + jsdom + @vue/test-utils）
