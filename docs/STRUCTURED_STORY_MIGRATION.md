# Structured Story 数据迁移说明

## 用途
将 `project_memories` 中的历史结构化 JSON 迁移到新主存表（`global_constraints`、`chapter_tasks`、`structural_drafts` 等）。

## 执行方式

```bash
python migrations/migrate_structured_story_data.py
```

或保持兼容入口：

```bash
python scripts/migrate_structured_story_data.py
```

## 执行结果
- 脚本会遍历 `project_memories` 的所有 `project_id`
- 触发新表优先的内存加载与同步逻辑
- 输出 `migrated_projects=<数量>, skipped=<数量>`
- 同步更新 `structured_story_migrated=1` 标记

## 兼容策略
- 新逻辑优先读取独立主存表
- `project_memories` 旧 JSON 仅作为兼容镜像和迁移兜底
