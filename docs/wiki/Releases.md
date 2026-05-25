# Releases

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
