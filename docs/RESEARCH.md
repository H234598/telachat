# Telachat research notes

Date: 2026-05-25

## What existing tools do well

Open WebUI and LibreChat both validate the main architectural decision:
target protocols, not individual vendors. Open WebUI documents direct support
for any server/provider that implements an OpenAI-compatible API and explicitly
describes a protocol-oriented design around Chat Completions. LibreChat's custom
endpoint docs use the same idea: endpoint name, API URL, models and API keys are
configuration, not hard-coded provider classes.

Jan and LM Studio validate the native-desktop/local-first direction. Jan exposes
a desktop app with local models and cloud providers configured by user-owned API
keys. LM Studio's server path is OpenAI-compatible and keeps tool/function-use
available through standard `/v1/chat/completions` and `/v1/responses` shapes.

Simon Willison's `llm` CLI is the strongest small-tool reference. It supports
additional OpenAI-compatible models by config, separates the public model ID
from the provider's actual model name, supports extra headers, and logs prompts.

The OpenAI streaming docs confirm that Chat Completions streaming is still a
common SSE shape: `stream=true` returns data-only server-sent events where chunks
carry incremental deltas. Telachat implements this directly without depending on
the fast-moving OpenAI Python SDK.

The XDG Base Directory Specification is the right storage convention for Linux:
configuration under `$XDG_CONFIG_HOME`, portable app data under `$XDG_DATA_HOME`,
and local state under `$XDG_STATE_HOME`.

## What is painful in common tools

- Full web UIs are powerful but heavy for one local user: browser/server state,
  Docker/service updates, admin panels, and larger attack surface.
- Some tools store custom endpoints in several files and require restarts after
  changes. That is fine for multi-user servers, too much for a personal CLI.
- Provider auto-detection often depends on `/models`. Some compatible services
  do not expose `/models` or expose too many models, so manual model config must
  remain first-class.
- Desktop clients that also act as model servers are useful, but they can blur
  the boundary between "client", "provider config" and "runtime". Telachat keeps
  that boundary explicit.
- GUI tools can hide fragile state. Bavarder was easy to start with, but provider
  slugs, current-provider state, and old chat roles made failures confusing.
- SDK-first clients can break when SDKs change. Telachat uses only Python's
  standard library for HTTP, TOML reading and SQLite.

## Telachat design choices

- Use OpenAI-compatible `/v1/chat/completions` and `/v1/models`.
- Keep provider profiles in `~/.config/telachat/config.toml`.
- Resolve real secrets from `env:VARIABLE` or `file:/path` when desired.
- Store history in SQLite at `~/.local/share/telachat/history.sqlite3`.
- Provide both machine-friendly one-shot `ask` and human interactive `chat`.
- Include `doctor` for real endpoint checks and `tests/` for offline fake-API
  regression tests.
- Do not implement provider-specific purchase or billing actions.
- GUI frontends must run long API calls off the main UI thread. GTK updates are
  returned through `GLib.idle_add`; Tk updates are returned through `after()` and
  a queue.
- Build a GTK frontend for the Linux desktop and a Tk frontend for packaging
  simplicity on Windows.
- Chat management must include collapseable side panels, folder/grouping,
  sorting, search, regeneration, and a command path. Otherwise a desktop client
  becomes painful as soon as more than a handful of chats exist.
- For Windows installers, use PyInstaller on Windows plus NSIS. PyInstaller is
  not a cross-compiler, so Linux cannot honestly emit a native Windows `.exe`.
- OpenAI is exposed as a normal OpenAI-compatible `/v1` profile with
  `env:OPENAI_API_KEY`. The separate ChatGPT alias was removed because it used
  the same Responses API path. Codex is exposed through the local `codex exec`
  CLI because it is an agent CLI, not a normal Chat Completions model endpoint.

## Feature ideas kept for later

- Per-session model/temperature overrides.
- Stop/cancel in-flight request.
- Config editor with validation and secret redaction.
- Markdown rendering with copy buttons.
- Token/latency counters when backends provide usage data.
- Tags in addition to folders and pinned chats.
- Per-folder defaults for system prompt, model and attached knowledge/context.
- Import/export bundles for a folder of chats without including API keys.
- Optional local provider presets for Ollama, LM Studio and Jan Server.
- Tool/function-call viewer once a backend returns structured tool calls.

## Sources

- Open WebUI OpenAI-compatible docs: https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/
- Open WebUI chat features overview: https://docs.openwebui.com/features/chat-conversations/chat-features/
- Open WebUI folders/projects: https://docs.openwebui.com/features/chat-conversations/chat-features/conversation-organization
- Open WebUI prompts/slash commands: https://docs.openwebui.com/features/workspace/prompts/
- LibreChat custom endpoints: https://www.librechat.ai/docs/quick_start/custom_endpoints
- LibreChat resumable streams: https://www.librechat.ai/docs/features/resumable_streams
- Jan model/provider management: https://www.jan.ai/docs/desktop/manage-models
- LM Studio tool use/server API: https://www.lmstudio.ai/docs/advanced/tool-use
- Msty Turnstiles/regeneration: https://docs.msty.studio/features/turnstiles
- OpenAI Help retry/regenerate note: https://help.openai.com/en/articles/11909943-gpt-53-and-gpt-54-in-chatgpt
- LLM OpenAI-compatible models: https://llm.datasette.io/en/stable/other-models.html
- OpenAI streaming responses: https://developers.openai.com/api/docs/guides/streaming-responses
- XDG Base Directory Specification: https://specifications.freedesktop.org/basedir-spec/0.8/
