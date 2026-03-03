/**
 * Live Lyrics Widget — Preload Script
 * Exposes safe IPC bridge to the renderer process.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    moveWindow: (deltaX, deltaY) => ipcRenderer.send('window-move', { x: deltaX, y: deltaY }),
    toggleExpanded: (expanded) => ipcRenderer.send('toggle-expanded', expanded),
});
