# InkTrace AI小说自动编写助手 - 启动手册

## 1. 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端运行环境 |
| pip | 最新版 | Python包管理器 |
| npm | 最新版 | Node包管理器 |

## 2. 首次安装

### 2.1 安装后端依赖

```powershell
cd d:\Work\InkTrace\ink-trace
pip install -r requirements.txt
```

### 2.2 安装前端依赖

```powershell
cd d:\Work\InkTrace\ink-trace\frontend
npm install
cd ..
```

### 2.3 配置API密钥（可选）

如需使用AI写作功能，请配置大模型API密钥：

```powershell
# DeepSeek API（主用）
set DEEPSEEK_API_KEY=your_deepseek_api_key

# Kimi API（备用）
set KIMI_API_KEY=your_kimi_api_key
```

或在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
KIMI_API_KEY=your_kimi_api_key
```

### 2.4 创建数据目录

```powershell
mkdir data
mkdir logs
```

## 3. 日常使用

### 3.1 一键启动所有服务

```powershell
.\start-all.bat
```

启动后访问：
- 后端API：http://127.0.0.1:9527
- 前端界面：http://localhost:3000

### 3.2 停止所有服务

```powershell
.\stop.bat
```

## 4. 单独控制服务

### 4.1 仅启动后端

```powershell
.\start.bat
```

### 4.2 仅启动前端

```powershell
.\start-frontend.bat
```

### 4.3 后台启动后端

```powershell
.\start_background.bat
```

## 5. 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:3000 | Web操作界面 |
| API文档 | http://127.0.0.1:9527/docs | Swagger交互文档 |
| API文档 | http://127.0.0.1:9527/redoc | ReDoc文档 |

## 6. 端口配置

默认端口：
- 后端：9527
- 前端：3000

修改后端端口方式一：编辑 `config.py`

```python
port: int = 9527  # 修改此值
```

修改后端端口方式二：设置环境变量

```powershell
set INKTRACE_PORT=8888
```

## 7. 常见问题

### 7.1 端口被占用

```powershell
# 查看端口占用情况
netstat -ano | findstr :9527

# 终止进程（替换PID为实际进程ID）
taskkill /F /PID <PID>
```

### 7.2 Python未找到

确认Python已添加到PATH：
```powershell
python --version
```

如未找到，需将Python添加到系统PATH或重新安装时勾选"Add to PATH"选项。

### 7.3 npm依赖安装失败

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
npm install
```

### 7.4 API密钥无效

检查API密钥配置：
```powershell
echo %DEEPSEEK_API_KEY%
```

### 7.5 服务启动后无法访问

1. 检查防火墙是否阻止端口
2. 确认服务已正常启动（查看终端输出）
3. 尝试使用 `127.0.0.1` 替代 `localhost`

## 8. 项目结构

```
ink-trace/
├── config.py              # 应用配置
├── main.py                # 程序入口
├── requirements.txt       # Python依赖
├── start.bat              # 启动后端
├── stop.bat               # 停止服务
├── start-all.bat          # 一键启动
├── start-frontend.bat     # 启动前端
├── start_background.bat   # 后台模式
├── data/                  # 数据库存储
├── logs/                  # 日志文件
├── domain/                # 领域层（DDD）
├── application/           # 应用层
├── infrastructure/        # 基础设施层
├── presentation/          # API接口层
└── frontend/              # Vue3前端
    ├── src/
    ├── package.json
    └── vite.config.js
```

## 9. 快速启动检查清单

- [ ] 已安装 Python 3.11+
- [ ] 已安装 Node.js 18+
- [ ] 已执行 `pip install -r requirements.txt`
- [ ] 已执行 `cd frontend && npm install`
- [ ] 已配置API密钥（可选）
- [ ] 已执行 `.\start-all.bat`
- [ ] 已打开 http://localhost:3000

## 10. 功能说明

### 10.1 小说导入
- 支持TXT格式导入
- 自动识别章节结构
- 解析人物、大纲信息

### 10.2 风格分析
- 词汇特征分析
- 句式模式识别
- 修辞手法统计
- 对话风格提取

### 10.3 自动续写
- 基于风格模仿
- 情节逻辑连贯
- 人物状态一致
- 可配置章节字数

### 10.4 导出功能
- 支持Markdown导出
- 保留原文格式
- 批量导出支持
