/**
 * 系统托盘管理器
 * 
 * 作者：孔利群
 */

const { Tray, Menu, app, nativeImage } = require('electron');

class TrayManager {
    constructor(iconPath, mainWindow) {
        this.iconPath = iconPath;
        this.mainWindow = mainWindow;
        this.tray = null;
    }

    create() {
        const icon = nativeImage.createFromPath(this.iconPath);
        
        this.tray = new Tray(icon);
        this.tray.setToolTip('InkTrace - AI小说自动编写助手');
        
        const contextMenu = Menu.buildFromTemplate([
            {
                label: '显示主窗口',
                click: () => this.showWindow()
            },
            {
                label: '隐藏主窗口',
                click: () => this.hideWindow()
            },
            { type: 'separator' },
            {
                label: '重启后端服务',
                click: () => this._restartBackend()
            },
            { type: 'separator' },
            {
                label: '退出',
                click: () => this.quit()
            }
        ]);

        this.tray.setContextMenu(contextMenu);

        this.tray.on('double-click', () => {
            this.showWindow();
        });
    }

    showWindow() {
        if (this.mainWindow) {
            if (this.mainWindow.isMinimized()) {
                this.mainWindow.restore();
            }
            this.mainWindow.show();
            this.mainWindow.focus();
        }
    }

    hideWindow() {
        if (this.mainWindow) {
            this.mainWindow.hide();
        }
    }

    quit() {
        app.isQuitting = true;
        app.quit();
    }

    destroy() {
        if (this.tray) {
            this.tray.destroy();
            this.tray = null;
        }
    }

    updateStatus(status) {
        if (this.tray) {
            const statusText = status === 'running' ? '运行中' : 
                              status === 'starting' ? '启动中...' :
                              status === 'stopping' ? '停止中...' :
                              status === 'error' ? '错误' : '已停止';
            this.tray.setToolTip(`InkTrace - ${statusText}`);
        }
    }

    _restartBackend() {
        if (this.mainWindow) {
            this.mainWindow.webContents.send('restart-backend-request');
        }
    }
}

module.exports = { TrayManager };
