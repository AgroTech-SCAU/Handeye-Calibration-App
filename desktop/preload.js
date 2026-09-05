'use strict'

const { contextBridge, ipcRenderer } = require('electron')

function subscribe(channel, callback) {
  const handler = (_event, message) => callback(message)
  ipcRenderer.on(channel, handler)
  return () => ipcRenderer.removeListener(channel, handler)
}

contextBridge.exposeInMainWorld('handeye', {
  request: (method, params = {}) => ipcRenderer.invoke('handeye:request', method, params),
  selectDirectory: initial => ipcRenderer.invoke('handeye:select-directory', initial),
  runtimeInfo: () => ipcRenderer.invoke('handeye:runtime-info'),
  runtimeInstall: () => ipcRenderer.invoke('handeye:runtime-install'),
  backendRestart: () => ipcRenderer.invoke('handeye:backend-restart'),
  onEvent: callback => subscribe('bridge-event', callback),
  onRuntime: callback => subscribe('bridge-runtime', callback),
  onRuntimeInstall: callback => subscribe('runtime-install', callback),
  onStderr: callback => subscribe('bridge-stderr', callback),
  onWindowState: callback => subscribe('window-state', callback),
  window: {
    minimize: () => ipcRenderer.send('window:minimize'),
    maximize: () => ipcRenderer.send('window:maximize'),
    close: () => ipcRenderer.send('window:close')
  }
})
