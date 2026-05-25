# GUI

Telachat hat zwei native Python-GUIs:

- `telachat-tk` fuer Tk/ttk
- `telachat-gtk` fuer GTK4/Adwaita

Die Tk-Version ist der pragmatische Default fuer Paketierung, weil sie ohne
Webserver auskommt und einfacher als lokales Bundle gebaut werden kann.

## Bedienung

- Links: Provider, Modell, Chats, Ordner, Suche und Sortierung.
- Mitte: Chatverlauf und Eingabe.
- Rechts: Systemprompt.
- Linke Seite und Systemprompt sind einklappbar.
- Die Seitenbreiten sind per Splitter anpassbar.
- `Shift+Enter` sendet eine Nachricht.
- `Enter` fuegt einen Zeilenumbruch ein.

## Chatverwaltung

- Chats koennen in Ordner verschoben werden.
- Ordner koennen umbenannt und geloescht werden.
- Ordner koennen einen Default-Systemprompt speichern.
- Chats koennen gepinnt werden.
- Suche und Sortierung sind in der Seitenleiste verfuegbar.

## Prompt-Templates

Ab Version `0.3.0` enthalten beide GUIs einen Template-Waehler. Ein Template
wird in den Composer eingefuegt und kann vor dem Senden angepasst werden.

Slash-Commands funktionieren ebenfalls:

```text
/templates
/template summarize Mein Text
/folder-system Projektkontext
```

Der Button `Ordner-Prompt` speichert den aktuell sichtbaren Systemprompt fuer
den gewaehlten Ordner.
