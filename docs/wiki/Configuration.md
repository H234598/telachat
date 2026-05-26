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

Globale Optionen stehen im Kopf von `config.toml`:

```toml
theme = "system"
app_icon = "system"
chat_background_image = ""
validate_profile_headers = true
skill_watchdog_enabled = false
max_history_messages = 24
```

`validate_profile_headers` prueft konfigurierte Zusatz-Header vor dem Senden.
Setze den Wert auf `false`, wenn ein absichtlich ungewoehnlicher Provider
Headernamen erwartet, die nicht durch die strikte Standard-HTTP-Pruefung
passen. Steuerzeichen in Headerwerten und parser-gefaehrliche Headernamen
werden ebenso wie nicht-portable Headernamen weiter abgelehnt. In Tk und GTK
ist dieselbe Option im Optionen-/Preferences-Dialog verfuegbar.

`app_icon` akzeptiert `system`, `random` oder einen der mitgelieferten
Icon-Namen. `random` waehlt sofort ein Icon und rotiert danach stuendlich.
`chat_background_image` speichert einen lokalen Bildpfad fuer das Chatmodul.

## Codex-Skill-Watchdog

Der Codex-Skill-Watchdog scannt standardmaessig `~/.codex/plugins/cache`,
`~/.codex/.tmp/plugins/plugins`, `~/.codex/skills` und `~/.agents/skills`,
kuerzt nur ueberlange Frontmatter-`description`-Felder auf unter 1024 Zeichen
und schreibt vor der ersten Aenderung ein `SKILL.md.telachat-watchdog.bak`.
Der eigentliche Skill-Body bleibt erhalten. Manuell laeuft er mit:

```sh
telachat skill-watchdog --json
```

Neue Konfigurationen setzen `skill_watchdog_enabled = false`. Tk und GTK
starten denselben Lauf nur mit `skill_watchdog_enabled = true` beim App-Start
und danach stuendlich im Hintergrund. `TELACHAT_DISABLE_SKILL_WATCHDOG=1`
deaktiviert ihn auch dann. `TELACHAT_SKILL_WATCHDOG_ROOTS` kann eine mit `:`
getrennte Root-Liste setzen.

Beispiele fuer Provider:

- `huggingface`
- `openai`
- `lmstudio`
- `ollama`
- `jan`
- `codex`

`huggingface` ist das Default-Profil. Das Modell `TKI` ist ein sichtbarer Alias
und wird intern auf `Qwen/Qwen2.5-1.5B-Instruct` gemappt. Alte gespeicherte
`tki`-Profilreferenzen werden beim Laden weiter auf `huggingface` aufgeloest,
aber neue Standardconfigs enthalten kein separates `tki`-Profil mehr.

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
telachat templates --set brief "Kurz antworten: {input}"
telachat templates --rename brief kurz
telachat templates --delete kurz
telachat ask --template summarize "Langer Text"
```

Templates unterstuetzen die eingebauten Platzhalter `{input}`, `{date}`,
`{time}` und `{datetime}`. Wenn ein Template kein `{input}` enthaelt, haengt
Telachat den eingegebenen Text wie bisher darunter an.

## Ordner-Kontext

Ordner-Systemprompts und Ordner-Kontextnotizen werden in SQLite gespeichert,
nicht in `config.toml`. Dadurch bleiben sie Teil der lokalen Chat-Historie und
koennen pro Projekt angepasst werden. Kontextnotizen werden beim Start neuer
Chats unter den Systemprompt gehaengt.

```sh
telachat folders --create Projekt --system "Antworte mit Projektkontext." --context "Projektwissen."
telachat folders --set-system Projekt "Neuer Kontext."
telachat folders --set-context Projekt "Aktueller Wissensstand."
telachat folders --show-system --show-context
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
