# Repository Guidelines

## Project Structure & Module Organization

Telachat is a Python 3.11+ application in `src/telachat/`. Core modules include
`cli.py`, `client.py`, `config.py`, `controller.py`, `store.py`, and `commands.py`.
Desktop frontends live in `tkgui.py` and `gtkgui.py`. Tests are in `tests/` and
use `test_*.py` naming. Icons and bundled GUI assets are under
`src/telachat/assets/`. Packaging lives in `packaging/`, `snap/`, `bin/`, and
`docs/man/`; project documentation is in `docs/` and `docs/wiki/`.

## Build, Test, and Development Commands

- `make check`: compile sources, run the full unittest suite, then run
  `git diff --check`.
- `make test`: run all tests with `PYTHONPATH=src`.
- `make test3`: run the suite three times to catch state leaks.
- `make zipapp`: build `dist/telachat.pyz`.
- `make install`: install local launchers and man pages under `$(PREFIX)`.
- `make linux-installer` / `make linux-rpm`: build Linux release artifacts.
- `PYTHONPATH=src python3 -m telachat doctor`: run local configuration checks.

## Coding Style & Naming Conventions

Use standard Python style with 4-space indentation, type hints where helpful,
and focused functions that match existing module boundaries. Keep user-facing
strings consistent with the current German UI wording. Prefer structured config
and store APIs over ad hoc parsing. Shell scripts in `packaging/linux/` should
stay POSIX-`sh` compatible and ShellCheck-clean.

## Testing Guidelines

Tests use the Python standard `unittest` framework. Add focused regression tests
near the changed surface, for example `tests/test_gui_imports.py` for GUI
behavior or `tests/test_client.py` for provider requests. Run `make check`
before committing. For packaging changes, also run the relevant artifact target,
such as `make linux-installer` or `make linux-rpm`.

## Commit & Pull Request Guidelines

Keep commits small and outcome-focused. Existing history uses concise messages
such as `Release 0.55.0 copyable GUI errors` and `Add Linux shell lint CI`.
Follow Semantic Versioning for feature and fix releases. Pull requests should
describe the user-visible change, list verification commands, link related
issues, and include screenshots for GUI changes. Never include API keys, raw
tokens, private config files, or generated secrets in commits or PR text.
