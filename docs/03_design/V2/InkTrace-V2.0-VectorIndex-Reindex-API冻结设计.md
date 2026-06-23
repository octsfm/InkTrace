# InkTrace V2.0 VectorIndex Reindex API 冻结设计

版本：v1.0 / Reindex API 冻结契约版
状态：已冻结
日期：2026-06-18
所属阶段：InkTrace V2.0 P2 开发阻塞解封
设计范围：VectorIndex Reindex API 正式契约

依据文档：

- `docs/03_design/V2/InkTrace-V2.0-P0-05-VectorRecall详细设计.md`（§7.5 reindex 行为、§12 AIJobSystem 关系）
- `docs/03_design/V2/InkTrace-V2.0-P0-02-AIJobSystem详细设计.md`（AIJob 生命周期、状态机、Step 模型）
- `docs/03_design/V2/InkTrace-V2.0-P0-11-API与集成边界详细设计.md`（统一响应格式、caller_type、idempotency_key）
- `docs/03_design/InkTrace-V2.0-P2-11-API与前端集成边界详细设计.md`（P2 错误码前缀、Feature Flag 体系）
- `domain/entities/ai/models.py`（AIJob、AIJobStep、VectorIndexBuildResult 实体）
- `application/services/ai/vector_reindex_service.py`（VectorReindexApplicationService 当前实现）
- `application/services/ai/vector_index_service.py`（VectorIndexService reindex_work / reindex_chapter）

说明：本文档是 reindex API 的冻结契约，用于指导 Router、DTO、Application Service、AIJob 接线和测试实现。本文档不定义底层向量库算法、不写代码、不生成数据库迁移、不拆 Task、不进入开发计划。

---

## 一、文档定位

### 1.1 本文档是什么

本文档将"支持 reindex"从模糊能力冻结为可实现、可测试、无须开发者主观猜测的正式 API 契约。

### 1.2 本文档覆盖

- Reindex API 的 HTTP 接口完整定义（路径、方法、权限、Feature Flag）。
- Request / Response DTO 的字段、类型、必填规则、校验规则。
- 与现有 AIJob 系统的集成方式（job_type、Step、状态流转、轮询）。
- 并发控制与幂等规则。
- 正式错误码体系。
- 安全边界与日志脱敏规则。
- 索引一致性与失败恢复策略。
- 前端交互边界与用户文案。
- 测试要求。
- 实现改动面预估。

### 1.3 本文档不覆盖

- 底层向量库算法（chunking、embedding 生成、向量存储选型）。
- VectorIndex / RAG 全系统重构。
- ContextPack、StoryMemory、StoryState、CandidateDraft 的修改。
- P0-05 中已冻结的 VectorIndexService 行为规则（本文档只在其上叠加 API 契约）。
- 前端 UI 组件具体实现代码。

---

## 二、设计决策

### 2.1 一个接口还是两个接口

**冻结决策：一个接口，通过 `index_scope` 字段区分模式。**

理由：
- P0-05 §7.2 已将 `index_scope`（`full_work | chapter`）定义为 VectorIndexService 的输入字段。
- `VectorReindexApplicationService.start_reindex()` 已接受 `index_scope` 参数，单一方法同时支持两种模式。
- 一个接口减少路由注册、Feature Flag 配置和前端调用复杂度，避免两个接口之间的一致性问题。

### 2.2 同步还是异步

**冻结决策：异步。API 只创建 AIJob，不在 HTTP 请求内直接重建索引。**

理由：
- P0-05 §7.5 规定 reindex 是"受控操作"，P0-05 §12.2 规定"reindex chapter 可以作为后续操作"，明确建立 AIJob 是可选项。
- 现有 `VectorReindexApplicationService` 已通过 AIJob 包装 reindex，`auto_run=True` 时可同步执行。
- 全作品 reindex 可能耗时数十秒到数分钟，不适合阻塞 HTTP 请求。
- 与现有 initialization（创建 `ai_initialization` Job 后异步执行）模式一致。

API 行为：
- POST 请求立即返回 `202 Accepted`，携带 `job_id` 和轮询提示。
- 后端通过 `VectorReindexApplicationService` 异步执行 reindex，更新 AIJob 状态。
- 前端通过 `GET /api/v2/ai/jobs/{job_id}` 轮询进度。

### 2.3 是否统一复用 AIJob

**冻结决策：是。统一复用现有 AIJob 系统。**

理由：
- `job_type = "vector_indexing"` 已在 P0-02 §5.3 中定义，`VectorReindexApplicationService` 已使用。
- AIJob 的 `queued → running → completed/failed/cancelled/paused` 状态机覆盖 reindex 全生命周期。
- 现有 Job API（`GET /api/v2/ai/jobs/{job_id}`、`GET /api/v2/ai/jobs`、`POST /api/v2/ai/jobs/{job_id}/cancel`）可直接用于状态查询和取消，无需新建 API。
- P0-05 §12.2 已确认"reindex 可以复用 AIJobSystem"。

### 2.4 是否仅允许用户手动触发

**冻结决策：API 层面仅允许 `caller_type = user_action`。**

理由：
- P0-05 §7.5 规定 reindex 触发方包括"用户在 Presentation / UI 中手动点击'重建索引'"和"reanalysis 流程完成后的受控触发"。
- P0-05 §7.5 也规定"系统检测到索引 stale 后，应提示用户触发 reindex，而不是静默执行"——明确禁止静默自动重建。
- API 端点仅开放给用户手动操作。Agent / Workflow / Quick Trial / Reviewer / system 调用此端点返回 `403`。

**系统内部调用路径**：
- 初始化流程（`InitializationApplicationService`）在 `ai_initialization` Job 的 `build_vector_index` Step 中直接调用 `VectorIndexService.build_initial_index()`，不经过 Reindex API。
- reanalysis 流程如需受控触发 reindex，应通过独立的 Application Service 内部方法调用 `VectorIndexService.reindex_work()` 或 `VectorIndexService.reindex_chapter()`，**不得伪造 `caller_type = user_action` 调用 Reindex API**。
- 此规则对齐 P0-11 §2.2："API 层不得伪造 user_action"。

### 2.5 work 级和 chapter 级的具体语义

**`index_scope = full_work`**：
- 对该作品所有已确认（confirmed / published）章节重建向量索引。
- 行为等同于 P0-05 §7.5 定义的"work 级 reindex 可重建全部 confirmed chapters 的索引"。
- 先标记所有已有 chunk / embedding / vector 为 stale，再逐章重建。
- 已删除章节的旧 chunk 不会被重新激活。

**`index_scope = chapter`**：
- 对 `target_chapter_ids` 指定的已确认章节重建向量索引。
- 行为等同于 P0-05 §7.5 定义的"chapter 级 reindex 可只重建指定章节"。
- 先标记指定章节的已有 chunk / embedding / vector 为 stale，再重建。
- 不重建其他章节的索引。
- work 级 `index_status` 更新为 `degraded` 或 `partial_stale`（取决于其他章节状态）。

---

## 三、接口定义

### 3.1 基本信息

| 属性 | 值 |
|---|---|
| HTTP Method | `POST` |
| Path | `/api/v2/ai/vector-index/reindex` |
| Content-Type | `application/json` |
| 调用权限 | 仅 `caller_type = user_action` |
| Feature Flag | 不需要独立的 P2 Feature Flag（向量索引是 P0 核心能力） |
| Provider 要求 | 需要 Embedding Provider 已配置且可用 |
| 需要 user_action | 是（不属于门控端点，但需要 caller_type 校验） |

### 3.2 路径唯一性验证

- 现有 P2 API 路由均以 `/api/v2/ai/multi-chapter`、`/api/v2/ai/citations` 等前缀注册。
- 现有 P0 API 路由包括 `/api/v2/ai/jobs`、`/api/v2/ai/initializations` 等。
- `/api/v2/ai/vector-index/reindex` 不与任何现有路由冲突。
- `vector-index` 前缀在现有路由注册中唯一。

### 3.3 Router 注册

```python
# 在 presentation/api/app.py 中追加
from presentation.api.routers.v2.ai import vector_index

app.include_router(vector_index.router, prefix="/api/v2/ai")
```

### 3.4 与 Feature Flag 中间件的关系

`/api/v2/ai/vector-index` 路径不在现有 P2 Feature Flag 中间件的任何路径匹配规则中，因此：
- 不会被现有 P2 Feature Flag 中间件拦截返回 503。
- 不需要新增 Feature Flag 环境变量。
- 如果 Embedding Provider 不可用，API 返回 `P2_VECTOR_EMBEDDING_UNAVAILABLE`（503），语义不同于 `P2_FEATURE_DISABLED`。

> **设计说明**：向量索引是 P0 核心基础设施（用于 ContextPack 的 RAG 层），不是可选 P2 模块。Feature Flag 不应阻止用户重建已存在的基础设施。如后续需要灰度控制，可新增环境变量 `INKTRACE_ENABLE_VECTOR_INDEX_API`，但当前不要求。

---

## 四、请求契约

### 4.1 Request DTO

```python
class ReindexRequest(V2AIBaseModel):
    work_id: str                              # 必填，作品 ID
    index_scope: str                          # 必填，枚举：full_work | chapter
    target_chapter_ids: list[str] | None = None  # 条件必填（index_scope=chapter 时必填）
    idempotency_key: str = ""                 # 可选，推荐前端生成并传入
    force_rebuild: bool = False               # 可选，默认 false
    reason: str = ""                          # 可选，用户触发原因说明
    caller_type: str = "user_action"          # 必填，API 层校验必须为 user_action
```

### 4.2 字段详细定义

#### `work_id`

| 属性 | 值 |
|---|---|
| 类型 | `str` |
| 必填 | 是 |
| 校验规则 | 非空字符串；必须对应已存在的作品 |
| 错误码 | `P2_VECTOR_WORK_NOT_FOUND`（404） |

#### `index_scope`

| 属性 | 值 |
|---|---|
| 类型 | `str` |
| 必填 | 是 |
| 枚举值 | `"full_work"` \| `"chapter"` |
| 校验规则 | 必须为枚举值之一，大小写敏感 |
| 默认值 | 无（必须显式传入） |
| 错误码 | `P2_VECTOR_INVALID_INDEX_SCOPE`（400） |

#### `target_chapter_ids`

| 属性 | 值 |
|---|---|
| 类型 | `list[str]` |
| 必填 | 条件必填：`index_scope = chapter` 时必填且不得为空 |
| 条件约束 | `index_scope = full_work` 时，传入此字段拒绝（400） |
| 校验规则 | 每个 chapter_id 非空字符串；必须属于 `work_id` 对应作品；不允许重复 |
| 长度限制 | 单次最多 50 个章节（防止单次请求过大） |
| 错误码 | 缺失：`P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED`（400） |
|  | 不允许：`P2_VECTOR_TARGET_CHAPTER_IDS_NOT_ALLOWED`（400） |
|  | 章节不属于作品：`P2_VECTOR_CHAPTER_NOT_IN_WORK`（400） |
|  | 章节不存在：`P2_VECTOR_CHAPTER_NOT_FOUND`（404） |
|  | 超过上限：`P2_VECTOR_TOO_MANY_CHAPTERS`（400） |

**full_work 模式传入 `target_chapter_ids` 的处理**：

**冻结决策：拒绝（400），不忽略。**

理由：
- 静默忽略会导致调用方误以为传入的章节列表已生效，产生隐蔽 bug。
- 显式拒绝迫使调用方修正请求，符合 fail-fast 原则。
- 对齐 P0-11 的 caller_type 校验和 idempotency_key 要求的严格风格——宁可拒绝明确错误，也不猜测意图。

#### `idempotency_key`

| 属性 | 值 |
|---|---|
| 类型 | `str` |
| 必填 | 否（但强烈推荐传入） |
| 默认值 | `""`（空字符串 = 不启用幂等复用） |
| 校验规则 | 非空时，用于匹配已存在的 reindex 任务 |
| 长度限制 | 最大 256 字符 |
| 行为 | 见 §七 并发与幂等规则 |

> **设计说明**：与门控端点（accept/apply/confirm 等）不同，reindex 不属于不可逆的用户确认操作，因此 `idempotency_key` 不是强制必填。但前端应在用户点击"重建索引"时生成并传入，以支持防重复点击和页面刷新后恢复任务状态。

#### `force_rebuild`

| 属性 | 值 |
|---|---|
| 类型 | `bool` |
| 必填 | 否 |
| 默认值 | `false` |

**语义**：
- `false`（默认）：如索引状态为 `ready` 且无 stale 标记，可返回已有成功 Job（不重复执行）。
- `true`：无论当前索引状态如何，强制执行完整重建。覆盖所有已有 chunk/embedding/vector。

> **实现注意**：`force_rebuild = true` 时仍遵守并发规则（同 work 同时只允许一个写任务）。如果已有运行中任务，返回 409。

#### `reason`

| 属性 | 值 |
|---|---|
| 类型 | `str` |
| 必填 | 否 |
| 默认值 | `""` |
| 长度限制 | 最大 500 字符 |
| 用途 | 记录用户触发 reindex 的原因，保存在 AIJob.payload 中，不进入日志安全脱敏范围 |

#### `caller_type`

| 属性 | 值 |
|---|---|
| 类型 | `str` |
| 必填 | 是（API 层校验） |
| 允许值 | 仅 `"user_action"` |
| 错误码 | `P2_VECTOR_CALLER_FORBIDDEN`（403） |

### 4.3 校验执行顺序

API 层按以下顺序执行校验，首个失败即返回错误：

1. `caller_type` 校验 → 403
2. `index_scope` 校验 → 400
3. `work_id` 存在性校验 → 404
4. `index_scope = chapter` 条件必填校验 → 400
5. `index_scope = full_work` 且 `target_chapter_ids` 非空 → 400
6. `target_chapter_ids` 每个 ID 的存在性和归属校验 → 400/404
7. `target_chapter_ids` 去重和上限校验 → 400
8. Embedding Provider 可用性校验 → 503
9. Vector Store 可用性校验 → 503
10. 并发冲突校验 → 409

---

## 五、响应契约

### 5.1 Response DTO

```python
class ReindexResponse:
    job_id: str                    # AIJob ID
    job_type: str                  # 固定 "vector_indexing"
    operation: str                 # 固定 "reindex"
    work_id: str                   # 作品 ID
    index_scope: str               # "full_work" | "chapter"
    target_chapter_ids: list[str]  # 目标章节 ID 列表（full_work 时为空列表）
    status: str                    # AIJob 状态（新创建为 "queued"，复用已存在 Job 时可能为其他状态）
    created_at: str                # Job 创建时间（ISO 8601）
    request_id: str                # 请求 ID
    trace_id: str                  # 追踪 ID
    polling_hint: dict             # 轮询提示
    reused_existing_job: bool      # 是否复用了已存在的 Job
```

### 5.2 HTTP 状态码

| 场景 | 状态码 |
|---|---|
| 创建新 Job 成功 | **202 Accepted** |
| 通过 idempotency_key 复用已有 Job | **200 OK**（`reused_existing_job = true`） |
| 请求参数错误 | 400 / 404 |
| caller_type 校验失败 | 403 |
| 并发冲突 | 409 |
| Embedding / Vector Store 不可用 | 503 |

### 5.3 创建新任务时的响应

```json
{
    "request_id": "req_1718700000_abc123def",
    "trace_id": "trace_a1b2c3d4e5f6",
    "status": "ok",
    "data": {
        "job_id": "job_a1b2c3d4e5f6",
        "job_type": "vector_indexing",
        "operation": "reindex",
        "work_id": "work_1234567890ab",
        "index_scope": "full_work",
        "target_chapter_ids": [],
        "status": "queued",
        "created_at": "2026-06-18T10:30:00.000000",
        "request_id": "req_1718700000_abc123def",
        "trace_id": "trace_a1b2c3d4e5f6",
        "polling_hint": {
            "next_poll_after_ms": 3000,
            "max_poll_interval_ms": 10000,
            "timeout_hint_ms": 300000,
            "still_running_message": "索引重建中，请耐心等待。"
        },
        "reused_existing_job": false
    }
}
```

### 5.4 复用已有 Job 时的响应

当 `idempotency_key` 匹配到已存在的 Job（范围相同）时：

```json
{
    "request_id": "req_1718700000_xyz789ghi",
    "trace_id": "trace_f6e5d4c3b2a1",
    "status": "ok",
    "data": {
        "job_id": "job_a1b2c3d4e5f6",
        "job_type": "vector_indexing",
        "operation": "reindex",
        "work_id": "work_1234567890ab",
        "index_scope": "full_work",
        "target_chapter_ids": [],
        "status": "running",
        "created_at": "2026-06-18T10:30:00.000000",
        "request_id": "req_1718700000_xyz789ghi",
        "trace_id": "trace_f6e5d4c3b2a1",
        "polling_hint": {
            "next_poll_after_ms": 3000,
            "max_poll_interval_ms": 10000,
            "timeout_hint_ms": 300000,
            "still_running_message": "索引重建中，请耐心等待。"
        },
        "reused_existing_job": true
    }
}
```

### 5.5 不返回的内容

以下内容**不得**出现在响应中（安全边界）：
- 索引结果正文（chunk_text、text_excerpt）
- Embedding 原始向量
- 完整 Chunk 数据
- API Key
- query_text
- AIJob.payload 原始内容（payload 在序列化时排除，对齐 `jobs.py._serialize_job`）

### 5.6 轮询入口

前端获取 reindex 进度通过现有 Job API：

```
GET /api/v2/ai/jobs/{job_id}        → 获取 Job 状态和进度
GET /api/v2/ai/jobs/{job_id}/steps  → 获取 Step 详情
```

无需新增专用轮询端点。

---

## 六、AIJob 集成

### 6.1 Job 创建

| 属性 | 值 |
|---|---|
| `job_type` | `"vector_indexing"` |
| `operation` | `"reindex"`（存入 `AIJob.payload`） |
| `created_by` | `"user_action"` |

**Job 创建复用 `VectorReindexApplicationService.start_reindex()`**，该服务已完成以下工作：
- 通过 `AIJobService.create_job()` 创建 AIJob
- 创建单个 `build_vector_index` Step
- 将 `index_scope`、`target_chapter_ids_csv`、`target_chapter_count` 写入 `AIJob.payload`

**API 层新增职责**：
- 在执行 `start_reindex()` 前完成所有校验（caller_type、参数、并发、Provider 可用性）。
- 将 `reason` 和 `force_rebuild` 传入 `AIJob.payload`（当前 `VectorReindexApplicationService` 未存储这两个字段，需要扩展）。

### 6.2 Job Context（payload）字段

以下字段可安全存入 `AIJob.payload`：

| 字段 | 说明 |
|---|---|
| `work_id` | 作品 ID |
| `index_scope` | `full_work` \| `chapter` |
| `target_chapter_ids_csv` | 逗号分隔的章节 ID |
| `target_chapter_count` | 章节数量 |
| `source_job_id` | 触发源 Job ID（可选） |
| `force_rebuild` | 是否强制重建（新增） |
| `reason` | 用户触发原因（新增） |

以下字段**禁止**进入 `AIJob.payload`：

| 禁止项 | 原因 |
|---|---|
| 完整章节正文 | 安全边界 |
| Chunk 文本（text_excerpt） | 安全边界 |
| Embedding 向量 | 安全边界 |
| API Key | 安全边界 |
| query_text | 不适用于 reindex 场景 |

### 6.3 Job Step 定义

Reindex Job 包含**单个 Step**：

| 属性 | 值 |
|---|---|
| `step_type` | `"build_vector_index"` |
| `step_name` | `"构建向量索引"` 或 `"Build Vector Index"` |
| `order_index` | 0 |
| `max_attempts` | 3 |

**冻结决策：不拆分为多个子 Step。**

理由：
- P0-05 §12.2 规定"P0 不要求拆成复杂子 Job"。
- 当前 `VectorReindexApplicationService` 已使用单个 `build_vector_index` Step。
- 单 Step 足够覆盖 reindex 的进度上报（通过 `AIJobProgress.percent` + `current_step_label`）。
- 如需更细粒度进度（如"正在处理第 3/10 章"），通过 `AIJobProgress.current_step_label` 动态更新实现，不拆 Step。

**Step 内部执行阶段（逻辑分段，非 AIJobStep）：**

1. **validate_scope** — 确认 scope 和 target chapters 有效。
2. **mark_stale** — 标记旧 chunk/embedding/vector 为 stale。
3. **load_documents** — 读取 confirmed chapters 正文。
4. **chunk_documents** — 对每章执行切片。
5. **embed_chunks** — 调用 EmbeddingProviderPort 生成 embedding。
6. **upsert_vectors** — 写入 VectorStorePort。
7. **finalize_metadata** — 保存 chunk/embedding metadata，更新 index_status。

以上阶段为 `VectorIndexService` 内部逻辑（已在 P0-05 §7.4 定义），不需要额外创建 AIJobStep。

### 6.4 Job 状态流转

Reindex Job 完全复用 AIJobSystem 状态机（P0-02 §5.5）：

```
[*] → queued → running → completed
                       → failed → queued (retry)
                       → cancelled
              → paused → running (resume)
                       → cancelled
              → cancelled
```

**Step 状态流转**：

```
[*] → pending → running → completed (含 warning_count)
                       → failed → pending (retry)
                       → skipped
```

### 6.5 进度上报

`VectorReindexApplicationService` 在执行 reindex 时通过以下方式更新进度：

- `AIJobProgress.percent`：根据已处理章节数 / 总章节数估算（`VectorIndexService` 内部更新）。
- `AIJobProgress.current_step_label`：动态更新为 `"正在处理第 N/M 章"` 或 `"正在生成嵌入向量"`。
- `AIJobProgress.warning_count`：记录 warning 数量。

### 6.6 状态查询

完全复用现有 Job API：

```
GET /api/v2/ai/jobs/{job_id}        → 获取 Job 状态、进度（percent、current_step_label）、result_summary
GET /api/v2/ai/jobs/{job_id}/steps  → 获取 Step 详情（状态、warning_count、error_code）
GET /api/v2/ai/jobs?work_id=xxx     → 列出该作品所有 Job
```

### 6.7 取消 / 暂停 / 恢复 / 重试

**全部复用现有 Job API 和 `VectorReindexApplicationService` 方法**：

| 操作 | API 端点 | Service 方法 |
|---|---|---|
| 取消 | `POST /api/v2/ai/jobs/{job_id}/cancel` | `VectorReindexApplicationService.cancel_job()` |
| 暂停 | 当前无 API 端点（仅 service 层） | `VectorReindexApplicationService.pause_job()` |
| 恢复 | 当前无 API 端点（仅 service 层） | `VectorReindexApplicationService.resume_job()` / `resume_and_run()` |
| 重试 | 当前无 API 端点（仅 service 层） | `VectorReindexApplicationService.retry_job()` / `retry_and_run()` |

> **现状说明**：暂停、恢复、重试目前只在 service 层实现，未通过独立的 Job API 端点暴露。reindex API 不需要新增这些端点——如果有用户驱动的暂停/恢复/重试需求，应统一在 Job API 层新增 `POST /api/v2/ai/jobs/{job_id}/pause`、`/resume`、`/retry`，而不是在 reindex 专有端点中实现。当前设计不阻塞 reindex API 落地，暂停/恢复/重试可通过直接操作 AIJob 实现。

### 6.8 retry 语义

**冻结决策：retry 重跑整个 build_vector_index Step（从 mark_stale 开始），而不是从失败 Step 内部续跑。**

理由：
- 当前 `VectorReindexApplicationService.retry_job()` 将 failed step 重置为 pending，然后调用 `run_reindex()` 完整重跑。
- 断点续跑需要保存和恢复 chunking/embedding 的中间状态，增加复杂度且容易引入不一致。
- 对于 P0 场景（单作品几百章以内），完整重跑的代价可接受。
- 如后续需要断点续跑，可通过 `target_chapter_ids` 缩小范围（仅重建失败的章节）。

### 6.9 Job 完成后的统计信息

`AIJob.result_summary` 记录以下统计（由 `VectorReindexApplicationService._build_result_summary()` 生成）：

```json
{
    "index_scope": "full_work",
    "target_chapter_ids": "chapter_a,chapter_b",
    "target_chapter_count": 2,
    "index_status": "ready",
    "indexed_chapter_count": 2,
    "indexed_chunk_count": 45,
    "failed_chunk_count": 0,
    "warning_count": 1,
    "completion_mode": "partial_success",
    "degraded_reason": "some_chunks_too_small",
    "warnings": ["章节 chapter_a 的 2 个 chunk 低于最小长度阈值"]
}
```

`AIJob.result_ref` 记录索引状态引用：`"vector_index_status:{work_id}"`。

---

## 七、并发与幂等规则

### 7.1 核心原则

**冻结决策：同一 work 同一时刻只允许一个 `vector_indexing` 类型的写任务（非终态）存在。**

理由：
- P0-05 §15 数据一致性与写入顺序要求"cancel 后迟到写入不得污染当前 active index"，多个并发写任务会使污染风险不可控。
- 向量索引的 stale → active 状态迁移在并发场景下难以保证正确性。
- 用户通常不需要同时对同一作品执行多个 reindex。

### 7.2 具体规则

#### 规则 1：同 work 已有运行中任务

当 `work_id` 已存在一个非终态（`queued` / `running` / `paused`）的 `vector_indexing` Job 时：

- **非幂等请求**（无 idempotency_key 或 idempotency_key 不匹配）：返回 `409 Conflict`，错误码 `P2_VECTOR_INDEXING_IN_PROGRESS`。
- **幂等请求**（idempotency_key 匹配到正在运行的任务）：返回 `200 OK`，`reused_existing_job = true`，指向现有 Job。

#### 规则 2：相同 idempotency_key 重复请求

- 如果 idempotency_key 匹配到已存在的 Job（任何状态），返回 `200 OK`，`reused_existing_job = true`。
- 匹配范围：同一 `work_id` + 同一 `index_scope` + 同一 `target_chapter_ids`（排序后比对）。
- 如果 idempotency_key 匹配但 scope / target_chapter_ids 不同：返回 `409 Conflict`，错误码 `P2_VECTOR_IDEMPOTENCY_CONFLICT`。

#### 规则 3：full_work 任务运行中，是否允许 chapter 任务

**冻结决策：不允许。**

同一 work 的 `vector_indexing` 写任务互斥，无论 scope。

#### 规则 4：chapter 任务运行中，是否允许 full_work 任务

**冻结决策：不允许。**

同上，互斥。

#### 规则 5：多个不重叠 chapter 任务是否允许并行

**冻结决策：不允许。**

保守规则——同一 work 同一时刻只允许一个 `vector_indexing` 写任务。多章节 reindex 通过单次请求的 `target_chapter_ids` 数组指定，在单个 Job 内串行处理。

#### 规则 6：重叠章节任务

由于规则 5 已禁止并行，重叠章节场景被并发互斥覆盖。

#### 规则 7：任务完成后多久内允许通过 idempotency_key 复用

**冻结决策：Job 创建后 24 小时内可通过 idempotency_key 复用。超过 24 小时后，idempotency_key 可被新请求复用（视为新任务）。**

此规则需要 `VectorReindexApplicationService` 或 Repository 层记录 `idempotency_key → job_id` 映射及其创建时间。超过 24 小时的映射可被新请求覆盖。

> **实现注意**：当前 `VectorReindexApplicationService` 不支持 idempotency_key 映射。需要在 `start_reindex()` 中新增 idempotency_key 查询/匹配逻辑。如使用 `FileAIJobStore`（JSON 文件存储），可在 AIJob 实体中新增 `idempotency_key` 字段，通过遍历现有 Job 匹配。

#### 规则 8：force_rebuild 与幂等

`force_rebuild = true` 时：
- 如果存在相同 scope 的非终态 Job，行为同规则 1（等待或冲突）。
- 如果存在相同 scope 的终态 Job（completed / failed / cancelled），不复用已有的成功 Job，创建新 Job 执行完整重建。
- idempotency_key 在 `force_rebuild = true` 时仍按规则 2 处理。

### 7.3 并发保证层级

| 层级 | 职责 |
|---|---|
| **API 层**（Presentation） | 校验 caller_type、参数格式、调用 `VectorReindexApplicationService` 并捕获异常 |
| **Application Service 层** | 执行并发冲突检测（查询同 work_id 的非终态 `vector_indexing` Job）、idempotency_key 匹配、创建/复用 Job |
| **Repository 层** | 提供 Job 查询方法（按 work_id + job_type + status 过滤），保证读一致 |

**冻结决策：并发判断由 Application Service（`VectorReindexApplicationService.start_reindex()`）保证，API 层只负责异常→错误响应的映射。**

---

## 八、错误码

### 8.1 错误码表

| 内部错误码 | HTTP | message（中文） | safe_message（用户可见） | 可重试 | 前端建议动作 |
|---|---|---|---|---|---|
| `P2_VECTOR_INVALID_INDEX_SCOPE` | 400 | 无效的索引范围，仅支持 full_work 或 chapter | 请选择"整部作品"或"指定章节"。 | 否 | 修正选择后重试 |
| `P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED` | 400 | 章节模式下必须提供目标章节列表 | 请选择至少一个章节。 | 否 | 选择章节后重试 |
| `P2_VECTOR_TARGET_CHAPTER_IDS_NOT_ALLOWED` | 400 | 全作品模式下不允许指定章节列表 | 全作品重建不需要选择章节，请取消章节选择后重试。 | 否 | 清空章节选择后重试 |
| `P2_VECTOR_TOO_MANY_CHAPTERS` | 400 | 单次最多支持 50 个章节 | 选择的章节数量超过上限，请分批操作。 | 否 | 减少选择章节数量 |
| `P2_VECTOR_WORK_NOT_FOUND` | 404 | 未找到对应作品 | 未找到对应作品。 | 否 | 检查作品是否存在 |
| `P2_VECTOR_CHAPTER_NOT_FOUND` | 404 | 未找到对应章节 | 未找到对应章节。 | 否 | 检查章节是否存在 |
| `P2_VECTOR_CHAPTER_NOT_IN_WORK` | 400 | 章节不属于指定作品 | 所选章节不属于当前作品，请刷新后重试。 | 否 | 刷新章节列表后重试 |
| `P2_VECTOR_INDEXING_IN_PROGRESS` | 409 | 该作品已有索引任务正在运行 | 这个作品已有索引任务正在运行，请等待完成后再试。 | 是 | 等待当前任务完成后重试，或取消当前任务 |
| `P2_VECTOR_IDEMPOTENCY_CONFLICT` | 409 | 幂等键冲突：相同键但不同参数 | 当前操作已提交，请勿重复执行。 | 否 | 检查是否重复提交 |
| `P2_VECTOR_CALLER_FORBIDDEN` | 403 | 调用方类型不被允许 | 当前请求来源不被允许。 | 否 | 无（不应在前端正常流程中出现） |
| `P2_VECTOR_EMBEDDING_UNAVAILABLE` | 503 | Embedding 服务不可用 | AI 嵌入服务暂时不可用，请稍后重试或检查 AI 设置。 | 是 | 检查 AI 设置中的模型配置，稍后重试 |
| `P2_VECTOR_STORE_UNAVAILABLE` | 503 | 向量存储服务不可用 | 向量存储服务暂时不可用，请稍后重试。 | 是 | 稍后重试 |
| `P2_VECTOR_REINDEX_FAILED` | 500 | 索引重建失败 | 索引重建失败，可以重试。 | 是 | 点击重试 |
| `P2_FEATURE_DISABLED` | 503 | 该功能未启用 | 该功能在当前版本未启用。 | 否 | 无 |

### 8.2 HTTP 状态码使用边界

| 状态码 | 使用场景 |
|---|---|
| **200** | 幂等复用已有 Job |
| **202** | 成功创建新 Job（异步执行） |
| **400** | 参数校验失败（scope 非法、缺少必填字段、条件冲突、章节归属错误） |
| **403** | caller_type 非 user_action |
| **404** | work 或 chapter 不存在 |
| **409** | 并发冲突（同 work 已有运行中任务）或 idempotency_key 冲突 |
| **422** | 不使用（当前项目未采用 422，业务校验错误统一使用 400） |
| **500** | 未预期的内部错误（通用兜底，safe_message 为"服务暂时不可用，请稍后重试。"） |
| **503** | Embedding Provider 不可用、Vector Store 不可用、Feature Flag 禁用 |

### 8.3 错误码在 `response_utils.py` 中的注册

在 `SAFE_MESSAGE_MAP` 中新增以下映射：

```python
"P2_VECTOR_INVALID_INDEX_SCOPE": "请选择"整部作品"或"指定章节"。",
"P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED": "请选择至少一个章节。",
"P2_VECTOR_TARGET_CHAPTER_IDS_NOT_ALLOWED": "全作品重建不需要选择章节，请取消章节选择后重试。",
"P2_VECTOR_TOO_MANY_CHAPTERS": "选择的章节数量超过上限，请分批操作。",
"P2_VECTOR_WORK_NOT_FOUND": "未找到对应作品。",
"P2_VECTOR_CHAPTER_NOT_FOUND": "未找到对应章节。",
"P2_VECTOR_CHAPTER_NOT_IN_WORK": "所选章节不属于当前作品，请刷新后重试。",
"P2_VECTOR_INDEXING_IN_PROGRESS": "这个作品已有索引任务正在运行，请等待完成后再试。",
"P2_VECTOR_IDEMPOTENCY_CONFLICT": "当前操作已提交，请勿重复执行。",
"P2_VECTOR_CALLER_FORBIDDEN": "当前请求来源不被允许。",
"P2_VECTOR_EMBEDDING_UNAVAILABLE": "AI 嵌入服务暂时不可用，请稍后重试或检查 AI 设置。",
"P2_VECTOR_STORE_UNAVAILABLE": "向量存储服务暂时不可用，请稍后重试。",
"P2_VECTOR_REINDEX_FAILED": "索引重建失败，可以重试。",
```

---

## 九、权限与安全边界

### 9.1 caller_type 规则

| caller_type | 允许调用 Reindex API | 说明 |
|---|---|---|
| `user_action` | **是** | 用户在 UI 中手动点击"重建索引" |
| `workflow` | **否** | Workflow 内部如需 reindex，走独立 Application Service 内部方法 |
| `quick_trial` | **否** | Quick Trial 不更新正式索引 |
| `system` | **否** | 系统初始化走 `VectorIndexService.build_initial_index()` |

- API 层校验 `caller_type != "user_action"` → `403 P2_VECTOR_CALLER_FORBIDDEN`。
- 使用 `_reject_invalid_caller_type` 模式（同 context_pack.py、continuation.py 等），不需要 `_ensure_gate_request`（reindex 不是门控操作，不需要 `user_action` 布尔字段和 `idempotency_key` 强制要求）。

### 9.2 禁止的操作

- Agent / Workflow 不得直接调用 Reindex API。
- Agent / Workflow 不得伪造 `caller_type = user_action` 调用 Reindex API。
- 系统初始化流程不得经过 Reindex API——必须通过 `InitializationApplicationService` 直接调用 `VectorIndexService.build_initial_index()`。
- reanalysis 受控触发 reindex 时，应由对应的 Application Service 直接调用 `VectorIndexService.reindex_work()` / `VectorIndexService.reindex_chapter()`，不经过 Reindex API。

### 9.3 数据隔离

Reindex API 只影响以下数据：

- `chapter_chunks` 表：新增/更新/标记 stale ChapterChunk 记录。
- `chunk_embeddings` 表：新增/更新/标记 stale ChunkEmbedding 记录。
- `vector_index_status` 表：更新 work 级索引状态。
- ChromaDB（VectorStore）：新增/更新/标记 stale 向量。

Reindex API **不影响**以下数据：

- 章节正文（chapter content）
- StoryState（analysis_baseline）
- StoryMemory（StoryMemorySnapshot）
- CandidateDraft
- 用户草稿（Workbench draft）
- 大纲（Outline）
- 人物、伏笔、时间线等写作资产

### 9.4 安全日志边界

以下信息**禁止**出现在任何日志（包括普通日志、AIJob context、Trace、错误响应）中：

| 禁止项 | 说明 |
|---|---|
| 完整章节正文 | 只记录 chapter_id 和字符数 |
| 完整 Chunk 文本（text_excerpt） | 只记录 chunk_id 和 content_hash |
| Embedding 原始向量 | 只记录 vector_id 和 embedding_model |
| query_text | reindex 不涉及 query |
| API Key | 绝对禁止 |
| Provider 鉴权信息 | 绝对禁止 |

**允许记录的信息**：
- work_id、chapter_id、chunk_id、vector_id
- index_scope、target_chapter_ids
- chunk 数量、embedding 数量、成功/失败计数
- index_status、stale_status
- 操作耗时（elapsed_ms）
- 错误类型（error_code）、warning 类型
- request_id、trace_id、job_id

**日志脱敏对齐 P0-05 §3.3**："普通日志记录完整正文、完整 chunk_text、完整 Prompt、API Key"明确列为禁止行为。

---

## 十、索引一致性与失败恢复

### 10.1 full_work 重建策略

**冻结决策：先构建新索引，成功后再切换（保留旧索引直到新索引就绪）。**

具体流程：
1. 读取所有 confirmed chapters，生成新 chunk 和 embedding。
2. 新 chunk/embedding/vector 全部写入成功后，标记旧 chunk/embedding/vector 为 stale。
3. 更新 work 级 `index_status`。

**关键保证**：
- 重建过程中旧索引仍然可用（旧 chunk 保持 active）。
- ContextPack 在重建期间仍可使用旧索引（允许 stale 召回仅用于重建中的降级场景）。
- 重建失败时旧索引不受影响——旧 chunk 保持 active，`index_status` 不变。
- **"重建失败不能让现有可用索引整体消失"**——这是核心安全保证。

> **实现注意 1**：当前 `VectorIndexService.reindex_work()` 的实现是"先标记所有 stale 再重建"（见 `vector_index_service.py` line 61-72）。此行为与上述冻结决策不一致——如果重建中途失败，旧索引已全部标记 stale 且新索引未完成，索引整体不可用。**需要在实现阶段修改 `reindex_work()` 方法，改为先构建新索引再切换**。

> **实现注意 2**：新索引构建过程中，同一 chunk 的新旧版本需要共存（旧版本保持 active，新版本暂标记为 building/pending）。VectorStore 中新旧向量通过不同的 `vector_id` 区分（旧 `vec_{chunk_id}` vs 新 `vec_{chunk_id}_v2` 或使用版本后缀），不依赖 ChromaDB 的 ID 覆盖。

### 10.2 chapter 模式替换策略

**冻结决策：先构建指定章节的新索引，成功后再标记该章节旧索引为 stale。**

流程：
1. 为 `target_chapter_ids` 中的每章读取正文，生成新 chunk 和 embedding。
2. 该章全部新 chunk/embedding/vector 写入成功后，标记该章旧 chunk/embedding/vector 为 stale。
3. 逐章处理：一章完成后再处理下一章。
4. 所有章节处理完毕后，更新 work 级 `index_status`。

**部分失败处理**：
- 如果某章重建失败，该章旧索引保持 active，`index_status` 按现有规则处理（可能为 `degraded` 或 `stale`）。
- 已成功重建的章节切换到新索引（旧索引标记 stale）。
- 失败的章节保留旧索引。

### 10.3 索引版本号

**冻结决策：不需要全局 `index_revision` 字段。使用 `updated_at` 时间戳 + `content_hash` 实现版本追踪。**

理由：
- 现有 `ChapterChunk.content_hash`（SHA-256）已足够判断 chunk 是否过期。
- `vector_index_status.updated_at` 记录最后一次索引更新时间。
- Embedding 的 `content_hash` 绑定确保 embedding 与 chunk 内容一致。
- 新增全局 `index_revision` 会增加复杂度且不解决现有问题。

### 10.4 半成品索引的可见性

**冻结决策：Job 成功（status = completed）前，新索引不得被正式 ContextPack 查询到。**

实现方式：
- 新 chunk 初始 `index_status = "building"` 或暂不写入 `chapter_chunks` 表（在内存中构建，成功后再批量写入）。
- VectorRecall 查询必须过滤 `index_status = "active"`（对齐 P0-05 §8.4）。
- 或者：新索引使用独立的临时 VectorStore collection，Job 成功后切换到主 collection。

> **实现注意**：当前 `VectorIndexService` 在 `reindex_work()` 中直接调用 `upsert_vector` 写入主 VectorStore，chunk 直接标记 active。此行为需要调整——在实现 Reindex API 时必须保证半成品索引不可见。

### 10.5 Job 失败后的补偿与重试

| 场景 | 旧索引状态 | 补偿策略 |
|---|---|---|
| reindex 全部失败 | 旧索引完整保留（active） | 用户可重试，旧索引不受影响 |
| reindex 部分失败 | 已完成的章节切换到新索引，失败的章节保留旧索引 | `index_status = degraded`，用户可对失败章节单独重试 |
| Job 被取消 | 保持取消前的状态 | 旧索引不受影响；已写入的新 chunk 标记 stale/deleted |
| cancel 后迟到写入 | 不污染 active index | P0-05 §12.3 规则：迟到结果不得标记 chunk active，最多记录脱敏日志 |

---

## 十一、API 示例

### 11.1 full_work 请求

```http
POST /api/v2/ai/vector-index/reindex
Content-Type: application/json
X-Request-Id: req_1718700000_abc123
X-Trace-Id: trace_a1b2c3d4e5f6

{
    "work_id": "work_1234567890ab",
    "index_scope": "full_work",
    "idempotency_key": "idem_reindex_work123_20260618_001",
    "force_rebuild": false,
    "reason": "修改了多章正文，需要重建索引以保证上下文召回准确",
    "caller_type": "user_action"
}
```

### 11.2 chapter 请求

```http
POST /api/v2/ai/vector-index/reindex
Content-Type: application/json
X-Request-Id: req_1718700000_def456
X-Trace-Id: trace_b2c3d4e5f6a7

{
    "work_id": "work_1234567890ab",
    "index_scope": "chapter",
    "target_chapter_ids": ["chapter_aaa111", "chapter_bbb222"],
    "idempotency_key": "idem_reindex_ch3_4_20260618_001",
    "force_rebuild": true,
    "reason": "重写了第3章和第4章，需要重新索引",
    "caller_type": "user_action"
}
```

### 11.3 202 成功创建响应

```json
{
    "request_id": "req_1718700000_abc123",
    "trace_id": "trace_a1b2c3d4e5f6",
    "status": "ok",
    "data": {
        "job_id": "job_d7e8f9a0b1c2",
        "job_type": "vector_indexing",
        "operation": "reindex",
        "work_id": "work_1234567890ab",
        "index_scope": "full_work",
        "target_chapter_ids": [],
        "status": "queued",
        "created_at": "2026-06-18T10:30:00.000000",
        "request_id": "req_1718700000_abc123",
        "trace_id": "trace_a1b2c3d4e5f6",
        "polling_hint": {
            "next_poll_after_ms": 3000,
            "max_poll_interval_ms": 10000,
            "timeout_hint_ms": 300000,
            "still_running_message": "索引重建中，请耐心等待。"
        },
        "reused_existing_job": false
    }
}
```

### 11.4 幂等复用已有 Job 响应（200）

```json
{
    "request_id": "req_1718700000_xyz789",
    "trace_id": "trace_c3d4e5f6a7b8",
    "status": "ok",
    "data": {
        "job_id": "job_d7e8f9a0b1c2",
        "job_type": "vector_indexing",
        "operation": "reindex",
        "work_id": "work_1234567890ab",
        "index_scope": "full_work",
        "target_chapter_ids": [],
        "status": "running",
        "created_at": "2026-06-18T10:30:00.000000",
        "request_id": "req_1718700000_xyz789",
        "trace_id": "trace_c3d4e5f6a7b8",
        "polling_hint": {
            "next_poll_after_ms": 3000,
            "max_poll_interval_ms": 10000,
            "timeout_hint_ms": 300000,
            "still_running_message": "索引重建中，请耐心等待。"
        },
        "reused_existing_job": true
    }
}
```

### 11.5 chapter 缺少 target_chapter_ids 错误（400）

```json
{
    "request_id": "req_1718700000_err001",
    "trace_id": "trace_e1f2a3b4c5d6",
    "status": "error",
    "error": {
        "error_code": "P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED",
        "safe_message": "请选择至少一个章节。",
        "retryable": false
    }
}
```

### 11.6 已有任务运行中的 409 错误

```json
{
    "request_id": "req_1718700000_err002",
    "trace_id": "trace_f2a3b4c5d6e7",
    "status": "error",
    "error": {
        "error_code": "P2_VECTOR_INDEXING_IN_PROGRESS",
        "safe_message": "这个作品已有索引任务正在运行，请等待完成后再试。",
        "retryable": true
    }
}
```

### 11.7 caller_type 非 user_action 的 403 错误

```json
{
    "request_id": "req_1718700000_err003",
    "trace_id": "trace_a3b4c5d6e7f8",
    "status": "error",
    "error": {
        "error_code": "P2_VECTOR_CALLER_FORBIDDEN",
        "safe_message": "当前请求来源不被允许。",
        "retryable": false
    }
}
```

---

## 十二、前端交互边界

### 12.1 UI 入口建议

| 位置 | 入口形式 | 说明 |
|---|---|---|
| WritingStudio 右侧面板 | "向量索引" Tab 或 Settings 区域的"重建索引"按钮 | 主要入口 |
| AIPanel 状态区 | 当索引状态为 stale 时显示"索引已过期，点击重建"提示 | 被动提示 |
| 章节列表右键菜单 | "重新索引此章" | 单章快捷操作 |

### 12.2 用户交互流程

1. 用户点击"重建索引"按钮（或从 stale 提示进入）。
2. 弹出确认对话框：
   - 整部作品：显示"将重建全部已确认章节的向量索引，预计需要 X 分钟。"
   - 指定章节：显示已选章节列表，"将对已选的 N 个章节重建向量索引。"
3. 用户确认 → 发送 POST 请求（携带 `idempotency_key`）。
4. 收到 202 → 显示"索引重建已加入队列"，开始轮询 `GET /api/v2/ai/jobs/{job_id}`。
5. 轮询期间显示进度条（基于 `AIJobProgress.percent`）+ "正在重建索引"文案。
6. Job 完成 → 显示"索引重建完成"。
7. Job 失败 → 显示"索引重建失败，可以重试"，提供"重试"按钮。

### 12.3 重复点击处理

- 前端在发送请求后立即禁用"重建索引"按钮，直到收到响应。
- 如果收到 200（`reused_existing_job = true`）：不弹新对话框，直接跳转到已有 Job 的进度轮询。
- 如果收到 409（`P2_VECTOR_INDEXING_IN_PROGRESS`）：显示"这个作品已有索引任务正在运行"，引导用户查看现有任务。
- 页面刷新后：前端通过 `idempotency_key`（保存到 sessionStorage 或 Pinia store）重新请求 API，自动恢复到已有 Job 的轮询状态。

### 12.4 取消操作

- 运行中的 reindex Job 可通过 `POST /api/v2/ai/jobs/{job_id}/cancel` 取消。
- UI 在进度轮询期间显示"取消"按钮。

### 12.5 用户可见文案

所有用户可见文案必须使用**中文白话**，不暴露技术标识符：

| 场景 | 用户文案 |
|---|---|
| 正在重建索引 | "正在重建索引..." |
| 索引重建已加入队列 | "索引重建已加入队列，即将开始。" |
| 已有任务运行 | "这个作品已有索引任务正在运行，请等待完成后再试。" |
| 缺少章节选择 | "请选择至少一个章节。" |
| 索引重建完成 | "索引重建完成。" |
| 索引重建失败 | "索引重建失败，可以重试。" |
| 部分成功（degraded） | "索引部分重建成功，部分章节的索引可能不完整。可以针对失败章节单独重建。" |
| Embedding 不可用 | "AI 嵌入服务暂时不可用，请确保已在 AI 设置中配置嵌入模型。" |
| 点击重建确认（full_work） | "将重建全部已确认章节的向量索引。重建期间续写仍可使用现有索引。确认开始？" |
| 点击重建确认（chapter） | "将对已选的 N 个章节重建向量索引。确认开始？" |

### 12.6 前端轮询参数

| 参数 | 值 | 说明 |
|---|---|---|
| 初始轮询间隔 | 3000ms | 从 `polling_hint.next_poll_after_ms` 获取 |
| 最大轮询间隔 | 10000ms | 从 `polling_hint.max_poll_interval_ms` 获取 |
| 预估超时 | 300000ms（5 分钟） | 从 `polling_hint.timeout_hint_ms` 获取 |
| 终态 | `completed`、`failed`、`cancelled`、`partial_success` | 进入终态后停止轮询 |

---

## 十三、测试要求

### 13.1 正向测试

| # | 测试名称 | 测试场景 | 预期结果 |
|---|---|---|---|
| T1 | `test_reindex_api_full_work_creates_job` | POST full_work 请求 | 202，返回 job_id，status=queued |
| T2 | `test_reindex_api_single_chapter_creates_job` | POST chapter 请求，1 个章节 | 202，返回 job_id，target_chapter_ids 正确 |
| T3 | `test_reindex_api_multi_chapter_creates_job` | POST chapter 请求，3 个章节 | 202，返回 job_id，target_chapter_ids 正确 |
| T4 | `test_reindex_api_idempotency_returns_existing_job` | 相同 idempotency_key 重复请求 | 200，reused_existing_job=true |
| T5 | `test_reindex_api_job_completed_index_status_updated` | Job 完成后查询 index_status | index_status 为 ready 或 degraded |
| T6 | `test_reindex_api_status_query_via_job_api` | GET /api/v2/ai/jobs/{job_id} | 返回 Job 状态和进度 |
| T7 | `test_reindex_api_cancel_via_job_api` | POST /api/v2/ai/jobs/{job_id}/cancel | Job 状态变为 cancelled |
| T8 | `test_reindex_api_retry_failed_job` | 失败 Job 重试 | 重试后 Job 重新执行 |
| T9 | `test_reindex_api_force_rebuild_creates_new_job` | force_rebuild=true, 已有 completed Job | 202，创建新 Job（不复用已完成 Job） |
| T10 | `test_reindex_api_old_index_preserved_on_failure` | 重建失败 | 旧索引保持 active，VectorRecall 仍可召回 |

### 13.2 反向测试

| # | 测试名称 | 测试场景 | 预期结果 |
|---|---|---|---|
| T11 | `test_reindex_api_invalid_scope_rejected` | index_scope = "invalid" | 400，P2_VECTOR_INVALID_INDEX_SCOPE |
| T12 | `test_reindex_api_chapter_missing_target_ids_rejected` | index_scope=chapter，无 target_chapter_ids | 400，P2_VECTOR_TARGET_CHAPTER_IDS_REQUIRED |
| T13 | `test_reindex_api_full_work_with_target_ids_rejected` | index_scope=full_work，传入 target_chapter_ids | 400，P2_VECTOR_TARGET_CHAPTER_IDS_NOT_ALLOWED |
| T14 | `test_reindex_api_chapter_not_in_work_rejected` | target_chapter_ids 包含不属于 work 的章节 | 400，P2_VECTOR_CHAPTER_NOT_IN_WORK |
| T15 | `test_reindex_api_work_not_found` | work_id 不存在 | 404，P2_VECTOR_WORK_NOT_FOUND |
| T16 | `test_reindex_api_agent_caller_rejected` | caller_type = "workflow" | 403，P2_VECTOR_CALLER_FORBIDDEN |
| T17 | `test_reindex_api_system_caller_rejected` | caller_type = "system" | 403，P2_VECTOR_CALLER_FORBIDDEN |
| T18 | `test_reindex_api_concurrent_rejected` | 同一 work 已有 running Job 时再次请求 | 409，P2_VECTOR_INDEXING_IN_PROGRESS |
| T19 | `test_reindex_api_embedding_unavailable` | Embedding Provider 未配置 | 503，P2_VECTOR_EMBEDDING_UNAVAILABLE |
| T20 | `test_reindex_api_vector_store_unavailable` | ChromaDB 不可用 | 503，P2_VECTOR_STORE_UNAVAILABLE |
| T21 | `test_reindex_api_idempotency_key_mismatch_conflict` | 相同 idempotency_key，不同 target_chapter_ids | 409，P2_VECTOR_IDEMPOTENCY_CONFLICT |
| T22 | `test_reindex_api_log_excludes_full_text` | 重建过程中检查日志 | 日志不含完整正文、chunk_text、向量、API Key |
| T23 | `test_reindex_api_log_excludes_chunk_text` | 检查 AIJob.result_summary | result_summary 不含 chunk text_excerpt |
| T24 | `test_reindex_api_response_excludes_internal_data` | 检查 API 响应 | 响应不含 payload、input_snapshot、params、metadata |
| T25 | `test_reindex_api_too_many_chapters_rejected` | target_chapter_ids 超过 50 个 | 400，P2_VECTOR_TOO_MANY_CHAPTERS |

### 13.3 测试注意事项

- AIJob 相关测试复用 `tests/ai/test_vector_reindex_service.py` 中的现有测试模式和 fixture。
- Embedding 和 Vector Store 依赖使用 `LocalEmbeddingProvider`（确定性）和临时 ChromaDB 目录（`tmp_path`）。
- caller_type 校验在 API 层测试（`tests/ai/test_reindex_api.py`，新文件），使用 FastAPI `TestClient`。
- 并发冲突测试需要模拟同 work_id 已有非终态 vector_indexing Job 的场景。
- 日志脱敏测试需要捕获日志输出并断言不包含禁止项。

---

## 十四、实现改动面

### 14.1 新增文件

| # | 文件 | 说明 |
|---|---|---|
| 1 | `presentation/api/routers/v2/ai/vector_index.py` | Reindex API 路由（Router、DTO、验证函数） |
| 2 | `tests/ai/test_reindex_api.py` | Reindex API 测试（正向 10 + 反向 15） |

### 14.2 修改文件

| # | 文件 | 改动说明 |
|---|---|---|
| 1 | `presentation/api/app.py` | 注册 `vector_index.router` |
| 2 | `presentation/api/routers/v2/ai/response_utils.py` | 新增 P2_VECTOR_* 错误码的 safe_message 映射 |
| 3 | `application/services/ai/vector_reindex_service.py` | 新增：idempotency_key 匹配逻辑、并发冲突检测、force_rebuild 语义、reason 字段存入 payload |
| 4 | `application/services/ai/vector_index_service.py` | 修改：`reindex_work()` 改为先构建后切换策略；新 chunk 初始不可见 |
| 5 | `domain/entities/ai/models.py` | AIJob 实体可选新增 `idempotency_key` 字段（用于幂等匹配） |
| 6 | `domain/repositories/ai/ai_job_repository.py` | 可选新增 `find_by_idempotency_key()` 查询方法（如 `VectorReindexApplicationService` 需要） |
| 7 | `infrastructure/database/repositories/ai/file_ai_job_store.py` | 实现 `find_by_idempotency_key()`（如新增） |

### 14.3 复用现有能力（不改动）

| # | 能力 | 来源 |
|---|---|---|
| 1 | AIJob 创建、状态查询、取消 | `AIJobService` + `jobs.py` API |
| 2 | AIJob 状态机（queued/running/paused/failed/cancelled/completed） | `AIJobService` |
| 3 | Step 生命周期（pending/running/completed/failed/skipped） | `AIJobService` |
| 4 | Job 轮询（GET /api/v2/ai/jobs/{job_id}） | `jobs.py` |
| 5 | VectorIndexService.reindex_work / reindex_chapter | `vector_index_service.py` |
| 6 | VectorReindexApplicationService 基础骨架（start_reindex、run_reindex、cancel、pause、resume、retry） | `vector_reindex_service.py` |
| 7 | EmbeddingProviderPort / VectorStorePort / VectorIndexRepositoryPort | domain ports |
| 8 | 统一响应格式（success_response / error_response） | `response_utils.py` |
| 9 | caller_type 校验模式（`_reject_invalid_caller_type`） | 多个 V2 路由已有模板 |
| 10 | DI 注入（`get_vector_reindex_service()`） | `dependencies.py` |
| 11 | P2 Feature Flag 中间件（不拦截 vector-index 路径） | `p2_feature_flag.py` |

### 14.4 改动量评估

| 类别 | 改动量 | 说明 |
|---|---|---|
| 新增代码 | ~200 行 | Router + DTO + 测试 |
| 修改代码 | ~150 行 | vector_reindex_service + vector_index_service + response_utils |
| 设计风险 | 中 | `reindex_work()` 的先构建后切换策略需要修改现有实现 |
| 测试工作量 | ~25 个测试用例 | 10 正向 + 15 反向 |

---

## 十五、冻结结论

### 15.1 已冻结决策

| # | 决策 | 结论 |
|---|---|---|
| 1 | 接口数量 | **1 个**：`POST /api/v2/ai/vector-index/reindex` |
| 2 | 模式区分 | 通过 `index_scope` 字段：`full_work` \| `chapter` |
| 3 | 执行模型 | **异步**：创建 AIJob（`job_type = "vector_indexing"`），返回 202 |
| 4 | AIJob 复用 | **是**：完全复用现有 AIJob 系统 |
| 5 | caller_type | **仅 `user_action`**，Agent/Workflow/system 调用返回 403 |
| 6 | Feature Flag | **不需要**独立 P2 Feature Flag |
| 7 | full_work + target_chapter_ids | **拒绝**（400），不静默忽略 |
| 8 | chapter + 无 target_chapter_ids | **拒绝**（400） |
| 9 | 并发策略 | **同 work 互斥**：同一 work 同时只允许一个 vector_indexing 写任务 |
| 10 | 幂等策略 | idempotency_key 匹配 → 返回已有 Job；不匹配 → 409 |
| 11 | 多个不重叠 chapter 并行 | **不允许**，保守互斥 |
| 12 | full_work 重建策略 | **先构建后切换**：旧索引可用直到新索引就绪 |
| 13 | 索引版本号 | **不需要**全局 revision，使用 content_hash + updated_at |
| 14 | 半成品可见性 | **不可见**：Job 成功前新索引不对 ContextPack 暴露 |
| 15 | retry 语义 | **完整重跑** build_vector_index Step |
| 16 | 暂停/恢复/重试 API | **不新增**专用端点，复用现有 Job API（暂停/恢复当前仅 service 层） |

### 15.2 仍待确认项

| # | 待确认项 | 推荐默认值 | 影响 | 建议确认方 |
|---|---|---|---|---|
| A1 | AIJob 实体是否需要新增 `idempotency_key` 字段 | **是**，新增 optional 字段 | 低——不影响 API 契约，仅影响 Repository 实现方式 | 架构评审 |
| A2 | `FileAIJobStore` 中的 idempotency_key 查询性能（JSON 文件遍历） | 当前作品量级下可接受；后期可优化为内存索引 | 低——P0 阶段作品量小 | 架构评审 |
| A3 | `reindex_work()` 先构建后切换策略的实现复杂度 | 需要重构现有实现（当前是先 stale 再重建） | 中——是安全性的关键保证 | 架构评审 + 开发估时 |

### 15.3 是否已达到可编码状态

**是。本文档已冻结足够多的决策，可以直接指导后端实现。**

待确认项 A1~A3 可在编码过程中按推荐默认值执行，不影响 API 契约的稳定性。如果在编码过程中发现推荐默认值不可行，再回到本文档修改对应决策。

### 15.4 文档版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-06-18 | 初始冻结版：完成全部 15 章设计，冻结 16 项关键决策 |

---

> **本文档完结。**
>
> 本文档是 Reindex API 的唯一冻结契约。后续实现、测试、验收均以此文档为准。如有冲突，以本文档为准，并更新本文档版本。
