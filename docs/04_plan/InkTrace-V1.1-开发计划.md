# InkTrace V1.1 开发计划 Final

版本：v1.1 Final  
更新时间：2026-04-30  
依据文档：

- `docs/01_requirements/InkTrace-V1.1-需求规格说明书.md`
- `docs/02_architecture/InkTrace-V1.1-架构设计文档.md`
- `docs/03_design/InkTrace-V1.1-详细设计文档.md`
- `docs/03_design/InkTrace-V1.1-界面与交互设计文档.md`

***

## 1. 总体策略

### 1.1 阶段目标

V1.1 是 V2 AI 接入前的非 AI 创作工作台封版阶段，目标是完成写作体验收口、数据闭环增强与结构化写作资产沉淀。

交付批次：

| 批次 | 范围 | 交付属性 | 是否影响 V1.1 完整性 |
|---|---|---|---|
| V1.1-A | 写作体验与数据闭环收口 | 必须交付，可单独提测 | 是 |
| V1.1-B | 非 AI 写作组织能力 | 必须交付，后置批次 | 是 |
| V1.1-C | 体验偏好增强 | 可选交付 | 否 |

### 1.2 开发原则

- 新功能一律落在 Workbench 域。
- API 统一使用 `/api/v1/*` 前缀。
- Service 统一使用 V1.1 专用服务命名：`WorkService`、`ChapterService`、`SessionService`、`IOService`、`WritingAssetService`。
- Store 统一使用 Workbench 命名：`useWorkspaceStore`、`useChapterDataStore`、`useSaveStateStore`、`useWritingAssetStore`、`usePreferenceStore`。
- 资源命名统一使用 `outline`、`timeline`、`foreshadow`、`character`。
- 禁止 Workbench 引用 Legacy Store、Legacy UI、Legacy API、Legacy Service。
- 禁止新增 AI 入口、AI 自动分析、AI 自动生成、AI 自动抽取。
- 禁止新增主页面。
- 结构化资产只允许通过 AssetDrawer 编辑。
- 正文链路优先保证 Local-First 与不中断输入。
- 每个阶段完成 60%~70% 时必须进行前后端联调验证。

### 1.3 工期估算

| 阶段 | 估算工时 | 交付物 |
|---|---:|---|
| Stage 0：基线校准与隔离检查 | 1 天 | V1.1 开发基线与风险清单 |
| Stage 1：V1.1-A 后端收口 | 2-3 天 | Works/Chapters/Sessions/IO API 收口 |
| Stage 2：V1.1-A 前端收口 | 3-4 天 | 写作页 UI/UE、Local-First、导入导出闭环 |
| Stage 3：V1.1-B 后端结构化资产 | 3-4 天 | Outlines/Timeline/Foreshadows/Characters API |
| Stage 4：V1.1-B 前端结构化资产 | 4-5 天 | AssetRail/AssetDrawer 与四大面板 |
| Stage 5：稳定性与验收 | 2-3 天 | 冲突、离线、删除清理、回归测试 |
| Stage 6：V1.1-C 可选增强 | 1-2 天 | 专注模式、偏好、今日新增字数、立即同步 |
| 合计 | 16-22 天 | V1.1 完整交付 |

***

## 2. Stage 0：基线校准与隔离检查

### 2.1 目标

确认当前 V1 主链路稳定，建立 V1.1 开发基线，防止在旧 AI/Legacy 语义上继续叠加。

### 2.2 任务清单

| ID | 任务 | 类型 | 验收标准 |
|---|---|---|---|
| S0-01 | 确认 Workbench 主路由 | 前端 | `/works`、`/works/:id` 为 V1.1 主入口 |
| S0-02 | 确认 Legacy 路由隔离 | 前端 | Workbench 页面不引用 Legacy Store/UI |
| S0-03 | 确认 `/api/v1/*` 边界 | 后端 | V1.1 新 API 全部挂载在 `/api/v1/*` |
| S0-04 | 确认 Legacy API 不承载新能力 | 后端 | 旧 `/api/*` 不新增 V1.1 能力 |
| S0-05 | 确认数据表迁移基线 | 后端 | `works`、`chapters`、`edit_sessions` 字段口径符合设计 |
| S0-06 | 确认非 AI 边界 | 全栈 | Workbench 无 AI 按钮、AI 状态、AI 自动生成入口 |
| S0-07 | 建立 V1.1 回归用例清单 | 测试 | 覆盖写作页、保存、切章、导入导出、删除章节 |

### 2.3 关键实现约束

- Workbench 与 Legacy 允许运行时共存，但新功能不得落入 Legacy。
- Legacy 页面、接口、Store 不作为 V1.1 隐式迁移路径。

### 2.4 联调节点

当 Stage 0 完成 60%~70% 时，进行基线启动验证：

- 前端路由可进入 `/works` 与 `/works/:id`。
- 后端 `/api/v1/*` 路由命名空间可注册。
- Workbench 页面无 Legacy Store/UI/API 调用。

### 2.5 出口标准

- V1 当前功能可启动、可写作、可保存。
- Workbench 与 Legacy 边界可验证。
- V1.1-A 开发不依赖 Legacy 业务语义。

***

## 3. Stage 1：V1.1-A 后端收口

### 3.1 数据与迁移

骨架路径：

| 层级 | 骨架路径 | 范围 |
|---|---|---|
| 数据模型 | `infrastructure/database/v1/models.py` | `works`、`chapters`、`edit_sessions` |
| Repository | `infrastructure/database/v1/repositories/` | `WorkRepo`、`ChapterRepo`、`EditSessionRepo` |
| 数据库连接 | `infrastructure/database/v1/session.py` | SQLite WAL、foreign key、busy timeout |

任务：

| ID | 任务 | 范围 | 验收标准 |
|---|---|---|---|
| S1-01 | `chapters.title` 空值策略收口 | chapters | 后端统一存空字符串，不存 `NULL` |
| S1-02 | `chapters.order_index` 排序口径收口 | chapters | 列表、导入、删除、调序均以 `order_index` 为唯一排序依据 |
| S1-03 | `chapters.version` 乐观锁收口 | chapters | 保存时校验 `expected_version`，冲突返回 409 |
| S1-04 | `chapters.word_count` 口径收口 | chapters | 服务端按 textMetrics 规则重算正文有效字符数 |
| S1-05 | `edit_sessions` 会话恢复收口 | edit_sessions | 支持章节、光标、滚动位置恢复 |
| S1-06 | 通用字段口径收口 | 全表 | `id` UUID 字符串，`version` 资源级自增，时间 ISO 8601 统一时区 |

### 3.2 Service 收口

骨架路径：

| Service | 文件路径 | 职责 |
|---|---|---|
| `WorkService` | `application/services/v1/work_service.py` | 作品 CRUD、创建首章、删除作品级联 |
| `ChapterService` | `application/services/v1/chapter_service.py` | 章节 CRUD、乐观锁保存、删除焦点建议、章节调序 |
| `SessionService` | `application/services/v1/session_service.py` | 会话恢复、光标与滚动位置保存 |
| `IOService` | `application/services/v1/io_service.py` | TXT 导入导出 |

任务：

| ID | 任务 | 服务 | 验收标准 |
|---|---|---|---|
| S1-07 | WorkService 创建作品首章 | WorkService | 创建作品时同事务创建第 1 章 |
| S1-08 | WorkService 删除作品级联 | WorkService | 删除作品时删除章节、会话与结构化资产 |
| S1-09 | ChapterService 标题正文同链路保存 | ChapterService | 每次保存同时处理 `title` 与 `content` |
| S1-10 | ChapterService 删除章节编排 | ChapterService | 删除后返回建议激活章节，重排 `order_index` |
| S1-11 | ChapterService 调序原子化 | ChapterService | 完整映射列表 + 单事务批量写入 |
| S1-12 | SessionService 兜底恢复 | SessionService | 无会话时默认第一章、光标 0、滚动 0 |
| S1-13 | IOService TXT 导入 | IOService | 支持空文件、无章节标记单章兜底、编码识别 |
| S1-14 | IOService TXT 导出 | IOService | 按 `order_index ASC` 导出，支持格式选项 |

### 3.3 API 收口

Router 骨架路径：`presentation/api/routers/v1/`

| ID | Router | API | 验收标准 |
|---|---|---|---|
| S1-15 | `works.py` | `/api/v1/works/*` | 更新作品名、作者；删除作品；返回字数与时间 |
| S1-16 | `chapters.py` | `/api/v1/works/{work_id}/chapters`、`/api/v1/chapters/{chapter_id}` | 新建、保存、删除、调序符合详细设计 |
| S1-17 | `sessions.py` | `/api/v1/works/{work_id}/session` | 读取与保存 `last_open_chapter_id`、`cursor_position`、`scroll_top` |
| S1-18 | `io.py` | `/api/v1/io/import`、`/api/v1/io/export/{work_id}` | Web TXT 导入与导出闭环 |
| S1-19 | `schemas.py` | 请求/响应 DTO | 错误码与 409 模板统一 |

### 3.4 关键实现约束

- Chapter 调序必须一次性提交完整映射列表，由后端单事务批量写入，禁止逐条更新或逐条 `commit`。
- 切章相关保存不得依赖网络保存成功作为前置条件；当前内容进入本地可恢复状态后即可继续。

### 3.5 联调节点

当 Stage 1 完成 60%~70% 时，进行 A 批后端联调：

- Works/Chapters/Sessions API 返回结构稳定。
- 保存接口可模拟 409。
- TXT 导入导出接口可用。
- 前端可基于 `/api/v1/*` 真实接口替换 Mock。

### 3.6 后端测试

必须覆盖：

- 创建作品自动创建首章。
- 标题为空字符串保存。
- 标题禁止写入“第X章”前缀。
- 正文字数按 textMetrics 口径计算。
- 保存版本冲突返回 409 模板。
- 删除章节后焦点建议正确。
- 删除章节后 `order_index` 连续。
- 章节调序拒绝缺失、重复、多余映射。
- TXT 导入空文件、无章节标记、编码失败、20MB 上限。
- TXT 导出按章节顺序输出。

***

## 4. Stage 2：V1.1-A 前端收口

### 4.1 前端骨架

核心模块：

| 模块 | 关键对象 | 职责 |
|---|---|---|
| 页面 | `WorksList`、`WritingStudio` | 书架入口与写作页主容器 |
| 章节 | `ChapterSidebar`、`ChapterTitleInput`、`PureTextEditor` | 章节定位、标题、正文输入 |
| 状态 | `StatusBar`、`VersionConflictModal` | 保存状态与冲突处理 |
| Store | `useWorkspaceStore`、`useChapterDataStore`、`useSaveStateStore` | 会话、章节数据、Local-First 保存 |
| 缓存 | `useLocalCache` | 正文草稿、本地容量控制 |

### 4.2 写作页 UI/UE

| ID | 任务 | 组件 | 验收标准 |
|---|---|---|---|
| S2-01 | Header 收口 | Header | 显示作品名，长标题截断，不显示 UUID |
| S2-02 | 作品重命名 | Header | Enter 提交，Esc 放弃，失败回滚 |
| S2-03 | 章节标题输入 | ChapterTitleInput | 展示“第X章 + title”，保存时不写前缀 |
| S2-04 | 正文编辑区去噪 | PureTextEditor | 仅标题、正文、状态条，无说明/调试占位 |
| S2-05 | 默认焦点规则 | WritingStudio | 打开、切章、新建章节后正文 textarea 获得焦点 |
| S2-06 | 纯文本输入 | PureTextEditor | 禁止富文本工具栏，粘贴按纯文本处理 |
| S2-07 | 状态条 | StatusBar | 展示 saving、synced、offline、conflict、error |

### 4.3 ChapterSidebar

| ID | 任务 | 验收标准 |
|---|---|---|
| S2-08 | 章节列表动态编号 | 章节编号由 `order_index` 计算 |
| S2-09 | 章节搜索 | 搜索只过滤展示，不改变原数组顺序 |
| S2-10 | 跳转第 N 章 | 非数字、越界、成功跳转均有确定行为 |
| S2-11 | 新建章节 | 默认追加末尾，清空搜索，激活新章，正文聚焦 |
| S2-12 | 激活项可见 | active chapter 变化后 `scrollIntoView` |
| S2-13 | 本地状态标记 | 草稿、冲突状态在章节项轻量展示 |

### 4.4 Local-First 保存链路

| ID | 任务 | Store/模块 | 验收标准 |
|---|---|---|---|
| S2-14 | Store 职责收口 | `useWorkspaceStore` | 管作品上下文、会话恢复 |
| S2-15 | Store 职责收口 | `useChapterDataStore` | 管章节、激活章节、标题/正文草稿 |
| S2-16 | Store 职责收口 | `useSaveStateStore` | 管 Local-First、离线回放、409 冲突 |
| S2-17 | 本地草稿写入 | `useLocalCache` | 输入立即写入本地草稿 |
| S2-18 | 防抖保存 | `useSaveStateStore` | debounce 后提交远端 |
| S2-19 | 成功清理缓存 | `useSaveStateStore` | 收到 200 后清理对应草稿 |
| S2-20 | 409 保留缓存 | `useSaveStateStore` | 冲突未决策前不清理草稿 |
| S2-21 | 离线回放 | `useSaveStateStore` | 网络恢复后按 timestamp 串行回放 |
| S2-22 | 切章保护 | `useSaveStateStore` | 切章前写入本地草稿，网络保存异步继续 |
| S2-23 | Ctrl/Cmd+S 正文路径 | `useSaveStateStore` | 正文聚焦时立即 flush 标题 + 正文，并更新会话 |

### 4.5 导入导出 UI

| ID | 任务 | 验收标准 |
|---|---|---|
| S2-24 | Web TXT 导入入口 | 书架或作品操作入口可上传 TXT |
| S2-25 | 导入结果跳转 | 导入成功后进入写作页并展示章节 |
| S2-26 | 导入错误提示 | 编码失败、超限文件提示明确 |
| S2-27 | TXT 导出入口 | 作品设置或书架卡片提供导出 |
| S2-28 | 导出选项 | 支持 `include_titles` 与 `gap_lines` |

### 4.6 关键实现约束

- Local-First 不允许等待网络保存成功后才允许切章；切章前必须确保本地草稿已写入。
- 搜索只改变展示集合，不改变章节数组顺序与 `order_index`。

### 4.7 联调节点

当 Stage 2 完成 60%~70% 时，进行 V1.1-A 前后端联调：

- 前端从 Mock 切换到 `/api/v1/*`。
- 验证创建作品、章节保存、会话恢复、TXT 导入导出。
- 验证 409 冲突与离线写入本地草稿。

### 4.8 前端测试

必须覆盖：

- 页面打开默认焦点给正文 textarea。
- 标题输入不保存“第X章”前缀。
- 输入正文后刷新不丢字。
- 切章前写入本地草稿，不等待网络成功。
- 搜索不改变章节顺序。
- 新建章节追加末尾并聚焦正文。
- Ctrl/Cmd+S 正文聚焦触发立即 flush。
- 409 冲突保留本地草稿。
- 离线输入恢复后自动回放。

### 4.9 V1.1-A 提测出口

- 从书架创建作品，进入写作页，输入标题和正文，刷新不丢。
- 新建章节、切章、删除章节、搜索、跳转第 N 章可用。
- TXT 导入导出闭环可用。
- 保存状态、离线状态、冲突状态可验证。
- Workbench 不出现 AI 入口。

***

## 5. Stage 3：V1.1-B 后端结构化资产

### 5.1 数据表与字段口径

骨架路径：

| 层级 | 骨架路径 | 范围 |
|---|---|---|
| 数据模型 | `infrastructure/database/v1/models.py` | `work_outlines`、`chapter_outlines`、`timeline_events`、`foreshadows`、`characters` |
| Repository | `infrastructure/database/v1/repositories/` | 结构化资产 Repository |
| Service | `application/services/v1/writing_asset_service.py` | 结构化资产业务编排 |

任务：

| ID | 表 | 验收标准 |
|---|---|---|
| S3-01 | `work_outlines` | `content_text` 唯一真实存储，`content_tree_json` 派生缓存 |
| S3-02 | `chapter_outlines` | 章节细纲随章节删除 |
| S3-03 | `timeline_events` | `order_index` 为排序唯一依据，章节删除时引用置空 |
| S3-04 | `foreshadows` | `status` 仅允许 `open/resolved`，章节引用可置空 |
| S3-05 | `characters` | `aliases_json` JSON array，服务端规范化 aliases |
| S3-06 | `content_tree_json` schema | 节点字段白名单、`chapter_ref` 引用、禁止 AI 语义字段 |

### 5.2 Repository 与事务

| ID | 任务 | 验收标准 |
|---|---|---|
| S3-07 | WorkOutlineRepo | 支持读取、保存、清理章节引用 |
| S3-08 | ChapterOutlineRepo | 支持读取、保存、随章节删除 |
| S3-09 | TimelineEventRepo | 支持 CRUD、完整映射调序 |
| S3-10 | ForeshadowRepo | 支持 CRUD、按状态筛选、章节引用置空 |
| S3-11 | CharacterRepo | 支持 CRUD、按 `name + aliases` 搜索 |
| S3-12 | 删除章节引用清理 | 单事务内清理大纲节点、时间线、伏笔、细纲 |
| S3-13 | Timeline 调序事务 | 一次性提交完整映射，单事务批量写入 |

### 5.3 WritingAssetService

| ID | 任务 | 验收标准 |
|---|---|---|
| S3-14 | Outline 显式保存 | 携带 `expected_version`，409 返回冲突模板 |
| S3-15 | ChapterOutline 显式保存 | 当前章节细纲独立版本控制 |
| S3-16 | Timeline CRUD | 新事件追加末尾，更新携带 `expected_version` |
| S3-17 | Timeline 调序 | 校验数量、连续顺序、缺失/重复/多余映射 |
| S3-18 | Foreshadow CRUD | 默认列表 `open`，支持切换 `resolved` |
| S3-19 | Character CRUD | aliases trim、去空、去重、保持顺序 |
| S3-20 | 结构化资产冲突 | `asset_version_conflict` 409 模板统一 |

### 5.4 API

Router 骨架路径：`presentation/api/routers/v1/`

| ID | Router | API | 验收标准 |
|---|---|---|---|
| S3-21 | `outlines.py` | `/api/v1/works/{work_id}/outline`、`/api/v1/chapters/{chapter_id}/outline` | 全书大纲、章节细纲读取与保存 |
| S3-22 | `timeline.py` | `/api/v1/works/{work_id}/timeline-events`、`/api/v1/timeline-events/{event_id}` | 事件 CRUD、调序 API |
| S3-23 | `foreshadows.py` | `/api/v1/works/{work_id}/foreshadows`、`/api/v1/foreshadows/{foreshadow_id}` | 伏笔 CRUD、状态筛选 |
| S3-24 | `characters.py` | `/api/v1/works/{work_id}/characters`、`/api/v1/characters/{character_id}` | 人物 CRUD、搜索 |
| S3-25 | `chapters.py` 联动 | `/api/v1/chapters/{chapter_id}` | 删除章节后所有结构化资产引用符合设计 |

### 5.5 关键实现约束

- Timeline 调序必须完整映射提交，禁止前端逐条提交或后端逐条独立提交。
- `content_tree_json` 必须遵循 schema 白名单，禁止 AI 语义字段。

### 5.6 联调节点

当 Stage 3 完成 60%~70% 时，进行 B 批后端联调：

- Outlines/Timeline/Foreshadows/Characters API 返回结构稳定。
- 结构化资产 409 可模拟。
- 删除章节后引用清理可验证。
- 前端 AssetDrawer 可接入真实接口。

### 5.7 后端测试

必须覆盖：

- Outline `content_text` 主存储与 `content_tree_json` 派生缓存。
- `content_tree_json` schema 白名单。
- 删除章节仅置空大纲节点 `chapter_ref`。
- 删除章节删除对应 `chapter_outlines`。
- 删除章节置空 timeline、foreshadow 章节引用。
- Timeline 调序完整映射校验。
- 结构化资产 409 响应模板。
- Character aliases 规范化与搜索。

***

## 6. Stage 4：V1.1-B 前端结构化资产

### 6.1 前端骨架

核心模块：

| 模块 | 关键对象 | 职责 |
|---|---|---|
| Store | `useWritingAssetStore` | 结构化资产读取、编辑草稿、显式保存、冲突状态 |
| 缓存 | `useLocalCache` | `asset_draft:*` 本地暂存 |
| 抽屉 | `AssetRail`、`AssetDrawer` | 结构化资产入口与单抽屉容器 |
| 面板 | `OutlinePanel`、`TimelinePanel`、`ForeshadowPanel`、`CharacterPanel` | 四类结构化资产编辑 |
| 冲突 | `AssetConflictModal` | 结构化资产 409 决策 |

### 6.2 AssetRail 与 AssetDrawer

| ID | 任务 | 组件 | 验收标准 |
|---|---|---|---|
| S4-01 | AssetRail 图标入口 | AssetRail | 展示 Outline/Timeline/Foreshadow/Character |
| S4-02 | 单 Drawer 容器 | AssetDrawer | 同一时间只打开一个 Drawer |
| S4-03 | 单 Tab 激活 | AssetDrawer | 同一时间只显示一个模块 |
| S4-04 | Drawer 不抢焦点 | AssetDrawer | 打开/关闭不主动改变正文焦点 |
| S4-05 | dirty 切换保护 | AssetDrawer | dirty 时切换 Tab 需保存/放弃/取消 |
| S4-06 | 移动端覆盖层 | AssetDrawer | 小屏下 Drawer 使用覆盖层 |

### 6.3 OutlinePanel

| ID | 任务 | 验收标准 |
|---|---|---|
| S4-07 | 全书大纲文本编辑 | `content_text` 为主编辑视图 |
| S4-08 | 当前章节细纲编辑 | 切章后自动加载目标章节细纲 |
| S4-09 | 树状视图缓存 | `content_tree_json` 仅显式保存时提交 |
| S4-10 | 章节引用清理展示 | 被删除章节引用显示为空 |
| S4-11 | 保存与冲突 | 保存携带 `expected_version`，409 打开冲突弹窗 |

### 6.4 TimelinePanel

| ID | 任务 | 验收标准 |
|---|---|---|
| S4-12 | 事件列表 | 按 `order_index ASC` 展示 |
| S4-13 | 事件 CRUD | 创建、编辑、删除可用 |
| S4-14 | 关联章节 | 可选择章节或空引用 |
| S4-15 | 上移/下移排序 | 本地重排后提交完整映射 |
| S4-16 | 排序保存 | 成功后更新列表版本与顺序 |

### 6.5 ForeshadowPanel

| ID | 任务 | 验收标准 |
|---|---|---|
| S4-17 | 未回收默认视图 | 默认展示 `open` |
| S4-18 | 已回收切换 | 可切换 `resolved` 列表 |
| S4-19 | 伏笔 CRUD | 标题、描述、引入章、回收章可编辑 |
| S4-20 | 章节引用置空展示 | 被删除章节引用显示为空 |

### 6.6 CharacterPanel

| ID | 任务 | 验收标准 |
|---|---|---|
| S4-21 | 人物列表 | 展示人物名称 |
| S4-22 | 人物编辑区 | 支持 name、aliases、description |
| S4-23 | aliases 输入转换 | 逗号输入转换数组，空值提交 `[]` |
| S4-24 | 重名提示 | 同名允许保存但必须提示 |
| S4-25 | 搜索 | 按 `name + aliases` 搜索，不改变原始顺序 |

### 6.7 结构化资产本地暂存

| ID | 任务 | 验收标准 |
|---|---|---|
| S4-26 | asset_draft 写入 | 编辑结构化资产时写入本地暂存 |
| S4-27 | 手动保存 | 仅用户点击保存或 Ctrl/Cmd+S 时提交 |
| S4-28 | 保存成功清理 | 200 后清理对应 `asset_draft` |
| S4-29 | 409 保留暂存 | 冲突未决策前不清理 |
| S4-30 | 离线策略 | 离线可编辑但联网后需手动保存 |
| S4-31 | LRU 优先级 | 结构化资产暂存优先淘汰，正文草稿优先保留 |

### 6.8 Ctrl/Cmd+S 行为矩阵

| 当前焦点 | 验收标准 |
|---|---|
| 正文 textarea | 立即 flush 当前章节标题与正文，并更新会话位置 |
| OutlinePanel | 保存当前激活 Outline 资源 |
| TimelinePanel | 保存当前 Timeline 编辑项或排序 |
| ForeshadowPanel | 保存当前 Foreshadow 编辑项 |
| CharacterPanel | 保存当前 Character 编辑项 |
| Header / ChapterSidebar / AssetRail | 不发起保存请求，显示当前无可保存编辑区 |

### 6.9 关键实现约束

- 结构化资产不进入正文自动回放队列，离线编辑仅写本地暂存。
- Drawer 打开、关闭、Tab 切换不得主动改变正文焦点。

### 6.10 联调节点

当 Stage 4 完成 60%~70% 时，进行 V1.1-B 前后端联调：

- AssetDrawer 四个面板接入真实 `/api/v1/*`。
- 验证显式保存、409 冲突、离线暂存。
- 验证删除章节后的结构化资产引用展示。

### 6.11 前端测试

必须覆盖：

- Drawer 同一时间只打开一个模块。
- Drawer 打开/关闭不抢正文焦点。
- dirty Tab 切换保存/放弃/取消分支。
- Outline 全书大纲与章节细纲切换。
- 切章时未保存章节细纲处理。
- Timeline 上移/下移提交完整映射。
- Foreshadow open/resolved 切换。
- Character aliases 转换、规范化结果展示、重名提示。
- 结构化资产离线编辑后不进入正文自动回放队列。
- 结构化资产 409 冲突保留本地暂存。

***

## 7. Stage 5：稳定性与验收

### 7.1 冲突处理

| ID | 任务 | 验收标准 |
|---|---|---|
| S5-01 | 正文冲突弹窗 | 提供本地版本 vs 服务端版本对比入口 |
| S5-02 | 结构化资产冲突弹窗 | 提供本地版本 vs 服务端版本对比入口 |
| S5-03 | 覆盖服务端 | 使用本地内容重新提交，成功后清理缓存 |
| S5-04 | 放弃本地 | 清理缓存并重新加载服务端内容 |
| S5-05 | 取消 | 保持本地编辑状态与缓存 |

### 7.2 离线与缓存

| ID | 任务 | 验收标准 |
|---|---|---|
| S5-06 | 离线提示 | 顶部提示离线模式 |
| S5-07 | 正文离线写作 | 输入写入本地草稿，网络恢复后自动回放 |
| S5-08 | 资产离线编辑 | 写入 asset_draft，不自动回放 |
| S5-09 | 缓存容量控制 | 10MB 软上限，LRU 淘汰 |
| S5-10 | 缓存淘汰提示 | 非当前编辑资产被清理时提示 |

### 7.3 删除与引用清理回归

| ID | 任务 | 验收标准 |
|---|---|---|
| S5-11 | 删除章节 | 焦点跳转相邻章节，编辑器不白屏 |
| S5-12 | 删除最后章节 | 编辑器进入不可输入空状态 |
| S5-13 | 删除章节清理细纲 | `chapter_outlines` 删除 |
| S5-14 | 删除章节置空引用 | timeline、foreshadow、大纲节点引用置空 |
| S5-15 | 删除作品 | 章节、会话、结构化资产全部删除 |

### 7.4 联调节点

当 Stage 5 完成 60%~70% 时，进行完整链路联调：

- A/B 批功能在同一作品中连续操作。
- 删除章节、冲突处理、离线恢复、导入导出同时回归。
- 验证 Workbench 与 Legacy 无交叉调用。

### 7.5 端到端验收

V1.1-A：

- 创建作品，自动创建第 1 章。
- 输入标题与正文，刷新不丢。
- 切章恢复光标与滚动。
- 搜索、跳转、新建章节、删除章节可用。
- TXT 导入与导出可用。
- 离线写作恢复后自动同步。

V1.1-B：

- 创建并保存全书大纲、章节细纲、时间线、伏笔、人物卡。
- 刷新后结构化资产数据仍在。
- 删除章节后所有引用处理符合设计。
- 结构化资产 409 冲突要求用户决策。
- Drawer 不抢正文焦点。

V1.1 非 AI 边界：

- 无 AI 按钮。
- 无自动生成入口。
- 无自动分析入口。
- 无自动抽取结构化资产行为。
- Workbench 不引用 Legacy Store/UI/API/Service。

***

## 8. Stage 6：V1.1-C 可选增强

### 8.1 任务清单

核心对象：

| 对象 | 职责 |
|---|---|
| `usePreferenceStore` | 本地偏好、专注模式、今日新增字数 |
| `FocusModeToggle` | 专注模式切换 |
| `WritingPreferencePanel` | 字体、字号、行距、主题偏好 |
| `ManualSyncButton` | 立即同步正文草稿 |

任务：

| ID | 任务 | 验收标准 |
|---|---|---|
| S6-01 | 专注模式 | 切换后不丢稿、不重置光标与滚动 |
| S6-02 | 字体偏好 | 字体、字号、行距本地持久化 |
| S6-03 | 主题偏好 | 主题本地持久化 |
| S6-04 | 今日新增字数 | 本地近似统计，不作为强一致数据来源 |
| S6-05 | 立即同步按钮 | 触发当前正文草稿 flush |

### 8.2 联调节点

当 Stage 6 完成 60%~70% 时，进行可选增强回归：

- 验证偏好只影响本地展示。
- 验证专注模式不影响 A/B 批保存与 Drawer。
- 验证立即同步不改变自动保存机制。

### 8.3 出口标准

- V1.1-C 不影响 V1.1-A/B 主链路。
- 偏好数据只存本地。
- 今日新增字数刷新后保持本地值。

***

## 9. 风险与控制

| 风险 | 影响 | 控制措施 |
|---|---|---|
| 复用 Legacy 语义 | Workbench 数据污染 | Stage 0 做隔离检查，代码评审禁止引用 Legacy |
| 切章等待网络保存 | 写作体验卡顿 | 切章前只要求写入本地草稿，网络保存异步继续 |
| 结构化资产进入自动回放 | 保存复杂度上升 | 资产只手动保存，离线只暂存 |
| Timeline 调序逐条提交 | 排序中间态污染 | 完整映射 + 单事务批量写入 |
| `content_tree_json` schema 分叉 | 清引用失败 | 字段白名单与 schema 测试 |
| aliases 搜索不稳定 | 人物搜索混乱 | 服务端规范化 aliases |
| 409 清理本地缓存 | 用户数据丢失 | 冲突未决策前禁止清理缓存 |

***

## 10. 开发顺序总览

```text
Stage 0 基线校准
  ↓
Stage 1 V1.1-A 后端收口
  ↓
Stage 2 V1.1-A 前端收口
  ↓
V1.1-A 提测
  ↓
Stage 3 V1.1-B 后端结构化资产
  ↓
Stage 4 V1.1-B 前端结构化资产
  ↓
Stage 5 稳定性与完整验收
  ↓
V1.1 完整提测
  ↓
Stage 6 V1.1-C 可选增强
```

联调顺序：

```text
Stage 1 60%~70%：A 批后端接口联调
Stage 2 60%~70%：A 批前后端主链路联调
Stage 3 60%~70%：B 批结构化资产后端联调
Stage 4 60%~70%：B 批前后端抽屉联调
Stage 5 60%~70%：完整链路回归联调
Stage 6 60%~70%：可选增强回归
```

***

## 11. 封版检查清单

- [ ] Workbench 与 Legacy 隔离通过。
- [ ] `/api/v1/*` API 清单全部可用。
- [ ] 正文 Local-First 保存链路通过。
- [ ] 切章、刷新、离线、409 不丢字。
- [ ] TXT 导入导出闭环通过。
- [ ] AssetDrawer 单抽屉、单 Tab 约束通过。
- [ ] Outline、Timeline、Foreshadow、Character 全部可 CRUD。
- [ ] 结构化资产显式保存与 409 冲突通过。
- [ ] 删除章节引用清理通过。
- [ ] textMetrics、aliases、content_tree_json schema 口径通过。
- [ ] Timeline 完整映射提交与单事务写入通过。
- [ ] 无 AI 入口、无自动生成、无自动分析、无自动抽取。
- [ ] V1.1-A/B DoD 全部通过。
