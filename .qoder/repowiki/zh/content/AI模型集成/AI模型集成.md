# AI模型集成

<cite>
**本文引用的文件**
- [llm_factory.py](file://infrastructure/llm/llm_factory.py)
- [base_client.py](file://infrastructure/llm/base_client.py)
- [deepseek_client.py](file://infrastructure/llm/deepseek_client.py)
- [kimi_client.py](file://infrastructure/llm/kimi_client.py)
- [llm_config.py](file://domain/entities/llm_config.py)
- [llm_config_repository.py](file://domain/repositories/llm_config_repository.py)
- [exceptions.py](file://domain/exceptions.py)
- [sqlite_llm_config_repo.py](file://infrastructure/persistence/sqlite_llm_config_repo.py)
- [config.py](file://presentation/api/routers/config.py)
- [config.js](file://frontend/src/api/config.js)
- [config.js（store）](file://frontend/src/stores/config.js)
- [LLMConfig.vue](file://frontend/src/views/config/LLMConfig.vue)
- [model_router.py](file://application/agent_mvp/model_router.py)
- [orchestrator.py](file://application/agent_mvp/orchestrator.py)
- [tools.py](file://application/agent_mvp/tools.py)
- [recovery.py](file://application/agent_mvp/recovery.py)
- [test_llm_client.py](file://tests/unit/test_llm_client.py)
- [test_llm_client_improved.py](file://tests/unit/test_llm_client_improved.py)
- [test_recovery.py](file://tests/unit/test_recovery.py)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖分析](#依赖分析)
7. [性能考虑](#性能考虑)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介
本文件面向InkTrace项目的AI模型集成，系统性阐述基于工厂模式的大模型客户端统一管理方案，详解DeepSeek与Kimi两大模型的接入方式、参数配置、错误处理与主备切换机制；并覆盖LLM配置管理（API密钥、模型参数、调用频率限制）、模型选择策略与性能优化、最佳实践与调试方法，以及如何扩展新的AI模型支持。本次更新重点介绍了新增的JSON提取工具和增强的LLM交互模式，提供更强大的解析能力和错误处理机制。

## 项目结构
围绕AI模型集成的关键目录与文件如下：
- 基础接口与客户端：infrastructure/llm 下的抽象接口与具体实现
- 工厂与配置：llm_factory、llm_config 实体与仓储
- 异常体系：domain/exceptions 统一错误类型
- 后端API：presentation/api/routers/config 提供配置读写与测试
- 前端配置界面与状态：frontend/src/views/config 与 stores
- 应用编排：application/agent_mvp/model_router 与 orchestrator 的调用链路
- 工具与恢复：application/agent_mvp/tools 与 recovery 提供JSON提取和错误恢复机制

```mermaid
graph TB
subgraph "基础设施"
BC["LLMClient 抽象接口<br/>base_client.py"]
DS["DeepSeek 客户端<br/>deepseek_client.py"]
KM["Kimi 客户端<br/>kimi_client.py"]
F["LLM 工厂<br/>llm_factory.py"]
ENDP["JSON提取工具<br/>tools.py"]
RP["恢复管道<br/>recovery.py"]
end
subgraph "领域"
EX["异常体系<br/>exceptions.py"]
EC["LLM 配置实体<br/>llm_config.py"]
ER["LLM 配置仓储接口<br/>llm_config_repository.py"]
end
subgraph "持久化"
SR["SQLite LLM 配置仓储<br/>sqlite_llm_config_repo.py"]
end
subgraph "后端API"
CFG["配置API路由<br/>config.py"]
end
subgraph "前端"
FEV["配置页面<br/>LLMConfig.vue"]
FES["配置Store<br/>config.jsstore"]
FEA["配置API封装<br/>config.jsapi"]
end
subgraph "应用编排"
MR["模型路由<br/>model_router.py"]
ORCH["编排器<br/>orchestrator.py"]
end
BC --> DS
BC --> KM
F --> DS
F --> KM
CFG --> SR
CFG --> EC
CFG --> ER
FEV --> FES
FES --> FEA
MR --> F
ORCH --> MR
ENDP --> MR
RP --> ENDP
```

**图表来源**
- [base_client.py:14-83](file://infrastructure/llm/base_client.py#L14-L83)
- [deepseek_client.py:25-238](file://infrastructure/llm/deepseek_client.py#L25-L238)
- [kimi_client.py:25-244](file://infrastructure/llm/kimi_client.py#L25-L244)
- [llm_factory.py:31-121](file://infrastructure/llm/llm_factory.py#L31-L121)
- [exceptions.py:51-100](file://domain/exceptions.py#L51-L100)
- [llm_config.py:15-54](file://domain/entities/llm_config.py#L15-L54)
- [llm_config_repository.py:16-68](file://domain/repositories/llm_config_repository.py#L16-L68)
- [sqlite_llm_config_repo.py:18-145](file://infrastructure/persistence/sqlite_llm_config_repo.py#L18-L145)
- [config.py:19-173](file://presentation/api/routers/config.py#L19-L173)
- [LLMConfig.vue:1-285](file://frontend/src/views/config/LLMConfig.vue#L1-L285)
- [config.js（store）:14-240](file://frontend/src/stores/config.js#L14-L240)
- [config.js:1-240](file://frontend/src/api/config.js#L1-L240)
- [model_router.py:6-42](file://application/agent_mvp/model_router.py#L6-L42)
- [orchestrator.py:17-212](file://application/agent_mvp/orchestrator.py#L17-L212)
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)
- [recovery.py:15-51](file://application/agent_mvp/recovery.py#L15-L51)

**章节来源**
- [llm_factory.py:1-121](file://infrastructure/llm/llm_factory.py#L1-L121)
- [base_client.py:1-83](file://infrastructure/llm/base_client.py#L1-L83)
- [deepseek_client.py:1-238](file://infrastructure/llm/deepseek_client.py#L1-L238)
- [kimi_client.py:1-244](file://infrastructure/llm/kimi_client.py#L1-L244)
- [llm_config.py:1-54](file://domain/entities/llm_config.py#L1-L54)
- [llm_config_repository.py:1-68](file://domain/repositories/llm_config_repository.py#L1-L68)
- [exceptions.py:1-100](file://domain/exceptions.py#L1-L100)
- [sqlite_llm_config_repo.py:1-145](file://infrastructure/persistence/sqlite_llm_config_repo.py#L1-L145)
- [config.py:1-173](file://presentation/api/routers/config.py#L1-L173)
- [LLMConfig.vue:1-285](file://frontend/src/views/config/LLMConfig.vue#L1-L285)
- [config.js（store）:1-240](file://frontend/src/stores/config.js#L1-L240)
- [config.js:1-240](file://frontend/src/api/config.js#L1-L240)
- [model_router.py:1-42](file://application/agent_mvp/model_router.py#L1-L42)
- [orchestrator.py:1-212](file://application/agent_mvp/orchestrator.py#L1-L212)
- [tools.py:1-1018](file://application/agent_mvp/tools.py#L1-L1018)
- [recovery.py:1-51](file://application/agent_mvp/recovery.py#L1-L51)

## 核心组件
- 抽象接口 LLMClient：定义 generate/chat/model_name/max_context_tokens/is_available 等标准方法，保证不同模型客户端的一致行为契约。
- 具体客户端 DeepSeekClient/KimiClient：分别封装对应平台的API调用、参数组装、重试与错误处理、连接池与可用性探测。
- LLM 工厂 LLMFactory：负责主备模型的按需实例化、可用性检测与切换、当前客户端缓存。
- 配置与仓储：LLMConfig 实体与 SQLiteLLMConfigRepository 提供配置的持久化与查询。
- 异常体系：统一的 LLMClientError 及其子类（APIKeyError、RateLimitError、NetworkError、TokenLimitError）便于上层捕获与处理。
- 前后端配置通道：后端 FastAPI 路由提供配置读取/保存/测试；前端 Store/API 组件完成用户交互与状态同步。
- JSON提取工具：提供强大的JSON解析能力，支持代码围栏去除、对象和数组提取、容错处理。
- 恢复管道：实现多阶段错误恢复机制，包括重试、修复、回退和降级处理。

**章节来源**
- [base_client.py:14-83](file://infrastructure/llm/base_client.py#L14-L83)
- [deepseek_client.py:25-238](file://infrastructure/llm/deepseek_client.py#L25-L238)
- [kimi_client.py:25-244](file://infrastructure/llm/kimi_client.py#L25-L244)
- [llm_factory.py:31-121](file://infrastructure/llm/llm_factory.py#L31-L121)
- [llm_config.py:15-54](file://domain/entities/llm_config.py#L15-L54)
- [sqlite_llm_config_repo.py:18-145](file://infrastructure/persistence/sqlite_llm_config_repo.py#L18-L145)
- [exceptions.py:51-100](file://domain/exceptions.py#L51-L100)
- [config.py:19-173](file://presentation/api/routers/config.py#L19-L173)
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)
- [recovery.py:15-51](file://application/agent_mvp/recovery.py#L15-L51)

## 架构总览
下图展示从前端配置到后端API再到LLM客户端工厂与具体模型的完整调用链与数据流，包括新增的JSON提取和恢复机制。

```mermaid
sequenceDiagram
participant FE as "前端页面<br/>LLMConfig.vue"
participant FS as "前端Store<br/>config.jsstore"
participant FA as "前端API封装<br/>config.js"
participant API as "后端路由<br/>config.py"
participant SVC as "配置服务<br/>ConfigService"
participant REPO as "仓储<br/>SQLiteLLMConfigRepository"
participant ENT as "实体<br/>LLMConfig"
participant FAC as "工厂<br/>LLMFactory"
participant PRI as "主模型<br/>DeepSeekClient"
participant BAK as "备模型<br/>KimiClient"
participant TOOL as "工具<br/>tools.py"
participant RP as "恢复管道<br/>recovery.py"
FE->>FS : 打开配置页/加载状态
FS->>FA : 调用 getLLMConfig()
FA->>API : GET /api/config/llm
API->>SVC : 获取配置
SVC->>REPO : 查询配置
REPO-->>SVC : 返回实体
SVC-->>API : 返回解密后的配置
API-->>FA : 返回配置数据
FA-->>FS : 更新本地状态
FE->>FS : 保存配置/测试
FS->>FA : 调用 updateLLMConfig()/testLLMConfig()
FA->>API : POST /api/config/llm 或 POST /api/config/llm/test
API->>SVC : 校验/保存/测试
SVC->>REPO : 保存或测试连接
REPO-->>SVC : 结果
SVC-->>API : 结果
API-->>FA : 返回结果
FA-->>FS : 回调通知
Note over FAC,PRI : 运行时获取客户端
FS->>FAC : 获取可用客户端
FAC->>PRI : is_available()
PRI-->>FAC : 可用/不可用
FAC-->>FS : 返回当前客户端
Note over TOOL,RP : 新增JSON提取和恢复机制
FS->>TOOL : 调用LLM工具
TOOL->>RP : 执行恢复管道
RP->>PRI : 主模型调用
PRI-->>RP : 成功/失败
RP->>BAK : 备用模型调用
BAK-->>RP : 成功/失败
RP-->>TOOL : 返回结果
TOOL-->>FS : JSON提取和解析
```

**图表来源**
- [LLMConfig.vue:104-164](file://frontend/src/views/config/LLMConfig.vue#L104-L164)
- [config.js（store）:42-107](file://frontend/src/stores/config.js#L42-L107)
- [config.js:1-240](file://frontend/src/api/config.js#L1-L240)
- [config.py:67-147](file://presentation/api/routers/config.py#L67-L147)
- [sqlite_llm_config_repo.py:92-110](file://infrastructure/persistence/sqlite_llm_config_repo.py#L92-L110)
- [llm_factory.py:78-121](file://infrastructure/llm/llm_factory.py#L78-L121)
- [deepseek_client.py:213-227](file://infrastructure/llm/deepseek_client.py#L213-L227)
- [kimi_client.py:219-227](file://infrastructure/llm/kimi_client.py#L219-L227)
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)
- [recovery.py:19-51](file://application/agent_mvp/recovery.py#L19-L51)

## 详细组件分析

### 工厂模式与主备切换
- 设计要点
  - 抽象接口 LLMClient 统一不同模型客户端的行为契约。
  - LLMFactory 负责延迟创建主/备客户端，并根据 is_available() 决定当前可用客户端。
  - 提供显式切换接口 switch_to_backup/reset_to_primary，便于运行时干预。
- 关键流程
  - 获取客户端：优先检测主模型可用性，否则回退到备模型。
  - 切换逻辑：手动切换或重置为主模型，均基于可用性探测。
- 适用场景
  - 稳定性：主模型故障时自动切备模型。
  - 可运维性：支持强制切换与恢复，便于维护窗口内的主动切换。

```mermaid
flowchart TD
Start(["获取客户端"]) --> CheckCur{"已有当前客户端?"}
CheckCur --> |是| ReturnCur["返回当前客户端"]
CheckCur --> |否| ProbePri["探测主模型可用性"]
ProbePri --> PriAvail{"主模型可用?"}
PriAvail --> |是| SetPri["设置当前客户端=主模型"]
PriAvail --> |否| SetBak["设置当前客户端=备模型"]
SetPri --> ReturnCur
SetBak --> ReturnCur
ReturnCur --> End(["结束"])
```

**图表来源**
- [llm_factory.py:78-95](file://infrastructure/llm/llm_factory.py#L78-L95)
- [llm_factory.py:97-121](file://infrastructure/llm/llm_factory.py#L97-L121)
- [deepseek_client.py:213-227](file://infrastructure/llm/deepseek_client.py#L213-L227)
- [kimi_client.py:219-227](file://infrastructure/llm/kimi_client.py#L219-L227)

**章节来源**
- [llm_factory.py:31-121](file://infrastructure/llm/llm_factory.py#L31-L121)
- [base_client.py:14-83](file://infrastructure/llm/base_client.py#L14-L83)

### DeepSeek 客户端集成
- 能力与特性
  - 支持 generate/chat 接口，可选 system_prompt。
  - 参数：max_tokens、temperature；内部对输入进行字符级截断以控制Token。
  - 连接复用：使用 httpx.AsyncClient 并配置连接池与超时。
  - 错误处理：针对 401、429、5xx 等状态码抛出特定异常；支持指数退避重试。
  - 可用性探测：通过一次短文本生成测试连通性。
- 关键点
  - 基础URL与模型名可配置，默认值见工厂配置。
  - 日志记录便于问题定位。

**章节来源**
- [deepseek_client.py:25-238](file://infrastructure/llm/deepseek_client.py#L25-L238)

### Kimi（Moonshot）客户端集成
- 能力与特性
  - 与 DeepSeek 类似的接口与错误处理策略。
  - 模型上下文长度根据模型后缀动态判定（如 128k/32k/8k）。
  - 同样具备连接复用、重试与可用性探测。
- 关键点
  - 不同模型族的上下文上限差异，需在调用侧合理设置 max_tokens。

**章节来源**
- [kimi_client.py:25-244](file://infrastructure/llm/kimi_client.py#L25-L244)

### LLM 配置管理
- 配置实体与仓储
  - LLMConfig 实体包含 DeepSeek/Kimi 密钥、加密密钥哈希与时间戳。
  - ILLMConfigRepository 定义保存/获取/删除/存在性检查接口。
  - SQLiteLLMConfigRepository 提供 SQLite 实现，含建表、CRUD、历史查询。
- 后端API
  - 提供 /api/config/llm 的 GET/POST/DELETE 与 /api/config/llm/test 的测试接口。
  - 依赖注入配置服务，统一处理校验、保存与测试。
- 前端配置界面
  - LLMConfig.vue 展示配置状态、提供删除与测试能力。
  - Store/Api 封装了加载、保存、测试与状态更新逻辑。

```mermaid
classDiagram
class LLMConfig {
+int id
+string deepseek_api_key
+string kimi_api_key
+string encryption_key_hash
+datetime created_at
+datetime updated_at
+has_valid_config() bool
+validate() bool
}
class ILLMConfigRepository {
<<interface>>
+save(config) LLMConfig
+get() LLMConfig
+delete() bool
+exists() bool
}
class SQLiteLLMConfigRepository {
+save(config) LLMConfig
+get() LLMConfig
+delete() bool
+exists() bool
+get_all() list
}
ILLMConfigRepository <|.. SQLiteLLMConfigRepository
LLMConfig ..> SQLiteLLMConfigRepository : "被仓储持久化"
```

**图表来源**
- [llm_config.py:15-54](file://domain/entities/llm_config.py#L15-L54)
- [llm_config_repository.py:16-68](file://domain/repositories/llm_config_repository.py#L16-L68)
- [sqlite_llm_config_repo.py:18-145](file://infrastructure/persistence/sqlite_llm_config_repo.py#L18-L145)

**章节来源**
- [llm_config.py:15-54](file://domain/entities/llm_config.py#L15-L54)
- [llm_config_repository.py:16-68](file://domain/repositories/llm_config_repository.py#L16-L68)
- [sqlite_llm_config_repo.py:18-145](file://infrastructure/persistence/sqlite_llm_config_repo.py#L18-L145)
- [config.py:19-173](file://presentation/api/routers/config.py#L19-L173)
- [LLMConfig.vue:1-285](file://frontend/src/views/config/LLMConfig.vue#L1-L285)
- [config.js（store）:14-240](file://frontend/src/stores/config.js#L14-L240)
- [config.js:1-240](file://frontend/src/api/config.js#L1-L240)

### 模型选择策略与应用编排
- 模型路由 ModelRouter
  - 优先尝试主模型 generate；若失败则回退备模型；若两者均失败则终止。
  - 返回结果包含 ok、text、route（primary/backup/terminate）与 primary_error 信息，便于上层决策。
- 编排器 Orchestrator
  - 在工具执行失败时结合可重试标记决定是否重试。
  - 与模型路由配合，形成"主模型优先、备模型兜底"的稳定输出链路。

```mermaid
sequenceDiagram
participant ORCH as "编排器<br/>orchestrator.py"
participant MR as "模型路由<br/>model_router.py"
participant PRI as "主模型<br/>DeepSeekClient"
participant BAK as "备模型<br/>KimiClient"
ORCH->>MR : generate(prompt, ...)
alt 有主模型
MR->>PRI : generate(...)
PRI-->>MR : 成功/失败
alt 成功
MR-->>ORCH : {"ok" : True, "route" : "primary"}
else 失败
MR->>BAK : generate(...)
BAK-->>MR : 成功/失败
alt 成功
MR-->>ORCH : {"ok" : True, "route" : "backup"}
else 失败
MR-->>ORCH : {"ok" : False, "route" : "terminate", "error" : "...", "primary_error" : "..."}
end
end
else 无主模型
MR-->>ORCH : {"ok" : False, "route" : "terminate", "error" : "primary_unavailable"}
end
```

**图表来源**
- [model_router.py:11-42](file://application/agent_mvp/model_router.py#L11-L42)
- [orchestrator.py:189-191](file://application/agent_mvp/orchestrator.py#L189-L191)

**章节来源**
- [model_router.py:6-42](file://application/agent_mvp/model_router.py#L6-L42)
- [orchestrator.py:17-212](file://application/agent_mvp/orchestrator.py#L17-L212)

### JSON提取工具与增强的LLM交互模式
- JSON提取工具设计
  - `_strip_code_fence`：去除代码围栏标记，支持多种编程语言标识。
  - `_extract_json_object`：提取JSON对象，支持直接解析和范围查找两种方式。
  - `_extract_json_array`：提取JSON数组，自动过滤非字典元素。
- 增强的LLM交互模式
  - 在AnalysisTool、StoryBranchTool、ContinueWritingTool中广泛应用JSON提取。
  - 支持容错处理：当JSON解析失败时，自动尝试范围提取和修复。
  - 提供标准化输出：统一的字段规范化和数据清洗。
- 关键应用场景
  - 结构分析：从LLM输出中提取人物、事件、世界观等结构化数据。
  - 分支生成：提取多个剧情分支的JSON数组。
  - 续写生成：提取章节内容和新增事件的JSON对象。

```mermaid
flowchart TD
Start(["LLM输出"]) --> Strip["去除代码围栏<br/>_strip_code_fence"]
Strip --> TryDirect["直接JSON解析<br/>json.loads"]
TryDirect --> DirectSuccess{"解析成功?"}
DirectSuccess --> |是| ReturnObj["返回对象/数组"]
DirectSuccess --> |否| FindRange["查找{}或[]范围"]
FindRange --> TryRange["范围JSON解析"]
TryRange --> RangeSuccess{"解析成功?"}
RangeSuccess --> |是| Filter["过滤字典元素"]
RangeSuccess --> |否| Empty["返回空结果"]
Filter --> ReturnObj
ReturnObj --> Normalize["标准化输出<br/>字段清洗和规范化"]
Normalize --> End(["完成"])
Empty --> End
```

**图表来源**
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)

**章节来源**
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)

### 恢复管道与错误处理机制
- 恢复管道设计
  - `RecoveryPipeline`：实现多阶段错误恢复，包括重试、修复、回退和降级。
  - `RecoveryResult`：数据类封装恢复结果，包含状态、数据、阶段和错误信息。
- 多阶段恢复策略
  - Execute阶段：正常执行，支持多次重试。
  - Repair阶段：修复输入或参数，提高成功率。
  - Fallback阶段：使用备用模型或替代方案。
  - Degrade阶段：降级到基本功能，确保系统可用性。
- 应用场景
  - AnalysisTool：结构分析的多阶段恢复。
  - StoryBranchTool：分支生成的容错处理。
  - ContinueWritingTool：续写生成的质量保证。

```mermaid
flowchart TD
Start(["开始恢复"]) --> Execute["Execute阶段<br/>正常执行"]
Execute --> ExecSuccess{"执行成功?"}
ExecSuccess --> |是| Success["返回成功结果"]
ExecSuccess --> |否| RetryCount{"重试次数<限制?"}
RetryCount --> |是| Execute
RetryCount --> |否| Repair["Repair阶段<br/>修复输入"]
Repair --> RepairSuccess{"修复成功?"}
RepairSuccess --> |是| Success
RepairSuccess --> |否| Fallback["Fallback阶段<br/>备用方案"]
Fallback --> FallSuccess{"回退成功?"}
FallSuccess --> |是| Success
FallSuccess --> |否| Degrade["Degrade阶段<br/>降级处理"]
Degrade --> DegradeSuccess{"降级成功?"}
DegradeSuccess --> |是| Success
DegradeSuccess --> |否| Fail["返回失败结果"]
Success --> End(["结束"])
Fail --> End
```

**图表来源**
- [recovery.py:19-51](file://application/agent_mvp/recovery.py#L19-L51)

**章节来源**
- [recovery.py:15-51](file://application/agent_mvp/recovery.py#L15-L51)

### 错误处理与异常体系
- 统一异常类型
  - LLMClientError 为基础异常。
  - APIKeyError、RateLimitError、NetworkError、TokenLimitError 分别对应密钥、限流、网络与Token超限。
- 客户端错误映射
  - DeepSeek/Kimi 客户端在收到特定HTTP状态码或网络异常时，抛出对应领域异常，便于上层统一处理。
- 建议处理策略
  - 限流：等待 retry-after 或降低并发。
  - 网络：指数退避重试，必要时切换备模型。
  - Token：缩短输入或调整 max_tokens。
- JSON提取错误处理
  - 提供容错机制，当JSON解析失败时自动尝试范围提取。
  - 支持多种格式的输入，包括带代码围栏的输出。

**章节来源**
- [exceptions.py:51-100](file://domain/exceptions.py#L51-L100)
- [deepseek_client.py:163-193](file://infrastructure/llm/deepseek_client.py#L163-L193)
- [kimi_client.py:169-199](file://infrastructure/llm/kimi_client.py#L169-L199)
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)

## 依赖分析
- 组件耦合
  - 工厂仅依赖抽象接口与具体实现类，保持低耦合。
  - 客户端依赖异常体系与HTTP库，职责清晰。
  - 前后端通过API路由与数据模型解耦。
  - 工具模块依赖恢复管道和JSON提取工具，形成完整的错误处理链。
- 外部依赖
  - httpx 用于异步HTTP请求与连接池。
  - FastAPI/Pydantic 用于后端API与数据校验。
  - Element Plus/Vue/Pinia 用于前端配置界面与状态管理。
  - Python标准库：json、re、logging、asyncio 等。

```mermaid
graph LR
FAC["LLMFactory"] --> |依赖| BC["LLMClient"]
FAC --> |创建| DS["DeepSeekClient"]
FAC --> |创建| KM["KimiClient"]
DS --> |使用| EXC["异常体系"]
KM --> |使用| EXC
API["配置API路由"] --> |读写| REPO["SQLiteLLMConfigRepository"]
API --> |读写| ENT["LLMConfig实体"]
FE["前端Store/API"] --> |调用| API
TOOL["工具模块"] --> |使用| MR["ModelRouter"]
TOOL --> |使用| RP["RecoveryPipeline"]
TOOL --> |使用| JSON["JSON提取工具"]
RP --> |使用| MR
```

**图表来源**
- [llm_factory.py:14-16](file://infrastructure/llm/llm_factory.py#L14-L16)
- [base_client.py:10-12](file://infrastructure/llm/base_client.py#L10-L12)
- [deepseek_client.py:13-22](file://infrastructure/llm/deepseek_client.py#L13-L22)
- [kimi_client.py:13-22](file://infrastructure/llm/kimi_client.py#L13-L22)
- [config.py:13-16](file://presentation/api/routers/config.py#L13-L16)
- [sqlite_llm_config_repo.py:14-15](file://infrastructure/persistence/sqlite_llm_config_repo.py#L14-L15)
- [llm_config.py:10-12](file://domain/entities/llm_config.py#L10-L12)
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)
- [recovery.py:19-51](file://application/agent_mvp/recovery.py#L19-L51)

**章节来源**
- [llm_factory.py:14-16](file://infrastructure/llm/llm_factory.py#L14-L16)
- [base_client.py:10-12](file://infrastructure/llm/base_client.py#L10-L12)
- [deepseek_client.py:13-22](file://infrastructure/llm/deepseek_client.py#L13-L22)
- [kimi_client.py:13-22](file://infrastructure/llm/kimi_client.py#L13-L22)
- [config.py:13-16](file://presentation/api/routers/config.py#L13-L16)
- [sqlite_llm_config_repo.py:14-15](file://infrastructure/persistence/sqlite_llm_config_repo.py#L14-L15)
- [llm_config.py:10-12](file://domain/entities/llm_config.py#L10-L12)
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)
- [recovery.py:15-51](file://application/agent_mvp/recovery.py#L15-L51)

## 性能考虑
- 连接复用与并发
  - 客户端使用 httpx.AsyncClient 并配置连接池上限与 keepalive，减少TCP握手开销。
- 超时与重试
  - 合理设置超时与最大重试次数，避免长时间阻塞；对网络与限流错误采用指数退避。
- 输入控制
  - 在客户端内部对输入进行字符级截断，避免Token超限导致的失败与资源浪费。
- 上下文长度
  - 根据模型族选择合适的 max_tokens，避免超出模型上下文上限。
- 主备切换
  - 通过 is_available() 快速探测，减少无效调用；在高负载或限流时主动切换备模型。
- JSON提取优化
  - 使用范围查找算法，避免全量扫描整个文本。
  - 提供容错机制，减少因格式问题导致的失败重试。
- 恢复管道效率
  - 多阶段恢复减少单次失败的影响，提高整体成功率。
  - 最大重试次数限制防止无限循环重试。

## 故障排查指南
- 常见问题定位
  - API密钥错误：检查前端配置页面与后端保存结果；确认密钥格式与权限。
  - 限流：关注 RateLimitError 中的 retry-after；降低并发或等待。
  - 网络异常：检查客户端日志与网络连通性；必要时切换备模型。
  - Token超限：缩短输入或调整 max_tokens；确认模型上下文上限。
  - JSON解析失败：检查LLM输出格式，确认是否包含代码围栏。
- 调试步骤
  - 前端：使用配置页面的"测试"按钮，观察返回结果与错误信息。
  - 后端：通过 /api/config/llm/test 获取各模型连通性测试结果。
  - 客户端：启用更详细的日志级别，观察重试与错误堆栈。
  - JSON提取：检查输入格式，确认是否为有效的JSON或带围栏的格式。
  - 恢复管道：观察各阶段的执行情况，确定失败发生在哪个阶段。
- 单元测试参考
  - 测试覆盖了客户端接口一致性、上下文长度判断与工厂创建逻辑，可作为行为回归依据。
  - JSON提取工具和恢复管道都有专门的单元测试，确保功能稳定性。

**章节来源**
- [exceptions.py:58-100](file://domain/exceptions.py#L58-L100)
- [deepseek_client.py:155-193](file://infrastructure/llm/deepseek_client.py#L155-L193)
- [kimi_client.py:161-199](file://infrastructure/llm/kimi_client.py#L161-L199)
- [config.py:126-147](file://presentation/api/routers/config.py#L126-L147)
- [test_llm_client.py:1-133](file://tests/unit/test_llm_client.py#L1-L133)
- [test_llm_client_improved.py:1-228](file://tests/unit/test_llm_client_improved.py#L1-L228)
- [test_recovery.py:1-219](file://tests/unit/test_recovery.py#L1-L219)

## 结论
InkTrace 的AI模型集成为后续扩展提供了清晰的抽象与稳定的主备切换机制。通过工厂模式统一管理不同模型客户端，结合完善的异常体系与前后端配置通道，既满足了易用性也兼顾了可靠性。本次更新新增的JSON提取工具和增强的LLM交互模式，显著提升了系统的解析能力和错误处理机制。通过多阶段恢复管道和容错处理，系统能够在各种异常情况下保持稳定运行。建议在生产环境中进一步完善密钥轮换、限流策略与可观测性指标，持续优化主备切换与重试策略。

## 附录

### 如何扩展新的AI模型支持
- 新增客户端
  - 继承 LLMClient，实现 generate/chat/model_name/max_context_tokens/is_available。
  - 在客户端内完成参数组装、HTTP调用、错误映射与重试策略。
- 注册到工厂
  - 在 LLMFactory 中新增备用客户端的创建逻辑，并在 get_client 中纳入可用性检测。
- 配置与前端
  - 在前端配置页面增加对应字段与校验规则；后端路由与仓储保持一致的数据结构。
- 测试
  - 补充单元测试，覆盖接口一致性、上下文长度与工厂创建逻辑。

### JSON提取工具使用指南
- 基本使用
  - `_strip_code_fence`：去除代码围栏标记，支持多种语言标识。
  - `_extract_json_object`：提取JSON对象，支持直接解析和范围查找。
  - `_extract_json_array`：提取JSON数组，自动过滤非字典元素。
- 最佳实践
  - 在LLM工具中优先使用JSON提取工具，确保输出格式正确。
  - 对于可能包含代码围栏的输出，先使用 `_strip_code_fence` 处理。
  - 结合恢复管道使用，提高解析成功率。

### 恢复管道配置建议
- 重试次数
  - 根据业务重要性设置合理的重试次数，避免无限重试。
- 阶段顺序
  - Execute → Repair → Fallback → Degrade 的顺序确保最优的失败处理效果。
- 错误分类
  - 明确区分可重试和不可重试错误，避免对不可重试错误进行重试。

**章节来源**
- [base_client.py:14-83](file://infrastructure/llm/base_client.py#L14-L83)
- [llm_factory.py:31-121](file://infrastructure/llm/llm_factory.py#L31-L121)
- [LLMConfig.vue:1-285](file://frontend/src/views/config/LLMConfig.vue#L1-L285)
- [config.js（store）:75-107](file://frontend/src/stores/config.js#L75-L107)
- [config.py:102-124](file://presentation/api/routers/config.py#L102-L124)
- [tools.py:118-156](file://application/agent_mvp/tools.py#L118-L156)
- [recovery.py:15-51](file://application/agent_mvp/recovery.py#L15-L51)