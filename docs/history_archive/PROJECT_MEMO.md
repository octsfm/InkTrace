# InkTrace 项目开发备忘录

> 供新任务/AI参考 | 作者：孔利群

---

## 一、重要提示（必读）

- **严格按6A流程执行**：Align → Architect → Atomize → Approve → Automate → Assess
- **TDD开发**：先写测试，后写实现，核心覆盖率≥80%
- **作者署名**：所有代码注释、文档作者统一填写「孔利群」，禁止Trae标识
- **清洁架构**：依赖由外向内，领域层独立无外部依赖
- **中文注释**：代码注释使用中文，Python遵循PEP8+类型注解

---

## 二、项目概述

### 2.1 项目目标
AI驱动的小说自动编写助手，帮助作者续写小说、分析风格、管理世界观设定。目标是续写一部142章、30万字的小说至800万字。

### 2.2 当前进度

| 阶段 | 内容 | 状态 |
|-----|------|------|
| 一期 | 核心写作功能 | ✅ 已完成 |
| 二期 | 多项目/模板/人物/世界观 | ✅ 已完成 |
| 三期 | 向量数据库/RAG智能检索 | ✅ 已完成 |
| 四期 | Electron桌面应用 | ✅ 已完成 |
| 五期 | 批量续写/自动发布/多格式导出 | 待开发 |

---

## 三、技术架构

### 3.1 分层架构

```
domain/          → 领域层（实体、值对象、仓储接口、领域服务）
application/     → 应用层（应用服务、DTO）
infrastructure/  → 基础设施层（仓储实现、LLM客户端、文件解析）
presentation/    → 接口层（FastAPI路由）
frontend/        → Vue3前端
desktop/         → Electron桌面应用
tests/           → 单元测试（pytest）
docs/            → 开发文档
```

### 3.2 技术栈

| 组件 | 技术选型 |
|-----|---------|
| 后端 | FastAPI + Uvicorn (端口9527) |
| 前端 | Vue3 + Element Plus + Vite (端口3000) |
| 数据库 | SQLite + ChromaDB（向量） |
| LLM | DeepSeek-V3（主）+ Kimi（备） |
| 向量嵌入 | text2vec-chinese |
| 桌面 | Electron + electron-builder |
| 测试 | pytest（280个测试） |

---

## 四、开发规范

### 4.1 6A流程

1. **Align（对齐）**：生成`docs/ALIGN_*.md`，需求边界、验收标准、疑问清单
2. **Architect（架构）**：生成`docs/ARCH_*.md`，分层图、模块、领域模型
3. **Atomize（拆解）**：生成`docs/ATOM_*.md`，原子任务、编号、依赖
4. **Approve（审批）**：生成`docs/APPR_*.md`，汇总前三阶段提交审批
5. **Automate（实现）**：按任务清单执行，TDD：先测试→实现→重构
6. **Assess（评估）**：生成`docs/ASSESS_*.md`，验证需求完成、测试结果

### 4.2 代码规范

- Python：PEP8 + 类型注解
- 注释：中文
- 作者署名：孔利群
- 值对象：使用 `@dataclass(frozen=True)`
- 仓储接口：定义在 `domain/repositories/`
- 仓储实现：定义在 `infrastructure/persistence/`

### 4.3 测试规范

- 测试文件：`tests/unit/test_*.py`
- 运行测试：`python -m pytest tests/ -v`
- 覆盖率要求：核心模块 ≥ 80%
- Mock隔离：使用 `unittest.mock`

---

## 五、关键文件说明

### 5.1 领域层

| 文件 | 说明 |
|-----|------|
| `domain/types.py` | 类型定义（NovelId, ChapterId, CharacterId等） |
| `domain/entities/novel.py` | 小说实体 |
| `domain/entities/chapter.py` | 章节实体 |
| `domain/entities/character.py` | 人物实体 |
| `domain/entities/project.py` | 项目实体 |
| `domain/entities/template.py` | 模板实体 |
| `domain/entities/worldview.py` | 世界观实体 |
| `domain/repositories/*.py` | 仓储接口定义 |
| `domain/services/style_analyzer.py` | 风格分析服务 |
| `domain/services/rag_context_builder.py` | RAG上下文构建器 |

### 5.2 基础设施层

| 文件 | 说明 |
|-----|------|
| `infrastructure/persistence/sqlite_*.py` | SQLite仓储实现 |
| `infrastructure/persistence/chromadb_vector_repo.py` | ChromaDB向量仓储 |
| `infrastructure/llm/deepseek_client.py` | DeepSeek LLM客户端 |
| `infrastructure/llm/llm_factory.py` | LLM工厂 |
| `infrastructure/file/txt_parser.py` | TXT文件解析器 |
| `infrastructure/templates/*.json` | 内置模板文件 |

### 5.3 接口层

| 文件 | 说明 |
|-----|------|
| `presentation/api/app.py` | FastAPI应用入口 |
| `presentation/api/dependencies.py` | 依赖注入配置 |
| `presentation/api/routers/novel.py` | 小说API |
| `presentation/api/routers/writing.py` | 续写API |
| `presentation/api/routers/vector.py` | 向量索引API |
| `presentation/api/routers/rag.py` | RAG检索API |

### 5.4 应用层

| 文件 | 说明 |
|-----|------|
| `application/services/project_service.py` | 项目服务 |
| `application/services/character_service.py` | 人物服务 |
| `application/services/worldview_service.py` | 世界观服务 |
| `application/services/vector_index_service.py` | 向量索引服务 |
| `application/services/rag_retrieval_service.py` | RAG检索服务 |

---

## 六、启动命令

### 6.1 开发模式

```bash
# 启动后端
python main.py

# 启动前端（另一终端）
cd frontend
npm run dev

# 运行测试
python -m pytest tests/ -v
```

### 6.2 生产构建

```bash
# 构建前端
cd frontend
npm run build

# 打包桌面应用
build-desktop.bat
```

---

## 七、API接口概览

| 模块 | 接口 | 功能 |
|-----|------|------|
| 小说管理 | `GET/POST /api/novels/` | 小说列表/创建 |
| 项目管理 | `GET/POST /api/projects/` | 项目列表/创建 |
| 人物管理 | `GET/POST /api/characters/` | 人物列表/创建 |
| 世界观 | `GET/POST /api/worldview/` | 世界观设定 |
| 向量索引 | `POST /api/novels/{id}/vector/index` | 索引小说内容 |
| RAG检索 | `POST /api/novels/{id}/rag/search` | 语义搜索 |
| RAG上下文 | `POST /api/novels/{id}/rag/context` | 获取续写上下文 |
| AI续写 | `POST /api/writing/generate` | 生成章节内容 |

---

## 八、常见问题

### Q1: 端口冲突怎么办？
后端默认端口9527，前端默认端口3000。如需修改，编辑 `config.py` 和 `frontend/vite.config.js`。

### Q2: 测试失败怎么办？
运行 `python -m pytest tests/ -v --tb=long` 查看详细错误信息。确保所有依赖已安装。

### Q3: 如何添加新的API路由？
1. 在 `presentation/api/routers/` 创建路由文件
2. 在 `presentation/api/dependencies.py` 添加服务依赖
3. 在 `presentation/api/app.py` 注册路由
4. 编写对应的单元测试

### Q4: 如何添加新的实体？
1. 在 `domain/entities/` 创建实体类
2. 在 `domain/repositories/` 创建仓储接口
3. 在 `infrastructure/persistence/` 实现仓储
4. 在 `application/services/` 创建应用服务
5. 编写单元测试

---

## 九、文档位置

所有开发文档存放在 `docs/` 目录：

- `ALIGN_AI小说自动编写助手*.md` - 需求对齐文档
- `ARCH_AI小说自动编写助手*.md` - 架构设计文档
- `ATOM_AI小说自动编写助手*.md` - 任务拆解文档
- `APPR_AI小说自动编写助手*.md` - 审批文档
- `ASSESS_AI小说自动编写助手*.md` - 评估验收文档

---

## 十、测试状态

```
当前测试数量：280个
状态：全部通过
覆盖率：核心模块 ≥ 80%
```

---

*祝开发顺利！*
