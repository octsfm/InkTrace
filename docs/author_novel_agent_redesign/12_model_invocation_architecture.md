# 模型调用架构

## 1. 目标

模型调用架构用于定义 Kimi 与 DeepSeek 在系统中如何被路由、调用、保护、降级与配置。

目标不是“能调模型”，而是：

- 职责清晰
- 上下文稳定
- token 可控
- 失败可恢复
- 不跨职责串线

## 2. 设计原则

1. 模型职责固定，不再使用主备模型语义
2. 分析与校验职责只给 Kimi
3. 写作与改写职责只给 DeepSeek
4. 降级只允许同职责降级
5. 长文本必须显式分层和拆分，不允许默认整本拼接

## 3. 模型职责矩阵

### 3.1 Kimi 负责

- 全书分析
- 章节分析
- 续写记忆提取
- PlotArc 抽取
- 弧状态更新
- 弧选择
- 章节规划
- 一致性校验
- 改写约束生成

### 3.2 DeepSeek 负责

- 结构稿写作
- 章节续写
- 自动正文生成
- 去模板化改写
- 风格改写
- 修订写作
- 扩写与压缩
- 标题补写

## 4. 严格模式与降级模式

### 4.1 严格模式

定义：

- 某职责必须由指定模型完成
- 失败后直接失败
- 不做低质量替代结果

适用：

- 全书结构分析
- PlotArc 抽取
- 一致性校验

### 4.2 降级模式

定义：

- 主路径失败后，可使用同职责备用策略继续执行

关键规则：

- Kimi 失败不能掉到 DeepSeek
- DeepSeek 写作失败不能掉到 Kimi
- 降级必须可追踪记录

## 5. Prompt 输入策略

### 5.1 基本原则

- Prompt 必须按任务类型分开
- 不同任务使用不同上下文 builder
- 结构化输入优先于原文大拼接

### 5.2 输入层级

模型输入由以下几层构成：

1. 任务目标
2. 锁定约束
3. 结构事实
4. 近期摘要
5. 必要原文片段

### 5.3 关键规则

- 全书分析不默认吃大量章节 preview
- 续写不默认带整本上下文
- 改写只聚焦目标章节及必要约束

## 6. Prompt 版本管理

每个正式任务都必须有独立 Prompt 版本。

建议至少记录：

- `prompt_template_id`
- `prompt_version`
- `policy_version`
- `context_builder_version`

### 6.1 原则

- Prompt 变化必须可追溯
- 结果质量问题必须能定位到具体 Prompt 版本
- Prompt 版本必须和策略版本关联

## 7. token 预算

### 7.1 预算原则

- 先保留约束
- 再保留结构事实
- 最后才给原文

### 7.2 长文本任务

对于：

- 整书分析
- 大规模重整
- 长篇接手

必须先走章节工件化，再做汇总，而不是整本原文直喂。

## 8. 长文本拆分策略

### 8.1 拆分层级

优先顺序：

1. 章节级
2. chunk 级
3. 分层摘要级

### 8.2 禁止规则

- 不允许默认把整本正文直接丢进全书分析
- 不允许大段原文 preview 替代结构工件

## 9. 重试策略

### 9.1 单次失败

允许有限次重试。

### 9.2 多次失败

根据任务类型分流：

- 严格模式任务：直接失败并阻断
- 可降级任务：使用同职责降级路径

### 9.3 记录要求

必须记录：

- 重试次数
- 重试原因
- 是否更换上下文装配策略
- 是否进入降级模式

## 10. 模型结果可信度

不是所有模型输出都能直接生效。

### 10.1 必须校验的任务

- 全书分析
- PlotArc 抽取
- 一致性校验

### 10.2 规则

- 低可信结构结果不能进入写作链
- 低可信弧结果不能作为正式目标弧
- 低可信校验结果不能作为唯一阻断依据，必须可解释

## 11. 错误分类

模型调用错误至少分为：

- `timeout`
- `llm_error`
- `invalid_request`
- `context_overflow`
- `incomplete_result`
- `low_confidence`

不同错误必须走不同恢复路径。

## 12. 当前重构要求

后续实现必须满足：

1. Kimi 不参与正文写作
2. DeepSeek 不参与全书结构分析
3. 同职责降级必须可追踪
4. Prompt 版本必须可回溯
5. 长文本任务必须显式采用分层上下文策略

## 13. 与其它文档的依赖

本架构强依赖：

- [08_execution_context_architecture.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/08_execution_context_architecture.md)
- [10_writing_and_rewriting_architecture.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/10_writing_and_rewriting_architecture.md)
- [11_quality_control_architecture.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/11_quality_control_architecture.md)
- [15_configuration_and_policy_architecture.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/15_configuration_and_policy_architecture.md)

## 14. 待补充内容

后续需要继续细化：

- Kimi 任务清单的 Prompt 模板体系
- DeepSeek 写作与改写模板体系
- 具体 token 档位表
- 降级策略矩阵
