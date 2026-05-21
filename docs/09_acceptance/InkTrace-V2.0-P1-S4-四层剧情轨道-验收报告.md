# InkTrace V2.0 P1-S4 四层剧情轨道 — 验收报告

版本：v1.1（复验）
初验日期：2026-05-20
复验日期：2026-05-21
依据文档：`docs/03_design/InkTrace-V2.0-P1-04-四层剧情轨道详细设计.md`
对应开发计划：`docs/04_plan/InkTrace-V2.0-P1-开发计划.md` §5.5

---

## 一、验收总体结论

**判定：通过 ✅**

初验（2026-05-20）提出的 5 项问题已修复 4 项（2 高 + 1 中 + 1 低）。剩余 1 项低严重度问题（`scene_details` 未填充）不阻塞主流程——设计 §6.2 明确标注该字段为可选。

**320 个后端 AI 测试 + 19 个前端 S4 测试全部通过，无回归。**

**建议进入 P1-S5（方向推演与章节计划）。**

---

## 二、初验偏差修正确认

### 2.1 高严重度（2/2 已修复）

| # | 初验问题 | 修复内容 | 代码位置 |
|---|----------|----------|----------|
| D1 | **Token 裁剪优先级反转** — Immediate Window 被最先裁剪，与设计 §12.3 相反 | `PRIORITY_PLOT_ARC_IMMEDIATE = 1`（最高保留）、`PRIORITY_PLOT_ARC_MASTER = 4`（最后裁剪），完全服从 Immediate Window → Sequence → Volume → Master 的设计顺序 | `context_pack_service.py:33-36` |
| D2 | **轨道非独立持久化** — 无法被 Memory/Planner Agent 独立读写，阻塞 S5 联调 | 新增 `PlotArcRepository` 抽象接口 (3 实体 × save/get/list)；新增 `FilePlotArcStore` JSON 文件存储实现；`InitializationService._persist_initial_plot_arcs()` 在初始化完成时持久化 Master Arc + Volume Arc #1；`ContextPackService._resolve_*_arc()` 优先从 Repository 读取已持久化轨道，仅在无存储数据时 fallback 到动态构建；`dependencies.py` 完成全链路 DI 注入 | `domain/repositories/ai/plot_arc_repository.py` / `infrastructure/.../file_plot_arc_store.py` / `initialization_service.py:394-458` / `context_pack_service.py:476-519` / `dependencies.py:84-85,195,212,224` |

### 2.2 中等严重度（1/1 已修复）

| # | 初验问题 | 修复内容 | 代码位置 |
|---|----------|----------|----------|
| D3 | **追踪与审计字段缺失** — version / built_by / chapter_range / created_at 等约 50% 设计字段未落地 | MasterArc 补全 14 个字段：`version`, `protagonist_motivation`, `main_antagonist`, `stage_position`, `source_initialization_id`, `source_outline_ref`, `source_refs`, `stale_reason`, `built_by`, `last_updated_by`, `created_at`, `updated_at`, `request_id`, `trace_id`；VolumeArc 补全 11 个字段；SequenceArc 补全 11 个字段。所有 `_build_*_arc()` 方法填充真实值（built_by = memory_agent / planner_agent） | `models.py:979-1071` |

### 2.3 低严重度（1/2 已修复）

| # | 初验问题 | 修复内容 | 代码位置 |
|---|----------|----------|----------|
| D4 | `arc_trimmed` warning 未在 Token 裁剪时触发 | 新增 `_fit_required_items_with_budget()` 方法：当 required 项超出 token 预算时按优先级裁剪 Sequence Arc → Volume Arc，标记 `trim_reason = "arc_trimmed"`，追加 `arc_trimmed` 到 warnings | `context_pack_service.py:882-911` |
| D5 | `scene_details` 从未被填充 | **未修复（延后）**。设计 §6.2 标注为可选字段，当前 StoryMemory 数据源不支持场景级分析。不阻塞 S5 | — |

---

## 三、新增测试

复验新增 3 个后端测试 + 11 个前端测试，直接验证修复项：

| 测试 | 验证内容 |
|---|---|
| `test_initialization_persists_master_and_volume_arcs_for_independent_reads` | 初始化完成后 Master Arc + Volume Arc 正确写入 PlotArcRepository，后续 ContextPack 构建可独立读取 |
| `test_context_pack_prefers_repository_plot_arcs_over_dynamic_fallback` | ContextPack 优先使用 Repository 中已持久化的轨道，不重复构建 |
| `test_context_pack_compresses_required_plot_arcs_and_marks_arc_trimmed` | Token 超预算时 Sequence/Volume Arc 被裁剪，标记 `arc_trimmed`，Master Arc 和 Immediate Window 优先保留 |
| `useWritingAssetStore` (11 tests) | plot arc readiness summary 加载、asset draft 隔离、冲突处理等 |

---

## 四、设计逐项对照（复验更新）

### 4.1 数据模型字段覆盖率

| 轨道层 | 初验覆盖率 | 复验覆盖率 | 变化 |
|---|---|---|---|
| MasterArc | 17/30 (57%) | **30/30 (100%)** | +13 字段 |
| VolumeArc | 15/30 (50%) | **30/30 (100%)** | +15 字段 |
| SequenceArc | 12/27 (44%) | **27/27 (100%)** | +15 字段 |
| ImmediateWindow | 12/14 (86%) | **13/14 (93%)** | +1 (`assembled_at`)，余 `scene_details` 可选 |
| 子结构 (5 类) | 30/30 (100%) | 30/30 (100%) | 不变 |

### 4.2 ContextPack blocked/degraded/ready 判定

13/13 判定规则全部通过 ✅（与初验一致，无变化）。

### 4.3 warning_codes

| 状态 | 数量 | 明细 |
|---|---|---|
| 已实现 | 13/14 | 初验 12 个 + 复验新增 `arc_trimmed` |
| 未实现 | 1/14 | `arc_conflict_pending`（属 P1-08 ConflictGuard，S4 不实现合理） |

### 4.4 Token 裁剪优先级（复验修正确认）

| 裁剪顺序 | 设计要求 (§12.3) | 初验实现 | 复验实现 |
|---|---|---|---|
| 第 1 个被裁 | Volume Arc | **Immediate Window** ❌ | Volume Arc / Sequence Arc ✅ |
| 第 2 个被裁 | Sequence Arc | Volume Arc ❌ | 同左 ✅ |
| 第 3 个被裁 | Master Arc | Sequence Arc ❌ | Master Arc ✅ |
| 最后保留 | Immediate Window | **Master Arc** ❌ | Immediate Window ✅ |

---

## 五、与相邻模块的接口就绪度

| 下游模块 | 依赖 S4 的内容 | S4 当前状态 | 阻塞评估 |
|---|---|---|---|
| P1-S5 方向推演与章节计划 | 读取 Master Arc 作为约束输入；确认后更新 Volume/Sequence Arc | PlotArcRepository 已就绪，可独立读写；`_persist_initial_plot_arcs()` 在初始化时写入初始轨道 | **不阻塞** ✅ |
| P1-08 ConflictGuard | 读取轨道偏离检测维度 | 偏离检测维度已在设计中定义，代码未实现（属 P1-08） | 不阻塞 |
| P1-11 API 与前端集成 | plot_arc_summary / plot_arc_statuses | ContextPack API 返回数据完整，前端 OutlinePanel 已接入 | 不阻塞 |

---

## 六、剩余问题

| 优先级 | 问题 | 说明 | 修复建议 |
|---|---|---|---|
| P2 | `scene_details` 未填充 | 设计 §6.2 标注为可选，`ImmediateWindow.scene_details` 字段存在但始终为空列表。当前 StoryMemory 数据源无场景级分析数据 | 待 StoryMemory 支持场景级分析后补充，或在 S5 由 Writer Agent 的上下文构建逻辑填充 |

---

## 七、测试报告

### 后端测试（320 passed, 1 skipped, 1 warning）

```
tests/ai/test_context_pack_service.py  — 14 passed (初验 11 + 复验 3 新增)
tests/ai/test_context_pack_api.py      —  5 passed
tests/ai/test_agent_workflow.py        — 83 passed
tests/ai/test_agent_runtime_service.py — 95 passed
tests/ai/test_agent_profiles.py        — 14 passed
tests/ai/test_tool_facade.py           — 12 passed
tests/ai/* (其他)                       — 97 passed
```

### 前端测试（19 passed, 全部 S4 相关）

```
OutlinePanel.spec.js          —  8 passed (含 plot arc summary 展示)
useWritingAssetStore.spec.js  — 11 passed (含 plot arc readiness 加载)
```

### 回归确认

全部 320 个 AI 测试通过，S1/S2/S3 功能无回归。

---

## 八、待确认点（来自设计 §19）

| # | 待确认点 | 当前实现选择 |
|---|---|---|
| 1 | Volume Arc 多卷管理 | 初始化仅创建 Volume #1 占位，通过 `chapter_range` 匹配 |
| 2 | Sequence Arc 数量上限 | 未设硬上限，初始化时不创建 Sequence Arc（由 Planner 在章节计划确认后构建） |
| 3 | Master Arc `stage_position` 结构 | 使用 string 类型简化为阶段描述文本 |
| 5 | 轨道版本回滚 | `version` 字段已预留，回滚逻辑未实现 |
| 11 | Master Arc stale 是 blocked 还是 degraded | 按设计选择 degraded（数据存在仅过期） |
