# Telachat

Telachat ist ein kleiner lokaler Chat-Client fuer OpenAI-kompatible KI-APIs.
Er ist auf dein `TKI`/Hugging-Face-Space-Profil voreingestellt, kann aber
weitere Provider ueber `config.toml` nutzen.

Aktuelle Version: `0.68.0`. Das Projekt nutzt Semantic Versioning; Details
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
make zipapp
packaging/linux/install-telachat.sh --prefix "$HOME/.local"
telachat --version
telachat init
telachat models
telachat config-check
telachat config-check --json
telachat config-check --show-redacted
telachat theme
telachat stats
telachat context <session-id>
telachat backup
telachat doctor --json
```

Der Linux-Installer installiert das Zipapp nach `~/.local/lib/telachat`, die
Starter nach `~/.local/bin`, Manpages nach `~/.local/share/man/man1`, einen
Freedesktop-Menueintrag, das Icon und eine Desktop-Verknuepfung. Falls der
Befehl in einer Shell nicht gefunden wird, pruefe, ob `~/.local/bin` im `PATH`
steht. Fuer einfache Quellcheckout-Installationen funktioniert weiterhin
`make install`; fuer Release-Artefakte sind `make linux-installer` und
`make linux-rpm` vorgesehen. Fuer lokale Installer-Pruefungen nutzt
`make linux-installer-smoke` ein temporaeres Ziel und schreibt keine
Verknuepfung auf den echten Desktop.

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
werden. Nach Antworten zeigen beide GUIs die gemessene Antwortzeit im Status
und, wenn der Provider Usage-Daten liefert, Input-/Output-/Total-Tokens. Der
Kopier-Button in der Chat-Kopfzeile kopiert die letzte KI-Antwort in die
Zwischenablage.
Laufende GUI-Anfragen koennen mit `Abbrechen` verworfen werden; Telachat macht
die Oberflaeche wieder bedienbar und ignoriert spaete Antworten oder Fehler,
kann den bereits gestarteten Provider-Request aber nicht garantiert serverseitig
stoppen. Bei abgebrochenen Send-Anfragen wird der abgeschickte Prompt wieder in
den Composer gesetzt, solange dort noch nichts Neues steht.
Ordner koennen einen eigenen Default-Systemprompt und ein Default-Backend aus
Provider/Modell tragen, damit sie als kleine Projektkontexte funktionieren.

Im Texteingabefeld funktioniert auch eine kleine Kommandozeile:
`Shift+Enter` schickt die Nachricht ab, normales `Enter` bleibt fuer
Zeilenumbrueche. Beim Tippen von Slash-Befehlen zeigen GTK und Tk sofort
Vorschlaege; `Tab` vervollstaendigt den aktuellen Befehl oder passende Werte
wie Provider, Modelle, Templates, Themes, Ordner, Tags und Sortierungen.
Mit `/shortcuts` oder `Ctrl+/` zeigt Telachat die wichtigsten Tastenkuerzel.
Mit `/edit-last TEXT` wird die letzte Nutzernachricht ersetzt und die danach
liegende KI-Antwort entfernt; `/regen` erzeugt danach eine neue Antwort.
Mit `/fork [TITLE]` wird die aktuelle Unterhaltung als neuer Chat kopiert, so
dass Varianten ausprobiert werden koennen, ohne den Originalverlauf zu aendern.

```text
/help
/shortcuts
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
/stats
/context
/doctor
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
/models [live]
/permissions
/left
/system
/exit
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
/stats
/context
/doctor
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
`/context` zeigt content-frei, wie gross der aktuell geladene Chat fuer den
naechsten Request grob wird: gespeicherte/gesendete Nachrichten, Zeichenumfang
und eine einfache Tokenschaetzung.

Fuer Skripte und Agenten liefern `profiles --json`, `models --json`,
`config-check --json`, `sessions --json`, `stats --json`, `context --json`,
`templates --json`, `folders --json`, `ask --json`, `export --json`,
`export-folder --json` und `doctor --json` strukturierte Daten;
Provider-/Secret-Konfiguration bleibt redaktiert.
Wenn Provider Usage-Daten melden, speichert Telachat diese an Assistant-
Nachrichten und `stats` fasst Input-/Output-/Total-Tokens content-frei zusammen.

GUI-Optionen werden dauerhaft im Kopf von `config.toml` gespeichert:
`theme`, `app_icon`, `chat_background_image`, `validate_profile_headers` und
`skill_watchdog_enabled`. Tk hat dafuer ein echtes Menue
`Optionen -> Einstellungen...`; GTK hat eine Preferences-Schaltflaeche in der
Titelleiste. Verfuegbare Themes sind unter anderem `system`, `light`, `dark`,
`high-contrast`, `solarized-light`, `solarized-dark`, `nord`, `dracula`,
`gruvbox`, `ocean`, `forest`, `rose`, `graphite-glass`, `liquid-chrome`,
`black-ice` und `brushed-steel`. Temporär kann das Umfeld
uebersteuern, z.B. `TELACHAT_THEME=dark telachat-tk`. Wenn `theme = "system"`
aktiv ist, nutzt Telachat uebliche Desktop-/Terminal-Hinweise; mit
`TELACHAT_SYSTEM_THEME=solarized-dark` kann nur die System-Erkennung fuer einen
Prozess fixiert werden. `app_icon = "random"` waehlt sofort ein importiertes
Icon und rotiert danach stuendlich. `chat_background_image` speichert einen
lokalen Bildpfad fuer das Chatmodul.

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
telachat stats
telachat stats --json
telachat archive SESSION_ID
telachat unarchive SESSION_ID
telachat tags SESSION_ID --add projekt --add review
telachat tags SESSION_ID --remove review
telachat tags --json
telachat fork SESSION_ID --title "Variante A"
telachat ask --json "Kurze Antwort bitte"
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

In der Tk-GUI zeigt die linke Chatliste Ordner als aufklappbare Zeilen.
Doppelklick klappt einen Ordner auf oder zu; Rechtsklick oeffnet Aktionen fuer
Chat, Ordner oder freien Listenraum. Der Neu-Befehl fragt vor dem Anlegen nach
dem Namen der Unterhaltung.

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
telachat folders --set-backend Arbeit huggingface TKI
telachat folders --clear-backend Arbeit
telachat folders --show-system
telachat folders --json --show-system
```

Prompt-Templates kommen aus `[prompt_templates]` in `config.toml` und koennen
per CLI oder GUI eingesetzt und verwaltet werden. Unterstuetzte Platzhalter
sind `{input}`, `{date}`, `{time}` und `{datetime}`. Weitere Platzhalter wie
`{topic}` werden als Custom-Variablen erkannt und koennen in der CLI mit
`--template-var NAME=VALUE` gefuellt werden. In Tk und GTK fragt Telachat
Custom-Variablen beim Einsetzen eines Templates per Dialog ab. Innerhalb einer
laufenden GUI-Sitzung merkt Telachat die zuletzt eingesetzten Werte pro Vorlage
und fuellt den naechsten Dialog damit vor.
In der GUI kann der aktuelle Composer-Text direkt als Template gespeichert
werden; Tk nutzt dafuer das Kontextmenue der Vorlagen-Auswahl, GTK den
`Speichern`-Button unter der Vorlagen-Auswahl. Beide GUIs koennen Templates
vor dem Einsetzen in einem kopierbaren Vorschaufenster mit Name, Laenge und
erkannten Variablen anzeigen.

```sh
telachat templates
telachat templates --json
telachat templates --show brief
telachat ask --template brief --template-var topic=Login "Fehlertext"
telachat templates --set brief "Kurz antworten: {input}"
telachat templates --rename brief kurz
telachat templates --delete kurz
telachat --version
telachat models
telachat models --live -p huggingface --json
telachat config-check
telachat config-check --strict
telachat config-check --profile huggingface --strict
telachat config-check --json
telachat config-check --show-redacted
telachat stats --json
telachat doctor --json --chat
telachat skill-watchdog --json
telachat ask --template summarize "Langer Text..."
```

`models` zeigt konfigurierte Modelle pro Profil; mit `--live -p PROFILE` fragt
es `/models` fuer ein Zielprofil ab. `config-check` prueft lokale Provider,
Modelle und Secret-Quellen ohne
Netzwerk/API-Anfrage und zeigt den Status der globalen Profil-Header-Pruefung.
Secret-Werte werden nicht ausgegeben; `--strict` gibt einen Fehlercode zurueck,
wenn eine nicht-lokale Secret-Quelle fehlt. `--show-redacted` gibt die aktive
Konfiguration als redaktierte TOML-Ansicht aus, ohne rohe API-Keys oder
Auth-Header offenzulegen.
`skill-watchdog` kuerzt ueberlange Codex-Skill-Frontmatter-`description`-
Felder auf Loader-kompatible Laenge, legt Backups als
`SKILL.md.telachat-watchdog.bak` an und laesst den Skill-Body erhalten. Tk/GTK
starten den Lauf nur mit `skill_watchdog_enabled = true`; neue
Konfigurationen bleiben sicher aus. `TELACHAT_DISABLE_SKILL_WATCHDOG=1`
deaktiviert ihn auch dann.

Manpages:

```sh
man telachat
man telachat-tk
man telachat-gtk
```

## Voreingestelltes HuggingFace-Profil

```toml
[profiles.huggingface]
label = "HuggingFace"
base_url = "https://haggfraise-qwen2-5-1-5b-instruct-free.hf.space/v1"
api_key = "env:TELACHAT_QWEN_API_KEY"
model = "TKI"
models = ["TKI", "Qwen/Qwen2.5-1.5B-Instruct", "qwen2-5-1-5b-instruct-free"]
temperature = 0.2
top_p = 0.9
max_tokens = 512
timeout_seconds = 300
stream = true
api_mode = "chat_completions"

[profiles.huggingface.model_aliases]
TKI = "Qwen/Qwen2.5-1.5B-Instruct"
```

Der sichtbare Modellname `TKI` wird intern auf die echte Qwen-ID gemappt. Der
Space erwartet inzwischen einen Bearer-Key; auf diesem Host liegt der lokale Wert in
`~/.config/telachat/qwen.env` und wird per
`envfile:~/.config/telachat/qwen.env#TELACHAT_QWEN_API_KEY` referenziert.

Weitere Standardprofile:

- `huggingface`: dein Hugging-Face/Qwen-Space; alte `tki`-Referenzen werden als Kompatibilitaetsalias auf dieses Profil aufgeloest.
- `openai`: allgemeine OpenAI-API-Anbindung mit `env:OPENAI_API_KEY`, `gpt-5.5`, Responses API, `reasoning_effort = "high"` und GPT-5.x-Modelloptionen. Sampling-Parameter werden standardmaessig nicht gesendet, weil GPT-5.x-Responses-Modelle `temperature` je nach Modell nicht akzeptieren.
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

Telachat prueft Headernamen und Headerwerte standardmaessig vor dem Senden.
Fuer absichtlich ungewoehnliche Provider kann die strikte Standard-HTTP-
Pruefung global in `config.toml` oder in den GUI-Einstellungen abgeschaltet
werden. Grundlegende Sicherheitschecks gegen Steuerzeichen in Headerwerten
und nicht-portable oder parser-gefaehrliche Headernamen bleiben aktiv:

```toml
validate_profile_headers = false
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


![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/H234598/telachat?utm_source=oss&utm_medium=github&utm_campaign=H234598%2Ftelachat&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
