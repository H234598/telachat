param(
    [string]$Python = "",
    [string]$Makensis = "",
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

function Resolve-Makensis {
    param([string]$Requested)
    if ($Requested) {
        $Command = Get-Command $Requested -ErrorAction SilentlyContinue
        if (-not $Command) {
            throw "Requested makensis.exe was not found: $Requested"
        }
        return $Command.Source
    }

    $Command = Get-Command makensis.exe -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Source
    }

    $CandidateRoots = @(
        (Join-Path $Root "..\..\tools\nsis"),
        (Join-Path $Root "..\..\tools\nsis-3.12"),
        (Join-Path $Root "..\..\tools\nsis-3.12-extracted")
    )
    foreach ($CandidateRoot in $CandidateRoots) {
        $Candidate = Join-Path $CandidateRoot "makensis.exe"
        if (Test-Path $Candidate) {
            return (Resolve-Path $Candidate).Path
        }
    }

    return $null
}

$PythonExe = Resolve-Python $Python
$VenvDir = Join-Path $Root ".venv-winbuild"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Version = & $PythonExe -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read project version from pyproject.toml"
}
$Installer = "dist\TelachatTk-Setup-$Version.exe"
$PortableZip = "dist\TelachatTk-$Version-windows-x64.zip"

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

$ResolvedPython = (Resolve-Path $PythonExe).Path
$ResolvedVenvPython = if (Test-Path $VenvPython) { (Resolve-Path $VenvPython).Path } else { $null }
if ($ResolvedVenvPython -and ($ResolvedPython -ieq $ResolvedVenvPython)) {
    Write-Host "Reusing existing .venv-winbuild because -Python points to its interpreter."
} else {
    Invoke-Native $PythonExe -m venv .venv-winbuild
}

Invoke-Native $VenvPython -m pip install --upgrade pip
Invoke-Native $VenvPython -m pip install pyinstaller

Invoke-Native .\.venv-winbuild\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --name TelachatTk `
    --windowed `
    --paths src `
    --exclude-module gi `
    --exclude-module telachat.gtkgui `
    packaging\launchers\telachat_tk_launcher.py

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

if (Test-Path $PortableZip) {
    Remove-Item -Force $PortableZip
}
Compress-Archive -Path "dist\TelachatTk" -DestinationPath $PortableZip -Force
Get-FileHash -Algorithm SHA256 $PortableZip |
    ForEach-Object { "$($_.Hash.ToLowerInvariant())  $(Split-Path -Leaf $_.Path)" } |
    Set-Content -Encoding ascii "$PortableZip.sha256"

if (-not $SkipInstaller) {
    $MakensisExe = Resolve-Makensis $Makensis
    if ($MakensisExe) {
        $DistDir = Join-Path $Root "dist"
        Invoke-Native $MakensisExe /DPRODUCT_VERSION=$Version "/DDIST_DIR=$DistDir" packaging\windows\telachat-tk.nsi
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
