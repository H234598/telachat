from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import textwrap
import tempfile
import zipfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from . import __version__
from .client import ApiError, ChatResult, OpenAICompatClient, token_usage_record
from .commands import (
    ContextEstimate,
    SESSION_SORT_NAMES,
    canonical_slash_command,
    estimate_context,
    format_context_lines,
    format_message_matches,
    format_stats_lines,
    keyboard_shortcut_help,
    slash_completion_candidates,
    slash_command_help,
)
from .config import (
    AppConfig,
    ConfigError,
    Profile,
    delete_config_prompt_template,
    ensure_default_config,
    load_config,
    redact_secret,
    rename_config_prompt_template,
    set_config_prompt_template,
    set_config_theme,
)
from .defaults import APP_TITLE
from .paths import config_path, db_path, state_dir
from .skill_watchdog import DEFAULT_DESCRIPTION_LIMIT, run_skill_watchdog
from .store import (
    ChatStore,
    Folder,
    HistoryImportSummary,
    Session,
    StoreStats,
    messages_for_api,
    normalize_tag,
    title_from_prompt,
)
from .templates import (
    SUPPORTED_TEMPLATE_VARIABLES,
    custom_template_variables,
    format_prompt_template_preview,
    is_template_variable_name,
    render_prompt_template,
    template_variables,
)
from .themes import theme_labels


SESSION_SORTS = {
    "newest": "updated_desc",
    "oldest": "updated_asc",
    "title": "title_asc",
    "title-desc": "title_desc",
    "provider": "profile_asc",
}
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (ConfigError, ApiError, KeyboardInterrupt) as exc:
        if isinstance(exc, KeyboardInterrupt):
            print("\nAbgebrochen.", file=sys.stderr)
            return 130
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telachat",
        description="Telachat: lokaler Chat-Client fuer OpenAI-kompatible KI-APIs.",
    )
    parser.add_argument("--config", type=Path, default=None, help="Pfad zu config.toml")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Standardkonfiguration anlegen")
    p_init.add_argument("--force", action="store_true", help="Config ueberschreiben")
    p_init.set_defaults(func=cmd_init)

    p_profiles = sub.add_parser("profiles", help="Profile anzeigen")
    p_profiles.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_profiles.set_defaults(func=cmd_profiles)

    p_models = sub.add_parser(
        "models",
        help="Konfigurierte oder live gemeldete Modelle anzeigen",
    )
    p_models.add_argument("-p", "--profile", help="Profil auswaehlen")
    p_models.add_argument(
        "--live",
        action="store_true",
        help="Live /models fuer das Zielprofil abfragen",
    )
    p_models.add_argument(
        "--json",
        action="store_true",
        help="Maschinenlesbares JSON ausgeben",
    )
    p_models.set_defaults(func=cmd_models)

    p_config = sub.add_parser(
        "config-check",
        aliases=["config"],
        help="Konfiguration ohne API-Anfrage pruefen",
    )
    p_config.add_argument(
        "--strict",
        action="store_true",
        help="Mit Fehlercode beenden, wenn Secret-Quellen fehlen",
    )
    p_config.add_argument(
        "-p",
        "--profile",
        help="Nur dieses Profil pruefen",
    )
    p_config.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_config.add_argument(
        "--show-redacted",
        action="store_true",
        help="Redaktierte config.toml ohne rohe Secrets ausgeben",
    )
    p_config.set_defaults(func=cmd_config_check)

    p_theme = sub.add_parser("theme", help="GUI-Theme anzeigen oder setzen")
    p_theme.add_argument("theme", nargs="?", metavar="NAME", help="Theme-Name oder Alias")
    p_theme.set_defaults(func=cmd_theme)

    p_skill_watchdog = sub.add_parser(
        "skill-watchdog",
        help="Codex-Skill-Beschreibungen auf Loader-kompatible Laenge kuerzen",
    )
    p_skill_watchdog.add_argument(
        "--root",
        action="append",
        type=Path,
        help="Skill-Wurzel scannen; mehrfach moeglich",
    )
    p_skill_watchdog.add_argument(
        "--max-description",
        type=int,
        default=DEFAULT_DESCRIPTION_LIMIT,
        help=f"Maximale description-Laenge (Standard: {DEFAULT_DESCRIPTION_LIMIT})",
    )
    p_skill_watchdog.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_skill_watchdog.set_defaults(func=cmd_skill_watchdog)

    p_templates = sub.add_parser("templates", help="Prompt-Templates anzeigen")
    p_templates.add_argument(
        "--set",
        nargs=2,
        metavar=("NAME", "TEXT"),
        help="Prompt-Template anlegen oder aktualisieren",
    )
    p_templates.add_argument(
        "--rename",
        nargs=2,
        metavar=("OLD", "NEW"),
        help="Prompt-Template umbenennen",
    )
    p_templates.add_argument("--delete", metavar="NAME", help="Prompt-Template loeschen")
    p_templates.add_argument(
        "--show",
        metavar="NAME",
        help="Prompt-Template mit Metadaten anzeigen",
    )
    p_templates.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_templates.set_defaults(func=cmd_templates)

    p_folders = sub.add_parser("folders", help="Ordner anzeigen/verwalten")
    p_folders.add_argument("--create", metavar="NAME", help="Ordner anlegen")
    p_folders.add_argument("--system", help="System-Prompt fuer --create")
    p_folders.add_argument("--context", help="Ordner-Kontext fuer --create")
    p_folders.add_argument("--profile", help="Default-Provider fuer --create")
    p_folders.add_argument("--model", help="Default-Modell fuer --create")
    p_folders.add_argument(
        "--set-system",
        nargs=2,
        metavar=("FOLDER", "PROMPT"),
        help="Default-Systemprompt fuer Ordner setzen",
    )
    p_folders.add_argument(
        "--set-context",
        nargs=2,
        metavar=("FOLDER", "TEXT"),
        help="Ordner-Kontextnotiz setzen",
    )
    p_folders.add_argument(
        "--set-backend",
        nargs="+",
        metavar="VALUE",
        help="Default-Backend setzen: FOLDER PROFILE [MODEL]",
    )
    p_folders.add_argument(
        "--clear-backend",
        metavar="FOLDER",
        help="Default-Backend eines Ordners loeschen",
    )
    p_folders.add_argument(
        "--show-system",
        action="store_true",
        help="Ordner-Systemprompts voll anzeigen",
    )
    p_folders.add_argument(
        "--show-context",
        action="store_true",
        help="Ordner-Kontextnotizen voll anzeigen",
    )
    p_folders.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_folders.set_defaults(func=cmd_folders)

    p_ask = sub.add_parser("ask", help="Einzelne Frage stellen")
    add_chat_options(p_ask)
    p_ask.add_argument("prompt", nargs="*", help="Prompt; leer liest interaktiv/stdin")
    p_ask.add_argument("--stdin", action="store_true", help="Prompt aus stdin lesen")
    p_ask.add_argument("--save", action="store_true", help="Frage und Antwort speichern")
    p_ask.add_argument("--template", "-t", help="Prompt-Template auf den Prompt anwenden")
    p_ask.add_argument(
        "--template-var",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Custom-Variable fuer Prompt-Template setzen; mehrfach moeglich",
    )
    p_ask.add_argument("--json", action="store_true", help="Antwort maschinenlesbar ausgeben")
    p_ask.set_defaults(func=cmd_ask)

    p_chat = sub.add_parser("chat", help="Interaktiven Chat starten")
    add_chat_options(p_chat)
    p_chat.add_argument("--session", "-s", help="Session-ID oder Prefix laden")
    p_chat.add_argument("--new", action="store_true", help="Neue Session erzwingen")
    p_chat.set_defaults(func=cmd_chat)

    p_sessions = sub.add_parser("sessions", help="Gespeicherte Sessions anzeigen")
    p_sessions.add_argument("--limit", type=int, default=20)
    p_sessions.add_argument("--query", "-q", help="Titel, Provider oder Nachrichteninhalt suchen")
    p_sessions.add_argument("--folder", help="Ordnername/-ID oder 'none' fuer Ohne Ordner")
    p_sessions.add_argument("--tag", help="Nur Sessions mit diesem Tag anzeigen")
    p_sessions.add_argument("--archived", action="store_true", help="Nur archivierte Sessions anzeigen")
    p_sessions.add_argument("--all", action="store_true", help="Aktive und archivierte Sessions anzeigen")
    p_sessions.add_argument(
        "--sort",
        choices=sorted(SESSION_SORTS),
        default="newest",
        help="Sortierung der Sessionliste",
    )
    p_sessions.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_sessions.set_defaults(func=cmd_sessions)

    p_stats = sub.add_parser("stats", help="Lokale Historienstatistik anzeigen")
    p_stats.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_stats.set_defaults(func=cmd_stats)

    p_context = sub.add_parser("context", help="Kontextgroesse einer Session schaetzen")
    p_context.add_argument("session", help="Session-ID oder Prefix")
    p_context.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_context.set_defaults(func=cmd_context)

    p_tags = sub.add_parser("tags", help="Session-Tags anzeigen/verwalten")
    p_tags.add_argument("session", nargs="?", help="Session-ID oder Prefix; leer listet alle Tags")
    p_tags.add_argument("--add", action="append", default=[], metavar="TAG", help="Tag hinzufuegen")
    p_tags.add_argument("--remove", action="append", default=[], metavar="TAG", help="Tag entfernen")
    p_tags.add_argument("--set", nargs="+", metavar="TAG", help="Tags ersetzen")
    p_tags.add_argument("--clear", action="store_true", help="Alle Tags der Session entfernen")
    p_tags.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_tags.set_defaults(func=cmd_tags)

    p_archive = sub.add_parser("archive", help="Session archivieren")
    p_archive.add_argument("session", help="Session-ID oder Prefix")
    p_archive.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_archive.set_defaults(func=cmd_archive)

    p_unarchive = sub.add_parser("unarchive", help="Session aus dem Archiv holen")
    p_unarchive.add_argument("session", help="Session-ID oder Prefix")
    p_unarchive.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_unarchive.set_defaults(func=cmd_unarchive)

    p_fork = sub.add_parser("fork", help="Session kopieren/verzweigen")
    p_fork.add_argument("session", help="Session-ID oder Prefix")
    p_fork.add_argument("-t", "--title", help="Titel fuer den neuen Fork")
    p_fork.set_defaults(func=cmd_fork)

    p_export = sub.add_parser("export", help="Session als Markdown exportieren")
    p_export.add_argument("session", help="Session-ID oder Prefix")
    p_export.add_argument("-o", "--output", type=Path, help="Ausgabedatei")
    p_export.add_argument("--json", action="store_true", help="Session als JSON exportieren")
    p_export.set_defaults(func=cmd_export)

    p_export_folder = sub.add_parser("export-folder", help="Ordner als Markdown exportieren")
    p_export_folder.add_argument("folder", help="Ordnername/-ID, 'all' oder 'none'")
    p_export_folder.add_argument("-o", "--output", type=Path, help="Ausgabedatei/-ordner")
    p_export_folder.add_argument(
        "--sort",
        choices=sorted(SESSION_SORTS),
        default="title",
        help="Sortierung der exportierten Sessions",
    )
    p_export_folder.add_argument(
        "--archived",
        action="store_true",
        help="Nur archivierte Sessions exportieren",
    )
    p_export_folder.add_argument(
        "--all",
        action="store_true",
        help="Aktive und archivierte Sessions exportieren",
    )
    p_export_folder.add_argument(
        "--single-file",
        action="store_true",
        help="Alle Chats in eine Markdown-Datei schreiben",
    )
    p_export_folder.add_argument(
        "--json",
        action="store_true",
        help="Ordner als maschinenlesbares JSON exportieren",
    )
    p_export_folder.add_argument(
        "--bundle",
        action="store_true",
        help="Ordner als portables ZIP-Bundle mit JSON-Export schreiben",
    )
    p_export_folder.set_defaults(func=cmd_export_folder)

    p_import_session = sub.add_parser(
        "import-session",
        help="Einzelne JSON-Session additiv importieren",
    )
    p_import_session.add_argument(
        "session_json",
        type=Path,
        help="Export aus `telachat export --json`",
    )
    p_import_session.add_argument(
        "--title",
        help="Importierten Titel ueberschreiben",
    )
    p_import_session.add_argument(
        "--folder",
        help="Import in Ordner ablegen/Ordner anlegen",
    )
    p_import_session.add_argument(
        "--json",
        action="store_true",
        help="Maschinenlesbares JSON ausgeben",
    )
    p_import_session.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur validieren und zaehlen, nichts schreiben",
    )
    p_import_session.set_defaults(func=cmd_import_session)

    p_import_folder = sub.add_parser(
        "import-folder",
        help="JSON-Ordnerexport oder ZIP-Bundle additiv importieren",
    )
    p_import_folder.add_argument(
        "folder_export",
        type=Path,
        help="Export aus `telachat export-folder --json` oder `--bundle`",
    )
    p_import_folder.add_argument(
        "--folder",
        help="Zielordner ueberschreiben/Ordner anlegen",
    )
    p_import_folder.add_argument(
        "--json",
        action="store_true",
        help="Maschinenlesbares JSON ausgeben",
    )
    p_import_folder.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur validieren und zaehlen, nichts schreiben",
    )
    p_import_folder.set_defaults(func=cmd_import_folder)

    p_backup = sub.add_parser("backup", help="SQLite-Historie und redaktierte Config sichern")
    p_backup.add_argument("-o", "--output", type=Path, help="Backup-Zip oder Zielverzeichnis")
    p_backup.set_defaults(func=cmd_backup)

    p_restore = sub.add_parser("restore", help="Backup-Historie sicher importieren")
    p_restore.add_argument("backup", type=Path, help="Telachat-Backup-ZIP")
    p_restore.add_argument("--dry-run", action="store_true", help="Nur anzeigen, was importiert wuerde")
    p_restore.set_defaults(func=cmd_restore)

    p_import_backup = sub.add_parser("import-backup", help="Alias fuer restore")
    p_import_backup.add_argument("backup", type=Path, help="Telachat-Backup-ZIP")
    p_import_backup.add_argument("--dry-run", action="store_true", help="Nur anzeigen, was importiert wuerde")
    p_import_backup.set_defaults(func=cmd_restore)

    p_doctor = sub.add_parser("doctor", help="Konfiguration/API pruefen")
    p_doctor.add_argument("-p", "--profile", help="Profilname")
    p_doctor.add_argument("--chat", action="store_true", help="Auch kurze Chat-Anfrage testen")
    p_doctor.add_argument("--json", action="store_true", help="Maschinenlesbares JSON ausgeben")
    p_doctor.set_defaults(func=cmd_doctor)

    p_gui = sub.add_parser("gui", help="GTK-GUI starten")
    p_gui.set_defaults(func=cmd_gtk_gui)

    p_gtk = sub.add_parser("gtk", help="GTK-GUI starten")
    p_gtk.set_defaults(func=cmd_gtk_gui)

    p_tk = sub.add_parser("tk", help="Tk-GUI starten")
    p_tk.set_defaults(func=cmd_tk_gui)

    return parser


def add_chat_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-p", "--profile", help="Profilname")
    parser.add_argument("--model", help="Model-ID ueberschreiben")
    parser.add_argument("--system", help="System-Prompt ueberschreiben")
    parser.add_argument("--temperature", type=float, help="Sampling-Temperatur")
    parser.add_argument("--max-tokens", type=int, help="Maximale neue Tokens")
    parser.add_argument(
        "--reasoning-effort",
        choices=REASONING_EFFORTS,
        help="Reasoning-Aufwand fuer passende OpenAI-Modelle",
    )
    parser.add_argument("--no-stream", action="store_true", help="Streaming deaktivieren")


def cmd_init(args: argparse.Namespace) -> int:
    path = ensure_default_config(args.config, force=args.force)
    print(f"Konfiguration bereit: {path}")
    print(f"Historie: {db_path()}")
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.json:
        print(
            json.dumps(
                {
                    "config": str(cfg.path),
                    "default_profile": cfg.default_profile,
                    "profiles": [
                        _profile_record(name, profile, is_default=name == cfg.default_profile)
                        for name, profile in sorted(cfg.profiles.items())
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(f"Config: {cfg.path}")
    for name in sorted(cfg.profiles):
        profile = cfg.profiles[name]
        marker = "*" if name == cfg.default_profile else " "
        print(f"{marker} {name} ({profile.display_name})")
        print(f"    base_url: {profile.base_url}")
        print(f"    model:    {profile.model}")
        if profile.reasoning_effort:
            print(f"    reasoning: {profile.reasoning_effort}")
        print(f"    api_key:  {redact_secret(profile.api_key)}")
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.live:
        profiles = [cfg.profile(args.profile)]
    elif args.profile:
        profiles = [cfg.profile(args.profile)]
    else:
        profiles = [cfg.profiles[name] for name in sorted(cfg.profiles)]

    rows = []
    for profile in profiles:
        row = _model_record(
            profile,
            is_default=profile.name == cfg.default_profile,
            live_models=OpenAICompatClient(profile, retries=1).list_models()
            if args.live
            else None,
        )
        rows.append(row)

    if args.json:
        print(
            json.dumps(
                {
                    "app": APP_TITLE,
                    "config": str(cfg.path),
                    "default_profile": cfg.default_profile,
                    "live": args.live,
                    "profile_filter": args.profile
                    if args.profile
                    else (cfg.default_profile if args.live else None),
                    "profiles": rows,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print(f"{APP_TITLE} models")
    print(f"Config: {cfg.path}")
    print(f"Source: {'live /models' if args.live else 'configured'}")
    if args.profile or args.live:
        print(f"Profile filter: {rows[0]['name']}")
    for row in rows:
        marker = "*" if row["default"] else " "
        print(f"{marker} {row['name']} ({row['label']})")
        print(f"    selected:   {row['selected_model']}")
        print(f"    configured: {', '.join(row['configured_models'])}")
        if args.live:
            live_models = row.get("live_models") or []
            detail = ", ".join(live_models) if live_models else "keine IDs gemeldet"
            print(f"    live:       {detail}")
    return 0


def cmd_config_check(args: argparse.Namespace) -> int:
    if args.show_redacted and args.json:
        raise ConfigError("--show-redacted kann nicht mit --json kombiniert werden.")
    cfg = load_config(args.config)
    missing = 0
    profile_rows = []
    profiles = [cfg.profile(args.profile)] if args.profile else [cfg.profiles[name] for name in sorted(cfg.profiles)]
    for profile in profiles:
        name = profile.name
        ok, detail = _secret_status(profile)
        if not ok:
            missing += 1
        profile_rows.append(
            {
                **_profile_record(name, profile, is_default=name == cfg.default_profile),
                "secret_ok": ok,
                "secret_status": detail,
                "model_count": len(profile.models or [profile.model]),
            }
        )
    if args.json:
        print(
            json.dumps(
                {
                    "app": APP_TITLE,
                    "config": str(cfg.path),
                    "sqlite": str(db_path()),
                    "default_profile": cfg.default_profile,
                    "theme": cfg.theme,
                    "app_icon": cfg.app_icon,
                    "chat_background_image": cfg.chat_background_image,
                    "validate_profile_headers": cfg.validate_profile_headers,
                    "skill_watchdog_enabled": cfg.skill_watchdog_enabled,
                    "profile_filter": args.profile,
                    "prompt_templates": len(cfg.prompt_templates),
                    "missing_secrets": missing,
                    "profiles": profile_rows,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1 if args.strict and missing else 0
    if args.show_redacted:
        print(_redacted_config_toml(cfg, profiles=profiles), end="")
        return 1 if args.strict and missing else 0
    print(f"{APP_TITLE} config")
    print(f"Config: {cfg.path}")
    print(f"SQLite: {db_path()}")
    print(f"Default profile: {cfg.default_profile}")
    print(f"Theme: {cfg.theme}")
    print(f"App icon: {cfg.app_icon}")
    print(f"Chat background: {cfg.chat_background_image or '-'}")
    print(f"Header validation: {'on' if cfg.validate_profile_headers else 'off'}")
    print(f"Skill watchdog: {'on' if cfg.skill_watchdog_enabled else 'off'}")
    if args.profile:
        print(f"Profile filter: {args.profile}")
    for row in profile_rows:
        marker = "*" if row["default"] else " "
        print(
            f"{marker} {row['name']}: mode={row['api_mode']} model={row['model']} "
            f"models={row['model_count']} key={row['secret_status']}"
        )
    print(f"Prompt templates: {len(cfg.prompt_templates)}")
    if missing:
        print(f"Warnings: {missing} profile(s) have missing secret sources.")
    return 1 if args.strict and missing else 0


def cmd_theme(args: argparse.Namespace) -> int:
    if args.theme:
        theme = set_config_theme(args.theme, args.config)
        print(f"Theme gesetzt: {theme}")
    cfg = load_config(args.config)
    print(f"Aktives Theme: {cfg.theme}")
    print("Verfuegbar:")
    labels = theme_labels()
    width = max(14, *(len(name) for name in labels))
    for name, label in labels.items():
        marker = "*" if name == cfg.theme else " "
        print(f"{marker} {name:{width}} {label}")
    return 0


def cmd_skill_watchdog(args: argparse.Namespace) -> int:
    roots = tuple(args.root or ())
    result = run_skill_watchdog(
        roots or None,
        description_limit=max(128, int(args.max_description)),
    )
    payload = {
        "scanned": result.scanned,
        "compacted": result.compacted,
        "unchanged": result.unchanged,
        "skipped": result.skipped,
        "errors": list(result.errors),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if result.errors else 0
    print(
        "Skill-Watchdog: "
        f"{result.compacted} gekuerzt, {result.unchanged} unveraendert, "
        f"{result.skipped} uebersprungen, {len(result.errors)} Fehler."
    )
    for error in result.errors:
        print(f"Fehler: {error}", file=sys.stderr)
    return 1 if result.errors else 0


def cmd_templates(args: argparse.Namespace) -> int:
    mutations = [
        bool(args.set),
        bool(args.rename),
        bool(args.delete),
        bool(args.show),
    ]
    if sum(mutations) > 1:
        raise ConfigError("Nur eine Template-Aktion pro Aufruf angeben.")
    if args.set:
        name, template = args.set
        saved = set_config_prompt_template(name, template, args.config)
        if args.json:
            print(
                json.dumps(
                    {"template": _template_record(name.strip(), saved)},
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"Prompt-Template gespeichert: {name.strip()}")
        return 0
    if args.rename:
        old_name, new_name = args.rename
        renamed = rename_config_prompt_template(old_name, new_name, args.config)
        if args.json:
            cfg = load_config(args.config)
            print(
                json.dumps(
                    {
                        "renamed": {"from": old_name.strip(), "to": renamed},
                        "template": _template_record(renamed, cfg.prompt_templates[renamed]),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"Prompt-Template umbenannt: {old_name.strip()} -> {renamed}")
        return 0
    if args.delete:
        deleted = delete_config_prompt_template(args.delete, args.config)
        if args.json:
            print(json.dumps({"deleted": deleted}, indent=2, sort_keys=True))
        else:
            print(f"Prompt-Template geloescht: {deleted}")
        return 0

    cfg = load_config(args.config)
    if args.show:
        name = args.show.strip()
        try:
            template = cfg.prompt_templates[name]
        except KeyError as exc:
            available = ", ".join(sorted(cfg.prompt_templates)) or "<keine>"
            raise ConfigError(
                f"Unbekanntes Prompt-Template: {name}. Verfuegbar: {available}"
            ) from exc
        if args.json:
            print(
                json.dumps(
                    {"template": _template_record(name, template)},
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(format_prompt_template_preview(name, template))
        return 0
    if args.json:
        print(
            json.dumps(
                {
                    "templates": [
                        _template_record(name, cfg.prompt_templates[name])
                        for name in sorted(cfg.prompt_templates)
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not cfg.prompt_templates:
        print("Keine Prompt-Templates konfiguriert.")
        return 0
    for name in sorted(cfg.prompt_templates):
        first_line = cfg.prompt_templates[name].splitlines()[0]
        print(f"{name:16} {first_line}")
    return 0


def cmd_folders(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    store = ChatStore()
    try:
        if args.create:
            profile_name, model = _validate_folder_backend(
                cfg,
                args.profile or "",
                args.model or "",
            )
            folder = store.create_folder(
                args.create,
                system_prompt=args.system or "",
                context=args.context or "",
                default_profile=profile_name,
                default_model=model,
            )
            if not args.json:
                print(f"Ordner bereit: {folder.id} {folder.name}")
        if args.set_system:
            folder_ref, prompt = args.set_system
            folder_id = _resolve_real_folder(store, folder_ref)
            folder = store.update_folder_system_prompt(folder_id, prompt)
            if not args.json:
                print(f"System-Prompt gesetzt: {folder.name}")
        if args.set_context:
            folder_ref, context = args.set_context
            folder_id = _resolve_real_folder(store, folder_ref)
            folder = store.update_folder_context(folder_id, context)
            if not args.json:
                print(f"Ordner-Kontext gesetzt: {folder.name}")
        if args.set_backend:
            if len(args.set_backend) not in {2, 3}:
                raise ConfigError("--set-backend braucht: FOLDER PROFILE [MODEL]")
            folder_ref = args.set_backend[0]
            profile_name = args.set_backend[1]
            model = args.set_backend[2] if len(args.set_backend) == 3 else ""
            profile_name, model = _validate_folder_backend(cfg, profile_name, model)
            folder_id = _resolve_real_folder(store, folder_ref)
            folder = store.update_folder_backend(folder_id, profile_name, model)
            if not args.json:
                print(f"Default-Backend gesetzt: {folder.name}")
        if args.clear_backend:
            folder_id = _resolve_real_folder(store, args.clear_backend)
            folder = store.update_folder_backend(folder_id, "", "")
            if not args.json:
                print(f"Default-Backend geloescht: {folder.name}")
        folders = store.list_folders()
        if args.json:
            print(
                json.dumps(
                    {
                        "folders": [
                            _folder_record(
                                folder,
                                include_system_prompt=args.show_system,
                                include_context=args.show_context,
                            )
                            for folder in folders
                        ]
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if not folders:
            print("Keine Ordner vorhanden.")
            return 0
        for folder in folders:
            markers = []
            if folder.system_prompt:
                markers.append("system")
            if folder.context:
                markers.append("context")
            if folder.default_profile or folder.default_model:
                markers.append("backend")
            marker = ",".join(markers) if markers else "-"
            print(f"{folder.id}  {marker:14}  {folder.name}")
            if folder.default_profile or folder.default_model:
                backend = f"{folder.default_profile or '-'} / {folder.default_model or '-'}"
                print(f"    Backend: {backend}")
            if args.show_system and folder.system_prompt:
                print(textwrap.indent(folder.system_prompt, "    "))
            if args.show_context and folder.context:
                print("    Kontext:")
                print(textwrap.indent(folder.context, "      "))
        return 0
    finally:
        store.close()


def cmd_ask(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    profile = _selected_profile(cfg, args)
    system_prompt = args.system or cfg.default_system_prompt
    if args.template_var and not args.template:
        raise ConfigError("--template-var braucht --template.")
    prompt = _read_prompt(args.prompt, args.stdin)
    if not prompt:
        raise ConfigError("Kein Prompt angegeben.")
    if args.template:
        prompt = _apply_prompt_template(
            cfg,
            args.template,
            prompt,
            values=_parse_template_values(args.template_var),
        )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    saved_session_id: str | None = None
    if args.json:
        result = OpenAICompatClient(profile, retries=1).chat(messages, stream=False)
        assert isinstance(result, ChatResult)
        response = result.content
    else:
        result = None
        response = _run_chat(profile, messages, stream=not args.no_stream)
    if args.save:
        store = ChatStore()
        try:
            session = store.create_session(
                title=title_from_prompt(prompt),
                profile=profile.name,
                model=profile.model,
                system_prompt=system_prompt,
            )
            store.add_message(session.id, "user", prompt)
            store.add_message(
                session.id,
                "assistant",
                response,
                metadata=_assistant_message_metadata(result if isinstance(result, ChatResult) else None),
            )
            saved_session_id = session.id
            if not args.json:
                print(f"\n[gespeichert: {session.id}]", file=sys.stderr)
        finally:
            store.close()
    if args.json:
        assert isinstance(result, ChatResult)
        payload: dict[str, object] = {
            "answer": response,
            "profile": profile.name,
            "model": profile.model,
        }
        usage = _usage_record(result)
        if usage:
            payload["usage"] = usage
        if saved_session_id:
            payload["saved_session_id"] = saved_session_id
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    profile = _selected_profile(cfg, args)
    system_prompt = args.system or cfg.default_system_prompt
    store = ChatStore()
    restore_completion = None
    try:
        store.delete_empty_sessions()
        if sys.stdin.isatty():
            restore_completion = install_readline_completion(cfg, store)
        session = None
        if args.session and not args.new:
            session = store.get_session(args.session)
            if session is None:
                raise ConfigError(f"Session nicht eindeutig gefunden: {args.session}")
            if args.profile is None:
                profile = _profile_for_loaded_session(cfg, args, session)
            system_prompt = session.system_prompt
            print(f"{APP_TITLE}: Session {session.id} geladen: {session.title}")
        if session is None:
            session = store.create_session(
                title="Neue Unterhaltung",
                profile=profile.name,
                model=profile.model,
                system_prompt=system_prompt,
            )
            print(f"{APP_TITLE}: Neue Session {session.id}. /help zeigt Befehle.")

        while True:
            try:
                user_input = input("Du> ").strip()
            except EOFError:
                print()
                break
            if not user_input:
                continue
            if user_input.startswith("/"):
                keep_going, cfg, profile, system_prompt, session = _handle_command(
                    user_input,
                    cfg,
                    store,
                    profile,
                    system_prompt,
                    session,
                    stream=not args.no_stream,
                )
                if not keep_going:
                    break
                continue

            if session.title == "Neue Unterhaltung":
                session = _retitle_session(store, session.id, title_from_prompt(user_input))
            if session.profile != profile.name or session.model != profile.model:
                session = store.update_session_backend(session.id, profile.name, profile.model)
            store.add_message(session.id, "user", user_input)
            history = store.messages(session.id, limit=cfg.max_history_messages)
            messages = messages_for_api(system_prompt, history)
            try:
                print("KI> ", end="", flush=True)
                answer = _run_chat(profile, messages, stream=not args.no_stream)
            except (ApiError, ConfigError, OSError) as exc:
                print(f"\nFehler: {exc}", file=sys.stderr)
                continue
            store.add_message(session.id, "assistant", answer)
    finally:
        if restore_completion:
            restore_completion()
        store.delete_empty_sessions()
        store.close()
    return 0


def cmd_sessions(args: argparse.Namespace) -> int:
    store = ChatStore()
    try:
        store.delete_empty_sessions()
        sessions = store.list_sessions(
            args.limit,
            folder_id=_resolve_folder_filter(store, args.folder),
            sort=SESSION_SORTS[args.sort],
            query=args.query,
            tag=_cli_tag(args.tag) if args.tag else None,
            archive=_archive_filter_from_args(args),
        )
        if args.json:
            print(
                json.dumps(
                    {"sessions": [_session_record(session) for session in sessions]},
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if not sessions:
            print("Keine Sessions gespeichert.")
            return 0
        for session in sessions:
            print(_format_session_line(session))
    finally:
        store.close()
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = ChatStore()
    try:
        stats = store.stats()
        if args.json:
            print(json.dumps(_stats_record(stats), indent=2, sort_keys=True))
            return 0
        print(f"{APP_TITLE} stats")
        for line in format_stats_lines(stats):
            print(line)
    finally:
        store.close()
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    store = ChatStore()
    try:
        session = store.get_session(args.session)
        if session is None:
            raise ConfigError(f"Session nicht gefunden: {args.session}")
        estimate = estimate_context(
            store.messages(session.id),
            session.system_prompt,
            max_history_messages=cfg.max_history_messages,
        )
        if args.json:
            print(json.dumps(_context_record(session, estimate), indent=2, sort_keys=True))
            return 0
        print(f"{APP_TITLE} context: {session.title} ({session.id})")
        for line in format_context_lines(estimate):
            print(line)
    finally:
        store.close()
    return 0


def cmd_tags(args: argparse.Namespace) -> int:
    store = ChatStore()
    try:
        if not args.session:
            if args.add or args.remove or args.set or args.clear:
                raise ConfigError("Zum Aendern von Tags ist eine Session erforderlich.")
            tags = store.list_tags()
            if args.json:
                print(
                    json.dumps(
                        {"tags": [{"tag": tag, "sessions": count} for tag, count in tags]},
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0
            if not tags:
                print("Keine Tags gespeichert.")
                return 0
            for tag, count in tags:
                print(f"#{tag}  {count}")
            return 0

        session = store.get_session(args.session)
        if session is None:
            raise ConfigError(f"Session nicht eindeutig gefunden: {args.session}")
        if args.clear and (args.add or args.remove):
            raise ConfigError("--clear kann nicht mit --add/--remove kombiniert werden.")
        if args.clear and args.set is not None:
            raise ConfigError("--clear und --set schliessen sich aus.")
        if args.set is not None and (args.add or args.remove):
            raise ConfigError("--set kann nicht mit --add/--remove kombiniert werden.")

        tags: list[str]
        if args.clear:
            tags = store.set_session_tags(session.id, [])
        elif args.set is not None:
            tags = store.set_session_tags(session.id, [_cli_tag(tag) for tag in args.set])
        else:
            tags = list(session.tags)
            if args.add:
                tags = store.add_session_tags(session.id, [_cli_tag(tag) for tag in args.add])
            if args.remove:
                tags = store.remove_session_tags(session.id, [_cli_tag(tag) for tag in args.remove])

        refreshed = store.get_session(session.id) or session
        if args.json:
            print(
                json.dumps(
                    {"session": _session_record(refreshed), "tags": list(tags)},
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        print(f"{refreshed.id}  {refreshed.title}")
        print("Tags: " + (" ".join(f"#{tag}" for tag in tags) if tags else "-"))
    finally:
        store.close()
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    return _cmd_set_archive(args, archived=True)


def cmd_unarchive(args: argparse.Namespace) -> int:
    return _cmd_set_archive(args, archived=False)


def _cmd_set_archive(args: argparse.Namespace, *, archived: bool) -> int:
    store = ChatStore()
    try:
        session = store.get_session(args.session)
        if session is None:
            raise ConfigError(f"Session nicht eindeutig gefunden: {args.session}")
        session = store.set_session_archived(session.id, archived)
        if args.json:
            print(
                json.dumps(
                    {"session": _session_record(session)},
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        state = "Archiviert" if archived else "Wiederhergestellt"
        print(f"{state}: {session.id}  {session.title}")
    finally:
        store.close()
    return 0


def _profile_record(name: str, profile: Profile, *, is_default: bool) -> dict[str, object]:
    return {
        "name": name,
        "label": profile.display_name,
        "default": is_default,
        "base_url": profile.base_url,
        "api_mode": profile.api_mode,
        "api_key": redact_secret(profile.api_key),
        "model": profile.model,
        "models": profile.models or [profile.model],
        "model_aliases": profile.model_aliases or {},
        "temperature": profile.temperature,
        "top_p": profile.top_p,
        "max_tokens": profile.max_tokens,
        "reasoning_effort": profile.reasoning_effort,
        "timeout_seconds": profile.timeout_seconds,
        "stream": profile.stream,
        "send_temperature": profile.send_temperature,
        "send_top_p": profile.send_top_p,
    }


def _usage_record(result: ChatResult) -> dict[str, int] | None:
    record = token_usage_record(result.usage)
    return record or None


def _assistant_message_metadata(result: ChatResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    usage = token_usage_record(result.usage)
    return {"usage": usage} if usage else None


def _model_record(
    profile: Profile,
    *,
    is_default: bool,
    live_models: list[str] | None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "name": profile.name,
        "label": profile.display_name,
        "default": is_default,
        "base_url": profile.base_url,
        "api_mode": profile.api_mode,
        "selected_model": profile.model,
        "configured_models": profile.models or [profile.model],
    }
    if live_models is not None:
        record["live_models"] = live_models
    return record


def _session_record(session: Session) -> dict[str, object]:
    return {
        "id": session.id,
        "title": session.title,
        "profile": session.profile,
        "model": session.model,
        "folder_id": session.folder_id,
        "pinned": session.pinned,
        "archived": session.archived,
        "tags": list(session.tags),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def _stats_record(stats: StoreStats) -> dict[str, object]:
    return {
        "database": stats.database_path,
        "sessions": {
            "total": stats.sessions_total,
            "active": stats.sessions_active,
            "archived": stats.sessions_archived,
            "pinned": stats.sessions_pinned,
            "unfiled": stats.sessions_unfiled,
        },
        "messages": {
            "total": stats.messages_total,
            "roles": [
                {"role": role, "messages": count}
                for role, count in stats.message_roles
            ],
        },
        "usage": {
            "records": stats.usage_records,
            "input_tokens": stats.usage_input_tokens,
            "output_tokens": stats.usage_output_tokens,
            "total_tokens": stats.usage_total_tokens,
            "cached_input_tokens": stats.usage_cached_input_tokens,
            "reasoning_tokens": stats.usage_reasoning_tokens,
        },
        "folders": {
            "total": stats.folders_total,
            "with_system_prompt": stats.folders_with_system_prompt,
        },
        "tags": {
            "total": stats.tags_total,
            "assignments": stats.tag_links_total,
            "tagged_sessions": stats.tagged_sessions,
        },
        "profiles": [
            {"profile": profile, "sessions": count}
            for profile, count in stats.session_profiles
        ],
        "models": [
            {"model": model, "sessions": count}
            for model, count in stats.session_models
        ],
    }


def _context_record(session: Session, estimate: ContextEstimate) -> dict[str, object]:
    return {
        "session": {
            "id": session.id,
            "title": session.title,
            "profile": session.profile,
            "model": session.model,
        },
        "messages": {
            "stored": estimate.messages_total,
            "next_request": estimate.history_messages,
            "max_history_messages": estimate.max_history_messages,
        },
        "characters": {
            "system": estimate.system_chars,
            "messages": estimate.history_chars,
            "total": estimate.total_chars,
        },
        "estimate": {
            "approx_tokens": estimate.approx_tokens,
            "method": "ceil(characters/4)",
        },
    }


def _template_record(name: str, template: str) -> dict[str, object]:
    lines = template.splitlines() or [""]
    preview = " ".join(lines[0].split())
    if len(preview) > 120:
        preview = preview[:117].rstrip() + "..."
    return {
        "name": name,
        "preview": preview,
        "lines": len(lines),
        "characters": len(template),
        "has_input_placeholder": "input" in template_variables(template),
        "variables": list(template_variables(template)),
        "custom_variables": list(custom_template_variables(template)),
    }


def _format_session_line(session: Session) -> str:
    pin = "*" if session.pinned else " "
    archive = "A" if session.archived else " "
    tags = " ".join(f"#{tag}" for tag in session.tags)
    suffix = f"  {tags}" if tags else ""
    return f"{pin}{archive} {session.id}  {_backend_label(session):18}  {session.title}{suffix}"


def _archive_filter_from_args(args: argparse.Namespace) -> str:
    if getattr(args, "archived", False) and getattr(args, "all", False):
        raise ConfigError("--archived und --all schliessen sich aus.")
    if getattr(args, "archived", False):
        return "archived"
    if getattr(args, "all", False):
        return "all"
    return "active"


def _cli_tag(tag: object) -> str:
    try:
        return normalize_tag(tag)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc


def _validate_folder_backend(cfg: AppConfig, profile_name: str, model: str) -> tuple[str, str]:
    clean_profile = profile_name.strip()
    clean_model = model.strip()
    if clean_profile:
        profile = cfg.profile(clean_profile).with_overrides(model=clean_model or None)
        clean_profile = profile.name
    elif clean_model:
        cfg.profile(None).with_overrides(model=clean_model)
    return clean_profile, clean_model


def _message_record(message: object) -> dict[str, object]:
    return {
        "id": getattr(message, "id"),
        "session_id": getattr(message, "session_id"),
        "role": getattr(message, "role"),
        "content": getattr(message, "content"),
        "created_at": getattr(message, "created_at"),
    }


def _folder_record(
    folder: Folder,
    *,
    include_system_prompt: bool,
    include_context: bool = False,
) -> dict[str, object]:
    record: dict[str, object] = {
        "id": folder.id,
        "name": folder.name,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
        "has_system_prompt": bool(folder.system_prompt),
        "has_context": bool(folder.context),
        "has_default_backend": bool(folder.default_profile or folder.default_model),
    }
    if folder.default_profile:
        record["default_profile"] = folder.default_profile
    if folder.default_model:
        record["default_model"] = folder.default_model
    if include_system_prompt:
        record["system_prompt"] = folder.system_prompt
    if include_context:
        record["context"] = folder.context
    return record


def _session_export_payload(store: ChatStore, session: Session) -> dict[str, object]:
    return {
        "session": {
            **_session_record(session),
            "system_prompt": session.system_prompt,
        },
        "messages": [_message_record(message) for message in store.messages(session.id)],
    }


def _folder_export_record(
    store: ChatStore,
    folder: str,
    folder_id: str | None,
) -> dict[str, object]:
    if folder_id == "__none__":
        return {
            "id": None,
            "name": "Ohne Ordner",
            "kind": "unfiled",
        }
    if folder_id is None:
        return {
            "id": None,
            "name": "Alle Sessions",
            "kind": "all",
        }
    item = store.get_folder(folder_id)
    if item is None:
        return {
            "id": folder_id,
            "name": folder,
            "kind": "folder",
        }
    record = _folder_record(item, include_system_prompt=True, include_context=True)
    record["kind"] = "folder"
    return record


def _folder_export_payload(
    store: ChatStore,
    folder: str,
    folder_id: str | None,
    title: str,
    sort: str,
    sessions: list[Session],
) -> dict[str, object]:
    return {
        "format": "telachat.folder.v1",
        "title": title,
        "folder": _folder_export_record(store, folder, folder_id),
        "sort": sort,
        "sessions": [_session_export_payload(store, session) for session in sessions],
    }


def _folder_bundle_manifest(
    payload: dict[str, object],
    archive_filter: str,
) -> dict[str, object]:
    sessions = payload.get("sessions")
    session_count = len(sessions) if isinstance(sessions, list) else 0
    message_count = 0
    if isinstance(sessions, list):
        for item in sessions:
            if isinstance(item, dict) and isinstance(item.get("messages"), list):
                message_count += len(item["messages"])
    return {
        "app": "telachat",
        "format": "telachat.folder-bundle.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "folder_export_format": payload.get("format"),
        "title": payload.get("title"),
        "folder": payload.get("folder"),
        "sort": payload.get("sort"),
        "archive_filter": archive_filter,
        "contains_config": False,
        "contains_api_keys": False,
        "files": ["folder.json", "manifest.json"],
        "counts": {
            "sessions": session_count,
            "messages": message_count,
        },
    }


def _clean_session_import_payload(payload: object) -> tuple[dict[str, object], list[tuple[str, str]]]:
    if not isinstance(payload, dict):
        raise ConfigError("Importsession ist kein Objekt.")
    source_session = payload.get("session")
    source_messages = payload.get("messages")
    if not isinstance(source_session, dict) or not isinstance(source_messages, list):
        raise ConfigError("Importdatei braucht 'session' und 'messages'.")
    clean_messages: list[tuple[str, str]] = []
    for item in source_messages:
        if not isinstance(item, dict):
            raise ConfigError("Importnachricht ist kein Objekt.")
        role = str(item.get("role") or "")
        if role not in {"user", "assistant", "system"}:
            raise ConfigError(f"Ungueltige Importrolle: {role or '<leer>'}")
        content = item.get("content")
        if not isinstance(content, str):
            raise ConfigError("Importnachricht braucht Textinhalt.")
        clean_messages.append((role, content))
    return (
        {
            "title": str(source_session.get("title") or "Importierte Session"),
            "profile": str(source_session.get("profile") or "tki"),
            "model": str(source_session.get("model") or ""),
            "system_prompt": str(source_session.get("system_prompt") or ""),
            "archived": _clean_import_bool(source_session.get("archived", False), "archived"),
            "tags": _clean_import_tags(source_session.get("tags")),
        },
        clean_messages,
    )


def _clean_import_bool(value: object, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise ConfigError(f"Session-{name} muss ein Boolean sein.")


def _clean_import_tags(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError("Session-Tags muessen eine Liste sein.")
    tags: list[str] = []
    for item in value:
        tags.append(_cli_tag(item))
    return tags


def _folder_import_target(store: ChatStore, payload: dict[str, object], override: str | None) -> Folder | None:
    if override:
        return store.create_folder(override)
    folder = payload.get("folder")
    if not isinstance(folder, dict) or folder.get("kind") != "folder":
        return None
    name = str(folder.get("name") or "").strip()
    if not name:
        return None
    return store.create_folder(
        name,
        system_prompt=str(folder.get("system_prompt") or ""),
        context=str(folder.get("context") or ""),
        default_profile=str(folder.get("default_profile") or ""),
        default_model=str(folder.get("default_model") or ""),
    )


def _folder_import_preview(payload: dict[str, object], override: str | None) -> dict[str, object] | None:
    if override:
        return {
            "name": override,
            "source": "override",
        }
    folder = payload.get("folder")
    if not isinstance(folder, dict) or folder.get("kind") != "folder":
        return None
    name = str(folder.get("name") or "").strip()
    if not name:
        return None
    return {
        "name": name,
        "source": "bundle",
        "has_system_prompt": bool(folder.get("system_prompt")),
        "has_context": bool(folder.get("context")),
        "has_default_backend": bool(folder.get("default_profile") or folder.get("default_model")),
    }


def cmd_fork(args: argparse.Namespace) -> int:
    store = ChatStore()
    try:
        fork = store.fork_session(args.session, args.title)
        print(f"Fork: {fork.id}  {_backend_label(fork):18}  {fork.title}")
    except KeyError as exc:
        raise ConfigError(f"Session nicht eindeutig gefunden: {args.session}") from exc
    finally:
        store.close()
    return 0


def _resolve_folder_filter(store: ChatStore, folder: str | None) -> str | None:
    if not folder:
        return None
    clean = folder.strip()
    lower = clean.lower()
    if lower in {"all", "alle", "*"}:
        return None
    if lower in {"none", "ohne", "ohne ordner", "unfiled"}:
        return "__none__"
    matches = [
        item
        for item in store.list_folders()
        if item.id == clean
        or item.id.startswith(clean)
        or item.name.lower() == lower
    ]
    if len(matches) != 1:
        raise ConfigError(f"Ordner nicht eindeutig gefunden: {folder}")
    return matches[0].id


def _resolve_real_folder(store: ChatStore, folder: str) -> str:
    clean = folder.strip()
    matches = [
        item
        for item in store.list_folders()
        if item.id.startswith(clean) or item.name.lower() == clean.lower()
    ]
    if not matches:
        raise ConfigError(f"Ordner nicht gefunden: {folder}")
    if len(matches) > 1:
        raise ConfigError(f"Ordner nicht eindeutig gefunden: {folder}")
    return matches[0].id


def cmd_export(args: argparse.Namespace) -> int:
    store = ChatStore()
    try:
        session = store.get_session(args.session)
        if session is None:
            raise ConfigError(f"Session nicht eindeutig gefunden: {args.session}")
        if args.json:
            payload = {
                "format": "telachat.session.v1",
                **_session_export_payload(store, session),
            }
            text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
            if args.output:
                args.output.write_text(text, encoding="utf-8")
                print(args.output)
            else:
                print(text, end="")
            return 0
        markdown = store.export_markdown(session.id)
        if args.output:
            args.output.write_text(markdown, encoding="utf-8")
            print(args.output)
        else:
            print(markdown, end="")
    finally:
        store.close()
    return 0


def cmd_export_folder(args: argparse.Namespace) -> int:
    if args.bundle and (args.json or args.single_file):
        raise ConfigError("--bundle kann nicht mit --json oder --single-file kombiniert werden.")
    store = ChatStore()
    try:
        folder_id = _resolve_folder_filter(store, args.folder)
        archive_filter = _archive_filter_from_args(args)
        sessions = store.list_sessions(
            10000,
            folder_id=folder_id,
            sort=SESSION_SORTS[args.sort],
            archive=archive_filter,
        )
        title = _folder_export_title(store, args.folder, folder_id)
        if args.bundle:
            payload = _folder_export_payload(store, args.folder, folder_id, title, args.sort, sessions)
            target = _folder_bundle_target(args.output, title)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "folder.json",
                    json.dumps(payload, indent=2, sort_keys=True) + "\n",
                )
                archive.writestr(
                    "manifest.json",
                    json.dumps(_folder_bundle_manifest(payload, archive_filter), indent=2, sort_keys=True) + "\n",
                )
            print(target)
            return 0
        if args.json:
            payload = _folder_export_payload(store, args.folder, folder_id, title, args.sort, sessions)
            text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text, encoding="utf-8")
                print(args.output)
            else:
                print(text, end="")
            return 0
        if not sessions:
            print("Keine Sessions fuer diesen Export gefunden.")
            return 0
        if args.single_file:
            markdown = _export_sessions_markdown(store, sessions, title)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(markdown, encoding="utf-8")
                print(args.output)
            else:
                print(markdown, end="")
            return 0

        output_dir = args.output or Path(f"telachat-export-{_safe_filename(title)}")
        output_dir.mkdir(parents=True, exist_ok=True)
        index_lines = [
            f"# Telachat Export: {title}",
            "",
            f"- Sessions: {len(sessions)}",
            "",
        ]
        for session in sessions:
            file_name = f"{_safe_filename(session.title)}-{session.id}.md"
            path = output_dir / file_name
            path.write_text(store.export_markdown(session.id), encoding="utf-8")
            index_lines.append(f"- [{session.title}]({file_name})")
        (output_dir / "index.md").write_text("\n".join(index_lines).rstrip() + "\n", encoding="utf-8")
        print(output_dir)
        return 0
    finally:
        store.close()


def cmd_import_session(args: argparse.Namespace) -> int:
    try:
        payload = json.loads(args.session_json.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Importdatei kann nicht gelesen werden: {args.session_json}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError("Importdatei ist nicht UTF-8-kodiert.") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Ungueltige JSON-Importdatei: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("format") != "telachat.session.v1":
        raise ConfigError("Importdatei ist kein telachat.session.v1 Export.")
    session_meta, clean_messages = _clean_session_import_payload(payload)
    title = args.title or str(session_meta["title"])
    if args.dry_run:
        if args.json:
            print(
                json.dumps(
                    {
                        "dry_run": True,
                        "folder": args.folder,
                        "messages": len(clean_messages),
                        "session": {
                            **session_meta,
                            "title": title,
                        },
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            target = f" in Ordner {args.folder}" if args.folder else ""
            print(f"Trockenlauf: 1 Session  {len(clean_messages)} Nachrichten{target}  {title}")
        return 0

    store = ChatStore()
    try:
        folder_id = store.create_folder(args.folder).id if args.folder else None
        imported = store.create_session(
            title=title,
            profile=str(session_meta["profile"]),
            model=str(session_meta["model"]),
            system_prompt=str(session_meta["system_prompt"]),
            folder_id=folder_id,
            archived=bool(session_meta["archived"]),
        )
        if session_meta["tags"]:
            store.set_session_tags(imported.id, list(session_meta["tags"]))
        count = 0
        for role, content in clean_messages:
            store.add_message(imported.id, role, content)
            count += 1
        imported = store.get_session(imported.id) or imported
        if args.json:
            print(
                json.dumps(
                    {
                        "imported": _session_record(imported),
                        "messages": count,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"Importiert: {imported.id}  {count} Nachrichten  {imported.title}")
    finally:
        store.close()
    return 0


def cmd_import_folder(args: argparse.Namespace) -> int:
    try:
        payload = _read_folder_export_payload(args.folder_export)
    except OSError as exc:
        raise ConfigError(f"Importdatei kann nicht gelesen werden: {args.folder_export}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError("Importdatei ist nicht UTF-8-kodiert.") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Ungueltige JSON-Importdatei: {exc}") from exc
    except zipfile.BadZipFile as exc:
        raise ConfigError(f"Ungueltiges Ordner-Bundle: {args.folder_export}") from exc
    if not isinstance(payload, dict) or payload.get("format") != "telachat.folder.v1":
        raise ConfigError("Importdatei ist kein telachat.folder.v1 Export.")
    source_sessions = payload.get("sessions")
    if not isinstance(source_sessions, list):
        raise ConfigError("Importdatei braucht 'sessions'.")

    clean_sessions: list[tuple[dict[str, object], list[tuple[str, str]]]] = []
    for item in source_sessions:
        clean_sessions.append(_clean_session_import_payload(item))
    total_messages = sum(len(messages) for _, messages in clean_sessions)
    if args.dry_run:
        if args.json:
            print(
                json.dumps(
                    {
                        "dry_run": True,
                        "folder": _folder_import_preview(payload, args.folder),
                        "messages": total_messages,
                        "sessions": [
                            {
                                **session_meta,
                                "messages": len(messages),
                            }
                            for session_meta, messages in clean_sessions
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            target = f" in Ordner {args.folder}" if args.folder else ""
            print(f"Trockenlauf: {len(clean_sessions)} Sessions  {total_messages} Nachrichten{target}")
        return 0

    store = ChatStore()
    try:
        folder = _folder_import_target(store, payload, args.folder)
        imported_sessions: list[Session] = []
        written_messages = 0
        for session_meta, messages in clean_sessions:
            imported = store.create_session(
                title=str(session_meta["title"]),
                profile=str(session_meta["profile"]),
                model=str(session_meta["model"]),
                system_prompt=str(session_meta["system_prompt"]),
                folder_id=folder.id if folder else None,
                archived=bool(session_meta["archived"]),
            )
            if session_meta["tags"]:
                store.set_session_tags(imported.id, list(session_meta["tags"]))
            for role, content in messages:
                store.add_message(imported.id, role, content)
                written_messages += 1
            imported_sessions.append(store.get_session(imported.id) or imported)
        if args.json:
            folder_record = (
                _folder_record(folder, include_system_prompt=True, include_context=True)
                if folder
                else None
            )
            print(
                json.dumps(
                    {
                        "imported": {
                            "folder": folder_record,
                            "sessions": [_session_record(session) for session in imported_sessions],
                        },
                        "messages": written_messages,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            target = f" in Ordner {folder.name}" if folder else ""
            print(f"Importiert: {len(imported_sessions)} Sessions  {written_messages} Nachrichten{target}")
    finally:
        store.close()
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    store = ChatStore()
    try:
        store.delete_empty_sessions()
    finally:
        store.close()

    target = _backup_target(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    source_db = db_path()
    with tempfile.TemporaryDirectory() as tmp:
        backup_db = Path(tmp) / "history.sqlite3"
        _sqlite_backup(source_db, backup_db)
        manifest = _backup_manifest(cfg, backup_db)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(backup_db, "history.sqlite3")
            archive.writestr("config.redacted.toml", _redacted_config_toml(cfg))
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
    print(target)
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    backup = args.backup.expanduser()
    if not backup.exists():
        raise ConfigError(f"Backup nicht gefunden: {backup}")
    with tempfile.TemporaryDirectory() as tmp:
        backup_db = Path(tmp) / "history.sqlite3"
        try:
            with zipfile.ZipFile(backup) as archive:
                if "history.sqlite3" not in archive.namelist():
                    raise ConfigError("Backup enthaelt keine history.sqlite3.")
                with archive.open("history.sqlite3") as source, backup_db.open("wb") as target:
                    shutil.copyfileobj(source, target)
        except zipfile.BadZipFile as exc:
            raise ConfigError(f"Ungueltiges Backup-ZIP: {backup}") from exc

        store = ChatStore()
        try:
            try:
                summary = store.import_history_database(backup_db, dry_run=args.dry_run)
            except (sqlite3.Error, ValueError) as exc:
                raise ConfigError(str(exc)) from exc
        finally:
            store.close()
    print(_restore_summary(summary))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    profile = cfg.profile(args.profile)
    if not args.json:
        print(f"{APP_TITLE} doctor")
        print(f"Config: {cfg.path}")
        print(f"SQLite: {db_path()}")
        print(f"Profil: {profile.name} ({profile.display_name})")
        print(f"API: {profile.base_url}")
        print(f"Model: {profile.model}")
        print(f"API-Key: {redact_secret(profile.api_key)}")
    client = OpenAICompatClient(profile, retries=1)
    models = client.list_models()
    if not args.json:
        print(f"/models: ok ({', '.join(models) if models else 'keine IDs gemeldet'})")
    chat_check: dict[str, object] | None = None
    if args.chat:
        messages = [
            {"role": "system", "content": cfg.default_system_prompt},
            {"role": "user", "content": "Antworte nur mit: OK"},
        ]
        result = client.chat(messages, stream=False)
        assert isinstance(result, ChatResult)
        label = "/responses" if profile.api_mode == "responses" else "/chat/completions"
        if profile.api_mode == "codex":
            label = "codex exec"
        chat_check = {
            "ok": True,
            "endpoint": label,
            "preview": result.content[:80],
        }
        usage = _usage_record(result)
        if usage:
            chat_check["usage"] = usage
        if not args.json:
            print(f"{label}: ok ({result.content[:80]!r})")
    if args.json:
        print(
            json.dumps(
                {
                    "app": APP_TITLE,
                    "config": str(cfg.path),
                    "sqlite": str(db_path()),
                    "profile": _profile_record(
                        profile.name,
                        profile,
                        is_default=profile.name == cfg.default_profile,
                    ),
                    "checks": {
                        "models": {"ok": True, "models": models},
                        "chat": chat_check,
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    return 0


def cmd_gtk_gui(args: argparse.Namespace) -> int:
    from .gtkgui import main as gtk_main

    return gtk_main([])


def cmd_tk_gui(args: argparse.Namespace) -> int:
    from .tkgui import main as tk_main

    return tk_main([])


def _selected_profile(cfg: object, args: argparse.Namespace) -> Profile:
    profile = cfg.profile(args.profile)
    return profile.with_overrides(
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        reasoning_effort=args.reasoning_effort,
        stream=False if args.no_stream else None,
    )


def _profile_for_loaded_session(
    cfg: object,
    args: argparse.Namespace,
    session: object,
) -> Profile:
    profile = cfg.profile(session.profile)
    return profile.with_overrides(
        model=args.model or session.model or None,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        reasoning_effort=args.reasoning_effort,
        stream=False if args.no_stream else None,
    )


def _secret_status(profile: Profile) -> tuple[bool, str]:
    if profile.api_mode == "codex" or profile.base_url == "codex://local":
        return True, "not-required"
    raw = profile.api_key or ""
    if not raw:
        return False, "missing:<empty>"
    try:
        resolved = profile.resolved_api_key()
    except (OSError, ConfigError) as exc:
        return False, f"missing:{redact_secret(raw)} ({exc.__class__.__name__})"
    if not resolved:
        return False, f"missing:{redact_secret(raw)}"
    return True, f"ok:{redact_secret(raw)}"


def install_readline_completion(cfg: object, store: ChatStore) -> object | None:
    try:
        import readline
    except ImportError:
        return None

    old_completer = readline.get_completer()
    old_delims = readline.get_completer_delims()
    matches: list[str] = []

    def completer(_text: str, state: int) -> str | None:
        nonlocal matches
        if state == 0:
            matches = cli_completion_candidates(readline.get_line_buffer(), cfg, store)
        if state >= len(matches):
            return None
        return matches[state]

    readline.set_completer(completer)
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("tab: complete")

    def restore() -> None:
        readline.set_completer(old_completer)
        readline.set_completer_delims(old_delims)

    return restore


def cli_completion_candidates(line: str, cfg: object, store: ChatStore) -> list[str]:
    return slash_completion_candidates(
        line,
        cfg,
        store,
        sort_names=SESSION_SORT_NAMES,
        theme_names=theme_labels().keys(),
    )


def _backend_label(session: object) -> str:
    if getattr(session, "model", ""):
        return f"{session.profile}/{session.model}"
    return session.profile


def _read_prompt(parts: Iterable[str], read_stdin: bool) -> str:
    if read_stdin:
        return sys.stdin.read().strip()
    joined = " ".join(parts).strip()
    if joined:
        return joined
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return input("Prompt> ").strip()


def _run_chat(profile: Profile, messages: list[dict[str, str]], *, stream: bool) -> str:
    client = OpenAICompatClient(profile, retries=1)
    result = client.chat(messages, stream=stream)
    if isinstance(result, ChatResult):
        print(result.content)
        return result.content
    chunks = []
    for chunk in result:
        chunks.append(chunk)
        print(chunk, end="", flush=True)
    print()
    return "".join(chunks)


def _handle_command(
    raw: str,
    cfg: object,
    store: ChatStore,
    profile: Profile,
    system_prompt: str,
    session: object,
    *,
    stream: bool,
) -> tuple[bool, object, Profile, str, object]:
    command, _, rest = raw.partition(" ")
    command = canonical_slash_command(command.lower())
    rest = rest.strip()
    if command == "/exit":
        return False, cfg, profile, system_prompt, session
    if command == "/help":
        print(slash_command_help())
    elif command == "/shortcuts":
        print(keyboard_shortcut_help())
    elif command == "/new":
        title = rest or "Neue Unterhaltung"
        session = store.create_session(
            title=title,
            profile=profile.name,
            model=profile.model,
            system_prompt=system_prompt,
        )
        print(f"Neue Session: {session.id}")
    elif command == "/rename":
        if not rest:
            print("Nutzung: /rename TITLE")
        else:
            session = store.update_session_title(session.id, rest)
            print(f"Umbenannt: {session.title}")
    elif command == "/delete":
        old_id = session.id
        store.delete_session(old_id)
        session = store.create_session(
            title="Neue Unterhaltung",
            profile=profile.name,
            model=profile.model,
            system_prompt=system_prompt,
        )
        print(f"Session geloescht: {old_id}")
        print(f"Neue Session: {session.id}")
    elif command == "/sessions":
        for item in store.list_sessions(20):
            print(_format_session_line(item))
    elif command == "/stats":
        for line in format_stats_lines(store.stats(), include_database=False):
            print(line)
    elif command == "/context":
        estimate = estimate_context(
            store.messages(session.id),
            system_prompt,
            max_history_messages=getattr(cfg, "max_history_messages", None),
        )
        for line in format_context_lines(estimate):
            print(line)
    elif command == "/doctor":
        try:
            models = OpenAICompatClient(profile, retries=1).list_models()
        except (ApiError, ConfigError, OSError) as exc:
            print(f"/models: Fehler ({exc})", file=sys.stderr)
        else:
            print(f"/models: ok ({', '.join(models) if models else 'keine IDs gemeldet'})")
    elif command == "/models":
        if rest and rest.lower() != "live":
            print("Nutzung: /models [live]")
        elif rest.lower() == "live":
            try:
                models = OpenAICompatClient(profile, retries=1).list_models()
            except (ApiError, ConfigError, OSError) as exc:
                print(f"/models: Fehler ({exc})", file=sys.stderr)
            else:
                print(f"/models: live ({', '.join(models) if models else 'keine IDs gemeldet'})")
        else:
            models = profile.models or [profile.model]
            print(f"/models: configured ({', '.join(models) if models else 'keine konfiguriert'})")
    elif command == "/archives":
        items = store.list_sessions(20, archive="archived")
        if not items:
            print("Keine archivierten Sessions.")
        for item in items:
            print(_format_session_line(item))
    elif command == "/load":
        if not rest:
            print("Nutzung: /load <session-id-oder-prefix>")
        else:
            loaded = store.get_session(rest)
            if loaded is None:
                print("Session nicht eindeutig gefunden.")
            else:
                session = loaded
                system_prompt = loaded.system_prompt
                print(f"Geladen: {loaded.id} {loaded.title}")
    elif command == "/pin":
        session = store.set_session_pinned(session.id, True)
        print("Session angeheftet.")
    elif command == "/unpin":
        session = store.set_session_pinned(session.id, False)
        print("Session geloest.")
    elif command == "/archive":
        session = store.set_session_archived(session.id, True)
        print("Session archiviert.")
    elif command == "/unarchive":
        session = store.set_session_archived(session.id, False)
        print("Session wiederhergestellt.")
    elif command == "/tag":
        if not rest:
            print("Tags: " + (" ".join(f"#{tag}" for tag in session.tags) if session.tags else "-"))
        else:
            try:
                tags = store.add_session_tags(session.id, rest.split())
                session = store.get_session(session.id) or session
            except (KeyError, ValueError) as exc:
                print(f"Fehler: {exc}", file=sys.stderr)
            else:
                print("Tags: " + (" ".join(f"#{tag}" for tag in tags) if tags else "-"))
    elif command == "/untag":
        if not rest:
            print("Nutzung: /untag TAG [TAG...]")
        else:
            try:
                tags = store.remove_session_tags(session.id, rest.split())
                session = store.get_session(session.id) or session
            except (KeyError, ValueError) as exc:
                print(f"Fehler: {exc}", file=sys.stderr)
            else:
                print("Tags: " + (" ".join(f"#{tag}" for tag in tags) if tags else "-"))
    elif command == "/tags":
        if rest:
            loaded = store.get_session(rest)
            if loaded is None:
                print("Session nicht eindeutig gefunden.")
            else:
                print("Tags: " + (" ".join(f"#{tag}" for tag in loaded.tags) if loaded.tags else "-"))
        else:
            tags = store.list_tags()
            if not tags:
                print("Keine Tags gespeichert.")
            for tag, count in tags:
                print(f"#{tag}  {count}")
    elif command == "/edit-last":
        if not rest:
            print("Nutzung: /edit-last TEXT")
        else:
            try:
                store.edit_last_user_message(session.id, rest)
                refreshed = store.get_session(session.id)
                if refreshed is not None:
                    session = refreshed
            except (KeyError, ValueError) as exc:
                print(f"Fehler: {exc}", file=sys.stderr)
            else:
                print("Letzte Nutzernachricht aktualisiert. /regen erzeugt eine neue Antwort.")
    elif command == "/fork":
        try:
            session = store.fork_session(session.id, rest or None)
            system_prompt = session.system_prompt
        except KeyError as exc:
            print(f"Fehler: {exc}", file=sys.stderr)
        else:
            print(f"Fork geladen: {session.id} {session.title}")
    elif command in {"/regen", "/regenerate"}:
        try:
            _regenerate_session(
                cfg=cfg,
                store=store,
                profile=profile,
                system_prompt=system_prompt,
                session=session,
                stream=stream,
            )
        except (ApiError, ConfigError, OSError) as exc:
            print(f"Fehler: {exc}", file=sys.stderr)
    elif command == "/templates":
        if not cfg.prompt_templates:
            print("Keine Prompt-Templates konfiguriert.")
        for name in sorted(cfg.prompt_templates):
            first_line = cfg.prompt_templates[name].splitlines()[0]
            print(f"{name:16} {first_line}")
    elif command == "/template":
        template_name, _, text = rest.partition(" ")
        if not template_name:
            print("Nutzung: /template NAME TEXT")
        else:
            try:
                prompt = _apply_prompt_template(cfg, template_name, text)
            except ConfigError as exc:
                print(f"Fehler: {exc}", file=sys.stderr)
            else:
                if session.title == "Neue Unterhaltung":
                    session = _retitle_session(store, session.id, title_from_prompt(prompt))
                if session.profile != profile.name or session.model != profile.model:
                    session = store.update_session_backend(session.id, profile.name, profile.model)
                store.add_message(session.id, "user", prompt)
                history = store.messages(session.id, limit=cfg.max_history_messages)
                messages = messages_for_api(system_prompt, history)
                try:
                    print("KI> ", end="", flush=True)
                    answer = _run_chat(profile, messages, stream=stream)
                except (ApiError, ConfigError, OSError) as exc:
                    print(f"\nFehler: {exc}", file=sys.stderr)
                else:
                    store.add_message(session.id, "assistant", answer)
    elif command == "/folder-prompt":
        folder_id = getattr(session, "folder_id", None)
        if not folder_id:
            print("Aktuelle Session liegt in keinem Ordner.")
        elif rest:
            folder = store.update_folder_system_prompt(folder_id, rest)
            print(f"Ordnerprompt gesetzt: {folder.name}")
        else:
            folder = store.get_folder(folder_id)
            if folder is None:
                print("Ordner nicht gefunden.")
            else:
                print(folder.system_prompt or "<leer>")
    elif command == "/folder-context":
        folder_id = getattr(session, "folder_id", None)
        if not folder_id:
            print("Aktuelle Session liegt in keinem Ordner.")
        elif rest:
            folder = store.update_folder_context(folder_id, rest)
            print(f"Ordner-Kontext gespeichert: {folder.name}")
        else:
            folder = store.get_folder(folder_id)
            if folder is None:
                print("Ordner nicht gefunden.")
            else:
                print(folder.context or "<leer>")
    elif command == "/folder":
        if not rest:
            folder = store.get_folder(session.folder_id) if session.folder_id else None
            print(f"Aktuell: {folder.name if folder else 'Ohne Ordner'}")
        else:
            folder = store.create_folder(rest)
            session = store.move_session(session.id, folder.id)
            if folder.system_prompt:
                system_prompt = folder.system_prompt
            print(f"Abgelegt in Ordner: {folder.name}")
    elif command == "/rename-folder":
        if not session.folder_id:
            print("Aktuelle Session liegt in keinem Ordner.")
        elif not rest:
            print("Nutzung: /rename-folder NAME")
        else:
            folder = store.update_folder_name(session.folder_id, rest)
            print(f"Ordner umbenannt: {folder.name}")
    elif command == "/delete-folder":
        if not session.folder_id:
            print("Aktuelle Session liegt in keinem Ordner.")
        else:
            folder = store.get_folder(session.folder_id)
            store.delete_folder(session.folder_id)
            refreshed = store.get_session(session.id)
            if refreshed is not None:
                session = refreshed
            print(f"Ordner geloescht: {folder.name if folder else session.folder_id}")
    elif command == "/move":
        if not rest:
            print("Nutzung: /move NAME")
        else:
            folder = store.create_folder(rest)
            session = store.move_session(session.id, folder.id)
            if folder.system_prompt:
                system_prompt = folder.system_prompt
            print(f"Chat abgelegt: {folder.name}")
    elif command == "/unfile":
        session = store.move_session(session.id, None)
        print("Chat aus Ordner geloest.")
    elif command == "/sort":
        sort_name = rest or "newest"
        sort_key = SESSION_SORTS.get(sort_name)
        if not sort_key:
            print("Nutzung: /sort newest|oldest|title|title-desc|provider")
        else:
            for item in store.list_sessions(20, sort=sort_key):
                print(_format_session_line(item))
    elif command == "/search":
        if not rest:
            print("Nutzung: /search TEXT")
        else:
            for item in store.list_sessions(20, query=rest):
                print(_format_session_line(item))
    elif command == "/find":
        if not rest:
            print("Nutzung: /find TEXT")
        else:
            matches = format_message_matches(store.messages(session.id), rest)
            if not matches:
                print("Keine Treffer in der aktuellen Unterhaltung.")
            else:
                print("Treffer:")
                for match in matches:
                    print(match)
    elif command in {"/profile", "/provider"}:
        if not rest:
            print(f"Aktiv: {profile.name} ({profile.display_name})")
        else:
            profile = cfg.profile(rest)
            session = store.update_session_backend(session.id, profile.name, profile.model)
            print(f"Aktiv: {profile.name} ({profile.display_name})")
    elif command == "/model":
        if not rest:
            print(f"Aktiv: {profile.model}")
        else:
            configured = profile.models or [profile.model]
            model = next((item for item in configured if item.lower() == rest.lower()), rest)
            profile = profile.with_overrides(model=model)
            session = store.update_session_backend(session.id, profile.name, profile.model)
            print(f"Modell: {profile.model}")
    elif command == "/theme":
        labels = theme_labels()
        if not rest:
            width = max(14, *(len(name) for name in labels))
            print(f"Aktives Theme: {cfg.theme}")
            for name, label in labels.items():
                marker = "*" if name == cfg.theme else " "
                print(f"{marker} {name:{width}} {label}")
        else:
            try:
                theme = set_config_theme(rest, cfg.path)
            except ValueError as exc:
                print(f"Fehler: {exc}", file=sys.stderr)
            else:
                cfg = load_config(cfg.path)
                print(f"Theme gesetzt: {theme}")
    elif command == "/profiles":
        for name, item in sorted(cfg.profiles.items()):
            marker = "*" if name == profile.name else " "
            print(f"{marker} {name}: {item.base_url} model={item.model}")
    elif command == "/permissions":
        print(f"Config: {cfg.path}")
        for name, item in sorted(cfg.profiles.items()):
            print(f"{name:12} api_key={redact_secret(item.api_key)}")
    elif command == "/system":
        if rest:
            system_prompt = rest
            print("System-Prompt gesetzt.")
        else:
            print(system_prompt)
    elif command == "/left":
        print("Die Seitenleiste gibt es nur in der GUI.")
    elif command == "/history":
        limit = int(rest) if rest.isdigit() else 12
        for message in store.messages(session.id, limit=limit):
            who = "Du" if message.role == "user" else "KI"
            print(f"{who}> {message.content}")
    elif command == "/export":
        output = Path(rest) if rest else Path(f"telachat-{session.id}.md")
        output.write_text(store.export_markdown(session.id), encoding="utf-8")
        print(output)
    else:
        print(f"Unbekannter Befehl: {command}. /help hilft.")
    return True, cfg, profile, system_prompt, session


def _retitle_session(store: ChatStore, session_id: str, title: str) -> object:
    store.db.execute(
        "UPDATE sessions SET title = ?, updated_at = strftime('%s','now') WHERE id = ?",
        (title, session_id),
    )
    store.db.commit()
    session = store.get_session(session_id)
    if session is None:
        raise ConfigError("Interner Fehler: Session nach Umbenennung fehlt.")
    return session


def _regenerate_session(
    *,
    cfg: object,
    store: ChatStore,
    profile: Profile,
    system_prompt: str,
    session: object,
    stream: bool,
) -> None:
    store.delete_last_assistant_message(session.id)
    history = store.messages(session.id, limit=cfg.max_history_messages)
    if not any(message.role == "user" for message in history):
        print("Keine Nutzernachricht zum Neu-Generieren vorhanden.")
        return
    messages = messages_for_api(system_prompt, history)
    print("KI> ", end="", flush=True)
    answer = _run_chat(profile, messages, stream=stream)
    store.add_message(session.id, "assistant", answer)


def _parse_template_values(raw_values: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_value in raw_values:
        name, separator, value = raw_value.partition("=")
        clean_name = name.strip()
        if not separator or not clean_name:
            raise ConfigError("Template-Variable muss NAME=VALUE verwenden.")
        if not is_template_variable_name(clean_name):
            raise ConfigError(f"Ungueltiger Template-Variablenname: {clean_name}")
        if clean_name in SUPPORTED_TEMPLATE_VARIABLES:
            raise ConfigError(f"Template-Variable ist eingebaut: {clean_name}")
        values[clean_name] = value
    return values


def _apply_prompt_template(
    cfg: object,
    name: str,
    text: str = "",
    *,
    values: dict[str, str] | None = None,
) -> str:
    try:
        template = cfg.prompt_templates[name]
    except KeyError as exc:
        available = ", ".join(sorted(cfg.prompt_templates)) or "<keine>"
        raise ConfigError(
            f"Prompt-Template '{name}' existiert nicht. Verfuegbar: {available}"
        ) from exc
    return render_prompt_template(template, text, values=values)


def _folder_export_title(store: ChatStore, folder: str, folder_id: str | None) -> str:
    if folder_id == "__none__":
        return "Ohne Ordner"
    if folder_id is None:
        return "Alle Sessions"
    item = store.get_folder(folder_id)
    return item.name if item else folder


def _export_sessions_markdown(store: ChatStore, sessions: list[object], title: str) -> str:
    lines = [
        f"# Telachat Export: {title}",
        "",
        f"- Sessions: {len(sessions)}",
        "",
    ]
    for session in sessions:
        lines.append(store.export_markdown(session.id).rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _safe_filename(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip(".-_")
    return clean[:80] or "telachat"


def _folder_bundle_target(output: Path | None, title: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_name = f"telachat-folder-{_safe_filename(title)}-{stamp}.zip"
    if output is None:
        return Path(default_name)
    target = output.expanduser()
    if target.suffix.lower() == ".zip":
        return target
    return target / default_name


def _read_folder_export_payload(path: Path) -> object:
    source = path.expanduser()
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            try:
                raw = archive.read("folder.json")
            except KeyError as exc:
                raise ConfigError("Ordner-Bundle enthaelt keine folder.json.") from exc
        return json.loads(raw.decode("utf-8"))
    return json.loads(source.read_text(encoding="utf-8"))


def _backup_target(output: Path | None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_name = f"telachat-backup-{stamp}.zip"
    if output is None:
        return state_dir() / "backups" / default_name
    target = output.expanduser()
    if target.suffix.lower() == ".zip":
        return target
    return target / default_name


def _sqlite_backup(source: Path, target: Path) -> None:
    source.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _backup_manifest(cfg: object, backup_db: Path) -> dict[str, object]:
    counts = {"sessions": 0, "folders": 0, "messages": 0}
    db = sqlite3.connect(backup_db)
    try:
        for table in counts:
            try:
                counts[table] = int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            except sqlite3.Error:
                counts[table] = 0
    finally:
        db.close()
    return {
        "app": "telachat",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "config_path": str(cfg.path),
        "database_path": str(db_path()),
        "default_profile": cfg.default_profile,
        "theme": cfg.theme,
        "app_icon": cfg.app_icon,
        "chat_background_image": cfg.chat_background_image,
        "validate_profile_headers": cfg.validate_profile_headers,
        "skill_watchdog_enabled": cfg.skill_watchdog_enabled,
        "profiles": {
            name: {
                "api_mode": profile.api_mode,
                "base_url": profile.base_url,
                "model": profile.model,
                "models": list(profile.models or [profile.model]),
                "model_aliases": dict(profile.model_aliases or {}),
                "api_key": redact_secret(profile.api_key),
                "send_temperature": profile.send_temperature,
                "send_top_p": profile.send_top_p,
            }
            for name, profile in sorted(cfg.profiles.items())
        },
        "prompt_templates": sorted(cfg.prompt_templates),
        "counts": counts,
    }


def _restore_summary(summary: HistoryImportSummary) -> str:
    prefix = "Wuerde importieren" if summary.dry_run else "Importiert"
    return (
        f"{prefix}: {summary.sessions} Sessions, "
        f"{summary.messages} Nachrichten, {summary.folders} neue Ordner"
    )


def _redacted_config_toml(cfg: object, profiles: list[object] | None = None) -> str:
    lines = [
        "# Redacted Telachat config.",
        "# Secret values are not included.",
        f"default_profile = {_toml_string(cfg.default_profile)}",
        f"theme = {_toml_string(cfg.theme)}",
        f"app_icon = {_toml_string(cfg.app_icon)}",
        f"chat_background_image = {_toml_string(cfg.chat_background_image)}",
        f"validate_profile_headers = {str(cfg.validate_profile_headers).lower()}",
        f"skill_watchdog_enabled = {str(cfg.skill_watchdog_enabled).lower()}",
        f"default_system_prompt = {_toml_string(cfg.default_system_prompt)}",
        f"max_history_messages = {cfg.max_history_messages}",
        "",
    ]
    if cfg.prompt_templates:
        lines.append("[prompt_templates]")
        for name, template in sorted(cfg.prompt_templates.items()):
            lines.append(f"{_toml_key(name)} = {_toml_string(template)}")
        lines.append("")
    profile_items = (
        [(profile.name, profile) for profile in profiles]
        if profiles is not None
        else sorted(cfg.profiles.items())
    )
    for name, profile in profile_items:
        lines.append(f"[profiles.{_toml_key(name)}]")
        lines.append(f"label = {_toml_string(profile.label)}")
        lines.append(f"base_url = {_toml_string(profile.base_url)}")
        lines.append(f"api_key = {_toml_string(redact_secret(profile.api_key))}")
        lines.append(f"model = {_toml_string(profile.model)}")
        lines.append(
            "models = ["
            + ", ".join(_toml_string(item) for item in (profile.models or [profile.model]))
            + "]"
        )
        lines.append(f"temperature = {profile.temperature}")
        lines.append(f"top_p = {profile.top_p}")
        lines.append(f"max_tokens = {profile.max_tokens}")
        if profile.reasoning_effort:
            lines.append(f"reasoning_effort = {_toml_string(profile.reasoning_effort)}")
        lines.append(f"timeout_seconds = {profile.timeout_seconds}")
        lines.append(f"stream = {str(profile.stream).lower()}")
        lines.append(f"api_mode = {_toml_string(profile.api_mode)}")
        lines.append(f"send_temperature = {str(profile.send_temperature).lower()}")
        lines.append(f"send_top_p = {str(profile.send_top_p).lower()}")
        if profile.extra_headers:
            lines.append("")
            lines.append(f"[profiles.{_toml_key(name)}.headers]")
            for header, value in sorted(profile.extra_headers.items()):
                lines.append(
                    f"{_toml_key(header)} = {_toml_string(_redacted_header_value(header, value))}"
                )
        if profile.model_aliases:
            lines.append("")
            lines.append(f"[profiles.{_toml_key(name)}.model_aliases]")
            for alias, model in sorted(profile.model_aliases.items()):
                lines.append(f"{_toml_key(alias)} = {_toml_string(model)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_key(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value
    return _toml_string(value)


def _redacted_header_value(header: str, value: str) -> str:
    if re.search(r"auth|cookie|credential|key|secret|token", header, re.IGNORECASE):
        return redact_secret(value)
    return value
