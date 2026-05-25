# Telachat architecture

## Components

- `telachat.config`
  - Reads `config.toml` using `tomllib`.
  - Validates provider profiles.
  - Loads prompt templates from `[prompt_templates]`.
  - Resolves the GUI theme from config plus `TELACHAT_THEME`.
  - Resolves API keys from literal values, `env:NAME`, or `file:/path`.
  - Carries optional model-specific knobs such as `reasoning_effort`.
- `telachat.themes`
  - Central theme token definitions shared by GTK and Tk.
- `telachat.client`
  - Minimal OpenAI-compatible HTTP client.
  - Supports `/models`, non-streaming chat, and SSE streaming chat.
  - Sends Responses API `reasoning.effort` when configured.
  - Reduces dependency risk by avoiding external SDKs.
- `telachat.store`
  - SQLite-backed session and message history.
  - Enables folders, archive filters, session listing, search, loading, and
    Markdown export.
- `telachat.cli`
  - `init`, `profiles`, `models`, `config-check`, `theme`, `ask`, `chat`,
    `sessions`, `archive`, `unarchive`, `tags`, `export`, `export-folder`,
    `backup`, `restore`, `doctor`.
  - Interactive `chat` installs optional Readline completion for slash commands
    and context values when stdin is a TTY.
- `telachat.commands`
  - Shared slash-command catalog for CLI help and GUI autocomplete.
  - Theme names are completed from the central theme catalog for `/theme`.
  - Current-chat match formatting is shared by CLI and GUI `/find`.
- `telachat.controller`
  - Shared application service for GUI frontends.
- `telachat.gtkgui`
  - Native GTK4/Libadwaita desktop GUI.
- `telachat.tkgui`
  - Native Tk/ttk desktop GUI and Windows packaging target.

## Data model

SQLite tables:

- `sessions`
  - `id`, `title`, `profile`, `model`, `system_prompt`, `created_at`, `updated_at`, `folder_id`, `pinned`, `archived`
- `folders`
  - `id`, `name`, `created_at`, `updated_at`, `system_prompt`
- `messages`
  - `id`, `session_id`, `role`, `content`, `created_at`, `metadata`

Only chat content is stored. API keys are not copied into SQLite.
Empty sessions are pruned automatically when controllers start/close and by
CLI cleanup paths, but GUI list refreshes keep freshly-created empty chats
alive so "Neu" is not immediately undone.

## Configuration

Default path:

```text
~/.config/telachat/config.toml
```

Default profile:

```toml
[profiles.tki]
label = "TKI"
base_url = "https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1"
api_key = "envfile:/home/teladi/.config/telachat/qwen.env#TELACHAT_QWEN_API_KEY"
model = "Qwen/Qwen2.5-1.5B-Instruct"
```

GUI theme:

```toml
theme = "system"
```

Allowed themes are `system`, `light`, `dark`, `high-contrast`,
`solarized-light`, `solarized-dark`, `nord`, `dracula`, `gruvbox`, `ocean`,
`forest`, and `rose`. `TELACHAT_THEME` overrides the config for one process and
is useful for wrappers, test launches, and temporary desktop-specific starts.
When the saved theme is `system`, `TELACHAT_SYSTEM_THEME` can force the detected
palette for one process without changing the config. GTK maps `system`, `light`,
and `dark` to Libadwaita color-scheme preferences and then applies
Telachat-specific CSS tokens. Tk uses the same token palette directly.

Additional built-in profiles:

- `openai`: OpenAI `/v1` Responses API using an env/envfile key, default model `gpt-5.5`, `reasoning_effort = "high"`, with GPT-5.x model options.
- `huggingface`: Hugging Face Space `/v1`, model list centered on Qwen.
- `codex`: local `codex exec` bridge. This is not OpenAI-compatible HTTP.

GUI frontends expose profiles as providers and `Profile.models` as the second
model-selection step. They also expose folder filtering, sorting, text search,
chat pinning, and a slash-command path through the same composer used for
prompts. The live Check action merges `/models` results into the model selector
while keeping the current selection first. The GUI composers show slash-command
suggestions while typing and Tab completes the current command. The left
chat/provider pane and the right system pane are real resizable split panes
rather than fixed sidebars. Session archive state is a soft-hide flag: normal
lists show active chats, while explicit archive filters and direct session
loads can still reach archived chats.
The shared command path includes `/edit-last TEXT`, which updates the latest
user message and removes later messages before `/regen` creates a replacement
answer.
`/fork [TITLE]` and `telachat fork` copy a session into an independent history
branch while preserving provider, model, folder, system prompt, and messages.
Saved sessions store both provider and model. Loading a session restores those
selectors in GTK/Tk and `telachat chat --session` uses the saved model unless a
CLI override is given.
Folders can store a default system prompt. New chats created inside such a
folder inherit that prompt unless the user explicitly overrides the system
prompt.

For real credentials, prefer:

```toml
api_key = "env:PROVIDER_API_KEY"
```

## Operational commands

```sh
telachat init
telachat --version
telachat profiles
telachat profiles --json
telachat models
telachat models --live -p tki
telachat models --json
telachat config-check
telachat config-check --strict
telachat config-check --json
telachat theme
telachat theme dark
telachat chat
/theme dracula
telachat templates
telachat folders
telachat doctor
telachat doctor --chat
telachat doctor --json --chat
telachat ask "Hallo"
telachat chat
telachat-gtk
telachat-tk
telachat sessions
telachat sessions --query TEXT
telachat sessions --folder NAME
telachat sessions --tag TAG
telachat sessions --archived
telachat sessions --all
telachat sessions --sort newest|oldest|title|title-desc|provider
telachat sessions --json
telachat archive SESSION
telachat unarchive SESSION
telachat tags [SESSION]
telachat tags SESSION --add TAG --remove TAG
telachat fork <session-id-or-prefix>
telachat export <session-id>
telachat export <session-id> --json
telachat import-session FILE.json
telachat import-session FILE.json --dry-run
telachat export-folder <folder-name-or-id>
telachat export-folder <folder-name-or-id> --single-file
telachat export-folder <folder-name-or-id> --json
telachat export-folder <folder-name-or-id> --all --json
telachat import-folder FILE.json
telachat import-folder FILE.json --dry-run
telachat backup
telachat backup -o DIR
telachat backup -o FILE.zip
telachat restore [--dry-run] FILE.zip
telachat import-backup [--dry-run] FILE.zip
```

`models` lists configured model IDs for all profiles without network access by
default; `models --live [-p PROFILE]` queries `/models` only for one target
profile. `config-check` is intentionally offline: it validates the loaded TOML
shape, profile modes, model metadata, and whether configured secret sources
resolve to a value. It prints only redacted secret references. `doctor` remains
the fuller live network/API check.
The generated default config includes non-default local OpenAI-compatible
presets for LM Studio, Ollama, and Jan. They are normal profiles and may fail
`doctor` until the corresponding local server and model are running.
`config-check --profile NAME --strict` narrows strict secret validation to one
profile, which is useful when optional provider presets are intentionally not
configured.
`profiles`, `models`, `config-check`, `sessions`, `folders`, `export`,
`export-folder`, and `doctor` also support `--json` for agent/script
consumption. JSON output is redacted where it contains provider configuration;
folder system prompts are
included only when `folders --show-system --json` is requested or when exporting
that folder as a portable data bundle.

Sessions can also carry normalized tags in the `session_tags` table. Tags are
many-to-one labels independent of folders; session search can match tags,
`sessions --tag TAG` filters by one tag, and JSON/Markdown exports preserve
tags for additive imports, forks, and backup restores.

Sessions can be archived with `telachat archive` or `/archive`. Archived
sessions stay in SQLite and in backups, but `list_sessions()` defaults to
active sessions only. Callers use `archive="archived"` or `archive="all"` for
archive views and exports. Forks are created as active chats even when the
source is archived.

`backup` creates a ZIP bundle with a consistent SQLite copy, a redacted TOML
config reconstruction, and a JSON manifest. It intentionally does not include
raw envfiles, raw API keys, or the user's original config file. The redacted
TOML writer quotes keys when needed and redacts potentially secret header
values.

`restore` and its alias `import-backup` import only the `history.sqlite3` from
a Telachat backup ZIP. They append imported chats to the existing database,
generate new session/folder IDs as needed, reuse matching folder names, and do
not overwrite or replace current history. `--dry-run` reports the number of
folders, sessions, and messages that would be imported.

Interactive CLI chat supports Tab completion for slash commands, provider names,
model IDs, prompt templates, folders, session references, sort modes, and common
history limits.

GUI slash commands:

```text
/new | /neu
/rename TITLE
/delete
/pin | /unpin
/archive | /unarchive | /archives
/tag TAG [TAG...]
/untag TAG [TAG...]
/tags [SESSION]
/regen | /regenerate
/templates
/template NAME TEXT
/folder NAME | /ordner NAME
/folder-system TEXT
/rename-folder NAME
/delete-folder
/edit-last TEXT | /edit TEXT
/fork [TITLE]
/move NAME | /ablegen NAME
/unfile
/sort newest|oldest|title|title-desc|provider
/search TEXT
/provider NAME
/model NAME
/permissions
/left | /links
/system
```

## Test strategy

- Config parsing and secret redaction.
- Theme config parsing, env overrides, CLI setting, and GUI controller
  persistence.
- Configured and live model inventory output.
- GUI model-choice merge behavior after live model discovery.
- Offline config-check behavior and strict missing-secret handling.
- Redacted JSON output for profiles, models, config-check, sessions, folders, and
  doctor.
- API client against a local fake OpenAI-compatible HTTP server.
- Non-streaming and streaming SSE responses.
- SQLite session/message roundtrip, Markdown export, and selective folder export.
- SQLite folder prompts, sorting and history-search behavior.
- SQLite session tags, tag filtering/search, tag import/export, and tag counts.
- SQLite session archive filtering, archive import/export, and legacy migration.
- SQLite session model metadata, legacy migration, exports, and backend restore.
- Latest user-message editing and post-edit answer removal.
- Session forking with independent copied history.
- Backup ZIP content, secret redaction, and safe backup restore/import.
- CLI init/profile behavior with temporary XDG directories.
- Shared slash-command catalog behavior.
- Interactive CLI Readline completion and documented terminal command actions.
- Bytecode compilation and zipapp packaging.
- Optional live `doctor --chat` against the configured HF Space.
