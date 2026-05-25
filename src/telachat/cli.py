from __future__ import annotations

import argparse
import os
import re
import sys
import textwrap
from collections.abc import Iterable
from pathlib import Path

from .client import ApiError, ChatResult, OpenAICompatClient
from .commands import (
    canonical_slash_command,
    slash_command_help,
    slash_command_name_suggestions,
)
from .config import ConfigError, Profile, ensure_default_config, load_config, redact_secret
from .defaults import APP_TITLE
from .paths import config_path, db_path
from .store import ChatStore, messages_for_api, title_from_prompt


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
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Standardkonfiguration anlegen")
    p_init.add_argument("--force", action="store_true", help="Config ueberschreiben")
    p_init.set_defaults(func=cmd_init)

    p_profiles = sub.add_parser("profiles", help="Profile anzeigen")
    p_profiles.set_defaults(func=cmd_profiles)

    p_templates = sub.add_parser("templates", help="Prompt-Templates anzeigen")
    p_templates.set_defaults(func=cmd_templates)

    p_folders = sub.add_parser("folders", help="Ordner anzeigen/verwalten")
    p_folders.add_argument("--create", metavar="NAME", help="Ordner anlegen")
    p_folders.add_argument("--system", help="System-Prompt fuer --create")
    p_folders.add_argument(
        "--set-system",
        nargs=2,
        metavar=("FOLDER", "PROMPT"),
        help="Default-Systemprompt fuer Ordner setzen",
    )
    p_folders.add_argument(
        "--show-system",
        action="store_true",
        help="Ordner-Systemprompts voll anzeigen",
    )
    p_folders.set_defaults(func=cmd_folders)

    p_ask = sub.add_parser("ask", help="Einzelne Frage stellen")
    add_chat_options(p_ask)
    p_ask.add_argument("prompt", nargs="*", help="Prompt; leer liest interaktiv/stdin")
    p_ask.add_argument("--stdin", action="store_true", help="Prompt aus stdin lesen")
    p_ask.add_argument("--save", action="store_true", help="Frage und Antwort speichern")
    p_ask.add_argument("--template", "-t", help="Prompt-Template auf den Prompt anwenden")
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
    p_sessions.add_argument(
        "--sort",
        choices=sorted(SESSION_SORTS),
        default="newest",
        help="Sortierung der Sessionliste",
    )
    p_sessions.set_defaults(func=cmd_sessions)

    p_export = sub.add_parser("export", help="Session als Markdown exportieren")
    p_export.add_argument("session", help="Session-ID oder Prefix")
    p_export.add_argument("-o", "--output", type=Path, help="Ausgabedatei")
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
        "--single-file",
        action="store_true",
        help="Alle Chats in eine Markdown-Datei schreiben",
    )
    p_export_folder.set_defaults(func=cmd_export_folder)

    p_doctor = sub.add_parser("doctor", help="Konfiguration/API pruefen")
    p_doctor.add_argument("-p", "--profile", help="Profilname")
    p_doctor.add_argument("--chat", action="store_true", help="Auch kurze Chat-Anfrage testen")
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


def cmd_templates(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if not cfg.prompt_templates:
        print("Keine Prompt-Templates konfiguriert.")
        return 0
    for name in sorted(cfg.prompt_templates):
        first_line = cfg.prompt_templates[name].splitlines()[0]
        print(f"{name:16} {first_line}")
    return 0


def cmd_folders(args: argparse.Namespace) -> int:
    store = ChatStore()
    try:
        if args.create:
            folder = store.create_folder(args.create, system_prompt=args.system or "")
            print(f"Ordner bereit: {folder.id} {folder.name}")
        if args.set_system:
            folder_ref, prompt = args.set_system
            folder_id = _resolve_real_folder(store, folder_ref)
            folder = store.update_folder_system_prompt(folder_id, prompt)
            print(f"System-Prompt gesetzt: {folder.name}")
        folders = store.list_folders()
        if not folders:
            print("Keine Ordner vorhanden.")
            return 0
        for folder in folders:
            marker = "system" if folder.system_prompt else "-"
            print(f"{folder.id}  {marker:6}  {folder.name}")
            if args.show_system and folder.system_prompt:
                print(textwrap.indent(folder.system_prompt, "    "))
        return 0
    finally:
        store.close()


def cmd_ask(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    profile = _selected_profile(cfg, args)
    system_prompt = args.system or cfg.default_system_prompt
    prompt = _read_prompt(args.prompt, args.stdin)
    if not prompt:
        raise ConfigError("Kein Prompt angegeben.")
    if args.template:
        prompt = _apply_prompt_template(cfg, args.template, prompt)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    response = _run_chat(profile, messages, stream=not args.no_stream)
    if args.save:
        store = ChatStore()
        try:
            session = store.create_session(
                title=title_from_prompt(prompt),
                profile=profile.name,
                system_prompt=system_prompt,
            )
            store.add_message(session.id, "user", prompt)
            store.add_message(session.id, "assistant", response)
            print(f"\n[gespeichert: {session.id}]", file=sys.stderr)
        finally:
            store.close()
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
            system_prompt = session.system_prompt
            print(f"{APP_TITLE}: Session {session.id} geladen: {session.title}")
        if session is None:
            session = store.create_session(
                title="Neue Unterhaltung",
                profile=profile.name,
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
                keep_going, profile, system_prompt, session = _handle_command(
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
            store.add_message(session.id, "user", user_input)
            history = store.messages(session.id, limit=cfg.max_history_messages)
            messages = messages_for_api(system_prompt, history)
            try:
                print("KI> ", end="", flush=True)
                answer = _run_chat(profile, messages, stream=not args.no_stream)
            except ApiError as exc:
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
        )
        if not sessions:
            print("Keine Sessions gespeichert.")
            return 0
        for session in sessions:
            pin = "*" if session.pinned else " "
            print(f"{pin} {session.id}  {session.profile:12}  {session.title}")
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
    store = ChatStore()
    try:
        folder_id = _resolve_folder_filter(store, args.folder)
        sessions = store.list_sessions(
            10000,
            folder_id=folder_id,
            sort=SESSION_SORTS[args.sort],
        )
        if not sessions:
            print("Keine Sessions fuer diesen Export gefunden.")
            return 0
        title = _folder_export_title(store, args.folder, folder_id)
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


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    profile = cfg.profile(args.profile)
    print(f"{APP_TITLE} doctor")
    print(f"Config: {cfg.path}")
    print(f"SQLite: {db_path()}")
    print(f"Profil: {profile.name} ({profile.display_name})")
    print(f"API: {profile.base_url}")
    print(f"Model: {profile.model}")
    print(f"API-Key: {redact_secret(profile.api_key)}")
    client = OpenAICompatClient(profile, retries=1)
    models = client.list_models()
    print(f"/models: ok ({', '.join(models) if models else 'keine IDs gemeldet'})")
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
        print(f"{label}: ok ({result.content[:80]!r})")
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
    if not line.startswith("/"):
        return []
    command_token, separator, rest = line.partition(" ")
    if not separator:
        return [f"{name} " for name in slash_command_name_suggestions(command_token)]

    command = canonical_slash_command(command_token)
    prefix = rest.rsplit(maxsplit=1)[-1] if rest and not rest.endswith(" ") else ""
    if command in {"/profile", "/provider"}:
        return _completion_matches(sorted(cfg.profiles), prefix)
    if command == "/model":
        return _completion_matches(_configured_models(cfg), prefix)
    if command == "/template":
        return _completion_matches(sorted(cfg.prompt_templates), prefix)
    if command in {"/folder", "/move", "/rename-folder"}:
        return _completion_matches([folder.name for folder in store.list_folders()], prefix)
    if command == "/load":
        return _completion_matches(_session_refs(store), prefix)
    if command == "/sort":
        return _completion_matches(sorted(SESSION_SORTS), prefix)
    if command in {"/history"}:
        return _completion_matches(["6", "12", "24", "48"], prefix)
    return []


def _completion_matches(values: Iterable[str], prefix: str) -> list[str]:
    clean = prefix.lower()
    matches = []
    for value in values:
        if value.lower().startswith(clean):
            matches.append(f"{value} ")
    return matches[:24]


def _configured_models(cfg: object) -> list[str]:
    models: list[str] = []
    seen: set[str] = set()
    for profile in cfg.profiles.values():
        for model in profile.models or [profile.model]:
            if model not in seen:
                models.append(model)
                seen.add(model)
    return models


def _session_refs(store: ChatStore) -> list[str]:
    refs: list[str] = []
    for session in store.list_sessions(100):
        refs.append(session.id)
        if session.title:
            refs.append(session.title)
    return refs


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
) -> tuple[bool, Profile, str, object]:
    command, _, rest = raw.partition(" ")
    command = canonical_slash_command(command.lower())
    rest = rest.strip()
    if command == "/exit":
        return False, profile, system_prompt, session
    if command == "/help":
        print(slash_command_help())
    elif command == "/new":
        title = rest or "Neue Unterhaltung"
        session = store.create_session(
            title=title, profile=profile.name, system_prompt=system_prompt
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
            system_prompt=system_prompt,
        )
        print(f"Session geloescht: {old_id}")
        print(f"Neue Session: {session.id}")
    elif command == "/sessions":
        for item in store.list_sessions(20):
            pin = "*" if item.pinned else " "
            print(f"{pin} {item.id}  {item.profile:12}  {item.title}")
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
        except ApiError as exc:
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
                store.add_message(session.id, "user", prompt)
                history = store.messages(session.id, limit=cfg.max_history_messages)
                messages = messages_for_api(system_prompt, history)
                try:
                    print("KI> ", end="", flush=True)
                    answer = _run_chat(profile, messages, stream=stream)
                except ApiError as exc:
                    print(f"\nFehler: {exc}", file=sys.stderr)
                else:
                    store.add_message(session.id, "assistant", answer)
    elif command == "/folder-system":
        folder_id = getattr(session, "folder_id", None)
        if not folder_id:
            print("Aktuelle Session liegt in keinem Ordner.")
        elif rest:
            folder = store.update_folder_system_prompt(folder_id, rest)
            print(f"Ordner-Systemprompt gesetzt: {folder.name}")
        else:
            folder = store.get_folder(folder_id)
            if folder is None:
                print("Ordner nicht gefunden.")
            else:
                print(folder.system_prompt or "<leer>")
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
                pin = "*" if item.pinned else " "
                print(f"{pin} {item.id}  {item.profile:12}  {item.title}")
    elif command == "/search":
        if not rest:
            print("Nutzung: /search TEXT")
        else:
            for item in store.list_sessions(20, query=rest):
                pin = "*" if item.pinned else " "
                print(f"{pin} {item.id}  {item.profile:12}  {item.title}")
    elif command in {"/profile", "/provider"}:
        if not rest:
            print(f"Aktiv: {profile.name} ({profile.display_name})")
        else:
            profile = cfg.profile(rest)
            print(f"Aktiv: {profile.name} ({profile.display_name})")
    elif command == "/model":
        if not rest:
            print(f"Aktiv: {profile.model}")
        else:
            configured = profile.models or [profile.model]
            model = next((item for item in configured if item.lower() == rest.lower()), rest)
            profile = profile.with_overrides(model=model)
            print(f"Modell: {profile.model}")
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
    return True, profile, system_prompt, session


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


def _apply_prompt_template(cfg: object, name: str, text: str = "") -> str:
    try:
        template = cfg.prompt_templates[name]
    except KeyError as exc:
        available = ", ".join(sorted(cfg.prompt_templates)) or "<keine>"
        raise ConfigError(
            f"Prompt-Template '{name}' existiert nicht. Verfuegbar: {available}"
        ) from exc
    clean = text.strip()
    if "{input}" in template:
        return template.replace("{input}", clean)
    return f"{template}\n\n{clean}".strip() if clean else template


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
