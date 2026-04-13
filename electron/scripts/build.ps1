param(
    [switch]$BundlePython,
    [switch]$ForceRebuildPython,
    [switch]$SkipFrontendBuild,
    [switch]$SkipSmokeTest,
    [switch]$ExtendedSmokeTest,
    [string]$PythonVersion = '3.11.9'
)

$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$electronRoot = Resolve-Path (Join-Path $scriptRoot '..')
$workspaceRoot = Resolve-Path (Join-Path $electronRoot '..')
$repoRoot = Resolve-Path (Join-Path $workspaceRoot '..')
$frontendRoot = Join-Path $workspaceRoot 'frontend'
$iconRoot = Join-Path $workspaceRoot 'icon'
$windowsIconPath = Join-Path $iconRoot 'polymindex.ico'
$executeRoot = Join-Path $repoRoot 'execute'
$electronExecuteRoot = Join-Path $executeRoot 'electron'
$distRoot = Join-Path $electronExecuteRoot 'dist'
$smokeOutput = Join-Path $electronExecuteRoot 'smoke-test.json'
$stageWorkspaceRoot = Join-Path $electronExecuteRoot 'stage\workspace'

if (Test-Path $distRoot) {
    Remove-Item -Path (Join-Path $distRoot '*') -Recurse -Force
}
else {
    New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference

    if ($exitCode -ne 0) {
        throw "Command failed with exit code ${exitCode}: $FilePath $($Arguments -join ' ')"
    }
}

function Invoke-ElectronSmokeTest {
    New-Item -ItemType Directory -Force -Path $electronExecuteRoot | Out-Null

    $smokeCandidates = @(
        (Join-Path $distRoot 'win-unpacked\PolymCrystIndex.exe'),
        (Join-Path $distRoot 'PolymCrystIndex.exe')
    )
    $smokeExecutable = $smokeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $smokeExecutable) {
        throw "Smoke test executable not found under $distRoot"
    }

    if (Test-Path $smokeOutput) {
        Remove-Item $smokeOutput -Force
    }

    $previousSmokeFlag = $env:POLYCRYINDEX_SMOKE_TEST
    $previousSmokeOutput = $env:POLYCRYINDEX_SMOKE_TEST_OUTPUT

    $env:POLYCRYINDEX_SMOKE_TEST = '1'
    $env:POLYCRYINDEX_SMOKE_TEST_OUTPUT = $smokeOutput

    try {
        $process = Start-Process -FilePath $smokeExecutable -PassThru -Wait -WindowStyle Hidden
        if ($process.ExitCode -ne 0) {
            throw "Smoke test executable exited with code $($process.ExitCode)"
        }

        if (-not (Test-Path $smokeOutput)) {
            throw "Smoke test did not produce result file: $smokeOutput"
        }

        $smokeResult = Get-Content -Path $smokeOutput -Raw | ConvertFrom-Json
        if (-not $smokeResult.ok) {
            throw "Smoke test reported failure: $($smokeResult | ConvertTo-Json -Compress)"
        }

        Write-Host "Smoke test passed: $smokeExecutable"
    }
    finally {
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
    }
}

function Update-WindowsIconBundle {
    if (-not (Test-Path $windowsIconPath)) {
        throw "Windows icon not found: $windowsIconPath"
    }

    Invoke-CheckedCommand python (Join-Path $scriptRoot 'normalize-windows-icon.py') $windowsIconPath
    Write-Host "Normalized Windows icon bundle: $windowsIconPath"
}

if (-not $SkipFrontendBuild) {
    Push-Location $frontendRoot
    $previousProfile = $env:VITE_APP_PROFILE
    try {
        $env:VITE_APP_PROFILE = 'local'
        Invoke-CheckedCommand npm 'run' 'build:desktop'
    }
    finally {
        if ($null -eq $previousProfile) {
            Remove-Item Env:VITE_APP_PROFILE -ErrorAction SilentlyContinue
        }
        else {
            $env:VITE_APP_PROFILE = $previousProfile
        }
        Pop-Location
    }
}

if ($BundlePython) {
    $pythonRuntimeArgs = @{
        PythonVersion = $PythonVersion
    }

    if ($ForceRebuildPython) {
        $pythonRuntimeArgs.ForceRebuild = $true
    }

    & (Join-Path $scriptRoot 'prepare-python-runtime.ps1') @pythonRuntimeArgs
}

Update-WindowsIconBundle

Push-Location $electronRoot
try {
    $stagePrepareSucceeded = $false
    & (Join-Path $scriptRoot 'prepare-workspace-stage.ps1')
    $stagePrepareSucceeded = $?
    if (-not $stagePrepareSucceeded) {
        throw 'prepare-workspace-stage.ps1 failed'
    }

    if (-not (Test-Path $stageWorkspaceRoot)) {
        throw "Expected staged workspace not found: $stageWorkspaceRoot"
    }

    Write-Host "Packaging Electron app from staged workspace: $stageWorkspaceRoot"

    Invoke-CheckedCommand npx 'electron-builder' '--config' 'electron-builder.json' '--win'
}
finally {
    Pop-Location
}

if (-not $SkipSmokeTest) {
    Invoke-ElectronSmokeTest
}

if ($ExtendedSmokeTest) {
    & (Join-Path $scriptRoot 'smoke-port-test.ps1') -All -OutputDir $electronExecuteRoot
}
