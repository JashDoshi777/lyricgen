/**
 * LiveLyrics desktop app (macOS + Windows).
 *  - Full lyrics window + floating widget + tray + hotkeys
 *  - Packaged: starts the bundled backend itself on a free port
 *  - Dev (npm start): uses ../backend (venv) and port 5000
 */
const { app, BrowserWindow, Tray, Menu, ipcMain, screen, globalShortcut, nativeImage, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const net = require('net');
const http = require('http');

const isMac = process.platform === 'darwin';
const isWin = process.platform === 'win32';
const widgetOnly = process.argv.includes('--widget') || process.env.LYRICS_WIDGET_ONLY === '1';

let PORT = Number(process.env.LYRICS_PORT || 5000);
let base = () => `http://127.0.0.1:${PORT}`;

let mainWin, widgetWin, tray, backend;
let pinned = true;
let clickThrough = false;
let quitting = false;

// ── single instance ───────────────────────────────────
if (!app.requestSingleInstanceLock()) { app.quit(); }
app.on('second-instance', () => showMain());

// ── paths ─────────────────────────────────────────────
const userFile = (n) => path.join(app.getPath('userData'), n);
const envFile = () => userFile('.env');
const ENV_TEMPLATE = `# LiveLyrics settings. Save this file, then restart the app.
# Everything is optional: lyrics and song detection work without any key.

# AI "what does this line mean" (free key: https://console.groq.com/)
GROQ_API_KEY=

# Identify songs from audio when a player reports nothing (free key: https://acoustid.org/)
ACOUSTID_API_KEY=

# Extra plain-text lyrics source (https://genius.com/api-clients)
GENIUS_ACCESS_TOKEN=
`;

// ── backend lifecycle ─────────────────────────────────
const ping = () => new Promise((resolve) => {
  const req = http.get({ host: '127.0.0.1', port: PORT, path: '/api/languages', timeout: 800 }, (r) => { r.resume(); resolve(r.statusCode === 200); });
  req.on('error', () => resolve(false));
  req.on('timeout', () => { req.destroy(); resolve(false); });
});

const freePort = () => new Promise((resolve, reject) => {
  const s = net.createServer();
  s.listen(0, '127.0.0.1', () => { const { port } = s.address(); s.close(() => resolve(port)); });
  s.on('error', reject);
});

function devPython(dir) {
  const venv = isMac ? path.join(dir, '.venv', 'bin', 'python') : path.join(dir, '.venv', 'Scripts', 'python.exe');
  return fs.existsSync(venv) ? venv : (isMac ? 'python3' : 'python');
}

async function ensureBackend() {
  if (!app.isPackaged && await ping()) return true;          // dev: reuse a backend you already started

  let cmd, args = [], cwd, env = { ...process.env, FLASK_HOST: '127.0.0.1' };
  if (app.isPackaged) {
    PORT = await freePort();
    const exe = path.join(process.resourcesPath, 'backend', isWin ? 'livelyrics-backend.exe' : 'livelyrics-backend');
    if (!fs.existsSync(envFile())) fs.writeFileSync(envFile(), ENV_TEMPLATE);
    cmd = exe; cwd = app.getPath('userData');
    Object.assign(env, {
      FLASK_PORT: String(PORT),
      DB_PATH: userFile('cache.sqlite'),
      FRONTEND_DIST: path.join(process.resourcesPath, 'frontend'),
      LIVELYRICS_ENV: envFile(),
    });
  } else {
    const dir = path.join(__dirname, '..', 'backend');
    cmd = devPython(dir); args = ['app.py']; cwd = dir;
    env.FLASK_PORT = String(PORT);
  }

  backend = spawn(cmd, args, { cwd, env, stdio: app.isPackaged ? 'ignore' : 'inherit', windowsHide: true });
  backend.on('error', (e) => console.error('[backend] failed to start:', e.message));
  backend.on('exit', (c) => { console.log('[backend] exited', c); backend = null; });
  for (let i = 0; i < 80; i++) { if (await ping()) return true; await new Promise((r) => setTimeout(r, 500)); }
  return false;
}

function stopBackend() { if (backend) { try { backend.kill(); } catch { /* ignore */ } backend = null; } }

// ── windows ───────────────────────────────────────────
const iconPath = path.join(__dirname, 'assets', isWin ? 'icon.ico' : 'icon.png');

function showMain() {
  if (mainWin) { if (mainWin.isMinimized()) mainWin.restore(); mainWin.show(); mainWin.focus(); return; }
  mainWin = new BrowserWindow({
    width: 1240, height: 800, minWidth: 760, minHeight: 520,
    backgroundColor: '#050507', title: 'LiveLyrics', icon: iconPath,
    ...(isMac ? { titleBarStyle: 'hiddenInset', trafficLightPosition: { x: 20, y: 22 } } : {}),
    show: false,
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, backgroundThrottling: false },
  });
  mainWin.once('ready-to-show', () => mainWin.show());
  mainWin.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  mainWin.loadURL(base());
  mainWin.on('closed', () => { mainWin = null; });
}

const boundsFile = () => userFile('widget-bounds.json');
const loadBounds = () => { try { return JSON.parse(fs.readFileSync(boundsFile(), 'utf8')); } catch { return null; } };
const saveBounds = () => { try { if (widgetWin) fs.writeFileSync(boundsFile(), JSON.stringify(widgetWin.getBounds())); } catch { /* ignore */ } };
const defaultBounds = () => { const wa = screen.getPrimaryDisplay().workArea; return { x: wa.x + wa.width - 480, y: wa.y + wa.height - 220, width: 460, height: 190 }; };

function showWidget() {
  if (widgetWin) { widgetWin.showInactive(); return; }
  let saved = loadBounds();
  if (saved) {                       // ignore positions that are no longer on any screen
    const d = screen.getDisplayMatching(saved).workArea;
    const overlap = Math.max(0, Math.min(saved.x + saved.width, d.x + d.width) - Math.max(saved.x, d.x))
                  * Math.max(0, Math.min(saved.y + saved.height, d.y + d.height) - Math.max(saved.y, d.y));
    if (overlap < 120 * 60 || saved.width < 240 || saved.height < 90) saved = null;
  }
  widgetWin = new BrowserWindow({
    ...(saved || defaultBounds()), minWidth: 240, minHeight: 90,
    frame: false, transparent: true, hasShadow: false, backgroundColor: '#00000000',
    alwaysOnTop: true, skipTaskbar: true, resizable: true, fullscreenable: false, show: false, icon: iconPath,
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, backgroundThrottling: false },
  });
  applyPin();
  widgetWin.once('ready-to-show', () => { widgetWin.show(); widgetWin.moveTop(); });
  widgetWin.webContents.on('did-fail-load', (_e, code, desc) => console.error('[widget] load failed:', code, desc));
  widgetWin.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  widgetWin.loadURL(`${base()}/?widget=1`);
  setTimeout(() => { if (widgetWin && !widgetWin.isVisible()) widgetWin.show(); }, 4000);
  widgetWin.on('moved', saveBounds);
  widgetWin.on('resized', saveBounds);
  widgetWin.on('closed', () => { widgetWin = null; buildTray(); });
  buildTray();
}

function toggleWidget() {
  if (!widgetWin) return showWidget();
  widgetWin.isVisible() ? widgetWin.hide() : widgetWin.showInactive();
}

function applyPin() {
  if (!widgetWin) return;
  widgetWin.setAlwaysOnTop(pinned, isMac ? 'screen-saver' : 'floating');   // above full-screen apps on macOS
  widgetWin.setVisibleOnAllWorkspaces(pinned, { visibleOnFullScreen: true });
}

function toggleClickThrough() {
  clickThrough = !clickThrough;
  widgetWin?.setIgnoreMouseEvents(clickThrough, { forward: true });
  buildTray();
}

function buildTray() {
  if (!tray) {
    let img;
    if (isMac) { img = nativeImage.createFromPath(path.join(__dirname, 'assets', 'trayTemplate.png')); img.setTemplateImage(true); }
    else img = nativeImage.createFromPath(path.join(__dirname, 'assets', 'icon.png')).resize({ width: 20, height: 20 });
    tray = new Tray(img);
    tray.setToolTip('LiveLyrics');
    tray.on('click', () => (isMac ? tray.popUpContextMenu() : showMain()));
  }
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Open Lyrics Window', click: showMain },
    { label: 'Show / Hide Widget', accelerator: 'CmdOrCtrl+Shift+L', click: toggleWidget },
    { label: 'Widget: click-through (lock)', type: 'checkbox', checked: clickThrough, accelerator: 'CmdOrCtrl+Shift+K', click: toggleClickThrough },
    { label: 'Widget: always on top', type: 'checkbox', checked: pinned, click: () => { pinned = !pinned; applyPin(); buildTray(); } },
    { label: 'Widget: reset position', click: () => widgetWin?.setBounds(defaultBounds()) },
    { type: 'separator' },
    { label: 'Edit API keys…', click: openEnvFile },
    { type: 'separator' },
    { label: 'Quit LiveLyrics', click: () => app.quit() },
  ]));
}

function openEnvFile() {
  if (!fs.existsSync(envFile())) { try { fs.mkdirSync(path.dirname(envFile()), { recursive: true }); fs.writeFileSync(envFile(), ENV_TEMPLATE); } catch { /* ignore */ } }
  shell.openPath(envFile());
}

// ── IPC (from the web UI) ─────────────────────────────
const winOf = (e) => BrowserWindow.fromWebContents(e.sender);
ipcMain.on('close', (e) => winOf(e)?.close());
ipcMain.on('toggle-pin', () => { pinned = !pinned; applyPin(); buildTray(); });
ipcMain.on('resize-by', (e, dx, dy) => {
  const w = winOf(e); if (!w) return;
  const b = w.getBounds();
  w.setBounds({ ...b, width: Math.max(240, b.width + dx), height: Math.max(90, b.height + dy) });
  saveBounds();
});
ipcMain.on('open-widget', toggleWidget);
ipcMain.on('open-env', openEnvFile);
ipcMain.on('restart', () => { app.relaunch(); app.quit(); });

// ── lifecycle ─────────────────────────────────────────
app.whenReady().then(async () => {
  buildTray();
  const ok = await ensureBackend();
  if (!ok) console.error('Could not start the backend.');
  if (widgetOnly) showWidget(); else showMain();
  globalShortcut.register('CommandOrControl+Shift+L', toggleWidget);
  globalShortcut.register('CommandOrControl+Shift+K', toggleClickThrough);
});

app.on('activate', () => { if (!mainWin && !widgetWin) showMain(); });
app.on('window-all-closed', () => { if (!isMac) app.quit(); });
app.on('before-quit', () => { quitting = true; });
app.on('will-quit', () => { globalShortcut.unregisterAll(); stopBackend(); });
