# Configuration

Telachat liest seine Standardkonfiguration aus:

```text
~/.config/telachat/config.toml
```

Die SQLite-Historie liegt unter:

```text
~/.local/share/telachat/history.sqlite3
```

## Provider und Modelle

Profile werden in TOML konfiguriert. Die GUI trennt Provider- und
Modellauswahl: erst Provider waehlen, dann Modell oder Profilvariante.

Beispiele fuer Provider:

- `huggingface` / `tki`
- `openai`
- `codex`

## Secrets

API-Schluessel gehoeren nicht direkt in das Repo oder Wiki. Telachat
unterstuetzt:

- `env:NAME`
- `envfile:/pfad/zur/datei#NAME`

Lokale Secret-Dateien sollten nur fuer den Benutzer lesbar sein:

```sh
chmod 600 ~/.config/telachat/*.env
```

## Prompt-Templates

Ab Version `0.3.0` gibt es in `config.toml` einen Abschnitt:

```toml
[prompt_templates]
summarize = "Fasse den folgenden Inhalt strukturiert zusammen:"
explain = "Erklaere das knapp, praktisch und mit einem Beispiel:"
translate_de = "Uebersetze ins Deutsche und erhalte Fachbegriffe, wenn sinnvoll:"
```

Verwendung:

```sh
telachat templates
telachat ask --template summarize "Langer Text"
```

## Ordner-Systemprompts

Ordner-Systemprompts werden in SQLite gespeichert, nicht in `config.toml`.
Dadurch bleiben sie Teil der lokalen Chat-Historie und koennen pro Projekt
angepasst werden.

```sh
telachat folders --create Projekt --system "Antworte mit Projektkontext."
telachat folders --set-system Projekt "Neuer Kontext."
telachat folders --show-system
```
