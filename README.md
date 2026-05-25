# Telachat

Telachat ist ein kleiner lokaler Chat-Client fuer OpenAI-kompatible KI-APIs.
Er ist auf dein `TKI`/Hugging-Face-Space-Profil voreingestellt, kann aber
weitere Provider ueber `config.toml` nutzen.

Aktuelle Version: `0.34.1`. Das Projekt nutzt Semantic Versioning; Details
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
telachat --version
telachat init
telachat models
telachat config-check
telachat config-check --json
telachat theme
telachat backup
telachat doctor --json
```

Der Wrapper wird nach `~/.local/bin/telachat` installiert, Manpages nach
`~/.local/share/man/man1`. Falls der Befehl in einer Shell nicht gefunden wird,
pruefe, ob `~/.local/bin` im `PATH` steht.

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
Ordnern abgelegt, mit Tags markiert, nach Datum/Titel/Provider sortiert und
ueber Titel, Provider, Tags oder Nachrichteninhalt gesucht werden. Wichtige
Chats koennen angeheftet werden; gepinnte Chats stehen in Listen zuerst.
Erledigte Chats koennen archiviert werden und verschwinden dann aus der
normalen Chatliste, bleiben aber ueber den sichtbaren Filter `Aktiv / Archiv /
Alle` ladbar. Tags haben ebenfalls einen sichtbaren Filter in der Seitenleiste,
inklusive aktueller Trefferzahl. Das pro Chat
verwendete Modell
wird gespeichert und beim Laden wieder in der Provider/Modell-Auswahl gesetzt.
Der GUI-Button `Check` fragt `/models` live fuer den gewaehlten Provider ab und
ergaenzt die Modellauswahl mit den gemeldeten IDs. Temperatur und maximale
Antworttokens koennen direkt im rechten Systembereich pro Anfrage gesetzt
werden.
Ordner koennen einen eigenen
Default-Systemprompt tragen, damit sie als kleine Projektkontexte funktionieren.

Im Texteingabefeld funktioniert auch eine kleine Kommandozeile:
`Shift+Enter` schickt die Nachricht ab, normales `Enter` bleibt fuer
Zeilenumbrueche. Beim Tippen von Slash-Befehlen zeigen GTK und Tk sofort
Vorschlaege; `Tab` vervollstaendigt den aktuellen Befehl.
Mit `/edit-last TEXT` wird die letzte Nutzernachricht ersetzt und die danach
liegende KI-Antwort entfernt; `/regen` erzeugt danach eine neue Antwort.
Mit `/fork [TITLE]` wird die aktuelle Unterhaltung als neuer Chat kopiert, so
dass Varianten ausprobiert werden koennen, ohne den Originalverlauf zu aendern.

```text
/help
/new
/rename TITLE
/delete
/pin
/unpin
/archive
/unarchive
/archives
/tag TAG [TAG...]
/untag TAG [TAG...]
/tags [SESSION]
/edit-last TEXT
/fork [TITLE]
/regen
/templates
/template NAME TEXT
/folder NAME
/folder-system TEXT
/rename-folder NAME
/delete-folder
/move NAME
/unfile
/sort newest|oldest|title|title-desc|provider
/search TEXT
/find TEXT
/provider NAME
/model NAME
/permissions
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
/archive
/unarchive
/archives
/tag TAG [TAG...]
/untag TAG [TAG...]
/tags [SESSION]
/edit-last TEXT
/fork [TITLE]
/regen
/templates
/template NAME TEXT
/folder-system TEXT
/profile [name]
/permissions
/system [prompt]
/history [n]
/export [datei.md]
/exit
```

Im interaktiven Terminal-Chat nutzt Telachat Readline-Completion: `Tab`
vervollstaendigt Slash-Befehle und passende Kontextwerte wie Profile, Modelle,
Templates, Ordner, Session-IDs, Session-Titel und Sortiermodi.
Fuer Skripte und Agenten liefern `profiles --json`, `models --json`,
`config-check --json`, `sessions --json`, `folders --json`, `export --json`,
`export-folder --json` und `doctor --json` strukturierte Daten;
Provider-/Secret-Konfiguration bleibt redaktiert.

GUI-Themes werden dauerhaft ueber `theme = "system"` in `config.toml`
gesteuert. Verfuegbar sind unter anderem `system`, `light`, `dark`,
`high-contrast`, `solarized-light`, `solarized-dark`, `nord`, `dracula`,
`gruvbox`, `ocean`, `forest` und `rose`. Temporär kann das Umfeld
uebersteuern, z.B. `TELACHAT_THEME=dark telachat-tk`. Wenn `theme = "system"`
aktiv ist, nutzt Telachat uebliche Desktop-/Terminal-Hinweise; mit
`TELACHAT_SYSTEM_THEME=solarized-dark` kann nur die System-Erkennung fuer einen
Prozess fixiert werden. Die GUIs haben zusaetzlich eine Theme-Auswahl im
Systembereich.

```sh
telachat theme
telachat theme dark
TELACHAT_THEME=high-contrast telachat-gtk
TELACHAT_SYSTEM_THEME=solarized-dark telachat-tk
```

Im interaktiven Chat kann das Theme ebenfalls gewechselt werden:

```text
/theme dracula
```

Gespeicherte Sessions koennen auch direkt in der CLI gefiltert werden:

```sh
telachat sessions --query projekt
telachat sessions --query gpt-5.5
telachat sessions --folder Arbeit
telachat sessions --tag projekt
telachat sessions --archived
telachat sessions --all
telachat sessions --sort title
telachat sessions --json
telachat archive SESSION_ID
telachat unarchive SESSION_ID
telachat tags SESSION_ID --add projekt --add review
telachat tags SESSION_ID --remove review
telachat tags --json
telachat fork SESSION_ID --title "Variante A"
telachat export SESSION_ID --json
telachat import-session session.json --folder Importe
telachat export-folder Arbeit -o ./arbeit-export
telachat export-folder Arbeit --single-file -o arbeit.md
telachat export-folder Arbeit --json -o arbeit.json
telachat export-folder Arbeit --all --json -o arbeit-alle.json
telachat import-folder arbeit.json --folder Importiert
telachat import-folder arbeit.json --dry-run --json
telachat backup -o ./backups
telachat backup -o telachat-backup.zip
telachat restore --dry-run telachat-backup.zip
telachat restore telachat-backup.zip
```

`backup` erzeugt ein ZIP mit konsistenter `history.sqlite3`, redaktierter
`config.redacted.toml` und `manifest.json`. Envfiles und rohe Secret-Werte
werden nicht in das Backup geschrieben; potentiell geheime Headerwerte werden
redaktiert.
`restore` importiert nur die Chat-Historie aus einem Telachat-Backup in die
bestehende SQLite-Datenbank. Bestehende Chats werden nicht ueberschrieben;
Sessions bekommen neue IDs. `--dry-run` zeigt vorher die Importmenge.

Ordner und ihre Projekt-Systemprompts lassen sich ebenfalls in der CLI
verwalten:

```sh
telachat folders
telachat folders --create Arbeit --system "Antworte knapp und projektbezogen."
telachat folders --set-system Arbeit "Nutze den Projektkontext."
telachat folders --show-system
telachat folders --json --show-system
```

Prompt-Templates kommen aus `[prompt_templates]` in `config.toml` und koennen
per CLI oder GUI eingesetzt werden:

```sh
telachat templates
telachat --version
telachat models
telachat models --live -p tki --json
telachat config-check
telachat config-check --strict
telachat config-check --profile tki --strict
telachat config-check --json
telachat doctor --json --chat
telachat ask --template summarize "Langer Text..."
```

`models` zeigt konfigurierte Modelle pro Profil; mit `--live -p PROFILE` fragt
es `/models` fuer ein Zielprofil ab. `config-check` prueft lokale Provider,
Modelle und Secret-Quellen ohne
Netzwerk/API-Anfrage. Secret-Werte werden nicht ausgegeben; `--strict` gibt
einen Fehlercode zurueck, wenn eine nicht-lokale Secret-Quelle fehlt.

Manpages:

```sh
man telachat
man telachat-tk
man telachat-gtk
```

## Voreingestelltes TKI-Profil

```toml
[profiles.tki]
label = "TKI"
base_url = "https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1"
api_key = "env:TELACHAT_QWEN_API_KEY"
model = "Qwen/Qwen2.5-1.5B-Instruct"
temperature = 0.2
top_p = 0.9
max_tokens = 512
timeout_seconds = 300
stream = true
api_mode = "chat_completions"
```

Das Modell wird mit seinem echten Qwen-Namen angesprochen. Der Space erwartet
inzwischen einen Bearer-Key; auf diesem Host liegt `Telachat_API_Teladi` in
`~/.config/telachat/qwen.env` und wird per
`envfile:~/.config/telachat/qwen.env#TELACHAT_QWEN_API_KEY` referenziert.

Weitere Standardprofile:

- `openai`: allgemeine OpenAI-API-Anbindung mit `env:OPENAI_API_KEY`, `gpt-5.5`, Responses API, `reasoning_effort = "high"` und GPT-5.x-Modelloptionen.
- `huggingface`: dein Hugging-Face/Qwen-Space mit Qwen-Modellnamen.
- `lmstudio`: lokaler LM-Studio-Server unter `http://localhost:1234/v1`, Modell-ID lokal anpassen.
- `ollama`: lokaler Ollama-OpenAI-Endpunkt unter `http://localhost:11434/v1`, Modell vorher mit Ollama bereitstellen.
- `jan`: lokaler Jan-API-Server unter `http://127.0.0.1:1337/v1`, API-Key ueber `TELACHAT_JAN_API_KEY`.
- `codex`: lokaler Codex-CLI-Zugriff ueber `codex exec`, kein `/v1`-HTTP-Modell.

Fuer OpenAI:

```sh
export OPENAI_API_KEY="..."
telachat ask -p openai "Hallo"
telachat ask -p openai --reasoning-effort high "Hallo"
```

Auf diesem Host liegt eine Telachat-eigene Kopie des Keys in
`~/.config/telachat/openai.env` und wird per
`envfile:~/.config/telachat/openai.env#OPENAI_API_KEY` referenziert.
Der fruehere `chatgpt`-Provider wurde entfernt, weil er dieselbe OpenAI
Responses API genutzt hat.

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
