$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $Root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python.exe not found in PATH"
}

python -m venv .venv-winbuild
& .\.venv-winbuild\Scripts\python.exe -m pip install --upgrade pip
& .\.venv-winbuild\Scripts\python.exe -m pip install pyinstaller

& .\.venv-winbuild\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --name TelachatTk `
    --windowed `
    --paths src `
    --exclude-module gi `
    --exclude-module telachat.gtkgui `
    packaging\launchers\telachat_tk_launcher.py

$Makensis = Get-Command makensis.exe -ErrorAction SilentlyContinue
if ($Makensis) {
    & $Makensis.Source packaging\windows\telachat-tk.nsi
} else {
    Write-Warning "makensis.exe not found. Built exe only; install NSIS for the setup wizard."
}
