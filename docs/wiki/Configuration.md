# Configuration

Telachat liest seine Standardkonfiguration aus:

```text
~/.config/telachat/config.toml
```

Die SQLite-Historie liegt unter:

```text
~/.local/share/telachat/history.sqlite3
```

## Provider und Modelle

Profile werden in TOML konfiguriert. Die GUI trennt Provider- und
Modellauswahl: erst Provider waehlen, dann Modell oder Profilvariante.

Beispiele fuer Provider:

- `huggingface` / `tki`
- `openai`
- `lmstudio`
- `ollama`
- `jan`
- `codex`

## Secrets

API-Schluessel gehoeren nicht direkt in das Repo oder Wiki. Telachat
unterstuetzt:

- `env:NAME`
- `envfile:/pfad/zur/datei#NAME`

Lokale Secret-Dateien sollten nur fuer den Benutzer lesbar sein:

```sh
chmod 600 ~/.config/telachat/*.env
```

## Prompt-Templates

Ab Version `0.3.0` gibt es in `config.toml` einen Abschnitt:

```toml
[prompt_templates]
summarize = "Fasse den folgenden Inhalt strukturiert zusammen:"
explain = "Erklaere das knapp, praktisch und mit einem Beispiel:"
translate_de = "Uebersetze ins Deutsche und erhalte Fachbegriffe, wenn sinnvoll:"
```

Verwendung:

```sh
telachat templates
telachat ask --template summarize "Langer Text"
```

Templates unterstuetzen die eingebauten Platzhalter `{input}`, `{date}`,
`{time}` und `{datetime}`. Wenn ein Template kein `{input}` enthaelt, haengt
Telachat den eingegebenen Text wie bisher darunter an.

## Ordner-Systemprompts

Ordner-Systemprompts werden in SQLite gespeichert, nicht in `config.toml`.
Dadurch bleiben sie Teil der lokalen Chat-Historie und koennen pro Projekt
angepasst werden.

```sh
telachat folders --create Projekt --system "Antworte mit Projektkontext."
telachat folders --set-system Projekt "Neuer Kontext."
telachat folders --show-system
```

## Lokale Provider-Presets

Die Standardkonfiguration enthaelt nicht-default Presets fuer lokale
OpenAI-kompatible Server. Starte den jeweiligen Server zuerst und passe das
Modell an ein installiertes lokales Modell an.

```toml
[profiles.lmstudio]
base_url = "http://localhost:1234/v1"
api_key = "lm-studio"
model = "local-model"

[profiles.ollama]
base_url = "http://localhost:11434/v1"
api_key = "ollama"
model = "llama3.2"

[profiles.jan]
base_url = "http://127.0.0.1:1337/v1"
api_key = "env:TELACHAT_JAN_API_KEY"
model = "jan-v3-4b-base-instruct"
```
