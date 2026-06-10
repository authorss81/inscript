/**
 * InScript Studio — Electron main process (v3.0.0)
 *
 * Architecture:
 *   1. Spawns `python inscript_runtime/inscript.py --studio --studio-port 8080`
 *      in a child process (the Python Studio web app + StudioBridge).
 *   2. Opens a BrowserWindow that loads http://localhost:8080.
 *   3. On window close: kills the Python child process cleanly.
 *
 * The Python server handles all language features. Electron is the shell:
 * window chrome, native menus, file dialogs, process lifecycle.
 */
const { app, BrowserWindow, Menu, dialog, shell } = require('electron');
const path  = require('path');
const { spawn } = require('child_process');
const http  = require('http');

const STUDIO_PORT  = 8080;
const BRIDGE_PORT  = 8765;
const STARTUP_WAIT = 3000;  // ms to wait for Python server

let mainWindow  = null;
let pythonProc  = null;

// ── Python server ──────────────────────────────────────────────────────────

function findPython() {
  // Try system python first (dev mode), then resourcesPath (production build)
  const candidates = [
    'python3',
    'python',
    path.join(process.resourcesPath, 'inscript_runtime', '.venv', 'bin', 'python'),
    path.join(process.resourcesPath, 'inscript_runtime', '.venv', 'Scripts', 'python.exe'),
  ];
  return candidates.find(c => { try { require('child_process').execSync(c + ' --version', {stdio:'ignore'}); return true; } catch { return false; } }) || 'python';
}

function startPythonServer(projectDir) {
  const python = findPython();
  const inscript = path.join(
    __dirname, '..', '..', 'inscript.py'  // dev: ../.. is inscript_package/
  );

  pythonProc = spawn(python, [
    inscript,
    '--studio',
    '--studio-port', String(STUDIO_PORT),
    '--bridge-port', String(BRIDGE_PORT),
    '--project-dir', projectDir || app.getPath('documents'),
  ], { stdio: ['ignore', 'pipe', 'pipe'] });

  pythonProc.stdout.on('data', d => console.log('[py]', d.toString().trim()));
  pythonProc.stderr.on('data', d => console.error('[py:err]', d.toString().trim()));
  pythonProc.on('exit', code => console.log('[py] exited', code));
}

// ── Wait for server ready ──────────────────────────────────────────────────

function waitForServer(timeout) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    function try_() {
      http.get(`http://localhost:${STUDIO_PORT}/status`, res => {
        resolve();
      }).on('error', () => {
        if (Date.now() - start > timeout) reject(new Error('timeout'));
        else setTimeout(try_, 200);
      });
    }
    try_();
  });
}

// ── Window ─────────────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width:          1400,
    height:         900,
    minWidth:       900,
    minHeight:      600,
    title:          'InScript Studio',
    backgroundColor: '#1e1e2e',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(`http://localhost:${STUDIO_PORT}`);
  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── App lifecycle ──────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  const projectDir = process.argv[2] || null;
  startPythonServer(projectDir);

  try {
    await waitForServer(STARTUP_WAIT);
  } catch {
    dialog.showErrorBox('Startup failed',
      'InScript runtime did not start in time.\nCheck that Python is installed.');
    app.quit(); return;
  }

  createWindow();
  buildMenu();
});

app.on('window-all-closed', () => {
  if (pythonProc) { pythonProc.kill(); }
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});

// ── Native menu ────────────────────────────────────────────────────────────

function buildMenu() {
  const template = [
    { label: 'File', submenu: [
      { label: 'Open Project…', accelerator: 'CmdOrCtrl+Shift+O',
        click: async () => {
          const { filePaths } = await dialog.showOpenDialog({
            properties: ['openDirectory'],
            title: 'Open InScript Project',
          });
          if (filePaths[0]) mainWindow.loadURL(
            `http://localhost:${STUDIO_PORT}?project=${encodeURIComponent(filePaths[0])}`
          );
        }},
      { type: 'separator' },
      { role: 'quit' },
    ]},
    { label: 'Edit', submenu: [
      { role: 'undo' }, { role: 'redo' },
      { type: 'separator' },
      { role: 'cut' }, { role: 'copy' }, { role: 'paste' },
    ]},
    { label: 'View', submenu: [
      { role: 'reload' },
      { label: 'Developer Tools', accelerator: 'F12',
        click: () => mainWindow.webContents.openDevTools() },
      { type: 'separator' },
      { role: 'zoomIn' }, { role: 'zoomOut' }, { role: 'resetZoom' },
    ]},
    { label: 'Help', submenu: [
      { label: 'InScript Docs',
        click: () => shell.openExternal('https://authorss81.github.io/inscript/docs/') },
      { label: 'Report Issue',
        click: () => shell.openExternal('https://github.com/authorss81/inscript/issues') },
    ]},
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}
