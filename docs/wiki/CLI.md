# CLI

Telachat kann komplett aus dem Terminal genutzt werden.

## Basisbefehle

```sh
telachat init
telachat profiles
telachat config-check
telachat config-check --json
telachat theme
telachat templates
telachat folders
telachat doctor
telachat doctor --json --chat
telachat doctor --chat
telachat ask "Deine Frage"
telachat chat
telachat backup -o ./backups
telachat restore --dry-run ./backups/telachat-backup.zip
```

## Provider und Template

```sh
telachat ask -p tki "Hallo"
telachat ask -p openai -m gpt-5.5 --reasoning-effort high "Hallo"
telachat ask --template explain "SQLite WAL"
```

`telachat config-check` prueft lokale Profile, Modelle und Secret-Quellen ohne
API-Anfrage. `telachat config-check --strict` liefert einen Fehlercode, wenn
eine nicht-lokale Secret-Quelle fehlt.
`telachat theme [NAME]` zeigt oder setzt das persistente GUI-Theme. Fuer
temporäre Starts kann `TELACHAT_THEME=dark telachat-tk` genutzt werden. Bei
`theme = "system"` kann `TELACHAT_SYSTEM_THEME=solarized-dark` nur die
System-Erkennung fuer einen Prozess fixieren. Im interaktiven Chat funktioniert
derselbe Wechsel mit `/theme NAME`.
`telachat backup` schreibt ein ZIP mit SQLite-Historie, redaktierter Config und
Manifest; rohe Secrets und Envfiles bleiben draussen.
`telachat restore` importiert die Backup-Historie additiv in die bestehende
SQLite-Datenbank. Mit `--dry-run` wird nur gezaehlt.
`profiles --json`, `config-check --json`, `sessions --json`, `folders --json`
und `doctor --json` liefern strukturierte, redaktierte Daten fuer Skripte und
Agenten.

## Sessions

```sh
telachat sessions
telachat sessions --query TEXT
telachat sessions --query gpt-5.5
telachat sessions --folder NAME
telachat sessions --sort newest
telachat sessions --json
telachat fork SESSION_ID --title "Variante A"
telachat folders --create Projekt --system "Projektkontext"
telachat folders --set-system Projekt "Neuer Projektkontext"
telachat folders --show-system
telachat folders --json --show-system
telachat export SESSION_ID
telachat export-folder Projekt -o ./projekt-export
telachat export-folder Projekt --single-file -o projekt.md
```

## Interaktive Slash-Commands

Im interaktiven Chat funktionieren unter anderem:

```text
/new
/rename TITLE
/delete
/pin
/unpin
/edit-last TEXT
/fork [TITLE]
/regen
/folder NAME
/move NAME
/unfile
/sort newest
/search TEXT
/provider NAME
/model NAME
/permissions
/templates
/template NAME TEXT
/folder-system TEXT
```

Wenn `telachat chat` in einem echten Terminal laeuft, vervollstaendigt `Tab`
Slash-Befehle und Kontextwerte wie Provider, Modelle, Templates, Ordner,
Session-Referenzen und Sortiermodi.
`/edit-last TEXT` ersetzt die letzte Nutzernachricht, entfernt danach liegende
Antworten und laesst dich mit `/regen` neu generieren.
`/fork [TITLE]` kopiert den aktuellen Chat in eine neue Session und laedt diese
direkt, damit du Varianten ausprobieren kannst.
Gespeicherte Chats merken sich Provider und Modell; `telachat chat --session`
nutzt diese Werte, solange du sie nicht per CLI-Option ueberschreibst.
