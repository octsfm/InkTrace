# Stage 1 Tasks

### T1-01：基础表迁移收口

目标：

* 完成 V1.1-A 后端所需 `works`、`chapters`、`edit_sessions` 基础表迁移。

涉及模块：

* Backend / DB

实现内容：

* 在 `infrastructure/database/v1/models.py` 定义 `works`、`chapters`、`edit_sessions` 表模型。
* 在迁移入口中使用 `CREATE TABLE IF NOT EXISTS` 创建基础表。
* 为 `chapters` 添加 `order_index`、`version`、`word_count` 字段。
* 为 `edit_sessions` 添加 `last_open_chapter_id`、`cursor_position`、`scroll_top` 字段。
* 为 `chapters.work_id`、`edit_sessions.work_id` 建立外键关系。
* 确认迁移重复执行不破坏已有数据。

关键规则：

* `id` 统一为 UUID 字符串。
* `version` 统一为整数类型，默认值为 `1`。
* 时间字段统一使用 ISO 8601 字符串且时区口径一致。

完成标准（DoD）：

* 数据库初始化后存在 `works`、`chapters`、`edit_sessions`。
* `chapters.version` 默认值为 `1`。
* 重复执行迁移无异常且不清空已有数据。

### T1-02：Domain 实体与 Repository 接口收口

目标：

* 建立 V1.1-A 后端核心实体与 Repository 边界。

涉及模块：

* Backend / DB

实现内容：

* 定义或收口 `domain/entities/work.py`。
* 定义或收口 `domain/entities/chapter.py`，包含 `order_index`、`version`、`word_count`。
* 定义或收口 `domain/entities/edit_session.py`。
* 定义或收口 `WorkRepository`、`ChapterRepository`、`EditSessionRepository` 接口。
* Repository 接口只表达数据访问能力，不包含业务编排。

关键规则：

* Domain 层实体禁止依赖 FastAPI、SQLite、HTTP DTO、前端字段名。
* `order_index` 是章节排序唯一依据。
* `version` 为资源级自增版本号，每条记录独立维护。

完成标准（DoD）：

* 三个实体可被 Service 层导入。
* 三个 Repository 接口职责清晰。
* Domain 层不引用 FastAPI、SQLAlchemy Session、HTTP Request。

### T1-03：WorkRepo 实现

目标：

* 实现作品数据访问能力，为 WorkService 提供基础读写。

涉及模块：

* Backend / DB

实现内容：

* 在 `infrastructure/database/v1/repositories/` 实现 WorkRepo。
* 支持作品列表查询。
* 支持按 `work_id` 查询作品。
* 支持创建、更新作品标题与作者。
* 支持删除作品。
* 删除作品操作预留事务入口，由 Service 层编排级联行为。

关键规则：

* Repository 只负责数据库读写，不包含业务编排。
* Workbench 数据不得反向写入 Legacy。
* 时间字段更新必须保持 ISO 8601 口径。

完成标准（DoD）：

* WorkRepo CRUD 单元测试通过。
* 查询不存在作品返回空结果或明确 not_found。
* WorkRepo 不依赖 Legacy Repository。

### T1-04：ChapterRepo 实现

目标：

* 实现章节数据访问能力，为章节保存、删除、调序提供基础。

涉及模块：

* Backend / DB

实现内容：

* 在 `infrastructure/database/v1/repositories/` 实现 ChapterRepo。
* 支持按 `work_id` 查询章节列表。
* 支持按 `chapter_id` 查询章节。
* 支持保存章节 `title`、`content`、`word_count`、`version`。
* 支持删除章节。
* 支持批量更新 `order_index` 与重排 `1..N`。

关键规则：

* `list_by_work` 必须按 `order_index ASC` 返回。
* `reorder` 必须在调用方传入的同一事务内批量执行，不得逐条独立 `commit`。
* `title` 后端统一存储空字符串，不使用 `NULL`。

完成标准（DoD）：

* 章节列表按 `order_index ASC` 返回。
* 批量调序测试通过。
* 删除后重排 `order_index` 测试通过。

### T1-05：EditSessionRepo 实现

目标：

* 实现写作会话读取与保存，为打开作品恢复编辑位置提供基础。

涉及模块：

* Backend / DB

实现内容：

* 在 `infrastructure/database/v1/repositories/` 实现 EditSessionRepo。
* 支持按 `work_id` 查询会话。
* 支持会话 upsert。
* 保存 `last_open_chapter_id`、`cursor_position`、`scroll_top`。
* 支持作品删除时会话随作品删除或由 Service 编排清理。

关键规则：

* 会话只保存编辑位置，不触发正文保存。
* 无会话记录时由 Service 层返回兜底会话。
* `cursor_position` 与 `scroll_top` 无记录时按 `0` 处理。

完成标准（DoD）：

* 会话 upsert 测试通过。
* 查询不存在会话时行为确定。
* 保存会话不修改章节正文或标题。

### T1-06：textMetrics 后端接入

目标：

* 将 Stage 0 textMetrics 工具接入章节保存链路，统一服务端字数口径。

涉及模块：

* Backend

实现内容：

* 在后端工具模块中确认 textMetrics 函数可被 Service 层调用。
* 在章节保存前根据 `content` 计算 `word_count`。
* 确认标题不参与 `word_count`。
* 增加中文、英文、空白、换行、制表符混合内容测试。

关键规则：

* `word_count` 必须采用同一套 textMetrics 口径。
* textMetrics 口径为去除空格、换行符、制表符等不可见空白字符后统计剩余字符数。
* 前端实时展示值与后端持久化值必须使用同一统计口径。

完成标准（DoD）：

* 后端 textMetrics 单元测试通过。
* Chapter 保存后 `word_count` 与 textMetrics 结果一致。
* 修改标题不影响 `word_count`。

### T1-07：WorkService 实现

目标：

* 实现作品级业务编排，完成作品创建、更新、删除基础能力。

涉及模块：

* Backend

实现内容：

* 在 `application/services/v1/work_service.py` 实现 WorkService。
* 实现作品列表查询。
* 实现创建作品，并在同一事务内创建首章。
* 实现作品标题与作者更新。
* 实现删除作品，并清理章节与会话。
* 删除结构化资产的接口位点仅预留，不实现 V1.1-B 业务。

关键规则：

* 创建作品必须在同一事务内创建首章。
* 新建作品首章 `title=""`、`content=""`、`order_index=1`、`version=1`。
* Stage 1 不实现 Outline、Timeline、Foreshadow、Character 业务。

完成标准（DoD）：

* 创建作品后自动存在 1 个空章节。
* 删除作品后对应章节与会话被清理。
* WorkService 不调用 Legacy Service。

### T1-08：ChapterService 保存与乐观锁

目标：

* 实现章节标题与正文同链路保存，并完成乐观锁冲突处理。

涉及模块：

* Backend

实现内容：

* 在 `application/services/v1/chapter_service.py` 实现章节保存。
* 保存请求同次处理 `title` 与 `content`。
* `title=None` 时不更新标题，`title=""` 时保存空字符串。
* 保存时根据提交后的 `content` 重算 `word_count`。
* 校验 `expected_version` 与当前 `version`。
* 冲突时返回 `version_conflict` 409 模板。

关键规则：

* 标题与正文共用同一套保存机制。
* 禁止将“第X章”前缀写入 `chapters.title`。
* 409 时必须返回 `detail`、`server_version`、`resource_type`、`resource_id`。

完成标准（DoD）：

* 正文保存成功后 `version+1`。
* `expected_version` 不匹配时返回 409。
* 保存请求同时携带标题与正文时两者一致落库。

### T1-09：ChapterService 新建、删除与焦点建议

目标：

* 实现章节新建、删除与删除后的建议激活章节计算。

涉及模块：

* Backend / DB

实现内容：

* 实现 `create_chapter(work_id)`。
* 新章节默认追加末尾，`order_index=max+1`。
* 实现 `delete_chapter(chapter_id)`。
* 删除章节后重排剩余章节 `order_index` 为 `1..N`。
* 返回建议激活章节 ID，优先下一章，无下一章则上一章。
* 删除最后章节时返回空激活章节结果。

关键规则：

* 新建章节默认追加到全书末尾。
* 删除当前编辑章节后编辑器禁止白屏或报错。
* 删除章节后必须重排 `order_index`。

完成标准（DoD）：

* 新建章节 `order_index` 正确。
* 删除中间章节后返回下一章 ID。
* 删除最后章节后返回上一章 ID 或空状态结果。

### T1-10：ChapterService 调序原子化

目标：

* 实现章节批量调序，确保排序操作无中间污染态。

涉及模块：

* Backend / DB

实现内容：

* 实现 `reorder_chapters(work_id, mappings)`。
* 校验 `items` 数量等于当前作品下章节数量。
* 校验章节 ID 无缺失、无重复、无多余。
* 校验 `order_index` 连续为 `1..N`。
* 使用单事务批量写入全部受影响章节。

关键规则：

* 调序接口必须一次性提交完整映射列表。
* 禁止前端逐条提交。
* 禁止后端逐条独立 `commit`。

完成标准（DoD）：

* 合法完整映射调序成功。
* 缺失、重复、多余章节映射返回 `invalid_input`。
* 任一写入失败时事务回滚。

### T1-11：SessionService 实现

目标：

* 实现打开作品时的会话恢复与编辑位置保存。

涉及模块：

* Backend

实现内容：

* 在 `application/services/v1/session_service.py` 实现 `get_session(work_id)`。
* 在无会话记录时返回兜底会话。
* 兜底会话优先指向第一章。
* 实现 `save_session(work_id, last_open_chapter_id, cursor_position, scroll_top)`。
* 保存会话时不触发正文保存。

关键规则：

* 打开作品时默认定位并打开上次最后编辑的章节。
* 若全新作品或记录丢失，默认打开第一章。
* 恢复会话必须包含 `cursor_position` 与 `scrollTop`。

完成标准（DoD）：

* 无会话时返回第一章与位置 0。
* 保存后再次读取能恢复章节、光标与滚动位置。
* 作品无章节时返回空章节兜底，不抛异常。

### T1-12：IOService TXT 导入

目标：

* 实现 Web TXT 导入服务，确保导入成功率与章节排序口径稳定。

涉及模块：

* Backend / DB

实现内容：

* 在 `application/services/v1/io_service.py` 实现 TXT 导入。
* 限制文件大小上限 20MB。
* 编码识别顺序为 `utf-8-sig -> utf-8 -> gb18030`。
* 解析章节标记并按物理顺序生成章节。
* 无章节标记时将全文作为单章导入。
* 空文件导入为单章空内容。

关键规则：

* TXT 导入必须有兜底，不因无法识别章节标记而失败。
* 导入后 `order_index` 必须连续 `1..N`。
* 导入后不信任原文自带编号作为真实排序依据。

完成标准（DoD）：

* 空文件导入成功。
* 无章节标记文件导入为单章。
* 多章节文件导入后章节顺序连续正确。

### T1-13：IOService TXT 导出

目标：

* 实现作品 TXT 导出服务，完成用户带走数据的后端闭环。

涉及模块：

* Backend

实现内容：

* 在 `application/services/v1/io_service.py` 实现 TXT 导出。
* 按 `order_index ASC` 读取章节。
* 支持 `include_titles` 选项。
* 支持 `gap_lines=0|1|2`。
* 生成文件名 `{作品名}-{YYYYMMDD}.txt`。
* 空作品导出 0 字节 UTF-8 无 BOM 内容。

关键规则：

* 必须允许用户随时导出 `.txt`。
* 导出顺序必须以 `order_index ASC` 为准。
* 导出不写入或修改作品数据。

完成标准（DoD）：

* 导出内容按章节顺序输出。
* `include_titles` 与 `gap_lines` 生效。
* 空作品导出行为确定。

### T1-14：V1.1-A DTO 与 Schema 收口

目标：

* 统一 Stage 1 API 请求与响应结构，减少前后端对接分歧。

涉及模块：

* Backend

实现内容：

* 在 `presentation/api/routers/v1/schemas.py` 定义 Works 请求/响应 DTO。
* 定义 Chapters 请求/响应 DTO。
* 定义 Sessions 请求/响应 DTO。
* 定义 IO 导入导出响应结构。
* 定义 409 冲突响应模板。
* 确认所有字段使用 `snake_case`。

关键规则：

* 所有错误响应字段必须使用 `snake_case` 命名，字段名全局不可变更。
* 409 响应包含 `detail`、`server_version`、`resource_type`、`resource_id`。
* API 前缀统一为 `/api/v1/*`。

完成标准（DoD）：

* Schema 可被 Router 复用。
* DTO 字段与详细设计一致。
* Schema 校验失败返回 `invalid_input`。

### T1-15：WorksRouter 实现

目标：

* 暴露作品级 V1.1 API，供书架与写作页初始化使用。

涉及模块：

* Backend

实现内容：

* 在 `presentation/api/routers/v1/works.py` 实现 WorksRouter。
* 实现作品列表接口。
* 实现创建作品接口。
* 实现作品详情接口。
* 实现作品更新接口。
* 实现作品删除接口。

关键规则：

* Router 只做请求校验、调用 Service、返回 DTO。
* 作品创建必须通过 WorkService 同事务创建首章。
* Workbench API 统一挂载 `/api/v1/*`。

完成标准（DoD）：

* Works API 集成测试通过。
* 创建作品返回作品基础信息。
* 删除作品后再次查询返回 `work_not_found`。

### T1-16：ChaptersRouter 实现

目标：

* 暴露章节级 V1.1 API，支持章节列表、新建、保存、删除与调序。

涉及模块：

* Backend

实现内容：

* 在 `presentation/api/routers/v1/chapters.py` 实现 ChaptersRouter。
* 实现 `GET /api/v1/works/{work_id}/chapters`。
* 实现 `POST /api/v1/works/{work_id}/chapters`。
* 实现 `PUT /api/v1/chapters/{chapter_id}`。
* 实现 `DELETE /api/v1/chapters/{chapter_id}`。
* 实现 `PUT /api/v1/works/{work_id}/chapters/reorder`。

关键规则：

* `PUT /chapters/{chapter_id}` 必须同时支持 `title`、`content`、`expected_version`。
* 章节调序必须完整映射提交。
* 版本冲突必须返回 `version_conflict` 409。

完成标准（DoD）：

* 章节 API 集成测试通过。
* 保存接口成功时返回新 `version`。
* 调序接口对非法映射返回 `invalid_input`。

### T1-17：SessionsRouter 实现

目标：

* 暴露会话恢复 API，支持写作页恢复最后编辑章节、光标与滚动位置。

涉及模块：

* Backend

实现内容：

* 在 `presentation/api/routers/v1/sessions.py` 实现 SessionsRouter。
* 实现 `GET /api/v1/works/{work_id}/session`。
* 实现 `PUT /api/v1/works/{work_id}/session`。
* GET 无会话时通过 SessionService 返回兜底会话。
* PUT 仅保存会话位置，不保存正文。

关键规则：

* 会话恢复不等于正文保存。
* 无会话时默认第一章。
* 光标与滚动位置必须可恢复。

完成标准（DoD）：

* Sessions API 集成测试通过。
* 无会话作品 GET 不报错。
* PUT 后再次 GET 返回更新后位置。

### T1-18：IORouter 实现

目标：

* 暴露 TXT 导入导出 API，完成 V1.1-A 数据带入带出能力。

涉及模块：

* Backend

实现内容：

* 在 `presentation/api/routers/v1/io.py` 实现 IORouter。
* 实现 `POST /api/v1/io/import`，接收 `multipart/form-data`。
* 实现 `GET /api/v1/io/export/{work_id}`。
* 导入支持可选 `title` 与 `author`。
* 导出支持 `include_titles` 与 `gap_lines`。

关键规则：

* 导入失败场景必须返回明确错误码。
* 无章节标记必须单章兜底导入。
* 导出不修改任何作品数据。

完成标准（DoD）：

* IO API 集成测试通过。
* 上传 TXT 后返回作品与章节结果。
* 导出接口返回 `.txt` 内容与文件名。

### T1-19：Stage 1 后端测试套件

目标：

* 建立 V1.1-A 后端回归测试，确保 Stage 1 可进入前端联调。

涉及模块：

* Backend / DB

实现内容：

* 增加 WorkService 与 WorksRouter 测试。
* 增加 ChapterService 与 ChaptersRouter 测试。
* 增加 SessionService 与 SessionsRouter 测试。
* 增加 IOService 与 IORouter 测试。
* 增加错误码与 409 响应模板测试。
* 增加数据库迁移与 Repository 基础测试。

关键规则：

* 每个 Service 必须覆盖正常路径、边界路径、异常路径。
* 409 冲突不得清理或覆盖本地数据的责任由前端承担，但后端必须返回完整模板。
* 调序与删除相关测试必须验证事务结果。

完成标准（DoD）：

* Stage 1 后端测试全部通过。
* 关键 API 均有集成测试覆盖。
* 测试数据不污染开发数据库。

### T1-20：Stage 1 联调验证

目标：

* 对 V1.1-A 后端进行阶段验收，确认可进入 Stage 2 前端收口。

涉及模块：

* Backend / DB

实现内容：

* 启动后端服务并确认 `/api/v1/health` 可用。
* 使用真实 API 验证 Works/Chapters/Sessions/IO 全链路。
* 验证保存接口可触发 409。
* 验证 TXT 导入导出闭环。
* 验证删除章节后 `order_index` 连续与建议激活章节正确。
* 生成 Stage 1 验收结果记录。

关键规则：

* Stage 1 不实现前端 Local-First 保存链路。
* Stage 1 不实现结构化资产业务。
* API 返回结构必须能支持 Stage 2 前端对接。

完成标准（DoD）：

* Works/Chapters/Sessions/IO API 全部可用。
* Stage 1 测试全部通过。
* 前端可基于 `/api/v1/*` 真实接口替换 Mock。
* 可进入 Stage 2 前端收口。
