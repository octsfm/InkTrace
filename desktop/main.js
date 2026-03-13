/**
 * Electron主进程入口
 * 
 * 作者：孔利群
 */

const { app, BrowserWindow, ipcMain } = require('electron');
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
        show: false
    });

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    if (isDev) {
        await mainWindow.loadURL('http://localhost:3000');
        mainWindow.webContents.openDevTools();
    } else {
        const frontendPath = path.join(__dirname, '..', 'frontend', 'dist', 'index.html');
        await mainWindow.loadFile(frontendPath);
    }
}

async function startBackend() {
    processManager = new ProcessManager();
    
    const backendPath = isDev 
        ? path.join(__dirname, '..', 'main.py')
        : path.join(process.resourcesPath, 'backend', 'main.py');
    
    await processManager.start(backendPath, BACKEND_PORT);
}

function setupTray() {
    trayManager = new TrayManager(
        path.join(__dirname, 'assets', 'icon.ico'),
        mainWindow
    );
    trayManager.create();
}

function setupAppEvents() {
    app.whenReady().then(async () => {
        try {
            await startBackend();
            await createWindow();
            setupTray();
            setupIpcHandlers(ipcMain, processManager);
        } catch (error) {
            console.error('Application startup failed:', error);
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
    });

    app.on('will-quit', () => {
        if (trayManager) {
            trayManager.destroy();
        }
    });
}

setupAppEvents();
