# Outline Import Tasks

## OI-01：作品大纲导入入口

目标：

* 在 OutlinePanel 作品大纲模式提供导入入口，并锁定入口显示边界。

涉及模块：

* Frontend / Component

实现内容：

* 在 `OutlinePanel.vue` 作品大纲模式 Header 增加“导入”按钮。
* 章节大纲模式不渲染“导入”按钮。
* 点击“导入”打开 `OutlineImportModal`。
* AssetRail、Editor、WritingStudio Header 不增加导入入口。

关键规则：

* 导入仅作用于作品大纲。
* 不新增页面。
* 导入入口不得影响正文输入焦点。

完成标准（DoD）：

* 作品大纲模式可见导入按钮。
* 章节大纲模式不可见导入按钮。
* 点击导入按钮只打开弹窗，不调用保存 API。

## OI-02：OutlineImportModal 基础组件

目标：

* 实现作品大纲导入弹窗基础 UI 与交互骨架。

涉及模块：

* Frontend / Component

实现内容：

* 新增 `frontend/src/components/workspace/OutlineImportModal.vue`。
* 提供文件选择控件。
* 提供粘贴 textarea。
* 提供纯文本预览区。
* 提供覆盖/追加单选项。
* 提供“取消”和“导入到草稿”按钮。

关键规则：

* Modal 不保存数据库。
* 预览只展示纯文本。
* Markdown 不渲染为 HTML。

完成标准（DoD）：

* Modal 可打开与关闭。
* 粘贴文本可显示在预览区。
* 覆盖/追加选项可切换。

## OI-03：文件读取与校验

目标：

* 支持 TXT 与 Markdown 文件读取，并完成输入边界校验。

涉及模块：

* Frontend / Component / Utils

实现内容：

* 限制文件后缀为 `.txt`、`.md`。
* 限制文件大小不超过 2MB。
* 支持 `utf-8-sig`、`utf-8` 文本读取。
* 非法文件类型显示错误。
* 空内容显示错误。

关键规则：

* `.md` 原样导入。
* 不做自动转码。
* 不解析章节标记。

完成标准（DoD）：

* TXT 文件可读取。
* Markdown 文件可读取并原样预览。
* 非法类型、超大文件、空内容均不写入草稿。

## OI-04：字符统计与性能提示

目标：

* 实现导入文本原始字符统计与性能提示。

涉及模块：

* Frontend / Component

实现内容：

* 统计导入文本原始字符数。
* 字符数包含空格、换行、制表符。
* 20,000 字符以上显示建议提示。
* 50,000 字符以上显示性能风险提示。
* 超过提示阈值不阻断导入。

关键规则：

* 不复用正文 `word_count` 口径。
* 不修改后端 `textMetrics`。

完成标准（DoD）：

* 字符数随粘贴与文件读取更新。
* 两级提示阈值显示正确。
* 50,000 字符以上仍可导入到草稿。

## OI-05：覆盖与追加合并

目标：

* 实现导入内容写入作品大纲草稿前的合并规则。

涉及模块：

* Frontend / Component

实现内容：

* 当前作品大纲草稿为空时直接导入。
* 当前作品大纲草稿非空时默认覆盖。
* 追加模式将导入文本追加到草稿末尾。
* 原草稿与导入文本均非空时插入两个换行。
* 空文本组合不插入多余换行。

关键规则：

* 导入结果必须确定。
* 不修改章节细纲草稿。
* 不生成 `content_tree_json`。

完成标准（DoD）：

* 覆盖结果正确。
* 追加结果正确。
* 空文本组合无多余换行。

## OI-06：dirty 与本地暂存接入

目标：

* 将导入结果接入既有作品大纲 dirty 与本地暂存链路。

涉及模块：

* Frontend / Component / Store

实现内容：

* 导入结果写入作品大纲 `localContent`。
* 设置作品大纲 dirty。
* 写入既有结构化资产本地暂存。
* 禁止新增 `outlineImportDraft`。
* 导入成功后关闭弹窗。

关键规则：

* 结构化资产手动保存。
* 导入阶段不调用保存 API。
* 冲突未决策前不得清理本地暂存。

完成标准（DoD）：

* 导入后 dirty=true。
* 导入后本地暂存存在。
* 导入后未发起保存 API。

## OI-07：保存与 409 冲突回归

目标：

* 验证导入后的保存仍复用现有作品大纲保存与冲突处理链路。

涉及模块：

* Frontend / Store / API

实现内容：

* 导入后点击“保存作品大纲”调用现有 Outline 保存动作。
* 保存请求携带 `expected_version`。
* 保存成功后更新 version 并清理暂存。
* 保存返回 409 时保留本地草稿、dirty 与暂存。
* 409 时打开本地版本 vs 服务端版本对比入口。

关键规则：

* 不新增 API。
* 不绕过结构化资产冲突弹窗。
* 409 未决策前禁止清理暂存。

完成标准（DoD）：

* 保存成功路径通过。
* 409 冲突路径通过。
* 取消冲突后导入草稿仍保留。

## OI-08：专项测试与验收

目标：

* 为作品大纲导入补齐最小必要测试与回归验证。

涉及模块：

* Frontend / Test

实现内容：

* 新增 `OutlineImportModal` 测试。
* 更新 `OutlinePanel` 测试。
* 覆盖 TXT、Markdown、粘贴三条输入路径。
* 覆盖覆盖/追加合并规则。
* 覆盖导入后不调用保存 API。
* 覆盖章节大纲模式不显示导入入口。

关键规则：

* 测试不得依赖真实后端解析 API。
* 测试必须证明导入只进入草稿。
* 测试必须证明无 AI 入口。

完成标准（DoD）：

* `OutlineImportModal` 测试通过。
* `OutlinePanel` 测试通过。
* 结构化资产冲突相关回归通过。

验证命令：

```powershell
npm test -- src/components/workspace/__tests__/OutlineImportModal.spec.js src/components/workspace/__tests__/OutlinePanel.spec.js
```

```powershell
npm test -- src/stores/__tests__/useWritingAssetStore.spec.js src/components/workspace/__tests__/AssetConflictModal.spec.js
```
