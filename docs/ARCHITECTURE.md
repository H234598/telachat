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
  - Sends Responses API `reasoning.effort`, temperature, top-p, and
    max-output settings when configured.
  - Reduces dependency risk by avoiding external SDKs.
- `telachat.store`
  - SQLite-backed session and message history.
  - Enables folders, archive filters, session listing, search, loading, and
    Markdown export.
  - Provides content-free aggregate statistics for local inventory checks.
- `telachat.cli`
  - `init`, `profiles`, `models`, `config-check`, `theme`, `ask`, `chat`,
    `sessions`, `stats`, `archive`, `unarchive`, `tags`, `export`,
    `export-folder`, `backup`, `restore`, `doctor`, `skill-watchdog`.
  - Interactive `chat` installs optional Readline completion for slash commands
    and context values when stdin is a TTY.
- `telachat.skill_watchdog`
  - Scans local Codex skill roots, compacts oversized frontmatter
    `description` fields, preserves full skill bodies, and writes sidecar
    backups before changing a Skill file.
- `telachat.commands`
  - Shared slash-command catalog for CLI help and GUI autocomplete.
  - Theme names are completed from the central theme catalog for `/theme`.
  - Current-chat match formatting is shared by CLI and GUI `/find`.
- `telachat.templates`
  - Shared prompt-template renderer for CLI and GUI/controller paths.
  - Expands built-in variables such as `{input}`, `{date}`, `{time}`, and
    `{datetime}`.
  - Reports custom variables so CLI and GUI paths can request values without
    overwriting built-in renderer variables.
- `telachat.controller`
  - Shared application service for GUI frontends.
  - Applies transient GUI generation overrides without rewriting config or
    session metadata.
  - Measures request elapsed time for successful send/regenerate payloads.
- `telachat.gtkgui`
  - Native GTK4/Libadwaita desktop GUI.
  - Tracks in-flight worker operation IDs so cancelled/stale results cannot
    overwrite the current view.
- `telachat.tkgui`
  - Native Tk/ttk desktop GUI and Windows packaging target.
  - Uses the same operation-ID cancellation guard as the GTK frontend.

## Data model

SQLite tables:

- `sessions`
  - `id`, `title`, `profile`, `model`, `system_prompt`, `created_at`, `updated_at`, `folder_id`, `pinned`, `archived`
- `folders`
  - `id`, `name`, `created_at`, `updated_at`, `system_prompt`, `default_profile`, `default_model`
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
[profiles.huggingface]
label = "HuggingFace"
base_url = "https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1"
api_key = "envfile:/home/teladi/.config/telachat/qwen.env#TELACHAT_QWEN_API_KEY"
model = "TKI"
```

GUI theme:

```toml
theme = "system"
```

Allowed themes are `system`, `light`, `dark`, `high-contrast`,
`solarized-light`, `solarized-dark`, `nord`, `dracula`, `gruvbox`, `ocean`,
`forest`, `rose`, `graphite-glass`, `liquid-chrome`, `black-ice`, and
`brushed-steel`. `TELACHAT_THEME` overrides the config for one process and
is useful for wrappers, test launches, and temporary desktop-specific starts.
When the saved theme is `system`, `TELACHAT_SYSTEM_THEME` can force the detected
palette for one process without changing the config. GTK maps `system`, `light`,
and `dark` to Libadwaita color-scheme preferences and then applies
Telachat-specific CSS tokens. Tk uses the same token palette directly.

Additional built-in profiles:

- `huggingface`: Hugging Face Space `/v1`, default profile and model label `TKI`, mapped internally to the Qwen API model. Legacy `tki` profile references resolve to this profile.
- `openai`: OpenAI `/v1` Responses API using an env/envfile key, default model `gpt-5.5`, `reasoning_effort = "high"`, with GPT-5.x model options and sampling parameters disabled by default.
- `codex`: local `codex exec` bridge. This is not OpenAI-compatible HTTP.

GUI frontends expose profiles as providers and `Profile.models` as the second
model-selection step. They also expose folder filtering, sorting, text search,
chat pinning, and a slash-command path through the same composer used for
prompts. The live Check action merges `/models` results into the model selector
while keeping the current selection first. The GUI composers show slash-command
suggestions while typing and Tab completes the current command or context values
such as providers, models, templates, themes, folders, tags, sort modes, and
history sizes. The left
chat/provider pane and the right system pane are real resizable split panes
rather than fixed sidebars. Session archive state is a soft-hide flag: normal
lists show active chats, while explicit archive filters and direct session
loads can still reach archived chats. GTK and Tk expose that archive filter in
the sidebar as active, archived, or all chats. When providers return token
usage, GTK and Tk include input/output/total token counts in the response status.
The shared command path includes `/edit-last TEXT`, which updates the latest
user message and removes later messages before `/regen` creates a replacement
answer.
Prompt-template custom-variable dialogs remember the latest values per template
for the current Tk or GTK GUI session, so repeated use of the same template is
prefilled without writing those transient values into config or history.
Tk and GTK start the Codex Skill watchdog once at launch only when
`skill_watchdog_enabled = true`; it then repeats hourly in a daemon thread.
The low-level background start is additionally gated by
`TELACHAT_ENABLE_SKILL_WATCHDOG=1`, and
`TELACHAT_DISABLE_SKILL_WATCHDOG=1` disables it even then. This keeps oversized
plugin descriptions below the local Codex loader limit without deleting the
detailed Skill body.
`/fork [TITLE]` and `telachat fork` copy a session into an independent history
branch while preserving provider, model, folder, system prompt, and messages.
Saved sessions store both provider and model. Loading a session restores those
selectors in GTK/Tk and `telachat chat --session` uses the saved model unless a
CLI override is given.
Linux installation is zipapp-first: the generic installer and RPM both place a
single `telachat.pyz` under the install prefix plus tiny launcher scripts for
CLI, Tk, GTK and GUI-auto mode. This keeps the app portable across distros while
still using Freedesktop desktop entries, hicolor icons and manpages where those
standards exist.
Folders can store a default system prompt, an optional plain-text context note,
and an optional default backend (`default_profile`, `default_model`). New chats
created inside such a folder inherit that prompt/backend unless the caller
explicitly overrides the prompt, profile, or model. When a folder context note
exists, Telachat appends it below the folder/default system prompt for the new
chat. GTK and Tk also apply folder backend defaults when selecting a folder for
a new chat.

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
telachat models --live -p huggingface
telachat models --json
telachat config-check
telachat config-check --strict
telachat config-check --json
telachat config-check --show-redacted
telachat theme
telachat theme dark
telachat chat
/theme dracula
telachat templates
telachat templates --json
telachat folders
telachat folders --create FOLDER --context "Project facts"
telachat folders --set-context FOLDER "Updated project facts"
telachat folders --show-context
telachat folders --set-backend FOLDER PROFILE [MODEL]
telachat folders --clear-backend FOLDER
telachat doctor
telachat doctor --chat
telachat doctor --json --chat
telachat ask "Hallo"
telachat ask --json "Hallo"
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
telachat stats
telachat stats --json
telachat context SESSION
telachat context SESSION --json
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
telachat export-folder <folder-name-or-id> --bundle
telachat export-folder <folder-name-or-id> --all --json
telachat import-folder FILE.json
telachat import-folder FILE.zip
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
`config-check --show-redacted` reuses the backup redaction writer to print a
TOML-shaped support view without raw API keys or auth headers.
Configured extra headers are validated by default with
`validate_profile_headers = true`. The option is global because header parsing
happens while loading TOML, before provider-specific runtime state exists. The
switch relaxes only strict standard-name validation; control characters and
non-portable or parser-unsafe names remain rejected. Tk and GTK expose the same
switch in the right settings pane.
`profiles`, `models`, `config-check`, `sessions`, `stats`, `context`,
`templates`, `folders`, `ask`, `export`, `export-folder`, and `doctor` also
support `--json` for agent/script consumption. JSON output is redacted where it
contains provider configuration;
folder system prompts and folder context notes are included only when
`folders --show-system --show-context --json` is requested or when exporting
that folder as a portable data bundle. `export-folder --bundle` stores the same
`telachat.folder.v1` payload as `folder.json` in a ZIP plus a small manifest;
it does not include `config.toml`, provider secrets, or environment files.
Folder context notes and backend defaults are not secrets and are included in
folder JSON whenever they are configured.

`stats` is read-only and does not include message content. It counts sessions,
messages by role, folders, tag assignments, profile usage, model usage, and
stored provider token usage so a local database can be inspected quickly from
scripts.

`context` is also read-only and content-free. It estimates one session's next
request size from the system prompt, the configured history-message window, and
message lengths, reporting character counts and a coarse token estimate.

`templates --json` returns a compact inventory of configured prompt templates:
name, first-line preview, size metadata, whether `{input}` is used, and the
supported and custom variables referenced by the template.
`templates --show NAME` prints the full prompt-template preview with name,
character count, variable metadata, and body text; with `--json` it emits the
same single-template record shape used by scripts.
`ask --template NAME --template-var KEY=VALUE` fills custom variables while
leaving built-in variables such as `{date}` and `{input}` controlled by the
renderer.
Tk and GTK use the same metadata to ask for custom variable values in native
dialogs before inserting a template into the composer.
`templates --set`, `--rename`, and `--delete` update only the
`[prompt_templates]` table and then reload the same config parser used by chat
and GUI flows.

Sessions can also carry normalized tags in the `session_tags` table. Tags are
many-to-one labels independent of folders; session search can match tags,
`sessions --tag TAG` and the GUI sidebar tag filter filter by one tag, and
JSON/Markdown exports preserve tags for additive imports, forks, and backup
restores.

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
/stats
/context
/doctor
/regen | /regenerate
/templates
/template NAME TEXT
/folder NAME | /ordner NAME
/folder-prompt TEXT
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
/exit | /quit | /q
```

`/folder-system TEXT` bleibt als kompatibler Alias fuer `/folder-prompt TEXT`
erhalten.

GUI request cancellation:

- Send, regenerate, and Check each allocate an operation ID before starting a
  worker thread.
- `Abbrechen` marks the active ID as cancelled, re-enables the UI, and leaves
  any already-started provider call to finish in the background.
- Cancelled send operations restore their submitted prompt if the composer is
  still empty.
- Late success/error results are accepted only when their operation ID is still
  active; cancelled or stale results are ignored.

## Test strategy

- Config parsing and secret redaction.
- Theme config parsing, env overrides, CLI setting, and GUI controller
  persistence.
- Configured and live model inventory output.
- GUI model-choice merge behavior after live model discovery.
- Token usage extraction from Chat Completions and Responses payloads, plus GUI
  response-status formatting when usage is available.
- Offline config-check behavior and strict missing-secret handling.
- Redacted JSON output for profiles, models, config-check, sessions, stats,
  folders, and doctor.
- API client against a local fake OpenAI-compatible HTTP server.
- Non-streaming and streaming SSE responses.
- SQLite session/message roundtrip, Markdown export, and selective folder export.
- SQLite folder prompts, folder backend defaults, sorting and history-search behavior.
- SQLite session tags, tag filtering/search, tag import/export, and tag counts.
- SQLite session archive filtering, archive import/export, and legacy migration.
- SQLite local statistics for content-free history inventory.
- GUI archive filter wiring in Tk and GTK.
- GUI cancelled-request guards and send-prompt restoration in Tk and GTK.
- SQLite session model metadata, legacy migration, exports, and backend restore.
- Latest user-message editing and post-edit answer removal.
- Session forking with independent copied history.
- Backup ZIP content, secret redaction, and safe backup restore/import.
- CLI init/profile behavior with temporary XDG directories.
- Shared slash-command catalog behavior.
- Interactive CLI Readline completion and documented terminal command actions.
- Bytecode compilation and zipapp packaging.
- Optional live `doctor --chat` against the configured HF Space.
