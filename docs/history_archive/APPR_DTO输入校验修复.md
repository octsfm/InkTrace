# APPR_DTO输入校验修复

**作者：孔利群**  
**日期：2026-03-17**

## 1. 需求边界（Align阶段）

### 1.1 问题分析
- ❌ 缺少输入校验：使用dataclass而非Pydantic
- ❌ 缺少上下文信息：无user_id、session_id、trace_id
- ❌ 语义不够Agent化：参数过于简单
- ❌ 缺少扩展能力：参数写死

### 1.2 需求范围
- 使用Pydantic BaseModel替换dataclass
- 添加字段验证（min_length, gt等）
- 创建基础请求DTO（BaseRequest）
- 优化语义为Agent友好格式
- 添加扩展能力（options字段）

## 2. 架构设计（Architect阶段）

### 2.1 架构改进

**改进前**：
```python
@dataclass
class CreateNovelRequest:
    title: str
    author: str
```

**改进后**：
```python
class BaseRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None

class CreateNovelRequest(BaseRequest):
    title: str = Field(..., min_length=1, max_length=100)
    author: str = Field(..., min_length=1, max_length=50)
    options: Optional[Dict[str, Any]] = None
```

### 2.2 模块设计
1. 基础请求DTO（BaseRequest）
2. 输入校验模块（Pydantic验证）
3. Agent友好模块（结构化参数）
4. 扩展能力模块（options字段）

## 3. 任务拆解（Atomize阶段）

| 任务编号 | 任务名称 | 层次 | 交付物 | 依赖 |
|---------|---------|------|--------|------|
| ATOM-01 | 创建BaseRequest基类 | 应用层 | request_dto.py | 无 |
| ATOM-02 | 重构CreateNovelRequest | 应用层 | request_dto.py | ATOM-01 |
| ATOM-03 | 重构ImportNovelRequest | 应用层 | request_dto.py | ATOM-01 |
| ATOM-04 | 重构AnalyzeNovelRequest | 应用层 | request_dto.py | ATOM-01 |
| ATOM-05 | 重构GenerateChapterRequest | 应用层 | request_dto.py | ATOM-01 |
| ATOM-06 | 重构PlanPlotRequest | 应用层 | request_dto.py | ATOM-01 |
| ATOM-07 | 重构ExportNovelRequest | 应用层 | request_dto.py | ATOM-01 |
| ATOM-08 | 重构UpdateChapterRequest | 应用层 | request_dto.py | ATOM-01 |
| ATOM-09 | 重构CreateCharacterRequest | 应用层 | request_dto.py | ATOM-01 |
| ATOM-10 | 同步优化response_dto | 应用层 | response_dto.py | ATOM-01 |
| ATOM-11 | 编写单元测试 | 测试层 | test_dto.py | ATOM-10 |
| ATOM-12 | 集成测试验证 | 测试层 | API测试 | ATOM-11 |

## 4. 技术方案

### 4.1 BaseRequest设计

```python
from pydantic import BaseModel
from typing import Optional

class BaseRequest(BaseModel):
    """基础请求DTO，包含上下文信息"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
```

### 4.2 字段验证规则

**CreateNovelRequest**：
- title: 1-100字符
- author: 1-50字符
- genre: 至少1字符
- target_word_count: 1-1000000

**GenerateChapterRequest**：
- novel_id: 非空
- goal: 至少1字符
- chapter_count: 1-100
- target_word_count: 1-50000

### 4.3 Agent友好格式

```python
class GenerateChapterRequest(BaseRequest):
    """生成章节请求 - Agent友好"""
    novel_id: str = Field(..., min_length=1)
    goal: str = Field(..., min_length=1)
    constraints: Optional[List[str]] = None
    context_summary: Optional[str] = None
    chapter_count: int = Field(1, ge=1, le=100)
    target_word_count: int = Field(2100, gt=0, le=50000)
    options: Optional[Dict[str, Any]] = None
```

## 5. 风险评估

### 5.1 技术风险
- **低风险**：Pydantic是成熟技术
- **低风险**：向后兼容设计

### 5.2 兼容性风险
- **低风险**：使用Optional字段保持兼容
- **低风险**：提供默认值

## 6. 预期效果

### 6.1 可靠性提升
- 输入校验拦截非法数据
- 减少运行时错误

### 6.2 Agent能力增强
- 结构化参数利于AI推理
- 上下文信息支持会话追踪

### 6.3 扩展能力提升
- options字段支持动态扩展
- 不破坏现有功能

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