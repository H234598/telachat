# Telachat testing

## Local deterministic tests

```sh
cd /home/teladi/telachat
PYTHONPATH=src python3 -m telachat --version
PYTHONPATH=src python3 -m telachat config-check
PYTHONPATH=src python3 -m telachat config-check --json
PYTHONPATH=src python3 -m telachat models --json
PYTHONPATH=src python3 -m telachat theme
PYTHONPATH=src python3 -m telachat stats --json
PYTHONPATH=src python3 -m telachat backup -o /tmp/telachat-backups
PYTHONPATH=src python3 -m telachat restore --dry-run /tmp/telachat-backups/FILE.zip
make check
make compile
make test3
make zipapp
make linux-installer
packaging/linux/install-telachat.sh --prefix /tmp/telachat-prefix --desktop-dir /tmp/telachat-desktop --zipapp dist/telachat.pyz
packaging/linux/package-cadence.py v0.54.2
man ./docs/man/telachat.1
```

The fake OpenAI-compatible HTTP server in `tests/test_client.py` binds to
`127.0.0.1`. If a sandbox blocks local sockets, run the tests outside that
sandbox. No external API key is needed.
`make check` runs bytecode compilation, the full offline suite, and
`git diff --check`; `make test3` repeats the suite three times to catch state
leaks.

## Live endpoint tests

```sh
telachat doctor
telachat --version
telachat models
telachat models --live -p huggingface --json
telachat config-check
telachat config-check --strict
telachat config-check --json
telachat theme
TELACHAT_THEME=dark telachat config-check
TELACHAT_SYSTEM_THEME=solarized-dark telachat theme
telachat backup -o /tmp/telachat-backups
telachat restore --dry-run /tmp/telachat-backups/FILE.zip
telachat doctor --chat
telachat doctor --json --chat
telachat config-check --profile huggingface --strict
telachat skill-watchdog --json
python3 dist/telachat.pyz config-check --profile jan --json --strict
telachat templates
telachat folders --show-system
telachat folders --json --show-system
telachat folders --set-backend Arbeit huggingface TKI
telachat folders --clear-backend Arbeit
telachat export SESSION_ID --json
telachat import-session session.json --json
telachat export-folder Arbeit --json
telachat export-folder Arbeit --all --json
telachat import-folder folder.json --json
telachat import-folder folder.json --dry-run --json
telachat export-folder Arbeit -o /tmp/telachat-export
telachat sessions --json
telachat stats --json
telachat sessions --tag projekt
telachat sessions --archived
telachat sessions --all
telachat archive SESSION_ID
telachat unarchive SESSION_ID
telachat tags SESSION_ID --add projekt
telachat tags SESSION_ID --remove projekt
telachat tags --json
telachat chat
/find TEXT
/theme dracula
telachat ask --template summarize "Was hat sich geaendert?"
telachat ask "Was ist 812 - 512?"
telachat ask -p openai --reasoning-effort high "Antworte nur mit: OK"
telachat ask -p codex "Antworte nur mit: CODEX-OK"
telachat-gtk
telachat-tk
```

Live tests use the active profile from `config.toml`, currently `huggingface`.
`doctor --chat` and `ask` send prompts to the configured API.
The GUI commands require a graphical desktop session.
OpenAI live tests require `OPENAI_API_KEY`.
On this host they can also use
`envfile:/home/teladi/.config/telachat/openai.env#OPENAI_API_KEY`
from `~/.config/telachat/config.toml`.

The deterministic suite also covers folder creation, duplicate folder handling,
folder-level system prompts, folder-level backend defaults, session moves, folder filters, pinned-chat
ordering, answer regeneration, prompt templates, title sorting, content search
across saved messages, CLI session filtering/sorting, and selective folder
exports. It also covers per-session tags, tag filtering/search, tag import/export,
tag counts, session archiving, archive filtering/search, archive import/export,
legacy archive-column migration, per-session model persistence, legacy model-column
migration, OpenAI Responses `reasoning.effort`, interactive CLI completion
candidates, offline config checks with secret redaction, and documented
terminal slash-command actions, including `/theme` and `/find`. Theme tests
cover config persistence, env overrides, system-palette detection, CLI setting,
and controller persistence. Config tests validate profile booleans, API modes,
and the `validate_profile_headers` option. `/stats` and `/context` tests cover
shared content-free formatters plus
terminal, Tk, and GTK prompt paths. `/doctor` prompt tests cover terminal
`/models` output, local secret-source errors, and GUI dispatch to the existing
Check action.
Command catalog tests assert that every declared alias resolves to its
canonical command. GUI tests also cover shared alias normalization for `/q` and
`/quit` closing Tk and GTK windows, plus `/regenerate` dispatching through the
canonical command catalog. Tk and GTK cancellation regressions verify that late
worker results from an `Abbrechen` operation are ignored instead of overwriting
the active view. They also verify prompt restoration for cancelled Send
operations when the composer is still empty.
Backup tests inspect the ZIP bundle and verify that envfile secret values and
secret-like header values are not included. GUI smoke and regression tests also
cover construction of the slash-command autocomplete widgets, visible
archive/tag-filter propagation, Tk tag-filter selection preservation, and
model-choice merge behavior after live model discovery. Controller and client
tests verify that generation overrides reach the API profile and that Responses
requests include temperature/top-p/max-output parameters. Controller and GUI
tests also cover elapsed-time propagation for successful responses.
Skill-watchdog tests cover compacting oversized Skill descriptions, preserving
the body, backup creation, CLI JSON output, and unchanged/skipped files.
Store and CLI tests cover content-free local statistics for sessions, messages,
folders, tags, profiles, and models, plus content-free context estimates for
single sessions.
CLI JSON tests cover profiles, models, config-check, sessions, stats, context,
templates, folders, and doctor while checking that secret values remain
redacted.
Restore tests verify dry-run counts, duplicate-safe imports, session ID
rewrites, and folder-name reuse.
Edit-last tests verify that the latest user message can be replaced and that
later assistant answers are removed before regeneration.
Fork tests verify copied provider/model/folder/system metadata, copied message
history, independent edits after forking, top-level CLI use, and `/fork` in
interactive chat.
Tag tests verify normalized tags, CLI `tags`, `sessions --tag`, JSON/Markdown
exports, additive imports, backup-history restores, completion, and `/tag`
slash-command behavior.
Archive tests verify `archive`/`unarchive`, `sessions --archived`, hidden-by-default
lists, JSON/Markdown preservation, additive imports, backup-history restore,
completion, and `/archive` slash-command behavior.

## Expected default live configuration

```text
Profile: huggingface / TKI
API: https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1
Model: Qwen/Qwen2.5-1.5B-Instruct
Key: local envfile `/home/teladi/.config/telachat/qwen.env`
```

The HF Space rejects the old placeholder key. The active Space secret list is
`TELACHAT_API_KEYS`; the local client key is loaded from the envfile above and
must not be committed.
