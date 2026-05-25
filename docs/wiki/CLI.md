# CLI

Telachat kann komplett aus dem Terminal genutzt werden.

## Basisbefehle

```sh
telachat init
telachat profiles
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
telachat ask -p openai -m gpt-5.4-mini "Hallo"
telachat ask --template explain "SQLite WAL"
```

## Sessions

```sh
telachat sessions
telachat sessions --query TEXT
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
