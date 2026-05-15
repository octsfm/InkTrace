# InkTrace V2.0-P1 实施唯一依据清单

版本：v1.0 / P1 实施治理清单  
状态：生效  
所属阶段：InkTrace V2.0 P1  
用途：约束实现阶段“只按冻结设计开发”，防止偏离、脑补和越界实现

## 一、生效规则（强制）

1. P1 实现阶段唯一设计依据为本清单列出的**无后缀正式文档**。  
2. 所有 `_001.md` 文件仅为历史合并来源或草稿来源，**不得**作为实现依据。  
3. 当无后缀文档与 `_001.md` 存在冲突时，以无后缀文档为准。  
4. 实现、联调、测试、验收、评审均以本清单为检查基线。  
5. 若需要新增/改动规则，必须先更新正式文档，再进入代码实现。

## 二、P1 正式依据文档（无后缀）

1. `docs/03_design/InkTrace-V2.0-P1-详细设计总纲.md`
2. `docs/03_design/InkTrace-V2.0-P1-01-AgentRuntime详细设计.md`
3. `docs/03_design/InkTrace-V2.0-P1-02-AgentWorkflow详细设计.md`
4. `docs/03_design/InkTrace-V2.0-P1-03-五Agent职责与编排详细设计.md`
5. `docs/03_design/InkTrace-V2.0-P1-04-四层剧情轨道详细设计.md`
6. `docs/03_design/InkTrace-V2.0-P1-05-方向推演与章节计划详细设计.md`
7. `docs/03_design/InkTrace-V2.0-P1-06-多轮CandidateDraft迭代详细设计.md`
8. `docs/03_design/InkTrace-V2.0-P1-07-AISuggestion详细设计.md`
9. `docs/03_design/InkTrace-V2.0-P1-08-ConflictGuard详细设计.md`
10. `docs/03_design/InkTrace-V2.0-P1-09-StoryMemoryRevision与MemoryReviewGate详细设计.md`
11. `docs/03_design/InkTrace-V2.0-P1-10-AgentTrace与可观测性详细设计.md`
12. `docs/03_design/InkTrace-V2.0-P1-11-API与前端集成边界详细设计.md`
13. `docs/03_design/InkTrace-V2.0-P1-UI-界面与交互设计.md`
14. `docs/03_design/InkTrace-DESIGN.md`

## 三、实现前必查项（执行清单）

1. 是否已读取对应模块的无后缀正式文档。  
2. 是否提取并遵守门控边界（user_action / caller_type / idempotency_key）。  
3. 是否提取并遵守状态机与终态约束（含 ignored_late_result / duplicate_ignored）。  
4. 是否提取并遵守权限边界（agent 不得 formal_write，不得伪造 user_action）。  
5. 是否提取并遵守安全边界（不泄露 Prompt/ContextPack/API Key/完整正文）。  
6. 是否确认未引入 P2 能力（自动队列、streaming、自动修复、分析看板等）。

## 四、术语统一（实现口径）

1. `CandidateDraft`：候选稿容器。  
2. `CandidateDraftVersion`：候选稿具体版本。  
3. `accept`：用户认可，不等于 `apply`。  
4. `apply`：用户明确应用到章节草稿区。  
5. `reject`：用户拒绝，不自动删除历史记录。  
6. `HumanReviewGate / ConflictGuard / MemoryReviewGate`：三个独立门控，不得混用。

## 五、例外处理机制

1. 若实现阶段发现正式文档冲突，必须暂停实现并提交“文档冲突单”。  
2. 冲突未在正式文档中修订前，不得以临时口头结论推进代码。  
3. 所有例外必须可追踪到正式文档更新记录。

