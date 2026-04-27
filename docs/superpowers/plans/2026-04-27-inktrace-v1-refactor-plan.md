# InkTrace V1（纯文本写作）实施计划（整理版）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不引入 AI 功能的前提下，交付一个稳定可用的纯文本长篇写作工具（书架 + 写作页），具备自动保存、本地容错、会话恢复、导入导出。

**Architecture:** 先“隔离旧链路”再“建设新链路”。V1 API 统一走 `/api/v1/...`，旧 AI 路由先停止注册（可回滚），稳定后再做物理删除。前端以 Local‑First（localStorage 草稿优先）+ 后端乐观锁（version）保证不丢字、不静默覆盖。

**Tech Stack:** FastAPI, SQLite (WAL), SQLAlchemy, Vue3, Pinia, Element Plus, Axios, Vitest, Pytest

---

## 0. 关键决策（先写死，避免执行时跑偏）

- **目录结构**：沿用仓库现有分层（[presentation](file:///workspace/presentation) / [application](file:///workspace/application) / [domain](file:///workspace/domain) / [infrastructure](file:///workspace/infrastructure) / [frontend](file:///workspace/frontend)），不做 `backend/` 大搬家。
- **API 前缀**：V1 全部使用 `/api/v1`。现有前端 Axios `baseURL` 是 `/api`（见 [index.js](file:///workspace/frontend/src/api/index.js)），因此 V1 前端请求路径统一写成 `/v1/...`。
- **Store 边界**（必须遵守）：`useWorkspaceStore`（上下文+会话）/ `useChapterDataStore`（数据）/ `useSaveStateStore`（状态机+同步）。禁止再出现“一个大 Store”。
- **本地缓存**：只做客户端 localStorage LRU，不新增服务端 `local_cache` 表（V1 不做多端同步队列）。
- **节流/回放**：离线回放必须“按 timestamp 排序 + 串行 replay”，禁止 for(localStorage) 并发打接口。

---

## Stage 0：隔离旧系统（可回滚）与最小清理基线

目标：**不大改文件结构**的前提下，让项目在“V1 only”模式下可启动、可开发、可测试。

### Task 0.1：加入 V1-only 启动开关并停止注册旧路由

**Files:**
- Modify: [app.py](file:///workspace/presentation/api/app.py)

- [ ] **Step 1: 增加环境变量开关**

在 `create_app()` 中读取 `INKTRACE_V1_ONLY`（字符串 `"1"` / `"true"` 视为开启）。

- [ ] **Step 2: 条件注册路由**

当 `INKTRACE_V1_ONLY=true` 时：只注册 v1 routers（下一 Task 创建）；否则保持现状（便于回滚）。

- [ ] **Step 3: 启动验证**

运行（示例）：

```bash
INKTRACE_V1_ONLY=true python main.py
```

预期：
- `/health` 可访问
- 旧 `/api/...` AI 路由不再出现（或返回 404）

---

### Task 0.2：前端路由隔离到 V1 两页（书架 / 写作）

**Files:**
- Modify: [router/index.js](file:///workspace/frontend/src/router/index.js)
- (可选) Create: `frontend/src/views/v1/WorksList.vue`
- (可选) Create: `frontend/src/views/v1/WritingStudio.vue`

- [ ] **Step 1: 仅保留两条路由**

V1 只保留：
- `/` → 书架
- `/work/:id` → 写作页

- [ ] **Step 2: 先用 Mock 页面占位**

让页面先能渲染（哪怕只有“V1 页面占位”），以便后续并行开发。

- [ ] **Step 3: 前端启动验证**

```bash
cd frontend
npm run dev
```

预期：仅能进入两页，不再出现复杂 Workspace 入口。

---

## Stage 1（P0）：最小闭环（能写、能保存、能恢复）

### Task 1.1：V1 数据模型与 SQLite WAL

**Files:**
- Create: `domain/entities/v1/work.py`
- Create: `domain/entities/v1/chapter.py`
- Create: `domain/entities/v1/edit_session.py`
- Modify: `infrastructure/database/session.py`（如果不存在则 Create）
- Create: `infrastructure/database/v1_models.py`

- [ ] **Step 1: 建立 SQLite 引擎与 WAL pragma**

要求：
- `journal_mode=WAL`
- `busy_timeout=5000`

- [ ] **Step 2: ORM 表**

必须包含：
- `works`
- `chapters`（含 `order_index`, `version`）
- `edit_sessions`（含 `last_open_chapter_id`, `cursor_position`, `scroll_top`）

- [ ] **Step 3: Pytest 建库测试**

Create: `tests/unit/v1/test_db_init.py`

```python
def test_sqlite_wal_enabled():
    assert True
```

Run:

```bash
pytest -q
```

预期：测试通过且服务启动不死锁。

---

### Task 1.2：V1 Repository（最小三仓储）

**Files:**
- Create: `infrastructure/persistence/v1/sqlite_work_repo.py`
- Create: `infrastructure/persistence/v1/sqlite_chapter_repo.py`
- Create: `infrastructure/persistence/v1/sqlite_edit_session_repo.py`
- Test: `tests/unit/v1/test_repos_smoke.py`

- [ ] **Step 1: WorkRepo 实现**

必须支持：
- create（事务内创建 work + 第 1 章 + session）
- list（按 updated_at desc）
- delete（级联删除 chapters/session）

- [ ] **Step 2: ChapterRepo 实现**

必须支持：
- list_by_work（order_index asc）
- create_after（插入在指定章节之后；后续章节 order_index 顺延）
- update_with_version（version 不一致抛 409）
- reorder_bulk（原子化全量提交）
- delete（删除后顺延 order_index）

- [ ] **Step 3: EditSessionRepo 实现**

必须支持：
- get(work_id)
- upsert(work_id, last_open_chapter_id, cursor_position, scroll_top)

- [ ] **Step 4: Repo 冒烟测试**

测试重点：
- create work 后必须有 1 章（R-CH-04）
- update_with_version 冲突返回 409 语义

---

### Task 1.3：V1 Service 层（业务规则落地）

**Files:**
- Create: `application/services/v1/work_service.py`
- Create: `application/services/v1/chapter_service.py`
- Create: `application/services/v1/session_service.py`
- Create: `application/services/v1/io_service.py`
- Test: `tests/unit/v1/test_services_rules.py`

- [ ] **Step 1: WorkService**

规则：
- 新建作品静默创建第 1 章 + session（R-CH-04）

- [ ] **Step 2: ChapterService**

规则：
- 保存携带 version，冲突抛 409（R-SAVE-04）
- reorder 必须单事务（R-CH-05）

- [ ] **Step 3: SessionService**

规则：
- get 返回 last_open_chapter_id/cursor/scroll
- put 必须幂等（重复提交不污染）

- [ ] **Step 4: IOService**

优先复用现有解析器（如 [txt_parser.py](file:///workspace/infrastructure/file/txt_parser.py) / [txt_exporter.py](file:///workspace/infrastructure/file/txt_exporter.py)），按 v1.1 规则封装：
- 导入解析失败 → 单章兜底（R-DATA-03）
- 导出按 order_index 拼接（R-DATA-04）

---

### Task 1.4：V1 API 路由（/api/v1）

**Files:**
- Create: `presentation/api/routers/v1/__init__.py`
- Create: `presentation/api/routers/v1/works.py`
- Create: `presentation/api/routers/v1/chapters.py`
- Create: `presentation/api/routers/v1/sessions.py`
- Create: `presentation/api/routers/v1/io.py`
- Modify: [app.py](file:///workspace/presentation/api/app.py)

- [ ] **Step 1: Works API**

实现：
- `GET /api/v1/works`
- `POST /api/v1/works`
- `GET /api/v1/works/{id}`
- `DELETE /api/v1/works/{id}`

- [ ] **Step 2: Chapters API**

实现：
- `GET /api/v1/works/{wid}/chapters`
- `POST /api/v1/works/{wid}/chapters`
- `PUT /api/v1/chapters/{id}`
- `DELETE /api/v1/chapters/{id}`
- `PUT /api/v1/works/{wid}/chapters/reorder`

- [ ] **Step 3: Sessions API**

实现：
- `GET /api/v1/works/{wid}/session`
- `PUT /api/v1/works/{wid}/session`

- [ ] **Step 4: IO API**

实现：
- `POST /api/v1/io/import`
- `GET /api/v1/io/export/{work_id}`

- [ ] **Step 5: curl 冒烟**

```bash
curl -s http://localhost:9527/health
```

---

### Task 1.5：前端 V1 API 层与 Stores（不依赖 lodash）

**Files:**
- Create: `frontend/src/api/v1.js`
- Create: `frontend/src/utils/debounce.js`
- Create: `frontend/src/stores/v1/useWorkspaceStore.js`
- Create: `frontend/src/stores/v1/useChapterDataStore.js`
- Create: `frontend/src/stores/v1/useSaveStateStore.js`
- Modify: `frontend/src/stores/index.js`（如存在）或在页面中直接引入

- [ ] **Step 1: 创建 v1 axios 实例**

基于现有 [index.js](file:///workspace/frontend/src/api/index.js) 的实现方式，V1 只需要：
- baseURL 指向 `/api/v1`（Electron 场景仍自动拼端口）

- [ ] **Step 2: 实现 debounce 工具**

不引入 lodash，提供一个最小 debounce：

```js
export function debounce(fn, wait) {
  let t = null
  const wrapped = (...args) => {
    if (t) clearTimeout(t)
    t = setTimeout(() => fn(...args), wait)
  }
  wrapped.flush = () => {
    if (!t) return
    clearTimeout(t)
    t = null
    fn()
  }
  return wrapped
}
```

- [ ] **Step 3: useWorkspaceStore（EditSession）**

职责：
- activeWorkId / activeChapterId / cursorPosition / scrollTop
- debouncedSaveSession()

- [ ] **Step 4: useChapterDataStore（数据）**

职责：
- 作品章节列表加载、切章数据加载
- reorder mapping 生成

- [ ] **Step 5: useSaveStateStore（状态机）**

职责：
- saveState 映射 UI（已保存/保存中/保存失败/离线）
- Local‑First：每次输入先写 localCache，再 debounce sync
- replayOfflineDrafts：按 timestamp 排序 + 串行 replay

---

### Task 1.6：前端页面 V1（书架 + 写作）

**Files:**
- Create: `frontend/src/views/v1/WorksList.vue`
- Create: `frontend/src/views/v1/WritingStudio.vue`
- Create: `frontend/src/views/v1/components/WorkCard.vue`
- Create: `frontend/src/views/v1/components/ImportModal.vue`
- Create: `frontend/src/views/v1/components/ChapterSidebar.vue`
- Create: `frontend/src/views/v1/components/PureTextEditor.vue`
- Create: `frontend/src/views/v1/components/StatusBar.vue`
- Modify: [router/index.js](file:///workspace/frontend/src/router/index.js)

- [ ] **Step 1: WorksList 状态（空/加载/失败）**

遵循 UI/UE 文档：
- 空态：大按钮新建/导入
- 加载态：Skeleton
- 错误态：重试按钮

- [ ] **Step 2: WritingStudio 布局（右侧栏默认隐藏）**

规则：
- 右侧栏 V1 默认隐藏，不允许展开复杂面板

- [ ] **Step 3: 自动保存链路打通**

链路：
用户输入 → Editor → DataStore → SaveStore → localCache → debounceSync → API → 后端 version+1 → 清除 localStorage 草稿

- [ ] **Step 4: 切章保护 UI**

规则：
- 保存中：阻止切章 + toast “正在同步…”
- 保存失败但有本地草稿：允许切章（无感）

- [ ] **Step 5: 运行前端测试**

```bash
cd frontend
npm run test
```

---

## Stage 2（P1）：稳定性增强（冲突/重试/容量/虚拟列表）

### Task 2.1：409 冲突弹窗与覆盖/放弃流程

- [ ] 前端弹窗（Element Plus Dialog）
- [ ] 覆盖：携带 `force_override=true`
- [ ] 放弃：重新拉取远端版本并覆盖编辑区，同时保留本地草稿直到用户确认

### Task 2.2：保存失败指数退避重试 + 手动重试入口

- [ ] 指数退避（例如 1s/2s/4s/8s，上限 N 次）
- [ ] 超过上限显示“点击重试”

### Task 2.3：虚拟滚动 + 拖拽兼容

- [ ] 章节列表 500+ 不卡顿
- [ ] 拖拽结束后顺序与可视区一致

---

## Stage 3（P2）：导入导出闭环与边界收口

### Task 3.1：TXT 导入兜底与顺序校正

- [ ] 无章节标记：单章兜底（成功返回）
- [ ] 空文件：导入成功，内容为空
- [ ] 导入后 order_index 连续 1..N

### Task 3.2：TXT 导出闭环

- [ ] 按 order_index 拼接导出
- [ ] 无章节：导出空文件

### Task 3.3：长章节软提示

- [ ] 超过 200000 字符显示软提示，不阻断输入/保存/切章

---

## DoD（总验收清单，全部完成才算 V1 交付）

- [ ] 书架可创建/导入/导出/删除作品
- [ ] 创建作品自动存在第 1 章（R-CH-04）
- [ ] 写作页可新建/删除/改名/调序/切章
- [ ] 章节编号与 order_index 一致（R-CH-01）
- [ ] 标题与正文同次 flush 提交（R-SAVE-01）
- [ ] 自动保存：Local‑First + 后端 version+1 + 清草稿
- [ ] 切章前内容进入可恢复状态（R-SAVE-03）
- [ ] 会话恢复：章节/光标/滚动条（R-EDIT-01）
- [ ] 并发编辑：409 冲突可见且无静默覆盖（R-SAVE-04）
- [ ] 离线写作不中断，联网后串行回放（R-SAVE-06）
- [ ] 编辑器仅支持纯文本（R-EDIT-04）

