$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$electronRoot = Resolve-Path (Join-Path $scriptRoot '..')
$workspaceRoot = Resolve-Path (Join-Path $electronRoot '..')
$repoRoot = Resolve-Path (Join-Path $workspaceRoot '..')
$stageRoot = Join-Path $repoRoot 'execute\electron\stage\workspace'
$runtimeSource = Join-Path $repoRoot 'execute\electron\runtime'
$runtimePythonExe = Join-Path $runtimeSource 'python\python.exe'
$frontendDist = Join-Path $workspaceRoot 'frontend\dist'
if (Test-Path $stageRoot) {
    Remove-Item $stageRoot -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null

if (-not (Test-Path $frontendDist)) {
    throw "Frontend dist not found: $frontendDist"
}

if (-not (Test-Path $runtimePythonExe)) {
    throw "Bundled Python runtime not found: $runtimePythonExe. Run prepare-python-runtime.ps1 before packaging."
}

$copyTargets = @(
    'backend',
    'fortrancode',
    'fiber_diffraction_indexing'
)

foreach ($target in $copyTargets) {
    Copy-Item -Path (Join-Path $workspaceRoot $target) -Destination (Join-Path $stageRoot $target) -Recurse -Force
}

$stageFortranRoot = Join-Path $stageRoot 'fortrancode'
$optExe = Join-Path $stageFortranRoot 'lm_opt2.exe'
$postExe = Join-Path $stageFortranRoot 'lm_postprocess.exe'
$gfortran = Get-Command gfortran -ErrorAction SilentlyContinue
if (-not $gfortran) {
    throw 'gfortran not found. Cannot prepare Windows Fortran binaries for Electron packaging.'
}

$mingwBin = Split-Path -Parent $gfortran.Source
$requiredRuntimeDlls = @(
    'libgcc_s_seh-1.dll',
    'libgomp-1.dll',
    'libquadmath-0.dll'
)

$optionalRuntimeDlls = @(
    'libstdc++-6.dll',
    'libwinpthread-1.dll'
)

Push-Location $stageFortranRoot
try {
    if (Test-Path $optExe) {
        Remove-Item $optExe -Force
    }
    if (Test-Path $postExe) {
        Remove-Item $postExe -Force
    }

    & $gfortran.Source -O2 -fopenmp -o $optExe 'minpack.f90' 'lm_opt2.f90'
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to build lm_opt2.exe'
    }

    & $gfortran.Source -O2 -o $postExe 'out.f90'
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to build lm_postprocess.exe'
    }

    foreach ($dllName in $requiredRuntimeDlls) {
        $dllSource = Join-Path $mingwBin $dllName
        if (-not (Test-Path $dllSource)) {
            throw "Required Fortran runtime DLL not found: $dllSource"
        }
        Copy-Item -Path $dllSource -Destination (Join-Path $stageFortranRoot $dllName) -Force
    }

    foreach ($dllName in $optionalRuntimeDlls) {
        $dllSource = Join-Path $mingwBin $dllName
        if (Test-Path $dllSource) {
            Copy-Item -Path $dllSource -Destination (Join-Path $stageFortranRoot $dllName) -Force
        }
    }
}
finally {
    Pop-Location
}

$frontendStage = Join-Path $stageRoot 'frontend'
New-Item -ItemType Directory -Force -Path $frontendStage | Out-Null
Copy-Item -Path $frontendDist -Destination (Join-Path $frontendStage 'dist') -Recurse -Force

Copy-Item -Path $runtimeSource -Destination (Join-Path $stageRoot 'runtime') -Recurse -Force

Write-Host "Prepared staged Workspace resources at $stageRoot"
