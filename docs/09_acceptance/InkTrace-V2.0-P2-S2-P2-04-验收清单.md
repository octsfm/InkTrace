# InkTrace V2.0 P2-04“接着写”封版验收报告

版本：v1.0

日期：2026-07-12

状态：本地封版通过，待 CI 复验

验收范围：方案 A、逐章确认、“接着写”作者入口、写作意图透传及安全边界

---

## 一、封版结论

本轮封版范围已经完成：作者可以在写作页打开“接着写”，选一个方向、写一句自己的想法，或不补充直接续写。系统每次只生成一章新稿，写完先交给作者查看，不会自动修改正式正文，也不会自动继续下一章。

本报告取代旧清单中 `safe / continuous` 双模式结论。P2-04 现在只有方案 A：每章完成后等待真实用户决定，不存在连续自动推进模式。

当前唯一未闭环项是远端 CI 回执，因此状态固定为“本地封版通过，待 CI 复验”，不得写成“发布验收全部完成”。

## 二、依据文档

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`（v2.1-final）
- `docs/02_architecture/InkTrace-V2.0-架构设计说明书.md`（v2.1）
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（v2.8）
- `docs/03_design/InkTrace-V2.0-P2-04-自动续写队列详细设计.md`（v1.3）
- `docs/03_design/InkTrace-V2.0-P2-11-API与前端集成边界详细设计.md`（v2.5）
- `docs/03_design/InkTrace-V2.0-P2-12-UI集成与交互设计说明书.md`（v2.4）

## 三、验收结果

| 验收项 | 封版要求 | 结果 |
|---|---|---|
| 作者入口 | 用户只看到“接着写”，默认界面不出现队列、Token、Prompt、Session 等技术词 | 通过 |
| 写作方向 | 提供“冲突更紧张、人物关系推进、承接伏笔”三项可编辑预填 | 通过 |
| 自由输入 | 允许 0 至 60 字；空值可以直接接着写；后端独立拒绝超长输入 | 通过 |
| 逐章确认 | 每章完成后等待作者，只有真实用户操作才能继续下一章 | 通过 |
| 正文隔离 | 只生成 CandidateDraft；未经过 HumanReviewGate apply 不进入正式正文 | 通过 |
| 权限边界 | workflow、agent、system 不得伪造 `user_action` 推进 | 通过 |
| 门控独立 | 继续下一章不等于把当前稿放进正文；各确认门不混用 | 通过 |
| 敏感日志 | 完整写作意图不进入通用 Job payload、日志、Trace 或审计回执 | 通过 |
| 视觉体验 | 真实写作路由中完成 Playwright 截图与设计对照 | 通过 |
| 回归测试 | 后端、前端全量测试及前端生产构建通过 | 通过 |
| 远端 CI | CI 关键检查回执 | 待复验 |

## 四、测试证据

### 后端全量

```powershell
python -m pytest -q
```

结果：`839 passed, 1 skipped`。

### 本功能后端测试

```powershell
python -m pytest tests/ai/test_auto_queue_service.py tests/ai/test_auto_queue_api.py -q
```

结果：`60 passed`。

### 前端全量

```powershell
cd frontend
npm test
```

结果：`443 passed`。

### 前端生产构建

```powershell
cd frontend
npm run build
```

结果：通过。

### 视觉验收

- 验收记录：`design-qa.md`
- 对照图：`artifacts/design-qa/continue-writing-comparison.png`
- 结果：Playwright `2 passed`

## 五、安全红线复核

以下行为均未出现：

- AI 自动写入正式正文；
- AI 自动 accept、reject 或 apply 候选稿；
- Agent、workflow 或 system 伪造真实用户操作；
- 绕过 HumanReviewGate、MemoryReviewGate 或 ConflictGuard；
- 日志记录完整 Prompt、ContextPack、正文、候选稿或 API Key；
- 把 blocked 状态显示成可用状态。

## 六、保留项与发布条件

1. `CONSECUTIVE_REVISION_FAILURE` 仍是设计预留条件，本轮没有启用自动修订循环；这不是本次方案 A 的未完成项。
2. 本报告只封版本轮 P2-04 方案 A 与“接着写”入口，不代表 P2-01 至 P2-10 所有模块均完成发布验收。
3. 合并或发布前仍需远端 CI 关键检查通过。

## 七、最终判定

- 本地功能封版：通过
- 文档封版：通过
- 安全边界：通过
- 本地测试与构建：通过
- 远端 CI：待复验
- 是否可以进入下一阶段：可以进入 CI 与人工发布确认；CI 通过前不建议直接发布
