const fs = require('fs')
const http = require('http')
const net = require('net')
const path = require('path')
const { spawn } = require('child_process')

const DESKTOP_PREFERRED_PORT = 18700
const PORT_SCAN_WINDOW = 20
const HEALTH_TIMEOUT_MS = 45000
const HEALTH_RETRY_MS = 1000

// Parse optional env-var override for preferred start port
let preferredStart = DESKTOP_PREFERRED_PORT
if (process.env.POLYCRYINDEX_BACKEND_PORT) {
  const envPort = Number(process.env.POLYCRYINDEX_BACKEND_PORT)
  if (!Number.isInteger(envPort) || envPort < 1 || envPort > 65535) {
    throw new Error(
      `POLYCRYINDEX_BACKEND_PORT 必须为 1-65535 之间的整数，当前值: ${process.env.POLYCRYINDEX_BACKEND_PORT}`
    )
  }
  preferredStart = envPort
}

/**
 * Probe whether a TCP port is free on the given host.
 * Returns true if the port is available, false if occupied.
 */
function probePort(host, port) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.once('error', () => resolve(false))
    server.once('listening', () => {
      server.close()
      resolve(true)
    })
    server.listen(port, host)
  })
}

/**
 * Scan ports from preferredStart to preferredStart + windowSize - 1.
 * Returns the first free port, or throws if all are occupied.
 */
async function findFreePort(preferredStart, windowSize) {
  const host = '127.0.0.1'
  for (let offset = 0; offset < windowSize; offset++) {
    const port = preferredStart + offset
    if (port > 65535) break
    if (await probePort(host, port)) {
      return port
    }
  }
  const rangeEnd = Math.min(preferredStart + windowSize - 1, 65535)
  throw new Error(
    `没有可用端口 (扫描范围: ${preferredStart}-${rangeEnd})，请关闭占用端口的其他程序后重试`
  )
}

let backendProcess = null
let stoppingBackend = false
let backendExitInfo = null
let backendStderrTail = ''
let backendState = {
  port: null,
  appUrl: null,
  healthUrl: null,
  started: false,
  pid: null,
  workspaceRoot: null,
  runtimeRoot: null,
  backendRoot: null,
  runtimeDataDir: null,
}

function appendBackendStderr(chunk) {
  const text = chunk.toString()
  backendStderrTail = `${backendStderrTail}${text}`.slice(-8000)
}

function buildBackendExitError() {
  if (!backendExitInfo) {
    return null
  }

  const suffix = backendStderrTail.trim()
    ? `\n\n后端错误输出:\n${backendStderrTail.trim()}`
    : ''

  return new Error(
    `本地后端进程已提前退出 (code=${backendExitInfo.code}, signal=${backendExitInfo.signal || 'none'})${suffix}`
  )
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
    const exitError = buildBackendExitError()
    if (exitError && !stoppingBackend) {
      throw exitError
    }

    try {
      return await httpGetJson(healthUrl)
    } catch (error) {
      lastError = error
      await new Promise((resolve) => setTimeout(resolve, HEALTH_RETRY_MS))
    }
  }

  const exitError = buildBackendExitError()
  if (exitError && !stoppingBackend) {
    throw exitError
  }

  throw new Error(`本地后端健康检查超时: ${lastError ? lastError.message : 'unknown error'}`)
}

async function startBackend({ packaged, userDataDir }) {
  if (backendProcess && backendState.started) {
    return backendState
  }

  const workspaceRoot = resolveWorkspaceRoot(packaged)
  const runtimeRoot = resolveRuntimeRoot(packaged, workspaceRoot)
  const backendRoot = path.join(workspaceRoot, 'backend')
  const frontendDist = path.join(workspaceRoot, 'frontend', 'dist', 'index.html')
  const fortranRoot = path.join(workspaceRoot, 'fortrancode')
  const pythonCommand = resolvePythonCommand(runtimeRoot)
  const runtimeDataDir = packaged ? path.join(userDataDir, 'backend-runtime') : null

  ensurePathExists(workspaceRoot, 'Workspace 根目录')
  ensurePathExists(backendRoot, 'backend 目录')
  ensurePathExists(frontendDist, 'frontend dist')
  ensurePathExists(fortranRoot, 'fortrancode 目录')
  if (runtimeDataDir) {
    fs.mkdirSync(runtimeDataDir, { recursive: true })
  }

  const port = await findFreePort(preferredStart, PORT_SCAN_WINDOW)
  process.stdout.write(`[backend] Using port ${port} (preferred: ${preferredStart})\n`)
  if (runtimeDataDir) {
    process.stdout.write(`[backend] Using runtime data directory ${runtimeDataDir}\n`)
  }

  backendExitInfo = null
  backendStderrTail = ''

  backendState = {
    port,
    appUrl: `http://127.0.0.1:${port}`,
    healthUrl: `http://127.0.0.1:${port}/health`,
    started: false,
    pid: null,
    workspaceRoot,
    runtimeRoot,
    backendRoot,
    runtimeDataDir,
  }

  backendProcess = spawn(
    pythonCommand,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(port)],
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
        POLYCRYINDEX_RUNTIME_DATA_DIR: runtimeDataDir || '',
      },
      windowsHide: true,
    }
  )

  backendState.pid = backendProcess.pid

  backendProcess.stdout.on('data', (chunk) => {
    process.stdout.write(`[backend] ${chunk}`)
  })

  backendProcess.stderr.on('data', (chunk) => {
    appendBackendStderr(chunk)
    process.stderr.write(`[backend] ${chunk}`)
  })

  backendProcess.once('exit', (code, signal) => {
    backendExitInfo = { code, signal }
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
  backendState.runtimeDataDir = null
}

function getStatus() {
  return { ...backendState }
}

module.exports = {
  startBackend,
  stopBackend,
  getStatus,
}
