'use strict'

const Module = require('module')
const { EventEmitter } = require('events')
const { PassThrough, Writable } = require('stream')
const path = require('path')

const handlers = new Map()
const appEvents = new Map()
let windowCount = 0

class FakeChild extends EventEmitter {
  constructor() {
    super()
    this.killed = false
    this.stdout = new PassThrough()
    this.stderr = new PassThrough()
    this.stdin = new Writable({
      write: (chunk, _encoding, done) => {
        for (const raw of String(chunk).split('\n').filter(Boolean)) {
          const request = JSON.parse(raw)
          if (request.method === 'shutdown') {
            this.stdout.write(JSON.stringify({ kind: 'response', id: request.id, ok: true, result: { ok: true } }) + '\n')
            setTimeout(() => this.emit('exit', 0, null), 5)
          } else {
            this.stdout.write(JSON.stringify({ kind: 'response', id: request.id, ok: true, result: { pong: true } }) + '\n')
          }
        }
        done()
      }
    })
    setTimeout(() => {
      this.stdout.write(JSON.stringify({ kind: 'event', event: 'ready', data: {} }) + '\n')
    }, 140)
  }

  kill() {
    if (this.killed) return
    this.killed = true
    this.emit('exit', 0, 'SIGTERM')
  }
}

class FakeBrowserWindow extends EventEmitter {
  constructor() {
    super()
    windowCount += 1
    this.webContents = { send() {} }
  }

  loadFile() {}
  show() {}
  isDestroyed() { return false }
  minimize() {}
  maximize() {}
  unmaximize() {}
  isMaximized() { return false }
  close() {}
  static getAllWindows() { return windowCount ? [{}] : [] }
}

const electron = {
  app: {
    isPackaged: false,
    getPath: key => key === 'userData' ? '/tmp/handeye-lifecycle' : '/tmp',
    getVersion: () => 'test',
    whenReady: () => Promise.resolve(),
    on: (name, fn) => appEvents.set(name, fn),
    quit() {}
  },
  BrowserWindow: FakeBrowserWindow,
  ipcMain: {
    handle: (name, fn) => handlers.set(name, fn),
    on() {}
  },
  dialog: { showOpenDialog: async () => ({ canceled: true, filePaths: [] }) },
  nativeTheme: { shouldUseDarkColors: true }
}

const childProcess = {
  spawn: () => new FakeChild()
}

const originalLoad = Module._load
Module._load = function(request, parent, isMain) {
  if (request === 'electron') return electron
  if (request === 'child_process') return childProcess
  return originalLoad.call(this, request, parent, isMain)
}

async function main() {
  require(path.resolve(__dirname, '..', 'desktop', 'main.js'))
  const request = handlers.get('handeye:request')
  if (!request) throw new Error('handeye request handler missing')
  const start = Date.now()
  const result = await request({}, 'ping', {})
  const elapsed = Date.now() - start
  if (!result?.pong) throw new Error(`unexpected ping result ${JSON.stringify(result)}`)
  if (elapsed < 100) throw new Error(`request did not wait for backend readiness elapsed=${elapsed}`)
  if (elapsed > 1500) throw new Error(`backend readiness wait took too long elapsed=${elapsed}`)
  console.log(`BACKEND LIFECYCLE SMOKE: PASS (${elapsed}ms delayed-ready request)`)
}

main().catch(error => {
  console.error(`BACKEND LIFECYCLE SMOKE: FAIL\n${error.stack || error}`)
  process.exit(1)
})
