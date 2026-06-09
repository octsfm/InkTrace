# InkTrace V2.0-P2-03 Style DNA 详细设计

版本：v1.0 / P2 模块级详细设计候选冻结版
状态：候选冻结
所属阶段：InkTrace V2.0 P2-S1
设计范围：文风指纹提取与应用系统

依据文档：

- `docs/01_requirements/InkTrace-V2.0-需求规格说明书.md`（R-AI-ENH-01）
- `docs/02_architecture/InkTrace-V2.0-P2-架构设计说明书.md`（§4.3）
- `docs/03_design/V2/InkTrace-V2.0-P0-06-ContextPack详细设计.md`
- `docs/03_design/V2/InkTrace-V2.0-P0-04-StoryMemory与StoryState详细设计.md`

说明：本文档冻结 Style DNA 子系统设计。StyleProfile 是**独立 P2 子域对象**，被 StoryMemory 和 ContextPack **引用**，不混入 StoryMemory 主体。本文档不写代码、不修改源码、不生成数据库迁移。

---

## 一、文档定位与设计范围

### 1.1 文档定位

本文档是 InkTrace V2.0-P2 的第三篇模块级详细设计文档，仅覆盖 Style DNA（文风指纹）子系统。

P2-03 的目标是冻结：用户如何上传/指定标杆文本、系统如何复用 Memory Extraction 能力提取文风特征、StyleProfile 的数据结构与状态机、如何进入 ContextPack 可选层（最低优先级）、低置信度场景的处理策略。

### 1.2 设计范围

本模块覆盖：

- StyleProfile 领域模型与状态机（5 状态）。
- StyleDNAExtractionService（Application 层，直接调用 ModelRouter，不走 Agent Runtime）。
- 与 Memory Extraction 能力复用（Prompt 模板思路 + model_role，不启动 Agent Runtime）。
- ContextPack 集成（可选层，Token 不足时首批裁剪）。
- 低置信度场景（标杆文本 < 500 字）的处理规则。
- Repository 接口与持久化。
- API 端点与 DTO。
- 前端配置页。
- 测试策略与安全边界。

### 1.3 不覆盖范围

- Memory Extraction 内部 Prompt 设计细节（属于 Prompt Registry）。
- ContextPack 组装核心逻辑（属于 P0-06）。
- StoryMemory / StoryState 主体设计（属于 P0-04）。
- 本章不涉及 Citation Link / 自动续写队列。

---

## 二、领域模型

### 2.1 StyleProfileSourceType 枚举

```python
class StyleProfileSourceType(StrEnum):
    USER_UPLOAD = "user_upload"        # 用户上传标杆文本
    CHAPTER_REFERENCE = "chapter_reference"  # 从已有章节指定
    MANUAL = "manual"                  # 手动输入描述
```

### 2.2 StyleProfileStatus 枚举

```python
class StyleProfileStatus(StrEnum):
    PENDING_CONFIRM = "pending_confirm"  # extract 完成后进入此状态，等待用户确认
    ACTIVE = "active"                    # 用户已确认，当前生效（可进入 ContextPack）
    DISABLED = "disabled"                # 用户手动关闭
    ARCHIVED = "archived"                # 已被新版本取代
    DRAFT = "draft"                      # 保留状态：未来用于"保存未完成提取草稿"或"手动编辑风格画像"。P2-03 暂不使用

# extract → PENDING_CONFIRM → (confirm) → ACTIVE
# DRAFT 仅为扩展预留，P2-03 不通过任何路径进入此状态
```

状态流转规则（P2-03）：

```
extract → PENDING_CONFIRM ──(用户确认)──→ ACTIVE ──(用户禁用)──→ DISABLED
                │                               │
                │                               └──(新版本取代)──→ ARCHIVED
                │
                └──(用户拒绝/删除)──→ [软删除: ARCHIVED]
```

**只有 `status = active` 的 StyleProfile 才进入 ContextPack 可选层。**

### 2.3 StyleProfile

| 字段 | 类型 | 说明 |
|---|---|---|
| profile_id | str | 主键，格式 `sp_{uuid_hex_12}` |
| work_id | str | 作品 ID |
| source_type | StyleProfileSourceType | 来源 |
| source_ref | str | 来源引用（章节 ID / 上传文件引用） |
| source_text_hash | str | 标杆文本 SHA256（用于校验完整性，不可逆推原文） |
| source_text_length | int | 标杆文本字数 |
| confidence | float | 置信度（0-1），< 0.5 时为低置信度 |
| low_confidence_reason | str | 低置信度原因（"source_text_too_short" 等） |
| **词频特征** | | |
| avg_sentence_length | float | 平均句长（字符数） |
| sentence_length_variance | float | 句长方差 |
| **句式特征** | | |
| short_sentence_ratio | float | 短句占比（≤10字） |
| long_sentence_ratio | float | 长句占比（≥50字） |
| compound_sentence_ratio | float | 复合句占比 |
| **段落节奏** | | |
| avg_paragraph_length | float | 平均段长（字符数） |
| paragraph_length_variance | float | 段长方差 |
| **内容特征** | | |
| dialogue_ratio | float | 对白占比 |
| psychological_ratio | float | 心理描写占比 |
| action_ratio | float | 动作描写占比 |
| description_ratio | float | 环境描写占比 |
| **叙事特征** | | |
| narrative_perspective | str | first_person / third_person_limited / omniscient |
| tense_preference | str | past / present / mixed |
| **风格摘要** | | |
| style_summary | str | 一句话风格摘要（~200 tokens，供 ContextPack 使用） |
| style_tags | list[str] | 标签：['简洁','冷峻','幽默','华丽','口语化'] 等 |
| **版本** | | |
| version | int | 版本号（重新提取时递增） |
| status | StyleProfileStatus | 状态 |
| created_at | str | 创建时间 |
| updated_at | str | 更新时间 |
| confirmed_at | str | 用户确认时间 |

### 2.4 StyleDNAExtractionRequest

提取请求对象（内存对象，非持久化）。

| 字段 | 类型 | 说明 |
|---|---|---|
| work_id | str | 作品 ID |
| source_type | StyleProfileSourceType | 来源 |
| source_text | str | 标杆文本内容（仅提取过程中使用，不持久化完整文本） |
| source_ref | str | 来源引用 |

### 2.5 StyleDNAExtractionResult

| 字段 | 类型 | 说明 |
|---|---|---|
| profile | StyleProfile | 提取结果 |
| confidence | float | 置信度 |
| warnings | list[str] | 警告（"source_text_too_short" 等） |

---

## 三、服务接口

### 3.1 StyleDNAExtractionService

```python
class StyleDNAExtractionService:
    def __init__(
        self,
        *,
        profile_repository: StyleProfileRepository,  # 新增
        model_router: ModelRouter,                    # 复用 P0
        prompt_registry: PromptRegistry,              # 复用 P0
        output_validator: OutputValidator,            # 复用 P0
        trace_service: AgentTraceService | None,      # 复用 P1
    ) -> None: ...

    # ── 提取 ──
    async def extract(
        self,
        *,
        work_id: str,
        source_text: str,
        source_type: StyleProfileSourceType,
        source_ref: str = "",
    ) -> StyleDNAExtractionResult: ...

    # ── 状态管理 ──
    async def confirm(self, profile_id: str) -> StyleProfile: ...
    async def disable(self, profile_id: str) -> StyleProfile: ...

    # ── 内部方法 ──
    async def _archive_current_active(self, work_id: str) -> None: ...
    # confirm 内部调用：将当前 active 的 profile 标记为 archived，再激活新 profile

    # ── 查询 ──
    async def get_active(self, work_id: str) -> StyleProfile | None: ...
    async def get_history(self, work_id: str) -> list[StyleProfile]: ...
    async def delete(self, profile_id: str) -> None: ...
    # 【冻结】软删除策略：
    # - PENDING_CONFIRM / DRAFT：可以物理删除（未被系统引用）。
    # - ACTIVE / DISABLED / ARCHIVED：标记为 ARCHIVED，不物理删除。
    #   原因：可能被历史 ContextPackSnapshot 或 StoryMemory 引用。
    #   删除后前端显示"风格画像已删除"，历史记录可追溯。
```

### 3.2 提取流程（extract 方法）

**架构路径（冻结）**：StyleDNAExtractionService 是 Core Application Service。它**直接调用 ModelRouter / PromptRegistry / OutputValidator**，不经过 Agent Runtime 或 ToolFacade。Style DNA 提取复用 Memory Extraction 的 Prompt 模板思路和模型角色（`style_extractor`），但不需要启动完整的 Agent Session/Step/PPAO 循环。

```python
async def extract(self, *, work_id, source_text, source_type, source_ref):
    # 1. 校验：source_text 不能为空
    # 2. 计算 source_text_hash = sha256(source_text)
    # 3. 判断低置信度：len(source_text) < 500 → 标记 low_confidence
    # 4. 构建 Prompt：使用 prompt_key = "style_dna_extraction"
    #    输入：source_text（完整标杆文本）
    #    输出 schema：StyleDNAOutputSchema
    # 5. 通过 ModelRouter 直接调用 model_role=style_extractor（默认 Kimi）
    #    （不走 ToolFacade，不走 Agent Runtime）
    # 6. Output Validator 校验结构化输出
    #    【冻结】复用 P0 OutputValidator 默认重试策略：schema 校验失败最多重试 2 次。
    #    超过重试次数后 extraction failed，不创建 StyleProfile，返回错误 + LLMCallLog ref。
    # 7. 校验通过 → 构建 StyleProfile（status=PENDING_CONFIRM, source_text_hash 已计算，
    #    source_text 不持久化完整内容，仅保留提取后的结构化特征）
    # 8. 持久化 → 返回 StyleDNAExtractionResult
```

### 3.3 确认流程（confirm 方法）

```python
async def confirm(self, profile_id: str) -> StyleProfile:
    profile = await self._load(profile_id)
    if profile.status != StyleProfileStatus.PENDING_CONFIRM:
        raise ValueError("profile_not_confirmable")

    # 【事务约束】同一 work_id 同一时刻只能有一个 active StyleProfile。
    # 以下两步必须在同一事务中完成：
    # 1. 将当前 active 的 profile 标记为 archived（内部方法）
    await self._archive_current_active(profile.work_id)
    # 2. 激活新 profile
    profile.status = StyleProfileStatus.ACTIVE
    profile.confirmed_at = _now()
    # 3. 提交事务（SQLite 若支持部分索引可加 UNIQUE(work_id) WHERE status='active'）
    return await self._save(profile)
```

---

## 四、ContextPack 集成

### 4.1 ContextPackService 修改点

在 `ContextPackService._assemble_optional_layers()` 中增加 Style DNA 层：

```python
async def _assemble_optional_layers(self, ...):
    # ... 现有可选层 ...

    # P2: Style DNA 可选层
    style_profile = await self._style_profile_repo.get_active(work_id)
    if style_profile and style_profile.status == StyleProfileStatus.ACTIVE:
        style_layer = ContextItem(
            item_id=f"style_dna_{style_profile.profile_id}",
            source_type="style_dna",
            source_id=style_profile.profile_id,
            priority=ContextPriority.OPTIONAL_LOWEST,  # 以 P0-06 为准
            content_text=style_profile.to_context_summary(),
            token_estimate=250,
            required=False,
            metadata={
                "confidence": style_profile.confidence,
                "low_confidence_reason": style_profile.low_confidence_reason,
            }
        )
        optional_items.append(style_layer)
```

### 4.2 格式化策略（冻结）

格式化逻辑属于 StyleProfile 领域对象本身，不放在 ContextPackService 中。ContextPackService 只调用 `style_profile.to_context_summary()`。

```python
# StyleProfile 领域方法
class StyleProfile(AIBaseModel):
    # ... 字段 ...

    def to_context_summary(self) -> str:
        """生成 ContextPack 可选层文本（约 200-300 tokens）。"""
        parts = [f"风格特征：{self.style_summary}"]
        if self.style_tags:
            parts.append(f"风格标签：{', '.join(self.style_tags)}")
        parts.append(f"对白占比约 {self.dialogue_ratio:.0%}")
        parts.append(f"平均句长 {self.avg_sentence_length:.0f} 字")
        parts.append(f"叙述视角：{self.narrative_perspective}")
        if self.confidence < 0.5:
            parts.append("[注意：风格画像置信度较低，仅供参考]")
        return "\n".join(parts)
```

ContextPackService 调用方式：

```python
style_layer = ContextItem(
    content_text=style_profile.to_context_summary(),
    # ...
)
```

### 4.3 Token 策略

| 场景 | 行为 |
|---|---|
| 无 active StyleProfile | 跳过此层 |
| 有 active + Token 充足 | 完整包含（~250 tokens） |
| 有 active + Token 不足 | **首批裁剪**（可选层中标记为 lowest_priority） |
| 有 active + confidence < 0.5 | 包含但标注"低置信度，仅供参考"。Writer/Rewriter 只能将其作为弱风格参考，不得作为强约束 |

**低置信度确认规则（冻结）**：`confidence < 0.5` 的 StyleProfile **允许用户确认激活**。进入 ContextPack 时携带 `low_confidence` 标记。此设计接受——风格画像始终是辅助参考，即使在低置信度下，用户也有权选择使用。

---

## 五、与 Memory Extraction 能力的复用关系

Style DNA 提取**复用 Memory Extraction 的能力边界**（prompt_key、model_role、OutputValidator、LLMCallLog），但**不启动完整 Agent Runtime，也不通过 ToolFacade 调用**。

| 复用什么 | 复用方式 |
|---|---|
| Prompt 模板思路 | 使用 prompt_key = `style_dna_extraction`，结构与 memory extraction 类似（输入长文本，输出结构化 JSON） |
| 模型角色 | 新增 `ModelRole.STYLE_EXTRACTOR`，默认路由到 Kimi（与 memory_extractor 相同的分析能力） |
| OutputValidator | 复用 P0 OutputValidator 进行 schema 校验 + 重试 |
| LLMCallLog | 复用 P0 LLMCallLog 记录提取调用（prompt_key, model_role, token usage, elapsed time） |
| Agent Runtime | **不**启动 AgentSession / AgentStep / PPAO。提取是用户触发的普通 AI 分析，非 Agent 编排任务 |

调用链路：

```
StyleDNAExtractionService.extract()
  → PromptRegistry.resolve("style_dna_extraction", "v1")
  → ModelRouter.invoke(model_role="style_extractor", messages=[...])
  → OutputValidator.validate(output, schema="style_dna_output")
  → LLMCallLogger.log(prompt_key, model_role, tokens, elapsed)
```

---

## 六、Repository 接口与持久化

### 6.1 StyleProfileRepository

```python
class StyleProfileRepository(ABC):
    @abstractmethod
    async def save(self, profile: StyleProfile) -> StyleProfile: ...
    @abstractmethod
    async def get_by_id(self, profile_id: str) -> StyleProfile | None: ...
    @abstractmethod
    async def get_active(self, work_id: str) -> StyleProfile | None: ...
    @abstractmethod
    async def get_history(self, work_id: str) -> list[StyleProfile]: ...
    @abstractmethod
    async def update(self, profile: StyleProfile) -> StyleProfile: ...
    @abstractmethod
    async def delete(self, profile_id: str) -> None: ...
```

### 6.2 持久化表

```sql
CREATE TABLE IF NOT EXISTS style_profiles (
    profile_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT DEFAULT '',
    source_text_hash TEXT DEFAULT '',
    source_text_length INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0.0,
    low_confidence_reason TEXT DEFAULT '',

    avg_sentence_length REAL DEFAULT 0.0,
    sentence_length_variance REAL DEFAULT 0.0,
    short_sentence_ratio REAL DEFAULT 0.0,
    long_sentence_ratio REAL DEFAULT 0.0,
    compound_sentence_ratio REAL DEFAULT 0.0,

    avg_paragraph_length REAL DEFAULT 0.0,
    paragraph_length_variance REAL DEFAULT 0.0,

    dialogue_ratio REAL DEFAULT 0.0,
    psychological_ratio REAL DEFAULT 0.0,
    action_ratio REAL DEFAULT 0.0,
    description_ratio REAL DEFAULT 0.0,

    narrative_perspective TEXT DEFAULT '',
    tense_preference TEXT DEFAULT '',

    style_summary TEXT DEFAULT '',
    style_tags_json TEXT DEFAULT '[]',

    version INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending_confirm',
    -- Repository 保存时必须显式写入状态；DRAFT 仅扩展预留，P2-03 不使用
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    confirmed_at TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_style_profiles_work
    ON style_profiles(work_id, status);
```

---

## 七、API 设计

### 7.1 路由前缀

`/api/v2/ai/style-dna`

### 7.2 端点

```
POST   /api/v2/ai/style-dna/extract
  Request:  { work_id, source_text, source_type, source_ref? }
  Response: { job_id, status: "queued" }
  Note:     LLM 调用耗时 10-30 秒，HTTP 立即返回 202。
            通过 P0 AIJob 跟踪提取进度（复用 /api/v2/ai/jobs/{job_id}）。
            提取成功后 AutoJob result 中包含 { profile_id }。
            前端 GET /api/v2/ai/jobs/{job_id} 轮询直到 job.completed → 再 GET /style-dna/profiles/{profile_id}。
            提取失败不创建 StyleProfile，job.status=failed。
            source_text 仅用于本次提取，不持久化完整内容。

GET    /api/v2/ai/style-dna/profiles/{profile_id}
  Response: { profile_id, status: "pending_confirm"|"active"|"disabled"|"archived",
              confidence, style_summary, ... }
  Note:     status 严格对应 StyleProfileStatus 枚举值。
            提取中（job 未完成）时 profile 不存在，返回 404。

GET    /api/v2/ai/style-dna/{work_id}/active
  Response: { profile } 或 { profile: null }

GET    /api/v2/ai/style-dna/{work_id}/history
  Response: { profiles: [...] }

POST   /api/v2/ai/style-dna/profiles/{profile_id}/confirm
  Response: { profile_id, status: "active" }

POST   /api/v2/ai/style-dna/profiles/{profile_id}/disable
  Response: { profile_id, status: "disabled" }

DELETE /api/v2/ai/style-dna/profiles/{profile_id}
  Response: { deleted: true, status: "archived"|"deleted" }
  Note:     PENDING_CONFIRM → 物理删除；ACTIVE/DISABLED/ARCHIVED → 标记 ARCHIVED
```

---

## 八、前端集成方向

### 8.1 配置入口

在 AI Settings 页面新增"Style DNA 风格画像"卡片：

```
┌─────────────────────────────────────┐
│  🎨 风格画像                        │
│  状态：✅ 已激活 | 置信度：高       │
│  "简洁冷峻的第三人称限知叙事..."    │
│                                     │
│  [上传标杆文本] [从已有章节选择]    │
│  [查看历史] [重新提取] [关闭]      │
└─────────────────────────────────────┘
```

### 8.2 上传流程

1. 用户点击"上传标杆文本" → 文件选择器（支持 .txt）
2. 预览文本内容 + 字数显示
3. 点击"开始提取" → 调用 POST /extract
4. 展示提取结果：风格摘要 + 各项指标 + 置信度
5. 用户确认 → POST /confirm → 激活

### 8.3 低置信度提示

```
⚠️ 标杆文本过短（< 500 字），风格画像置信度较低。
建议上传至少 2000 字的文本以获得更准确的风格分析。
[仍然激活] [重新上传]
```

---

## 九、测试策略

### 9.1 正向测试

| # | 用例 | 验证点 |
|---|---|---|
| T1 | 上传长文本提取 | confidence ≥ 0.5，profile 生成正确 |
| T2 | 确认后激活 | status=active，旧的 active 变为 archived |
| T3 | active profile 进入 ContextPack | ContextPack 可选层包含 style_summary |
| T4 | 禁用 profile | status=disabled，ContextPack 不再包含 |

### 9.2 边界测试

| # | 用例 | 验证点 |
|---|---|---|
| T5 | 短文本提取（< 500 字） | low_confidence_reason="source_text_too_short"，confidence < 0.5 |
| T6 | 无 active profile | ContextPack 跳过 Style DNA 层，不报错 |
| T7 | 重复提取 | 新 profile.version 递增，状态为 PENDING_CONFIRM；旧 active 保持 ACTIVE 不变。用户 confirm 新 profile 后旧 active → ARCHIVED |
| T8 | ContextPack Token 不足 | Style DNA 层首批裁剪 |

### 9.3 反向测试

| # | 用例 | 验证点 |
|---|---|---|
| T9 | source_text 完整内容不持久化 | 数据库查询 style_profiles 表无 source_text 字段 |
| T10a | 删除 PENDING_CONFIRM profile | 物理删除，get_by_id 返回 None |
| T10b | 删除 ACTIVE/DISABLED/ARCHIVED profile | 软删除：status=ARCHIVED，get_by_id 仍可查，ContextPack 不再使用 |
| T11 | 同时只能有一个 active | confirm 新 profile 时旧 active 自动 archived |

---

## 十、安全边界

| 约束 | 实施方式 |
|---|---|
| 标杆文本不持久化完整内容 | 提取后仅保留结构化特征 + source_text_hash |
| StyleProfile 不混入 StoryMemory | 独立表 + 独立 Repository，StoryMemory 仅持有 profile_id 引用 |
| 低置信度标注 | confidence < 0.5 → low_confidence_reason → ContextPack 标注警告 |
| 用户完全控制 | 可随时 disable / delete / 重新提取 |
| API 不暴露完整文本 | extract 请求后 source_text 不进入任何持久化 |

---

## 十一、已冻结决策

1. **从已有章节指定标杆文本**：仅限已确认章节（非候选稿/非草稿）。最多选择 3 章拼接。AI CandidateDraft、Quick Trial 输出不得作为标杆来源——防止 AI 味反向固化。
2. **model_role 专用名**：`style_extractor`，默认路由到 Kimi。
3. **多作品共享**：不支持。每个作品独立维护 StyleProfile。
4. **重复提取规则**：新 profile.version = 当前最大 version + 1，状态为 PENDING_CONFIRM；旧 active 保持 ACTIVE。用户 confirm 新 profile 后，旧 active 才变 ARCHIVED。这与 confirm() 的事务原则一致。

## 十二、待确认项

1. **Style DNA 提取的 Prompt 模板细节**：由 Prompt Registry 详细设计确定，本模块只定义 `prompt_key="style_dna_extraction"` 和 `output_schema_key="style_dna_output"`。

---

## 附录：代码改动面

### 新增文件

```
application/services/ai/style_dna_service.py
domain/repositories/ai/style_profile_repository.py
infrastructure/persistence/sqlite_style_profile_repo.py
presentation/api/routers/v2/ai/style_dna.py
tests/test_style_dna_service.py
```

### 需修改文件

```
domain/entities/ai/models.py              # 追加 StyleProfile, StyleProfileStatus, StyleProfileSourceType 等；ModelRole 追加 STYLE_EXTRACTOR
application/services/ai/context_pack_service.py  # _assemble_optional_layers 加 Style DNA
presentation/api/app.py                   # 注册 style-dna 路由
```

### 不可修改文件

```
application/services/ai/tool_facade.py
application/services/ai/agent_runtime_service.py
application/services/v1/*
```
