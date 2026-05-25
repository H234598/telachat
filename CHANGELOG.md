# Changelog

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
