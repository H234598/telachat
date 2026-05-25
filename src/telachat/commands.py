from __future__ import annotations

from collections.abc import Iterable
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


@dataclass(frozen=True)
class ContextEstimate:
    messages_total: int
    history_messages: int
    max_history_messages: int | None
    system_chars: int
    history_chars: int
    total_chars: int
    approx_tokens: int


SLASH_COMMANDS: tuple[SlashCommand, ...] = (
    SlashCommand("/help", "/help", "Befehle anzeigen", aliases=("/hilfe",)),
    SlashCommand("/new", "/new [Titel]", "Neue Session starten", aliases=("/neu",)),
    SlashCommand("/rename", "/rename TITLE", "Aktuellen Chat umbenennen"),
    SlashCommand("/delete", "/delete", "Aktuellen Chat loeschen"),
    SlashCommand("/pin", "/pin", "Aktuellen Chat anheften"),
    SlashCommand("/unpin", "/unpin", "Aktuellen Chat loesen"),
    SlashCommand("/archive", "/archive", "Aktuellen Chat archivieren"),
    SlashCommand("/unarchive", "/unarchive", "Aktuellen Chat wieder einblenden"),
    SlashCommand("/archives", "/archives", "Archivierte Chats anzeigen"),
    SlashCommand("/tag", "/tag TAG [TAG...]", "Tags zum aktuellen Chat hinzufuegen"),
    SlashCommand("/untag", "/untag TAG [TAG...]", "Tags vom aktuellen Chat entfernen"),
    SlashCommand("/tags", "/tags [SESSION]", "Tags anzeigen"),
    SlashCommand("/stats", "/stats", "Lokale Historienstatistik anzeigen"),
    SlashCommand("/context", "/context", "Groesse des aktuellen Chat-Kontexts schaetzen"),
    SlashCommand("/doctor", "/doctor", "Aktuelles Profil gegen /models pruefen"),
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
    SlashCommand("/find", "/find TEXT", "Aktuelle Unterhaltung durchsuchen"),
    SlashCommand("/provider", "/provider NAME", "Provider wechseln"),
    SlashCommand("/models", "/models [live]", "Modelle anzeigen oder live abfragen"),
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


def format_stats_lines(stats: object, *, include_database: bool = True) -> list[str]:
    lines = []
    if include_database:
        lines.append(f"SQLite: {getattr(stats, 'database_path')}")
    lines.extend(
        [
            (
                "Sessions: "
                f"{getattr(stats, 'sessions_total')} gesamt, "
                f"{getattr(stats, 'sessions_active')} aktiv, "
                f"{getattr(stats, 'sessions_archived')} archiviert, "
                f"{getattr(stats, 'sessions_pinned')} angeheftet, "
                f"{getattr(stats, 'sessions_unfiled')} ohne Ordner"
            ),
            (
                "Nachrichten: "
                f"{getattr(stats, 'messages_total')} gesamt"
                f"{_format_count_suffix(getattr(stats, 'message_roles'))}"
            ),
            (
                "Ordner: "
                f"{getattr(stats, 'folders_total')} gesamt, "
                f"{getattr(stats, 'folders_with_system_prompt')} mit System-Prompt"
            ),
            (
                "Tags: "
                f"{getattr(stats, 'tags_total')} Tags, "
                f"{getattr(stats, 'tag_links_total')} Zuweisungen, "
                f"{getattr(stats, 'tagged_sessions')} getaggte Sessions"
            ),
            f"Profile: {_format_count_pairs(getattr(stats, 'session_profiles'))}",
            (
                "Modelle: "
                f"{_format_count_pairs(getattr(stats, 'session_models'), empty_label='ohne Modell')}"
            ),
        ]
    )
    usage_records = getattr(stats, "usage_records", 0)
    if usage_records:
        lines.append(
            "Token-Nutzung: "
            f"{usage_records} Antworten, "
            f"{getattr(stats, 'usage_input_tokens', 0)} in, "
            f"{getattr(stats, 'usage_output_tokens', 0)} out, "
            f"{getattr(stats, 'usage_total_tokens', 0)} total"
        )
    return lines


def format_stats_summary(stats: object) -> str:
    return (
        f"Sessions {getattr(stats, 'sessions_total')} | "
        f"Nachrichten {getattr(stats, 'messages_total')} | "
        f"Ordner {getattr(stats, 'folders_total')} | "
        f"Tags {getattr(stats, 'tags_total')}"
    )


def estimate_context(
    messages: Iterable[object],
    system_prompt: str,
    *,
    max_history_messages: int | None = None,
) -> ContextEstimate:
    all_messages = list(messages)
    if max_history_messages is None:
        history = all_messages
    elif max_history_messages <= 0:
        history = []
    else:
        history = all_messages[-max_history_messages:]
    system_chars = len(system_prompt)
    history_chars = sum(len(str(getattr(message, "content", ""))) for message in history)
    total_chars = system_chars + history_chars
    return ContextEstimate(
        messages_total=len(all_messages),
        history_messages=len(history),
        max_history_messages=max_history_messages,
        system_chars=system_chars,
        history_chars=history_chars,
        total_chars=total_chars,
        approx_tokens=_approx_tokens(total_chars),
    )


def format_context_lines(estimate: ContextEstimate) -> list[str]:
    limit = (
        "unbegrenzt"
        if estimate.max_history_messages is None
        else str(estimate.max_history_messages)
    )
    return [
        (
            "Kontext: "
            f"{estimate.messages_total} Nachrichten gespeichert, "
            f"{estimate.history_messages} im naechsten Request"
        ),
        (
            "Zeichen: "
            f"Nachrichten {estimate.history_chars}, "
            f"System {estimate.system_chars}, "
            f"gesamt {estimate.total_chars}"
        ),
        f"Schaetzung: ca. {estimate.approx_tokens} Tokens (Zeichen/4)",
        f"History-Limit: {limit}",
    ]


def format_context_summary(estimate: ContextEstimate) -> str:
    return (
        f"Kontext ca. {estimate.approx_tokens} Tokens | "
        f"{estimate.history_messages}/{estimate.messages_total} Nachrichten"
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


def _format_count_suffix(pairs: Iterable[tuple[str, int]]) -> str:
    text = _format_count_pairs(pairs)
    return f" ({text})" if text != "-" else ""


def _format_count_pairs(
    pairs: Iterable[tuple[str, int]],
    *,
    empty_label: str = "leer",
) -> str:
    labels = [
        f"{label or empty_label}={count}"
        for label, count in pairs
    ]
    return ", ".join(labels) if labels else "-"


def _approx_tokens(chars: int) -> int:
    if chars <= 0:
        return 0
    return (chars + 3) // 4


def format_message_matches(
    messages: Iterable[object],
    query: str,
    *,
    limit: int = 10,
    width: int = 160,
) -> list[str]:
    needle = query.strip().lower()
    if not needle:
        return []
    results: list[str] = []
    for index, message in enumerate(messages, start=1):
        content = str(getattr(message, "content", ""))
        if needle not in content.lower():
            continue
        role = str(getattr(message, "role", ""))
        label = {"user": "Du", "assistant": "KI"}.get(role, role or "?")
        snippet = " ".join(content.split())
        if len(snippet) > width:
            snippet = snippet[: max(0, width - 3)].rstrip() + "..."
        results.append(f"{index}. {label}: {snippet}")
        if len(results) >= limit:
            break
    return results
