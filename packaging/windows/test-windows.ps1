param(
    [string]$Python = "",
    [switch]$NoGuiImportSkip
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $Root

function Test-Python {
    param([string]$Candidate)
    if (-not $Candidate) {
        return $false
    }
    try {
        & $Candidate -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Resolve-Python {
    param([string]$Requested)
    if ($Requested) {
        $Command = Get-Command $Requested -ErrorAction SilentlyContinue
        if (-not $Command) {
            throw "Requested Python was not found: $Requested"
        }
        if (-not (Test-Python $Command.Source)) {
            throw "Requested Python is not usable: $Requested"
        }
        return $Command.Source
    }

    $Command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($Command -and (Test-Python $Command.Source)) {
        return $Command.Source
    }

    $PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($PyLauncher -and (Test-Python $PyLauncher.Source)) {
        return $PyLauncher.Source
    }

    $VenvPython = Join-Path $Root ".venv-winbuild\Scripts\python.exe"
    if ((Test-Path $VenvPython) -and (Test-Python $VenvPython)) {
        return (Resolve-Path $VenvPython).Path
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
$VersionText = & $PythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to query Python version from $PythonExe"
}
$Version = [version]$VersionText
if ($Version -lt [version]"3.11.0") {
    throw "Python 3.11 or newer is required; found $VersionText"
}

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $Root "src"
    Invoke-Native $PythonExe -m compileall -q src tests packaging
    Invoke-Native $PythonExe -m unittest discover -s tests -v
    Invoke-Native $PythonExe -c "import tkinter; tkinter.Tcl().eval('info patchlevel'); import telachat.tkgui; import runpy; runpy.run_path('packaging/windows/../launchers/telachat_tk_launcher.py')"
    if ($NoGuiImportSkip) {
        Invoke-Native $PythonExe -c "import telachat.gtkgui"
    }
} finally {
    $env:PYTHONPATH = $OldPythonPath
}
