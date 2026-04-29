# InkTrace V1 缺失交互补充设计（无需导入大纲）

更新时间：2026-04-29  
适用范围：V1（纯文本写作工具）  
目标：补齐 V1 当前实现中缺失的关键交互与入口，指导开发落地（不涉及导入大纲）。

---

## 0. 背景与约束

### 0.1 背景

当前 V1 主链路（书架 → 写作页、自动保存、离线回放、409 冲突）已基本落地，但存在 3 个会显著影响“可用性/可发现性”的缺口：

1. 新建作品后直接进入写作页，但缺少“作品标题/作者”的输入入口（用户无法按自己的作品命名）。
2. 书架页缺少“删除作品”的入口（后端已支持删除，但前端无触发点）。
3. TXT 导入采用“手动输入本地路径”，不符合产品交互（应为“选择文件窗口”）。

### 0.2 硬约束（保持 V1 边界）

- 不新增“大纲导入/大纲管理/结构整理/AI 写作”能力。
- 不改变 V1 的主链路：新建/导入成功后进入写作页 `/works/:id`。
- 保持 Local‑First 保存链路不受影响。

---

## 1. 新建作品：标题/作者入口（Create Work Modal）

### 1.1 目标

- 用户在“新建作品”时可填写：
  - **作品标题**（必填）
  - **作者**（可选）
- 创建成功后仍然**直接进入写作页**（减少步骤）。

### 1.2 交互流程

1. 用户在书架页点击“新建作品”按钮
2. 弹出 `CreateWorkModal` 对话框
3. 用户输入 `title` / `author`
4. 点击“创建并进入写作”
5. 调用 `POST /api/v1/works`
6. 成功后跳转 `/works/:id`

### 1.3 UI 规范

- 字段
  - 作品标题（必填）
    - 默认值：可使用现有的 “未命名作品 + 日期” 逻辑作为预填
    - 校验：空字符串禁止提交，提示“请输入作品标题”
  - 作者（可选）
- 按钮
  - 取消
  - 创建并进入写作（主按钮）
- 状态
  - 提交中：按钮禁用 + 文案“创建中…”
  - 失败：弹轻提示（Toast），不阻断页面

### 1.4 API 契约

- Request：`POST /api/v1/works`
  - body：`{ "title": string, "author": string }`
- Response：`{ id, title, author, current_word_count, created_at, updated_at }`

后端已满足该接口：见 [works.py](file:///workspace/presentation/api/routers/v1/works.py#L9-L45)。

### 1.5 开发落点（建议）

- 书架页：在 [NovelList.vue](file:///workspace/frontend/src/views/novel/NovelList.vue) 的“新建作品”按钮点击处，改为“先打开弹窗”，弹窗确认后再调用 `v1WorksApi.create` 并跳转。
- 新增组件（建议路径）：
  - `frontend/src/components/works/CreateWorkModal.vue`

### 1.6 验收标准（DoD）

- 点击新建 → 必定出现弹窗
- 标题为空不能提交
- 创建成功后进入 `/works/:id`，并能在书架卡片中看到正确标题/作者

---

## 2. 书架作品卡：更多菜单与删除入口（WorkCard Actions）

### 2.1 目标

- 书架页每个作品卡片必须有可发现的 `(...)` 更多操作入口
- V1 最小闭环必须实现：**删除作品（带二次确认）**

可选（不作为本补丁强制项）：
- 导出 TXT
- 重命名/修改作者（需要后端新增 PUT/PATCH，暂不强制）

### 2.2 交互流程（删除）

1. 用户在作品卡片点击 `(...)`
2. 弹出菜单项：
   - 删除作品（危险色）
3. 点击删除后弹出二次确认 Dialog：
   - 文案：“此操作不可恢复，确认删除？”
   - 按钮：取消 / 删除
4. 点击“删除”：
   - 调用 `DELETE /api/v1/works/:id`
   - 成功后刷新作品列表（或从列表中移除该项）

### 2.3 UI 规范

- `(...)` 点击行为必须 `stopPropagation`，避免误触进入写作页
- 删除按钮使用危险样式（红色）
- 二次确认必须存在

### 2.4 API 契约

- Request：`DELETE /api/v1/works/{work_id}`
- Response：`{ ok: true, id: work_id }`

后端已满足：见 [works.py](file:///workspace/presentation/api/routers/v1/works.py#L64-L68)。

前端 API 已存在：见 [index.js](file:///workspace/frontend/src/api/index.js#L343-L348)。

### 2.5 开发落点（建议）

- 在 [WorkCard.vue](file:///workspace/frontend/src/components/works/WorkCard.vue) 增加：
  - `(...)` 按钮
  - 下拉菜单（至少“删除”）
  - 删除确认弹窗（可用 Element Plus Dialog，或沿用现有轻量 Modal 风格）

### 2.6 验收标准（DoD）

- 作品卡片点击主体仍进入写作页
- 点击 `(...)` 不会跳转
- 删除需要二次确认
- 删除成功后列表立刻更新，刷新页面作品不存在

---

## 3. TXT 导入：文件选择窗口（不再手输路径）

### 3.1 目标

- 导入交互必须变为：“选择文件” → “开始导入”
- 不要求支持导入大纲

### 3.2 运行形态与策略

当前后端导入接口是“传 `file_path` 由后端读取本地文件”：
- [io.py](file:///workspace/presentation/api/routers/v1/io.py#L9-L26)

该方式对 **Electron/本地一体化部署**可行，对纯 Web 浏览器不可行。  
因此本补丁先以 **Electron 可落地**为目标，同时为未来 Web 上传预留扩展点。

### 3.3 交互流程（Electron 优先）

1. 用户点击“导入 TXT”
2. 弹窗内点击“选择文件”
3. 打开系统文件选择器（过滤 `.txt`）
4. 选择成功后：
   - UI 展示：文件名（可选展示路径）
   - 内部保存 `file_path`
5. 点击“开始导入”：
   - 调用 `POST /api/v1/io/import`，body：`{ file_path, title, author }`
6. 导入成功：
   - 刷新书架列表
   - 直接进入 `/works/:id`

### 3.4 UI 规范

- 移除“TXT 路径”可编辑输入框，改为：
  - 只读输入框（显示选择结果）
  - “选择文件”按钮
- 未选择文件时点击导入：提示“请先选择 TXT 文件”
- 导入中：按钮禁用 + “导入中…”

### 3.5 开发落点（建议）

当前导入弹窗实现为“手输路径”，见 [ImportModal.vue](file:///workspace/frontend/src/components/works/ImportModal.vue#L12-L27)。

建议改造：
- `file_path` 不再由用户输入，而是由文件选择器填充
- Electron 环境可优先调用 `window.electronAPI`（若已存在）：
  - `const path = await window.electronAPI.openFileDialog({ filters: [{ name: 'Text', extensions: ['txt'] }] })`
- 若 electronAPI 暂未提供，可先用浏览器 `<input type="file">` 获取文件名用于展示，但此时仍无法把本地路径传给后端；因此 **最终仍建议补 electronAPI 文件选择能力**（作为桌面应用的一部分）。

### 3.6 API 契约

- Request：`POST /api/v1/io/import`
  - body：`{ file_path: string, title?: string, author?: string }`
- Response：work DTO（id/title/author/word_count/created/updated）

前端调用点：`v1IOApi.importTxt` 已存在，见 [index.js](file:///workspace/frontend/src/api/index.js#L364-L367)。

### 3.7 验收标准（DoD）

- 导入弹窗不允许手输路径（必须通过选择文件）
- 选择 TXT 后可正常导入并生成作品
- 导入成功后：作品出现在书架；可进入写作页；章节可加载

---

## 4. 不在本补丁范围内

- 导入大纲 / 大纲管理 / 结构整理 / AI 写作入口
- 作品重命名 / 修改作者（除非后端补 `PUT/PATCH /api/v1/works/{id}`）
- 导入 Web 上传（multipart upload）模式（需要后端新增 upload API）

