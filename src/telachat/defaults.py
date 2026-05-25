from __future__ import annotations

APP_NAME = "telachat"
APP_TITLE = "Telachat"
DEFAULT_PROFILE = "tki"
DEFAULT_BASE_URL = "https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1"
DEFAULT_API_KEY = "env:TELACHAT_QWEN_API_KEY"
DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DEFAULT_THEME = "system"
DEFAULT_SYSTEM_PROMPT = (
    "Du bist Telachat, ein direkter, praktischer KI-Assistent. "
    "Antworte in der Sprache des Nutzers, rechne sorgfaeltig und erfinde "
    "keine externen Fakten, wenn du sie nicht pruefen kannst."
)
DEFAULT_PROMPT_TEMPLATES = {
    "summarize": "Fasse den folgenden Inhalt strukturiert zusammen:\n\n{input}",
    "explain": "Erklaere das knapp, praktisch und mit einem Beispiel:\n\n{input}",
    "translate_de": "Uebersetze ins Deutsche und erhalte Fachbegriffe, wenn sinnvoll:\n\n{input}",
}

DEFAULT_CONFIG = f"""# Telachat configuration.
# Paths follow the XDG Base Directory spec:
#   config: $XDG_CONFIG_HOME/telachat/config.toml or ~/.config/telachat/config.toml
#   data:   $XDG_DATA_HOME/telachat/ or ~/.local/share/telachat/
#
# API keys can be literal placeholders, or environment references:
#   api_key = "env:TELACHAT_API_KEY"
# Direct real keys in this file are possible, but not recommended.

default_profile = "{DEFAULT_PROFILE}"
theme = "{DEFAULT_THEME}"
default_system_prompt = "{DEFAULT_SYSTEM_PROMPT}"
max_history_messages = 24

[prompt_templates]
# Supported variables: {{input}}, {{date}}, {{time}}, {{datetime}}.
summarize = "{DEFAULT_PROMPT_TEMPLATES["summarize"].replace(chr(10), "\\n").replace("{", "{{").replace("}", "}}")}"
explain = "{DEFAULT_PROMPT_TEMPLATES["explain"].replace(chr(10), "\\n").replace("{", "{{").replace("}", "}}")}"
translate_de = "{DEFAULT_PROMPT_TEMPLATES["translate_de"].replace(chr(10), "\\n").replace("{", "{{").replace("}", "}}")}"

[profiles.{DEFAULT_PROFILE}]
label = "HuggingFace TKI"
base_url = "{DEFAULT_BASE_URL}"
api_key = "{DEFAULT_API_KEY}"
model = "{DEFAULT_MODEL}"
models = ["Qwen/Qwen2.5-1.5B-Instruct", "qwen2-5-1-5b-instruct-free"]
temperature = 0.2
top_p = 0.9
max_tokens = 512
timeout_seconds = 300
stream = true
api_mode = "chat_completions"

[profiles.huggingface]
label = "HuggingFace"
base_url = "{DEFAULT_BASE_URL}"
api_key = "{DEFAULT_API_KEY}"
model = "Qwen/Qwen2.5-1.5B-Instruct"
models = ["Qwen/Qwen2.5-1.5B-Instruct", "qwen2-5-1-5b-instruct-free"]
temperature = 0.2
top_p = 0.9
max_tokens = 512
timeout_seconds = 300
stream = true
api_mode = "chat_completions"

[profiles.openai]
label = "OpenAI API"
base_url = "https://api.openai.com/v1"
api_key = "env:OPENAI_API_KEY"
model = "gpt-5.5"
models = ["gpt-5.5", "gpt-5.5-pro", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.2", "gpt-5.1", "gpt-5.1-chat-latest", "gpt-5-chat-latest", "gpt-4.1-mini", "gpt-4.1"]
temperature = 0.2
top_p = 0.9
max_tokens = 1024
reasoning_effort = "high"
timeout_seconds = 300
stream = false
api_mode = "responses"

# Local OpenAI-compatible desktop/server presets. Start the respective local
# server first and adjust `model` to a model installed in that tool.
[profiles.lmstudio]
label = "LM Studio"
base_url = "http://localhost:1234/v1"
api_key = "lm-studio"
model = "local-model"
models = ["local-model"]
temperature = 0.2
top_p = 0.9
max_tokens = 1024
timeout_seconds = 300
stream = true
api_mode = "chat_completions"

[profiles.ollama]
label = "Ollama"
base_url = "http://localhost:11434/v1"
api_key = "ollama"
model = "llama3.2"
models = ["llama3.2", "qwen2.5:1.5b", "gpt-oss:20b"]
temperature = 0.2
top_p = 0.9
max_tokens = 1024
timeout_seconds = 300
stream = true
api_mode = "chat_completions"

[profiles.jan]
label = "Jan Local API"
base_url = "http://127.0.0.1:1337/v1"
api_key = "env:TELACHAT_JAN_API_KEY"
model = "jan-v3-4b-base-instruct"
models = ["jan-v3-4b-base-instruct"]
temperature = 0.2
top_p = 0.9
max_tokens = 1024
timeout_seconds = 300
stream = true
api_mode = "chat_completions"

# Codex is not a normal OpenAI-compatible chat endpoint. This profile is a
# placeholder so the UI exposes the desired target, but direct Codex access is
# handled through the local `codex exec` CLI, not through /v1/chat/completions.
[profiles.codex]
label = "Codex CLI"
base_url = "codex://local"
api_key = ""
model = "codex-cli"
models = ["codex-cli", "gpt-5.3-codex", "gpt-5.2-codex", "gpt-5.1-codex", "gpt-5-codex"]
temperature = 0.2
top_p = 1.0
max_tokens = 4096
timeout_seconds = 600
stream = false
api_mode = "codex"
"""
