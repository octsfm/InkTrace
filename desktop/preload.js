/**
 * Electron预加载脚本
 * 
 * 作者：孔利群
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),
    restartBackend: () => ipcRenderer.invoke('restart-backend'),
    openExternal: (url) => ipcRenderer.invoke('open-external', url),
    showItemInFolder: (path) => ipcRenderer.invoke('show-item-in-folder', path),
    getAppVersion: () => ipcRenderer.invoke('get-app-version'),
    getAppPath: () => ipcRenderer.invoke('get-app-path'),
    
    onBackendStatusChanged: (callback) => {
        ipcRenderer.on('backend-status-changed', (event, status) => callback(status));
    },
    
    removeBackendStatusListener: () => {
        ipcRenderer.removeAllListeners('backend-status-changed');
    }
});
