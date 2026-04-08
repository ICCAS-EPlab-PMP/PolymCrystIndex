const fs = require('fs')
const http = require('http')
const path = require('path')
const { spawn } = require('child_process')

const DEFAULT_PORT = Number(process.env.POLYCRYINDEX_BACKEND_PORT || 8000)
const HEALTH_TIMEOUT_MS = 45000
const HEALTH_RETRY_MS = 1000

let backendProcess = null
let stoppingBackend = false
let backendState = {
  port: DEFAULT_PORT,
  appUrl: `http://127.0.0.1:${DEFAULT_PORT}`,
  healthUrl: `http://127.0.0.1:${DEFAULT_PORT}/health`,
  started: false,
  pid: null,
  workspaceRoot: null,
  runtimeRoot: null,
  backendRoot: null,
}

function resolveWorkspaceRoot(packaged) {
  if (packaged) {
    return path.join(process.resourcesPath, 'workspace')
  }
  return path.resolve(__dirname, '..')
}

function resolveRuntimeRoot(packaged, workspaceRoot) {
  if (packaged) {
    return path.join(workspaceRoot, 'runtime', 'python')
  }

  return path.resolve(__dirname, '..', '..', 'execute', 'electron', 'runtime', 'python')
}

function resolvePythonCommand(runtimeRoot) {
  if (process.env.POLYCRYINDEX_PYTHON) {
    return process.env.POLYCRYINDEX_PYTHON
  }

  const pythonCandidates = [
    path.join(runtimeRoot, 'python.exe'),
    path.join(runtimeRoot, 'Scripts', 'python.exe'),
  ]

  for (const bundledPython of pythonCandidates) {
    if (fs.existsSync(bundledPython)) {
      return bundledPython
    }
  }

  return process.platform === 'win32' ? 'python' : 'python3'
}

function ensurePathExists(targetPath, label) {
  if (!fs.existsSync(targetPath)) {
    throw new Error(`${label} 不存在: ${targetPath}`)
  }
}

function httpGetJson(url) {
  return new Promise((resolve, reject) => {
    const request = http.get(url, (response) => {
      let raw = ''
      response.setEncoding('utf8')
      response.on('data', (chunk) => {
        raw += chunk
      })
      response.on('end', () => {
        if (response.statusCode && response.statusCode >= 200 && response.statusCode < 300) {
          try {
            resolve(JSON.parse(raw))
          } catch (error) {
            reject(error)
          }
          return
        }
        reject(new Error(`Health check failed: ${response.statusCode || 'unknown status'}`))
      })
    })

    request.on('error', reject)
    request.setTimeout(5000, () => {
      request.destroy(new Error('Health check timeout'))
    })
  })
}

async function waitForHealth(healthUrl) {
  const deadline = Date.now() + HEALTH_TIMEOUT_MS
  let lastError = null

  while (Date.now() < deadline) {
    try {
      return await httpGetJson(healthUrl)
    } catch (error) {
      lastError = error
      await new Promise((resolve) => setTimeout(resolve, HEALTH_RETRY_MS))
    }
  }

  throw new Error(`本地后端健康检查超时: ${lastError ? lastError.message : 'unknown error'}`)
}

async function startBackend({ packaged }) {
  if (backendProcess && backendState.started) {
    return backendState
  }

  const workspaceRoot = resolveWorkspaceRoot(packaged)
  const runtimeRoot = resolveRuntimeRoot(packaged, workspaceRoot)
  const backendRoot = path.join(workspaceRoot, 'backend')
  const frontendDist = path.join(workspaceRoot, 'frontend', 'dist', 'index.html')
  const fortranRoot = path.join(workspaceRoot, 'fortrancode')
  const pythonCommand = resolvePythonCommand(runtimeRoot)

  ensurePathExists(workspaceRoot, 'Workspace 根目录')
  ensurePathExists(backendRoot, 'backend 目录')
  ensurePathExists(frontendDist, 'frontend dist')
  ensurePathExists(fortranRoot, 'fortrancode 目录')

  backendState = {
    port: DEFAULT_PORT,
    appUrl: `http://127.0.0.1:${DEFAULT_PORT}`,
    healthUrl: `http://127.0.0.1:${DEFAULT_PORT}/health`,
    started: false,
    pid: null,
    workspaceRoot,
    runtimeRoot,
    backendRoot,
  }

  backendProcess = spawn(
    pythonCommand,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(DEFAULT_PORT)],
    {
      cwd: backendRoot,
      env: {
        ...process.env,
        APP_PROFILE: process.env.APP_PROFILE || 'local',
        APP_ENV: process.env.APP_ENV || 'local',
        PROFILE: process.env.PROFILE || 'local',
        AUTH_DISABLED: process.env.AUTH_DISABLED || 'true',
        LOCAL_USERNAME: process.env.LOCAL_USERNAME || 'localuser',
        LOCAL_DISPLAY_NAME: process.env.LOCAL_DISPLAY_NAME || 'Local Researcher',
      },
      windowsHide: true,
    }
  )

  backendState.pid = backendProcess.pid

  backendProcess.stdout.on('data', (chunk) => {
    process.stdout.write(`[backend] ${chunk}`)
  })

  backendProcess.stderr.on('data', (chunk) => {
    process.stderr.write(`[backend] ${chunk}`)
  })

  backendProcess.once('exit', (code, signal) => {
    backendState.started = false
    backendState.pid = null
    backendProcess = null
    if (!stoppingBackend && code !== 0 && signal !== 'SIGTERM') {
      process.stderr.write(`[backend] exited with code=${code} signal=${signal}\n`)
    }
    stoppingBackend = false
  })

  try {
    await waitForHealth(backendState.healthUrl)
    backendState.started = true
    return backendState
  } catch (error) {
    await stopBackend()
    throw error
  }
}

function killWindowsProcessTree(pid) {
  return new Promise((resolve) => {
    const killer = spawn('taskkill', ['/pid', String(pid), '/t', '/f'], { windowsHide: true })
    killer.once('exit', () => resolve())
    killer.once('error', () => resolve())
  })
}

async function stopBackend() {
  if (!backendProcess || !backendState.pid) {
    return
  }

  const pid = backendState.pid
  stoppingBackend = true
  if (process.platform === 'win32') {
    await killWindowsProcessTree(pid)
  } else {
    backendProcess.kill('SIGTERM')
  }

  backendProcess = null
  backendState.started = false
  backendState.pid = null
}

function getStatus() {
  return { ...backendState }
}

module.exports = {
  startBackend,
  stopBackend,
  getStatus,
}
