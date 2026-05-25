# CLI

Telachat kann komplett aus dem Terminal genutzt werden.

## Basisbefehle

```sh
telachat init
telachat profiles
telachat config-check
telachat templates
telachat folders
telachat doctor
telachat doctor --chat
telachat ask "Deine Frage"
telachat chat
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

## Sessions

```sh
telachat sessions
telachat sessions --query TEXT
telachat sessions --query gpt-5.5
telachat sessions --folder NAME
telachat sessions --sort newest
telachat folders --create Projekt --system "Projektkontext"
telachat folders --set-system Projekt "Neuer Projektkontext"
telachat folders --show-system
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
Gespeicherte Chats merken sich Provider und Modell; `telachat chat --session`
nutzt diese Werte, solange du sie nicht per CLI-Option ueberschreibst.
