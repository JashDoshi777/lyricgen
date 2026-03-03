/**
 * Live Lyrics Widget — Electron Main Process
 * Creates a frameless, always-on-top, transparent floating window.
 */

const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
    const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

    mainWindow = new BrowserWindow({
        width: 480,
        height: 160,
        x: Math.floor(screenWidth / 2 - 240),
        y: screenHeight - 200,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: true,
        skipTaskbar: true,
        hasShadow: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });

    mainWindow.loadFile('widget.html');
    mainWindow.setVisibleOnAllWorkspaces(true);

    // Allow dragging
    ipcMain.on('window-move', (event, { x, y }) => {
        const [currentX, currentY] = mainWindow.getPosition();
        mainWindow.setPosition(currentX + x, currentY + y);
    });

    // Toggle expanded mode
    ipcMain.on('toggle-expanded', (event, expanded) => {
        if (expanded) {
            mainWindow.setSize(480, 400, true);
        } else {
            mainWindow.setSize(480, 160, true);
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
