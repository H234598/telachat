from __future__ import annotations

APP_NAME = "telachat"
APP_TITLE = "Telachat"
DEFAULT_PROFILE = "huggingface"
DEFAULT_BASE_URL = "https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1"
DEFAULT_API_KEY = "env:TELACHAT_QWEN_API_KEY"
DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DEFAULT_THEME = "system"
DEFAULT_APP_ICON = "system"
DEFAULT_CHAT_BACKGROUND_IMAGE = ""
DEFAULT_SKILL_WATCHDOG_ENABLED = False
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


def _default_config_template(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
        .replace("{", "{{")
        .replace("}", "}}")
    )


_DEFAULT_CONFIG_PROMPT_TEMPLATES = {
    name: _default_config_template(value)
    for name, value in DEFAULT_PROMPT_TEMPLATES.items()
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
app_icon = "{DEFAULT_APP_ICON}"
chat_background_image = "{DEFAULT_CHAT_BACKGROUND_IMAGE}"
validate_profile_headers = true
skill_watchdog_enabled = false
default_system_prompt = "{DEFAULT_SYSTEM_PROMPT}"
max_history_messages = 24

[prompt_templates]
# Supported variables: {{input}}, {{date}}, {{time}}, {{datetime}}.
summarize = "{_DEFAULT_CONFIG_PROMPT_TEMPLATES["summarize"]}"
explain = "{_DEFAULT_CONFIG_PROMPT_TEMPLATES["explain"]}"
translate_de = "{_DEFAULT_CONFIG_PROMPT_TEMPLATES["translate_de"]}"

[profiles.huggingface]
label = "HuggingFace"
base_url = "{DEFAULT_BASE_URL}"
api_key = "{DEFAULT_API_KEY}"
model = "TKI"
models = ["TKI", "Qwen/Qwen2.5-1.5B-Instruct", "qwen2-5-1-5b-instruct-free"]
temperature = 0.2
top_p = 0.9
max_tokens = 512
timeout_seconds = 300
stream = true
api_mode = "chat_completions"

[profiles.huggingface.model_aliases]
TKI = "{DEFAULT_MODEL}"

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
send_temperature = false
send_top_p = false

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
