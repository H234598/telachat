# Telachat testing

## Local deterministic tests

```sh
cd /home/teladi/telachat
make compile
make test3
make zipapp
```

The fake OpenAI-compatible HTTP server in `tests/test_client.py` binds to
`127.0.0.1`. If a sandbox blocks local sockets, run the tests outside that
sandbox. No external API key is needed.

## Live endpoint tests

```sh
telachat doctor
telachat doctor --chat
telachat templates
telachat ask --template summarize "Was hat sich geaendert?"
telachat ask "Was ist 812 - 512?"
telachat ask -p codex "Antworte nur mit: CODEX-OK"
telachat-gtk
telachat-tk
```

Live tests use the active profile from `config.toml`, currently `tki`.
`doctor --chat` and `ask` send prompts to the configured API.
The GUI commands require a graphical desktop session.
OpenAI/ChatGPT live tests require `OPENAI_API_KEY`.
On this host they can also use
`envfile:/home/teladi/.config/telachat/openai.env#OPENAI_API_KEY`
from `~/.config/telachat/config.toml`.

The deterministic suite also covers folder creation, duplicate folder handling,
session moves, folder filters, pinned-chat ordering, answer regeneration, prompt
templates, title sorting, content search across saved messages, and CLI session
filtering/sorting.

## Expected default live configuration

```text
Profile: tki / TKI
API: https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1
Model: gpt-4
Key: local envfile `/home/teladi/.config/telachat/qwen.env`
```

The HF Space rejects the old placeholder key. The active Space secret is
`TELACHAT_API_KEYS`; the local client key is `Telachat_API_Teladi`.
