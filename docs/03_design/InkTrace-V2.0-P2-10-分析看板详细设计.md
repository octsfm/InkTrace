# InkTrace V2.0-P2-10 分析看板详细设计

版本：v1.3 / P2 模块级详细设计冻结版（小白作者体验与 AI 使用分析裁决）
状态：冻结生效
所属阶段：InkTrace V2.0 P2-S3
设计范围：创作分析看板（写作统计、节奏分析、对白分析、高频词、风格一致性、AI 使用分析）

依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`（R-AI-ENH-05）
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§4.10）
- `docs/03_design/InkTrace-V2.0-P2-03-StyleDNA详细设计.md`（StyleProfile 结构化特征）
- `docs/03_design/InkTrace-V2.0-P1-04-四层剧情轨道详细设计.md`（VolumeArc / SequenceArc 高潮标记）
- `docs/03_design/V2/InkTrace-V2.0-P0-04-StoryMemory与StoryState详细设计.md`（阶段标记 / event_nodes）
- `docs/03_design/InkTrace-V2.0-P2-09-成本看板详细设计.md`（P2-09 已移除 adoption_rate，P2-10 为权威源）

说明：分析看板拆分为两个服务：`AnalysisDashboardQueryService`（纯只读查询）和 `AnalysisMetricRefreshService`（缓存写入，由定时任务或手动触发调用）。所有分析基于已确认章节正文（`Chapter.content`）、StoryMemory 结构化数据、AgentTrace 统计和 CandidateDraft 采纳记录。使用“AI 使用分析”命名，不使用“AI 检测器”，不得判断正文来源。页面面向零基础小说作者，先说可理解的写作现象，再按需展开计算口径。本文档不写代码、不修改源码。

> **路由说明**：本模块路由位于 `/api/v2/ai/analysis-dashboard`，与 P2 其他模块保持一致的前缀约定。但本模块**不触发 LLM 调用、不调用 ModelRouter**，所有分析在本地计算完成。

---

## 一、文档定位与设计范围

### 1.1 数据口径冻结：什么是"已确认章节正文"

P2-10 所有分析指标的**唯一正文数据源**为：

```
Chapter.content（V1.1 正式章节正文）
```

**不读取以下内容**：

| 排除项 | 原因 |
|---|---|
| Workbench 当前草稿（`EditSession` 未保存内容） | 草稿可能频繁变化，不应参与统计分析 |
| CandidateDraft 候选稿正文（`CandidateDraft.content`） | 候选稿未正式确认，不应计入章节统计 |
| SelectionRewriteCandidate 未应用结果 | 同上 |
| 被软删除的章节 | 已删除不应统计 |

**唯一例外**：AI 使用分析的采纳率统计需要读取 `CandidateDraft.status` / `CandidateDraft.applied_at`（元数据），但**不读取 CandidateDraft 正文内容**。

**口径确认**：
- 若系统有 `Chapter.confirmed_at IS NOT NULL` 语义 → 按此过滤已确认章节。
- 若系统无显式 confirmed 标记 → 按 `Chapter.status != 'draft'` 过滤。
- 实现时以 `ChapterRepository` 提供的 `get_confirmed_chapters(work_id)` 方法为准，具体过滤逻辑由 Repository 封装。

### 1.2 核心约束

- **正文/业务对象只读**：不写 `chapters`、`candidate_drafts`、`story_memory` 等业务表。
- **缓存可写**：`AnalysisMetricRefreshService` 写入 `analysis_metrics` 缓存表（派生数据，非创作数据）。
- **不产生新 AI 调用**：所有统计分析在本地完成（正则、计数、聚合），不调用 ModelRouter、Provider 或 embedding 模型。
- **指标结果展示性**：分析看板是**作者自我审阅工具**，所有指标仅供参考，不自动触发操作；可给出基于指标的中性阅读提示，但不得把统计结果包装成确定性写作结论。
- **小白作者优先**：Tab 和卡片先回答“最近章节长短是否稳定、对白多不多、哪些词反复出现、风格是否变化”等写作问题；公式、内部状态和技术名词默认隐藏。

### 1.3 设计范围

| 维度 | 服务方法 | 指标 |
|---|---|---|
| 写作统计 | `get_writing_stats` | 总字数、日均字数、章节字数分布、AI 候选稿采纳次数占比 |
| 节奏分析 | `get_rhythm_analysis` | 章节字数波动、段落长度波动、对白/叙述比例变化、短句密度、章尾钩子粗略统计 |
| 对白分析 | `get_dialogue_analysis` | 对白占比、对白段平均长度、角色对白分布（可选） |
| 高频词 | `get_word_frequency` | Top-N 高频词（排除停用词）、特征词（TF-IDF） |
| 风格一致性 | `get_style_consistency` | 风格漂移指数、一致性评分、章节趋势 |
| AI 使用分析 | `get_ai_usage_analysis` | 候选稿采纳率（次数比）、平均修订轮次、AI 常见词汇频率 |

---

## 二、数据源矩阵

每个维度 → 数据源 → 具体字段的完整映射：

### 2.1 写作统计

| 指标 | 数据源 | 具体字段 |
|---|---|---|
| 总字数 | `chapters` | `Chapter.content` → `len(content)` 或 `Chapter.word_count`（若有预计算字段优先使用） |
| 日均字数 | `chapters` | 总字数 / `(MAX(confirmed_at) - MIN(created_at) + 1天)` |
| 章节字数分布 | `chapters` | 每章 `word_count` / `len(content)`，按 `chapter_index` 排序 |
| AI 候选稿采纳次数占比 | `candidate_drafts` | `COUNT(status='applied' OR applied_at IS NOT NULL) / COUNT(*)`。**注意：P2-S3 做采纳次数占比，不做采纳字数占比**（原因见 §3.1.1） |

### 2.2 节奏分析

| 指标 | 数据源 | 具体字段 |
|---|---|---|
| 章节字数波动 | `chapters` | `Chapter.content` → 每章字数 → 标准差 / 均值 |
| 段落长度波动 | `chapters` | `Chapter.content` → 按 `\n\n` 分段 → 每段字符数 → 标准差 |
| 对白/叙述比例变化 | `chapters` | `Chapter.content` → 对白识别规则（§3.3.1）→ 每章对白比 → 趋势 |
| 短句密度 | `chapters` | `Chapter.content` → 按句末标点（`。！？`）分句 → 短句（≤15 字）占比 |
| 章尾钩子粗略统计 | `chapters` | `Chapter.content` → 最后 3 句的疑问句数、冲突词（"突然""竟然""难道"等）出现数 |
| 高潮事件间隔（可选增强） | `story_memory` | `VolumeArc.climax_description` + `SequenceArc.climax_chapter_estimate` + `SequenceEvent(type="climax")`。无 StoryMemory 数据时此指标不展示 |

### 2.3 对白分析

| 指标 | 数据源 | 具体字段 |
|---|---|---|
| 对白占比 | `chapters` | `Chapter.content` → 对白识别规则（§3.3.1）→ 对白字符 / 总字符 |
| 对白段平均长度 | `chapters` | `Chapter.content` → 含引号的段落 → AVG(段落字符数) |
| 角色对白分布 | `chapters` + `characters` | `Chapter.content` → 说话人归因规则（§3.3.2）+ `characters.name` 匹配 → 按角色聚合。无法归因的计入 `"unknown"` |

### 2.4 高频词

| 指标 | 数据源 | 具体字段 |
|---|---|---|
| Top-N 高频词 | `chapters` | `Chapter.content` → `jieba` 分词 → 过滤停用词（`STOP_WORDS_ZH`）→ 词频排序 |
| 特征词（TF-IDF） | `chapters` | 每章作为一篇文档 → `词频 × log(总章数 / 含该词章数)` |

### 2.5 风格一致性

| 指标 | 数据源 | 具体字段 |
|---|---|---|
| 风格漂移指数 | `style_profiles` + `chapters` | ① 读 `StyleProfile(status=ACTIVE)` 的结构化特征作为基准；② 每章正文本地提取同维度特征；③ 归一化欧氏距离求偏差 |
| 无 StyleProfile 时 | `chapters` | 降级为**纯文本统计特征**：平均句长、对白占比、段落长度、标点密度（`，。！？` 分布）。不调用 embedding，不调用 AI |
| 一致性评分 | 同上 | `1 - drift_index` |
| 章节趋势 | 同上 | 每章 `ChapterStyleSnapshot` 列表 |

### 2.6 AI 使用分析

| 指标 | 数据源 | 具体字段 |
|---|---|---|
| 候选稿采纳率 | `candidate_drafts` | `COUNT(CandidateDraft.status='applied' OR applied_at IS NOT NULL) / COUNT(*)`。**P2-10 是此指标的权威计算方** |
| 平均修订轮次 | `candidate_drafts` | `AVG(CandidateDraft.revision_count)` 或从 `AgentTrace` 聚合 `revision_round` |
| AI 常见词汇频率 | `chapters` | `Chapter.content` → `jieba` 分词 → 与内置 `AI_SIGNAL_WORDS` 词表匹配 → 按章/全作统计出现次数 |

---

## 三、各维度计算方式

### 3.1 写作统计（`get_writing_stats`）

#### 3.1.1 AI 候选稿采纳字数占比的处理

P2-S3 **不做采纳字数占比**，改为**采纳次数占比**：

```
adoption_rate = COUNT(candidate_drafts WHERE status='applied' OR applied_at IS NOT NULL)
              / COUNT(candidate_drafts)
```

**原因**：`candidate_drafts` 表中没有 `applied_word_count` 字段。正文中也没有 AI 来源片段边界标记。采纳字数占比需要更精细的数据支撑（如 CitationLink 中的 `source_candidate_draft_id` + `applied_range`），P2-S3 不具备此条件。

若后续版本需要采纳字数占比，需在 CandidateDraft 或 CitationLink 中补齐以下字段：

| 字段 | 说明 |
|---|---|
| `applied_word_count` | 已应用的字数 |
| `applied_ranges` | 应用位置范围（JSON） |

### 3.2 节奏分析（`get_rhythm_analysis`）

P2-S3 初期聚焦**可纯规则计算**的量化指标，不做强语义 AI 分析。

#### 3.2.1 为什么不做"高潮事件"和"过渡段"

| 指标 | 问题 | P2-S3 策略 |
|---|---|---|
| 高潮事件间隔 | "高潮"是强语义概念，纯规则（词频/句长）无法可靠识别。需要基于 StoryMemory 中的 `event_type=climax` 或人工标注的 EventNode | 作为**可选增强指标**：若作品存在 StoryMemory 且含 `climax` 类型事件节点，则展示；否则该字段为空列表 |
| 过渡段密度 | "过渡段"不是纯粹的段落长度概念——一段 30 字的段落可能是过渡，也可能是冲击性短句。纯规则假阳性率高 | P2-S3 不做。替换为**短句密度**（≤15 字句子占比）和**段落长度波动** |

#### 3.2.2 高潮事件的数据来源（可选增强）

若 StoryMemory 中存在以下数据，`climax_intervals` 可计算：

- `VolumeArc.climax_description`（卷级高潮节点描述）
- `SequenceArc.climax_chapter_estimate`（序列级预估高潮章节号）
- `SequenceEvent` 表中 `event_type = "climax"` 的事件

按 `climax_chapter_estimate` 或高潮事件所在章节号排序，计算相邻间距。此数据由 P1-04（四层剧情轨道）中 Planner Agent 生成，P2-10 只读取。

#### 3.2.3 章尾钩子粗略统计规则

```
1. 取每章正文最后 3 个句子（按 。！？ 分割）。
2. 统计疑问句数（以 ？ 结尾的句子）。
3. 匹配冲突词词表（内置常量 CLIFFHANGER_WORDS）：
   ["突然", "忽然", "竟然", "居然", "难道", "没想到", "出乎意料",
    "就在这时", "猛然", "一下子", "刹那间", "不料", "谁知"]
4. 以"每章匹配数"和"全作均值"作为输出。
```

---

### 3.3 对白分析（`get_dialogue_analysis`）

#### 3.3.1 对白识别规则（P2-S3 冻结）

中文小说对白识别规则，按优先级：

**规则 1（优先）**：中文引号包裹的文本视为对白。
- `"..."`（全角双引号）
- `「...」`（直角引号）
- `『...』`（直角双引号）
- 提取引号内文本 → 计为对白字符。

**规则 2（补充）**：冒号发言格式。
- 正则：`^[^：:]*[：:]\s*["「『]`（行首/段首 说话人 + 冒号 + 引号）
- 此格式已包含引号，不计入规则 1 的重复匹配。

**规则 3（不启用）**：无引号的自由间接引语。
- P2-S3 不做无引号对白识别（如"他想，今天天气真好。"）。

**对白段定义**：包含至少一个中文引号对（规则 1）的段落。

#### 3.3.2 角色对白分布（说话人归因）

P2-S3 说话人归因规则（简化版）：

1. 搜索对白段前后的**明确说话人模式**：`角色名："..."` 或 `角色名说："..."` 或 `角色名道："..."`。
2. 提取的角色名在 `characters` 表中做**模糊匹配**（完全匹配优先，无匹配则尝试 character 的 `aliases` 列表）。
3. 无法匹配任何角色的对白 → 计入 `"unknown"`。
4. 一个对白段可能包含多个角色的对白（交替发言），不做复杂角色分拆——归因给该段第一个匹配到的角色名。

**可选指标声明**：`by_character` 在 API 响应中标注 `"note": "角色归因为启发式匹配，可能存在误差，仅供参考"`。前端展示时附带此提示。

---

### 3.4 高频词（`get_word_frequency`）

#### 3.4.1 分词器与预处理

- **分词器**：`jieba`（默认中文精确模式），作为服务依赖安装（`pip install jieba`）。
- **预处理**：
  1. 移除标点符号、数字、空白字符。
  2. 统一全角/半角（全角字母数字 → 半角）。
  3. 单字词过滤：`len(word) < 2` 的词丢弃。
  4. 停用词过滤：加载内置 `STOP_WORDS_ZH` 常量（≈ 1200 词）。
  5. 敏感模式过滤：匹配 API Key 模式（`sk-*`）、邮箱、URL 的词丢弃。

#### 3.4.2 停用词表

`STOP_WORDS_ZH` 为模块常量，打包在 `analysis_dashboard_constants.py` 中。涵盖：

- 虚词（的、了、在、是、和、与、或、就、都、也、还、把、被、让、给、从、到、对、为、以、之、其、所、者、而、且、但、只、仅、等等）
- 人称代词（我、你、他、她、它、我们、你们、他们）
- 指示代词（这、那、这些、那些、这个、那个）
- 标点与数字

P2-S3 **不支持用户自定义停用词、不支持英文分词**。

#### 3.4.3 参数范围

| 参数 | 默认值 | 范围 | 说明 |
|---|---|---|---|
| `top_n` | 50 | 10~200 | 服务端校验并 clamp |

---

### 3.5 风格一致性（`get_style_consistency`）

#### 3.5.1 计算路径

```
IF StyleProfile(status=ACTIVE) 存在:
  → 以 StyleProfile 的结构化特征为基准向量
  → 基准维度：avg_sentence_length, dialogue_ratio, short_sentence_ratio,
               long_sentence_ratio, avg_paragraph_length, paragraph_length_variance
  → 每章正文本地提取同维度特征（正则/统计，不调用 AI）
  → 各维度 min-max 归一化 → 计算每章与基准的欧氏距离
  → drift_index = AVG(各章归一化距离)，范围 0~1
  → consistency_score = 1 - drift_index

ELSE（无 ACTIVE StyleProfile）:
  → 降级为纯文本统计基线
  → 基线 = 所有章的均值（avg_sentence_length, dialogue_ratio,
             short_sentence_ratio, long_sentence_ratio）
  → 每章与全局均值的偏差
  → API 响应中附带 warning: "no_active_style_profile"
```

**关键约束**：
- **不调用 embedding 模型**。章节风格特征通过本地正则/统计提取。
- **不重新训练风格模型**。基准来自 P2-03 已有的 `StyleProfile`，或降级为全章均值。
- P2-03 的 `StyleProfile` 是用户上传标杆文本后提取的结果，不包含逐章风格特征。P2-10 的 `chapter_trend` 是分析看板独立做的逐章统计。

---

### 3.6 AI 使用分析（`get_ai_usage_analysis`）

#### 3.6.1 候选稿采纳率

```
adoption_rate = COUNT(CandidateDraft WHERE status = 'applied' OR applied_at IS NOT NULL)
              / COUNT(CandidateDraft)
```

- **P2-10 是此指标的权威计算方**（P2-09 已完全移除 `adoption_rate`）。
- 数据源：`candidate_drafts` 表。
- 不做"采纳字数占比"（原因见 §3.1.1）。

#### 3.6.2 平均修订轮次

```
avg_revision_rounds = AVG(CandidateDraft.revision_count)
```

命名修正：原 v1.0 叫"人均修订轮次"，不准确。改为 **"平均修订轮次"**（章节/候选稿维度的平均值）。

数据来源优先级：
1. `CandidateDraft.revision_count`（如果有此字段）。
2. 若无显式字段，从 `agent_traces` 中按 `candidate_draft_id` 聚合 `revision_round` 最大值。

#### 3.6.3 AI 常见词汇频率

词表 `AI_SIGNAL_WORDS` ≈ 80 词（模块常量）。对所有已确认章节正文做 `jieba` 分词后，统计词表中词汇的出现次数。按"全作出现次数"和"出现章数"两个维度展示。

---

## 四、服务拆分

```
AnalysisDashboardQueryService      ← 纯只读查询（读 chapters + story_memory + candidate_drafts + analysis_metrics 缓存）
AnalysisMetricRefreshService       ← 缓存写入（写 analysis_metrics 表，由定时任务/手动触发调用）
```

### 4.1 AnalysisDashboardQueryService

```python
class AnalysisDashboardQueryService:
    """纯只读查询服务。不写任何业务表。读取 analysis_metrics 缓存（大作品）
       或实时计算（小作品）。"""

    def __init__(
        self,
        *,
        chapter_repository,
        candidate_draft_repository,
        story_memory_repository,
        agent_trace_repository,
        style_profile_repository,          # P2-03
        analysis_metric_repository,        # 缓存读取
    ) -> None: ...
    # 注意：不注入 llm_call_log_repository。token/cost 数据归 P2-09 成本看板。
    # P2-10 不读取 llm_call_logs，避免分析看板与成本数据耦合。

    async def get_writing_stats(self, work_id: str) -> WritingStats: ...
    async def get_rhythm_analysis(self, work_id: str) -> RhythmAnalysis: ...
    async def get_dialogue_analysis(self, work_id: str) -> DialogueAnalysis: ...
    async def get_word_frequency(self, work_id: str, *,
                                  top_n: int = 50) -> WordFrequencyResult: ...
    async def get_style_consistency(self, work_id: str) -> StyleConsistencyResult: ...
    async def get_ai_usage_analysis(self, work_id: str) -> AIUsageAnalysis: ...
```

### 4.2 AnalysisMetricRefreshService

```python
class AnalysisMetricRefreshService:
    """缓存写入服务。由定时任务或手动触发调用。只写 analysis_metrics 表（派生数据）。"""

    def __init__(
        self,
        *,
        chapter_repository,
        candidate_draft_repository,
        story_memory_repository,
        agent_trace_repository,
        style_profile_repository,
        analysis_metric_repository,        # 缓存读写
        query_service,                      # AnalysisDashboardQueryService（复用实时计算方法）
    ) -> None: ...

    async def recompute_all(self, work_id: str) -> None: ...
    async def recompute_stale(self, work_id: str) -> None: ...
    async def mark_stale(self, work_id: str,
                          metric_types: list[str] | None = None) -> None: ...
```

### 4.3 返回结构（与 v1.1 一致，略）

所有返回结构（`WritingStats`、`RhythmAnalysis`、`DialogueAnalysis`、`WordFrequencyResult`、`StyleConsistencyResult`、`AIUsageAnalysis` 及子结构）继承 v1.1 §2.2 定义。唯一变更：`WritingStats` 中 `ai_adopted_word_ratio` 改为 `ai_adoption_rate`（次数比替代字数比）。

---

## 五、计算策略：实时 vs 批量

### 5.1 阈值与切换

| 作品规模 | 策略 | 触发条件 |
|---|---|---|
| ≤ 30 万字 | **实时计算** | 每次 API 请求时即时统计 |
| > 30 万字 | **读取缓存** | API 请求读 `analysis_metrics` 表；计算由 `AnalysisMetricRefreshService` 异步执行 |

切换为**单向**（进入批量后不降级）。阈值默认 `300000`，可从配置读取。

### 5.2 缓存过期策略（stale 标记）

`stale = TRUE` 的判定规则：**`work.updated_at > metric.computed_at`**。

简化实现：当作品发生以下任一事件时，该作品的所有 `analysis_metrics` 行的 `stale` 置为 `TRUE`：

| 事件 | 触发方 | 影响范围 |
|---|---|---|
| 章节正文保存/确认 | ChapterService | 该 work_id 全部指标 |
| 章节新增/删除/重排 | ChapterService | 该 work_id 全部指标 |
| StoryMemory 更新 | StoryMemoryService | 该 work_id 全部指标 |
| StyleProfile 确认/变更/禁用 | StyleDNAExtractionService | 仅 `style_consistency` 指标 |
| CandidateDraft apply | CandidateDraftService | 仅 `ai_usage` 指标 |
| 作品元数据变更（updated_at 更新） | WorkService | 该 work_id 全部指标 |

**调用路径**：各业务服务在完成写操作后，调用 `AnalysisMetricRefreshService.mark_stale(work_id)`。

### 5.3 批量计算任务机制

P2-10 **不新增 AIJob**，不依赖 P0 AIJobSystem。

| 触发方式 | 说明 |
|---|---|
| **手动刷新** | `POST /api/v2/ai/analysis-dashboard/recompute?work_id=` → 异步启动 `AnalysisMetricRefreshService.recompute_all(work_id)` → 返回 `202 Accepted` + `{ estimated_seconds }` |
| **应用启动检查** | `AnalysisMetricRefreshService` 在启动时扫描 `stale=TRUE` 的大作品（>30万字），异步触发 `recompute_stale` |
| **定时任务（可选）** | 若项目有 cron/调度器，可每日凌晨对 `stale=TRUE` 的大作品执行 `recompute_stale`。不是必须——手动刷新 + 启动检查已覆盖主要场景 |

**前端行为**：
- 小作品（≤30万字）：API 请求时实时计算，`stale` 永远为 `FALSE`。
- 大作品（>30万字）：API 请求返回缓存数据。若 `stale=TRUE`，前端展示旧数据 + 提示："部分数据可能已过期，[点击刷新]"。用户点击后前端调用 `POST /recompute` → 轮询 `GET /status` 等待完成 → 重新拉取数据。

### 5.4 API 响应统一包装

所有 `/analysis-dashboard` 端点返回统一外层结构：

```json
{
  "source": "realtime | cached",
  "computed_at": "2025-06-09T03:00:00+08:00",
  "stale": false,
  "data": { ... }
}
```

| 字段 | 说明 |
|---|---|
| `source` | `"realtime"` = 本次实时计算；`"cached"` = 读取 `analysis_metrics` 缓存 |
| `computed_at` | 数据计算时间（缓存模式 = 缓存写入时间；实时模式 = 本次请求时间） |
| `stale` | 缓存是否过期（实时模式下永远 `false`） |
| `data` | 各端点的业务数据（与 v1.1 各维度返回结构一致） |

---

## 六、领域模型

### 6.1 AnalysisMetric 结构

```python
@dataclass
class AnalysisMetric:
    metric_id: str                        # 主键，格式 `am_{uuid_hex_12}`
    work_id: str                          # 作品 ID
    metric_type: str                      # 枚举：writing_stats / rhythm_analysis / dialogue_analysis / word_frequency / style_consistency / ai_usage
    metric_name: str                      # 人类可读名称
    metric_payload_json: str              # 复合值（JSON 字符串），schema 见 §6.2
    chapter_range_from: int               # 统计起始章节号（默认 1）
    chapter_range_to: int | None          # 统计结束章节号（None = 到最新章）。用于批量分片元数据
    source_revision: int                  # 数据源版本号（每次重算递增），默认 0
    computed_at: str                      # 计算时间（ISO 8601）
    stale: bool                           # 是否过期
```

### 6.2 metric_payload_json schema

| metric_type | payload 内容（JSON schema） |
|---|---|
| `writing_stats` | `{ total_word_count, daily_avg_words, chapter_word_counts: [{chapter_id, chapter_index, title, word_count}], ai_adoption_rate, total_chapters, active_days }` |
| `rhythm_analysis` | `{ chapter_word_count_std, avg_paragraph_length, paragraph_length_std, dialogue_ratio_trend: [float], short_sentence_density, cliffhanger_stats: {per_chapter: [{chapter_id, question_count, conflict_word_count}]}, climax_intervals: [...] }` |
| `dialogue_analysis` | `{ dialogue_ratio, avg_dialogue_length, by_character: {name: {dialogue_chars, dialogue_ratio, chapter_count}}, unknown_ratio }` |
| `word_frequency` | `{ words: [{word, frequency, tfidf_score}], total_unique_words, stop_words_removed }` |
| `style_consistency` | `{ drift_index, consistency_score, chapter_trend: [{chapter_id, chapter_index, avg_sentence_length, dialogue_ratio, deviation_from_baseline}], baseline_source: "style_profile" | "chapter_mean", warning: null | "no_active_style_profile" }` |
| `ai_usage` | `{ adoption_rate, avg_revision_rounds, ai_word_frequency: [{word, chapter_count, total_occurrences}], total_candidates, total_adopted }` |

### 6.3 analysis_metrics 表 DDL

```sql
CREATE TABLE IF NOT EXISTS analysis_metrics (
    metric_id            TEXT PRIMARY KEY,
    work_id              TEXT NOT NULL,
    metric_type          TEXT NOT NULL CHECK(metric_type IN (
                            'writing_stats','rhythm_analysis','dialogue_analysis',
                            'word_frequency','style_consistency','ai_usage')),
    metric_name          TEXT NOT NULL,
    metric_payload_json  TEXT NOT NULL DEFAULT '{}',
    chapter_range_from   INTEGER DEFAULT 1,
    chapter_range_to     INTEGER,
    source_revision      INTEGER DEFAULT 0,
    computed_at          TEXT NOT NULL,
    stale                INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_analysis_metrics_work
    ON analysis_metrics(work_id, metric_type);

CREATE INDEX IF NOT EXISTS idx_analysis_metrics_stale
    ON analysis_metrics(work_id, stale);
```

---

## 七、API 设计

路由前缀：`/api/v2/ai/analysis-dashboard`

> 路由位于 `/api/v2/ai` 下以保持 P2 模块统一前缀。但本模块不触发 LLM 调用。

```
GET  /api/v2/ai/analysis-dashboard/overview?work_id=
  Response: { source, computed_at, stale,
              data: { total_word_count, daily_avg_words, chapter_word_counts,
                      ai_adoption_rate, total_chapters, active_days } }

GET  /api/v2/ai/analysis-dashboard/rhythm?work_id=
  Response: { source, computed_at, stale,
              data: { chapter_word_count_std, avg_paragraph_length,
                      paragraph_length_std, dialogue_ratio_trend,
                      short_sentence_density, cliffhanger_stats,
                      climax_intervals } }

GET  /api/v2/ai/analysis-dashboard/dialogue?work_id=
  Response: { source, computed_at, stale,
              data: { dialogue_ratio, avg_dialogue_length,
                      by_character, unknown_ratio,
                      note: "角色归因为启发式匹配，可能存在误差，仅供参考" } }

GET  /api/v2/ai/analysis-dashboard/word-frequency?work_id=&top_n=50
  Response: { source, computed_at, stale,
              data: { words: [{ word, frequency, tfidf_score }],
                      total_unique_words, stop_words_removed } }

GET  /api/v2/ai/analysis-dashboard/style?work_id=
  Response: { source, computed_at, stale,
              data: { drift_index, consistency_score,
                      chapter_trend: [...],
                      baseline_source, warning } }

GET  /api/v2/ai/analysis-dashboard/ai-usage?work_id=
  Response: { source, computed_at, stale,
              data: { adoption_rate, avg_revision_rounds,
                      ai_word_frequency, total_candidates, total_adopted } }

POST /api/v2/ai/analysis-dashboard/recompute?work_id=
  Description: 手动触发异步重算。仅大作品（>30万字）有意义；小作品返回 400。
  Response: 202 { accepted: true, work_id, estimated_seconds }

GET  /api/v2/ai/analysis-dashboard/recompute/status?work_id=
  Description: 查询重算任务状态。P2-S3 使用进程内任务状态缓存，不持久化。
              应用重启后 running 状态丢失，前端可重新触发 recompute。
              进度按 6 个 metric_type 的完成数计算（progress = completed_count / 6）。
  Response: { status: "idle | running | completed | failed", progress: 0.0~1.0 }
```

---

## 八、与 P2-09 的数据一致性

| 指标 | P2-09 成本看板 | P2-10 分析看板 | 说明 |
|---|---|---|---|
| `adoption_rate` | ❌ 已移除（v1.2） | ✅ 权威计算方 | `candidate_drafts` 直接聚合 |
| `total_tokens` | ✅ 权威计算方 | ❌ 不涉及 | `llm_call_logs` |
| `avg_revision_rounds` | ❌ 不涉及 | ✅ 权威计算方 | `candidate_drafts.revision_count` |

**原则**：每个指标只有一个权威计算方。

---

## 九、安全边界

| 约束 | 实施 |
|---|---|
| 正文/业务对象只读 | `AnalysisDashboardQueryService` 只读查询，不写 `chapters` / `candidate_drafts` / `story_memory` 等业务表 |
| 缓存可写 | `AnalysisMetricRefreshService` 写入 `analysis_metrics` 表（派生数据，非创作数据） |
| 不基于 AI 使用分析自动修改正文/Prompt | 纯展示，不做自动处罚或自动优化 |
| 仅分析已确认章节 | 数据源为 `Chapter.content`（正式章节正文），不读取 CandidateDraft 正文、Workbench 草稿 |
| 高频词不包含敏感词 | 停用词 + API Key / 邮箱 / URL 模式过滤 |
| 不产生新 AI 调用 | 所有分析在本地完成（正则、`jieba`、计数、聚合），不调用 ModelRouter / Provider / embedding |
| AI 词汇统计不标注"AI 生成嫌疑" | 仅统计频率，不做判断性标注 |
| 角色归因带误差提示 | `by_character` 响应中附带 `note` 字段 |

---

## 十、前端 AnalysisDashboard.vue 设计概要

### 10.1 页面定位

独立路由页面，从设置导航或写作工作室"分析"入口跳转进入。

### 10.2 主要区块（Tab 切换布局）

```
┌──────────────────────────────────────────────────────────────┐
│  📊 创作分析看板                [缓存] 更新于: 06-09 03:00   │
│  ─────────────────────────────────────────────────────────── │
│  ⚠️ 部分数据可能已过期（有新章节未纳入统计），[点击刷新]     │
│                                                              │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ 写作统计 │ 节奏分析 │ 对白分析 │  高频词  │ 风格一致性│   │
│  │          │          │          │          │          │   │
│  │ 总字数   │ 字数波动 │ 对白占比 │ Top-50   │ 漂移指数 │   │
│  │ 采纳率   │ 段长波动 │ 角色分布 │ 特征词   │ 章节趋势 │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│                                                              │
│  ┌─ [AI 使用分析] Tab ───────────────────────────────────┐  │
│  │ 采纳率: 68%  |  均修订轮次: 1.2  |  候选稿: 45 篇    │  │
│  │                                                        │  │
│  │ AI 常见词汇（仅统计，非判断）:                         │  │
│  │ "值得注意的是" ████░░ 12次 / 8章                       │  │
│  │ "总而言之"     ███░░░ 9次 / 6章                        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 10.3 关键交互

| 交互 | 说明 |
|---|---|
| Tab 切换 | 六个维度通过水平 Tab 切换，默认显示"写作统计" |
| 过期提示 | `stale=true` 时顶部显示黄色提示条 + "点击刷新"按钮（仅大作品可用） |
| 缓存标识 | `source="cached"` 时右上角显示"缓存"标签 + 计算时间 |
| 手动刷新 | 仅大作品可用。调用 `POST /recompute` → 轮询状态 → 重新拉取 |
| 空状态 | 无 StyleProfile 时风格一致性 Tab 仍展示降级版结果（基于全书文本统计），顶部显示提示："尚未配置风格画像，当前结果基于全书文本统计，仅供参考。[前往配置 StyleDNA]"；作品无已确认章节时显示"暂无足够数据分析" |
| 角色归因提示 | 对白分析的角色分布旁显示 `info` 图标 + tooltip："角色归因为启发式匹配，可能存在误差" |
| 导出 | P2-S3 不提供导出功能 |

---

## 十一、代码改动面

```
新增：
  application/services/ai/analysis_dashboard_query_service.py     # AnalysisDashboardQueryService
  application/services/ai/analysis_metric_refresh_service.py      # AnalysisMetricRefreshService
  application/services/ai/analysis_dashboard_constants.py         # STOP_WORDS_ZH, AI_SIGNAL_WORDS, CLIFFHANGER_WORDS
  domain/entities/ai/analysis_entities.py                         # AnalysisMetric + 各维度返回结构
  domain/repositories/ai/analysis_metric_repository.py            # AnalysisMetricRepository (ABC)
  infrastructure/persistence/sqlite_analysis_metric_repo.py       # SqliteAnalysisMetricRepository
  presentation/api/routers/v2/ai/analysis_dashboard.py            # /api/v2/ai/analysis-dashboard/*
  frontend/src/views/AnalysisDashboard.vue

修改：
  presentation/api/app.py                                         # 注册路由

需修改（stale 触发方）：
  application/services/v1/chapter_service.py                      # 章节保存/确认后调用 mark_stale
  application/services/ai/style_dna_extraction_service.py         # StyleProfile 变更后调用 mark_stale
  # 或通过事件/钩子解耦，避免循环依赖。具体方案由实现阶段决定
```

---

## 附录：v1.1 → v1.2 变更摘要

| # | 变更 | 原因 |
|---|---|---|
| 1 | 新增 §1.1 数据口径冻结："已确认章节正文" = `Chapter.content`，排除 CandidateDraft 正文、Workbench 草稿 | 消除"已确认章节"的歧义 |
| 2 | 新增 §2 完整数据源矩阵（每维度 × 每指标 × 源表 × 源字段） | 原文档只有泛化描述 |
| 3 | §3.1.1 "采纳字数占比" → "采纳次数占比"，附原因 + 后续补字段建议 | `candidate_drafts` 无 `applied_word_count`，字数占比不可实现 |
| 4 | §3.6.2 "人均修订轮次" → "平均修订轮次" | "人均"说法不准确，应为章节/候选稿维度的平均值 |
| 5 | §3.5.1 风格一致性计算路径：有 StyleProfile → 用其特征；无 → 降级为全章均值文本统计。不调 embedding | 清除"风格向量从哪里来"的不确定性 |
| 6 | §3.3.1 对白识别规则冻结（3 级优先级 + 繁体引号覆盖），§3.3.2 说话人归因简化规则 + `unknown` 兜底 | 原文档只有指标名无识别规则 |
| 7 | §3.2 节奏分析重构：高潮事件 → 可选增强（需 StoryMemory 数据）；过渡段 → 替换为短句密度/段长波动/章尾钩子 | "高潮""过渡段"纯规则不可靠，改为可量化指标 |
| 8 | §5.2 缓存过期：`work.updated_at > metric.computed_at → stale=true`，附 6 种事件触发 stale 的表 | 原文档有 stale 字段无过期判定规则 |
| 9 | §5.3 批量任务 3 种触发方式（手动刷新/启动检查/定时任务），不新增 AIJob | 原文档只写"每日批量计算"无机制 |
| 10 | §5.4 API 响应统一包装 `{source, computed_at, stale, data}` | 前端需要知道缓存状态 |
| 11 | §4 服务拆分为 AnalysisDashboardQueryService + AnalysisMetricRefreshService | 解决"纯只读"与"写缓存"的语义冲突（与 P2-09 同模式） |
| 12 | §6.3 DDL 保留（v1.1 已补），#14 的问题已在 v1.1 解决 | — |
| 13 | #9 AnalysisMetric 复合值问题已在 v1.1 通过 `metric_payload_json TEXT` 解决 | — |
| 14 | §7 API 路由前缀注释："位于 /api/v2/ai 下但本模块不触发 LLM 调用" | 避免读者误以为 `/ai/` 前缀 = 有 AI 调用 |
| 15 | #15 已在文档头部的"路由说明"块处理 | — |
