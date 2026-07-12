# InkTrace

> 给小说作者使用的长篇创作工作台：你决定故事往哪里走，系统帮你准备新稿、检查问题和整理线索。

当前状态：V2.0 P2-04 方案 A 与“接着写”入口已完成本地封版，远端 CI 待复验。封版日期：2026-07-12。

## 先说最重要的

InkTrace 不会在你不知情时修改正式正文。

- AI 生成的内容先成为独立新稿。
- 只有你明确选择“放进正文”，新稿才会进入正式正文。
- 每写完一章都会停下来等你决定，不会无人值守地一直写。
- “继续写下一章”和“采用当前新稿”是两个不同操作。
- 系统不会在普通日志中记录完整正文、新稿、Prompt、ContextPack 或 API Key。

## 它可以帮你做什么

- 管理作品和章节；
- 在统一写作台中写正文；
- 整理大纲、人物、时间线和伏笔；
- 根据已有内容准备续写新稿；
- 推演方向、确认章节计划；
- 改写选中的文字；
- 检查一致性、冲突和记忆变化；
- 由作者逐次决定哪些内容真正进入作品。

## “接着写”怎么用

1. 打开作品和想继续写的章节。
2. 打开右侧“AI”，选择“接着写”。
3. 选择“让冲突更紧张”“让人物关系推进”或“把刚才的伏笔接下去”。
4. 也可以写一句自己的想法；没有特别要求时可以直接接着写。
5. 点击“写一章给我看”。
6. 写完先阅读新稿，再决定是否放进正文、是否继续下一章。

详细说明见：[“接着写”使用说明](docs/10_user_guide/InkTrace-接着写-使用说明.md)。

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.11 或更高版本
- Node.js 18 或更高版本

### 第一次安装

在项目目录打开 PowerShell：

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

- 写作界面：[http://localhost:3000](http://localhost:3000)
- 后端接口说明：[http://127.0.0.1:9527/docs](http://127.0.0.1:9527/docs)

停止服务：

```powershell
.\stop.bat
```

## 模型设置

你可以先浏览界面和管理作品；要使用分析、接着写、改写等 AI 功能，需要在应用的“设置”页面完成模型服务配置。

API Key 通过受控配置链路保存和读取，不应写进源码、README、日志或提交记录。

## 当前封版范围

本次完成的是 P2-04 方案 A 和面向作者的“接着写”入口：

- 入口统一使用作者语言；
- 支持三项写作方向、0 至 60 字自由输入和空值直写；
- 每次只生成一章并等待作者；
- 候选稿与正式正文保持隔离；
- 保留章数、篇幅、冲突和用量保护；
- 后端、前端、构建和视觉验收均已在本地通过。

这不代表 P2 所有模块已经完成发布验收。远端 CI 通过仍是合并或发布前置条件。

## 本地验证结果

| 检查 | 结果 |
|---|---|
| 后端全量测试 | `839 passed, 1 skipped` |
| P2-04 相关后端测试 | `60 passed` |
| 前端全量测试 | `443 passed` |
| 前端生产构建 | 通过 |
| Playwright 视觉验收 | `2 passed` |
| 远端 CI | 待复验 |

常用验证命令：

```powershell
python -m pytest -q
cd frontend
npm test
npm run build
```

## 文档入口

### 给作者

- [“接着写”使用说明](docs/10_user_guide/InkTrace-接着写-使用说明.md)
- [当前项目状态](docs/PROJECT_STATUS_CURRENT.md)

### 封版资料

- [“接着写”封版总结](docs/07_overview/InkTrace-V2.0-P2-04-接着写封版总结.md)
- [P2-04 封版验收报告](docs/09_acceptance/InkTrace-V2.0-P2-S2-P2-04-验收清单.md)
- [视觉验收记录](design-qa.md)
- [设计与实现对照图](artifacts/design-qa/continue-writing-comparison.png)

### 正式设计依据

- [需求规格说明书](docs/01_requirements/InkTrace-V2.0-需求规格说明书.md)
- [架构设计说明书](docs/02_architecture/InkTrace-V2.0-架构设计说明书.md)
- [概要设计说明书](docs/07_overview/InkTrace-V2.0-概要设计说明书.md)
- [P2-04 详细设计](docs/03_design/InkTrace-V2.0-P2-04-自动续写队列详细设计.md)
- [P2 API 与前端边界](docs/03_design/InkTrace-V2.0-P2-11-API与前端集成边界详细设计.md)
- [P2 UI 与交互设计](docs/03_design/InkTrace-V2.0-P2-12-UI集成与交互设计说明书.md)

历史重构资料已归档在 `docs/history_archive/`，不作为当前实现依据。所有 `*_001.md`、草稿和备份文档也不得作为正式实现依据。

## 仓库结构

```text
ink-trace/
├── application/       # 应用用例编排
├── domain/            # 领域对象与核心规则
├── infrastructure/    # 数据库、模型与外部适配
├── presentation/      # API 与依赖注入
├── frontend/          # Vue 3 + Vite + Pinia
├── tests/             # 后端测试
├── docs/              # 正式设计、计划、验收与使用说明
├── main.py            # 后端入口
├── start-all.bat      # 一键启动
└── stop.bat           # 一键停止
```

## 开发约束

本项目执行 DDD、Clean Architecture 和 TDD，并遵守根目录 [AGENTS.md](AGENTS.md) 的实现纪律。任何改动都不能绕过真实用户操作、人工审核门、记忆审核门或冲突保护。

## 许可证

[MIT](LICENSE)
