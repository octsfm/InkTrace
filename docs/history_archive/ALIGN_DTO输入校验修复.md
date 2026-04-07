# ALIGN_DTO输入校验修复

**作者：孔利群**  
**日期：2026-03-17**

## 1. 需求边界

### 1.1 问题分析

**当前问题**：
1. **缺少输入校验**：使用dataclass而非Pydantic，无字段验证
2. **缺少上下文信息**：无user_id、session_id、trace_id
3. **语义不够Agent化**：参数过于简单，不利于AI推理
4. **缺少扩展能力**：参数写死，难以扩展

### 1.2 需求范围

**功能需求**：
- 使用Pydantic BaseModel替换dataclass
- 添加字段验证（min_length, gt等）
- 创建基础请求DTO（BaseRequest）
- 优化语义为Agent友好格式
- 添加扩展能力（options字段）

**非功能需求**：
- 保持向后兼容
- 不影响现有API接口
- 提升系统可靠性

## 2. 验收标准

### 2.1 输入校验
- ✅ 所有DTO使用Pydantic BaseModel
- ✅ 字段验证规则完整
- ✅ 非法输入被拦截

### 2.2 上下文信息
- ✅ BaseRequest包含user_id、session_id、trace_id
- ✅ 所有请求DTO继承BaseRequest

### 2.3 Agent友好
- ✅ 结构化目标、约束、上下文
- ✅ 语义清晰，利于AI推理

### 2.4 扩展能力
- ✅ options字段支持动态扩展
- ✅ 不破坏现有功能

## 3. 疑问清单

### 3.1 需要确认的问题

1. **兼容性问题**：是否需要保持与现有API的完全兼容？
   - 建议：使用Optional字段保持兼容

2. **验证规则**：验证规则的严格程度？
   - 建议：关键字段严格验证，可选字段宽松

3. **上下文信息**：user_id、session_id是否必填？
   - 建议：Optional，由前端或中间件填充

4. **Agent语义**：是否需要同时支持旧格式和新格式？
   - 建议：支持两种格式，逐步迁移

### 3.2 技术选型

1. **Pydantic版本**：使用Pydantic v2
2. **验证规则**：使用Field进行字段验证
3. **继承结构**：BaseRequest → 具体请求DTO

## 4. 影响范围

### 4.1 需要修改的文件
- `application/dto/request_dto.py` - 主要修改
- `application/dto/response_dto.py` - 同步优化
- `presentation/api/routers/*.py` - 适配新DTO

### 4.2 不需要修改的文件
- 领域层实体
- 基础设施层
- 测试文件（需要更新）

## 5. 风险评估

### 5.1 技术风险
- **低风险**：Pydantic是成熟技术
- **中风险**：API兼容性需要测试

### 5.2 业务风险
- **低风险**：不影响核心业务逻辑
- **低风险**：向后兼容设计

---
**Align阶段完成，请确认需求边界是否正确？**