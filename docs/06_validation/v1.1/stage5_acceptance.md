# Stage 5 Acceptance

## 验证日期

2026-05-06

## 验证范围

- T5-01 ~ T5-05：正文/结构化资产冲突、离线回放、缓存 LRU。
- T5-06：删除章节后的细纲、Timeline、Foreshadow、全书大纲引用清理。
- T5-07：删除作品后的章节、会话、结构化资产级联清理。
- T5-08：TXT 导入导出闭环，包括空文件、无章节、多章节与导出选项。
- T5-09：Workbench / Legacy / AI 边界扫描。
- T5-10：Stage 5 验收脚本入口。
- T5-11：完整提测前回归结论。

## 验证命令

```powershell
python -m pytest tests/test_v1_work_service.py tests/test_v1_chapter_service.py tests/test_v1_routes_smoke.py
```

预期覆盖：

- `test_work_service_delete_cascades_workbench_data`
- `test_chapter_service_delete_cleans_structured_asset_chapter_refs`
- `test_v1_chapter_delete_cleans_asset_refs_smoke`
- `test_v1_work_delete_cleans_workbench_data_smoke`
- `test_v1_io_import_empty_file_smoke`
- `test_v1_io_import_fallback_smoke`
- `test_v1_io_import_and_export_smoke`
- `test_v1_io_export_follows_reordered_chapters_smoke`
- `test_v1_io_export_respects_options_smoke`

```powershell
npm test -- src/stores/__tests__/useSaveStateStore.spec.js src/stores/__tests__/useWritingAssetStore.spec.js src/utils/__tests__/localCache.spec.js src/components/workspace/__tests__/OutlinePanel.spec.js src/components/workspace/__tests__/TimelinePanel.spec.js src/components/workspace/__tests__/ForeshadowPanel.spec.js src/components/workspace/__tests__/CharacterPanel.spec.js src/components/workspace/__tests__/VersionConflictModal.spec.js src/views/__tests__/WritingStudio.spec.js
```

预期覆盖：

- 正文 409 冲突三路径。
- 结构化资产冲突三路径。
- 正文离线自动回放。
- 结构化资产离线仅暂存、不自动提交。
- 10MB 软上限、LRU 与清理提示。

```powershell
scripts\stage5_acceptance.bat
```

## 边界结论

- `frontend/src/views/WritingStudio.vue` 未发现 Legacy / AI 入口关键字引用。
- `presentation/api/routers/v1/*` 未发现 Legacy / AI / 自动生成 / 自动分析依赖。
- `/api/v1/*` 仅依赖 V1 Workbench Router、Service、Repository。
- 结构化资产仍为手动创建、编辑、排序、保存模式。

## 验收结论

- 删除章节后，章节细纲删除，Timeline / Foreshadow / 全书大纲章节引用按设计置空。
- 删除作品后，作品、章节、会话、结构化资产均不可再查询，幸存作品不受影响。
- TXT 导入导出闭环覆盖空文件、单章兜底、多章节、调序导出和导出选项。
- Workbench 主链路未引入 Legacy / AI 语义入口。
- Stage 5 已具备完整聚焦回归、脚本入口与提测结论记录，可进入下一阶段提测。
