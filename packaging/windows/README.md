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
2. Install NSIS from https://nsis.sourceforge.io/
3. Open PowerShell in the Telachat project root.
4. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\build-tk-windows.ps1
```

Expected outputs:

- `dist\TelachatTk\TelachatTk.exe`
- `dist\TelachatTk-Setup.exe`

The script is intentionally Tk-only and excludes GTK modules. Run OpenAI-backed
profiles by setting `OPENAI_API_KEY` in the user environment before starting
Telachat.

## Why Tk for Windows

GTK on Windows works, but packaging PyGObject/GTK with typelibs, DLLs, themes and
GSettings schemas is much easier to break. Tk is plainer, but robust and normal
for small Python desktop utilities.
