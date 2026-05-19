param(
    [switch]$TestDefault,
    [switch]$TestConflict,
    [switch]$TestOverride,
    [switch]$All,
    [string]$SmokeExecutable,
    [string]$OutputDir
)

$ErrorActionPreference = 'Stop'

# Constants from backend-manager.js
$DESKTOP_PREFERRED_PORT = 18700
$PORT_SCAN_WINDOW = 20

# Helper: check whether a port is bindable (free) on 127.0.0.1
function Test-PortBindable {
    param([int]$Port)
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse('127.0.0.1'), $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    }
    catch {
        return $false
    }
}

# Default smoke output names
$SMOKE_DEFAULT = 'smoke-default.json'
$SMOKE_CONFLICT = 'smoke-conflict.json'
$SMOKE_OVERRIDE = 'smoke-override.json'

# Find smoke executable if not provided
# Use the same layout as build.ps1: repo/execute/electron/dist
if (-not $SmokeExecutable) {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $electronRoot = Resolve-Path (Join-Path $scriptRoot '..')
    $workspaceRoot = Resolve-Path (Join-Path $electronRoot '..')
    $repoRoot = Resolve-Path (Join-Path $workspaceRoot '..')
    $executeRoot = Join-Path $repoRoot 'execute'
    $electronExecuteRoot = Join-Path $executeRoot 'electron'
    $distRoot = Join-Path $electronExecuteRoot 'dist'

    $smokeCandidates = @(
        (Join-Path $distRoot 'win-unpacked\PolymCrystIndex.exe'),
        (Join-Path $distRoot 'PolymCrystIndex.exe')
    )
    $SmokeExecutable = $smokeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $SmokeExecutable) {
        throw "Smoke test executable not found under $distRoot"
    }
}

# Default output dir to executable's parent directory
if (-not $OutputDir) {
    $OutputDir = Split-Path -Parent $SmokeExecutable
}

# Ensure output directory exists
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Helper function to run smoke test and parse result
function Invoke-SmokeTest {
    param(
        [string]$OutputPath,
        [string]$BackendPortEnv = $null
    )

    # Clean up any existing output
    if (Test-Path $OutputPath) {
        Remove-Item $OutputPath -Force
    }

    # Save and set env vars
    $previousSmokeFlag = $env:POLYCRYINDEX_SMOKE_TEST
    $previousSmokeOutput = $env:POLYCRYINDEX_SMOKE_TEST_OUTPUT
    $previousBackendPort = $env:POLYCRYINDEX_BACKEND_PORT

    $env:POLYCRYINDEX_SMOKE_TEST = '1'
    $env:POLYCRYINDEX_SMOKE_TEST_OUTPUT = $OutputPath

    if ($null -ne $BackendPortEnv) {
        $env:POLYCRYINDEX_BACKEND_PORT = $BackendPortEnv
    }
    elseif ($null -ne $previousBackendPort) {
        Remove-Item Env:POLYCRYINDEX_BACKEND_PORT -ErrorAction SilentlyContinue
    }

    try {
        $process = Start-Process -FilePath $SmokeExecutable -PassThru -Wait -WindowStyle Hidden
        if ($process.ExitCode -ne 0) {
            throw "Smoke test executable exited with code $($process.ExitCode)"
        }

        if (-not (Test-Path $OutputPath)) {
            throw "Smoke test did not produce result file: $OutputPath"
        }

        $smokeResult = Get-Content -Path $OutputPath -Raw | ConvertFrom-Json
        return $smokeResult
    }
    finally {
        # Restore env vars
        if ($null -eq $previousSmokeFlag) {
            Remove-Item Env:POLYCRYINDEX_SMOKE_TEST -ErrorAction SilentlyContinue
        }
        else {
            $env:POLYCRYINDEX_SMOKE_TEST = $previousSmokeFlag
        }

        if ($null -eq $previousSmokeOutput) {
            Remove-Item Env:POLYCRYINDEX_SMOKE_TEST_OUTPUT -ErrorAction SilentlyContinue
        }
        else {
            $env:POLYCRYINDEX_SMOKE_TEST_OUTPUT = $previousSmokeOutput
        }

        if ($null -ne $previousBackendPort) {
            $env:POLYCRYINDEX_BACKEND_PORT = $previousBackendPort
        }
        elseif ($null -ne $BackendPortEnv) {
            Remove-Item Env:POLYCRYINDEX_BACKEND_PORT -ErrorAction SilentlyContinue
        }
    }
}

# Test: Default preferred port (should be free and used)
function Test-DefaultPort {
    $outputPath = Join-Path $OutputDir $SMOKE_DEFAULT
    Write-Host "Running Test-DefaultPort..."

    try {
        $result = Invoke-SmokeTest -OutputPath $outputPath

        if (-not $result.ok) {
            throw "Smoke test failed: ok=$($result.ok)"
        }

        if ($result.backendInfo.port -ne $DESKTOP_PREFERRED_PORT) {
            throw "Expected port $DESKTOP_PREFERRED_PORT, got $($result.backendInfo.port)"
        }

        Write-Host "Test-DefaultPort PASSED: backend started on default port $($result.backendInfo.port)"
        return $true
    }
    catch {
        Write-Host "Test-DefaultPort FAILED: $_"
        throw
    }
}

# Test: Preferred port occupied, should fallback to the first free port in the scan window
function Test-ConflictFallback {
    $outputPath = Join-Path $OutputDir $SMOKE_CONFLICT
    Write-Host "Running Test-ConflictFallback..."

    $listener = $null
    try {
        # Occupy the preferred port so the backend must fallback
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse('127.0.0.1'), $DESKTOP_PREFERRED_PORT)
        $listener.Start()
        Write-Host "  Occupied port $DESKTOP_PREFERRED_PORT with TCP listener"

        # Dynamically discover the first free port in the scan window
        $firstFreePort = $null
        for ($offset = 1; $offset -lt $PORT_SCAN_WINDOW; $offset++) {
            $candidate = $DESKTOP_PREFERRED_PORT + $offset
            if ($candidate -gt 65535) { break }
            if (Test-PortBindable -Port $candidate) {
                $firstFreePort = $candidate
                break
            }
        }

        if ($null -eq $firstFreePort) {
            throw "No free port found in range $($DESKTOP_PREFERRED_PORT + 1)-$($DESKTOP_PREFERRED_PORT + $PORT_SCAN_WINDOW - 1)"
        }
        Write-Host "  First free fallback port detected: $firstFreePort"

        $result = Invoke-SmokeTest -OutputPath $outputPath

        if (-not $result.ok) {
            throw "Smoke test failed: ok=$($result.ok)"
        }

        if ($result.backendInfo.port -eq $DESKTOP_PREFERRED_PORT) {
            throw "Expected fallback port (not $DESKTOP_PREFERRED_PORT), but got $DESKTOP_PREFERRED_PORT"
        }

        if ($result.backendInfo.port -ne $firstFreePort) {
            throw "Expected backend on first free port ${firstFreePort}, but got $($result.backendInfo.port)"
        }

        Write-Host "Test-ConflictFallback PASSED: backend fell back to first free port $($result.backendInfo.port)"
        return $true
    }
    finally {
        if ($null -ne $listener) {
            $listener.Stop()
            Write-Host "  Released port $DESKTOP_PREFERRED_PORT"
        }
    }
}

# Test: POLYCRYINDEX_BACKEND_PORT env override
function Test-EnvOverride {
    $outputPath = Join-Path $OutputDir $SMOKE_OVERRIDE
    $overridePort = 19300
    Write-Host "Running Test-EnvOverride with port $overridePort..."

    $previousBackendPort = $env:POLYCRYINDEX_BACKEND_PORT
    try {
        $env:POLYCRYINDEX_BACKEND_PORT = $overridePort.ToString()
        $result = Invoke-SmokeTest -OutputPath $outputPath -BackendPortEnv $overridePort.ToString()

        if (-not $result.ok) {
            throw "Smoke test failed: ok=$($result.ok)"
        }

        if ($result.backendInfo.port -ne $overridePort) {
            throw "Expected override port $overridePort, got $($result.backendInfo.port)"
        }

        Write-Host "Test-EnvOverride PASSED: backend honored POLYCRYINDEX_BACKEND_PORT=$overridePort"
        return $true
    }
    finally {
        if ($null -ne $previousBackendPort) {
            $env:POLYCRYINDEX_BACKEND_PORT = $previousBackendPort
        }
        else {
            Remove-Item Env:POLYCRYINDEX_BACKEND_PORT -ErrorAction SilentlyContinue
        }
    }
}

# Determine which tests to run
$runAll = $All -or (-not $TestDefault -and -not $TestConflict -and -not $TestOverride)
$testsFailed = $false

if ($runAll -or $TestDefault) {
    try {
        Test-DefaultPort
    }
    catch {
        $testsFailed = $true
        Write-Host "Test-DefaultPort failed: $_" -ForegroundColor Red
    }
}

if ($runAll -or $TestConflict) {
    try {
        Test-ConflictFallback
    }
    catch {
        $testsFailed = $true
        Write-Host "Test-ConflictFallback failed: $_" -ForegroundColor Red
    }
}

if ($runAll -or $TestOverride) {
    try {
        Test-EnvOverride
    }
    catch {
        $testsFailed = $true
        Write-Host "Test-EnvOverride failed: $_" -ForegroundColor Red
    }
}

if ($testsFailed) {
    throw "One or more smoke port tests failed."
}

Write-Host ""
Write-Host "All requested smoke port tests passed." -ForegroundColor Green
