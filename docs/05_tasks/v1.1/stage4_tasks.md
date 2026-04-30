# Stage 4 Tasks

### T4-01：useWritingAssetStore 收口

目标：

* 实现结构化资产前端统一 Store，承载读取、草稿、显式保存与冲突状态。

涉及模块：

* Frontend / Store

实现内容：

* 维护 work outline 与 chapter outline 状态。
* 维护 timeline、foreshadows、characters 状态。
* 维护 assetDrafts。
* 维护 assetSaveStatus。
* 维护 assetConflictPayload。
* 提供加载、编辑、保存、放弃、冲突处理动作。

关键规则：

* 结构化资产不进入正文自动回放队列。
* 结构化资产采用显式保存。
* 409 未决策前不得清理本地暂存。

完成标准（DoD）：

* Store 可加载四类资产。
* Store 可写入 asset_draft。
* 409 后 assetConflictPayload 正确。

### T4-02：结构化资产本地暂存接入

目标：

* 将结构化资产编辑接入 asset_draft 本地暂存策略。

涉及模块：

* Frontend / Store

实现内容：

* 使用 `asset_draft:{asset_type}:{asset_id}` key。
* 编辑时写入本地暂存。
* 保存成功后清理对应暂存。
* 409 时保留暂存。
* 离线时允许继续编辑并保留暂存。
* LRU 淘汰优先淘汰非当前资产暂存。

关键规则：

* 结构化资产离线后需用户手动保存。
* 结构化资产暂存优先淘汰，正文草稿优先保留。
* 当前打开抽屉正在编辑项不得被淘汰。

完成标准（DoD）：

* 编辑资产后本地暂存存在。
* 保存成功后暂存清理。
* 409 后暂存仍存在。

### T4-03：AssetRail 实现

目标：

* 实现结构化资产入口条，打开对应 Drawer Tab。

涉及模块：

* Frontend

实现内容：

* 实现 `AssetRail`。
* 展示 Outline、Timeline、Foreshadow、Character 入口。
* 点击入口打开 AssetDrawer。
* 点击当前激活入口关闭 Drawer。
* 展示当前激活状态。

关键规则：

* AssetRail 不触发正文保存。
* AssetRail 不改变正文编辑区内容。
* 不新增 AI 入口。

完成标准（DoD）：

* 四个入口可点击。
* 激活状态展示正确。
* 点击当前入口可关闭 Drawer。

### T4-04：AssetDrawer 实现

目标：

* 实现右侧单抽屉容器和 Tab 切换保护。

涉及模块：

* Frontend

实现内容：

* 实现 `AssetDrawer`。
* 同一时间只显示一个 Tab。
* 支持 Outline、Timeline、Foreshadow、Character Tab。
* 关闭 Drawer 时检查 dirty。
* 切换 Tab 时检查 dirty。
* 移动端使用覆盖层。

关键规则：

* 同一时间只允许一个 Drawer。
* Drawer 打开/关闭不主动改变正文焦点。
* dirty 时切换或关闭必须提示保存/放弃/取消。

完成标准（DoD）：

* 单 Drawer 约束通过。
* dirty 保护三分支可验证。
* 关闭 Drawer 后正文焦点不被主动改变。

### T4-05：AssetConflictModal 实现

目标：

* 实现结构化资产 409 冲突处理弹窗。

涉及模块：

* Frontend

实现内容：

* 实现 `AssetConflictModal`。
* 展示本地版本与服务端版本。
* 提供本地 vs 服务端对比入口。
* 提供覆盖保存、放弃本地、取消操作。
* 决策前保留 asset_draft。

关键规则：

* 结构化资产 409 保留本地暂存。
* 覆盖保存使用本地内容重新提交。
* 放弃本地清理暂存并加载远端。

完成标准（DoD）：

* 409 后弹窗可打开。
* 取消后暂存仍存在。
* 覆盖与放弃路径可验证。

### T4-06：OutlinePanel 全书大纲实现

目标：

* 实现全书大纲文本编辑与显式保存。

涉及模块：

* Frontend

实现内容：

* 实现 `OutlinePanel` 全书大纲 Tab。
* 以 `content_text` 作为主编辑区。
* 展示 dirty 状态。
* 点击保存提交 `expected_version`。
* 保存成功更新本地 version。
* 409 打开 AssetConflictModal。

关键规则：

* `content_text` 为唯一真实存储。
* `content_tree_json` 仅为派生缓存。
* Outline 显式保存。

完成标准（DoD）：

* 可编辑并保存全书大纲。
* 保存成功后 dirty 清除。
* 409 后本地暂存保留。

### T4-07：OutlinePanel 章节细纲实现

目标：

* 实现当前章节细纲编辑与切章自动切换。

涉及模块：

* Frontend / Store

实现内容：

* 加载当前 active chapter 的 chapter outline。
* 切章时检查当前章节细纲 dirty。
* dirty 时提示保存/放弃/取消。
* 目标章节存在本地暂存时优先使用暂存。
* 无本地暂存时加载远端细纲。

关键规则：

* 当前章节细纲存在未保存编辑时，切换章节前必须提示用户保存或放弃。
* 用户取消时保持当前章节不变。
* 切章前正文仍按 Local-First 写本地草稿。

完成标准（DoD）：

* 切章后细纲切换到目标章节。
* dirty 分支三种选择可验证。
* 取消后不切章。

### T4-08：TimelinePanel 列表与 CRUD

目标：

* 实现时间线事件列表与基础编辑能力。

涉及模块：

* Frontend

实现内容：

* 实现 `TimelinePanel`。
* 按 `order_index ASC` 展示事件。
* 支持新建事件。
* 支持编辑事件标题、描述、关联章节。
* 支持删除事件。
* 保存携带 `expected_version`。

关键规则：

* 事件 `chapter_id` 可为空。
* 新事件追加末尾。
* Timeline 更新使用显式保存。

完成标准（DoD）：

* 事件 CRUD 可用。
* 列表顺序正确。
* 保存冲突可进入 AssetConflictModal。

### T4-09：TimelinePanel 排序

目标：

* 实现时间线事件上移/下移排序与完整映射提交。

涉及模块：

* Frontend

实现内容：

* 实现上移按钮。
* 实现下移按钮。
* 本地重算完整 `order_index`。
* 保存排序时提交完整 `items` 映射。
* 保存成功后更新本地顺序。

关键规则：

* 前端优先提供上移/下移。
* 拖拽为增强交互，不作为首期依赖。
* 调序必须提交完整映射列表。

完成标准（DoD）：

* 上移/下移改变本地顺序。
* 提交 payload 包含完整映射。
* 后端返回后列表顺序稳定。

### T4-10：ForeshadowPanel 实现

目标：

* 实现伏笔列表、状态切换与编辑能力。

涉及模块：

* Frontend

实现内容：

* 实现 `ForeshadowPanel`。
* 默认展示未回收 `open`。
* 支持切换已回收 `resolved`。
* 支持新建、编辑、删除伏笔。
* 支持选择引入章与回收章。
* 保存携带 `expected_version`。

关键规则：

* 默认视图为 `status=open`。
* 删除章节后引用为空时记录保留。
* 状态只允许 `open/resolved`。

完成标准（DoD）：

* open/resolved 切换可用。
* 伏笔 CRUD 可用。
* 被删除章节引用显示为空。

### T4-11：CharacterPanel 实现

目标：

* 实现人物卡列表、编辑、aliases 输入与搜索。

涉及模块：

* Frontend

实现内容：

* 实现 `CharacterPanel`。
* 展示人物列表。
* 支持编辑 name、aliases、description。
* aliases 逗号输入转换数组。
* 前端空 aliases 提交 `[]`。
* 支持按 name 与 aliases 搜索。

关键规则：

* `name` 必填。
* 重名允许继续保存，但必须提示。
* 搜索不改变原始存储顺序。

完成标准（DoD）：

* 人物 CRUD 可用。
* aliases 转换正确。
* 重名提示可见且不阻断保存。

### T4-12：结构化资产 Ctrl/Cmd+S 行为

目标：

* 实现结构化资产编辑区的 Ctrl/Cmd+S 显式保存。

涉及模块：

* Frontend / Store

实现内容：

* 拦截浏览器默认保存。
* 判断当前聚焦面板。
* OutlinePanel 聚焦时保存当前 Outline。
* TimelinePanel 聚焦时保存当前事件或排序。
* ForeshadowPanel 聚焦时保存当前伏笔。
* CharacterPanel 聚焦时保存当前人物卡。

关键规则：

* Ctrl/Cmd+S 只保存当前聚焦编辑区。
* 其它未保存项保持原状态并显式提示。
* Header/Sidebar/AssetRail 聚焦时不发起保存请求。

完成标准（DoD）：

* 各面板 Ctrl/Cmd+S 行为正确。
* 未聚焦 dirty 项不被保存。
* 浏览器默认保存不触发。

### T4-13：结构化资产移动端适配

目标：

* 实现 AssetDrawer 在移动端的覆盖层展示。

涉及模块：

* Frontend

实现内容：

* 小屏时 Drawer 使用全屏覆盖层。
* 提供明显关闭入口。
* 保持单 Tab 展示。
* dirty 关闭保护仍生效。
* 不改变正文保存逻辑。

关键规则：

* 移动端不新增页面。
* 结构化资产仍只在 Drawer 中编辑。
* Drawer 关闭不得丢弃 dirty 内容。

完成标准（DoD）：

* 小屏可打开/关闭 Drawer。
* dirty 保护可用。
* 不出现独立结构化资产页面。

### T4-14：Stage 4 前端测试套件

目标：

* 建立结构化资产前端回归测试。

涉及模块：

* Frontend / Store

实现内容：

* 增加 useWritingAssetStore 测试。
* 增加 AssetDrawer 单抽屉测试。
* 增加 dirty Tab 切换测试。
* 增加 OutlinePanel 测试。
* 增加 TimelinePanel 排序测试。
* 增加 ForeshadowPanel 与 CharacterPanel 测试。

关键规则：

* 结构化资产不进入正文自动回放队列。
* Drawer 不抢正文焦点。
* 409 冲突保留 asset_draft。

完成标准（DoD）：

* Stage 4 前端测试全部通过。
* 四个面板核心交互测试通过。
* asset_draft 行为测试通过。

### T4-15：Stage 4 联调验证

目标：

* 完成结构化资产前后端联调，确认 V1.1-B 可提测。

涉及模块：

* Frontend / Backend / Store

实现内容：

* AssetDrawer 接入真实 `/api/v1/*`。
* 验证 Outline 保存与冲突。
* 验证 Timeline CRUD 与调序。
* 验证 Foreshadow open/resolved。
* 验证 Character aliases 与搜索。
* 验证删除章节后的引用展示。

关键规则：

* 结构化资产显式保存。
* 结构化资产离线不进入正文自动回放。
* Workbench 无 AI 入口。

完成标准（DoD）：

* V1.1-B 端到端流程通过。
* 四类资产刷新后数据仍在。
* 可进入 Stage 5 稳定性与验收。
