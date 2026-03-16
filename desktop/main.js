/**
 * Electron主进程入口
 * 
 * 作者：孔利群
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { ProcessManager } = require('./process-manager');
const { TrayManager } = require('./tray-manager');
const { setupIpcHandlers } = require('./ipc-handlers');

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

let mainWindow = null;
let processManager = null;
let trayManager = null;

const BACKEND_PORT = 9527;

async function createWindow() {
    // 创建窗口时直接显示，不等待 ready-to-show
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        title: 'InkTrace - AI小说自动编写助手',
        icon: path.join(__dirname, 'assets', 'icon.ico'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        show: true,  // 直接显示窗口
        backgroundColor: '#f5f5f5'  // 设置背景色，避免白屏
    });

    // 窗口关闭时的处理
    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // 加载前端页面
    try {
        if (isDev) {
            // 开发模式：加载开发服务器
            await mainWindow.loadURL('http://localhost:3000');
            mainWindow.webContents.openDevTools();
        } else {
            // 生产模式：加载打包后的前端文件
            const frontendPath = path.join(process.resourcesPath, 'frontend', 'index.html');
            console.log('Frontend path:', frontendPath);
            console.log('Frontend file exists:', require('fs').existsSync(frontendPath));
            
            if (require('fs').existsSync(frontendPath)) {
                await mainWindow.loadFile(frontendPath);
            } else {
                // 如果前端文件不存在，显示错误页面
                await showErrorPage('前端文件未找到');
            }
        }
    } catch (error) {
        console.error('Failed to load frontend:', error);
        await showErrorPage(error.message);
    }
}

async function showErrorPage(errorMessage) {
    if (!mainWindow) return;
    
    await mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(`
        <html>
            <head>
                <title>InkTrace - AI小说自动编写助手</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        padding: 40px; 
                        background: #f5f5f5; 
                        margin: 0;
                    }
                    .container { 
                        max-width: 800px; 
                        margin: 0 auto; 
                        background: white; 
                        padding: 30px; 
                        border-radius: 8px; 
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                    }
                    h1 { color: #409eff; margin-bottom: 20px; }
                    .status { background: #f0f9ff; padding: 15px; border-radius: 4px; margin: 20px 0; }
                    .error { background: #fef0f0; color: #f56c6c; }
                    .debug { background: #f8f9fa; font-family: monospace; font-size: 12px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>InkTrace - AI小说自动编写助手</h1>
                    <div class="status">
                        <h3>应用状态</h3>
                        <p>✅ 后端服务已启动 (端口: 9527)</p>
                        <p>❌ 前端界面加载失败</p>
                        <p>错误信息：${errorMessage}</p>
                    </div>
                    <div class="status debug">
                        <h3>调试信息</h3>
                        <p>资源路径: ${process.resourcesPath}</p>
                        <p>当前目录: ${__dirname}</p>
                        <p>打包状态: ${app.isPackaged ? '已打包' : '开发模式'}</p>
                    </div>
                    <div class="status error">
                        <h3>解决方案</h3>
                        <p>1. 请重新安装应用</p>
                        <p>2. 或联系技术支持</p>
                    </div>
                </div>
            </body>
        </html>
    `));
}

async function startBackend() {
    processManager = new ProcessManager();
    
    const backendPath = isDev 
        ? path.join(__dirname, '..', 'main.py')
        : path.join(process.resourcesPath, 'backend', 'inktrace-backend.exe');
    
    console.log('Backend path:', backendPath);
    console.log('File exists:', require('fs').existsSync(backendPath));
    
    await processManager.start(backendPath, BACKEND_PORT, isDev);
}

function setupTray() {
    trayManager = new TrayManager(
        path.join(__dirname, 'assets', 'icon.ico'),
        mainWindow
    );
    trayManager.create();
}

async function showErrorDialog(message) {
    if (mainWindow) {
        await dialog.showMessageBox(mainWindow, {
            type: 'error',
            title: '启动错误',
            message: message
        });
    }
}

function setupAppEvents() {
    app.whenReady().then(async () => {
        try {
            console.log('Application starting...');
            
            // 先创建窗口，让用户立即看到界面
            console.log('Creating window...');
            await createWindow();
            console.log('Window created successfully');
            
            // 然后启动后端服务
            console.log('Starting backend...');
            await startBackend();
            console.log('Backend started successfully');
            
            // 设置系统托盘
            setupTray();
            setupIpcHandlers(ipcMain, processManager);
            
            console.log('Application startup completed');
        } catch (error) {
            console.error('Application startup failed:', error);
            await showErrorDialog(`应用启动失败：${error.message}`);
            app.quit();
        }
    });

    app.on('window-all-closed', () => {
        if (process.platform !== 'darwin') {
            app.quit();
        }
    });

    app.on('activate', async () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            await createWindow();
        }
    });

    app.on('before-quit', async () => {
        app.isQuitting = true;
        if (processManager) {
            await processManager.stop();
        }
        if (trayManager) {
            trayManager.destroy();
        }
    });
}

// 启动应用
setupAppEvents();
