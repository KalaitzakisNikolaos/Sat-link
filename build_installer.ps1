param(
    [string]$PythonExe = "python",
    [string]$Version = "3.0.0",
    [switch]$SkipDependencies,
    [switch]$SkipExeBuild,
    [switch]$SkipInstaller,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Resolve-IsccPath {
    $cmd = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )

    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

function Ensure-SpecRecursionLimit {
    param([string]$SpecPath)

    if (-not (Test-Path $SpecPath)) {
        return
    }

    $content = Get-Content -Raw -Path $SpecPath
    if ($content -match "setrecursionlimit\(") {
        return
    }

    $prefix = "import sys; sys.setrecursionlimit(sys.getrecursionlimit() * 5)`r`n"
    Set-Content -Path $SpecPath -Value ($prefix + $content) -Encoding UTF8
    Write-Host "Patched spec with recursion-limit workaround: $SpecPath" -ForegroundColor Yellow
}

function Invoke-PyInstallerBuild {
    param(
        [string]$PythonExe,
        [string[]]$PyInstallerArgs
    )

    # Stream PyInstaller logs to console, but keep function output as a single numeric exit code.
    & $PythonExe -m PyInstaller @PyInstallerArgs 2>&1 | Out-Host
    $exitCode = $LASTEXITCODE
    return [int]$exitCode
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$exePath = "dist\Sat-Link\Sat-Link.exe"
$specPath = Join-Path $repoRoot "Sat-Link.spec"

$iscc = $null
if (-not $SkipInstaller) {
    $iscc = Resolve-IsccPath
    if (-not $iscc) {
        throw "Inno Setup compiler (ISCC.exe) was not found. Install Inno Setup 6 or re-run with -SkipInstaller."
    }
}

if ($Clean) {
    Write-Step "Cleaning old build outputs"
    Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "release" -ErrorAction SilentlyContinue
    Remove-Item -Force "Sat-Link.spec" -ErrorAction SilentlyContinue
}

if (-not $SkipDependencies) {
    $cacheDir = Join-Path $repoRoot ".build-cache"
    $hashFile = Join-Path $cacheDir "requirements.sha256"
    $requirementsHash = (Get-FileHash -Path "requirements.txt" -Algorithm SHA256).Hash
    $canSkip = $false

    if ((Test-Path $hashFile) -and ((Get-Content -Raw -Path $hashFile).Trim() -eq $requirementsHash)) {
        & $PythonExe -m PyInstaller --version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $canSkip = $true
        }
    }

    if ($canSkip) {
        Write-Step "Dependencies unchanged; skipping install"
    } else {
        Write-Step "Installing dependencies for build"
        & $PythonExe -m pip install --upgrade pip
        & $PythonExe -m pip install -r requirements.txt
        & $PythonExe -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib
        New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
        Set-Content -Path $hashFile -Value $requirementsHash -Encoding ASCII
    }
}

if (-not $SkipExeBuild) {
    Write-Step "Building Windows executable with PyInstaller"
    $pyInstallerArgs = @(
        "--noconfirm",
        "--windowed",
        "--name", "Sat-Link",
        "--icon", "satellite_icon.ico",
        "--add-data", "assets;assets",
        "--add-data", "txt_info;txt_info",
        "--add-data", "hmu.png;.",
        "--add-data", "detailed_shapes.csv;.",
        "--add-data", "satellite_icon.ico;.",
        "--collect-all", "pyvista",
        "--collect-all", "pyvistaqt",
        "--collect-data", "pyqtgraph",
        "--collect-data", "matplotlib",
        "--collect-data", "seaborn",
        "--exclude-module", "torch",
        "--exclude-module", "torchvision",
        "--exclude-module", "torchaudio",
        "--exclude-module", "tensorflow",
        "--exclude-module", "jax",
        "--exclude-module", "triton",
        "--exclude-module", "plotly",
        "--exclude-module", "sympy",
        "--exclude-module", "skimage",
        "--exclude-module", "sklearn",
        "--exclude-module", "numba",
        "--exclude-module", "llvmlite",
        "--exclude-module", "imageio",
        "--exclude-module", "tkinter",
        "--exclude-module", "_tkinter",
        "--exclude-module", "PyQt5.QtBluetooth",
        "--exclude-module", "PyQt5.QtDesigner",
        "--exclude-module", "PyQt5.QtHelp",
        "--exclude-module", "PyQt5.QtLocation",
        "--exclude-module", "PyQt5.QtMultimedia",
        "--exclude-module", "PyQt5.QtMultimediaWidgets",
        "--exclude-module", "PyQt5.QtNfc",
        "--exclude-module", "PyQt5.QtQml",
        "--exclude-module", "PyQt5.QtQuick",
        "--exclude-module", "PyQt5.QtQuick3D",
        "--exclude-module", "PyQt5.QtQuickWidgets",
        "--exclude-module", "PyQt5.QtRemoteObjects",
        "--exclude-module", "PyQt5.QtSensors",
        "--exclude-module", "PyQt5.QtSerialPort",
        "--exclude-module", "PyQt5.QtSql",
        "--exclude-module", "PyQt5.QtTextToSpeech",
        "--exclude-module", "PyQt5.QtWebEngine",
        "--exclude-module", "PyQt5.QtWebEngineCore",
        "--exclude-module", "PyQt5.QtWebEngineWidgets",
        "--exclude-module", "PyQt5.QtWebChannel",
        "--exclude-module", "PyQt5.QtWebSockets",
        "--exclude-module", "PyQt5.QtWinExtras",
        "--exclude-module", "PyQt5.QtXml",
        "--exclude-module", "PyQt5.QtXmlPatterns",
        "--exclude-module", "pyqtgraph.examples",
        "main_advanced.py"
    )

    if ($Clean) {
        $pyInstallerArgs = @("--clean") + $pyInstallerArgs
    }

    $buildExitCode = Invoke-PyInstallerBuild -PythonExe $PythonExe -PyInstallerArgs $pyInstallerArgs
    if (($buildExitCode -ne 0) -or (-not (Test-Path $exePath))) {
        if (Test-Path $specPath) {
            Write-Warning "PyInstaller did not produce an executable (exit code: $buildExitCode). Retrying using .spec recursion workaround."
            Ensure-SpecRecursionLimit -SpecPath $specPath
            $retryArgs = @("--noconfirm")
            if ($Clean) {
                $retryArgs += "--clean"
            }
            $retryArgs += $specPath
            $buildExitCode = Invoke-PyInstallerBuild -PythonExe $PythonExe -PyInstallerArgs $retryArgs
        }
    }

    if (($buildExitCode -ne 0) -or (-not (Test-Path $exePath))) {
        throw "PyInstaller failed (exit code: $buildExitCode) and $exePath was not found."
    }
    Write-Host "Executable build complete: $exePath" -ForegroundColor Green
} else {
    if (-not (Test-Path $exePath)) {
        throw "SkipExeBuild was requested, but $exePath was not found."
    }
    Write-Host "Skipping executable build; reusing existing: $exePath" -ForegroundColor Yellow
}

if ($SkipInstaller) {
    Write-Host "Skipping installer build as requested." -ForegroundColor Yellow
    exit 0
}

Write-Step "Compiling installer with Inno Setup"

$issFile = Join-Path $repoRoot "installer\SatLinkSetup.iss"
if (-not (Test-Path $issFile)) {
    throw "Installer script not found: $issFile"
}

& $iscc $issFile "/DAppVersion=$Version"

Write-Host "Installer build complete. Output is under release\" -ForegroundColor Green
