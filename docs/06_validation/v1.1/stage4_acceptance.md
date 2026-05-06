# Stage 4 Acceptance

## 验证日期

2026-05-05

## 验证范围

- Writing Asset Store：`asset_draft` 显式保存、冲突保留、Timeline 调序 draft。
- AssetDrawer：单抽屉切换、dirty guard、移动端覆盖层。
- OutlinePanel：全书大纲、章节细纲读取与显式保存。
- TimelinePanel：事件 CRUD、完整映射调序、`Ctrl/Cmd+S` 焦点分发。
- ForeshadowPanel：`open/resolved` 切换、章节引用选择、冲突保留。
- CharacterPanel：CRUD、aliases 规范化、keyword 搜索、重名提示不阻断。
- WritingStudio：右侧资产抽屉接线、快捷键分发、移动端抽屉接入。
- Backend V1 Assets：Outlines / Timeline / Foreshadows / Characters Router、Service、Repository、删章引用清理。

## 验证命令

```powershell
python -m pytest tests/test_v1_content_tree_schema.py tests/test_v1_outline_repositories.py tests/test_v1_timeline_repositories.py tests/test_v1_foreshadow_repositories.py tests/test_v1_character_repositories.py tests/test_v1_writing_asset_service_outline.py tests/test_v1_writing_asset_service_timeline.py tests/test_v1_writing_asset_service_foreshadow.py tests/test_v1_writing_asset_service_character.py tests/test_v1_outlines_router.py tests/test_v1_timeline_router.py tests/test_v1_foreshadows_router.py tests/test_v1_characters_router.py tests/test_v1_chapter_service.py
```

结果：`56 passed`

```powershell
npm test -- src/stores/__tests__/useWritingAssetStore.spec.js src/components/workspace/__tests__/AssetDrawer.spec.js src/components/workspace/__tests__/OutlinePanel.spec.js src/components/workspace/__tests__/TimelinePanel.spec.js src/components/workspace/__tests__/ForeshadowPanel.spec.js src/components/workspace/__tests__/CharacterPanel.spec.js src/views/__tests__/WritingStudio.spec.js
```

结果：`49 passed`

## 联调备注

- Stage 4 后端联调前，发现一批 Python 文件头携带连续 `U+FEFF`，导致 `pytest` 收集阶段直接 `SyntaxError`。
- 本轮已清理相关 Router / Repository / Service / Entity / Test 文件头的 BOM 残留，后端资产链路回归恢复可执行。
- 前端结构化资产测试覆盖已包含 `asset_draft` 与正文离线回放队列隔离规则，符合 Stage 4 设计要求。

## 验收结论

- Stage 4 结构化资产前端工作台通过聚焦回归。
- Stage 4 结构化资产后端链路通过 Router / Service / Repository 联调回归。
- Outline / Timeline / Foreshadow / Character 四类资产在刷新后具备持久化读取能力。
- 结构化资产保持显式保存，不进入正文自动回放队列。
- V1.1-B 可进入 Stage 5 稳定性与验收。
