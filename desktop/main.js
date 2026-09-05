'use strict'

const { app, BrowserWindow, ipcMain, dialog, nativeTheme } = require('electron')
const path = require('path')
const fs = require('fs')
const os = require('os')
const { spawn } = require('child_process')
const readline = require('readline')

let win = null
let python = null
let requestSeq = 0
const pending = new Map()
let runtimeInstall = null
let backendReady = false
let backendReadyPromise = null
let backendReadyResolve = null
let backendReadyReject = null
let backendStderrTail = ''

function appRoot() {
  return path.resolve(__dirname, '..')
}

function rendererRoot() {
  // In a packaged build __dirname lives inside app.asar/desktop; renderer files
  // are packaged alongside it inside app.asar/src/renderer
  return path.join(appRoot(), 'src', 'renderer')
}

function coreRoot() {
  // Python + algorithms are extraResources because they must remain normal
  // filesystem files that host Python can import
  return app.isPackaged ? path.join(process.resourcesPath, 'handeye') : appRoot()
}

function readUbuntuVersion() {
  try {
    const text = fs.readFileSync('/etc/os-release', 'utf8')
    const match = text.match(/^VERSION_ID="?([^"\n]+)"?/m)
    return match ? match[1] : ''
  } catch (_) {
    return ''
  }
}

function mappedRosDistro(version = readUbuntuVersion()) {
  return { '20.04': 'foxy', '22.04': 'humble', '24.04': 'jazzy' }[version] || ''
}

function findRosSetup() {
  if (process.env.ROS_SETUP && fs.existsSync(process.env.ROS_SETUP)) return process.env.ROS_SETUP
  if (process.env.ROS_DISTRO) {
    const candidate = `/opt/ros/${process.env.ROS_DISTRO}/setup.bash`
    if (fs.existsSync(candidate)) return candidate
  }

  const preferred = mappedRosDistro()
  if (preferred) {
    const candidate = `/opt/ros/${preferred}/setup.bash`
    if (fs.existsSync(candidate)) return candidate
  }

  try {
    const entries = fs.readdirSync('/opt/ros')
      .map(name => `/opt/ros/${name}/setup.bash`)
      .filter(candidate => fs.existsSync(candidate))
    if (entries.length === 1) return entries[0]
  } catch (_) {}
  return ''
}

function userRuntimePython() {
  return path.join(os.homedir(), '.local', 'share', 'handeye-calibration', '.venv', 'bin', 'python')
}

function findPython() {
  const candidates = [
    process.env.HANDEYE_PYTHON,
    app.isPackaged ? null : path.join(coreRoot(), '.venv', 'bin', 'python'),
    userRuntimePython(),
    'python3'
  ].filter(Boolean)
  for (const candidate of candidates) {
    if (!candidate.includes('/') || fs.existsSync(candidate)) return candidate
  }
  return 'python3'
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'"'"'`)}'`
}

function bridgeCommand() {
  const root = coreRoot()
  const bridge = path.join(root, 'backend', 'bridge.py')
  const pythonExe = findPython()
  const rosSetup = findRosSetup()
  const dataDir = app.getPath('userData')
  const env = { ...process.env, HANDEYE_DATA_DIR: dataDir, PYTHONNOUSERSITE: '1' }
  if (process.env.HANDEYE_MOCK === '1') env.HANDEYE_MOCK = '1'

  if (rosSetup) {
    const script = `source ${shellQuote(rosSetup)} >/dev/null 2>&1; exec ${shellQuote(pythonExe)} ${shellQuote(bridge)}`
    return { command: '/bin/bash', args: ['-c', script], env, rosSetup, pythonExe }
  }
  return { command: pythonExe, args: [bridge], env, rosSetup: '', pythonExe }
}

function sendRenderer(channel, payload) {
  if (win && !win.isDestroyed()) win.webContents.send(channel, payload)
}

function stopPython() {
  return new Promise(resolve => {
    if (!python || python.killed) {
      python = null
      resolve()
      return
    }
    const child = python
    python = null
    backendReady = false
    try {
      child.stdin.write(JSON.stringify({ id: ++requestSeq, method: 'shutdown', params: {} }) + '\n')
    } catch (_) {}
    const timer = setTimeout(() => {
      try { child.kill('SIGTERM') } catch (_) {}
      resolve()
    }, 500)
    child.once('exit', () => {
      clearTimeout(timer)
      resolve()
    })
  })
}

function resetBackendReady() {
  backendReady = false
  backendReadyResolve = null
  backendReadyReject = null
  backendReadyPromise = new Promise((resolve, reject) => {
    backendReadyResolve = resolve
    backendReadyReject = reject
  })
  backendReadyPromise.catch(() => {})
}

function resolveBackendReady() {
  backendReady = true
  if (backendReadyResolve) backendReadyResolve(true)
  backendReadyResolve = null
  backendReadyReject = null
}

function rejectBackendReady(error) {
  backendReady = false
  if (backendReadyReject) backendReadyReject(error)
  backendReadyResolve = null
  backendReadyReject = null
}

function backendFailureMessage(prefix) {
  const detail = backendStderrTail.trim()
  return detail ? `${prefix}\n${detail}` : prefix
}

function startPython() {
  if (python && !python.killed) return backendReadyPromise
  resetBackendReady()
  backendStderrTail = ''
  const cfg = bridgeCommand()
  sendRenderer('bridge-runtime', {
    state: 'starting', python: cfg.pythonExe, rosSetup: cfg.rosSetup,
    runtimePython: userRuntimePython(), runtimeInstalled: fs.existsSync(userRuntimePython())
  })

  python = spawn(cfg.command, cfg.args, {
    cwd: coreRoot(),
    env: cfg.env,
    stdio: ['pipe', 'pipe', 'pipe']
  })

  const child = python
  const lines = readline.createInterface({ input: child.stdout })
  lines.on('line', line => {
    try {
      const message = JSON.parse(line)
      if (message.kind === 'response') {
        const slot = pending.get(message.id)
        if (slot) {
          pending.delete(message.id)
          clearTimeout(slot.timer)
          if (message.ok) slot.resolve(message.result)
          else slot.reject(new Error(message.error || 'Python backend error'))
        }
      } else if (message.kind === 'event') {
        sendRenderer('bridge-event', message)
        if (message.event === 'ready') {
          resolveBackendReady()
          sendRenderer('bridge-runtime', {
            state: 'ready', python: cfg.pythonExe, rosSetup: cfg.rosSetup,
            runtimePython: userRuntimePython(), runtimeInstalled: fs.existsSync(userRuntimePython())
          })
        }
      }
    } catch (error) {
      sendRenderer('bridge-runtime', { state: 'protocol-error', message: String(error), line })
    }
  })
  child.stderr.on('data', data => {
    const text = data.toString()
    backendStderrTail = (backendStderrTail + text).slice(-8000)
    sendRenderer('bridge-stderr', text)
  })
  child.on('error', error => {
    const wrapped = new Error(backendFailureMessage(error.message))
    rejectBackendReady(wrapped)
    sendRenderer('bridge-runtime', { state: 'error', message: wrapped.message })
  })
  child.on('exit', (code, signal) => {
    if (python === child) python = null
    if (!backendReady) {
      rejectBackendReady(new Error(backendFailureMessage(`Python backend stopped during startup (code=${code})`)))
    }
    backendReady = false
    sendRenderer('bridge-runtime', {
      state: 'stopped', code, signal, message: backendStderrTail.trim(),
      runtimeInstalled: fs.existsSync(userRuntimePython())
    })
    for (const [, slot] of pending) {
      clearTimeout(slot.timer)
      slot.reject(new Error(backendFailureMessage(`Python backend stopped (code=${code})`)))
    }
    pending.clear()
  })
  return backendReadyPromise
}

async function awaitBackendReady(timeoutMs = 15000) {
  if (backendReady && python && !python.killed && python.stdin.writable) return true
  if (!python || python.killed) startPython()
  const ready = backendReadyPromise
  if (!ready) throw new Error('Python backend startup was not initialized')

  let timer = null
  try {
    await Promise.race([
      ready,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(backendFailureMessage('Python backend startup timed out'))), timeoutMs)
      })
    ])
  } finally {
    if (timer) clearTimeout(timer)
  }
  if (!python || python.killed || !python.stdin.writable) {
    throw new Error(backendFailureMessage('Python backend is not available'))
  }
  return true
}

async function bridgeRequest(method, params = {}) {
  await awaitBackendReady()
  return new Promise((resolve, reject) => {
    const id = ++requestSeq
    const timer = setTimeout(() => {
      pending.delete(id)
      reject(new Error(`Backend timeout: ${method}`))
    }, method === 'run_tool' ? 180000 : 20000)
    pending.set(id, { resolve, reject, timer })
    try {
      python.stdin.write(JSON.stringify({ id, method, params }) + '\n')
    } catch (error) {
      clearTimeout(timer)
      pending.delete(id)
      reject(error)
    }
  })
}

function runtimeInstallerPath() {
  return path.join(coreRoot(), 'scripts', 'install-runtime.sh')
}

function installRuntime() {
  if (runtimeInstall && !runtimeInstall.killed) {
    return Promise.reject(new Error('Python runtime installation is already running'))
  }
  const script = runtimeInstallerPath()
  if (!fs.existsSync(script)) {
    return Promise.reject(new Error(`Runtime installer not found: ${script}`))
  }

  return new Promise((resolve, reject) => {
    const env = { ...process.env, HANDEYE_CORE_ROOT: coreRoot() }
    const rosSetup = findRosSetup()
    if (rosSetup) env.ROS_SETUP = rosSetup
    sendRenderer('runtime-install', { state: 'starting', rosSetup, path: userRuntimePython() })
    runtimeInstall = spawn('/bin/bash', [script], { cwd: coreRoot(), env, stdio: ['ignore', 'pipe', 'pipe'] })
    const child = runtimeInstall
    child.stdout.on('data', data => sendRenderer('runtime-install', { state: 'log', stream: 'stdout', text: data.toString() }))
    child.stderr.on('data', data => sendRenderer('runtime-install', { state: 'log', stream: 'stderr', text: data.toString() }))
    child.on('error', error => {
      if (runtimeInstall === child) runtimeInstall = null
      sendRenderer('runtime-install', { state: 'error', message: error.message })
      reject(error)
    })
    child.on('exit', async code => {
      if (runtimeInstall === child) runtimeInstall = null
      if (code !== 0) {
        const error = new Error(`Runtime installer exited with code ${code}`)
        sendRenderer('runtime-install', { state: 'error', code, message: error.message })
        reject(error)
        return
      }
      sendRenderer('runtime-install', { state: 'done', code: 0, path: userRuntimePython() })
      await stopPython()
      await startPython()
      resolve({ ok: true, python: userRuntimePython(), rosSetup })
    })
  })
}

function createWindow() {
  win = new BrowserWindow({
    width: 1460,
    height: 940,
    minWidth: 1120,
    minHeight: 720,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0a0a10',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })
  startPython()
  win.loadFile(path.join(rendererRoot(), 'index.html'))
  win.once('ready-to-show', () => {
    win.show()
  })
  win.on('maximize', () => sendRenderer('window-state', { maximized: true }))
  win.on('unmaximize', () => sendRenderer('window-state', { maximized: false }))
}

ipcMain.handle('handeye:request', (_event, method, params) => bridgeRequest(method, params))
ipcMain.handle('handeye:select-directory', async (_event, initial) => {
  const result = await dialog.showOpenDialog(win, {
    title: '选择标定输出目录',
    defaultPath: initial || app.getPath('documents'),
    properties: ['openDirectory', 'createDirectory']
  })
  return result.canceled ? '' : (result.filePaths[0] || '')
})
ipcMain.handle('handeye:runtime-info', () => {
  const cfg = bridgeCommand()
  return {
    appVersion: app.getVersion(),
    packaged: app.isPackaged,
    platform: process.platform,
    arch: process.arch,
    ubuntu: readUbuntuVersion(),
    rosDistro: process.env.ROS_DISTRO || mappedRosDistro(),
    rosSetup: cfg.rosSetup,
    python: cfg.pythonExe,
    runtimePython: userRuntimePython(),
    runtimeInstalled: fs.existsSync(userRuntimePython()),
    nativeTheme: nativeTheme.shouldUseDarkColors ? 'dark' : 'light'
  }
})
ipcMain.handle('handeye:runtime-install', () => installRuntime())
ipcMain.handle('handeye:backend-restart', async () => {
  await stopPython()
  await startPython()
  return { ok: true }
})
ipcMain.on('window:minimize', () => win?.minimize())
ipcMain.on('window:maximize', () => win?.isMaximized() ? win.unmaximize() : win?.maximize())
ipcMain.on('window:close', () => win?.close())

app.whenReady().then(createWindow)
app.on('window-all-closed', async () => {
  await stopPython()
  if (process.platform !== 'darwin') app.quit()
})
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
