# APPR_LLM客户端修复

**作者：孔利群**  
**日期：2026-03-17**

## 1. 需求边界（Align阶段）

### 1.1 功能需求
- 添加HTTP客户端连接复用和连接池
- 实现完善的错误处理机制
- 支持系统提示（system prompt）
- 实现token控制策略

### 1.2 非功能需求
- 提升多轮调用性能
- 增强系统可靠性
- 支持Agent能力
- 避免超上下文问题

### 1.3 验收标准
1. HTTP客户端复用，支持连接池
2. 完善的错误处理，API异常不会导致系统崩溃
3. 支持系统提示参数
4. 实现token控制，避免超上下文

## 2. 架构设计（Architect阶段）

### 2.1 架构改进

**改进前**：
- 每次请求创建新HTTP客户端 ❌
- 无错误处理机制 ❌
- 不支持系统提示 ❌
- 无token控制 ❌

**改进后**：
- HTTP客户端复用 ✅
- 完善的错误处理机制 ✅
- 支持系统提示 ✅
- Token控制策略 ✅

### 2.2 模块设计

1. **HTTP客户端管理模块**
   - 初始化时创建客户端
   - 连接池配置
   - 资源清理机制

2. **错误处理模块**
   - API错误分类
   - 重试机制
   - 错误日志

3. **系统提示模块**
   - messages结构化
   - 角色支持（system/user/assistant）

4. **Token控制模块**
   - 输入截断
   - Token计数
   - 上下文管理

## 3. 任务拆解（Atomize阶段）

### 3.1 原子任务清单

| 任务编号 | 任务名称 | 层次 | 交付物 | 依赖 | 验收标准 |
|---------|---------|------|--------|------|---------|
| ATOM-01 | 创建LLM客户端异常类 | 领域层 | `domain/exceptions.py` | 无 | 异常类定义完整 |
| ATOM-02 | 修改DeepSeek客户端初始化 | 基础设施层 | `infrastructure/llm/deepseek_client.py` | ATOM-01 | HTTP客户端复用 |
| ATOM-03 | 实现错误处理机制 | 基础设施层 | `infrastructure/llm/deepseek_client.py` | ATOM-02 | 完善的错误处理 |
| ATOM-04 | 添加系统提示支持 | 基础设施层 | `infrastructure/llm/deepseek_client.py` | ATOM-03 | 支持system_prompt参数 |
| ATOM-05 | 实现Token控制策略 | 基础设施层 | `infrastructure/llm/deepseek_client.py` | ATOM-04 | 输入截断功能 |
| ATOM-06 | 添加资源清理方法 | 基础设施层 | `infrastructure/llm/deepseek_client.py` | ATOM-05 | close()方法 |
| ATOM-07 | 同步修复Kimi客户端 | 基础设施层 | `infrastructure/llm/kimi_client.py` | ATOM-06 | Kimi客户端同样改进 |
| ATOM-08 | 编写单元测试 | 测试层 | `tests/unit/test_llm_client.py` | ATOM-07 | 测试覆盖率≥80% |
| ATOM-09 | 集成测试验证 | 测试层 | API测试 | ATOM-08 | 功能验证通过 |

### 3.2 交付物清单

1. **领域层**：
   - `domain/exceptions.py` - LLM客户端异常类

2. **基础设施层**：
   - `infrastructure/llm/deepseek_client.py` - 改进的DeepSeek客户端
   - `infrastructure/llm/kimi_client.py` - 同步改进的Kimi客户端

3. **测试层**：
   - `tests/unit/test_llm_client.py` - 单元测试

4. **文档**：
   - `docs/ATOM_LLM客户端修复.md` - 任务清单文档

## 4. 技术方案

### 4.1 HTTP客户端复用

```python
class DeepSeekClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        super().__init__(api_key)
        self.model = model
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        # 创建复用的HTTP客户端
        self._client = httpx.AsyncClient(timeout=120.0)
```

### 4.2 错误处理机制

```python
class LLMClientError(Exception):
    """LLM客户端基础异常"""

class APIKeyError(LLMClientError):
    """API密钥错误"""

class RateLimitError(LLMClientError):
    """限流错误"""

class NetworkError(LLMClientError):
    """网络错误"""
```

### 4.3 系统提示支持

```python
async def generate(
    self, 
    prompt: str, 
    system_prompt: str = None,
    max_tokens: int = 4000
) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
```

### 4.4 Token控制策略

```python
def _truncate_input(self, text: str, max_chars: int = 50000) -> str:
    """截断输入文本以控制token数量"""
    return text[:max_chars]
```

## 5. 风险评估

### 5.1 技术风险
- **低风险**：HTTP客户端复用是成熟技术
- **低风险**：错误处理机制标准实现
- **中风险**：Token控制策略需要后续优化

### 5.2 兼容性风险
- **低风险**：接口向后兼容，添加可选参数
- **低风险**：不影响现有调用方式

## 6. 预期效果

### 6.1 性能提升
- 多轮调用性能提升50%以上
- 减少HTTP连接建立开销

### 6.2 可靠性提升
- API异常不会导致系统崩溃
- 完善的错误日志和监控

### 6.3 功能增强
- 支持更复杂的Agent行为
- 支持长文本处理

## 7. 审批请求

请确认以下内容：
1. ✅ 需求边界是否明确
2. ✅ 架构设计是否合理
3. ✅ 任务拆解是否完整
4. ✅ 技术方案是否可行

**请批准后开始实施**

---
**审批人：**  
**审批日期：**  
**审批状态：**