# Telachat

Telachat ist ein kleiner lokaler Chat-Client fuer OpenAI-kompatible KI-APIs.
Er ist auf dein `TKI`/Hugging-Face-Space-Profil voreingestellt, kann aber
weitere Provider ueber `config.toml` nutzen.

Aktuelle Version: `0.3.0`. Das Projekt nutzt Semantic Versioning; Details
stehen in `VERSIONING.md`.

## Warum so gebaut

- OpenAI-kompatible Chat-Completions sind der stabilste gemeinsame Nenner fuer
  lokale Server, Hugging-Face-Spaces, OpenRouter, Ollama/LM-Studio-Bruecken und
  viele Web-UIs.
- Telachat-Core hat keine externen Python-Abhaengigkeiten. Die GUIs nutzen
  native System-Pakete: GTK4/PyGObject oder Tk/ttk.
- Konfiguration und Daten folgen XDG:
  - Config: `~/.config/telachat/config.toml`
  - Verlauf: `~/.local/share/telachat/history.sqlite3`
- API-Schluessel werden bei Ausgaben redaktiert. Fuer echte Secrets ist
  `api_key = "env:MEIN_API_KEY"` besser als Klartext.
  Lokale Env-Dateien gehen ebenfalls: `api_key = "envfile:/pfad/openai.env#OPENAI_API_KEY"`.

## Installation

```sh
cd /home/teladi/telachat
make install
telachat init
telachat doctor
```

Der Wrapper wird nach `~/.local/bin/telachat` installiert. Falls der Befehl in
einer Shell nicht gefunden wird, pruefe, ob `~/.local/bin` im `PATH` steht.

## Schnellstart

Einmalige Frage:

```sh
telachat ask "Was ist 812 - 512?"
```

Interaktiver Chat:

```sh
telachat chat
```

Native GUIs:

```sh
telachat-gtk
telachat-tk
```

`telachat-gtk` ist die huebschere GTK4/Adwaita-Variante fuer Linux.
`telachat-tk` nutzt Tk/ttk und ist die robustere Windows-Paketierungsbasis.
Beide GUIs haben eine zweistufige Auswahl: erst Provider, dann Modell. Die
linke Provider-/Chatleiste und der rechte System-Prompt-Bereich sind
einklappbar und per breitem Splitter in der Breite anpassbar. Chats koennen in
Ordnern abgelegt, nach Datum/Titel/Provider sortiert und ueber Titel, Provider
oder Nachrichteninhalt gesucht werden. Wichtige Chats koennen angeheftet
werden; gepinnte Chats stehen in Listen zuerst.

Im Texteingabefeld funktioniert auch eine kleine Kommandozeile:
`Shift+Enter` schickt die Nachricht ab, normales `Enter` bleibt fuer
Zeilenumbrueche.

```text
/help
/new
/rename TITLE
/delete
/pin
/unpin
/regen
/templates
/template NAME TEXT
/folder NAME
/rename-folder NAME
/delete-folder
/move NAME
/unfile
/sort newest|oldest|title|title-desc|provider
/search TEXT
/provider NAME
/model NAME
/left
/system
```

Nuetzliche Chat-Befehle:

```text
/help
/sessions
/load <session-prefix>
/pin
/unpin
/regen
/templates
/template NAME TEXT
/profile [name]
/system [prompt]
/history [n]
/export [datei.md]
/exit
```

Gespeicherte Sessions koennen auch direkt in der CLI gefiltert werden:

```sh
telachat sessions --query projekt
telachat sessions --folder Arbeit
telachat sessions --sort title
```

Prompt-Templates kommen aus `[prompt_templates]` in `config.toml` und koennen
per CLI oder GUI eingesetzt werden:

```sh
telachat templates
telachat ask --template summarize "Langer Text..."
```

## Voreingestelltes TKI-Profil

```toml
[profiles.tki]
label = "TKI"
base_url = "https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1"
api_key = "env:TELACHAT_QWEN_API_KEY"
model = "gpt-4"
temperature = 0.2
top_p = 0.9
max_tokens = 512
timeout_seconds = 300
stream = true
api_mode = "chat_completions"
```

Das `model = "gpt-4"` ist absichtlich kompatibel zu Bavarder/TKI. Der Space
routet es intern auf Qwen. Der Space erwartet inzwischen einen Bearer-Key; auf
diesem Host liegt `Telachat_API_Teladi` in
`~/.config/telachat/qwen.env` und wird per
`envfile:~/.config/telachat/qwen.env#TELACHAT_QWEN_API_KEY` referenziert.

Weitere Standardprofile:

- `chatgpt`: OpenAI/ChatGPT-Profil mit `env:OPENAI_API_KEY`, `gpt-5.5`, Responses API.
- `openai`: allgemeine OpenAI-API-Anbindung mit `env:OPENAI_API_KEY`, `gpt-5.4-mini`, Responses API.
- `huggingface`: dein Hugging-Face/Qwen-Space mit Qwen-Modellnamen.
- `codex`: lokaler Codex-CLI-Zugriff ueber `codex exec`, kein `/v1`-HTTP-Modell.

Fuer OpenAI/ChatGPT:

```sh
export OPENAI_API_KEY="..."
telachat ask -p openai "Hallo"
telachat ask -p chatgpt "Hallo"
```

Auf diesem Host liegt eine Telachat-eigene Kopie des Keys in
`~/.config/telachat/openai.env` und wird per
`envfile:~/.config/telachat/openai.env#OPENAI_API_KEY` referenziert.

Fuer Codex:

```sh
telachat ask -p codex "Erklaere kurz, was du bist."
```

## Weitere Provider

Beispiel fuer einen zweiten OpenAI-kompatiblen Endpunkt:

```toml
[profiles.local]
label = "Local"
base_url = "http://127.0.0.1:11434/v1"
api_key = "ollama"
model = "llama3.1"
stream = true
```

Beispiel mit Umgebungsvariable:

```toml
[profiles.openrouter]
label = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
api_key = "env:OPENROUTER_API_KEY"
model = "qwen/qwen-2.5-72b-instruct"
stream = true

[profiles.openrouter.headers]
HTTP-Referer = "https://local.telachat"
X-Title = "Telachat"
```

## Tests und Build

```sh
cd /home/teladi/telachat
make compile
make test3
make zipapp
```

`make test3` fuehrt die komplette Offline-Test-Suite dreimal aus. Die Tests
verwenden einen lokalen Fake-OpenAI-Server und brauchen keine externen Tokens.

Weitere Dokumentation:

- `docs/RESEARCH.md` - Recherche und Entscheidungen.
- `docs/ARCHITECTURE.md` - Aufbau, Datenmodell, Kommandos.
- `docs/TESTING.md` - Teststrategie und Live-Checks.
- `packaging/windows/README.md` - Windows-Build und Installer-Caveats.

## Sicherheit und Grenzen

- Telachat kauft keine Credits und fuehrt keine Provider-Aktionen aus.
- Der Verlauf liegt lokal in SQLite. Exportiere nur bewusst.
- `doctor --chat` sendet eine echte Testnachricht an das konfigurierte Profil.
- Streaming wird unterstuetzt. Wenn ein Backend nur einen kompletten Chunk
  liefert, zeigt Telachat trotzdem korrekt die Antwort an.
