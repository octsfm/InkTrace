# InkTrace V1.1 Stage 1 验收结果

验收日期：2026-04-30

## 验收范围

- Stage 0 基线验证
- `/api/v1/health`
- Works API
- Chapters API
- Sessions API
- IO Import / Export API
- Chapter `version_conflict` 409 响应
- TXT 导入导出闭环
- 删除章节后的 `order_index` 连续性与建议激活章节

## 验收命令

```powershell
python scripts/verify_stage0_v1.py
pytest tests/test_v1_routes_smoke.py tests/test_v1_works_router.py tests/test_v1_chapters_router.py tests/test_v1_sessions_router.py tests/test_v1_io_router.py
pytest tests/test_v1_core_schema_migration.py tests/test_v1_database_session.py tests/test_v1_database_repositories.py tests/test_v1_repositories_stage1.py tests/test_v1_work_entity.py tests/test_v1_chapter_entity.py tests/test_v1_edit_session_entity.py tests/test_v1_work_service.py tests/test_v1_chapter_service.py tests/test_v1_session_service.py tests/test_v1_io_service.py tests/test_v1_text_metrics.py tests/test_v1_schemas.py tests/test_v1_works_router.py tests/test_v1_chapters_router.py tests/test_v1_sessions_router.py tests/test_v1_io_router.py tests/test_v1_routes_smoke.py
```

## 验收结果

- Stage 0 基线：通过，输出 `stage0_v1_baseline_ok`
- API 联调测试：通过，`30 passed`
- Stage 1 后端回归：通过，`80 passed`

## 验收结论

Stage 1 后端落地完成。

Works / Chapters / Sessions / IO API 已可用于 Stage 2 前端联调。

## 边界确认

- Stage 1 未实现前端 Local-First 保存链路。
- Stage 1 未实现结构化资产业务。
- Stage 1 未引入 AI 能力。
- Workbench API 统一挂载 `/api/v1/*`。
