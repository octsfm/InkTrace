# Stage 3 Tasks

### T3-01：结构化资产表迁移

目标：

* 完成 V1.1-B 后端结构化资产基础表迁移。

涉及模块：

* Backend / DB

实现内容：

* 在 `infrastructure/database/v1/models.py` 增加 `work_outlines`。
* 增加 `chapter_outlines`。
* 增加 `timeline_events`。
* 增加 `foreshadows`。
* 增加 `characters`。
* 迁移入口使用 `CREATE TABLE IF NOT EXISTS`。

关键规则：

* 结构化资产完全非 AI。
* 新增结构化资产表不读取、不写入 Legacy 表。
* 所有 `version` 默认值为 `1`。

完成标准（DoD）：

* 五类结构化资产表可重复迁移。
* 表字段与详细设计一致。
* 迁移不破坏 Stage 1 数据。

### T3-02：content_tree_json schema 校验工具

目标：

* 建立大纲树派生缓存的 schema 校验能力。

涉及模块：

* Backend

实现内容：

* 新增 `content_tree_json` 节点校验工具。
* 校验字段白名单：`node_id`、`text`、`children`、`chapter_ref`、`collapsed`。
* 校验 `children` 为数组。
* 校验 `chapter_ref` 可为空。
* 拒绝 AI 语义字段、分析字段、生成来源字段。

关键规则：

* `content_text` 为唯一真实存储。
* `content_tree_json` 为派生视图缓存。
* `content_tree_json` 仅在用户显式保存 outline 时更新。

完成标准（DoD）：

* 合法树结构校验通过。
* 非白名单字段校验失败。
* schema 测试覆盖空树、嵌套树、非法字段。

### T3-03：结构化资产 Repository 接口

目标：

* 建立 V1.1-B 结构化资产 Repository 接口边界。

涉及模块：

* Backend / DB

实现内容：

* 定义 WorkOutlineRepository 接口。
* 定义 ChapterOutlineRepository 接口。
* 定义 TimelineEventRepository 接口。
* 定义 ForeshadowRepository 接口。
* 定义 CharacterRepository 接口。
* 接口只表达数据访问，不包含业务编排。

关键规则：

* Repository 不复用 Legacy 业务语义 Repository。
* Repository 只负责数据库读写。
* Workbench 数据不得写入 Legacy。

完成标准（DoD）：

* 接口可被 WritingAssetService 导入。
* 接口职责清晰且无业务编排。
* 无 Legacy Repository 依赖。

### T3-04：Outline Repository 实现

目标：

* 实现全书大纲与章节细纲的数据访问能力。

涉及模块：

* Backend / DB

实现内容：

* 实现 WorkOutlineRepo 读取与保存。
* 实现 ChapterOutlineRepo 读取与保存。
* 支持按章节删除 chapter outline。
* 支持清理 work outline 中的章节引用。
* 保存时维护 `version` 与 `updated_at`。

关键规则：

* `content_text` 为唯一真实存储。
* 删除章节时仅置空全书大纲节点章节引用。
* 删除章节时章节细纲整条记录随章节删除。

完成标准（DoD）：

* Work outline CRUD 测试通过。
* Chapter outline CRUD 测试通过。
* 清理章节引用测试通过。

### T3-05：Timeline Repository 实现

目标：

* 实现时间线事件 CRUD 与排序数据访问能力。

涉及模块：

* Backend / DB

实现内容：

* 实现 TimelineEventRepo 列表查询。
* 实现创建、更新、删除事件。
* 实现按 `work_id` 查询并按 `order_index ASC` 返回。
* 实现批量调序写入。
* 实现删除章节时置空 `chapter_id`。

关键规则：

* `order_index` 是时间线事件排序唯一依据。
* 调序必须单事务批量更新。
* 删除章节时相关事件 `chapter_id` 置空。

完成标准（DoD）：

* Timeline CRUD 测试通过。
* 列表顺序按 `order_index ASC`。
* 批量调序不逐条独立提交。

### T3-06：Foreshadow Repository 实现

目标：

* 实现伏笔 CRUD、状态筛选与章节引用清理。

涉及模块：

* Backend / DB

实现内容：

* 实现 ForeshadowRepo 列表查询。
* 支持按 `status` 筛选。
* 实现创建、更新、删除伏笔。
* 实现删除章节时置空 `introduced_chapter_id`。
* 实现删除章节时置空 `resolved_chapter_id`。

关键规则：

* `status` 只允许 `open` 或 `resolved`。
* 章节引用可为空。
* 删除章节时伏笔记录保留。

完成标准（DoD）：

* 伏笔 CRUD 测试通过。
* `open/resolved` 筛选测试通过。
* 删除章节后引用置空测试通过。

### T3-07：Character Repository 实现

目标：

* 实现人物卡 CRUD、aliases 存储与搜索能力。

涉及模块：

* Backend / DB

实现内容：

* 实现 CharacterRepo 列表查询。
* 实现创建、更新、删除人物卡。
* `aliases_json` 存储 JSON array 字符串。
* 搜索匹配 `name` 与 `aliases_json`。
* 搜索大小写不敏感。

关键规则：

* `name` 必填。
* 前端传 `null` 或空数组时后端统一存储为 `[]`。
* aliases 存储前必须 trim、去空、去重并保持首次出现顺序。

完成标准（DoD）：

* 人物 CRUD 测试通过。
* aliases 规范化测试通过。
* name 与 aliases 搜索测试通过。

### T3-08：WritingAssetService Outline 实现

目标：

* 实现全书大纲与章节细纲的业务保存逻辑。

涉及模块：

* Backend

实现内容：

* 实现 `get_work_outline`。
* 实现 `save_work_outline`。
* 实现 `get_chapter_outline`。
* 实现 `save_chapter_outline`。
* 保存时校验 `expected_version`。
* 保存时校验 `content_tree_json` schema。

关键规则：

* Outline 显式保存。
* `expected_version` 不匹配返回 `asset_version_conflict`。
* `content_tree_json` 不做自动同步或后台同步。

完成标准（DoD）：

* Outline 保存成功后 `version+1`。
* 版本不匹配返回 409。
* 非法 tree schema 返回 `invalid_input`。

### T3-09：WritingAssetService Timeline 实现

目标：

* 实现时间线事件业务逻辑与完整映射调序。

涉及模块：

* Backend

实现内容：

* 实现 timeline 列表查询。
* 实现创建、更新、删除事件。
* 新事件追加末尾。
* 实现 reorder 完整映射校验。
* 调序使用单事务批量写入。

关键规则：

* Timeline 调序必须一次性提交完整映射列表。
* `items` 数量必须等于当前作品下事件数量。
* 禁止逐条独立 commit。

完成标准（DoD）：

* Timeline CRUD Service 测试通过。
* 缺失、重复、多余映射返回 `invalid_input`。
* 调序成功后顺序连续。

### T3-10：WritingAssetService Foreshadow 实现

目标：

* 实现伏笔业务逻辑与状态切换。

涉及模块：

* Backend

实现内容：

* 实现伏笔列表查询。
* 默认支持 `status=open` 查询。
* 实现创建、更新、删除伏笔。
* 支持 `open/resolved` 状态切换。
* 校验章节引用可为空。

关键规则：

* `status` 仅允许 `open/resolved`。
* 删除章节时引用置空，伏笔保留。
* 更新接口携带 `expected_version`。

完成标准（DoD）：

* open 默认列表测试通过。
* 状态切换测试通过。
* 版本冲突返回 `asset_version_conflict`。

### T3-11：WritingAssetService Character 实现

目标：

* 实现人物卡业务逻辑、aliases 规范化与搜索。

涉及模块：

* Backend

实现内容：

* 实现人物列表查询。
* 实现创建、更新、删除人物卡。
* 保存前规范化 aliases。
* 支持 keyword 搜索。
* 更新接口携带 `expected_version`。

关键规则：

* 重名允许，由前端提示。
* aliases_json 必须为 JSON array 字符串。
* 搜索按 name 与 aliases 匹配。

完成标准（DoD）：

* 人物卡 Service 测试通过。
* aliases 规范化结果稳定。
* 版本冲突返回 409 模板。

### T3-12：ChapterService 删除引用清理扩展

目标：

* 扩展删除章节事务，清理结构化资产中的章节引用。

涉及模块：

* Backend / DB

实现内容：

* 删除章节时删除对应 `chapter_outlines`。
* 置空 `timeline_events.chapter_id`。
* 置空 `foreshadows` 引入章与回收章引用。
* 置空 `work_outlines.content_tree_json` 中匹配 `chapter_ref`。
* 删除章节后重排章节 `order_index`。

关键规则：

* 删除章节必须在单事务中完成。
* 全书大纲节点仅置空引用，不删除节点。
* 任一步失败时事务回滚。

完成标准（DoD）：

* 删除章节引用清理测试通过。
* 回滚测试通过。
* 删除后章节顺序连续。

### T3-13：OutlinesRouter 实现

目标：

* 暴露全书大纲与章节细纲 API。

涉及模块：

* Backend

实现内容：

* 实现 `GET /api/v1/works/{work_id}/outline`。
* 实现 `PUT /api/v1/works/{work_id}/outline`。
* 实现 `GET /api/v1/chapters/{chapter_id}/outline`。
* 实现 `PUT /api/v1/chapters/{chapter_id}/outline`。
* 请求与响应使用统一 DTO。

关键规则：

* 保存携带 `expected_version`。
* 409 返回 `asset_version_conflict` 模板。
* `content_text` 是唯一真实存储。

完成标准（DoD）：

* Outlines API 集成测试通过。
* 版本冲突响应字段完整。
* 非法 schema 返回 `invalid_input`。

### T3-14：TimelineRouter 实现

目标：

* 暴露时间线事件 CRUD 与调序 API。

涉及模块：

* Backend

实现内容：

* 实现 `GET/POST /api/v1/works/{work_id}/timeline-events`。
* 实现 `PUT/DELETE /api/v1/timeline-events/{event_id}`。
* 实现 `PUT /api/v1/works/{work_id}/timeline-events/reorder`。
* 更新接口支持 `expected_version`。
* 调序接口接收完整 `items` 映射。

关键规则：

* 调序完整映射提交。
* 新事件追加末尾。
* 章节引用可为空。

完成标准（DoD）：

* Timeline API 集成测试通过。
* 调序非法映射返回 `invalid_input`。
* 删除事件后列表顺序稳定。

### T3-15：ForeshadowsRouter 实现

目标：

* 暴露伏笔 CRUD 与状态筛选 API。

涉及模块：

* Backend

实现内容：

* 实现 `GET/POST /api/v1/works/{work_id}/foreshadows`。
* 实现 `PUT/DELETE /api/v1/foreshadows/{foreshadow_id}`。
* 支持 `status` 查询参数。
* 更新接口支持 `expected_version`。
* 返回 DTO 包含章节引用字段。

关键规则：

* 列表默认请求 `status=open`。
* `status` 只允许 `open/resolved`。
* 章节引用可为空。

完成标准（DoD）：

* Foreshadows API 集成测试通过。
* open/resolved 筛选正确。
* 版本冲突返回 409 模板。

### T3-16：CharactersRouter 实现

目标：

* 暴露人物卡 CRUD 与搜索 API。

涉及模块：

* Backend

实现内容：

* 实现 `GET/POST /api/v1/works/{work_id}/characters`。
* 实现 `PUT/DELETE /api/v1/characters/{character_id}`。
* 支持 keyword 查询。
* 请求 aliases 接收数组。
* 响应 aliases 返回数组。

关键规则：

* `name` 必填。
* aliases 空值统一为 `[]`。
* 重名允许，不由后端阻断。

完成标准（DoD）：

* Characters API 集成测试通过。
* aliases 规范化可通过 API 验证。
* keyword 搜索结果正确。

### T3-17：Stage 3 后端测试套件

目标：

* 建立结构化资产后端回归测试。

涉及模块：

* Backend / DB

实现内容：

* 增加 Outline 测试。
* 增加 Timeline 测试。
* 增加 Foreshadow 测试。
* 增加 Character 测试。
* 增加删除章节引用清理测试。
* 增加结构化资产 409 模板测试。

关键规则：

* 每个结构化资产更新必须覆盖乐观锁冲突。
* 删除章节引用清理必须验证事务结果。
* `content_tree_json` schema 必须覆盖非法字段。

完成标准（DoD）：

* Stage 3 后端测试全部通过。
* 结构化资产 API 均有集成测试。
* 数据库测试不污染开发数据。

### T3-18：Stage 3 联调验证

目标：

* 验证结构化资产后端可供 Stage 4 前端接入。

涉及模块：

* Backend / DB

实现内容：

* 启动后端并验证 Outlines API。
* 验证 Timeline CRUD 与调序。
* 验证 Foreshadow CRUD 与状态筛选。
* 验证 Character CRUD 与搜索。
* 验证结构化资产 409。
* 验证删除章节引用清理。

关键规则：

* Stage 3 不实现前端 Drawer。
* 结构化资产不涉及 AI 语义。
* API 返回结构必须支持 Stage 4 前端对接。

完成标准（DoD）：

* Outlines/Timeline/Foreshadows/Characters API 可用。
* Stage 3 测试全部通过。
* 可进入 Stage 4 前端结构化资产开发。
