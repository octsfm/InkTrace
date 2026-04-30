# InkTrace V1.1 Stage 2 Acceptance

验收时间：2026-05-01

## 验收范围

- Stage 2 前端 Workbench 主链路
- V1.1 `/api/v1/*` 前后端字段对齐基线
- Local-First 正文保存链路
- 章节切换与会话恢复链路
- TXT 导入与导出入口
- 409 冲突保留本地草稿链路

## 验收结果

- 前端 API 封装使用 `/api/v1/*`。
- 书架页支持作品创建、导入入口、导出弹窗入口、重命名、改作者、删除与打开作品。
- 写作页保持单主页面结构：章节侧栏、正文编辑区、AssetRail、AssetDrawer。
- 写作页初始化由 `useWorkspaceStore.initializeWorkspace` 承担作品与会话恢复。
- 正文输入链路遵守 Local-First：输入先通过 `useSaveStateStore` 写本地缓存，网络保存异步执行。
- 切章流程不等待网络保存成功，切章前写入当前章节本地草稿快照。
- 会话恢复包含最后章节、cursor_position、scrollTop。
- 离线状态在状态条中以 `offline` 状态展示，不映射为保存失败。
- 409 冲突弹窗保留本地草稿，并提供本地版本与服务端版本对比入口。
- TXT 导入调用 `/api/v1/io/import`，TXT 导出调用 `/api/v1/io/export/{work_id}`。
- TXT 导出文件名优先使用后端 `Content-Disposition`，无响应头时使用前端安全兜底文件名。
- Workbench UI 未新增 AI 入口。

## 自动化证据

- `src/api/__tests__/works.spec.js` 覆盖 `/api/v1/*`、409 识别、TXT 导出 blob 响应。
- `src/stores/__tests__/useWorkspaceStore.spec.js` 覆盖作品初始化、会话恢复、会话位置保存。
- `src/stores/__tests__/useSaveStateStore.spec.js` 覆盖本地草稿、成功清理、409 保留、离线回放。
- `src/views/__tests__/WritingStudio.spec.js` 覆盖写作页布局、Store 初始化、Local-First 草稿边界、切章不等待网络、Ctrl/Cmd+S。
- `src/components/works/__tests__/ExportTxtModal.spec.js` 覆盖导出选项、snake_case 参数、Content-Disposition 文件名入口。
- `tests/test_v1_routes_smoke.py` 覆盖 V1 路由基线。
- `tests/test_v1_*` 覆盖 V1 Work、Chapter、Session、IO、Schema、Repository 主链路。

## 验证命令

```powershell
cd D:\Work\InkTrace\ink-trace\frontend
npm test -- --run
npm run build

cd D:\Work\InkTrace\ink-trace
python -m pytest tests -k v1
```

## 验证结果

- Frontend Vitest：21 files passed，107 tests passed。
- Frontend Build：vite build passed。
- Backend V1 Pytest：82 passed，4 deselected。

## 风险与备注

- `WorksList.vue` 与部分历史测试文件仍存在早期中文乱码文案，但不影响 Stage 2 功能链路与构建结果；后续独立执行文案清理，不与业务任务混做。
- 旧 Legacy 测试仍存在于前端测试集中，当前回归已通过；Stage 2 不删除 Legacy。
- Stage 2 自动化验证覆盖接口契约、Store 行为、关键 UI 契约与后端 V1 路由/服务；浏览器级人工联调仍需在提测环境执行一次烟测。

## 结论

Stage 2 前端主链路与 V1.1-A 联调基线通过，可进入 Stage 3 后端结构化资产开发。
