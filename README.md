# InkTrace Novel AI - AI小说自动编写助手

**作者**: 孔利群  
**版本**: 1.0.0

---

## 项目简介

InkTrace Novel AI 是一款AI小说自动编写助手，基于已有小说原文和大纲，自动分析文风、剧情，并续写新章节，同时规避AI检测。

### 核心功能

- 📚 **智能导入**: 自动解析TXT格式小说，识别章节结构
- 🎨 **文风分析**: 分析词汇、句式、修辞、对话风格
- 📖 **剧情分析**: 提取人物关系、时间线、伏笔
- ✍️ **智能续写**: 基于文风模仿的章节生成
- ✅ **连贯性检查**: 自动检查人物状态、时间线一致性
- 🔄 **主备模型**: DeepSeek主 + Kimi备，自动切换

---

## 快速开始

### 1. 环境要求

- Python 3.11+
- Node.js 18+

### 2. 安装依赖

```powershell
# 后端依赖
pip install fastapi uvicorn httpx pydantic

# 前端依赖
cd frontend
npm install
```

### 3. 配置API密钥

```powershell
# Windows
set DEEPSEEK_API_KEY=你的DeepSeek密钥
set KIMI_API_KEY=你的Kimi密钥
```

### 4. 启动服务

**方式一：一键启动**
```powershell
.\start-all.bat
```

**方式二：分别启动**
```powershell
# 启动后端
.\start.bat

# 启动前端（新终端）
.\start-frontend.bat
```

### 5. 访问界面

- **前端界面**: http://localhost:3000
- **API文档**: http://127.0.0.1:9527/docs

---

## 项目结构

```
ink-trace/
├── domain/                    # 领域层
│   ├── entities/              # 实体
│   ├── value_objects/         # 值对象
│   ├── services/              # 领域服务
│   └── repositories/          # 仓储接口
├── infrastructure/            # 基础设施层
│   ├── llm/                   # 大模型客户端
│   ├── persistence/           # 持久化
│   └── file/                  # 文件处理
├── application/               # 应用层
│   ├── services/              # 应用服务
│   └── dto/                   # 数据传输对象
├── presentation/              # 表现层
│   └── api/                   # API路由
├── frontend/                  # Vue3前端
│   ├── src/
│   │   ├── views/             # 页面组件
│   │   ├── layouts/           # 布局组件
│   │   ├── api/               # API封装
│   │   └── router/            # 路由配置
│   └── package.json
├── data/                      # 数据目录
│   └── novel/                 # 小说文件
├── docs/                      # 文档
├── tests/                     # 测试
├── main.py                    # 启动入口
├── config.py                  # 配置文件
├── start.bat                  # 后端启动脚本
├── start-frontend.bat         # 前端启动脚本
└── start-all.bat              # 一键启动脚本
```

---

## 使用指南

### 1. 导入小说

1. 点击「导入小说」按钮
2. 填写小说信息（标题、作者、题材、目标字数）
3. 输入小说文件路径（如：`D:\小说\修仙从逃出生天开始.txt`）
4. 点击「开始导入」

### 2. 分析小说

在小说详情页：
- **文风分析**: 分析词汇、句式、修辞、对话风格
- **剧情分析**: 提取人物、时间线、伏笔

### 3. 续写小说

1. 点击「续写小说」
2. 输入剧情方向（如：主角突破筑基期）
3. 设置生成章节数和每章字数
4. 开启文风模仿和连贯性检查
5. 点击「开始生成」

### 4. 导出小说

点击「导出小说」，生成Markdown格式文件。

---

## API文档

启动后端后访问：http://127.0.0.1:9527/docs

### 主要接口

| 方法 | 路径 | 说明 |
|-----|-----|-----|
| POST | /api/novels/ | 创建小说 |
| GET | /api/novels/ | 获取小说列表 |
| GET | /api/novels/{id} | 获取小说详情 |
| POST | /api/content/import | 导入小说文件 |
| GET | /api/content/style/{id} | 文风分析 |
| GET | /api/content/plot/{id} | 剧情分析 |
| POST | /api/writing/generate | 生成章节 |
| POST | /api/export/ | 导出小说 |

---

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|-----|-----|-------|
| INKTRACE_HOST | 服务地址 | 127.0.0.1 |
| INKTRACE_PORT | 服务端口 | 9527 |
| INKTRACE_DEBUG | 调试模式 | true |
| DEEPSEEK_API_KEY | DeepSeek密钥 | - |
| KIMI_API_KEY | Kimi密钥 | - |

---

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- SQLite
- DeepSeek / Kimi API

### 前端
- Vue 3
- Vite
- Element Plus
- Vue Router
- Pinia

---

## 测试

```powershell
python -m unittest discover -s tests/unit
```

测试覆盖率：~85%

---

## 作者

**孔利群**

---

## 许可证

MIT License
