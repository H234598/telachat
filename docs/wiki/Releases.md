# Releases

## 0.16.0 - 2026-05-25

- JSON-Ausgabe fuer `telachat doctor --json`.
- `doctor --json --chat` meldet Modelle und Chat-Check strukturiert.
- Regressionstest stellt sicher, dass aufgeloeste Env-Secrets nicht ausgegeben
  werden.

## 0.15.0 - 2026-05-25

- JSON-Ausgabe fuer `profiles`, `config-check`, `sessions` und `folders`.
- `config-check --json` bleibt redaktiert und gibt Secret-Status strukturiert
  aus.
- `folders --json` enthaelt Systemprompts nur mit `--show-system`.
- CLI-Tests pruefen JSON-Ausgabe und Secret-Redaction.

## 0.14.0 - 2026-05-25

- Neuer Befehl `telachat fork SESSION [--title TITLE]`.
- Neuer Slash-Befehl `/fork [TITLE]` fuer CLI, GTK und Tk.
- Forks kopieren Provider, Modell, Ordner, Systemprompt und Nachrichten in
  eine neue unabhaengige Session; der Fork ist nicht angeheftet.
- Tests pruefen Store, Controller, Command-Katalog, Top-Level-CLI und
  interaktiven Slash-Fork.

## 0.13.0 - 2026-05-25

- Neuer Slash-Befehl `/edit-last TEXT` mit Alias `/edit`.
- Ersetzt die letzte Nutzernachricht und entfernt danach liegende Antworten,
  damit `/regen` eine neue Antwort aus dem korrigierten Prompt erzeugt.
- Regressionstests fuer Store, Controller, Command-Katalog und interaktiven CLI.

## 0.12.1 - 2026-05-25

- Patch-Fix: `telachat theme NAME` schreibt nur noch Top-Level-Config und
  ueberschreibt kein gleichnamiges Feld in einem Profilblock.
- Regressionstest fuer Theme-Einfuegung vor `[profiles.*]`.

## 0.12.0 - 2026-05-25

- Zentrale Themes: `system`, `light`, `dark`, `high-contrast`.
- `theme = "..."` in `config.toml`; `TELACHAT_THEME` kann temporär
  uebersteuern.
- Neuer CLI-Befehl `telachat theme [NAME]`.
- GTK und Tk nutzen dieselbe Theme-Palette.
- Backup-Manifest und redaktierte Config enthalten das aktive Theme.
- Tests pruefen Theme-Parsing, Env-Override, CLI-Setzen und Controller-Persistenz.

## 0.11.0 - 2026-05-25

- Neue Befehle `telachat restore` und `telachat import-backup`.
- Backup-Historien werden additiv in die bestehende SQLite-Datenbank importiert.
- Bestehende Sessions werden nicht ueberschrieben; importierte Sessions
  bekommen neue IDs.
- Ordnerbeziehungen bleiben erhalten, gleichnamige Zielordner werden
  wiederverwendet.
- `--dry-run` zeigt vorab Ordner-, Session- und Nachrichtenanzahlen.
- Tests pruefen CLI-Import, Store-Import, ID-Neuschreibung und Ordner-Mapping.

## 0.10.0 - 2026-05-25

- Neuer Befehl `telachat backup` fuer lokale Backup-ZIP-Dateien.
- Nutzt die SQLite-Backup-API fuer eine konsistente `history.sqlite3`.
- Enthält `config.redacted.toml` und `manifest.json`, aber keine rohen
  Secret-Werte oder Envfiles.
- Redaktiert potentiell geheime Headerwerte und bleibt auch mit Bindestrich-
  Namen parsebares TOML.
- `-o DIR` und `-o FILE.zip` werden unterstuetzt.
- Tests pruefen ZIP-Inhalte und Secret-Redaction.

## 0.9.0 - 2026-05-25

- Neuer Offline-Befehl `telachat config-check` mit Alias `telachat config`.
- Prueft lokale Konfiguration, Profile, Modelle und Secret-Quellen ohne
  API-Anfrage.
- `--strict` liefert einen Fehlercode, wenn eine nicht-lokale Secret-Quelle
  fehlt.
- Tests stellen sicher, dass Envfile-Secret-Werte nicht ausgegeben werden.

## 0.8.0 - 2026-05-25

- Gespeicherte Chats merken sich jetzt das konkret verwendete Modell.
- SQLite-Migration fuer bestehende Sessions ohne Modell-Metadaten.
- GTK/Tk stellen Provider und Modell beim Laden eines Chats wieder her.
- `telachat chat --session` nutzt gespeicherte Session-Modelle, solange kein
  CLI-Override gesetzt ist.
- Sessionlisten, Suche und Markdown-Exporte enthalten Modell-Metadaten.

## 0.7.0 - 2026-05-25

- Readline-Tab-Completion fuer `telachat chat`.
- CLI vervollstaendigt Slash-Befehle, Provider, Modelle, Templates, Ordner,
  Session-Referenzen und Sortiermodi.
- Terminal-Slash-Commands wurden an den dokumentierten Katalog angeglichen.
- OpenAI-Profile koennen `reasoning_effort` setzen.
- Standard-OpenAI-Profil nutzt jetzt `gpt-5.5` mit
  `reasoning_effort = "high"`.

## 0.6.0 - 2026-05-25

- Gemeinsamer Slash-Command-Katalog fuer CLI, GTK und Tk.
- Autocomplete fuer Slash-Befehle in beiden GUIs.
- Neuer Slash-Befehl `/permissions` fuer Provider und redaktierte Secret-Quellen.
- Manpages `telachat(1)`, `telachat-tk(1)` und `telachat-gtk(1)`.
- `make install` installiert die Manpages lokal mit.
- TKI/Hugging-Face nutzt jetzt den echten Modellnamen
  `Qwen/Qwen2.5-1.5B-Instruct` statt des alten `gpt-4`-Alias.

## 0.5.0 - 2026-05-25

- Selektiver Ordnerexport mit `telachat export-folder FOLDER`.
- Verzeichnisexport mit `index.md` und einer Markdown-Datei pro Chat.
- Optionaler `--single-file` Export fuer ein gebuendeltes Markdown.

## 0.4.0 - 2026-05-25

- Ordner erhalten optionale Default-Systemprompts.
- Neuer CLI-Befehl `telachat folders`.
- `/folder-system TEXT` in CLI, GTK und Tk.
- GUI-Button `Ordner-Prompt` speichert den aktuellen Systemprompt im Ordner.
- SQLite-Migration fuer bestehende Ordnerdatenbanken.
- Redundanter `chatgpt`-Provider entfernt; `openai` bleibt fuer die OpenAI
  Responses API und GPT-5.x-Modelle.

## 0.3.0 - 2026-05-25

- Konfigurierbare Prompt-Templates in `[prompt_templates]`.
- Neuer CLI-Befehl `telachat templates`.
- `telachat ask --template NAME ...`.
- `/templates` und `/template NAME TEXT` in CLI, GTK und Tk.
- Template-Waehler in beiden GUIs.
- Tests fuer Konfiguration, Controller und CLI-Templatepfade.

## 0.2.0 - 2026-05-25

- Native GTK- und Tk-GUIs.
- Profile fuer TKI/Hugging Face, OpenAI und Codex.
- SQLite-Historie mit Ordnern, Suche, Sortierung und gepinnten Chats.
- Antwort-Regeneration ohne doppelte User-Nachricht.
- Einklappbare und breiteveraenderbare Seitenbereiche.
- `Shift+Enter` sendet Nachrichten.
- Windows-Paketierungsskripte fuer die Tk-Version.
