# Stage 0 Tasks

### T0-01：项目结构初始化

目标：

- 建立 V1.1 Workbench 的前后端基础目录与命名空间，形成后续开发基线。

涉及模块：

- Backend / Frontend / Store

实现内容：0000000000000000000000

- 新建后端 V1.1 Router 命名空间：`presentation/api/routers/v1/`。
- 新建后端 V1.1 Service 命名空间：`application/services/v1/`。
- 新建后端 V1.1 数据访问命名空间：`infrastructure/database/v1/`。
- 确认前端 Workbench 页面与组件命名空间：`frontend/src/views/works/`、`frontend/src/components/works/`。
- 确认前端 Store 文件命名：`workspace.js`、`chapterData.js`、`saveState.js`、`writingAsset.js`、`preference.js`。
- 新建 V1.1 基线说明文件或目录占位文件，避免空目录无法提交。

关键规则：

- 新功能一律落在 Workbench 域。
- 禁止 Workbench 引用 Legacy Store、Legacy UI、Legacy API、Legacy Service。
- 禁止新增 AI 入口、AI 自动分析、AI 自动生成、AI 自动抽取。

完成标准（DoD）：

- 后端 V1.1 目录存在且可被 Python 导入。
- 前端 Workbench 目录存在且不引用 Legacy 目录。
- 项目启动不因新增目录或占位文件报错。

### T0-02：API 路由基础（/api/v1）

目标：

- 建立 `/api/v1/*` API 挂载基础，确保 V1.1 后续接口统一进入 Workbench 路由命名空间。

涉及模块：

- Backend

实现内容：

- 在 `presentation/api/routers/v1/__init__.py` 暴露 V1.1 Router 注册入口。
- 新建 `presentation/api/routers/v1/health.py` 或等价基础路由文件。
- 在应用入口中注册 `/api/v1` 前缀。
- 提供 `GET /api/v1/health` 基础健康检查接口。
- 确认旧 `/api/*` 不承载 V1.1 新能力。

关键规则：

- Workbench API 统一挂载 `/api/v1/*`。
- Legacy 旧 `/api/*` 不承载 V1.1 新能力。
- Stage 0 不实现 Works、Chapters、Outline、Timeline、Foreshadow、Character 业务接口。

完成标准（DoD）：

- 启动后访问 `GET /api/v1/health` 返回 200。
- `/api/v1/health` 响应可标识 V1.1 Workbench API 可用。
- 应用启动日志中能确认 V1.1 Router 已注册。

### T0-03：数据库连接与基础表基线

目标：

- 建立 V1.1 数据库连接与基础表迁移基线，为 Stage 1 数据结构收口提供稳定基础。

涉及模块：

- Backend / DB

实现内容：

- 新建或确认 `infrastructure/database/v1/session.py` 数据库连接入口。
- 配置 SQLite WAL、`busy_timeout`、`foreign_keys` 基础连接行为。
- 新建或确认 `infrastructure/database/v1/models.py` 作为 V1.1 ORM 模型入口。
- 建立基础表迁移入口，允许后续使用 `CREATE TABLE IF NOT EXISTS` 扩展。
- 仅校验 `works`、`chapters`、`edit_sessions` 基础表是否可迁移，不实现业务写入。
- 统一 `version` 字段策略：整数类型，默认值为 `1`，仅作为后续乐观锁字段预留。

关键规则：

- 新增表使用 `CREATE TABLE IF NOT EXISTS`。
- 所有 `id` 统一为 UUID 字符串。
- `version` 字段统一为整数类型，默认值为 `1`，Stage 0 不实现版本校验逻辑。
- 所有时间字段使用 ISO 8601 字符串且时区口径统一。

完成标准（DoD）：

- 数据库连接可初始化成功。
- 外键约束开启。
- 基础迁移入口可重复执行且不破坏现有数据。
- Stage 0 不写入章节、作品、结构化资产业务数据。

### T0-04：错误处理与返回结构

目标：

- 建立 V1.1 API 统一错误响应与 409 冲突响应模板。

涉及模块：

- Backend

实现内容：

- 新建或确认 `presentation/api/routers/v1/schemas.py` 中的通用错误响应结构。
- 定义通用错误响应：`{"detail": "error_code"}`。
- 定义 409 冲突响应字段：`detail`、`server_version`、`resource_type`、`resource_id`。
- 建立错误码到 HTTP 状态码映射表。
- 统一错误响应字段命名规范：所有字段必须使用 `snake_case`，字段名全局不可变更。
- 在 `/api/v1/health` 或测试路由中验证统一错误响应处理链路。

关键规则：

- `version_conflict` 对应 409。
- `asset_version_conflict` 对应 409。
- `work_not_found`、`chapter_not_found`、`asset_not_found` 对应 404，`invalid_input` 对应 400。
- 错误响应字段必须使用 `snake_case` 命名。

完成标准（DoD）：

- 通用错误响应结构可被 Router 复用。
- 409 响应模板字段完整。
- 错误码映射单元测试通过。

### T0-05：日志系统基线

目标：

- 建立 V1.1 可追踪的基础日志口径，支持后续联调定位路由、数据库、保存链路问题。

涉及模块：

- Backend / Frontend

实现内容：

- 后端新增或确认 V1.1 日志分类：API、DB、Service、Error。
- 后端 `/api/v1/*` 请求记录 method、path、status、duration。
- 后端错误日志记录 `error_code` 与 request path。
- 前端新增或确认 Workbench 调试日志开关，仅在开发环境启用。
- 前端 Local-First 相关日志预留分类：draft、flush、conflict、offline。

关键规则：

- 日志不得记录正文完整内容。
- 日志不得记录结构化资产完整内容。
- 日志不得暴露本地草稿内容或用户隐私文本。

完成标准（DoD）：

- 请求 `/api/v1/health` 时后端输出一条 V1.1 API 日志。
- 触发测试错误时后端输出 `error_code`。
- 前端生产构建不输出开发调试日志。

### T0-06：工具函数基线（textMetrics）

目标：

- 建立正文有效字数统计的统一工具口径，避免前后端统计分叉。

涉及模块：

- Backend / Frontend

实现内容：

- 后端新增或确认 textMetrics 工具入口，用于计算正文有效字符数。
- 前端新增或确认 textMetrics 工具入口，用于实时展示正文有效字符数。
- 统一统计规则：去除空格、换行符、制表符等不可见空白字符后统计剩余字符数。
- 增加基础测试用例覆盖中文、英文、空格、换行、制表符、空字符串。
- 标题不纳入正文有效字数统计。

关键规则：

- `word_count` 必须采用同一套 textMetrics 口径。
- 前端实时展示值与后端持久化值必须使用同一统计口径。
- 标题不计入正文字数。

完成标准（DoD）：

- 后端 textMetrics 测试通过。
- 前端 textMetrics 测试通过。
- 同一输入在前后端统计结果一致。

### T0-07：Local-First 草稿结构定义

目标：

- 建立 Local-First 草稿数据结构与缓存 key 规范，为 Stage 2 保存链路实现提供基础。

涉及模块：

- Frontend / Store

实现内容：

- 新建或确认 `frontend/src/composables/useLocalCache.js` 基础入口。
- 定义正文草稿 key：`draft:{work_id}:{chapter_id}`。
- 定义结构化资产暂存 key 前缀：`asset_draft:{asset_type}:{asset_id}`。
- 定义正文草稿 payload 字段：`workId`、`chapterId`、`title`、`content`、`version`、`cursorPosition`、`scrollTop`、`timestamp`。
- 定义结构化资产暂存 payload 字段：`assetType`、`assetId`、`payload`、`version`、`timestamp`。
- 定义缓存容量策略常量：10MB 软上限、LRU 淘汰、当前正文草稿与冲突草稿保护。

关键规则：

- 切章前必须将当前编辑内容写入本地草稿，网络保存允许异步完成。
- 结构化资产不进入正文自动回放队列。
- 冲突未决策前不得清理本地草稿或本地暂存。

完成标准（DoD）：

- Local cache 工具入口可被 Store 导入。
- 正文草稿 key 与 payload 类型定义完成。
- 结构化资产暂存 key 与 payload 类型定义完成。
- 单元测试覆盖 key 生成、payload 基础校验、LRU 保护规则。

### T0-08：Workbench Store 空壳初始化

目标：

- 建立 V1.1 前端 Store 基础壳，确保后续 Stage 2/4 可以在统一状态边界内开发。

涉及模块：

- Frontend / Store

实现内容：

- 新建或确认 `useWorkspaceStore`，仅保留作品上下文与会话字段占位。
- 新建或确认 `useChapterDataStore`，仅保留章节列表、激活章节、标题/正文草稿字段占位。
- 新建或确认 `useSaveStateStore`，仅保留保存状态、待保存队列、冲突 payload 字段占位。
- 新建或确认 `useWritingAssetStore`，仅保留资产列表、资产草稿、Drawer 状态字段占位。
- 新建或确认 `usePreferenceStore`，仅保留本地偏好字段占位。
- 所有 Store 禁止在 Stage 0 调用业务 API。

关键规则：

- Store 命名必须使用 Workbench 语义。
- Workbench Store 禁止引用 Legacy Store。
- Stage 0 不实现 Chapters、Outline、Timeline、Foreshadow、Character 业务行为。

完成标准（DoD）：

- 所有 Store 可被前端项目导入。
- Store 初始化不发起业务 API 请求。
- 前端启动不因 Store 空壳报错。

### T0-09：Workbench 前端路由与页面壳

目标：

- 建立 Workbench 前端路由与页面壳，供后续 Stage 2 写作页开发挂载。

涉及模块：

- Frontend

实现内容：

- 确认 `/works` 路由指向书架页壳。
- 确认 `/works/:id` 路由指向 `WritingStudio` 页面壳。
- 新建或确认 `WorksList` 页面壳，不实现作品业务列表。
- 新建或确认 `WritingStudio` 页面壳，仅保留 Header、ChapterSidebar、Editor、AssetRail、AssetDrawer 占位区域。
- 确认路由不自动混跳到 Legacy 页面。

关键规则：

- V1.1 不新增主页面。
- `/works/:id` 是写作工作台唯一页面。
- 结构化资产不得出现在主编辑区，只能通过 AssetDrawer 承载。

完成标准（DoD）：

- 前端访问 `/works` 不报错。
- 前端访问 `/works/:id` 不报错。
- 页面壳中不存在 AI 入口。
- 页面壳中不存在 Legacy 组件引用。

### T0-10：Stage 0 基线验证

目标：

- 对 Stage 0 输出进行统一验证，确认可进入 Stage 1。

涉及模块：

- Backend / Frontend / DB / Store

实现内容：

- 启动后端并访问 `GET /api/v1/health`。
- 执行数据库连接与基础迁移验证。
- 启动前端并访问 `/works`、`/works/:id`。
- 执行后端错误码、textMetrics 基础测试。
- 执行前端 Store、Local cache、textMetrics 基础测试。
- 检查 Workbench 无 Legacy 引用与无 AI 入口。

关键规则：

- Stage 0 只建立开发基线，不实现业务功能。
- Workbench 与 Legacy 边界必须可验证。
- Local-First 基础结构必须先于正文保存业务实现完成。

完成标准（DoD）：

- 后端服务可启动。
- 前端服务可启动。
- `/api/v1/health` 返回 200。
- `/works` 与 `/works/:id` 页面壳可访问。
- Stage 0 测试全部通过。
- 可进入 Stage 1 后端收口。

