param(
    [string]$Python = "",
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $Root

function Resolve-Python {
    param([string]$Requested)
    if ($Requested) {
        $Command = Get-Command $Requested -ErrorAction SilentlyContinue
        if (-not $Command) {
            throw "Requested Python was not found: $Requested"
        }
        return $Command.Source
    }
    $Command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Source
    }
    $PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        return $PyLauncher.Source
    }
    throw "python.exe not found in PATH"
}

function Invoke-Native {
    & $args[0] @($args | Select-Object -Skip 1)
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $($args -join ' ')"
    }
}

$PythonExe = Resolve-Python $Python
$Version = & $PythonExe -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read project version from pyproject.toml"
}
$Installer = "dist\TelachatTk-Setup-$Version.exe"

if (-not $SkipTests) {
    & (Join-Path $Root "packaging\windows\test-windows.ps1") -Python $PythonExe
    if ($LASTEXITCODE -ne 0) {
        throw "Windows tests failed"
    }
}

if (Test-Path build) {
    Remove-Item -Recurse -Force build
}
if (Test-Path dist) {
    Remove-Item -Recurse -Force dist
}

Invoke-Native $PythonExe -m venv .venv-winbuild
Invoke-Native .\.venv-winbuild\Scripts\python.exe -m pip install --upgrade pip
Invoke-Native .\.venv-winbuild\Scripts\python.exe -m pip install pyinstaller

Invoke-Native .\.venv-winbuild\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    TelachatTk.spec

if (-not (Test-Path "dist\TelachatTk\TelachatTk.exe")) {
    throw "PyInstaller did not create dist\TelachatTk\TelachatTk.exe"
}

$WarningFile = "build\TelachatTk\warn-TelachatTk.txt"
if (Test-Path $WarningFile) {
    $Warnings = Get-Content -Raw -Path $WarningFile
    if ($Warnings -match "missing module named tkinter") {
        throw "PyInstaller did not bundle tkinter. Use a complete python.org Windows Python with Tcl/Tk installed."
    }
}

if (-not $SkipInstaller) {
    $Makensis = Get-Command makensis.exe -ErrorAction SilentlyContinue
    if ($Makensis) {
        Invoke-Native $Makensis.Source /DPRODUCT_VERSION=$Version packaging\windows\telachat-tk.nsi
        if (-not (Test-Path $Installer)) {
            throw "NSIS did not create $Installer"
        }
        Get-FileHash -Algorithm SHA256 $Installer |
            ForEach-Object { "$($_.Hash.ToLowerInvariant())  $(Split-Path -Leaf $_.Path)" } |
            Set-Content -Encoding ascii "$Installer.sha256"
    } else {
        Write-Warning "makensis.exe not found. Built exe only; install NSIS for the setup wizard."
    }
}
