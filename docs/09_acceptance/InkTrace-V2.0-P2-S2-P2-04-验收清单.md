# InkTrace V2.0 P2-S2 P2-04 自动续写队列验收清单

版本：v0.1 / 阶段性收口清单
状态：阶段性通过（后端主链）
所属阶段：InkTrace V2.0 P2-S2
验收范围：P2-04 Auto Queue 后端能力、恢复闭环、守门测试与关键安全边界

## 一、依据文档

- `docs/04_plan/InkTrace-V2.0-P2-开发计划.md` §S2
- `docs/03_design/InkTrace-V2.0-P2-04-自动续写队列详细设计.md`
- `docs/03_design/InkTrace-V2.0-P2-01-多章续写详细设计.md`

## 二、当前结论

本清单用于 `P2-04 Auto Queue` 当前后端收口验收，不代表整个 `P2` 或 `P2-04` 全量封板。

当前已确认通过的范围：

- 启动校验与关键门控边界已落地
- `safe / continuous` 两种模式的恢复路径已落地
- terminal run 恢复幂等与 `AIJob` 终态收敛已落地
- `generated_count / total_word_count / consumed_tokens / consecutive_blocking_count` 的最小同步闭环已落地
- `provider / blocking` 错误上下文从 `MultiChapterSession` 到 `AutoQueueRun` 的透传已落地
- `budget_stop_recorded` 审计只记录安全摘要，未泄露正文、ContextPack、CandidateDraft、Prompt 与 provider 原始细节

当前不宣称已完全完成的范围：

- `last_review_result` 未形成完整输入链，`StopConditionEvaluator` 的 reviewer 细粒度分支仍非完整态
- `CONSECUTIVE_REVISION_FAILURE` 仍属设计预留项，当前未触发
- 前端面板、全量 E2E、P2 全局联调与封板不在本清单范围内

## 三、阶段验收项

| 验收项 | 设计要求 | 当前证据 | 状态 |
|---|---|---|---|
| 启动校验 | 目标章数/字数/预算全部无效时拒绝启动 | `tests/ai/test_auto_queue_api.py`、`tests/ai/test_auto_queue_gate.py` 已覆盖 `422 auto_queue_target_chapters_required` | 已通过 |
| confirm-continue 门控 | `confirm-continue` 必须是 `caller_type=user_action` | `tests/ai/test_auto_queue_api.py`、`tests/ai/test_auto_queue_gate.py` 已覆盖 agent 调用拒绝 | 已通过 |
| continuous 恢复自动推进 | `continuous + waiting_user_decision` 恢复后继续自动推进，不自动 apply | `tests/ai/test_auto_queue_service.py`、`tests/ai/test_auto_queue_gate.py` 已覆盖恢复后 `CONTINUE_WITHOUT_APPLY` | 已通过 |
| safe 等待保持 | `safe + waiting_user_decision` 恢复后保持等待用户确认 | `tests/ai/test_auto_queue_service.py` 已覆盖 | 已通过 |
| terminal 恢复收敛 | completed / stopped / failed / cancelled 恢复时只做终态收敛，不伪装重新执行 | `tests/ai/test_auto_queue_api.py` 已覆盖 completed、stopped、failed、cancelled | 已通过 |
| terminal 恢复幂等 | 重复 warmup 不重复 reconverge 已终态 `AIJob` | `tests/ai/test_auto_queue_api.py`、`tests/ai/test_auto_queue_gate.py` 已覆盖 | 已通过 |
| 运行统计同步 | `generated_count / total_word_count / consumed_tokens` 从 `MultiChapterSession` 同步到 `AutoQueueRun` | `tests/ai/test_auto_queue_service.py` 已覆盖目标字数达成与 token 同步 | 已通过 |
| blocking 收敛 | `blocking_review_consecutive` 停止时收敛 `consecutive_blocking_count`，非 blocking 时清零 | `tests/ai/test_auto_queue_service.py`、`tests/ai/test_auto_queue_gate.py` 已覆盖 | 已通过 |
| 错误上下文透传 | `provider / blocking / failed` 场景保留 `error_code / error_message` | `tests/ai/test_auto_queue_service.py` 已覆盖 | 已通过 |
| 预算停止审计 | `budget_exceeded` 写 `budget_stop_recorded`，且只写安全摘要 | `tests/ai/test_auto_queue_service.py`、`tests/ai/test_auto_queue_gate.py` 已覆盖 | 已通过 |
| 非预算停止不误写预算审计 | `provider_unrecoverable / user_manual_stop` 不写预算审计 | `tests/ai/test_auto_queue_service.py` 已覆盖 | 已通过 |

## 四、守门测试组

当前 `P2-04` 阶段守门测试文件：

- `tests/ai/test_auto_queue_gate.py`

守门场景共 6 条：

1. `confirm-continue` 非 `user_action` caller 被拒绝
2. `start` 在 `target_chapters=0` 时返回 `422`
3. `continuous + waiting_user_decision` 重启恢复后自动推进
4. `blocking_review_consecutive` 终态同步 `consecutive_blocking_count` 与错误细节
5. terminal run 重复 warmup 不重复 reconverge
6. `budget_stop_recorded` 审计只保留安全摘要

## 五、已执行验证

### 5.1 阶段守门测试

命令：

```bash
pytest tests/ai/test_auto_queue_gate.py
```

结果：

```text
6 passed
```

### 5.2 Auto Queue Service 回归

命令：

```bash
pytest tests/ai/test_auto_queue_service.py
```

结果：

```text
35 passed
```

### 5.3 Auto Queue API 回归

命令：

```bash
pytest tests/ai/test_auto_queue_service.py tests/ai/test_auto_queue_api.py
```

结果：

```text
54 passed
```

说明：

- 该命令覆盖启动校验、恢复路径、runner 幂等、terminal 收敛等 API 关键回归
- 当前清单未额外重跑前端与全量 `tests/ai`，因此不宣称 P2 全局封板

## 六、已知偏差与风险

### 6.1 设计冲突已按人工裁决临时收口

`P2-04` 设计原文允许 `target_chapters=0` 配合其它正常停止条件启动，但 `P2-01` 与当前实现要求 `target_chapters >= 1`。当前代码按人工裁决维持 `P2-01` 现实约束，并以 `422 auto_queue_target_chapters_required` 收口。

这意味着：

- 当前实现是“按裁决后的现实口径通过”，不是彻底消除了设计文档冲突
- 若后续要完全支持 `0=不限`，需单独发起跨模块设计调整

### 6.2 reviewer 细粒度停止条件仍非完整态

当前 `P2-04` 已能同步：

- `blocked_reason_code`
- `error_code`
- `error_message`
- `consecutive_blocking_count`

但 `last_review_result` 尚未形成完整输入链，因此：

- `StopConditionEvaluator` 中 reviewer 细粒度分支仍不是完整主通路
- 当前更多依赖 `P2-01` 暴露的 session 终态来收敛

## 七、阶段判定

对照 `P2-04` 当前后端主线，结论如下：

- 后端最小主链：已通过
- 守门测试：已建立
- 恢复/幂等/审计安全边界：已建立
- 完整前后端集成：未在本清单内验收
- `P2-04` 全量封板：暂不建议直接宣称

建议下一步：

- 以本清单作为 `P2-04` 后端阶段签收依据
- 后续若继续推进，优先补 `P2-04` 与 `P2-11/P2-12` 的前端集成与联调证据
