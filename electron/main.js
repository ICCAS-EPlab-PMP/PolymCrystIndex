const fs = require('fs')
const path = require('path')
const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron')
const packageMetadata = require('./package.json')

const backendManager = require('./backend-manager')

const DISPLAY_VERSION = packageMetadata.polymcrystindexDisplayVersion || app.getVersion()

let mainWindow = null
let shuttingDown = false

app.setAppUserModelId('com.polymcrystindex.desktop')

function isSmokeTestMode() {
  return process.env.POLYCRYINDEX_SMOKE_TEST === '1'
}

function writeSmokeTestResult(payload) {
  const outputPath = process.env.POLYCRYINDEX_SMOKE_TEST_OUTPUT
  if (!outputPath) {
    return
  }

  fs.mkdirSync(path.dirname(outputPath), { recursive: true })
  fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2), 'utf8')
}

function resolveWindowIcon() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'icon', 'polymindex.ico')
  }
  return path.resolve(__dirname, '..', 'icon', 'polymindex.ico')
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1200,
    minHeight: 820,
    show: false,
    autoHideMenuBar: true,
    title: 'PolymCrystIndex',
    icon: resolveWindowIcon(),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

async function loadApplication() {
  const backendInfo = await backendManager.startBackend({
    packaged: app.isPackaged,
    userDataDir: app.getPath('userData'),
  })
  if (isSmokeTestMode()) {
    writeSmokeTestResult({ ok: true, packaged: app.isPackaged, backendInfo })
    return
  }

  createMainWindow()
  await mainWindow.loadURL(backendInfo.appUrl)
}

async function showStartupError(error) {
  const message = error instanceof Error ? error.message : String(error)
  if (isSmokeTestMode()) {
    writeSmokeTestResult({ ok: false, packaged: app.isPackaged, error: message })
    return
  }

  await dialog.showErrorBox(
    'PolymCrystIndex 启动失败',
    `Electron 未能启动本地后端。\n\n${message}`
  )
}

async function shutdownBackend() {
  if (shuttingDown) return
  shuttingDown = true
  try {
    await backendManager.stopBackend()
  } finally {
    shuttingDown = false
  }
}

ipcMain.handle('app:get-runtime-info', async () => ({
  appVersion: DISPLAY_VERSION,
  backendStatus: backendManager.getStatus(),
  isPackaged: app.isPackaged,
}))

ipcMain.handle('app:open-external', async (_event, url) => {
  if (typeof url === 'string' && url.trim()) {
    await shell.openExternal(url)
  }
})

app.whenReady().then(async () => {
  try {
    await loadApplication()
    if (isSmokeTestMode()) {
      await shutdownBackend()
      app.quit()
      return
    }
  } catch (error) {
    await showStartupError(error)
    app.quit()
  }

  app.on('activate', async () => {
    if (isSmokeTestMode()) {
      return
    }

    if (BrowserWindow.getAllWindows().length === 0) {
      try {
        await loadApplication()
      } catch (error) {
        await showStartupError(error)
        app.quit()
      }
    }
  })
})

app.on('window-all-closed', async () => {
  await shutdownBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', async () => {
  await shutdownBackend()
})
