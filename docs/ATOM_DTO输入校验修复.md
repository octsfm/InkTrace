# ATOM_DTO输入校验修复

**作者：孔利群**  
**日期：2026-03-17**

## 1. 原子任务清单

| 任务编号 | 任务名称 | 层次 | 交付物 | 依赖 | 验收标准 |
|---------|---------|------|--------|------|---------|
| ATOM-01 | 创建BaseRequest基础DTO | 应用层 | `application/dto/request_dto.py` | 无 | 包含user_id、session_id、trace_id |
| ATOM-02 | 重构CreateNovelRequest | 应用层 | `application/dto/request_dto.py` | ATOM-01 | 使用Pydantic，添加字段验证 |
| ATOM-03 | 重构ImportNovelRequest | 应用层 | `application/dto/request_dto.py` | ATOM-01 | 使用Pydantic，添加字段验证 |
| ATOM-04 | 重构AnalyzeNovelRequest | 应用层 | `application/dto/request_dto.py` | ATOM-01 | 使用Pydantic，添加字段验证 |
| ATOM-05 | 重构GenerateChapterRequest | 应用层 | `application/dto/request_dto.py` | ATOM-01 | Agent友好格式，添加字段验证 |
| ATOM-06 | 重构PlanPlotRequest | 应用层 | `application/dto/request_dto.py` | ATOM-01 | Agent友好格式，添加字段验证 |
| ATOM-07 | 重构ExportNovelRequest | 应用层 | `application/dto/request_dto.py` | ATOM-01 | 使用Pydantic，添加字段验证 |
| ATOM-08 | 重构UpdateChapterRequest | 应用层 | `application/dto/request_dto.py` | ATOM-01 | 使用Pydantic，添加字段验证 |
| ATOM-09 | 重构CreateCharacterRequest | 应用层 | `application/dto/request_dto.py` | ATOM-01 | 使用Pydantic，添加字段验证 |
| ATOM-10 | 同步优化response_dto.py | 应用层 | `application/dto/response_dto.py` | ATOM-02~09 | 使用Pydantic，添加字段验证 |
| ATOM-11 | 编写单元测试 | 测试层 | `tests/unit/test_dto.py` | ATOM-10 | 测试覆盖率≥80% |
| ATOM-12 | 集成测试验证 | 测试层 | API测试 | ATOM-11 | 功能验证通过 |

## 2. 任务依赖关系

```
ATOM-01 (BaseRequest)
    ├── ATOM-02 (CreateNovelRequest)
    ├── ATOM-03 (ImportNovelRequest)
    ├── ATOM-04 (AnalyzeNovelRequest)
    ├── ATOM-05 (GenerateChapterRequest)
    ├── ATOM-06 (PlanPlotRequest)
    ├── ATOM-07 (ExportNovelRequest)
    ├── ATOM-08 (UpdateChapterRequest)
    └── ATOM-09 (CreateCharacterRequest)
            ↓
        ATOM-10 (response_dto)
            ↓
        ATOM-11 (单元测试)
            ↓
        ATOM-12 (集成测试)
```

## 3. 交付物清单

1. **应用层**：
   - `application/dto/request_dto.py` - 重构的请求DTO
   - `application/dto/response_dto.py` - 同步优化的响应DTO

2. **测试层**：
   - `tests/unit/test_dto.py` - 单元测试

3. **文档**：
   - `docs/ATOM_DTO输入校验修复.md` - 任务清单文档

## 4. 技术实现要点

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

**GenerateChapterRequest改进**：
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

### 4.4 向后兼容策略

- 所有新增字段使用Optional
- 提供合理的默认值
- 保持原有字段名不变

## 5. 验收标准

### 5.1 功能验收
- ✅ 所有DTO使用Pydantic BaseModel
- ✅ 字段验证规则完整
- ✅ BaseRequest包含上下文信息
- ✅ Agent友好格式实现
- ✅ 扩展能力支持

### 5.2 质量验收
- ✅ 代码规范符合要求
- ✅ 测试覆盖率≥80%
- ✅ 无遗留bug
- ✅ 文档完整

---
**Atomize阶段完成，任务拆解是否合理？**