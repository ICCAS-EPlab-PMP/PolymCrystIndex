param(
    [switch]$BundlePython,
    [switch]$ForceRebuildPython,
    [switch]$SkipFrontendBuild,
    [string]$PythonVersion = '3.11.9'
)

$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$electronRoot = Resolve-Path (Join-Path $scriptRoot '..')
$workspaceRoot = Resolve-Path (Join-Path $electronRoot '..')
$frontendRoot = Join-Path $workspaceRoot 'frontend'

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

Push-Location $electronRoot
try {
    Invoke-CheckedCommand npm 'run' 'start'
}
finally {
    Pop-Location
}
