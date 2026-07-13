# InkTrace V2.0 项目状态报告（当前核验版）

更新时间：2026-07-13

当前基线：V2.0 本地功能完成版

封版状态：除远端 CI 与需要真实服务密钥的 Provider 联机冒烟外，冻结范围内功能已完成本地实现与自动化回归

## 一、当前结论

V2.0 P0、P1、P2 冻结功能已完成本地实现。作者可在设置中心直接开关各项写作助手，不再需要脚本；关闭功能不会删除正文、候选稿或资料。

所有 AI 写作结果继续先进入 CandidateDraft。系统不会自动接受、拒绝、应用候选稿，也不会自动写入正式正文。

## 二、完成度矩阵

| 阶段/模块 | 本地状态 | 核验重点 |
|---|---|---|
| P0 AIJob / 设置 / 初始化 / ContextPack / 候选稿 | 完成 | 暂停、恢复、取消、重试与步骤重试均有用户门控 |
| P1 AgentRuntime / Workflow / 剧情轨道 / 方向与计划 / 审阅与记忆门 | 完成 | 四类确认门语义独立，blocked 不伪装 ready |
| P2-01 多章续写 | 完成 | 每章等待作者决定，不自动写正式正文 |
| P2-02 CitationLink | 完成 | 候选稿引用来源可查看、可追溯 |
| P2-03 StyleDNA | 完成 | 提取、确认、历史和启停闭环 |
| P2-04 自动续写队列 | 完成 | 暂停、停止、恢复历史、用户放弃、预算 unknown 暂停 |
| P2-05 @ 引用 | 完成 | 联想、持久化、行内高亮、悬停摘要和失效状态 |
| P2-06 OpeningAgent | 完成 | 方向选择、原创性检查、候选开篇与人工确认 |
| P2-07 大纲辅助 | 完成 | 润色、扩写、续写、导入转换和冲突转交 |
| P2-08 选区改写 | 完成 | 生成、差异查看、编辑、采用/拒绝和历史 |
| P2-09 AI 用量与预算 | 完成 | 调用前后保护、unknown fail-safe、作品/默认设置继承、审计 |
| P2-10 创作分析 | 完成 | 实时/缓存、stale、异步重算、节奏/对白/词频/风格/AI 使用 |
| P2-11 API 集成边界 | 完成 | 服务端与前端统一功能开关，作者偏好实际生效 |
| P2-12 UI 集成 | 完成 | 小白写手用语、可理解状态、设置入口和恢复入口 |

## 三、安全边界

- AI 不自动写正式正文；
- AI 不自动 accept/reject/apply CandidateDraft；
- workflow、agent、system 不得伪造 `user_action`；
- DirectionSelection、PlanConfirmation、HumanReviewGate、MemoryReviewGate 不混用；
- 预算无法判定时保护性阻断或暂停，不显示为可继续；
- 日志不记录完整 Prompt、ContextPack、正文、候选稿或 API Key；
- 修改预算或价格不会自动恢复 Job、Session 或 AutoQueueRun。

## 四、本地验证证据

| 检查 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `pytest -q` | `863 passed, 1 skipped` |
| 前端全量 | `cd frontend; npm test -- --run` | `450 passed` |
| 前端生产构建 | `cd frontend; npm run build` | 通过 |
| 差异检查 | `git diff --check` | 通过（仅 Git 行尾提示） |

跳过项为真实 Provider 联机冒烟；当前环境没有配置 `INKTRACE_SMOKE_PROVIDER`、`INKTRACE_SMOKE_API_KEY`、`INKTRACE_SMOKE_MODEL`。MockTransport、密钥解密与 Provider 适配测试均已通过，但发布前仍需用人工提供的真实测试账号补跑。

## 五、作者文档

- `docs/10_user_guide/InkTrace-小白写手完整操作手册.md`
- `docs/10_user_guide/InkTrace-小白写手完整操作手册.docx`
- `docs/10_user_guide/InkTrace-小白写手完整操作指南.pptx`

## 六、未完成与风险

1. 远端 CI：按任务要求排除，未执行。
2. 真实 Provider 联机冒烟：缺少测试服务密钥，未执行；不得在补跑前宣称真实外部服务已验收。

除上述外，当前没有已知的冻结范围功能性未完成项。

## 七、最终判定

- V2.0 冻结功能代码：完成
- 本地自动化测试：通过
- 前端生产构建：通过
- 小白写手操作文档：完成
- 远端 CI：排除
- 真实 Provider 联机冒烟：待人工提供测试凭据补跑
- 建议：可进入真实 Provider 冒烟与人工验收；完成前不建议直接发布
