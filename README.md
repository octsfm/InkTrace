# InkTrace

> 面向长篇小说创作的作者智能体工作系统

InkTrace 不是一个“AI 续写按钮”，也不是把很多模型能力堆在一起的写作工具箱。  
它的目标是成为一个真正服务小说创作的工作系统：能理解已有小说，能接手未完成小说，能从零协助创作，也能在写作过程中持续提供规划、续写、改写、审查和修订能力。

当前项目正在从旧的“功能页 + workflow 控制台”重构为新的 `Dashboard + Novel Workspace` 形态，并逐步走向真正的 `AuthorAgent` 体系。

## 它是什么

InkTrace 的最终定位是：

- 一个能分析已有小说的系统
- 一个能接手未完成小说继续写的系统
- 一个能帮助作者从零创作的系统
- 一个能改写、润色、去 AI 味的系统
- 一个长期维护人物、世界观、剧情弧和一致性的系统

一句话说：

**InkTrace 想做的是“作者与智能体协作写小说的 IDE”。**

## 核心设计

### 双模型协同

系统固定使用两类模型：

- `Kimi`：理解、分析、规划、控制、校验
- `DeepSeek`：写作、续写、改写、润色

对应原则是：

**Kimi 决定故事往哪走，DeepSeek 把它写出来。**

### Story Model

InkTrace 不想靠“把最近几章拼起来扔给模型”来续写。  
系统会尽量把一部小说建成一套可持续使用的结构模型，包括：

- 人物图谱
- 世界观规则
- 主线与支线
- PlotArc
- 当前推进状态
- 风格画像
- 一致性风险点

### PlotArc

`PlotArc` 是正式的中层叙事推进单位，不是章节摘要。  
它承担的是：

- 全书结构理解
- 下一章规划
- 长线一致性控制
- 续写目标约束

在设计上，PlotArc 至少有三层视角：

- 全书总弧
- 开局到当前阶段弧
- 最近几章局部推进弧

## 当前产品形态

当前前端正在重构为两层结构：

- `Dashboard`
- `Novel Workspace`

其中 `Novel Workspace` 是某一本小说的完整工作环境，主要包含：

- `Writing`：写作核心区
- `Overview`：整体概览
- `Structure`：结构与 PlotArc
- `Chapters`：章节管理
- `Tasks`：任务与审查
- `Settings`：后续配置区

这意味着 InkTrace 的方向已经从“详情页 + 一堆按钮”转向“统一工作区 + 中央编辑器 + Copilot 协作”。

## 当前实现状态

当前仓库已经不再是早期原型，但也还没有完全到达最终形态。

更准确地说，它现在是：

- 一个已经开始落地新工作区 UI 的小说创作系统
- 一个已经具备导入、分析、规划、续写、改写、审查主链的后端系统
- 一个仍在从 workflow 主导，向真正 `AuthorAgent` 演进的系统

现阶段比较明确的状态是：

- 新 `Workspace` UI 主骨架已经搭起来
- `Writing` 写作台已经开始成形
- 双模型职责已经基本明确
- PlotArc / Story Model / 记忆体系已经有正式设计
- 真正的 `AuthorAgent` 还没有完全落成主链

## 仓库结构

```text
ink-trace/
├── application/         # 应用服务、workflow、agent_mvp
├── domain/              # 领域对象、仓储接口、核心规则
├── infrastructure/      # LLM、持久化、外部集成
├── presentation/        # API 与依赖注入
├── frontend/            # Vue 3 + Vite + Pinia 前端
├── docs/                # 文档
├── data/                # 本地数据库与项目数据
├── main.py              # 后端入口
├── start-all.bat        # 一键启动前后端
└── stop.bat             # 停止前后端
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+

### 安装依赖

```powershell
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### 启动

```powershell
.\start-all.bat
```

启动后访问：

- 前端：[http://localhost:3000](http://localhost:3000)
- 后端 API：[http://127.0.0.1:9527/docs](http://127.0.0.1:9527/docs)

### 停止

```powershell
.\stop.bat
```

`stop.bat` 现在会同时关闭：

- 后端 `9527`
- 前端 `3000`

## 模型配置

当前运行逻辑中，API Key 不再以环境变量作为主配置入口。  
模型配置应通过应用内配置页完成，再由后端持久化到本地数据库读取。

如果你只想先跑界面和基础流程，不一定需要马上配置模型；但要真正使用分析、续写、改写等能力，仍需要先在界面里完成模型配置。

## 文档入口

重构设计文档已经集中放在：

- [docs/author_novel_agent_redesign/README.md](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/README.md)

其中最重要的几份包括：

- [产品蓝图](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/AUTHOR_NOVEL_AGENT_PRODUCT_BLUEPRINT.md)
- [智能体架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/02_agent_architecture.md)
- [工作流架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/03_workflow_architecture.md)
- [小说领域架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/05_novel_domain_architecture.md)
- [PlotArc 架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/06_plot_arc_architecture.md)
- [记忆架构](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/07_memory_architecture.md)
- [UI 工作区重构设计稿](/D:/Work/InkTrace/ink-trace/docs/author_novel_agent_redesign/24_ui_workspace_redesign_spec.md)

## 适合谁

InkTrace 适合这几类使用者：

- 有长篇小说、想让系统先理解再继续写的人
- 不想只用“续写按钮”，而是想做结构化创作的人
- 需要大纲、章节计划、正文、审查、修订一体化的人
- 希望 AI 参与写作，但仍然保留作者控制权的人

## 当前重点

当前仓库的重点不是继续堆功能，而是完成这轮重大重构：

- 从旧详情页式产品收口到 `Dashboard + Workspace`
- 从“主备模型”语义收口到“职责模型”语义
- 从“workflow 控制台”收口到“作者智能体工作系统”
- 从“单次生成”收口到“长期理解作品”的 Story Model / PlotArc / Memory 体系

## 许可证

[MIT](./LICENSE)
