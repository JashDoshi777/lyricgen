// Starts Electron with ELECTRON_RUN_AS_NODE cleared (VS Code's terminal sets it, which breaks Electron).
const { spawn } = require('child_process');
const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
const p = spawn(require('electron'), ['.'], { stdio: 'inherit', env });
p.on('exit', (c) => process.exit(c ?? 0));
