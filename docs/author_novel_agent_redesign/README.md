# 作者小说智能体重构设计

## 1. 目录用途

这个文件夹用于承载 InkTrace 本次重大重构的正式设计文档。

这次重构的目标不是继续在旧实现上打补丁，而是围绕“作者小说智能体”重新定义产品、架构、状态、任务、数据与页面边界。

说明：

- 文件名暂时保留英文，目的是保证工程路径稳定
- 文档标题与正文统一使用中文
- 后续所有重大设计，优先写入这个目录，不再散落在旧 `docs/` 根目录

基线蓝图文档：

- [AUTHOR_NOVEL_AGENT_PRODUCT_BLUEPRINT.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/AUTHOR_NOVEL_AGENT_PRODUCT_BLUEPRINT.md)

## 2. 设计原则

- 从最终产品形态出发，而不是从当前页面出发
- 先定边界，再做实现
- 工作流与状态分离
- 记忆与执行上下文分离
- 源数据、派生数据、缓存、运行态分离
- 所有长任务必须可追踪、可恢复、可回溯

## 3. 推荐阅读顺序

1. [01 产品架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/01_product_architecture.md)
2. [02 智能体架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/02_agent_architecture.md)
3. [03 工作流架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/03_workflow_architecture.md)
4. [04 状态架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/04_state_architecture.md)
5. [05 小说领域架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/05_novel_domain_architecture.md)
6. [06 PlotArc 架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/06_plot_arc_architecture.md)
7. [07 记忆架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/07_memory_architecture.md)
8. [08 执行上下文架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/08_execution_context_architecture.md)
9. [09 导入与接手架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/09_import_and_takeover_architecture.md)
10. [10 写作与改写架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/10_writing_and_rewriting_architecture.md)
11. [11 质量控制架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/11_quality_control_architecture.md)
12. [12 模型调用架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/12_model_invocation_architecture.md)
13. [13 版本架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/13_version_architecture.md)
14. [14 存储架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/14_storage_architecture.md)
15. [15 配置与策略架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/15_configuration_and_policy_architecture.md)
16. [16 前端交互架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/16_frontend_interaction_architecture.md)
17. [17 权限与控制边界架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/17_permission_and_control_boundary_architecture.md)
18. [18 可观测性与运维架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/18_observability_and_operations_architecture.md)
19. [19 术语表](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/19_glossary.md)
20. [20 状态机清单](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/20_state_machines.md)
21. [21 重构路线图](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/21_refactor_roadmap.md)
22. [22 资产盘点与迁移清单](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/22_asset_inventory_and_migration_map.md)
23. [23 目标模块与页面结构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/23_target_module_and_page_structure.md)
24. [24 UI 工作区重构正式设计稿](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/24_ui_workspace_redesign_spec.md)
25. [25 第一阶段实施计划](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/25_first_implementation_plan.md)
26. [26 Workspace 页面级规格说明](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/26_workspace_page_specifications.md)
27. [27 页面状态与导航规则](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/27_page_state_and_navigation.md)
28. [28 核心组件规格说明](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/28_component_specifications.md)
29. [29 交互与任务时序说明](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/29_interaction_and_task_sequence.md)
30. [30 组件树与状态归属说明](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/30_component_tree_and_state_ownership.md)

## 4. 当前规则

这次重构阶段有 4 条硬规则：

1. 旧实现可以作为零件库复用，但不作为新产品结构基线
2. 旧页面边界不能直接继承
3. 旧“主备模型”叙事不再作为设计基线
4. 所有新设计必须服务于长篇小说的分析、接手、续写、改写与质量控制
