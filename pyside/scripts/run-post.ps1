param()

$ErrorActionPreference = 'Stop'

function Invoke-Step {
    param([string]$FilePath, [string[]]$Arguments)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pysideRoot = Resolve-Path (Join-Path $scriptRoot '..')
$toolRoot = Join-Path $pysideRoot 'post\silxversion'
$venvRoot = Join-Path $pysideRoot '.venv-post'
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'
$requirements = Join-Path $toolRoot 'requirements.txt'

if (-not (Test-Path $venvPython)) {
    Invoke-Step 'python' @('-m', 'venv', $venvRoot)
}

Invoke-Step $venvPython @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-Step $venvPython @('-m', 'pip', 'install', '-r', $requirements)

Push-Location $toolRoot
try {
    Invoke-Step $venvPython @('post16.py')
}
finally {
    Pop-Location
}
