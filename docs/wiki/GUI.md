# GUI

Telachat hat zwei native Python-GUIs:

- `telachat-tk` fuer Tk/ttk
- `telachat-gtk` fuer GTK4/Adwaita

Die Tk-Version ist der pragmatische Default fuer Paketierung, weil sie ohne
Webserver auskommt und einfacher als lokales Bundle gebaut werden kann.

## Bedienung

- Links: Provider, Modell, Chats, Ordner, Tagfilter, Suche und Sortierung.
- Mitte: Chatverlauf und Eingabe.
- Rechts: Systemprompt sowie Temperatur- und Token-Limit-Regler.
- Linke Seite und Systemprompt sind einklappbar.
- Die Seitenbreiten sind per Splitter anpassbar.
- Der Archivfilter `Aktiv / Archiv / Alle` sitzt in der linken Seitenleiste.
- Der Tagfilter zeigt vorhandene Tags mit Zaehlern und filtert die Chatliste.
- Temperatur und maximale Antworttokens koennen pro Anfrage im rechten Bereich
  angepasst werden.
- Nach erfolgreichen Antworten zeigt der Status die gemessene Antwortzeit.
- `Abbrechen` verwirft laufende Send-, Regenerate- oder Check-Ergebnisse und
  macht die GUI sofort wieder bedienbar. Bereits gestartete Provider-Requests
  koennen serverseitig trotzdem weiterlaufen. Bei abgebrochenen Send-Anfragen
  wird der abgeschickte Prompt wieder eingesetzt, wenn der Composer noch leer
  ist.
- `Check` fragt `/models` live fuer den gewaehlten Provider ab und ergaenzt die
  Modellauswahl mit den gemeldeten IDs.
- `Shift+Enter` sendet eine Nachricht.
- `Enter` fuegt einen Zeilenumbruch ein.
- Slash-Befehle zeigen beim Tippen Vorschlaege.
- `Tab` vervollstaendigt den aktuellen Slash-Befehl.
- `/edit-last TEXT` ersetzt die letzte Nutzernachricht und entfernt die danach
  liegende Antwort; `/regen` generiert danach neu.
- `/fork [TITLE]` kopiert den aktuellen Chat und laedt den neuen Fork.
- `/archive`, `/unarchive` und `/archives` verwalten erledigte Chats.
- `/tag`, `/untag` und `/tags` verwalten flexible Chat-Markierungen.
- `/stats` zeigt lokale Historienzaehler ohne Chat-Inhalte.
- `/context` zeigt content-frei eine grobe Groesse des naechsten Requests.
- `/doctor` startet denselben Erreichbarkeitscheck wie der Check-Button.
- `/exit`, `/quit` und `/q` schliessen das Fenster.
- `/theme [NAME]` wechselt das GUI-Theme direkt aus dem Prompt.
- `/find TEXT` zeigt Treffer in der aktuell geladenen Unterhaltung.

## Chatverwaltung

- Chats koennen in Ordner verschoben werden.
- Chats koennen Tags tragen; die Tags erscheinen in der Chatliste und sind
  direkt ueber den Tagfilter auswaehlbar.
- Chats koennen archiviert werden; der sichtbare Archivfilter wechselt
  zwischen aktiven, archivierten und allen Chats.
- Ordner koennen umbenannt und geloescht werden.
- Ordner koennen einen Default-Systemprompt und ein Default-Backend speichern.
  Beim Auswaehlen eines Ordners setzen GTK und Tk den konfigurierten
  Provider/Modell-Default fuer neue Chats.
- Chats koennen gepinnt werden.
- Suche und Sortierung sind in der Seitenleiste verfuegbar.

## Themes

- Beide GUIs nutzen denselben Theme-Katalog.
- `system` folgt soweit moeglich Desktop-/Terminal-Hinweisen.
- `TELACHAT_THEME` uebersteuert das gespeicherte Theme fuer einen Prozess.
- `TELACHAT_SYSTEM_THEME` fixiert nur die System-Erkennung fuer einen Prozess.
- Verfuegbare Paletten: `light`, `dark`, `high-contrast`, `solarized-light`,
  `solarized-dark`, `nord`, `dracula`, `gruvbox`, `ocean`, `forest`, `rose`.
- Der Prompt-Befehl `/theme dracula` nutzt denselben gespeicherten Wert wie der
  Theme-Waehler im Systembereich.

## Prompt-Templates

Ab Version `0.3.0` enthalten beide GUIs einen Template-Waehler. Ein Template
wird in den Composer eingefuegt und kann vor dem Senden angepasst werden.

Slash-Commands funktionieren ebenfalls:

```text
/templates
/template summarize Mein Text
/edit-last Besser formulierter Prompt
/fork Variante A
/archive
/archives
/tag projekt review
/stats
/context
/doctor
/q
/folder-system Projektkontext
/permissions
```

Der Button `Ordner-Prompt` speichert den aktuell sichtbaren Systemprompt fuer
den gewaehlten Ordner.
