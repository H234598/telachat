# Changelog

## 0.21.0 - 2026-05-25

- Add `telachat import-session FILE.json` for additive single-session imports.
- Support `--title`, `--folder`, and `--json` for imported JSON sessions.
- Validate import format and message roles before writing imported data.

## 0.20.0 - 2026-05-25

- Add `telachat export SESSION --json` for machine-readable single-session
  exports.
- Include session metadata, system prompt, and ordered messages in JSON export.
- Support `-o/--output` for JSON exports as well as Markdown.

## 0.19.0 - 2026-05-25

- Add `/find TEXT` to search within the currently loaded conversation in
  interactive CLI, GTK, and Tk.
- Share compact match formatting for CLI and GUI result dialogs.
- Add regression coverage for current-chat matching and CLI slash-find output.

## 0.18.0 - 2026-05-25

- Add `/theme [NAME]` to interactive CLI, GTK, and Tk.
- Add slash-command completion for theme names.
- Add regression coverage for the prompt-level theme command and help text.
- Harden system-theme tests for explicit override precedence.

## 0.17.0 - 2026-05-25

- Expand the built-in GUI theme catalog with Solarized, Nord, Dracula, Gruvbox,
  Ocean, Forest, and Rose palettes.
- Add system-theme detection from common desktop and terminal environment
  hints while keeping `theme = "system"` persistent.
- Add `TELACHAT_SYSTEM_THEME` for one-process system-palette overrides without
  changing the saved theme.
- Add regression coverage for expanded theme aliases, system detection, and
  doctor JSON without `--chat`.

## 0.16.0 - 2026-05-25

- Add redacted JSON output for `telachat doctor --json`.
- Include `/models` results and optional `--chat` check metadata in doctor JSON.
- Add regression coverage that doctor JSON does not leak resolved env secrets.
- Keep text `doctor` diagnostics visible when later live checks fail.

## 0.15.0 - 2026-05-25

- Add redacted JSON output for `telachat profiles --json`.
- Add redacted JSON output for `telachat config-check --json`.
- Add JSON output for `telachat sessions --json` and `telachat folders --json`.
- Keep folder system prompts out of folder JSON unless `--show-system` is used.
- Add CLI regression coverage for JSON output and secret redaction.
- Add store regression coverage for SQLite foreign-key protection.

## 0.14.0 - 2026-05-25

- Add `telachat fork SESSION [--title TITLE]` to copy a saved chat into a new
  independent session.
- Add `/fork [TITLE]` to interactive CLI, GTK, and Tk so prompt variants can be
  tried without changing the original conversation.
- Preserve source provider, model, folder, system prompt, and messages while
  leaving the new fork unpinned.
- Add Store, Controller, command catalog, top-level CLI, and slash-command
  regression tests.

## 0.13.0 - 2026-05-25

- Add `/edit-last TEXT` with `/edit` alias for interactive CLI, GTK, and Tk.
- Replace the latest user message in a session and remove later messages so
  `/regen` can create a fresh answer from the corrected prompt.
- Add Store, Controller, command catalog, and interactive CLI regression tests.

## 0.12.1 - 2026-05-25

- Fix `telachat theme NAME` so it only updates top-level config keys and never
  rewrites a profile-local `theme` field.
- Add regression coverage for inserting a top-level theme before profile tables.
- Add release-marker consistency coverage for README, changelog, wiki, manpages,
  and package version.

## 0.12.0 - 2026-05-25

- Add central theme definitions for `system`, `light`, `dark`, and
  `high-contrast`.
- Add `theme = "..."` config support with `TELACHAT_THEME` as an environment
  override.
- Add `telachat theme [NAME]` to inspect and persist the configured GUI theme.
- Apply the shared theme palette in both GTK and Tk frontends.
- Include the active theme in backup manifests and redacted config backups.
- Add deterministic tests for theme parsing, env overrides, CLI setting, and
  controller persistence.

## 0.11.0 - 2026-05-25

- Add `telachat restore` and `telachat import-backup` for safe backup imports.
- Import backup history into the existing SQLite database without overwriting
  existing sessions.
- Preserve folder relationships, reuse matching folder names, and create new
  session IDs for imported chats.
- Add `--dry-run` so backup contents can be counted before import.
- Add deterministic CLI and store coverage for restore/import behavior.

## 0.10.0 - 2026-05-25

- Add `telachat backup` for local, secret-aware backup bundles.
- Create a consistent SQLite history backup via SQLite's backup API.
- Include `config.redacted.toml` and `manifest.json` without raw secret values.
- Keep redacted TOML parseable for dashed profile/template/header names and
  redact potentially secret header values.
- Support `telachat backup -o DIR` and `telachat backup -o FILE.zip`.
- Add deterministic ZIP inspection coverage for backup contents and redaction.

## 0.9.0 - 2026-05-25

- Add `telachat config-check` with alias `telachat config`.
- Validate local configuration, profile modes, model lists, and redacted secret
  source status without sending an API request.
- Add `--strict` so scripts can fail when a configured non-Codex provider has a
  missing secret source.
- Add deterministic coverage that config checks do not leak envfile secret
  values.

## 0.8.0 - 2026-05-25

- Persist the selected model on each saved chat session.
- Add a SQLite migration for legacy sessions without model metadata.
- Restore provider and model selectors in GTK/Tk when loading a saved chat.
- Use saved session models for CLI `chat --session` unless explicitly
  overridden.
- Include session model metadata in session lists, search, and Markdown exports.

## 0.7.0 - 2026-05-25

- Add Readline Tab completion for interactive `telachat chat`.
- Complete slash commands, profiles, models, templates, folders, session refs,
  sort modes, and common history limits in the CLI prompt.
- Align interactive CLI slash-command handling with the documented command
  catalog for rename/delete/folder/move/search/sort/provider/model actions.
- Add configurable `reasoning_effort` for provider profiles and CLI overrides.
- Change the default OpenAI profile to `gpt-5.5` with `reasoning_effort = "high"`.

## 0.6.0 - 2026-05-25

- Add a shared slash-command catalog for CLI, GTK, and Tk.
- Add prompt autocomplete for slash commands in both GUIs.
- Add `/permissions` to show provider and redacted secret sources.
- Add `telachat(1)`, `telachat-tk(1)`, and `telachat-gtk(1)` manpages.
- Install manpages through `make install`.
- Rename the default TKI/Hugging Face model from the Bavarder-compatible
  `gpt-4` alias to the real `Qwen/Qwen2.5-1.5B-Instruct` model name.

## 0.5.0 - 2026-05-25

- Add selective folder export with `telachat export-folder FOLDER`.
- Write directory exports with `index.md` plus one Markdown file per session.
- Add `--single-file` folder exports for one combined Markdown artifact.
- Add deterministic CLI coverage for folder directory and single-file exports.

## 0.4.0 - 2026-05-25

- Add folder-level default system prompts so folders can behave like lightweight
  project contexts.
- Add `telachat folders` with create/list/show-system/set-system operations.
- Add `/folder-system TEXT` to CLI, GTK, and Tk command paths.
- Add an `Ordner-Prompt` GUI action that saves the current system prompt to the
  selected folder.
- Add SQLite migration coverage for the new folder prompt column.
- Remove the redundant `chatgpt` provider; use `openai` for OpenAI Responses API
  models, including GPT-5.x options.

## 0.3.0 - 2026-05-25

- Add configurable prompt templates through `[prompt_templates]` in
  `config.toml`.
- Add `telachat templates` and `telachat ask --template NAME ...`.
- Add `/templates` and `/template NAME TEXT` to interactive CLI chat and both
  GUI prompt command paths.
- Add GTK and Tk template selectors that insert a configured template into the
  composer.
- Add tests for template config loading, template application, CLI listing, and
  templated one-shot prompts.

## 0.2.0 - 2026-05-25

- Add native GTK and Tk desktop clients.
- Add OpenAI-compatible provider profiles for Hugging Face/TKI, OpenAI,
  ChatGPT, and a local Codex CLI bridge.
- Add SQLite chat history, folder grouping, pinned chats, filtering, sorting,
  full-history search, exports, and live `doctor` checks.
- Add regeneration of the latest assistant answer in CLI, GTK, and Tk without
  duplicating the previous user message.
- Add collapsible/resizable side panes and `Shift+Enter` send in both GUIs.
- Add CLI session filtering with `--query`, `--folder`, and `--sort`.
- Add Hugging Face Space bearer-token authentication and local Telachat/Bavarder
  key wiring without storing tokens in the repository.
- Add Windows packaging scripts for the Tk frontend.
- Add regression tests for config loading, API client behavior, SQLite history,
  thread-safe store access, DB migrations, answer regeneration, GUI imports, and
  CLI session filtering.
