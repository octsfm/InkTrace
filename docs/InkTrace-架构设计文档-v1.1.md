# InkTrace 架构设计文档（v1.1）

更新时间：2026-04-24  
适用阶段：当前版本

### 3.4 状态机：保存状态机制 (Save State Machine)
满足 `R-UI-02` 和 `R-SAVE-05`，前端保存状态机仅允许以下三种状态及其确定性流转：

- **初始状态**: `已保存` (Loaded / Saved)
- **状态流转**:
  - `已保存` → 用户输入/触发防抖 → `保存中` (Saving)
  - `保存中` → API 请求成功 (`200 OK`) → `已保存` (Saved)
  - `保存中` → API 请求失败 / 断网离线 → `保存失败` (Failed)
  - `保存失败` → 用户继续输入/触发防抖 → `保存中` (Saving)
  - `保存失败` → 离线回放/后台重试成功 → `已保存` (Saved)
- **特殊规则**:
  - **离线模式**下，输入直接将数据写入 LocalStorage，状态强制停留在 `保存失败` (或独立显示离线徽章)，但不阻断用户继续输入。
  - **版本冲突 (409)** 时，状态转为 `保存失败`，直到用户完成决策（覆盖或放弃）。

---

## 1. 架构目标

基于《InkTrace 基础方案落地文档（v1.1）》，本次架构重构的核心目标是：
- **剥离过度设计**：移除之前不稳定的 AI 工作流，回归纯粹的长篇小说写作工具本质。
- **强化本地容错**：通过“本地 LRU 缓存优先”与“后端乐观锁”双重机制，保障创作者的极端情况数据安全（断网、多端并发）。
- **保证性能体验**：在纯前端侧支撑 500+ 章节的流畅渲染与 20 万字单章的高性能纯文本编辑。

---

## 2. 总体系统架构

系统采用经典的前后端分离架构，但在数据同步策略上采用了 **Local-First（本地优先）** 的思想。

```mermaid
graph TD
    %% 定义样式
    classDef client fill:#e1f5fe,stroke:#333,stroke-width:2px;
    classDef storage fill:#fff3e0,stroke:#333,stroke-width:2px;
    classDef server fill:#e8f5e9,stroke:#333,stroke-width:2px;
    classDef database fill:#f3e5f5,stroke:#333,stroke-width:2px;

    %% 客户端子系统
    subgraph Client [Browser / Desktop Client (Vue3 + Pinia)]
        direction TB
        UI[写作界面\nWorksList / WritingStudio] -->|防抖输入| State[Pinia Store\n状态管理]
        State -->|更新| UI
    end

    %% 本地缓存子系统
    subgraph LocalStorage [Local Storage (LRU Cache)]
        Drafts[(本地草稿\ninktrace_draft_ID)]
    end

    %% 服务端子系统
    subgraph Server [Backend (FastAPI)]
        direction TB
        API[REST API\nRouter Layer] --> Service[业务逻辑\nService Layer]
        Service --> Lock{乐观锁校验\nVersion Match?}
    end

    %% 数据库子系统
    subgraph Database [Database (SQLite WAL)]
        DB[(核心表\nworks / chapters)]
    end

    %% 核心数据流转
    State -->|1. 实时/离线写入| Drafts
    State -->|2. 定时/在线同步| API
    
    Lock -->|Yes: 更新并 version+1| DB
    Lock -->|No: 拒绝并返回 409| API
    
    API -->|3. 成功 (200 OK)| State
    State -->|4. 删除对应缓存| Drafts
    
    API -->|3. 失败/冲突 (409)| State
    State -.->|保留缓存以备恢复| Drafts

    %% 样式应用
    class Client client;
    class LocalStorage storage;
    class Server server;
    class Database database;
```

---

## 3. 前端架构设计 (Vue3 + Pinia)

前端架构重点解决三个问题：**虚拟列表渲染、纯文本强制拦截、本地草稿缓存**。

### 3.1 视图与组件树
严格限制在两个核心视图：

1. **`WorksList.vue` (书架)**
   - `WorkCard.vue`: 作品卡片（展示信息、导出操作）。
   - `ImportModal.vue`: TXT 导入弹窗。

2. **`WritingStudio.vue` (写作页)**
   - `ChapterSidebar.vue`: 章节侧边栏。
     - `VirtualScrollList.vue`: 虚拟滚动容器（支撑 500+ 章节，复用 DOM 节点）。
     - `DraggableItem.vue`: 支持 HTML5 Drag & Drop 的拖拽排序项。
   - `PureTextEditor.vue`: 纯文本编辑器核心。
     - 拦截 `paste` 事件，强制转换为纯文本。
     - 监听 `input` 事件进行防抖（Debounce）字数统计与自动保存。
   - `StatusBar.vue`: 极简状态栏（保存中/已保存/保存失败）。

### 3.2 状态管理 (Pinia Stores)
状态拆分为两个正交的 Store，避免大对象带来的响应式性能损耗：

1. **`useWorkStore`**: 
   - 管理作品列表、当前打开的作品基础信息。
2. **`useChapterStore`**: 
   - 管理当前激活章节（Active Chapter）、章节列表（List）、排序状态、保存状态（Save State）。

### 3.3 Local-First 缓存与同步机制 (核心)
这是满足 `R-SAVE-06` 和 `R-SAVE-07` 的核心设计：

- **写入策略**：任何正文或标题的修改，**第一时间同步写入** `LocalStorage` (键名 `inktrace_draft_{chapter_id}`)，同时触发防抖的 API 请求。
- **LRU 淘汰策略**：
  - 设定 LocalStorage 配额软上限（如 5MB-10MB）。
  - 每次写入前检查容量（捕获 `QuotaExceededError`）。
  - 若超限，按 `timestamp` 淘汰最旧的未同步草稿，直到腾出空间。
- **网络状态感知**：监听 `window.addEventListener('offline'/'online')`。离线时挂起 API 请求，仅写本地；上线后遍历 LocalStorage 中的 `inktrace_draft_*` 执行回放。

---

## 4. 后端架构设计 (FastAPI + SQLAlchemy)

后端架构抛弃原有的复杂微服务/智能体调度，回归**领域驱动设计 (DDD)** 的极简分层。

### 4.1 分层架构
1. **Presentation Layer (表现层 / API)**:
   - `routers/works.py`: 作品 CRUD、打开会话记录。
   - `routers/chapters.py`: 章节 CRUD、拖拽全量调序、正文保存。
   - `routers/io.py`: TXT 导入（正则分章）、TXT 导出。
2. **Application Layer (应用层 / Service)**:
   - `work_service.py`: 编排新建作品与静默创建“第1章”（`R-CH-04`）。
   - `chapter_service.py`: 编排乐观锁校验与原子化批量排序（`R-CH-05`）。
3. **Domain Layer (领域层 / Entity)**:
   - `entities.py`: 纯粹的业务对象定义。
4. **Infrastructure Layer (基础设施层)**:
   - `database/models.py`: SQLAlchemy ORM 模型定义。
   - `database/session.py`: 数据库连接池，**开启 SQLite WAL 模式**提升并发写性能。

### 4.2 接口定义（API清单）

为了支撑上述业务流程，需要实现以下 RESTful API：

#### Works API (`routers/works.py`)
| 接口路径 | 方法 | 说明 |
| --- | --- | --- |
| `/api/works` | `GET` | 获取作品列表（按最近更新时间排序） |
| `/api/works` | `POST` | 新建作品（系统需静默创建第1章） |
| `/api/works/{id}` | `GET` | 获取单个作品详情 |
| `/api/works/{id}` | `DELETE` | 删除作品及级联数据 |

#### Chapters API (`routers/chapters.py`)
| 接口路径 | 方法 | 说明 |
| --- | --- | --- |
| `/api/works/{work_id}/chapters` | `GET` | 获取某作品下的所有章节（按 `order_index` 升序） |
| `/api/works/{work_id}/chapters` | `POST` | 新建章节（插入在指定的 `order_index` 后，后续章节顺延） |
| `/api/chapters/{id}` | `PUT` | 保存章节标题与正文（需携带 `version` 进行乐观锁校验） |
| `/api/chapters/{id}` | `DELETE` | 删除章节（后续章节 `order_index` 需顺延重算） |
| `/api/works/{work_id}/chapters/reorder` | `PUT` | 原子化全量调整章节顺序（接收 `[{"id": "A", "order_index": 1}, ...]`） |

#### Edit Session API (`routers/sessions.py`)
| 接口路径 | 方法 | 说明 |
| --- | --- | --- |
| `/api/works/{work_id}/session` | `GET` | 获取该作品的最后一次编辑会话（章节ID、光标、滚动条） |
| `/api/works/{work_id}/session` | `PUT` | 更新最后一次编辑会话状态 |

#### IO API (`routers/io.py`)
| 接口路径 | 方法 | 说明 |
| --- | --- | --- |
| `/api/io/import` | `POST` | 导入 TXT 文件，按正则分章入库 |
| `/api/io/export/{work_id}` | `GET` | 导出指定作品为 TXT 文件 |

### 4.3 数据库核心模型 (SQLite)

基于 v1.1 需求，数据库表结构必须严格遵循以下字段定义：

#### 1. `works` (作品表)
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `String(36)` | 主键 UUID |
| `title` | `String(255)` | 作品名称 |
| `author` | `String(100)` | 作者名称 (可空) |
| `created_at` | `DateTime` | 创建时间 |
| `updated_at` | `DateTime` | 最后更新时间 |

#### 2. `chapters` (章节表)
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `String(36)` | 主键 UUID |
| `work_id` | `String(36)` | 外键，关联 `works.id` |
| `chapter_no` | `String(50)` | 保留字段，不参与排序 (可空) |
| `title` | `String(255)` | 章节标题 (默认"") |
| `content` | `Text` | 章节正文 (默认"") |
| `word_count` | `Integer` | 有效字数统计 |
| `order_index` | `Integer` | **排序绝对依据** |
| `version` | `Integer` | **乐观锁版本号** (默认 1) |
| `created_at` | `DateTime` | 创建时间 |
| `updated_at` | `DateTime` | 最后更新时间 |

#### 3. `edit_sessions` (编辑会话表)
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `work_id` | `String(36)` | 主键，外键关联 `works.id` |
| `last_open_chapter_id`| `String(36)` | 上次最后编辑的章节ID (可空) |
| `cursor_position` | `Integer` | 光标位置 (用于恢复现场) |
| `scroll_top` | `Integer` | 滚动条高度 (用于恢复现场) |
| `last_opened_at` | `DateTime` | 最后打开时间 |

---

## 5. 核心业务流程设计 (时序图简述)

### 5.1 乐观锁防覆盖保存流程 (满足 R-SAVE-04)
解决多端或多标签页同时编辑同一章节的静默覆盖问题：

1. **Client** 修改内容，发起 `PUT /api/chapters/{id}`，Payload 携带 `version=N`。
2. **Server** 开启事务，查询数据库当前 `db_version`。
3. **Server** 校验：
   - 如果 `version == db_version`: 执行更新，`version = db_version + 1`，提交事务，返回 `200 OK` 及新 `version`。
   - 如果 `version != db_version`: 触发冲突，回滚，返回 `409 Conflict`。
4. **Client** 收到 409：
   - 保持编辑区内容不变（保留本地草稿）。
   - UI 提示“检测到远端有新版本，是否覆盖？”。
   - 若用户选择“覆盖”，发起 `PUT` 并携带 `force_override=true`，服务端以数据库当前版本为基准强制加 1 并保存。

### 5.2 拖拽调序原子化流程 (满足 R-CH-05)
解决调序过程中的顺序错乱和并发问题：

1. **Client** 在虚拟列表中完成拖拽。
2. **Client** 在内存中重算所有章节的 `order_index` (1...N)。
3. **Client** 发起 `PUT /api/chapters/reorder`，Payload 包含全量映射 `[{"id": "A", "order_index": 1}, {"id": "B", "order_index": 2}, ...]`。
4. **Server** 开启单个数据库事务。
5. **Server** 遍历映射，批量执行 `UPDATE chapters SET order_index=? WHERE id=?`。
6. **Server** 提交事务（若任何一步失败则全量回滚）。
7. **Client** 刷新列表。

### 5.3 异常恢复与离线回放流程 (满足 R-SAVE-06, R-SAVE-08)
解决断网或后端宕机导致的数据丢失：

1. **Client** 断网。
2. 用户持续输入，防抖触发 `saveLocalDraft()`，数据安全落盘 `LocalStorage`。
3. 网络恢复触发 `online` 事件。
4. **Client** 遍历 `LocalStorage` 中所有 `inktrace_draft_*`。
5. 针对每一个草稿，发起携带缓存中 `version` 的保存请求。
6. 如果请求成功 (`200 OK`)，**删除该条 LocalStorage 缓存**。
7. 如果请求失败 (`409 Conflict`)，**保留该条 LocalStorage 缓存**，交由乐观锁冲突流程处理（等待用户干预）。

---

## 6. 安全与边界防御设计

- **TXT 导入兜底 (R-DATA-03)**:
  - 采用流式读取或分块处理（防大文件 OOM）。
  - 若正则 `第.*?章` 匹配失败，强制生成一条 `order_index=1`, `title="全本导入"` 的单章记录。
- **纯文本粘贴拦截 (R-EDIT-04)**:
  - 在 Vue 组件挂载时，对 `textarea` 绑定 `@paste` 事件：
  ```javascript
  const handlePaste = (e) => {
      e.preventDefault();
      const text = (e.originalEvent || e).clipboardData.getData('text/plain');
      document.execCommand('insertText', false, text);
  };
  ```
- **事务一致性**: 
  - 作品创建时，“作品主表插入”与“第1章创建”必须包裹在同一个 `db.commit()` 事务内，一荣俱荣一损俱损。