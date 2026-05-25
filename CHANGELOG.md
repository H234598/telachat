# Changelog

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
