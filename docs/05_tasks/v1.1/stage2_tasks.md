# Stage 2 Tasks

### T2-01：前端 API 封装收口

目标：

* 建立 V1.1-A 前端访问 `/api/v1/*` 的统一 API 封装。

涉及模块：

* Frontend

实现内容：

* 新建或确认 `frontend/src/api/works.js`。
* 封装 Works、Chapters、Sessions、IO API 调用。
* 统一处理 `version_conflict` 409 响应。
* 统一使用 `snake_case` 字段与后端 DTO 对齐。
* 保留前端从 Mock 切换真实 API 的入口。

关键规则：

* API 前缀统一为 `/api/v1/*`。
* 409 冲突必须保留本地草稿。
* Workbench 前端禁止调用 Legacy API。

完成标准（DoD）：

* API 封装可被 Store 导入。
* 409 响应可被识别为冲突状态。
* 前端代码中无新增 Legacy API 调用。

### T2-02：useWorkspaceStore 收口

目标：

* 实现写作页作品上下文与会话恢复状态管理。

涉及模块：

* Frontend / Store

实现内容：

* 在 `useWorkspaceStore` 中维护当前 `work`。
* 维护当前 `session`。
* 提供初始化写作页动作。
* 调用 Sessions API 获取最后编辑章节、光标、滚动位置。
* 提供保存会话位置动作。

关键规则：

* 打开作品时必须恢复上次最后编辑章节。
* 无会话时默认第一章。
* 会话保存不触发正文保存。

完成标准（DoD）：

* Store 初始化后可获得 work 与 session。
* 无 session 时返回兜底状态。
* 保存会话位置不调用章节保存 API。

### T2-03：useChapterDataStore 收口

目标：

* 实现章节列表、激活章节、标题草稿与正文草稿的前端状态管理。

涉及模块：

* Frontend / Store

实现内容：

* 维护 `chapters` 列表。
* 维护 `activeChapterId`。
* 维护 `draftByChapterId` 与 `titleDraftByChapterId`。
* 实现章节列表加载与激活章节设置。
* 实现章节新增、删除后的本地状态更新。

关键规则：

* 章节编号由 `order_index` 动态计算。
* 搜索不得改变章节原数组顺序。
* 新建章节默认追加末尾并激活。

完成标准（DoD）：

* 章节列表按 `order_index ASC` 展示。
* 激活章节切换状态正确。
* 新建章节后搜索状态可被清空并定位新章节。

### T2-04：useSaveStateStore Local-First 收口

目标：

* 实现正文 Local-First 保存状态机与远端同步基础链路。

涉及模块：

* Frontend / Store

实现内容：

* 维护 `saveStatus`、`pendingQueue`、`conflictPayload`。
* 输入后立即写入本地草稿。
* debounce 后调用章节保存 API。
* 保存成功后清理对应草稿。
* 409 时保留草稿并进入冲突状态。
* 网络恢复后按 timestamp 串行回放。

关键规则：

* 切章前只要求写入本地草稿，不等待网络保存成功。
* 409 未决策前不得清理本地草稿。
* 回放时同章节只保留最新 timestamp。

完成标准（DoD）：

* 输入后本地草稿立即存在。
* 保存成功后对应草稿被清理。
* 409 后草稿仍存在且冲突状态可见。

### T2-05：WorksList 页面收口

目标：

* 实现 V1.1 书架页入口，承载作品创建、打开、导入与导出入口。

涉及模块：

* Frontend

实现内容：

* 实现 `frontend/src/views/works/WorksList.vue`。
* 展示作品卡片列表。
* 提供新建作品入口。
* 提供 TXT 导入入口。
* 提供作品操作入口：重命名、改作者、删除、导出。

关键规则：

* 书架页只负责作品入口和作品级操作。
* 不新增主页面。
* 不出现 AI 入口。

完成标准（DoD）：

* `/works` 页面可访问。
* 可打开作品进入 `/works/:id`。
* 页面无 Legacy 组件与 AI 入口。

### T2-06：WritingStudio 页面布局收口

目标：

* 实现写作页三栏布局与核心区域挂载。

涉及模块：

* Frontend

实现内容：

* 实现 `frontend/src/views/works/WritingStudio.vue`。
* 挂载 Header、ChapterSidebar、Editor、AssetRail、AssetDrawer 占位。
* 初始化作品、章节、会话。
* 页面打开后恢复激活章节、光标、滚动位置。
* 页面打开后正文 textarea 获得默认焦点。

关键规则：

* `/works/:id` 是写作工作台唯一页面。
* 正文区优先，任何 UI 不得干扰输入。
* Drawer 打开/关闭不得主动改变正文焦点。

完成标准（DoD）：

* `/works/:id` 页面可访问。
* 页面初始化不报错。
* 默认焦点落在正文 textarea。

### T2-07：Header 与作品重命名收口

目标：

* 实现写作页 Header 的作品信息展示与重命名交互。

涉及模块：

* Frontend

实现内容：

* Header 显示作品名与轻量状态。
* 长作品名单行截断。
* 点击作品名进入编辑态。
* Enter 提交重命名，Esc 放弃。
* 提交失败时恢复原展示值。

关键规则：

* Header 不显示作品 UUID。
* 重命名失败不得污染本地展示状态。
* Header 不抢正文输入焦点。

完成标准（DoD）：

* Header 可展示作品名。
* 重命名成功后作品名更新。
* Esc 放弃后原作品名保持不变。

### T2-08：ChapterSidebar 收口

目标：

* 实现章节列表、搜索、跳转、第 N 章定位、新建与删除入口。

涉及模块：

* Frontend

实现内容：

* 实现 `ChapterSidebar`。
* 展示章节编号与用户标题。
* 实现章节搜索，仅过滤展示。
* 实现跳转第 N 章输入。
* 实现新建章节入口。
* 激活章节变化后执行 `scrollIntoView`。

关键规则：

* 搜索不改变 `order_index`。
* 新建章节默认追加末尾。
* 激活项必须高亮并滚动到可见区。

完成标准（DoD）：

* 搜索结果按原顺序展示。
* 跳转非法输入有轻量提示。
* 新建章节后激活新章并正文聚焦。

### T2-09：ChapterTitleInput 收口

目标：

* 实现章节标题展示与输入，避免标题前缀污染存储。

涉及模块：

* Frontend

实现内容：

* 实现 `ChapterTitleInput`。
* 展示 `第{order_index}章 + title`。
* `title` 为空时只展示 `第{order_index}章`。
* 保存时只提交用户输入标题。
* 用户输入含“第X章”前缀时前端清理后提交。

关键规则：

* `title` 禁止写入“第X章”前缀。
* 空标题保存空字符串。
* 标题与正文同次 flush 保存。

完成标准（DoD）：

* 展示不出现“第1章 第1章”。
* 保存请求不包含章节编号前缀。
* 空标题可保存为空字符串。

### T2-10：PureTextEditor 收口

目标：

* 实现纯文本正文编辑器，支撑 Local-First 输入与会话位置上报。

涉及模块：

* Frontend

实现内容：

* 实现 `PureTextEditor`。
* 使用纯文本 textarea。
* 输入时更新正文草稿并触发 Local-First 写入。
* 上报 `cursorPosition` 与 `scrollTop`。
* 粘贴时仅读取 `text/plain`。
* 支持 Ctrl/Cmd+S 触发当前正文立即 flush。

关键规则：

* V1.1 仅支持纯文本。
* 正文输入不得被保存失败或离线打断。
* Ctrl/Cmd+S 只保存当前聚焦编辑区。

完成标准（DoD）：

* 输入内容立即进入本地草稿。
* 粘贴富文本后仅保留纯文本。
* Ctrl/Cmd+S 不触发浏览器默认保存。

### T2-11：StatusBar 与保存状态提示

目标：

* 实现正文底部状态条，展示保存、离线、冲突与字数信息。

涉及模块：

* Frontend

实现内容：

* 实现 `StatusBar`。
* 展示 `saving`、`synced`、`offline`、`conflict`、`error` 状态。
* 展示当前正文有效字数。
* 保存失败时显示轻量提示。
* 离线时显示“离线模式，本地已暂存”。

关键规则：

* 保存失败禁止使用阻断式全屏弹窗。
* 离线时写作主链路不能断。
* 字数口径使用 textMetrics。

完成标准（DoD）：

* 各状态 UI 可切换展示。
* 离线状态不阻断输入。
* 字数统计与 textMetrics 一致。

### T2-12：正文 409 冲突弹窗

目标：

* 实现正文版本冲突处理入口，保证冲突时本地草稿不丢失。

涉及模块：

* Frontend

实现内容：

* 实现 `VersionConflictModal`。
* 展示本地版本与服务端版本。
* 提供本地 vs 服务端对比入口。
* 提供覆盖服务端、放弃本地、取消操作。
* 决策前保留本地草稿。

关键规则：

* 409 冲突未处理前不得清理本地缓存。
* 覆盖服务端使用本地内容重新提交。
* 放弃本地时重新加载服务端内容。

完成标准（DoD）：

* 409 后弹窗可打开。
* 点击取消后本地草稿仍存在。
* 覆盖/放弃路径行为可验证。

### T2-13：TXT 导入 UI 收口

目标：

* 实现 Web TXT 导入入口与导入结果跳转。

涉及模块：

* Frontend

实现内容：

* 实现 `ImportTxtModal`。
* 支持选择 `.txt` 文件。
* 调用 `POST /api/v1/io/import`。
* 展示编码失败、文件超限等错误提示。
* 导入成功后跳转 `/works/:id`。

关键规则：

* TXT 导入无章节标记时由后端单章兜底。
* 导入后章节顺序按 `order_index` 展示。
* 导入失败提示不得阻断现有写作页输入。

完成标准（DoD）：

* 可上传 TXT。
* 成功后进入写作页。
* 错误提示明确可见。

### T2-14：TXT 导出 UI 收口

目标：

* 实现作品 TXT 导出入口与格式选项。

涉及模块：

* Frontend

实现内容：

* 实现 `ExportTxtModal` 或等价导出入口。
* 支持 `include_titles` 选项。
* 支持 `gap_lines=0|1|2` 选项。
* 调用 `GET /api/v1/io/export/{work_id}`。
* 触发浏览器下载 `.txt` 文件。

关键规则：

* 必须允许用户随时导出 `.txt`。
* 导出不修改作品数据。
* 导出按后端 `order_index ASC` 结果输出。

完成标准（DoD）：

* 可从作品操作入口导出 TXT。
* 导出选项生效。
* 下载文件名符合后端响应。

### T2-15：切章流程与会话保存

目标：

* 实现切章时的 Local-First 保护、会话保存与编辑位置恢复。

涉及模块：

* Frontend / Store

实现内容：

* 点击章节前写入当前章节本地草稿。
* 网络保存异步继续，不阻断切章。
* 切换 `activeChapterId`。
* 加载目标章节正文草稿或远端内容。
* 保存会话 `last_open_chapter_id`、`cursorPosition`、`scrollTop`。
* nextTick 后恢复光标与滚动。

关键规则：

* 切章前必须将当前编辑内容写入本地草稿。
* 网络保存允许异步完成。
* 打开作品必须恢复上次最后编辑位置。

完成标准（DoD）：

* 切章不等待网络保存成功。
* 刷新后恢复最后章节与编辑位置。
* 保存失败但本地草稿存在时允许切章。

### T2-16：Stage 2 前端测试套件

目标：

* 建立 V1.1-A 前端回归测试，覆盖写作主链路。

涉及模块：

* Frontend / Store

实现内容：

* 增加 Store 测试：workspace、chapterData、saveState。
* 增加 Local cache 测试。
* 增加 ChapterSidebar 交互测试。
* 增加 ChapterTitleInput 前缀清理测试。
* 增加 PureTextEditor 输入与 Ctrl/Cmd+S 测试。
* 增加 409 冲突弹窗测试。

关键规则：

* 输入正文后刷新不丢字。
* 搜索不改变章节顺序。
* 409 冲突不清理本地缓存。

完成标准（DoD）：

* Stage 2 前端测试全部通过。
* 核心 Store action 行为可验证。
* 关键组件交互测试通过。

### T2-17：Stage 2 联调验证

目标：

* 完成 V1.1-A 前后端联调，确认可进入 V1.1-A 提测。

涉及模块：

* Frontend / Backend / Store

实现内容：

* 前端从 Mock 切换到真实 `/api/v1/*`。
* 验证创建作品、打开写作页、保存标题正文。
* 验证会话恢复、切章、删除章节、新建章节。
* 验证 TXT 导入导出。
* 验证 409 冲突与离线本地草稿。
* 记录 V1.1-A 提测结果。

关键规则：

* Workbench 不出现 AI 入口。
* 正文 Local-First 链路必须通过。
* 切章、刷新、离线、409 不丢字。

完成标准（DoD）：

* V1.1-A 端到端流程通过。
* 前后端接口字段对齐。
* 可进入 Stage 3 后端结构化资产开发。
