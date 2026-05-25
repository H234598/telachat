# Versioning

Telachat folgt Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

## Regeln

- Neues kompatibles Feature: `MINOR` erhoehen.
- Bugfix ohne neue Oberflaeche: `PATCH` erhoehen.
- Inkompatible Aenderung: `MAJOR` erhoehen.

## Release-Checkliste

Vor einem Release:

```sh
make compile
make test3
make zipapp
make install
telachat --help
python3 dist/telachat.pyz --help
telachat doctor --chat
git diff --check
```

Wenn die Tk-Binary gebaut wird:

```sh
.venv-build/bin/pyinstaller --noconfirm --clean --name TelachatTk --windowed --paths src --exclude-module gi --exclude-module telachat.gtkgui packaging/launchers/telachat_tk_launcher.py
dist/TelachatTk/TelachatTk --help
```

Danach:

```sh
git commit
git tag vX.Y.Z
git push origin main --follow-tags
gh release create vX.Y.Z dist/telachat.pyz
```
