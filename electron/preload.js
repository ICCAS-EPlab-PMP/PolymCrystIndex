const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getRuntimeInfo: () => ipcRenderer.invoke('app:get-runtime-info'),
  openExternal: (url) => ipcRenderer.invoke('app:open-external', url),
})
