/**
 * IPC通信处理器
 * 
 * 作者：孔利群
 */

const { shell, app, BrowserWindow, dialog } = require('electron');

function setupIpcHandlers(ipcMain, processManager) {
    ipcMain.handle('get-backend-status', () => {
        return processManager.getStatus();
    });

    ipcMain.handle('restart-backend', async () => {
        try {
            await processManager.restart();
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('open-external', async (event, url) => {
        await shell.openExternal(url);
        return { success: true };
    });

    ipcMain.handle('show-item-in-folder', async (event, filePath) => {
        shell.showItemInFolder(filePath);
        return { success: true };
    });

    ipcMain.handle('get-app-version', () => {
        return app.getVersion();
    });

    ipcMain.handle('get-app-path', () => {
        return app.getAppPath();
    });

    ipcMain.handle('select-file', async (event, options) => {
        const result = await dialog.showOpenDialog({
            title: options.title || '选择文件',
            defaultPath: options.defaultPath || '',
            filters: options.filters || [{ name: '文本文件', extensions: ['txt'] }],
            properties: ['openFile']
        });
        return result;
    });

    ipcMain.handle('select-folder', async (event, options) => {
        const result = await dialog.showOpenDialog({
            title: options.title || '选择文件夹',
            defaultPath: options.defaultPath || '',
            properties: ['openDirectory']
        });
        return result;
    });

    processManager.onStatusChange((status) => {
        const windows = BrowserWindow.getAllWindows();
        windows.forEach(win => {
            win.webContents.send('backend-status-changed', status);
        });
    });
}

module.exports = { setupIpcHandlers };
