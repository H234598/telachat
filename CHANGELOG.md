# Changelog

## Unreleased

## 0.49.0 - 2026-05-26

- Remove the duplicate default `tki` provider while keeping it as a legacy alias for stored sessions and folder backends.
- Show the HuggingFace model alias `TKI` while sending the real Qwen model ID to the API.
- Let profiles omit `temperature` and `top_p` from API requests; the OpenAI Responses profile disables both by default for GPT-5.x compatibility.
- Harden Windows packaging around unusable Microsoft Store Python aliases and add a reusable Windows test script.
- Add versioned Windows portable ZIP and NSIS installer outputs with SHA256 sidecar files.
- Add Windows CI packaging coverage and release upload validation without raw wildcard uploads.
- Keep Windows escape-like path tests inside temporary directories.

## 0.48.1 - 2026-05-25

- Add direct GUI regression coverage for `/models` and `/models live` in both Tk and GTK frontends.
- Validate configured profile header names and values before they are sent with API requests.
- Add a persistent `validate_profile_headers` option plus Tk/GTK settings controls to relax strict standard header-name validation for intentionally unusual providers while still rejecting control characters.

## 0.48.0 - 2026-05-25

- Add `/models [live]` to the shared slash-command catalog, CLI chat, and both desktop frontends.
- Show configured models for the active provider without a network call, or run the existing live model check with `/models live`.
- Add completion and regression coverage for the new interactive model command.
- Include direct correction coverage so the release-upload guard follows PowerShell continuation lines.

## 0.47.5 - 2026-05-25

- Ignore negative token-usage counts when formatting or persisting provider usage metadata.
- Keep valid zero token counts in structured usage records while avoiding misleading text output.
- Add regression coverage for invalid usage metadata in both local stats and client formatting.

## 0.47.4 - 2026-05-25

- Return a stored metadata copy from `ChatStore.add_message()` so later caller-side dictionary mutations cannot affect the returned message state.
- Add regression coverage proving saved message metadata stays isolated from input and returned metadata mutations.

## 0.47.3 - 2026-05-25

- Add regression coverage proving assistant usage metadata survives session forks.
- Add regression coverage proving additive history imports preserve stored usage metadata.
- Add regression coverage proving deleted assistant messages keep their usage metadata.

## 0.47.2 - 2026-05-25

- Add workflow regression coverage that rejects raw wildcards passed directly to `gh release upload`.
- Guard the Windows packaging release-upload path so assets must be resolved and validated before upload.

## 0.47.1 - 2026-05-25

- Add a legacy SQLite migration for old `messages` tables that do not yet have the `metadata` column.
- Cover the migration so token-usage metadata can be stored safely on older local histories.

## 0.47.0 - 2026-05-25

- Persist provider token-usage metadata on saved assistant messages when usage is available.
- Aggregate stored input/output/total token counts in `telachat stats` and `stats --json` without exposing message content.
- Reuse the shared token-usage record helper across CLI/controller storage and JSON output.

## 0.46.0 - 2026-05-25

- Add built-in prompt-template variables: `{date}`, `{time}`, and `{datetime}` in addition to `{input}`.
- Report referenced built-in variables in `telachat templates --json`.
- Share prompt-template rendering between CLI and GUI/controller paths.

## 0.45.1 - 2026-05-25

- Add regression coverage for `telachat ask --json --save` session persistence and quiet stderr.

## 0.45.0 - 2026-05-25

- Add `telachat ask --json` for scriptable one-shot answers with provider, model, and usage metadata.
- Add tracked-source secret-shape hygiene coverage.

## 0.44.0 - 2026-05-25

- Surface provider token usage from Chat Completions and Responses results in GUI response status and `doctor --json --chat`.
- Further redact documented local key names and keep additional secret-source parsing coverage.

## 0.43.11 - 2026-05-25

- Add GUI regression coverage for refreshing live model choices after Check.

## 0.43.10 - 2026-05-25

- Add focused regression coverage for Windows-style secret paths containing escape-like backslashes.

## 0.43.9 - 2026-05-25

- Align configuration validation with GUI generation ranges for `temperature` and `top_p`.
- Compile packaging helper modules during `make check`.

## 0.43.8 - 2026-05-25

- Validate numeric configuration values and per-request generation overrides with clear `ConfigError` messages.

## 0.43.7 - 2026-05-25

- Preserve raw UNC prefixes in Windows-style `file:` and `envfile:` secret-source paths.

## 0.43.6 - 2026-05-25

- Preserve raw Windows backslashes in `file:` and `envfile:` secret sources written as TOML basic strings.

## 0.43.5 - 2026-05-25

- Prevent GTK/Tk folder model defaults from being applied when the folder's default profile is not configured locally.

## 0.43.4 - 2026-05-25

- Validate controller-created folder backend defaults before storing them.

## 0.43.3 - 2026-05-25

- Label stored `system` messages as `System` in Markdown exports instead of treating every non-user role as assistant text.

## 0.43.2 - 2026-05-25

- Wrap unreadable `file:` and `envfile:` secret sources as `ConfigError` with compact user-facing messages.
- Add regression coverage for missing secret files.

## 0.43.1 - 2026-05-25

- Keep interactive chat sessions alive when a send fails because a configured secret envfile cannot be read.
- Report `ApiError`, `ConfigError`, and `OSError` send failures inside `/template` and normal chat sends without exiting the loop.

## 0.43.0 - 2026-05-25

- Add optional folder default backends: provider/profile plus model.
- Add `telachat folders --set-backend FOLDER PROFILE [MODEL]`, `--clear-backend FOLDER`, and create-time `--profile/--model`.
- Apply folder backend defaults in controller-created sessions and GTK/Tk folder selection.
- Preserve folder backend defaults in folder JSON exports/imports and backup-history restores.

## 0.42.1 - 2026-05-25

- Restore the just-sent prompt after cancelling a running GUI send operation when the composer is still empty.
- Clear stored prompt drafts when late cancelled or stale GUI worker results arrive.

## 0.42.0 - 2026-05-25

- Add an `Abbrechen` button to GTK and Tk while send, regenerate, or Check is running.
- Ignore late GUI worker results from cancelled operations so stale answers or errors do not overwrite the current UI.
- Cover cancelled GTK and Tk request results in regression tests.

## 0.41.0 - 2026-05-25

- Add `telachat templates --json` for structured prompt-template inventory.
- Report template name, preview, line/character counts, and `{input}` usage.

## 0.40.0 - 2026-05-25

- Add content-free chat context estimates via `telachat context` and `/context`.
- Show stored/request message counts, character totals, and approximate tokens.
- Cover CLI, Tk, GTK, and shared formatting paths.

## 0.39.2 - 2026-05-25

- Cover every declared slash-command alias resolving to its canonical command.

## 0.39.1 - 2026-05-25

- Cover Tk and GTK `/regenerate` aliases through the shared command catalog.

## 0.39.0 - 2026-05-25

- Normalize Tk and GTK slash-command aliases through the shared command catalog.
- Add GUI `/exit`, `/quit`, and `/q` prompt commands for closing the window.
- Cover Tk and GTK exit aliases.

## 0.38.2 - 2026-05-25

- Validate profile `stream` and `api_mode` values while loading config.
- Add regression coverage for invalid profile booleans and API modes.

## 0.38.1 - 2026-05-25

- Keep interactive `/doctor` alive when local secret sources or OS access fail.
- Add regression coverage for missing envfile errors in terminal chat.

## 0.38.0 - 2026-05-25

- Add `/doctor` to interactive CLI, Tk, and GTK prompt command paths.
- Reuse the GUI Check action from the prompt and report `/models` reachability in terminal chat.
- Cover command catalog, terminal slash-command, and GUI prompt dispatch behavior.

## 0.37.1 - 2026-05-25

- Add GTK regression coverage for the `/stats` prompt dialog.

## 0.37.0 - 2026-05-25

- Add `/stats` to interactive CLI, Tk, and GTK prompt command paths.
- Share content-free statistics formatting across CLI and GUI output.
- Cover command catalog, terminal slash-command, and Tk `/stats` behavior.

## 0.36.1 - 2026-05-25

- Add regression coverage for zero-count `telachat stats` behavior on an empty
  history database.

## 0.36.0 - 2026-05-25

- Add `telachat stats` for local, content-free history inventory.
- Report counts for sessions, messages, folders, tags, profiles, and models.
- Add JSON output and regression tests that verify message content and provider
  secrets stay out of the statistics.
- Integrate additional response-timing regression coverage for GTK status
  updates and regenerate calls.

## 0.35.0 - 2026-05-25

- Measure API response latency for send/regenerate operations.
- Show elapsed response time in both Tk and GTK GUI status areas.
- Add focused Controller/GUI tests for elapsed-time reporting.

## 0.34.1 - 2026-05-25

- Add focused Chat Completions regression coverage for generation parameters.

## 0.34.0 - 2026-05-25

- Add visible Tk/GTK generation controls for temperature and max output tokens.
- Pass GUI generation overrides through Controller send/regenerate calls.
- Send temperature/top_p on OpenAI Responses API requests so CLI and GUI
  parameters behave consistently.

## 0.33.0 - 2026-05-25

- Add visible Tk/GTK tag filters in the sidebar, including tag counts.
- Preserve the selected tag filter when `/tag` or `/untag` changes counts.
- Cover GUI refresh propagation and Tk tag-filter selection preservation.

## 0.32.1 - 2026-05-25

- Add focused GUI regression coverage for Tk/GTK archive-filter session refresh.

## 0.32.0 - 2026-05-25

- Add visible GUI archive filters in both Tk and GTK sidebars.
- Let the session list switch between active, archived, and all chats without
  using slash commands.
- Make `/archives` switch the GUI list into the archive view before showing
  archive status.

## 0.31.0 - 2026-05-25

- Add soft archiving for sessions with SQLite migration and active/archived/all
  list filters.
- Add `telachat archive`, `telachat unarchive`, `sessions --archived`,
  `sessions --all`, and archive-aware folder exports.
- Add `/archive`, `/unarchive`, and `/archives` in CLI, GTK, and Tk; GUI
  session labels and JSON/Markdown exports preserve archive state.

## 0.30.0 - 2026-05-25

- Add persistent per-session tags in SQLite with tag normalization and counts.
- Add `telachat tags` plus `sessions --tag` for CLI tag management/filtering.
- Include tags in session JSON/Markdown exports, imports, forks, backup
  history restores, search, completion, and GUI session labels.

## 0.29.0 - 2026-05-25

- Add the standard `telachat --version` CLI option.
- Cover the version option with a CLI regression test.

## 0.28.0 - 2026-05-25

- Update GTK and Tk model selectors with live `/models` results after the GUI
  Check action.
- Keep the currently selected model first while merging live and configured
  model IDs without duplicates.
- Add focused tests for model-choice merging.

## 0.27.0 - 2026-05-25

- Add `telachat models` for configured model inventory across profiles.
- Add `telachat models --live [-p PROFILE]` to query `/models` for one target
  profile.
- Add redacted JSON output for model inventory and live model discovery.

## 0.26.0 - 2026-05-25

- Add `config-check --profile NAME` to validate one configured profile.
- Make `--strict` useful for a selected profile without counting optional
  providers that are not being used.
- Include `profile_filter` in JSON config-check output.
- Fix Zipapp command exit codes by using a `SystemExit(main())` launcher.

## 0.25.0 - 2026-05-25

- Add default local OpenAI-compatible provider presets for LM Studio, Ollama,
  and Jan Local API.
- Keep local presets non-default and secret-safe; users still choose or adjust
  installed local model IDs explicitly.
- Add regression coverage for the new default local profile metadata.

## 0.24.0 - 2026-05-25

- Add `--dry-run` to `import-session` and `import-folder`.
- Validate JSON import files and report session/message counts without writing
  folders, sessions, or messages.
- Add regression coverage that dry-run imports leave SQLite unchanged.

## 0.23.0 - 2026-05-25

- Add `telachat import-folder FILE.json` for additive imports of
  `telachat.folder.v1` exports.
- Support `--folder` and `--json` for scripted multi-session imports.
- Validate every bundled session and message before creating folders or
  sessions, preventing partial imports on bad data.

## 0.22.0 - 2026-05-25

- Add `telachat export-folder FOLDER --json` for machine-readable
  multi-session folder exports.
- Include folder metadata, selected sort mode, session metadata, system
  prompts, and ordered messages without provider config or raw secrets.
- Keep empty folder JSON exports machine-readable with an empty session list.

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
