# Releases

## Unreleased

## 0.54.2 - 2026-05-26

- Macht die RPM-Build-Verzeichnisanlage POSIX-sh-kompatibel, damit
  Ubuntu/dash-CI-Runner den erwarteten `dist/rpm/SOURCES`-Baum erzeugen.

## 0.54.1 - 2026-05-26

- Macht RPM-Builds auf Nicht-RPM-CI-Hosts robuster, indem das Build-Script
  RPM-Datenbank-Abhaengigkeitspruefungen ueberspringt, die Spec-Metadaten aber
  beibehaelt.
- Verbessert den Linux-Packaging-Test, damit entfernte RPM-Buildfehler stdout
  und stderr anzeigen.

## 0.54.0 - 2026-05-26

- Ergaenzt einen Linux-Installer, der Zipapp, Starter, Manpages,
  Freedesktop-Desktopdatei, Icon und optionale Desktop-Verknuepfung unter einem
  waehlbaren Prefix installiert.
- Ergaenzt RPM-Paketbau und einen periodischen Linux-Release-Packaging-Workflow.
- Ergaenzt eine Snapcraft-Datei fuer optionale Snap-Builds, falls Snapcraft im
  Build-Umfeld verfuegbar ist.

## 0.53.1 - 2026-05-26

- Stellt den sicheren Opt-in-Default fuer den Skill-Watchdog nach der
  Regression in `0.53.0` wieder her.
- Sichert den Low-Level-Hintergrundstart wieder ueber
  `TELACHAT_ENABLE_SKILL_WATCHDOG=1`, damit Tests und GUI-Starts keine
  externen Codex-Skill-Dateien ohne explizite Aktivierung veraendern.

## 0.53.0 - 2026-05-26

- Ergaenzt in Tk eine Ordner-/Chat-Exploreransicht mit aufklappbaren
  Ordnerzeilen.
- Fuegt ein Tk-Rechtsklickmenue fuer Chat-, Ordner- und Leerraumaktionen hinzu.
- Laesst Tk und GTK beim Neu-Anlegen zuerst den Unterhaltungsnamen abfragen.
- Fuegt die Skill-Watchdog-Option in den neuen Tk/GTK-Einstellungen hinzu.

## 0.52.1 - 2026-05-26

- Stellt temporaer den sicheren Skill-Watchdog-Default wieder her: neue
  Konfigurationen bleiben aus, bis `skill_watchdog_enabled = true` gesetzt wird.
- Macht die Default-Konfiguration wieder mit Python 3.11 kompatibel.

## 0.52.0 - 2026-05-26

- Ergaenzt ein echtes Tk-Optionsmenue und ein GTK-Preferences-Fenster fuer
  persistente GUI-Einstellungen.
- Speichert `app_icon`, `chat_background_image` und `skill_watchdog_enabled`
  in `config.toml`.
- Importiert die bereitgestellten SVG-Icons, liefert PNG-Renderings mit und
  ergaenzt einen stuendlich rotierenden Zufallsmodus.
- Haelt den Skill-Watchdog in Tk/GTK standardmaessig aktiv, aber abschaltbar
  ueber GUI, `config.toml` oder `TELACHAT_DISABLE_SKILL_WATCHDOG=1`.

## 0.51.1 - 2026-05-26

- Korrigiert die Skill-Watchdog-Dokumentation, damit sie zum implementierten
  Default-Start in Tk/GTK passt.

## 0.51.0 - 2026-05-26

- Erweitert den GUI-Theme-Katalog um metallisch/glaeserne Paletten:
  `graphite-glass`, `liquid-chrome`, `black-ice` und `brushed-steel`.
- Startet den Tk/GTK-Skill-Watchdog standardmaessig; abschaltbar bleibt er mit
  `TELACHAT_DISABLE_SKILL_WATCHDOG=1`.

## 0.50.0 - 2026-05-26

- Ergaenzt `telachat skill-watchdog` plus Tk/GTK-Startwatchdog, der
  ueberlange Codex-Skill-Frontmatter-Descriptions kuerzt, aber den Skill-Body
  erhaelt.

## 0.49.0 - 2026-05-26

- Entfernt den doppelten Default-Provider `tki`; alte Referenzen werden weiter
  als Alias auf `huggingface` aufgeloest.
- Zeigt im HuggingFace-Profil den Modellalias `TKI`, sendet intern aber weiter
  die echte Qwen-Modell-ID.
- Profile koennen `temperature` und `top_p` aus API-Requests weglassen; das
  OpenAI-Responses-Profil deaktiviert beide standardmaessig fuer GPT-5.x-
  Kompatibilitaet.
- Haertet das Windows-Packaging gegen unbrauchbare Microsoft-Store-Python-
  Aliasse und ergaenzt ein wiederverwendbares Windows-Testskript.
- Erzeugt versionierte portable Windows-ZIP- und NSIS-Installer-Artefakte mit
  SHA256-Sidecars.
- Deckt Windows-CI-Packaging und Release-Upload-Validierung ohne direkte
  Wildcard-Uploads ab.
- Haelt Windows-Pfadtests mit escape-aehnlichen Sequenzen in temporaeren
  Verzeichnissen.

## 0.48.1 - 2026-05-25

- Ergaenzt direkte GUI-Regression-Coverage fuer `/models` und `/models live`
  in Tk und GTK.
- Validiert konfigurierte Profil-Headernamen und -Werte, bevor sie mit
  API-Requests gesendet werden.
- Ergaenzt die persistente Option `validate_profile_headers` plus Tk/GTK-
  Einstellungen, um die strikte Standard-Headernamen-Pruefung fuer bewusst
  ungewoehnliche Provider abzuschalten; Steuerzeichen bleiben abgelehnt.

## 0.48.0 - 2026-05-25

- Ergaenzt `/models [live]` im gemeinsamen Slash-Katalog, im CLI-Chat und in
  beiden Desktop-Frontends.
- Zeigt ohne Netzaufruf die konfigurierten Modelle des aktiven Providers oder
  startet mit `/models live` den bestehenden Live-Modellcheck.
- Ergaenzt Completion- und Regression-Coverage fuer den neuen interaktiven
  Modellbefehl.
- Enthaelt direkte Korrektur-Coverage, damit der Release-Upload-Guard auch
  PowerShell-Fortsetzungszeilen verfolgt.

## 0.47.5 - 2026-05-25

- Ignoriert negative Token-Usage-Werte beim Formatieren und Persistieren von
  Provider-Metadaten.
- Behaelt valide Nullwerte in strukturierten Usage-Records, ohne irrefuehrende
  Textausgabe fuer leere Detailwerte zu erzeugen.
- Ergaenzt Regression-Coverage fuer ungueltige Usage-Metadaten in lokalen
  Statistiken und Client-Formatierung.

## 0.47.4 - 2026-05-25

- Gibt aus `ChatStore.add_message()` eine gespeicherte Metadata-Kopie zurueck,
  damit spaetere Dict-Mutationen am Aufruferobjekt den Message-Zustand nicht
  nachtraeglich veraendern.
- Ergaenzt Regression-Coverage, dass gespeicherte Message-Metadaten gegen
  Mutationen an Eingabe- und Rueckgabe-Dicts isoliert bleiben.

## 0.47.3 - 2026-05-25

- Ergaenzt Regression-Coverage, dass Assistant-Usage-Metadaten beim Forken von
  Sessions erhalten bleiben.
- Ergaenzt Regression-Coverage, dass additive History-Imports Usage-Metadaten
  aus bestehenden SQLite-Historien erhalten.
- Ergaenzt Regression-Coverage, dass geloeschte Assistant-Nachrichten ihre
  Usage-Metadaten im Rueckgabewert behalten.

## 0.47.2 - 2026-05-25

- Ergaenzt einen Workflow-Regressionstest, der rohe Wildcards direkt in
  `gh release upload`-Kommandos verhindert.
- Sichert damit den bei Windows-Packaging-PRs gefundenen Release-Upload-
  Blocker dauerhaft ab.

## 0.47.1 - 2026-05-25

- Ergaenzt eine Legacy-SQLite-Migration fuer sehr alte `messages`-Tabellen ohne
  `metadata`-Spalte.
- Deckt die Migration mit einem Regressionstest ab, damit Usage-Metadaten auch
  auf alten Historien sicher gespeichert werden koennen.

## 0.47.0 - 2026-05-25

- Speichert Provider-Token-Usage an Assistant-Nachrichten, wenn der Provider
  Usage-Daten meldet.
- `telachat stats` und `stats --json` aggregieren gespeicherte Input-/Output-/
  Total-Tokens content-frei.

## 0.46.0 - 2026-05-25

- Prompt-Templates unterstuetzen jetzt `{date}`, `{time}` und `{datetime}`
  zusaetzlich zu `{input}`.
- `telachat templates --json` meldet die verwendeten eingebauten Variablen pro
  Template.

## 0.45.1 - 2026-05-25

- Ergaenzt Regression-Coverage fuer `telachat ask --json --save`: die Session
  wird gespeichert, `saved_session_id` wird ausgegeben, und stderr bleibt ruhig.

## 0.45.0 - 2026-05-25

- `telachat ask --json` gibt One-Shot-Antworten maschinenlesbar mit Provider,
  Modell und verfuegbaren Usage-Metadaten aus.
- Tracked-Source-Secret-Hygiene wird nun ueber einen Regressionstest bewacht.

## 0.44.0 - 2026-05-25

- Zeigt Provider-Usage-Daten aus Chat-Completions- und Responses-Antworten in
  der GUI-Statuszeile und in `doctor --json --chat`, wenn der Provider sie
  liefert.
- Dokumentierte lokale Key-Namen sind weiter entschaerft; Secret-Source-Parsing
  hat zusaetzliche Regression-Coverage.

## 0.43.11 - 2026-05-25

- Ergaenzt GTK/Tk-Regressionstests, die sicherstellen, dass die Modellliste
  nach einem erfolgreichen GUI-Check aus Live-`/models`-Daten aktualisiert wird.

## 0.43.10 - 2026-05-25

- Ergaenzt gezielte Regressionstests fuer Windows-artige Secret-Pfade mit
  TOML-Escape-aehnlichen Backslashes.

## 0.43.9 - 2026-05-25

- Die Konfigurationsvalidierung nutzt jetzt dieselben sinnvollen
  Generierungsbereiche wie die GUI fuer `temperature` und `top_p`.
- `make check` kompiliert jetzt auch die Packaging-Hilfsmodule.

## 0.43.8 - 2026-05-25

- Numerische Konfigurationswerte und per Request gesetzte Generierungswerte
  werden jetzt mit klaren `ConfigError`-Meldungen validiert.

## 0.43.7 - 2026-05-25

- Windows-artige `file:`- und `envfile:`-Secret-Quellen behalten rohe
  UNC-Praefixe wie `\\server\share` bei.

## 0.43.6 - 2026-05-25

- `file:`- und `envfile:`-Secret-Quellen behalten rohe Windows-Backslashes in
  TOML-Basic-Strings bei.

## 0.43.5 - 2026-05-25

- GTK/Tk wenden ein Ordner-Default-Modell nicht mehr an, wenn das zugehoerige
  Default-Profil lokal nicht konfiguriert ist.

## 0.43.4 - 2026-05-25

- Controller-seitig angelegte Ordner pruefen Default-Provider/-Modell jetzt
  vor dem Speichern.

## 0.43.3 - 2026-05-25

- Markdown-Exports beschriften gespeicherte `system`-Nachrichten jetzt als
  `System`, statt jede Nicht-User-Rolle als Assistant zu behandeln.

## 0.43.2 - 2026-05-25

- Nicht lesbare `file:`- und `envfile:`-Secretquellen werden jetzt als
  `ConfigError` mit kompakter Meldung ausgegeben.
- Regressionstests decken fehlende Secret-Dateien ab.

## 0.43.1 - 2026-05-25

- Interaktive Chat-Sends bleiben nach Secret-/Envfile-Fehlern im Chat statt
  die Sitzung zu beenden.
- Normale Chat-Sends und `/template` melden `ApiError`, `ConfigError` und
  `OSError` kompakt im Prompt.

## 0.43.0 - 2026-05-25

- Ordner koennen jetzt optional Default-Provider und Default-Modell speichern.
- `telachat folders --set-backend FOLDER PROFILE [MODEL]`,
  `--clear-backend FOLDER` sowie `--profile/--model` bei `--create` verwalten
  diese Defaults.
- Controller, GTK und Tk wenden Ordner-Backends fuer neue Chats an.
- Folder-JSON-Export/-Import und Backup-History-Restore erhalten die
  Backend-Defaults.

## 0.42.1 - 2026-05-25

- Wenn eine laufende Send-Anfrage abgebrochen wird, setzen GTK und Tk den
  gerade abgeschickten Prompt wieder in den Composer, solange dort noch nichts
  Neues steht.
- Gespeicherte Prompt-Drafts werden auch bei spaeten abgebrochenen oder
  veralteten Worker-Ergebnissen aufgeraeumt.

## 0.42.0 - 2026-05-25

- GTK und Tk zeigen waehrend Senden, Regenerieren oder Check einen
  `Abbrechen`-Knopf.
- Abgebrochene GUI-Operationen geben die Oberflaeche sofort frei; spaete
  Worker-Ergebnisse werden ignoriert, damit keine alte Antwort oder kein alter
  Fehlerdialog den aktuellen Chat ueberschreibt.
- Tests decken die Cancel-Guards fuer beide GUI-Frontends ab.

## 0.41.0 - 2026-05-25

- `telachat templates --json` liefert eine strukturierte Prompt-Template-
  Inventur mit Name, Preview, Zeilen-/Zeichenzahl und `{input}`-Marker.

## 0.40.0 - 2026-05-25

- Neuer content-freier Kontextumfang: `telachat context SESSION` und
  `/context` zeigen Nachrichtenzaehler, Zeichenumfang und grobe Tokenschaetzung
  fuer den naechsten Request.
- Tests decken CLI, Tk, GTK und gemeinsame Formatierung ab.

## 0.39.2 - 2026-05-25

- Tests pruefen jetzt fuer jeden deklarierten Slash-Alias die Aufloesung auf
  das kanonische Kommando.

## 0.39.1 - 2026-05-25

- Tests decken jetzt auch die Tk- und GTK-Normalisierung fuer
  `/regenerate` ueber den gemeinsamen Command-Katalog ab.

## 0.39.0 - 2026-05-25

- Tk und GTK normalisieren Slash-Aliase jetzt ueber den gemeinsamen
  Command-Katalog.
- `/exit`, `/quit` und `/q` schliessen das jeweilige GUI-Fenster.
- Tests decken Tk- und GTK-Exit-Aliase ab.

## 0.38.2 - 2026-05-25

- Profile mit ungueltigem `stream` oder `api_mode` werden jetzt beim Laden der
  Konfiguration abgewiesen.
- Ergaenzt Regressionstests fuer ungueltige Profil-Booleans und API-Modi.

## 0.38.1 - 2026-05-25

- `/doctor` beendet den interaktiven Chat nicht mehr, wenn lokale
  Secret-Quellen oder OS-Zugriffe fehlschlagen.
- Ergaenzt Regressionstests fuer fehlende Envfile-Fehler im Terminal-Chat.

## 0.38.0 - 2026-05-25

- `/doctor` funktioniert jetzt im interaktiven CLI-Prompt sowie in Tk und GTK.
- Die GUI nutzt dabei denselben Check wie der vorhandene Check-Button; das
  Terminal meldet `/models` direkt im Chat.
- Tests decken Command-Katalog, Terminal-Slash-Befehl und GUI-Dispatch ab.

## 0.37.1 - 2026-05-25

- Ergaenzt GTK-Regressionstests fuer den `/stats`-Promptdialog.

## 0.37.0 - 2026-05-25

- `/stats` funktioniert jetzt im interaktiven CLI-Prompt sowie in Tk und GTK.
- CLI und GUI teilen die content-freie Statistikformatierung.
- Tests decken Command-Katalog, Terminal-Slash-Befehl und Tk-Dialog ab.

## 0.36.1 - 2026-05-25

- Ergaenzt Regressionstests fuer `telachat stats` auf einer leeren Historie.

## 0.36.0 - 2026-05-25

- `telachat stats` zeigt lokale Historienstatistiken ohne Nachrichtentexte.
- Text- und JSON-Ausgabe zaehlen Sessions, Nachrichten, Ordner, Tags, Profile
  und Modelle.
- Tests sichern ab, dass weder Chat-Inhalte noch Secret-Felder in der Statistik
  auftauchen.
- Zusaetzliche Timing-Regressionstests pruefen GTK-Status und Regenerate.

## 0.35.0 - 2026-05-25

- Send und Regenerate messen jetzt die API-Antwortzeit.
- GTK und Tk zeigen die Antwortzeit nach erfolgreichen Antworten im Status.
- Neue Controller/GUI-Tests pruefen die Latenzweitergabe.

## 0.34.1 - 2026-05-25

- Ergaenzt fokussierte Regressionstests fuer Chat-Completions-Parameter wie
  Temperatur, `top_p`, Tokenlimit und Reasoning-Aufwand.

## 0.34.0 - 2026-05-25

- GTK und Tk haben jetzt sichtbare Generierungsregler fuer Temperatur und
  maximale Antworttokens.
- Send und Regenerate nutzen diese Werte pro Anfrage.
- Der OpenAI-Responses-Pfad sendet Temperatur und `top_p` jetzt ebenfalls.

## 0.33.0 - 2026-05-25

- GTK und Tk haben jetzt einen sichtbaren Tagfilter in der Seitenleiste.
- Die Tagauswahl zeigt Zaehler und bleibt erhalten, wenn `/tag` oder `/untag`
  nur die Zaehler veraendert.
- Neue GUI-Regressionstests pruefen Tagfilter-Weitergabe und Auswahl-Erhalt.

## 0.32.1 - 2026-05-25

- Ergaenzt fokussierte Regressionstests fuer den sichtbaren Archivfilter in
  Tk und GTK.

## 0.32.0 - 2026-05-25

- GTK und Tk haben jetzt einen sichtbaren Archivfilter in der Seitenleiste.
- Die Chatliste kann direkt zwischen `Aktiv`, `Archiv` und `Alle` wechseln.
- `/archives` schaltet die GUI-Liste automatisch in die Archivansicht.

## 0.31.0 - 2026-05-25

- Sessions koennen weich archiviert werden, ohne sie zu loeschen.
- Normale Listen zeigen aktive Chats; `sessions --archived` und
  `sessions --all` holen archivierte Chats gezielt zurueck.
- `telachat archive`, `telachat unarchive`, `/archive`, `/unarchive` und
  `/archives` funktionieren in CLI, GTK und Tk.
- JSON/Markdown-Exporte, Imports, Forks und Backup-Restore erhalten den
  Archivstatus.

## 0.30.0 - 2026-05-25

- Sessions koennen persistente Tags tragen.
- `telachat tags` verwaltet Tags; `telachat sessions --tag TAG` filtert
  gespeicherte Chats.
- Tags werden in JSON/Markdown-Exporten, Imports, Forks, Restore-Imports,
  Suche, Completion und GUI-Listen erhalten.

## 0.29.0 - 2026-05-25

- `telachat --version` gibt die installierte Version aus.
- Ein CLI-Test prueft die Ausgabe.

## 0.28.0 - 2026-05-25

- GTK und Tk aktualisieren die Modell-Auswahl nach dem GUI-Check mit live
  gemeldeten `/models`-IDs.
- Das aktuell gewaehlte Modell bleibt vorne; Live- und konfigurierte Modelle
  werden ohne Duplikate zusammengefuehrt.
- Neue Tests pruefen diese Merge-Logik separat.

## 0.27.0 - 2026-05-25

- `telachat models` zeigt konfigurierte Modelle pro Profil.
- `telachat models --live [-p PROFILE]` fragt `/models` gezielt fuer ein
  Profil ab.
- JSON-Ausgabe bleibt redaktiert und enthaelt konfigurierte sowie live
  gemeldete Modell-IDs.

## 0.26.0 - 2026-05-25

- `config-check --profile NAME` prueft nur ein Profil.
- `--strict` kann damit gezielt fuer ein Zielprofil genutzt werden, ohne
  optionale Provider mitzuzählen.
- JSON-Ausgabe enthaelt `profile_filter`.

## 0.25.0 - 2026-05-25

- Standardkonfiguration enthaelt lokale Provider-Presets fuer LM Studio,
  Ollama und Jan.
- Die Presets sind nicht Default und enthalten keine echten Secrets.
- Tests pruefen die neuen lokalen Profile und Endpunkt-Metadaten.

## 0.24.0 - 2026-05-25

- `import-session` und `import-folder` unterstuetzen `--dry-run`.
- Dry-Runs validieren JSON-Importe und melden Sessions/Nachrichten, ohne
  SQLite zu beschreiben.
- Tests stellen sicher, dass Dry-Runs keine Ordner oder Sessions anlegen.

## 0.23.0 - 2026-05-25

- `telachat import-folder FILE.json` importiert `telachat.folder.v1` additiv.
- `--folder` legt alle importierten Sessions in einen Zielordner.
- `--json` gibt Zielordner, importierte Sessions und Nachrichtenanzahl
  strukturiert aus.
- Der Import validiert alle Sessions und Nachrichten vor dem Schreiben.

## 0.22.0 - 2026-05-25

- `telachat export-folder FOLDER --json` exportiert mehrere Sessions als
  `telachat.folder.v1`.
- JSON enthaelt Ordner-Metadaten, Sortierung, Session-Metadaten,
  Systemprompts und Nachrichten.
- Leere Ordner bleiben als JSON mit leerer `sessions`-Liste skriptbar.

## 0.21.0 - 2026-05-25

- `telachat import-session FILE.json` importiert `telachat.session.v1`
  additiv als neue Session.
- `--title` und `--folder` setzen Zielmetadaten beim Import.
- `--json` gibt die importierte Session und Nachrichtenanzahl strukturiert aus.

## 0.20.0 - 2026-05-25

- `telachat export SESSION --json` exportiert eine einzelne Session
  maschinenlesbar.
- JSON enthaelt Session-Metadaten, Systemprompt und sortierte Nachrichten.
- `-o/--output` funktioniert fuer JSON- und Markdown-Export.

## 0.19.0 - 2026-05-25

- Neuer Slash-Befehl `/find TEXT` durchsucht die aktuell geladene Unterhaltung.
- CLI gibt kompakte Trefferzeilen aus; GTK und Tk zeigen die Treffer im Dialog.
- Tests pruefen Trefferformatierung und CLI-Ausgabe nach einem Fork.

## 0.18.0 - 2026-05-25

- Neuer Slash-Befehl `/theme [NAME]` fuer CLI, GTK und Tk.
- Completion kennt Theme-Namen wie `dracula`.
- Tests pruefen Hilfe, Completion und interaktives CLI-Setzen.

## 0.17.0 - 2026-05-25

- Theme-Katalog erweitert: Solarized, Nord, Dracula, Gruvbox, Ocean, Forest und
  Rose.
- `system` nutzt Desktop-/Terminal-Hinweise fuer die Palette.
- `TELACHAT_SYSTEM_THEME` kann die System-Palette fuer einen Prozess fixieren,
  ohne `theme = "system"` zu aendern.
- Tests pruefen Theme-Aliase, System-Erkennung und `doctor --json` ohne
  `--chat`.

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
