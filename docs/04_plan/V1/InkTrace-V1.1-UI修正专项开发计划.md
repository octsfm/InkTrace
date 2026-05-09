# InkTrace V1.1 UI 修正专项开发计划

版本：v1.1-ui-fix  
依据文档：
- `docs/03_design/InkTrace-V1.1-界面与交互设计文档.md`
- `docs/03_design/InkTrace-V1.1-详细设计文档.md`

## 1. 目标

本计划用于修正 V1.1 写作页结构化资产区域与写作偏好区域的 UI/UE 偏差。

目标：
- 修复 OutlinePanel 高度不足导致内容显示不全的问题。
- 收敛 AssetRail 按钮展示形态。
- Drawer 打开后隐藏当前激活模块入口。
- 修正写作偏好面板以内联方块展开导致界面割裂的问题。
- 锁定作品大纲导入入口边界。

非目标：
- 不新增 AI 能力。
- 不新增页面。
- 不新增结构化资产类型。
- 不修改后端数据模型。
- 不修改 Outline / Timeline / Foreshadow / Character 的业务语义。

## 2. 影响范围

Frontend：
- `frontend/src/components/workspace/AssetRail.vue`
- `frontend/src/components/workspace/AssetDrawer.vue`
- `frontend/src/components/workspace/OutlinePanel.vue`
- `frontend/src/views/WritingStudio.vue`
- `frontend/src/stores/preference.js` 或现有偏好 Store
- 对应组件测试文件

Docs：
- 本计划不再修改需求边界。
- 如实现中发现设计冲突，仅回写 UI/UE 或详细设计文档，不扩展功能。

## 3. 执行顺序

### UI-FIX-01：AssetRail 单字入口收口

目标：
- 修正 AssetRail 同时显示单字与全称导致的视觉噪音。

实现内容：
- AssetRail 按钮仅显示单字：`纲`、`线`、`伏`、`人`。
- 完整名称仅作为 `title` / `aria-label` / hover 提示存在。
- 不显示“上方单字 + 下方全称”的双层文本。
- 按钮尺寸保持稳定，不因文字长度改变布局。

关键规则：
- AssetRail 不触发正文保存。
- AssetRail 不改变正文编辑区内容。
- AssetRail 不新增 AI 入口。

DoD：
- 四个入口仅显示单字。
- hover 或无障碍标签可识别完整模块名称。
- AssetRail 测试通过。

### UI-FIX-02：Drawer 打开后隐藏当前激活模块入口

目标：
- 修正当前模块已在 Drawer Header 展示时，AssetRail 重复显示当前按钮的问题。

实现内容：
- Drawer 打开后，AssetRail 仅渲染未激活模块入口。
- 当前激活模块入口不在 AssetRail 中显示。
- 当前模块名称由 Drawer Header 展示。
- Drawer 关闭仅通过 Drawer Header 关闭按钮触发。
- 点击其它模块入口时，继续执行 dirty 检查后切换。

关键规则：
- 当前激活模块不通过 AssetRail 再次点击关闭。
- Drawer 同一时间只允许一个模块打开。
- dirty 时切换模块必须提示保存 / 放弃 / 取消。

DoD：
- 打开 Outline Drawer 后，AssetRail 中不显示 `纲`。
- 打开 Timeline Drawer 后，AssetRail 中不显示 `线`。
- 点击其它入口仍可切换模块。
- 当前模块 dirty 时切换仍触发保护。

### UI-FIX-03：AssetDrawer 内容区滚动与底部操作吸底

目标：
- 修复大纲等长内容在 Drawer 内显示不全的问题。

实现内容：
- AssetDrawer 使用三段式布局：Header / ScrollBody / Footer。
- Header 固定展示当前模块标题与关闭按钮。
- ScrollBody 独立滚动，承载当前面板内容。
- Footer 固定或吸底展示状态与保存操作。
- Drawer 高度不随内容撑破页面。

关键规则：
- Drawer 内容区独立滚动。
- 保存按钮与状态区保持可见。
- Drawer 打开/关闭不抢正文焦点。

DoD：
- OutlinePanel 长内容可滚动查看到底部。
- 保存按钮不被长内容挤出可视区域。
- 移动端 Drawer 仍为覆盖层，不新增页面。

### UI-FIX-04：OutlinePanel 二级切换收口

目标：
- 避免“作品大纲 + 章节大纲”上下同时展示导致内容挤压。

实现内容：
- OutlinePanel 内提供二级切换：`作品大纲 / 章节大纲`。
- 同一时间只显示一个编辑区。
- 默认进入 `作品大纲`。
- 切换到 `章节大纲` 时，仅展示当前激活章节细纲。
- 章节细纲 dirty 时，沿用保存 / 放弃 / 取消保护。

关键规则：
- `content_text` 为唯一真实存储。
- `content_tree_json` 仅为派生缓存。
- 仅作品大纲模式允许导入入口，章节大纲模式不允许导入入口。

DoD：
- OutlinePanel 不再上下同时显示两个 textarea。
- 长大纲内容显示完整且可滚动。
- 切换作品大纲 / 章节大纲不丢失 draft。
- OutlinePanel 测试通过。

### UI-FIX-05：写作偏好浮层化

目标：
- 修正写作偏好点击后以内联方块区域展开导致界面割裂的问题。

实现内容：
- 桌面端点击 Header 内“写作偏好”后，显示锚定在按钮下方的浮层卡片。
- 偏好面板不占用主页面文档流，不推挤 Header、Editor、Sidebar、Drawer。
- 支持点击空白区域关闭。
- 支持 `Esc` 关闭。
- 移动端使用底部弹层或右侧覆盖层。

关键规则：
- 写作偏好只影响本地展示配置。
- 偏好面板打开/关闭不触发正文 flush。
- 偏好面板打开/关闭不修改正文内容。

DoD：
- 点击写作偏好不再在页面下方生成整块内联区域。
- 浮层可打开、关闭。
- 偏好修改后本地状态生效。
- 写作页布局不被偏好面板推挤。

### UI-FIX-06：作品大纲导入入口边界锁定

目标：
- 在不新增页面、不新增后端解析 API 的前提下，允许作品大纲导入纯文本草稿。
- 防止导入能力误扩展到章节细纲、章节正文或其它结构化资产。

实现内容：
- OutlinePanel 的作品大纲模式 Header 显示“导入”按钮。
- OutlinePanel 的章节细纲模式不显示“导入”按钮。
- 新增 `OutlineImportModal`，支持 `.txt`、`.md` 文件与手动粘贴。
- 导入结果只写入作品大纲 `localContent`，进入 dirty 状态与既有本地暂存。
- 导入阶段不调用保存 API。

关键规则：
- 导入仅作用于作品大纲，不作用于章节细纲。
- Markdown 原样导入，不渲染、不解析、不生成树。
- 覆盖为默认导入方式；追加时在原草稿和导入文本之间插入两个换行。
- 不新增 API。
- 不新增 `outlineImportDraft` 状态链路。
- 保存仍使用 `PUT /api/v1/works/{work_id}/outline`。

DoD：
- 作品大纲模式显示导入入口。
- 章节细纲模式不显示导入入口。
- TXT、Markdown、粘贴三种路径可导入到作品大纲草稿。
- 导入后 dirty=true，未发起保存请求。
- 保存返回 409 时保留本地草稿与对比入口。

### UI-FIX-07：回归测试与验收

目标：
- 验证 UI 修正不破坏 Stage 3 ~ Stage 5 已完成能力。

实现内容：
- 更新 AssetRail 测试。
- 更新 AssetDrawer 测试。
- 更新 OutlinePanel 测试。
- 增加或更新写作偏好面板测试。
- 执行 Stage 5 指定前端回归。
- 执行后端 V1 回归，确认本次 UI 修正未影响 API。

验证命令：

```powershell
npm test -- src/components/workspace/__tests__/AssetRail.spec.js src/components/workspace/__tests__/AssetDrawer.spec.js src/components/workspace/__tests__/OutlinePanel.spec.js src/views/__tests__/WritingStudio.spec.js
```

```powershell
npm test -- src/stores/__tests__/useSaveStateStore.spec.js src/stores/__tests__/useWritingAssetStore.spec.js src/utils/__tests__/localCache.spec.js src/components/workspace/__tests__/OutlinePanel.spec.js src/components/workspace/__tests__/TimelinePanel.spec.js src/components/workspace/__tests__/ForeshadowPanel.spec.js src/components/workspace/__tests__/CharacterPanel.spec.js src/components/workspace/__tests__/VersionConflictModal.spec.js src/views/__tests__/WritingStudio.spec.js
```

```powershell
python -m pytest tests -k v1
```

DoD：
- UI 修正专项测试通过。
- Stage 5 指定前端回归通过。
- 后端 V1 回归通过。
- Workbench / Legacy / AI 边界扫描不新增违规项。

## 4. 验收清单

- [ ] AssetRail 只显示单字入口。
- [ ] Drawer 打开后隐藏当前激活模块入口。
- [ ] 当前模块名称只在 Drawer Header 展示。
- [ ] Drawer 关闭只通过 Header 关闭按钮。
- [ ] Drawer 内容区独立滚动。
- [ ] Drawer 底部状态与保存操作可见。
- [ ] OutlinePanel 作品大纲 / 章节大纲二级切换生效。
- [ ] OutlinePanel 不显示大纲导入入口。
- [ ] 写作偏好以浮层展示，不以内联方块推挤页面。
- [ ] 正文输入焦点不被 Drawer / 偏好面板主动抢占。
- [ ] 结构化资产仍为手动保存。
- [ ] 无 AI 入口。

## 5. 风险与控制

风险：隐藏当前激活 Rail 入口后，用户失去“再次点击关闭”的路径。  
控制：Drawer Header 必须提供明显关闭按钮。

风险：Drawer 内容区滚动与底部吸底可能影响移动端高度。  
控制：移动端继续使用全屏覆盖层，并保持 Header / Body / Footer 三段布局。

风险：OutlinePanel 二级切换可能隐藏另一个未保存编辑区。  
控制：切换二级 Tab 前必须检查当前编辑区 dirty 状态。

风险：写作偏好浮层点击外部关闭可能误触。  
控制：关闭只隐藏浮层，不保存正文、不清理草稿、不触发远端请求。

## 6. 完成定义

本专项完成后，视为 V1.1 UI/UE 封版前修正完成。

完成条件：
- UI-FIX-01 ~ UI-FIX-07 全部通过。
- 设计文档、实现、测试三者口径一致。
- 不新增功能范围。
- 不破坏 Stage 3 ~ Stage 5 已完成能力。
