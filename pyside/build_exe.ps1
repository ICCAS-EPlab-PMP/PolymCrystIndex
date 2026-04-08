param(
    [switch]$SkipPrevious,
    [switch]$SkipPost
)

$ErrorActionPreference = 'Stop'

function Invoke-Step {
    param([string]$FilePath, [string[]]$Arguments)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Remove-PathIfExists {
    param([string]$Path)
    if (Test-Path $Path) {
        Remove-Item -Recurse -Force $Path
    }
}

function Invoke-PyInstallerBuild {
    param(
        [string]$PythonExe,
        [string]$SpecPath,
        [string]$PackageMode,
        [string]$DistRoot,
        [string]$BuildRoot,
        [string]$SpecOutRoot
    )

    $previousMode = $env:POLYCRY_PYSIDE_PACKAGE_MODE
    $env:POLYCRY_PYSIDE_PACKAGE_MODE = $PackageMode
    try {
        Invoke-Step $PythonExe @(
            '-m', 'PyInstaller',
            '--noconfirm',
            '--clean',
            '--distpath', $DistRoot,
            '--workpath', $BuildRoot,
            '--specpath', $SpecOutRoot,
            $SpecPath
        )
    }
    finally {
        if ($null -eq $previousMode) {
            Remove-Item Env:POLYCRY_PYSIDE_PACKAGE_MODE -ErrorAction SilentlyContinue
        }
        else {
            $env:POLYCRY_PYSIDE_PACKAGE_MODE = $previousMode
        }
    }
}

function Copy-PackageArtifact {
    param(
        [string]$SourcePath,
        [string]$TargetRoot,
        [string]$ExecutableName
    )

    Remove-PathIfExists $TargetRoot
    New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null

    if (Test-Path $SourcePath -PathType Container) {
        Copy-Item -Recurse -Force (Join-Path $SourcePath '*') $TargetRoot
    }
    elseif (Test-Path $SourcePath -PathType Leaf) {
        Copy-Item -Force $SourcePath (Join-Path $TargetRoot $ExecutableName)
    }
    else {
        throw "Built artifact not found: $SourcePath"
    }
}

function Invoke-PackageTarget {
    param(
        [string]$Label,
        [string]$PythonExe,
        [string]$SpecPath,
        [string]$BaseName,
        [string]$DistRoot,
        [string]$BuildRoot,
        [string]$SpecOutRoot,
        [string]$WinExeRoot,
        [string]$TargetFolderName
    )

    $exeName = "$BaseName.exe"
    $onedirPath = Join-Path $DistRoot $BaseName
    $onefilePath = Join-Path $DistRoot $exeName
    $targetRoot = Join-Path $WinExeRoot $TargetFolderName
    $onefileError = $null
    $fallbackTriggered = $false
    $selectedMode = $null
    $sourceArtifact = $null

    Remove-PathIfExists $onedirPath
    Remove-PathIfExists $onefilePath

    try {
        Write-Host "[$Label] Attempting onefile package..."
        Invoke-PyInstallerBuild -PythonExe $PythonExe -SpecPath $SpecPath -PackageMode 'onefile' -DistRoot $DistRoot -BuildRoot $BuildRoot -SpecOutRoot $SpecOutRoot
        if (-not (Test-Path $onefilePath -PathType Leaf)) {
            throw "Onefile build finished but expected artifact is missing: $onefilePath"
        }
        $selectedMode = 'onefile'
        $sourceArtifact = $onefilePath
    }
    catch {
        $fallbackTriggered = $true
        $onefileError = $_.Exception.Message
        Write-Warning "[$Label] Onefile package failed, falling back to onedir. $onefileError"

        Remove-PathIfExists $onedirPath
        Remove-PathIfExists $onefilePath

        Write-Host "[$Label] Attempting onedir package..."
        Invoke-PyInstallerBuild -PythonExe $PythonExe -SpecPath $SpecPath -PackageMode 'onedir' -DistRoot $DistRoot -BuildRoot $BuildRoot -SpecOutRoot $SpecOutRoot
        if (-not (Test-Path $onedirPath -PathType Container)) {
            throw "Onedir fallback finished but expected artifact is missing: $onedirPath"
        }
        $selectedMode = 'onedir'
        $sourceArtifact = $onedirPath
    }

    Copy-PackageArtifact -SourcePath $sourceArtifact -TargetRoot $targetRoot -ExecutableName $exeName

    return [pscustomobject]@{
        Label = $Label
        BaseName = $BaseName
        Mode = $selectedMode
        DistArtifact = $sourceArtifact
        WinExeTarget = $targetRoot
        FallbackTriggered = $fallbackTriggered
        OnefileError = $onefileError
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pysideRoot = Resolve-Path $scriptRoot
$repoRoot = Resolve-Path (Join-Path $pysideRoot '..')
$venvRoot = Join-Path $pysideRoot '.venv-build'
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'
$executeRoot = Join-Path $repoRoot 'execute\pyside'
$distRoot = Join-Path $executeRoot 'dist'
$buildRoot = Join-Path $executeRoot 'build'
$specOutRoot = Join-Path $executeRoot 'spec'
$winExeRoot = Join-Path $executeRoot 'win-exe'
$summaryFile = Join-Path $executeRoot 'package-summary.txt'
$previousSpec = Join-Path $pysideRoot 'package_previous.spec'
$postSpec = Join-Path $pysideRoot 'package_post.spec'

if (-not (Test-Path $venvPython)) {
    Invoke-Step 'python' @('-m', 'venv', $venvRoot)
}

Invoke-Step $venvPython @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-Step $venvPython @('-m', 'pip', 'install', 'PyInstaller', 'pyinstaller-hooks-contrib', 'hdf5plugin')
Invoke-Step $venvPython @('-m', 'pip', 'install', '-r', (Join-Path $pysideRoot 'previous\requirements.txt'))
Invoke-Step $venvPython @('-m', 'pip', 'install', '-r', (Join-Path $pysideRoot 'post\silxversion\requirements.txt'))

New-Item -ItemType Directory -Force -Path $distRoot, $buildRoot, $specOutRoot, $winExeRoot | Out-Null

$results = @()

Push-Location $pysideRoot
try {
    if (-not $SkipPrevious) {
        $results += Invoke-PackageTarget -Label 'previous' -PythonExe $venvPython -SpecPath $previousSpec -BaseName 'PolymCrystIndex-Previous' -DistRoot $distRoot -BuildRoot $buildRoot -SpecOutRoot $specOutRoot -WinExeRoot $winExeRoot -TargetFolderName 'pyside-previous'
    }
    if (-not $SkipPost) {
        $results += Invoke-PackageTarget -Label 'post' -PythonExe $venvPython -SpecPath $postSpec -BaseName 'PolymCrystIndex-Post' -DistRoot $distRoot -BuildRoot $buildRoot -SpecOutRoot $specOutRoot -WinExeRoot $winExeRoot -TargetFolderName 'pyside-post'
    }
}
finally {
    Pop-Location
}

$summaryLines = @(
    "PySide packaging summary",
    "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Output root: $executeRoot"
)

foreach ($result in $results) {
    $summaryLines += ''
    $summaryLines += "Target: $($result.Label)"
    $summaryLines += "Mode: $($result.Mode)"
    $summaryLines += "Fallback triggered: $($result.FallbackTriggered)"
    $summaryLines += "Dist artifact: $($result.DistArtifact)"
    $summaryLines += "Win-exe target: $($result.WinExeTarget)"
    if ($result.OnefileError) {
        $summaryLines += "Onefile error: $($result.OnefileError)"
    }
}

Set-Content -Path $summaryFile -Value $summaryLines -Encoding UTF8

Write-Host 'PySide packaging completed.'
foreach ($result in $results) {
    Write-Host ("[{0}] final mode: {1}; fallback triggered: {2}" -f $result.Label, $result.Mode, $result.FallbackTriggered)
}
Write-Host "Packaging summary written to: $summaryFile"
