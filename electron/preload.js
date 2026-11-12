const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  close: () => ipcRenderer.send('close'),
  togglePin: () => ipcRenderer.send('toggle-pin'),
  resizeBy: (dx, dy) => ipcRenderer.send('resize-by', dx, dy),
  openWidget: () => ipcRenderer.send('open-widget'),
  openKeysFile: () => ipcRenderer.send('open-env'),
  restart: () => ipcRenderer.send('restart'),
});
