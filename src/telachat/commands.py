from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlashCommand:
    name: str
    usage: str
    description: str
    aliases: tuple[str, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


SLASH_COMMANDS: tuple[SlashCommand, ...] = (
    SlashCommand("/help", "/help", "Befehle anzeigen", aliases=("/hilfe",)),
    SlashCommand("/new", "/new [Titel]", "Neue Session starten", aliases=("/neu",)),
    SlashCommand("/rename", "/rename TITLE", "Aktuellen Chat umbenennen"),
    SlashCommand("/delete", "/delete", "Aktuellen Chat loeschen"),
    SlashCommand("/pin", "/pin", "Aktuellen Chat anheften"),
    SlashCommand("/unpin", "/unpin", "Aktuellen Chat loesen"),
    SlashCommand(
        "/edit-last",
        "/edit-last TEXT",
        "Letzte Nutzernachricht ersetzen",
        aliases=("/edit",),
    ),
    SlashCommand("/fork", "/fork [TITLE]", "Aktuellen Chat kopieren/verzweigen"),
    SlashCommand("/regen", "/regen", "Letzte KI-Antwort neu generieren", aliases=("/regenerate",)),
    SlashCommand("/templates", "/templates", "Prompt-Templates anzeigen"),
    SlashCommand("/template", "/template NAME TEXT", "Prompt-Template einsetzen"),
    SlashCommand("/folder", "/folder NAME", "Ordner anlegen/waehlen", aliases=("/ordner",)),
    SlashCommand("/folder-system", "/folder-system TEXT", "Ordner-Systemprompt setzen"),
    SlashCommand("/rename-folder", "/rename-folder NAME", "Gewaehlten Ordner umbenennen"),
    SlashCommand("/delete-folder", "/delete-folder", "Gewaehlten Ordner loeschen"),
    SlashCommand("/move", "/move NAME", "Chat in Ordner ablegen", aliases=("/ablegen",)),
    SlashCommand("/unfile", "/unfile", "Chat aus Ordner loesen"),
    SlashCommand("/sort", "/sort newest|oldest|title|title-desc|provider", "Chatliste sortieren"),
    SlashCommand("/search", "/search TEXT", "Chatliste durchsuchen"),
    SlashCommand("/provider", "/provider NAME", "Provider wechseln"),
    SlashCommand("/model", "/model NAME", "Modell wechseln"),
    SlashCommand("/theme", "/theme [NAME]", "GUI-Theme anzeigen/wechseln"),
    SlashCommand("/permissions", "/permissions", "Provider und Secret-Quellen anzeigen"),
    SlashCommand("/left", "/left", "Linke Seite ein-/ausklappen", aliases=("/links",)),
    SlashCommand("/system", "/system [prompt]", "Systembereich ein-/ausklappen oder Prompt setzen"),
    SlashCommand("/sessions", "/sessions", "Sessions anzeigen"),
    SlashCommand("/load", "/load ID", "Session laden"),
    SlashCommand("/profile", "/profile [name]", "Profil anzeigen/wechseln"),
    SlashCommand("/profiles", "/profiles", "Profile anzeigen"),
    SlashCommand("/history", "/history [n]", "Letzte Nachrichten anzeigen"),
    SlashCommand("/export", "/export [datei.md]", "Aktuelle Session exportieren"),
    SlashCommand("/exit", "/exit", "Chat beenden", aliases=("/quit", "/q")),
)


def slash_command_help() -> str:
    width = max(len(item.usage) for item in SLASH_COMMANDS)
    return "\n".join(
        f"{item.usage:<{width}}  {item.description}" for item in SLASH_COMMANDS
    )


def slash_command_suggestions(prefix: str, *, limit: int = 8) -> list[SlashCommand]:
    clean = prefix.strip().lower()
    if not clean.startswith("/"):
        return []
    matches = [
        command
        for command in SLASH_COMMANDS
        if any(name.startswith(clean) for name in command.names)
    ]
    return matches[:limit]


def slash_command_name_suggestions(prefix: str, *, limit: int = 24) -> list[str]:
    clean = prefix.strip().lower()
    if not clean.startswith("/"):
        return []
    matches: list[str] = []
    seen: set[str] = set()
    for command in SLASH_COMMANDS:
        for name in command.names:
            if name.startswith(clean) and name not in seen:
                matches.append(name)
                seen.add(name)
                if len(matches) >= limit:
                    return matches
    return matches


def canonical_slash_command(name: str) -> str:
    clean = name.strip().lower()
    for command in SLASH_COMMANDS:
        if clean in command.names:
            return command.name
    return clean
