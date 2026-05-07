# UI Fix Tasks (V1.1)

### TUI-01：AssetRail 单字入口收口

目标：

- 修正 AssetRail 同时显示单字与全称导致的视觉冗余。

涉及模块：

- Frontend / UI

实现内容：

- 将 AssetRail 按钮文案统一为单字入口：`纲`、`线`、`伏`、`人`。
- 移除按钮内双层文案展示（上单字 + 下全称）。
- 完整模块名称仅保留在 `title`、`aria-label` 或 hover 提示中。
- 保持四个按钮尺寸一致，避免文本长度导致布局抖动。
- 校验点击行为不触发正文保存链路。

关键规则：

- AssetRail 只承担模块入口，不承担正文交互。
- AssetRail 不改变正文编辑内容。
- 不新增 AI 入口。

完成标准（DoD）：

- AssetRail 仅显示四个单字入口。
- hover 或无障碍标签能识别完整模块名。
- AssetRail 现有与新增测试通过。

### TUI-02：Drawer 打开后隐藏当前激活模块入口

目标：

- 修正 Drawer 打开后当前模块在 AssetRail 重复显示的问题。

涉及模块：

- Frontend / UI / Store

实现内容：

- Drawer 打开时，AssetRail 仅渲染未激活模块入口。
- 当前激活模块入口从 AssetRail 中隐藏。
- 当前模块名称仅由 Drawer Header 展示。
- Drawer 关闭只通过 Drawer Header 关闭按钮触发。
- 保留点击其它未激活入口切换模块能力。

关键规则：

- 当前激活模块不通过 AssetRail 再次点击关闭。
- 同一时间只允许一个 Drawer 模块打开。
- 切换模块前仍执行 dirty 保护。

完成标准（DoD）：

- 打开 `outline` 时不显示 `纲` 入口，打开 `timeline` 时不显示 `线` 入口。
- Drawer 关闭按钮可用，关闭后 Rail 恢复四个入口。
- 模块切换与 dirty 保护测试通过。

### TUI-03：AssetDrawer 三段式布局与可见性修复

目标：

- 修复大纲等长内容在 Drawer 内显示不全的问题。

涉及模块：

- Frontend / UI

实现内容：

- 将 Drawer 收口为 `Header / ScrollBody / Footer` 三段式结构。
- Header 固定显示模块标题和关闭按钮。
- Body 独立滚动，承载当前面板内容。
- Footer 固定或吸底显示状态与保存操作。
- 桌面与移动端均保证保存操作区可见。

关键规则：

- Drawer 内容区独立滚动。
- Footer 操作区不可被长内容挤出可视区域。
- Drawer 打开/关闭不主动抢占正文焦点。

完成标准（DoD）：

- 大纲长内容可滚动查看到底部。
- 保存按钮始终可见可操作。
- Drawer 布局测试通过。

### TUI-04：OutlinePanel 二级切换收口

目标：

- 避免“作品大纲 + 章节大纲”同时展示导致内容挤压。

涉及模块：

- Frontend / UI / Store

实现内容：

- OutlinePanel 提供二级切换：`作品大纲` 与 `章节大纲`。
- 同一时间仅展示一个编辑区。
- 默认进入 `作品大纲`。
- 切换到 `章节大纲` 时仅展示当前激活章节细纲。
- 二级切换前执行 dirty 检查，支持保存 / 放弃 / 取消分支。

关键规则：

- `content_text` 为唯一真实存储。
- `content_tree_json` 为派生缓存。
- 不允许上下同时渲染两个大纲编辑区。

完成标准（DoD）：

- OutlinePanel 不再上下并排/叠加双编辑区。
- 切换二级 tab 不丢 draft。
- OutlinePanel 测试通过。

### TUI-05：写作偏好浮层化

目标：

- 修复写作偏好点击后以内联方块区域展开导致界面割裂的问题。

涉及模块：

- Frontend / UI / Store

实现内容：

- 桌面端将写作偏好改为锚定 Header 按钮的浮层卡片。
- 移动端使用底部弹层或右侧覆盖层。
- 支持点击空白关闭。
- 支持 `Esc` 关闭。
- 偏好面板打开/关闭不改变正文内容与保存状态。

关键规则：

- 写作偏好仅影响本地显示配置。
- 偏好面板不推挤 Header、Editor、Sidebar、Drawer 主布局。
- 偏好面板不触发正文 flush。

完成标准（DoD）：

- 写作偏好不再以内联整块渲染。
- 浮层开关行为稳定。
- 偏好修改后本地状态生效。

### TUI-06：大纲导入入口边界锁定

目标：

- 锁定 V1.1 写作页不提供大纲导入入口。

涉及模块：

- Frontend / UI

实现内容：

- 检查 OutlinePanel 与 AssetDrawer，移除或禁止“导入大纲”按钮。
- 保留作品导入流程既有导入链路，不在写作页新增上传逻辑。
- 检查快捷入口、菜单入口、悬浮入口是否存在大纲导入按钮并清理。

关键规则：

- V1.1 写作页内不提供“大纲导入”入口。
- 如需导入大纲，仅允许走作品导入流程。
- 不新增 API。

完成标准（DoD）：

- 写作页无“大纲导入”入口。
- OutlinePanel 无上传逻辑。
- 边界扫描无违规项。

### TUI-07：回归测试与验收收口

目标：

- 验证 UI 修正不破坏 Stage 3 ~ Stage 5 既有能力。

涉及模块：

- Frontend / Backend / Store

实现内容：

- 更新 AssetRail、AssetDrawer、OutlinePanel、WritingStudio 相关测试。
- 补充写作偏好浮层行为测试。
- 执行 Stage 5 指定前端回归测试集。
- 执行后端 `python -m pytest tests -k v1` 回归。
- 执行 Workbench/Legacy/AI 边界扫描。

关键规则：

- 结构化资产仍为显式保存。
- 结构化资产不进入正文自动回放队列。
- 无 AI 入口、无 Legacy 违规引用。

完成标准（DoD）：

- UI 修正专项测试通过。
- Stage 5 指定前端回归通过。
- 后端 V1 回归通过。
- 边界扫描通过。
