# AI小说自动编写助手四期 - 架构设计

**作者：孔利群**  
**日期：2026-03-12**

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron 桌面应用                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  主进程      │  │  渲染进程    │  │  后端进程管理器      │  │
│  │  (main.js)  │  │  (Vue3)     │  │  (ProcessManager)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                │                    │              │
│         ▼                ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    IPC 通信层                            ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python 后端服务                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  FastAPI Server (Port 9527)                             ││
│  │  ├── Novel API                                          ││
│  │  ├── Writing API                                        ││
│  │  ├── Vector API (三期)                                  ││
│  │  └── RAG API (三期)                                     ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  数据存储层                                              ││
│  │  ├── SQLite (关系数据)                                  ││
│  │  └── ChromaDB (向量数据)                                ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## 二、模块设计

### 2.1 Electron主进程模块

```
desktop/
├── main.js              # 主进程入口
├── preload.js           # 预加载脚本
├── process-manager.js   # Python进程管理
├── tray-manager.js      # 系统托盘管理
├── window-manager.js    # 窗口管理
└── ipc-handlers.js      # IPC通信处理
```

### 2.2 进程管理模块

```javascript
// ProcessManager - Python后端进程管理
class ProcessManager {
    startBackend()      // 启动后端服务
    stopBackend()       // 停止后端服务
    restartBackend()    // 重启后端服务
    getBackendStatus()  // 获取后端状态
}
```

### 2.3 系统托盘模块

```javascript
// TrayManager - 系统托盘管理
class TrayManager {
    create()            // 创建托盘图标
    showWindow()        // 显示主窗口
    hideWindow()        // 隐藏主窗口
    quit()              // 退出应用
}
```

---

## 三、技术架构

### 3.1 技术栈

| 层次 | 技术 | 版本 |
|-----|------|------|
| 桌面框架 | Electron | ^28.0.0 |
| 前端框架 | Vue3 | ^3.4.0 |
| UI组件 | Element Plus | ^2.5.0 |
| 后端框架 | FastAPI | ^0.109.0 |
| 打包工具 | electron-builder | ^24.0.0 |

### 3.2 目录结构

```
ink-trace/
├── desktop/                    # Electron桌面应用
│   ├── main.js                 # 主进程
│   ├── preload.js              # 预加载脚本
│   ├── process-manager.js      # 进程管理
│   ├── tray-manager.js         # 托盘管理
│   ├── ipc-handlers.js         # IPC处理
│   └── assets/                 # 资源文件
│       └── icon.ico            # 应用图标
├── frontend/                   # Vue3前端（现有）
├── backend/                    # Python后端（现有）
│   ├── domain/                 # 领域层
│   ├── application/            # 应用层
│   ├── infrastructure/         # 基础设施层
│   └── presentation/           # 接口层
└── dist/                       # 打包输出
```

---

## 四、数据流设计

### 4.1 启动流程

```
用户双击图标
    │
    ▼
Electron主进程启动
    │
    ├──▶ 创建主窗口
    │
    ├──▶ 启动Python后端
    │        │
    │        ▼
    │    等待后端就绪
    │        │
    │        ▼
    │    加载前端页面
    │
    └──▶ 创建系统托盘
```

### 4.2 通信流程

```
渲染进程(Vue) ←→ IPC ←→ 主进程(Electron) ←→ HTTP ←→ Python后端
```

---

## 五、打包配置

### 5.1 electron-builder配置

```json
{
  "build": {
    "appId": "com.inktrace.desktop",
    "productName": "InkTrace",
    "directories": {
      "output": "dist"
    },
    "files": [
      "desktop/**/*",
      "frontend/dist/**/*",
      "backend/**/*"
    ],
    "win": {
      "target": "nsis",
      "icon": "desktop/assets/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true
    }
  }
}
```

### 5.2 Python打包方案

使用PyInstaller打包Python后端为独立可执行文件：

```bash
pyinstaller --onefile --name inktrace-backend presentation/api/app.py
```

---

## 六、安全设计

| 安全项 | 措施 |
|-------|------|
| IPC通信 | 使用contextBridge暴露有限API |
| 远程代码 | 禁用remote模块 |
| Node集成 | 渲染进程禁用nodeIntegration |
| 本地数据 | 用户目录加密存储 |

---

## 七、性能优化

| 优化项 | 措施 |
|-------|------|
| 启动速度 | 延迟加载非关键模块 |
| 内存占用 | 限制渲染进程内存 |
| 打包大小 | 压缩资源、精简依赖 |
