# Telachat research notes

Date: 2026-05-25

## What existing tools do well

Open WebUI and LibreChat both validate the main architectural decision:
target protocols, not individual vendors. Open WebUI documents direct support
for any server/provider that implements an OpenAI-compatible API and explicitly
describes a protocol-oriented design around Chat Completions. LibreChat's custom
endpoint docs use the same idea: endpoint name, API URL, models and API keys are
configuration, not hard-coded provider classes.

Open WebUI, LibreChat and Msty all treat conversation portability as a normal
chat-client responsibility. The common pattern is JSON for machine-readable
archives and Markdown for readable exports; imports should add copies rather
than overwriting existing history. That makes Telachat's single-session JSON
export/import and folder JSON export worth keeping first-class.

Open WebUI, LibreChat and Msty also treat model visibility as its own workflow,
not as an incidental config detail. Open WebUI has a model workspace with
presets, hiding, import/export, bulk management and model switching. LibreChat
uses model specs to define curated model entries and defaults. Msty separates
local model management from online provider setup. Telachat should keep its
model inventory scriptable first, then reuse the same shape for GUI refreshes.

Jan and LM Studio validate the native-desktop/local-first direction. Jan exposes
a desktop app with local models and cloud providers configured by user-owned API
keys. LM Studio's server path is OpenAI-compatible and keeps tool/function-use
available through standard `/v1/chat/completions` and `/v1/responses` shapes.
Ollama documents OpenAI-compatible `/v1/chat/completions` at
`http://localhost:11434/v1`, with the API key required by clients but ignored by
the server.

Simon Willison's `llm` CLI is the strongest small-tool reference. It supports
additional OpenAI-compatible models by config, separates the public model ID
from the provider's actual model name, supports extra headers, and logs prompts.

The OpenAI streaming docs confirm that Chat Completions streaming is still a
common SSE shape: `stream=true` returns data-only server-sent events where chunks
carry incremental deltas. Telachat implements this directly without depending on
the fast-moving OpenAI Python SDK.

The OpenAI model and Responses API docs confirm that `gpt-5.5` is a valid model
ID on the API and that Responses accepts `reasoning.effort` values including
`high`. Telachat maps profile `reasoning_effort = "high"` to that Responses API
shape for OpenAI defaults.

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
- Expose configured and live model lists through `telachat models` before
  adding heavier GUI model-management flows.
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
- Local desktop/server presets are included for LM Studio, Ollama and Jan, but
  they are not the default profile. The user still has to start the local
  server and choose a model installed in that tool.

## Feature ideas kept for later

- Per-session model/temperature overrides.
- Stop/cancel in-flight request.
- Config editor with validation and secret redaction.
- Markdown rendering with copy buttons.
- Token/latency counters when backends provide usage data.
- Tags in addition to folders and pinned chats.
- Per-folder defaults for system prompt, model and attached knowledge/context.
- Import bundles for a folder of chats without including API keys.
- Tool/function-call viewer once a backend returns structured tool calls.

## Sources

- Open WebUI OpenAI-compatible docs: https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/
- Open WebUI import/export docs: https://docs.openwebui.com/features/chat-conversations/data-controls/import-export/
- Open WebUI chat features overview: https://docs.openwebui.com/features/chat-conversations/chat-features/
- Open WebUI folders/projects: https://docs.openwebui.com/features/chat-conversations/chat-features/conversation-organization
- Open WebUI prompts/slash commands: https://docs.openwebui.com/features/workspace/prompts/
- Open WebUI model workspace: https://docs.openwebui.com/features/workspace/models/
- LibreChat custom endpoints: https://www.librechat.ai/docs/quick_start/custom_endpoints
- LibreChat model specs: https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/model_specs
- LibreChat import conversations: https://www.librechat.ai/docs/features/import_convos
- LibreChat resumable streams: https://www.librechat.ai/docs/features/resumable_streams
- Jan model/provider management: https://www.jan.ai/docs/desktop/manage-models
- Jan local API server: https://www.jan.ai/docs/desktop/api-server
- Jan API reference: https://www.jan.ai/docs/desktop/api-preference
- Ollama OpenAI compatibility: https://docs.ollama.com/openai
- LM Studio tool use/server API: https://www.lmstudio.ai/docs/advanced/tool-use
- LM Studio OpenAI compatibility endpoints: https://lmstudio.ai/docs/developer/openai-compat/
- Msty export chat: https://docs.msty.app/features/export-chat
- Msty local models: https://docs.msty.studio/managing-models/local-models
- Msty Turnstiles/regeneration: https://docs.msty.studio/features/turnstiles
- OpenAI Help retry/regenerate note: https://help.openai.com/en/articles/11909943-gpt-53-and-gpt-54-in-chatgpt
- LLM OpenAI-compatible models: https://llm.datasette.io/en/stable/other-models.html
- OpenAI streaming responses: https://developers.openai.com/api/docs/guides/streaming-responses
- OpenAI GPT-5.5 model docs: https://developers.openai.com/api/docs/models/gpt-5.5
- OpenAI Responses API reasoning docs: https://platform.openai.com/docs/api-reference/responses/compact?lang=curl
- XDG Base Directory Specification: https://specifications.freedesktop.org/basedir-spec/0.8/
