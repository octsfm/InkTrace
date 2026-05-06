# Stage 6 Acceptance

## 验证日期

2026-05-06

## 验证范围

- T6-02：专注模式切换，隐藏非核心区域但保留正文输入和必要状态提示。
- T6-03：写作偏好面板，支持字体、字号、行距、主题本地展示配置。
- T6-04：今日新增字数，基于正文有效字符变化进行本地自然日近似统计。
- T6-05：立即同步按钮，触发当前章节标题与正文草稿 flush。
- T6-06：V1.1-C 回归测试与 V1.1-A/B 核心写作入口复核。
- T6-07：Stage 6 验收文档与脚本入口。

## 验证命令

```powershell
npm test -- src/stores/__tests__/usePreferenceStore.spec.js src/stores/__tests__/workbenchStores.spec.js src/components/workspace/__tests__/ManualSyncButton.spec.js src/components/workspace/__tests__/WritingPreferencePanel.spec.js src/components/workspace/__tests__/PureTextEditor.spec.js src/components/workspace/__tests__/StatusBar.spec.js src/components/workspace/__tests__/AssetRail.spec.js src/components/workspace/__tests__/AssetDrawer.spec.js src/components/workspace/__tests__/ChapterSidebar.spec.js src/views/__tests__/WritingStudio.spec.js
```

预期覆盖：

- 偏好 Store 本地持久化、刷新恢复、今日新增跨刷新恢复。
- 专注模式切换不丢稿、不重建正文编辑区、保留状态提示。
- 写作偏好只影响本地展示，不触发章节保存请求。
- 今日新增只统计正文有效字符变化，标题编辑不计入。
- 立即同步成功路径与离线/在线失败保留草稿路径。
- AssetRail、AssetDrawer、ChapterSidebar 等 V1.1-A/B 核心入口未被 Stage 6 破坏。

```powershell
scripts\stage6_acceptance.bat
```

## 边界结论

- `frontend/src/views/WritingStudio.vue` 未新增主页面跳转，专注模式仍在原写作页内部切换。
- `frontend/src/views/WritingStudio.vue` 与 `frontend/src/components/workspace/*` 未引入 AI、Legacy、自动生成、自动分析相关入口。
- Stage 6 新增能力全部复用本地偏好 Store 或现有正文草稿 flush 链路，没有新增后端偏好 API。
- 结构化资产入口仍保持手动打开、手动编辑、手动保存模式。

## 验收结论

- 专注模式可开关，切换时隐藏章节侧栏与资产区，但保留正文输入与状态提示。
- 写作偏好面板已支持字体、字号、行距、主题配置，刷新后仍可恢复。
- 今日新增字数已按正文有效字符变化在本地累计，删除内容后不显示负数。
- 立即同步按钮已接入当前章节草稿 flush，离线或失败时保留本地草稿。
- V1.1-C 回归通过，V1.1-A/B 核心写作与结构化资产入口未发现阻断回归，可进入最终封版。
