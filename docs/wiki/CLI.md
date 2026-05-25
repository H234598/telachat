# CLI

Telachat kann komplett aus dem Terminal genutzt werden.

## Basisbefehle

```sh
telachat --version
telachat init
telachat profiles
telachat models
telachat models --live -p tki --json
telachat config-check
telachat config-check --profile tki --strict
telachat config-check --json
telachat theme
telachat templates
telachat folders
telachat stats
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

`telachat models` zeigt konfigurierte Modelle pro Profil. Mit
`telachat models --live -p PROFILE` wird `/models` fuer genau ein Zielprofil
abgefragt. `telachat config-check` prueft lokale Profile, Modelle und
Secret-Quellen ohne API-Anfrage. `telachat config-check --strict` liefert einen
Fehlercode, wenn eine nicht-lokale Secret-Quelle fehlt.
`telachat theme [NAME]` zeigt oder setzt das persistente GUI-Theme. Fuer
temporäre Starts kann `TELACHAT_THEME=dark telachat-tk` genutzt werden. Bei
`theme = "system"` kann `TELACHAT_SYSTEM_THEME=solarized-dark` nur die
System-Erkennung fuer einen Prozess fixieren. Im interaktiven Chat funktioniert
derselbe Wechsel mit `/theme NAME`.
`telachat backup` schreibt ein ZIP mit SQLite-Historie, redaktierter Config und
Manifest; rohe Secrets und Envfiles bleiben draussen.
`telachat restore` importiert die Backup-Historie additiv in die bestehende
SQLite-Datenbank. Mit `--dry-run` wird nur gezaehlt.
`profiles --json`, `models --json`, `config-check --json`, `sessions --json`,
`stats --json`, `context --json`, `templates --json`, `folders --json`,
`export --json`, `export-folder --json` und `doctor --json` liefern
strukturierte Daten fuer Skripte und Agenten; Provider-/Secret-Konfiguration
bleibt redaktiert.

## Sessions

```sh
telachat sessions
telachat sessions --query TEXT
telachat sessions --query gpt-5.5
telachat sessions --folder NAME
telachat sessions --tag TAG
telachat sessions --archived
telachat sessions --all
telachat sessions --sort newest
telachat sessions --json
telachat stats
telachat stats --json
telachat context SESSION_ID
telachat context SESSION_ID --json
telachat templates --json
telachat archive SESSION_ID
telachat unarchive SESSION_ID
telachat tags
telachat tags SESSION_ID --add projekt --add review
telachat tags SESSION_ID --remove review
telachat tags SESSION_ID --set projekt inbox
telachat tags SESSION_ID --clear
telachat tags --json
telachat fork SESSION_ID --title "Variante A"
telachat folders --create Projekt --system "Projektkontext"
telachat folders --set-system Projekt "Neuer Projektkontext"
telachat folders --set-backend Projekt tki Qwen/Qwen2.5-1.5B-Instruct
telachat folders --clear-backend Projekt
telachat folders --show-system
telachat folders --json --show-system
telachat export SESSION_ID
telachat export SESSION_ID --json
telachat import-session session.json --folder Importe
telachat export-folder Projekt -o ./projekt-export
telachat export-folder Projekt --single-file -o projekt.md
telachat export-folder Projekt --json -o projekt.json
telachat export-folder Projekt --all --json -o projekt-alle.json
telachat import-folder projekt.json --folder Importiert
telachat import-folder projekt.json --dry-run --json
```

## Interaktive Slash-Commands

Im interaktiven Chat funktionieren unter anderem:

```text
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
/folder NAME
/move NAME
/unfile
/sort newest
/search TEXT
/find TEXT
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
`/tag`, `/untag` und `/tags` verwalten flexible Chat-Gruppen ohne die
Ordnerstruktur zu veraendern.
`/archive` blendet den aktuellen Chat aus den normalen Listen aus,
`/unarchive` holt ihn zurueck, und `/archives` zeigt archivierte Chats.
GTK und Tk bieten denselben Archivwechsel sichtbar als `Aktiv / Archiv / Alle`
in der Seitenleiste an. Daneben gibt es einen sichtbaren Tagfilter mit
aktuellen Zaehlern.
Gespeicherte Chats merken sich Provider und Modell; `telachat chat --session`
nutzt diese Werte, solange du sie nicht per CLI-Option ueberschreibst.
