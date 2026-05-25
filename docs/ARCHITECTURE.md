# Telachat architecture

## Components

- `telachat.config`
  - Reads `config.toml` using `tomllib`.
  - Validates provider profiles.
  - Loads prompt templates from `[prompt_templates]`.
  - Resolves API keys from literal values, `env:NAME`, or `file:/path`.
- `telachat.client`
  - Minimal OpenAI-compatible HTTP client.
  - Supports `/models`, non-streaming chat, and SSE streaming chat.
  - Reduces dependency risk by avoiding external SDKs.
- `telachat.store`
  - SQLite-backed session and message history.
  - Enables folders, session listing, search, loading, and Markdown export.
- `telachat.cli`
  - `init`, `profiles`, `ask`, `chat`, `sessions`, `export`, `export-folder`, `doctor`.
- `telachat.commands`
  - Shared slash-command catalog for CLI help and GUI autocomplete.
- `telachat.controller`
  - Shared application service for GUI frontends.
- `telachat.gtkgui`
  - Native GTK4/Libadwaita desktop GUI.
- `telachat.tkgui`
  - Native Tk/ttk desktop GUI and Windows packaging target.

## Data model

SQLite tables:

- `sessions`
  - `id`, `title`, `profile`, `system_prompt`, `created_at`, `updated_at`, `folder_id`, `pinned`
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

Additional built-in profiles:

- `openai`: OpenAI `/v1` Responses API using an env/envfile key, default model `gpt-5.4-mini`, with GPT-5.x model options.
- `huggingface`: Hugging Face Space `/v1`, model list centered on Qwen.
- `codex`: local `codex exec` bridge. This is not OpenAI-compatible HTTP.

GUI frontends expose profiles as providers and `Profile.models` as the second
model-selection step. They also expose folder filtering, sorting, text search,
chat pinning, and a slash-command path through the same composer used for
prompts. The GUI composers show slash-command suggestions while typing and Tab
completes the current command. The left chat/provider pane and the right system
pane are real resizable split panes rather than fixed sidebars.
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
telachat profiles
telachat templates
telachat folders
telachat doctor
telachat doctor --chat
telachat ask "Hallo"
telachat chat
telachat-gtk
telachat-tk
telachat sessions
telachat sessions --query TEXT
telachat sessions --folder NAME
telachat sessions --sort newest|oldest|title|title-desc|provider
telachat export <session-id>
telachat export-folder <folder-name-or-id>
telachat export-folder <folder-name-or-id> --single-file
```

GUI slash commands:

```text
/new | /neu
/rename TITLE
/delete
/pin | /unpin
/regen | /regenerate
/templates
/template NAME TEXT
/folder NAME | /ordner NAME
/folder-system TEXT
/rename-folder NAME
/delete-folder
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
- API client against a local fake OpenAI-compatible HTTP server.
- Non-streaming and streaming SSE responses.
- SQLite session/message roundtrip, Markdown export, and selective folder export.
- SQLite folder prompts, sorting and history-search behavior.
- CLI init/profile behavior with temporary XDG directories.
- Shared slash-command catalog behavior.
- Bytecode compilation and zipapp packaging.
- Optional live `doctor --chat` against the configured HF Space.
