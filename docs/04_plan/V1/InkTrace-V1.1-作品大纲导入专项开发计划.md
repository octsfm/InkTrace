# InkTrace V1.1 作品大纲导入专项开发计划

版本：v1.1-outline-import-plan

依据文档：

- `docs/03_design/InkTrace-V1.1-作品大纲导入功能设计文档.md`
- `docs/03_design/InkTrace-V1.1-界面与交互设计文档.md`
- `docs/03_design/InkTrace-V1.1-详细设计文档.md`
- `docs/01_requirements/InkTrace-V1.1-需求规格说明书.md`

---

## 1. 目标

本计划用于落地作品大纲导入能力。

目标：

- 在作品大纲模式提供导入入口。
- 支持 TXT、Markdown 文件与手动粘贴导入。
- 导入结果只进入作品大纲草稿与 dirty 状态。
- 保存继续复用现有作品大纲保存链路。
- 保持 V1.1 非 AI、手动保存、Workbench 隔离边界。

非目标：

- 不新增页面。
- 不新增后端解析 API。
- 不修改后端数据模型。
- 不导入章节细纲。
- 不创建章节。
- 不解析 Markdown 结构。
- 不生成 `content_tree_json`。
- 不自动抽取时间线、伏笔、人物。
- 不引入 AI 分析、生成、拆分或抽取能力。

---

## 2. 影响范围

Frontend：

- `frontend/src/components/workspace/OutlinePanel.vue`
- `frontend/src/components/workspace/OutlineImportModal.vue`
- `frontend/src/stores/useWritingAssetStore.js` 或现有结构化资产 Store
- `frontend/src/utils/` 下的文本读取、字符统计或本地暂存工具
- `frontend/src/components/workspace/__tests__/OutlinePanel.spec.js`
- 新增 `OutlineImportModal` 对应测试

Backend：

- 不新增 Router。
- 不新增 Service。
- 不新增 Repository。
- 仅通过现有 `PUT /api/v1/works/{work_id}/outline` 完成最终保存。

Docs：

- 专项设计已完成。
- 开发完成后补充验收记录。

---

## 3. 执行顺序

### OI-01：入口与显示边界

目标：

- 在 OutlinePanel 作品大纲模式显示导入入口，并锁定其它区域不出现入口。

实现内容：

- 作品大纲模式 Header 显示“导入”按钮。
- 章节大纲模式隐藏“导入”按钮。
- AssetRail、Editor、全局 Header 不显示导入入口。
- 点击导入按钮打开导入弹窗。

关键规则：

- 导入仅作用于作品大纲。
- 不新增页面。
- 不影响正文焦点与输入。

DoD：

- 作品大纲模式可见导入入口。
- 章节大纲模式不可见导入入口。
- 点击入口只打开导入弹窗，不调用保存 API。

### OI-02：OutlineImportModal 基础结构

目标：

- 新增作品大纲导入弹窗基础 UI。

实现内容：

- 新增 `OutlineImportModal.vue`。
- 提供文件选择入口。
- 提供粘贴 textarea。
- 提供纯文本预览区。
- 提供覆盖/追加选择。
- 提供取消与导入到草稿操作。

关键规则：

- Modal 不承载保存数据库职责。
- 预览只显示纯文本。
- 不渲染 Markdown。

DoD：

- 弹窗可打开、关闭。
- 粘贴文本可进入预览。
- 覆盖/追加选项可切换。

### OI-03：文件读取与输入校验

目标：

- 实现 TXT 与 Markdown 文件读取，并完成边界校验。

实现内容：

- 限制文件后缀为 `.txt`、`.md`。
- 限制文件大小不超过 2MB。
- 支持 `utf-8-sig`、`utf-8`。
- 不支持编码时提示失败。
- 空内容禁止导入。

关键规则：

- `.md` 原样导入。
- 不做自动转码。
- 不解析章节标记。

DoD：

- TXT 文件可读取。
- Markdown 文件可读取且原样展示。
- 非法文件类型、超大文件、空内容有确定提示。

### OI-04：字符统计与性能提示

目标：

- 实现导入内容字符统计与性能提示。

实现内容：

- 统计原始字符数。
- 统计口径包含空格、换行、制表符。
- 20,000 字符以上显示建议提示。
- 50,000 字符以上显示性能风险提示。
- 提示不阻断导入。

关键规则：

- 不复用正文 `word_count` 口径。
- 不修改后端 `word_count` 逻辑。

DoD：

- 字符数随文件读取与粘贴实时更新。
- 两级提示阈值表现正确。
- 超过 50,000 字符仍可导入到草稿。

### OI-05：覆盖与追加合并逻辑

目标：

- 实现导入文本写入作品大纲草稿前的合并规则。

实现内容：

- 当前草稿为空时直接导入。
- 当前草稿非空时默认覆盖。
- 追加模式按末尾追加。
- 原草稿与导入文本均非空时插入 `\n\n`。
- 原草稿或导入文本为空时不额外插入换行。

关键规则：

- 导入结果必须确定。
- 不修改章节细纲草稿。

DoD：

- 覆盖结果正确。
- 追加结果正确。
- 空文本组合不产生多余换行。

### OI-06：接入 OutlinePanel dirty 与本地暂存

目标：

- 将导入结果接入现有作品大纲草稿、dirty 与本地暂存链路。

实现内容：

- 导入结果写入作品大纲 `localContent`。
- 设置作品大纲 dirty。
- 写入既有结构化资产本地暂存。
- 不新增 `outlineImportDraft`。
- 导入后关闭弹窗。

关键规则：

- 结构化资产手动保存。
- 导入阶段不调用保存 API。
- 409 冲突前后均不得误清理本地暂存。

DoD：

- 导入后 dirty=true。
- 导入后本地暂存存在。
- 导入后未发起保存 API。
- 保存成功后沿用既有逻辑清理暂存。

### OI-07：冲突与保存路径回归

目标：

- 验证导入后的保存仍走现有作品大纲保存与冲突处理链路。

实现内容：

- 导入后点击保存作品大纲，提交 `PUT /api/v1/works/{work_id}/outline`。
- 保存请求携带 `expected_version`。
- 保存成功更新 version 并清理暂存。
- 409 时保留本地草稿、dirty 与暂存。
- 409 时打开本地版本 vs 服务端版本对比入口。

关键规则：

- 不新增 API。
- 不绕过结构化资产冲突弹窗。
- 冲突未决策前禁止清理暂存。

DoD：

- 保存成功路径通过。
- 409 冲突路径通过。
- 取消冲突后导入草稿仍保留。

### OI-08：测试与验收

目标：

- 为作品大纲导入补齐组件、Store 与回归测试。

实现内容：

- 增加 `OutlineImportModal` 测试。
- 更新 `OutlinePanel` 测试。
- 验证 TXT、Markdown、粘贴三路径。
- 验证覆盖/追加规则。
- 验证导入后不调用保存 API。
- 执行结构化资产前端回归。

验证命令：

```powershell
npm test -- src/components/workspace/__tests__/OutlinePanel.spec.js
```

```powershell
npm test -- src/components/workspace/__tests__/OutlineImportModal.spec.js
```

```powershell
npm test -- src/stores/__tests__/useWritingAssetStore.spec.js src/components/workspace/__tests__/AssetConflictModal.spec.js
```

DoD：

- 新增测试通过。
- OutlinePanel 回归通过。
- 结构化资产冲突回归通过。

---

## 4. 联调节点

联调节点：

- OI-06 完成后进行前端内部联调。
- OI-07 完成后进行前后端保存链路回归。

联调内容：

- 导入到草稿后保存作品大纲。
- 保存成功后刷新仍可读取最新作品大纲。
- 模拟 409 后本地导入草稿不丢失。
- 验证未新增后端解析 API。

---

## 5. 验收清单

- [ ] 作品大纲模式显示导入入口。
- [ ] 章节大纲模式不显示导入入口。
- [ ] TXT 文件可导入。
- [ ] Markdown 文件可原样导入。
- [ ] 手动粘贴可导入。
- [ ] 非法文件类型被阻止。
- [ ] 超过 2MB 文件被阻止。
- [ ] 空内容被阻止。
- [ ] 字符统计使用原始字符数。
- [ ] 20,000 与 50,000 字符提示生效。
- [ ] 覆盖当前草稿行为正确。
- [ ] 追加到末尾行为正确。
- [ ] 导入后 dirty=true。
- [ ] 导入后写入既有本地暂存。
- [ ] 导入后不调用保存 API。
- [ ] 保存仍使用现有 Outline API。
- [ ] 409 后本地草稿与暂存保留。
- [ ] 导入不创建章节、不修改章节细纲、不影响正文。
- [ ] 无 AI 入口、无 AI 文案、无 AI 自动处理。

---

## 6. 风险与控制

风险：导入入口被误认为会自动保存。  
控制：按钮文案使用“导入到草稿”，保存仍由“保存作品大纲”完成。

风险：Markdown 被误做成结构化树。  
控制：文档与测试锁定 Markdown 原样导入，不生成 `content_tree_json`。

风险：导入后刷新丢失。  
控制：导入写入既有作品大纲本地暂存。

风险：409 后导入草稿被清理。  
控制：冲突未决策前禁止清理暂存。

风险：入口误扩展到章节细纲。  
控制：章节大纲模式不渲染导入入口，并加入测试。

---

## 7. 完成定义

本专项完成条件：

- OI-01 ~ OI-08 全部通过。
- 新增与更新测试全部通过。
- 不新增后端解析 API。
- 不新增页面。
- 不引入 AI 能力。
- 与作品大纲导入设计文档一致。
