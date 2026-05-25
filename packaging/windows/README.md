# Telachat Windows packaging

Telachat ships two native GUI frontends:

- `telachat-gtk`: GTK4/PyGObject. Best fit for Linux desktops.
- `telachat-tk`: Tk/ttk. Best Windows packaging target because Tk is included
  with normal Windows Python installations and PyInstaller handles it well.

## Important caveat

PyInstaller is not a cross-compiler. A real Windows `.exe` must be built on
Windows. Building it on Linux creates a Linux executable, not a Windows one.

Recommended Windows build path:

1. Install Python 3.12+ from python.org and enable "Add Python to PATH".
   Keep the Tcl/Tk and IDLE feature enabled; the Windows build treats missing
   or broken Tk as a packaging failure.
2. Install NSIS from https://nsis.sourceforge.io/
3. Open PowerShell in the Telachat project root.
4. Run the Windows test suite:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\test-windows.ps1
```

5. Build the Tk executable and installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\build-tk-windows.ps1
```

Expected outputs:

- `dist\TelachatTk\TelachatTk.exe`
- `dist\TelachatTk-Setup-<version>.exe`
- `dist\TelachatTk-Setup-<version>.exe.sha256`

The build script runs the Windows tests before packaging unless `-SkipTests` is
passed. Use that switch only in CI steps that already ran `test-windows.ps1`.

The script is intentionally Tk-only and excludes GTK modules. Run OpenAI-backed
profiles by setting `OPENAI_API_KEY` in the user environment before starting
Telachat.

## CI and releases

`.github/workflows/windows.yml` runs the Windows compile and unit-test suite on
pull requests, on pushes to `main`, and manually via `workflow_dispatch`.

For tags named `v*`, the workflow also builds the Tk installer, writes a SHA256
checksum, creates the GitHub release if needed, and uploads both files as release
assets. The release upload uses the built-in `GITHUB_TOKEN` and GitHub CLI on the
Windows runner.

## Why Tk for Windows

GTK on Windows works, but packaging PyGObject/GTK with typelibs, DLLs, themes and
GSettings schemas is much easier to break. Tk is plainer, but robust and normal
for small Python desktop utilities.
