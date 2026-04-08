param(
    [string]$PythonVersion = '3.11.9',
    [switch]$ForceRebuild
)

$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$electronRoot = Resolve-Path (Join-Path $scriptRoot '..')
$workspaceRoot = Resolve-Path (Join-Path $electronRoot '..')
$repoRoot = Resolve-Path (Join-Path $workspaceRoot '..')
$executeRoot = Join-Path $repoRoot 'execute'
$runtimeRoot = Join-Path $executeRoot 'electron\runtime\python'
$cacheRoot = Join-Path $electronRoot '.cache\python-runtime'
$backendRequirements = Join-Path $workspaceRoot 'backend\requirements.txt'
$pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$pythonZip = Join-Path $cacheRoot "python-$PythonVersion-embed-amd64.zip"
$getPip = Join-Path $cacheRoot 'get-pip.py'

function Invoke-ExternalCommand {
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

if ((Test-Path (Join-Path $runtimeRoot 'python.exe')) -and -not $ForceRebuild) {
    Write-Host "Bundled Python runtime already exists at $runtimeRoot"
    exit 0
}

if (Test-Path $runtimeRoot) {
    Remove-Item $runtimeRoot -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $executeRoot | Out-Null
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null

Write-Host "Downloading embedded Python $PythonVersion"
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip

Write-Host "Extracting embedded Python to $runtimeRoot"
Expand-Archive -Path $pythonZip -DestinationPath $runtimeRoot -Force

$pthFile = Get-ChildItem -Path $runtimeRoot -Filter '*._pth' | Select-Object -First 1
if (-not $pthFile) {
    throw "Embedded Python ._pth file not found in $runtimeRoot"
}

$sitePackages = Join-Path $runtimeRoot 'Lib\site-packages'
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null

$pthContent = @(
    [System.IO.Path]::GetFileNameWithoutExtension($pthFile.Name) + '.zip'
    '.'
    'Lib\\site-packages'
    'import site'
)
Set-Content -Path $pthFile.FullName -Value $pthContent -Encoding ASCII

Write-Host 'Downloading pip bootstrap script'
Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile $getPip

$pythonExe = Join-Path $runtimeRoot 'python.exe'
Invoke-ExternalCommand $pythonExe $getPip '--no-warn-script-location'

Invoke-ExternalCommand $pythonExe '-m' 'pip' 'install' '--upgrade' 'pip' 'setuptools' 'wheel' '--no-warn-script-location'
Invoke-ExternalCommand $pythonExe '-m' 'pip' 'install' '-r' $backendRequirements '--no-warn-script-location'

$verification = @(
    'import fastapi'
    'import uvicorn'
    'import numpy'
    'import scipy'
    'import h5py'
    'import fabio'
    'import pyFAI'
    'from PIL import Image'
    "print('python runtime ok')"
) -join '; '

Invoke-ExternalCommand $pythonExe '-c' $verification

Write-Host "Bundled Python runtime is ready at $runtimeRoot"
