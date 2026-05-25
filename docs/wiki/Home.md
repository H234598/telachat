# Telachat

Telachat ist ein lokaler Desktop- und CLI-Client fuer OpenAI-kompatible
Chat-APIs. Der Standard auf diesem Rechner ist das Hugging-Face/TKI-Profil,
zusaetzlich gibt es Profile fuer OpenAI, ChatGPT und eine lokale Codex-Bridge.

## Schnellstart

```sh
telachat profiles
telachat doctor --chat
telachat ask "Hallo"
telachat-tk
telachat-gtk
```

## Aktuelle Artefakte

- Repository: `https://github.com/H234598/telachat`
- Release-Serie: `0.x`
- Zipapp: `dist/telachat.pyz`
- Tk-Bundle: `dist/TelachatTk`
- Installierte Wrapper: `~/.local/bin/telachat`, `telachat-tk`, `telachat-gtk`

## Wiki-Seiten

- Configuration
- CLI
- GUI
- Versioning
- Releases

## Sicherheitsregeln

- Keine API-Tokens in Wiki, Repository, Gists oder Logs schreiben.
- Hugging-Face-Credits nicht kaufen, ausser es wird explizit angefordert.
- Lokale Secret-Dateien mit Dateimodus `0600` behandeln.
