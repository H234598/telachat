# Telachat testing

## Local deterministic tests

```sh
cd /home/teladi/telachat
PYTHONPATH=src python3 -m telachat config-check
PYTHONPATH=src python3 -m telachat config-check --json
PYTHONPATH=src python3 -m telachat theme
PYTHONPATH=src python3 -m telachat backup -o /tmp/telachat-backups
PYTHONPATH=src python3 -m telachat restore --dry-run /tmp/telachat-backups/FILE.zip
make compile
make test3
make zipapp
man ./docs/man/telachat.1
```

The fake OpenAI-compatible HTTP server in `tests/test_client.py` binds to
`127.0.0.1`. If a sandbox blocks local sockets, run the tests outside that
sandbox. No external API key is needed.

## Live endpoint tests

```sh
telachat doctor
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
telachat templates
telachat folders --show-system
telachat folders --json --show-system
telachat export SESSION_ID --json
telachat export-folder Arbeit -o /tmp/telachat-export
telachat sessions --json
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

Live tests use the active profile from `config.toml`, currently `tki`.
`doctor --chat` and `ask` send prompts to the configured API.
The GUI commands require a graphical desktop session.
OpenAI live tests require `OPENAI_API_KEY`.
On this host they can also use
`envfile:/home/teladi/.config/telachat/openai.env#OPENAI_API_KEY`
from `~/.config/telachat/config.toml`.

The deterministic suite also covers folder creation, duplicate folder handling,
folder-level system prompts, session moves, folder filters, pinned-chat
ordering, answer regeneration, prompt templates, title sorting, content search
across saved messages, CLI session filtering/sorting, and selective folder
exports. It also covers per-session model persistence, legacy model-column
migration, OpenAI Responses `reasoning.effort`, interactive CLI completion
candidates, offline config checks with secret redaction, and documented
terminal slash-command actions, including `/theme` and `/find`. Theme tests
cover config persistence, env overrides, system-palette detection, CLI setting,
and controller persistence.
Backup tests inspect the ZIP bundle and verify that envfile secret values and
secret-like header values are not included. GUI smoke tests also cover
construction of the slash-command autocomplete widgets.
CLI JSON tests cover profiles, config-check, sessions, folders, and doctor
while checking that secret values remain redacted.
Restore tests verify dry-run counts, duplicate-safe imports, session ID
rewrites, and folder-name reuse.
Edit-last tests verify that the latest user message can be replaced and that
later assistant answers are removed before regeneration.
Fork tests verify copied provider/model/folder/system metadata, copied message
history, independent edits after forking, top-level CLI use, and `/fork` in
interactive chat.

## Expected default live configuration

```text
Profile: tki / TKI
API: https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1
Model: Qwen/Qwen2.5-1.5B-Instruct
Key: local envfile `/home/teladi/.config/telachat/qwen.env`
```

The HF Space rejects the old placeholder key. The active Space secret is
`TELACHAT_API_KEYS`; the local client key is `Telachat_API_Teladi`.
